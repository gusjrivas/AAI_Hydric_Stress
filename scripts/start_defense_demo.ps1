<#
.SYNOPSIS
    Arranque/parada reproducible y transaccional de los tres modos de la
    demo de defensa (Pergamino, Melchor Romero, Laboratorio de sensores)
    desde un checkout limpio, sin rutas personales hardcodeadas.

.DESCRIPTION
    Envoltorio sobre los scripts ya existentes
    (`scripts/run_producer_preview_backend.py`, `uvicorn backend.app.main:app`)
    y sobre `npm run dev` del frontend. No entrena modelos, no prepara
    emisiones nuevas, no sustituye artefactos faltantes por datos sintéticos:
    si falta algo, falla con un diagnóstico concreto (delegado a los scripts
    Python ya validados, cuya salida de error hace fallar todo el arranque)
    y no arranca en un estado a medias.

    Los tres modos:

    - "pergamino" y "melchor-romero" comparten el mismo backend
      (`producer_v2`, genérico por sensor_id): requieren -DataDir y
      -BundleRoot apuntando a directorios EXTERNOS (nunca `data/` del
      repositorio) ya preparados. Ver docs/design/defense-demo-startup-guide.md.
    - "sensor-lab" arranca un backend plano (`uvicorn backend.app.main:app`)
      sin la fachada producer_v2, contra el propio `data/` del repositorio
      (los sensores del laboratorio usan el prefijo aislado `lab-`, ya
      excluido de git). No requiere -DataDir/-BundleRoot.
    - "all" arranca ambos backends (producer_v2 + laboratorio) y un único
      frontend, que separa sus solicitudes entre los dos backends vía
      VITE_API_BASE_URL (laboratorio) y VITE_PRODUCER_API_BASE_URL
      (Pergamino/Melchor Romero) -- ver frontend/src/api/baseUrl.ts. Antes
      de esta variable, todos los clientes del frontend compartían
      VITE_API_BASE_URL y en -Mode all las lecturas del laboratorio se
      enviaban por error al backend productor.

    Arranque transaccional: cada invocación registra en
    .defense-demo-run/registry.json (gitignored) qué procesos creó ella
    misma (servicio, PID, instante de creación del proceso, ejecutable,
    identificador de esta ejecución -- no solo el PID, que Windows puede
    reciclar). No anuncia éxito hasta que cada servicio solicitado responde
    realmente (ver sección de espera de disponibilidad). Ante cualquier
    fallo durante el arranque, se revierte -- se detienen únicamente los
    procesos que ESTA invocación creó, verificando su identidad antes de
    matarlos, preservando los logs. `-Stop` es idempotente y solo actúa
    sobre procesos cuya identidad coincide con lo registrado; un PID
    reciclado por otro proceso nunca se detiene.

.PARAMETER Mode
    Uno de: pergamino, melchor-romero, sensor-lab, all.

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
    máquinas donde el intérprete correcto no está en PATH, pasar la ruta
    completa, p. ej. -PythonExe "C:\ruta\a\tu\venv\Scripts\python.exe".

.PARAMETER ReadyTimeoutSeconds
    Plazo máximo, en segundos, para esperar a que CADA servicio arrancado
    responda antes de considerarlo fallido. Default 60.

.PARAMETER Stop
    Detiene los procesos previamente registrados por este script en
    .defense-demo-run/registry.json (verificando identidad) y no arranca
    nada nuevo. Idempotente: correrlo sin nada que detener no es un error.

.EXAMPLE
    ./scripts/start_defense_demo.ps1 -Mode sensor-lab

.EXAMPLE
    ./scripts/start_defense_demo.ps1 -Mode all -DataDir <...> -BundleRoot <...>

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

    [Parameter(ParameterSetName = 'Start')]
    [int]$ReadyTimeoutSeconds = 60,

    [Parameter(ParameterSetName = 'Stop', Mandatory = $true)]
    [switch]$Stop
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runDir = Join-Path $repoRoot '.defense-demo-run'
$registryPath = Join-Path $runDir 'registry.json'
$runId = [guid]::NewGuid().ToString('N')

function Write-Info($msg) { Write-Host "[start_defense_demo] $msg" }
function Write-Err($msg) { Write-Host "[start_defense_demo] ERROR: $msg" -ForegroundColor Red }

