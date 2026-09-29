<#
.SYNOPSIS
    Arranque/parada reproducible de los tres modos de la demo de defensa
    (Pergamino, Melchor Romero, Laboratorio de sensores) desde un checkout
    limpio, sin rutas personales hardcodeadas.

.DESCRIPTION
    Envoltorio fino sobre los scripts ya existentes
    (`scripts/run_producer_preview_backend.py`, `uvicorn backend.app.main:app`)
    y sobre `npm run dev` del frontend. No entrena modelos, no prepara
    emisiones nuevas, no sustituye artefactos faltantes por datos sintéticos:
    si falta algo, falla con un diagnóstico concreto (delegado a los scripts
    Python ya validados) y no arranca en un estado a medias.

    Los tres modos:

    - "pergamino" y "melchor-romero" comparten el mismo backend
      (`producer_v2`, genérico por sensor_id): requieren -DataDir y
      -BundleRoot apuntando a directorios EXTERNOS (nunca `data/` del
      repositorio) ya preparados:
        * Pergamino: preparación externa documentada en
          docs/design/ensemble-real-execution-report-2026-09-26.md +
          scripts/prepare_defense_data.ps1 (requiere artefactos reales que
          no están versionados en este repositorio).
        * Melchor Romero: reproducible desde el propio repositorio con
          scripts/prepare_melchor_romero_historical_demo.py --data-dir
          <DataDir> --bundle-root <BundleRoot> (usa el dataset versionado
          data/melchor_romero_2024_consolidado.parquet).
      Ambos sitios pueden convivir en el mismo -DataDir/-BundleRoot (los
      archivos se nombran por sensor_id) para servirse desde el mismo
      backend, o usarse por separado.

    - "sensor-lab" arranca un backend plano (`uvicorn backend.app.main:app`)
      sin la fachada producer_v2, contra el propio `data/` del repositorio
      (los sensores del laboratorio usan el prefijo aislado `lab-`, ya
      excluido de git). No requiere -DataDir/-BundleRoot.

    El estado de arranque (PIDs, puertos) se registra en
    .defense-demo-run/ (gitignored) para poder detener limpiamente con
    -Stop, sin matar procesos ajenos.

.PARAMETER Mode
    Uno de: pergamino, melchor-romero, sensor-lab, all. "all" arranca un
    backend producer_v2 compartido (si -DataDir/-BundleRoot se pasan) más
    el backend plano del laboratorio, y el frontend una sola vez.

.PARAMETER DataDir
    Directorio externo con catálogo/lecturas/emisiones ya preparadas
    (PRODUCER_DATA_DIR). Requerido para pergamino/melchor-romero/all.

.PARAMETER BundleRoot
    Directorio externo con los bundles reales del ensamble
    (PRODUCER_BUNDLE_ROOT). Requerido para pergamino/melchor-romero/all.

.PARAMETER ProducerPort
    Puerto del backend producer_v2 (Pergamino/Melchor Romero). Default 8199.

.PARAMETER LabPort
    Puerto del backend plano del laboratorio. Default 8299.

.PARAMETER FrontendPort
    Puerto del frontend Vite. Default 5199.

.PARAMETER SkipFrontend
    No arranca el frontend (solo backend/s), útil para verificación por API.

.PARAMETER PythonExe
    Ejecutable de Python a usar (default "python", resuelto por PATH). En
    máquinas donde el intérprete correcto no está en PATH (verificado en
    esta tarea: no lo está en esta sesión), pasar la ruta completa, p. ej.
    -PythonExe "C:\ruta\a\tu\venv\Scripts\python.exe".

