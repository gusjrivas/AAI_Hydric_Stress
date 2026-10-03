<#
.SYNOPSIS
    Deja la demo (Laboratorio, Mi cultivo, Pergamino y Melchor Romero) lista y la reinicia de cero cuando se quiera.

.DESCRIPTION
    Opera SOLO sobre el proyecto Compose aislado `aai-defense-rehearsal` (docker/defense-rehearsal/compose.yml):
    los servicios `lab-backend` y `producer-backend`, el volumen `aai-defense-rehearsal_lab_data` y la copia de trabajo
    de los datos del productor. No toca MLflow, MinIO, Postgres, `./data` del repositorio ni los demás contenedores.

    Estado que se restaura:
      * Datos del productor (Pergamino y Melchor Romero): copia de trabajo <- línea base, con verificación SHA-256.
      * Laboratorio: volumen recreado con SOLO los datos versionados del repositorio (se podan las sesiones
        `lab-*`/`demo-*` y los `feedback__*` que la imagen trae horneados, y `mlruns`).

    Acciones:
      -Action Init   Prepara la línea base una sola vez (copias estables fuera del repositorio, respaldo del volumen
                     actual del laboratorio y manifiesto de huellas). Requiere -ProducerDataSource y
                     -ProducerBundlesSource con los artefactos YA verificados de la demo.
      -Action Reset  Detiene los backends, restaura, recrea el volumen del laboratorio, levanta y verifica.
                     Con -StartFrontend también reinicia el frontend (Vite, puerto 15199).
      -Action Status Compara el estado actual con la línea base (no modifica nada).

.EXAMPLE
    ./scripts/demo_reset.ps1 -Action Init -ProducerDataSource <copia de producer-data> -ProducerBundlesSource <copia de producer-bundles>
    ./scripts/demo_reset.ps1 -Action Reset -StartFrontend
#>
[CmdletBinding()]
param(
    [ValidateSet("Init", "Reset", "Status")][string]$Action = "Reset",
    [string]$RuntimeDir,
    [string]$ProducerDataSource,
    [string]$ProducerBundlesSource,
    [switch]$StartFrontend,
    [switch]$Force,
    [int]$UiPort = 15199,
    [int]$LabPort = 18299,
    [int]$ProducerPort = 18199
)

# Docker escribe su progreso por stderr: en PowerShell 5.1 "Stop" lo trataría como error fatal.
# Los cmdlets sí detienen ante un error; los comandos nativos se validan con $LASTEXITCODE.
$ErrorActionPreference = "Continue"
$PSDefaultParameterValues["*:ErrorAction"] = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $RuntimeDir) { $RuntimeDir = Join-Path (Split-Path -Parent $repoRoot) "AAI_Hydric_Stress_demo_runtime" }
$compose = Join-Path $repoRoot "docker/defense-rehearsal/compose.yml"
$project = "aai-defense-rehearsal"
$labVolume = "$project`_lab_data"
$labImage = "aai-defense-rehearsal-backend:local"
$baseline = Join-Path $RuntimeDir "producer-data-baseline"
$work = Join-Path $RuntimeDir "producer-data"
$bundles = Join-Path $RuntimeDir "producer-bundles"
$manifest = Join-Path $RuntimeDir "producer-data-baseline.sha256"
$statePath = Join-Path $RuntimeDir "state.json"

function Say($m) { Write-Host "[demo_reset] $m" }
function Fail($m) { Write-Host "[demo_reset] ERROR: $m" -ForegroundColor Red; exit 1 }
function Fwd($p) { return ($p -replace "\\", "/") }

function Get-Snapshot([string]$root) {
    if (-not (Test-Path $root)) { return @() }
    $full = (Resolve-Path $root).Path
    return @(Get-ChildItem $full -Recurse -File -Force | Get-FileHash -Algorithm SHA256 |
        ForEach-Object { "{0}  {1}" -f $_.Hash, $_.Path.Substring($full.Length) } | Sort-Object)
}

function Set-ComposeEnv {
    $env:REHEARSAL_PRODUCER_DATA = Fwd $work
    $env:REHEARSAL_PRODUCER_BUNDLES = Fwd $bundles
    $env:REHEARSAL_UI_PORT = "$UiPort"
    $env:REHEARSAL_LAB_PORT = "$LabPort"
    $env:REHEARSAL_PRODUCER_PORT = "$ProducerPort"
}
function Compose { & docker compose -p $project -f $compose @args; if ($LASTEXITCODE -ne 0) { throw "docker compose $($args -join ' ') falló" } }