# =======================================================================
# TODAS las definiciones de función van antes del guard de dot-source de
# más abajo, para que scripts/start_defense_demo.Tests.ps1 pueda hacer
# `. .\start_defense_demo.ps1` y reusarlas (Test-PortAssignment,
# Resolve-FrontendBaseUrls, Test-IdentityMatches, etc.) sin arrancar
# procesos reales ni exigir -Mode/-Stop.
# =======================================================================

# ---------------------------------------------------------------------
# Identidad de procesos y registro estructurado
# ---------------------------------------------------------------------

function Get-ProcessIdentity([int]$processId) {
    # CreationDate + ExecutablePath identifican un proceso de forma mucho
    # más confiable que el PID solo: Windows recicla PIDs, así que un PID
    # que coincide con un registro viejo puede ser un proceso totalmente
    # distinto arrancado después. Devuelve $null si el PID no existe.
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    if (-not $proc) { return $null }
    return [pscustomobject]@{
        ProcessId      = $processId
        CreationTime   = $proc.CreationDate
        ExecutablePath = $proc.ExecutablePath
    }
}

function Test-IdentityMatches($recorded, $current) {
    if (-not $current) { return $false }
    # Hallazgo del ensayo de esta tarea: ConvertTo-Json/ConvertFrom-Json
    # serializa el DateTime grabado como Kind=Utc (formato ISO "Z"),
    # mientras que Get-CimInstance siempre devuelve CreationDate con
    # Kind=Local. El operador "-" de [datetime] en PowerShell/.NET NO
    # ajusta por Kind -- resta los Ticks tal cual, así que comparar sin
    # normalizar produce una diferencia falsa exactamente igual al offset
    # de huso horario de la máquina (3 horas aquí). Se normalizan ambos a
    # UTC explícitamente antes de comparar, con tolerancia de 1 segundo
    # por la granularidad/redondeo de la serialización JSON.
    $recordedTime = ([datetime]$recorded.CreationTime).ToUniversalTime()
    $currentTime = ([datetime]$current.CreationTime).ToUniversalTime()
    $sameTime = [math]::Abs(($recordedTime - $currentTime).TotalSeconds) -lt 1
    $sameExe = $recorded.ExecutablePath -eq $current.ExecutablePath
    return $sameTime -and $sameExe
}

function Read-Registry {
    if (-not (Test-Path $registryPath)) { return @() }
    try {
        $raw = Get-Content $registryPath -Raw -ErrorAction Stop
        if ([string]::IsNullOrWhiteSpace($raw)) { return @() }
        $parsed = $raw | ConvertFrom-Json
        if ($null -eq $parsed) { return @() }
        if ($parsed -isnot [System.Array]) { return @($parsed) }
        return $parsed
    } catch {
        Write-Err "registry.json existe pero no se pudo leer/parsear ($($_.Exception.Message)); se trata como vacío para no perder el control de procesos ajenos."
        return @()
    }
}

function Save-Registry($entries) {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    ($entries | ConvertTo-Json -Depth 5) | Set-Content -Path $registryPath -Encoding UTF8
}

$script:trackedThisRun = New-Object System.Collections.Generic.List[object]

function Add-TrackedProcess([string]$service, [int]$processId, [string]$logBase) {
    $identity = Get-ProcessIdentity -processId $processId
    if (-not $identity) {
        throw "No se pudo leer la identidad del proceso recién arrancado para '$service' (PID $processId); no se puede rastrear con confianza."
    }
    $entry = [pscustomobject]@{
        service        = $service
        pid            = $processId
        creationTime   = $identity.CreationTime
        executablePath = $identity.ExecutablePath
        runId          = $runId
        logBase        = $logBase
    }
    $script:trackedThisRun.Add($entry) | Out-Null
    $existing = Read-Registry
    Save-Registry -entries (@($existing) + @($entry))
    return $entry
}

function Test-OwnRunActive {
    # "Detectar una ejecución propia todavía activa; no sobrescribir su
    # registro ni detenerla automáticamente." Se considera activa una
    # entrada del registro cuyo PID existe con la MISMA identidad grabada
    # (no solo el mismo número de PID).
    $existing = Read-Registry
    $active = @()
    foreach ($entry in $existing) {
        $current = Get-ProcessIdentity -processId $entry.pid
        if (Test-IdentityMatches -recorded $entry -current $current) {
            $active += $entry
        }
    }
    return $active
}