.PARAMETER Stop
    Detiene los procesos previamente arrancados por este script (lee
    .defense-demo-run/*.pid) y no arranca nada nuevo.

.EXAMPLE
    # Melchor Romero, reproducible sin artefactos externos manuales:
    python scripts/prepare_melchor_romero_historical_demo.py `
        --data-dir C:\ruta\externa\melchor-data --bundle-root C:\ruta\externa\melchor-bundles
    ./scripts/start_defense_demo.ps1 -Mode melchor-romero `
        -DataDir C:\ruta\externa\melchor-data -BundleRoot C:\ruta\externa\melchor-bundles

.EXAMPLE
    ./scripts/start_defense_demo.ps1 -Mode sensor-lab

.EXAMPLE
    ./scripts/start_defense_demo.ps1 -Stop
#>
[CmdletBinding(DefaultParameterSetName = 'Start')]
param(
    [Parameter(ParameterSetName = 'Start')]
    [ValidateSet('pergamino', 'melchor-romero', 'sensor-lab', 'all')]
    [string]$Mode = 'sensor-lab',

    [Parameter(ParameterSetName = 'Start')]
    [string]$DataDir,

    [Parameter(ParameterSetName = 'Start')]
    [string]$BundleRoot,

    [Parameter(ParameterSetName = 'Start')]
    [int]$ProducerPort = 8199,

    [Parameter(ParameterSetName = 'Start')]
    [int]$LabPort = 8299,

    [Parameter(ParameterSetName = 'Start')]
    [int]$FrontendPort = 5199,

    [Parameter(ParameterSetName = 'Start')]
    [switch]$SkipFrontend,

    [Parameter(ParameterSetName = 'Start')]
    [string]$PythonExe = 'python',

    [Parameter(ParameterSetName = 'Stop', Mandatory = $true)]
    [switch]$Stop
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runDir = Join-Path $repoRoot '.defense-demo-run'

function Write-Info($msg) { Write-Host "[start_defense_demo] $msg" }

function Test-PortFree([int]$port) {
    # Solo cuenta como "ocupado" un socket realmente escuchando (Listen).
    # TIME_WAIT/CLOSE_WAIT de una conexión ya cerrada no impiden bindear el
    # puerto y no deben bloquear un reinicio inmediato (hallazgo del ensayo
    # de esta tarea: el chequeo original rechazaba puertos libres).
    $listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return -not $listening
}

function Stop-ProcessTree([int]$processId) {
    # El frontend se lanza vía cmd.exe /c npm ..., que a su vez genera un
    # proceso node hijo: matar solo el PID rastreado (cmd.exe) deja el
    # servidor Vite huérfano corriendo. Se detienen recursivamente los
    # descendientes primero (hallazgo del ensayo de esta tarea).
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$processId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -processId $child.ProcessId
    }
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

function Stop-TrackedProcesses {
    if (-not (Test-Path $runDir)) {
        Write-Info "No hay .defense-demo-run/: nada que detener."
        return
    }
    Get-ChildItem -Path $runDir -Filter '*.pid' | ForEach-Object {
        $pidValue = (Get-Content $_.FullName -Raw).Trim()
        if ($pidValue -match '^\d+$') {
            $proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Info "Deteniendo $($_.BaseName) (PID $pidValue) y su árbol de procesos."
                Stop-ProcessTree -processId ([int]$pidValue)
            } else {
                Write-Info "$($_.BaseName) (PID $pidValue) ya no está en ejecución."
            }
        }
        Remove-Item $_.FullName -Force
    }
    Write-Info "Servicios de la demo de defensa detenidos."
}

if ($Stop) {
    Stop-TrackedProcesses
    return
}

New-Item -ItemType Directory -Path $runDir -Force | Out-Null

$needsProducer = $Mode -in @('pergamino', 'melchor-romero', 'all')
$needsLab = $Mode -in @('sensor-lab', 'all')

# CORS_EXTRA_ORIGINS debe quedar seteada ANTES de arrancar CUALQUIER backend
# (el proceso hijo hereda el entorno al momento de Start-Process): fijarla
# solo dentro de la rama producer_v2 dejaba al backend plano del
# laboratorio sin ese origen y el frontend fallaba con "Failed to fetch"
# (hallazgo del ensayo de esta tarea, modo sensor-lab con -FrontendPort
# distinto de 5173).
if (-not $SkipFrontend) {
    $env:CORS_EXTRA_ORIGINS = "http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort"
}

if ($needsProducer) {
    if (-not $DataDir -or -not $BundleRoot) {
        throw "El modo '$Mode' requiere -DataDir y -BundleRoot (directorios EXTERNOS, nunca data/ del repositorio). " +
              "Ver docs/design/defense-demo-startup-guide.md para cómo prepararlos por sitio."
    }
    if (-not (Test-PortFree -port $ProducerPort)) {
        throw "El puerto $ProducerPort ya está en uso. Elegí otro con -ProducerPort (puede haber otra sesión de verificación corriendo)."
    }
    Write-Info "Arrancando backend producer_v2 (Pergamino/Melchor Romero) en el puerto $ProducerPort..."
    $env:PRODUCER_DATA_DIR = $DataDir
    $env:PRODUCER_BUNDLE_ROOT = $BundleRoot
    $env:PRODUCER_PREVIEW_PORT = "$ProducerPort"
    $proc = Start-Process -FilePath $PythonExe -ArgumentList 'scripts/run_producer_preview_backend.py' `
        -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $runDir 'producer_backend.out.log') `
        -RedirectStandardError (Join-Path $runDir 'producer_backend.err.log')
    Set-Content -Path (Join-Path $runDir 'producer_backend.pid') -Value $proc.Id
    Write-Info "Backend producer_v2 arrancado (PID $($proc.Id)). Logs en .defense-demo-run/producer_backend.*.log"
}

if ($needsLab) {
    if (-not (Test-PortFree -port $LabPort)) {
        throw "El puerto $LabPort ya está en uso. Elegí otro con -LabPort."
    }
    Write-Info "Arrancando backend plano del laboratorio de sensores en el puerto $LabPort..."
    Push-Location $repoRoot
    try {
        $labProc = Start-Process -FilePath $PythonExe `
            -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$LabPort" `
            -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $runDir 'lab_backend.out.log') `
            -RedirectStandardError (Join-Path $runDir 'lab_backend.err.log')
    } finally {
        Pop-Location
    }
    Set-Content -Path (Join-Path $runDir 'lab_backend.pid') -Value $labProc.Id
    Write-Info "Backend del laboratorio arrancado (PID $($labProc.Id)). Logs en .defense-demo-run/lab_backend.*.log"
}

if (-not $SkipFrontend) {
    if (-not (Test-PortFree -port $FrontendPort)) {
        throw "El puerto $FrontendPort ya está en uso. Elegí otro con -FrontendPort."
    }
    Write-Info "Arrancando frontend (Vite) en el puerto $FrontendPort..."
    if ($needsProducer) { $env:VITE_API_BASE_URL = "http://127.0.0.1:$ProducerPort" }
    elseif ($needsLab) { $env:VITE_API_BASE_URL = "http://127.0.0.1:$LabPort" }
    # Start-Process (Windows PowerShell 5.1) no tiene parámetro -Environment: el
    # proceso hijo hereda las variables de entorno del proceso actual, que ya
    # fueron seteadas arriba (VITE_API_BASE_URL, y PRODUCER_*/CORS_EXTRA_ORIGINS
    # si corresponde).
    # `npm` es un script .cmd en Windows: Start-Process -FilePath npm falla
    # con "no es una aplicación Win32 válida" (hallazgo del ensayo de esta
    # tarea). Se invoca vía cmd.exe /c, igual que cualquier otro .cmd/.bat.
    # --host 127.0.0.1 fuerza IPv4: en esta máquina Vite se bindeó por
    # defecto solo a [::1] (IPv6), dejando http://127.0.0.1:<puerto>/
    # inalcanzable aunque "localhost" sí respondiera (hallazgo del ensayo de
    # esta tarea) — forzarlo evita esa ambigüedad para quien siga esta guía.
    $feProc = Start-Process -FilePath cmd.exe -ArgumentList '/c', 'npm', 'run', 'dev', '--', '--port', "$FrontendPort", '--host', '127.0.0.1' `
        -WorkingDirectory (Join-Path $repoRoot 'frontend') -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $runDir 'frontend.out.log') `
        -RedirectStandardError (Join-Path $runDir 'frontend.err.log')
    Set-Content -Path (Join-Path $runDir 'frontend.pid') -Value $feProc.Id
    Write-Info "Frontend arrancado (PID $($feProc.Id)) en http://127.0.0.1:$FrontendPort"
}

Write-Info "Listo. Para detener todo: ./scripts/start_defense_demo.ps1 -Stop"