function Test-DockerReady {
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { Fail "Docker no responde. Iniciá Docker Desktop y reintentá." }
}

function Wait-Http([string]$url, [int]$seconds = 90) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try { if ((Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { return $true } } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

# Archivos de datos versionados del repositorio (lo único que debe quedar en el volumen del laboratorio).
function Get-TrackedDataNames {
    $names = & git -C $repoRoot ls-files -- data | ForEach-Object { ($_ -split "/")[1] } | Sort-Object -Unique
    if (-not $names) { Fail "No se pudieron leer los datos versionados de data/ (git ls-files)." }
    return @($names)
}

function New-CleanLabVolume {
    $keep = Get-TrackedDataNames
    & docker volume rm $labVolume *> $null   # puede no existir
    & docker volume create --label "com.docker.compose.project=$project" --label "com.docker.compose.volume=lab_data" $labVolume | Out-Null
    # Un volumen vacío se puebla con el contenido de la imagen en el primer montaje; luego se poda lo que no es versionado.
    $keepArgs = ($keep | ForEach-Object { "! -name '$_'" }) -join " "
    $cmd = "cd /workspace/data && find . -mindepth 1 -maxdepth 1 $keepArgs -exec rm -rf {} +"
    & docker run --rm -v "${labVolume}:/workspace/data" --entrypoint sh $labImage -c $cmd
    if ($LASTEXITCODE -ne 0) { throw "No se pudo preparar el volumen limpio del laboratorio." }
}

function Get-LabLeftovers {
    $out = & docker run --rm -v "${labVolume}:/workspace/data:ro" --entrypoint sh $labImage -c "ls /workspace/data | grep -E '^(sensor__|feedback__|feedback_ui|mlruns)' | wc -l" 2>$null
    return [int]($out | Select-Object -First 1)
}

function Test-Backends {
    $ok = $true
    if (-not (Wait-Http "http://127.0.0.1:$LabPort/openapi.json")) { Say "FALLA: laboratorio no responde"; $ok = $false } else { Say "OK laboratorio (:$LabPort)" }
    if (-not (Wait-Http "http://127.0.0.1:$ProducerPort/api/v2/sensors")) { Say "FALLA: productor no responde"; $ok = $false } else { Say "OK productor (:$ProducerPort)" }
    foreach ($case in @(@("pergamino-ensemble-demo", "2023-06-13"), @("melchor-romero-demo", "2024-10-20"))) {
        $url = "http://127.0.0.1:$ProducerPort/api/v2/sensors/$($case[0])/historical/$($case[1])/forecasts"
        try { $c = (Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 20).StatusCode } catch { $c = "error" }
        if ($c -eq 200) { Say "OK histórico $($case[0]) $($case[1])" } else { Say "FALLA histórico $($case[0]): $c"; $ok = $false }
    }
    return $ok
}

function Start-Frontend {
    $listener = Get-NetTCPConnection -LocalPort $UiPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listener) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        if ($proc.CommandLine -match "vite|node") { Stop-Process -Id $listener.OwningProcess -Force; Start-Sleep 1 }
        else { Fail "El puerto $UiPort lo usa otro proceso ($($proc.Name)); no se toca." }
    }
    $env:VITE_API_BASE_URL = "http://127.0.0.1:$LabPort"
    $env:VITE_PRODUCER_API_BASE_URL = "http://127.0.0.1:$ProducerPort"
    $frontend = Join-Path $repoRoot "frontend"
    if (-not (Test-Path (Join-Path $frontend "node_modules"))) { Fail "Faltan las dependencias del frontend: ejecutá 'npm ci' en frontend/." }
    Start-Process cmd -ArgumentList "/c", "cd /d `"$frontend`" && npx vite --port $UiPort --strictPort --host 127.0.0.1" -WindowStyle Hidden
    if (Wait-Http "http://127.0.0.1:$UiPort/" 60) { Say "OK frontend: http://127.0.0.1:$UiPort/" } else { Fail "El frontend no arrancó en :$UiPort." }
}

Test-DockerReady

switch ($Action) {
    "Init" {
        if ((Test-Path $baseline) -and -not $Force) { Fail "Ya existe una línea base en $RuntimeDir. Usá -Force para reemplazarla." }
        if (-not $ProducerDataSource -or -not (Test-Path $ProducerDataSource)) { Fail "Falta -ProducerDataSource (copia verificada de los datos del productor)." }
        if (-not $ProducerBundlesSource -or -not (Test-Path $ProducerBundlesSource)) { Fail "Falta -ProducerBundlesSource (bundles del ensamble)." }
        New-Item -ItemType Directory -Force $RuntimeDir | Out-Null
        foreach ($d in @($baseline, $work, $bundles)) { if (Test-Path $d) { Remove-Item $d -Recurse -Force } }
        Copy-Item $ProducerDataSource $baseline -Recurse -Force
        Copy-Item $ProducerDataSource $work -Recurse -Force
        Copy-Item $ProducerBundlesSource $bundles -Recurse -Force
        Get-Snapshot $baseline | Set-Content $manifest -Encoding utf8
        Say "Línea base del productor: $((Get-Content $manifest).Count) archivos con huella SHA-256."
        # Respaldo ÚNICO del volumen actual del laboratorio antes de que un reinicio lo reemplace.
        & docker volume inspect $labVolume *> $null
        if ($LASTEXITCODE -eq 0) {
            $backup = Join-Path $RuntimeDir ("lab-volume-backup-{0}.tgz" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
            & docker run --rm -v "${labVolume}:/data:ro" -v "$(Fwd $RuntimeDir):/backup" --entrypoint tar $labImage czf "/backup/$(Split-Path $backup -Leaf)" -C /data .
            if ($LASTEXITCODE -ne 0) { Fail "No se pudo respaldar el volumen del laboratorio; no se continúa." }
            Say "Respaldo del volumen actual del laboratorio: $backup"
        }
        @{ initialized = (Get-Date).ToString("o"); repo = $repoRoot; keepData = (Get-TrackedDataNames) } | ConvertTo-Json | Set-Content $statePath -Encoding utf8
        Say "Listo. Ejecutá: ./scripts/demo_reset.ps1 -Action Reset -StartFrontend"
    }
    "Status" {
        if (-not (Test-Path $baseline)) { Fail "No hay línea base. Ejecutá -Action Init primero." }
        $diff = Compare-Object (Get-Content $manifest) (Get-Snapshot $work)
        if ($diff) { Say "Datos del productor: DIFERENTES de la línea base"; $diff | ForEach-Object { "  {0} {1}" -f $_.SideIndicator, $_.InputObject } } else { Say "Datos del productor: idénticos a la línea base" }
        & docker volume inspect $labVolume *> $null
        if ($LASTEXITCODE -eq 0) { Say "Laboratorio: $(Get-LabLeftovers) archivo(s) de sesión/feedback/mlruns en el volumen (0 = limpio)" } else { Say "Laboratorio: el volumen no existe" }
    }
    "Reset" {
        if (-not (Test-Path $baseline)) { Fail "No hay línea base. Ejecutá -Action Init primero." }
        Set-ComposeEnv
        Say "Deteniendo backends de la demo ($project)..."
        Compose stop lab-backend producer-backend
        Compose rm -f lab-backend producer-backend | Out-Null
        Say "Restaurando datos del productor desde la línea base..."
        & robocopy $baseline $work /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { Fail "robocopy falló (código $LASTEXITCODE)." }
        $diff = Compare-Object (Get-Content $manifest) (Get-Snapshot $work)
        if ($diff) { Fail "La restauración no coincide con la línea base." } else { Say "OK productor idéntico a la línea base (SHA-256)." }
        Say "Recreando el volumen del laboratorio solo con datos versionados..."
        New-CleanLabVolume
        $left = Get-LabLeftovers
        if ($left -ne 0) { Fail "El volumen del laboratorio no quedó limpio ($left archivos)." } else { Say "OK laboratorio sin sesiones, feedback ni mlruns." }
        Say "Levantando backends..."
        Compose up -d --no-build lab-backend producer-backend
        if (-not (Test-Backends)) { Fail "La verificación posterior falló." }
        if ($StartFrontend) { Start-Frontend }
        Say "Demo reiniciada de cero. Laboratorio :$LabPort · Productor :$ProducerPort$(if ($StartFrontend) { " · UI http://127.0.0.1:$UiPort/" })"
    }
}