function Stop-ProcessTreeVerified([int]$processId, $expectedIdentity, [System.Collections.Generic.List[string]]$diagnostics) {
    # $diagnostics es una List<string> (tipo referencia de .NET): las
    # mutaciones con .Add() dentro de esta función y de sus llamadas
    # recursivas ya son visibles para quien la creó, sin necesitar [ref]
    # (que además causó un ArgumentException real en el ensayo de esta
    # tarea al mezclarlo con un objeto que ya era List<T>).
    # Se detienen primero los descendientes (recursivo), verificando en
    # cada nivel que el padre inmediato sea el proceso ya validado -- así
    # nunca se mata un proceso ajeno que por coincidencia comparte PID de
    # padre con uno reciclado.
    $current = Get-ProcessIdentity -processId $processId
    if (-not (Test-IdentityMatches -recorded $expectedIdentity -current $current)) {
        $diagnostics.Add("PID $processId ya no tiene la identidad registrada (creado=$($expectedIdentity.CreationTime), ejecutable=$($expectedIdentity.ExecutablePath)) -- no se detiene, puede ser un proceso distinto reciclando ese PID.") | Out-Null
        return
    }
    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$processId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        $childIdentity = Get-ProcessIdentity -processId $child.ProcessId
        if ($childIdentity) {
            Stop-ProcessTreeVerified -processId $child.ProcessId -expectedIdentity $childIdentity -diagnostics $diagnostics
        }
    }
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

function Stop-TrackedProcesses([switch]$OnlyThisRun) {
    if (-not (Test-Path $registryPath)) {
        # Compatibilidad hacia atrás: si solo hay *.pid viejos (sin
        # identidad), no se usan para matar -- se informa que no se puede
        # verificar el propietario, en vez de arriesgarse a matar un
        # proceso ajeno que recicló ese PID.
        $legacyPids = Get-ChildItem -Path $runDir -Filter '*.pid' -ErrorAction SilentlyContinue
        if ($legacyPids) {
            Write-Info "Se encontraron archivos .pid antiguos sin identidad verificable (de una versión anterior de este script): $($legacyPids.Name -join ', '). No se usan para detener procesos -- no se puede confirmar que el PID siga perteneciendo al mismo proceso. Borralos manualmente si estás seguro de que no hay nada corriendo."
        } else {
            Write-Info "No hay registry.json: nada que detener."
        }
        return
    }
    $entries = Read-Registry
    if ($OnlyThisRun) {
        $toStop = $entries | Where-Object { $_.runId -eq $runId }
    } else {
        $toStop = $entries
    }
    if (-not $toStop -or @($toStop).Count -eq 0) {
        Write-Info "registry.json no tiene entradas para detener (posiblemente ya detenido antes: -Stop es idempotente)."
        return
    }
    $diagnostics = New-Object System.Collections.Generic.List[string]
    $remaining = New-Object System.Collections.Generic.List[object]
    foreach ($entry in $entries) {
        $shouldStop = -not $OnlyThisRun -or $entry.runId -eq $runId
        if (-not $shouldStop) {
            $remaining.Add($entry) | Out-Null
            continue
        }
        $identity = [pscustomobject]@{ CreationTime = $entry.creationTime; ExecutablePath = $entry.executablePath }
        $current = Get-ProcessIdentity -processId $entry.pid
        if (Test-IdentityMatches -recorded $identity -current $current) {
            Write-Info "Deteniendo $($entry.service) (PID $($entry.pid)) y su árbol de procesos verificado."
            Stop-ProcessTreeVerified -processId $entry.pid -expectedIdentity $identity -diagnostics $diagnostics
        } else {
            Write-Info "$($entry.service) (PID $($entry.pid)) ya no está corriendo, o el PID fue reciclado por otro proceso: no se detiene nada, se limpia solo el registro."
        }
        # Se remueve del registro tanto si se detuvo como si ya no existía
        # (idempotencia: la segunda corrida de -Stop no vuelve a intentarlo).
    }
    # Nota: envolver una System.Collections.Generic.List[object] vacía con
    # el operador @() de PowerShell dispara un ArgumentException real
    # ("Los tipos de argumentos no coinciden", confirmado en el ensayo de
    # esta tarea) en el binder interno de PSToObjectArrayBinder en esta
    # versión de PowerShell -- .ToArray() evita ese camino.
    Save-Registry -entries $remaining.ToArray()
    foreach ($d in $diagnostics) { Write-Info $d }
    Write-Info "Servicios detenidos (logs preservados en .defense-demo-run/)."
}

# ---------------------------------------------------------------------
# Validación previa (funciones puras, testeables sin arrancar procesos)
# ---------------------------------------------------------------------

function Test-PortFree([int]$port) {
    $listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return -not $listening
}

function Test-PortAssignment([System.Collections.Generic.List[object]]$portsToUse) {
    # Separada del flujo principal para poder probarla con Pester sin
    # arrancar procesos reales. Lanza una excepción ante rango inválido,
    # duplicados, o puerto ya escuchando (Test-PortFree sí toca la red).
    foreach ($p in $portsToUse) {
        if ($p.value -lt 1 -or $p.value -gt 65535) {
            throw "$($p.name)=$($p.value) fuera de rango válido (1-65535)."
        }
    }
    $dupGroups = $portsToUse | Group-Object { $_.value } | Where-Object { $_.Count -gt 1 }
    if ($dupGroups) {
        $dupDesc = ($dupGroups | ForEach-Object { "puerto $($_.Name) usado por " + (($_.Group | ForEach-Object { $_.name }) -join ' y ') }) -join '; '
        throw "Puertos duplicados entre los servicios que se van a arrancar: $dupDesc. Cada servicio necesita su propio puerto."
    }
    foreach ($p in $portsToUse) {
        if (-not (Test-PortFree -port $p.value)) {
            throw "El puerto $($p.value) ($($p.name)) ya está en uso (socket en estado Listen). Elegí otro puerto, o corré -Stop si es una ejecución anterior de este mismo script."
        }
    }
}

function Resolve-FrontendBaseUrls([string]$Mode, [int]$ProducerPort, [int]$LabPort, [bool]$NeedsProducer, [bool]$NeedsLab) {
    # Función pura: decide a qué backend apunta cada una de las dos
    # variables de entorno del frontend según el modo. Separada del flujo
    # principal específicamente para poder probarla con Pester sin
    # arrancar Vite ni ningún backend real (hallazgo de esta tarea: antes
    # de existir VITE_PRODUCER_API_BASE_URL, -Mode all mandaba las
    # lecturas del laboratorio al backend productor por compartir una sola
    # variable).
    if ($Mode -eq 'all') {
        return @{ ApiBaseUrl = "http://127.0.0.1:$LabPort"; ProducerApiBaseUrl = "http://127.0.0.1:$ProducerPort" }
    } elseif ($NeedsLab) {
        return @{ ApiBaseUrl = "http://127.0.0.1:$LabPort"; ProducerApiBaseUrl = "http://127.0.0.1:$LabPort" }
    } elseif ($NeedsProducer) {
        return @{ ApiBaseUrl = "http://127.0.0.1:$ProducerPort"; ProducerApiBaseUrl = "http://127.0.0.1:$ProducerPort" }
    }
    return @{ ApiBaseUrl = $null; ProducerApiBaseUrl = $null }
}

# ---------------------------------------------------------------------
# Espera de disponibilidad real (no solo "el proceso existe")
# ---------------------------------------------------------------------

function Wait-ForHttpReady {
    param(
        [Parameter(Mandatory)][string]$Service,
        [Parameter(Mandatory)][int]$ProcessId,
        [Parameter(Mandatory)][string]$Url,
        [Parameter(Mandatory)][int]$TimeoutSeconds,
        [scriptblock]$Validate = { param($response) $true },
        [string]$LogBase
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = $null
    while ((Get-Date) -lt $deadline) {
        $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if (-not $proc) {
            $errLog = if ($LogBase) { "$LogBase.err.log" } else { '(sin log)' }
            throw "$Service (PID $ProcessId) terminó durante la espera de disponibilidad, antes de responder. Ver log: $errLog"
        }
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
            if (& $Validate $response) {
                return
            } else {
                $lastError = "respuesta recibida pero no pasó la validación esperada (status=$($response.StatusCode))"
            }
        } catch {
            $lastError = $_.Exception.Message
        }
        Start-Sleep -Milliseconds 500
    }
    $errLog = if ($LogBase) { "$LogBase.err.log" } else { '(sin log)' }
    throw "$Service no respondió correctamente en $Url dentro de $TimeoutSeconds s (último error: $lastError). Ver log: $errLog"
}

# ---------------------------------------------------------------------
# Entorno: guardar/restaurar (funciones puras sobre Env:, testeables)
# ---------------------------------------------------------------------

$script:envSnapshot = @{}
function Save-EnvVar([string]$name) {
    if (Test-Path "Env:\$name") { $script:envSnapshot[$name] = (Get-Item "Env:\$name").Value }
    else { $script:envSnapshot[$name] = $null }
}

function Restore-EnvVars {
    foreach ($name in $script:envSnapshot.Keys) {
        if ($null -eq $script:envSnapshot[$name]) {
            Remove-Item "Env:\$name" -ErrorAction SilentlyContinue
        } else {
            Set-Item "Env:\$name" $script:envSnapshot[$name]
        }
    }
}

# =======================================================================
# A partir de acá, ejecución imperativa real. Protegida contra correr al
# hacer dot-source (`. .\start_defense_demo.ps1`, usado por los tests de
# Pester para reusar las funciones de arriba sin arrancar nada real).
# Invocado normalmente (`& .\start_defense_demo.ps1 ...` o
# `.\start_defense_demo.ps1 ...`), $MyInvocation.InvocationName nunca es
# '.', así que el comportamiento para uso real no cambia.
# =======================================================================
if ($MyInvocation.InvocationName -eq '.') { return }

if ($Stop) {
    Stop-TrackedProcesses
    return
}

$needsProducer = $Mode -in @('pergamino', 'melchor-romero', 'all')
$needsLab = $Mode -in @('sensor-lab', 'all')
$needsFrontend = -not $SkipFrontend

$portsToUse = New-Object System.Collections.Generic.List[object]
if ($needsProducer) { $portsToUse.Add(@{ name = '-ProducerPort'; value = $ProducerPort }) | Out-Null }
if ($needsLab) { $portsToUse.Add(@{ name = '-LabPort'; value = $LabPort }) | Out-Null }
if ($needsFrontend) { $portsToUse.Add(@{ name = '-FrontendPort'; value = $FrontendPort }) | Out-Null }

Test-PortAssignment -portsToUse $portsToUse

# Detectar una ejecución propia todavía activa: no se sobrescribe su
# registro ni se la detiene automáticamente.
$activeOwnRun = Test-OwnRunActive
if ($activeOwnRun -and @($activeOwnRun).Count -gt 0) {
    $desc = ($activeOwnRun | ForEach-Object { "$($_.service) (PID $($_.pid), runId $($_.runId))" }) -join ', '
    throw "Ya hay una ejecución propia de este script activa (verificada por identidad de proceso, no solo PID): $desc. Corré '-Stop' primero, o esperá a que termine, antes de arrancar una nueva. No se sobrescribe su registro ni se la detiene automáticamente."
}

# Verificar Python.
try {
    $pythonVersionOutput = & $PythonExe --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "código de salida $LASTEXITCODE" }
} catch {
    throw "No se pudo ejecutar '$PythonExe --version' ($($_.Exception.Message)). Verificá -PythonExe o que 'python' esté en PATH."
}
Write-Info "Python verificado: $pythonVersionOutput"

# Verificar npm y dependencias del frontend, si se va a arrancar.
if ($needsFrontend) {
    try {
        $npmVersion = & cmd.exe /c npm --version 2>&1
        if ($LASTEXITCODE -ne 0) { throw "código de salida $LASTEXITCODE" }
    } catch {
        throw "No se pudo ejecutar 'npm --version' ($($_.Exception.Message)). Instalá Node.js/npm o agregalo a PATH."
    }
    Write-Info "npm verificado: $npmVersion"
    $frontendNodeModules = Join-Path $repoRoot 'frontend\node_modules'
    if (-not (Test-Path $frontendNodeModules)) {
        throw "Falta frontend/node_modules. Corré 'npm ci' (o 'npm install') dentro de frontend/ antes de arrancar el frontend, o pasá -SkipFrontend."
    }
    Write-Info "Dependencias del frontend verificadas (frontend/node_modules existe)."
}

# Validar existencia de DataDir/BundleRoot para los modos que los
# requieren. La validación PROFUNDA de contenido (lecturas/emisiones/
# manifiestos reales) sigue delegada al lanzador Python
# (run_producer_preview_backend.py) -- esto es solo un chequeo previo de
# existencia para fallar más rápido y con un mensaje más claro.
if ($needsProducer) {
    if (-not $DataDir -or -not $BundleRoot) {
        throw "El modo '$Mode' requiere -DataDir y -BundleRoot (directorios EXTERNOS, nunca data/ del repositorio). " +
              "Ver docs/design/defense-demo-startup-guide.md para cómo prepararlos por sitio."
    }
    if (-not (Test-Path -LiteralPath $DataDir -PathType Container)) {
        throw "-DataDir '$DataDir' no existe o no es un directorio."
    }
    if (-not (Test-Path -LiteralPath $BundleRoot -PathType Container)) {
        throw "-BundleRoot '$BundleRoot' no existe o no es un directorio."
    }
}

New-Item -ItemType Directory -Path $runDir -Force | Out-Null

foreach ($n in @('CORS_EXTRA_ORIGINS', 'PRODUCER_DATA_DIR', 'PRODUCER_BUNDLE_ROOT', 'PRODUCER_PREVIEW_PORT', 'PRODUCER_V2_ENABLED', 'VITE_API_BASE_URL', 'VITE_PRODUCER_API_BASE_URL')) {
    Save-EnvVar $n
}

try {
    if ($needsFrontend) {
        # CORS_EXTRA_ORIGINS debe quedar seteada ANTES de arrancar
        # cualquier backend (el proceso hijo hereda el entorno al momento
        # de Start-Process).
        $env:CORS_EXTRA_ORIGINS = "http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort"
    }

    if ($needsProducer) {
        Write-Info "Arrancando backend producer_v2 (Pergamino/Melchor Romero) en el puerto $ProducerPort..."
        $env:PRODUCER_DATA_DIR = $DataDir
        $env:PRODUCER_BUNDLE_ROOT = $BundleRoot
        $env:PRODUCER_PREVIEW_PORT = "$ProducerPort"
        $producerOut = Join-Path $runDir 'producer_backend.out.log'
        $producerErr = Join-Path $runDir 'producer_backend.err.log'
        # La validación profunda de artefactos vive en este lanzador
        # Python (run_producer_preview_backend.py): si falla (falta algo
        # en DataDir/BundleRoot), termina con código de error y ese error
        # debe hacer fallar todo el arranque -- se detecta en
        # Wait-ForHttpReady por el proceso terminando durante la espera.
        $proc = Start-Process -FilePath $PythonExe -ArgumentList 'scripts/run_producer_preview_backend.py' `
            -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $producerOut -RedirectStandardError $producerErr
        Add-TrackedProcess -service 'producer_backend' -processId $proc.Id -logBase (Join-Path $runDir 'producer_backend') | Out-Null
        Wait-ForHttpReady -Service 'Backend producer_v2' -ProcessId $proc.Id `
            -Url "http://127.0.0.1:$ProducerPort/api/v2/sensors" -TimeoutSeconds $ReadyTimeoutSeconds `
            -Validate { param($r) $r.StatusCode -eq 200 } -LogBase (Join-Path $runDir 'producer_backend')
        Write-Info "Backend producer_v2 arrancado y verificado (PID $($proc.Id)) en http://127.0.0.1:$ProducerPort"
    }

    if ($needsLab) {
        Write-Info "Arrancando backend plano del laboratorio de sensores en el puerto $LabPort..."
        $labOut = Join-Path $runDir 'lab_backend.out.log'
        $labErr = Join-Path $runDir 'lab_backend.err.log'
        Push-Location $repoRoot
        try {
            $labProc = Start-Process -FilePath $PythonExe `
                -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$LabPort" `
                -WorkingDirectory $repoRoot -PassThru -WindowStyle Hidden `
                -RedirectStandardOutput $labOut -RedirectStandardError $labErr
        } finally {
            Pop-Location
        }
        Add-TrackedProcess -service 'lab_backend' -processId $labProc.Id -logBase (Join-Path $runDir 'lab_backend') | Out-Null
        Wait-ForHttpReady -Service 'Backend del laboratorio' -ProcessId $labProc.Id `
            -Url "http://127.0.0.1:$LabPort/openapi.json" -TimeoutSeconds $ReadyTimeoutSeconds `
            -Validate {
                param($r)
                if ($r.StatusCode -ne 200) { return $false }
                $schema = $r.Content | ConvertFrom-Json
                # Confirma que la ruta genérica de ingesta de lecturas está
                # publicada -- no solo que el servidor HTTP responde algo.
                return [bool]($schema.paths.PSObject.Properties.Name | Where-Object { $_ -like '*/readings*' })
            } -LogBase (Join-Path $runDir 'lab_backend')
        Write-Info "Backend del laboratorio arrancado y verificado (PID $($labProc.Id)) en http://127.0.0.1:$LabPort"
    }

    if ($needsFrontend) {
        Write-Info "Arrancando frontend (Vite) en el puerto $FrontendPort..."
        # Separación de conexiones (hallazgo de esta tarea): en -Mode all,
        # VITE_API_BASE_URL (usada por el laboratorio, forecast operativo,
        # calidad y linaje) y VITE_PRODUCER_API_BASE_URL (usada
        # exclusivamente por los cuatro clientes de frontend/src/features/
        # producer/*Api.ts: catalogApi, readingsApi, forecastsApi,
        # historicalApi) deben apuntar a backends DISTINTOS -- si ambas
        # apuntaran al mismo puerto, las lecturas del laboratorio
        # terminarían escribiéndose en el PRODUCER_DATA_DIR compartido.
        $urls = Resolve-FrontendBaseUrls -Mode $Mode -ProducerPort $ProducerPort -LabPort $LabPort -NeedsProducer $needsProducer -NeedsLab $needsLab
        if ($urls.ApiBaseUrl) { $env:VITE_API_BASE_URL = $urls.ApiBaseUrl }
        if ($urls.ProducerApiBaseUrl) { $env:VITE_PRODUCER_API_BASE_URL = $urls.ProducerApiBaseUrl }
        $frontendOut = Join-Path $runDir 'frontend.out.log'
        $frontendErr = Join-Path $runDir 'frontend.err.log'
        # `npm` es un script .cmd en Windows: Start-Process -FilePath npm
        # falla ("no es una aplicación Win32 válida"); se invoca vía
        # cmd.exe /c. --host 127.0.0.1 fuerza IPv4 (esta máquina bindeaba
        # solo [::1] por defecto). --strictPort evita que Vite "resuelva"
        # un puerto ocupado eligiendo otro distinto en silencio -- sin
        # esto, el puerto realmente usado podría no coincidir con
        # -FrontendPort y la espera de disponibilidad fallaría contra el
        # puerto equivocado sin que quede claro por qué.
        $feProc = Start-Process -FilePath cmd.exe -ArgumentList '/c', 'npm', 'run', 'dev', '--', '--port', "$FrontendPort", '--host', '127.0.0.1', '--strictPort' `
            -WorkingDirectory (Join-Path $repoRoot 'frontend') -PassThru -WindowStyle Hidden `
            -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr
        Add-TrackedProcess -service 'frontend' -processId $feProc.Id -logBase (Join-Path $runDir 'frontend') | Out-Null
        Wait-ForHttpReady -Service 'Frontend' -ProcessId $feProc.Id `
            -Url "http://127.0.0.1:$FrontendPort/" -TimeoutSeconds $ReadyTimeoutSeconds `
            -Validate { param($r) $r.StatusCode -eq 200 } -LogBase (Join-Path $runDir 'frontend')
        Write-Info "Frontend arrancado y verificado (PID $($feProc.Id)) en http://127.0.0.1:$FrontendPort"
    }

    Write-Info "Listo -- todos los servicios solicitados respondieron correctamente. Para detener: ./scripts/start_defense_demo.ps1 -Stop"
}
catch {
    Write-Err $_.Exception.Message
    Write-Info "Revirtiendo: deteniendo únicamente los procesos creados por ESTA invocación (runId $runId), preservando logs..."
    Stop-TrackedProcesses -OnlyThisRun
    Restore-EnvVars
    throw
}
finally {
    Restore-EnvVars
}
