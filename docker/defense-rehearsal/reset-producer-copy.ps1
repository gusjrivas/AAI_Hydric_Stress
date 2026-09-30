<#
.SYNOPSIS
    Regenera la copia de trabajo de los artefactos del productor (Pergamino +
    Melchor Romero) a partir del paquete verificado, para el ensayo Docker.

.DESCRIPTION
    Verifica la ORIGEN contra `producer-package.sha256` (hashes fijados en el
    repositorio) ANTES de copiar, recrea el destino desde cero (sin archivos
    `.lock` ni `historical_feedback`) y vuelve a verificar la copia. Nunca
    modifica el origen, nunca entrena ni regenera modelos. Si algo no coincide,
    aborta sin dejar una copia a medias como "verificada".

    Antes de ejecutarlo, detené el servicio `producer-backend` (escribe en el
    destino) y volvé a levantarlo después:

      docker compose -f docker/defense-rehearsal/compose.yml stop producer-backend
      ./docker/defense-rehearsal/reset-producer-copy.ps1 -SourceDataDir <..> -SourceBundleRoot <..> -Destination <dir>
      docker compose -f docker/defense-rehearsal/compose.yml up -d producer-backend

    Destino: <Destination>/producer-data y <Destination>/producer-bundles
    (las rutas que espera REHEARSAL_PRODUCER_DATA / REHEARSAL_PRODUCER_BUNDLES).

.PARAMETER SourceDataDir
    Directorio con `sensor__*.parquet` y `ui_metadata/` del paquete verificado.
.PARAMETER SourceBundleRoot
    Directorio raíz de bundles (contiene `pergamino-ensemble-demo/` y `melchor-romero-demo/`).
.PARAMETER Destination
    Directorio donde se (re)crean `producer-data` y `producer-bundles`.
#>
param(
    [Parameter(Mandatory = $true)][string]$SourceDataDir,
    [Parameter(Mandatory = $true)][string]$SourceBundleRoot,
    [Parameter(Mandatory = $true)][string]$Destination
)

$ErrorActionPreference = 'Stop'
$manifestPath = Join-Path $PSScriptRoot 'producer-package.sha256'

function Read-Manifest {
    Get-Content -LiteralPath $manifestPath | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object {
        $hash, $path = $_ -split '\s+', 2
        [pscustomobject]@{ Hash = $hash.ToLowerInvariant(); Path = $path.Trim() }
    }
}

function Test-Tree([string]$dataDir, [string]$bundleDir, [string]$label) {
    $errors = @()
    $expected = Read-Manifest
    foreach ($entry in $expected) {
        $root = if ($entry.Path.StartsWith('data/')) { $dataDir } else { $bundleDir }
        $relative = $entry.Path -replace '^(data|bundles)/', ''
        $file = Join-Path $root $relative
        if (-not (Test-Path -LiteralPath $file)) { $errors += "falta: $($entry.Path)"; continue }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $entry.Hash) { $errors += "hash distinto: $($entry.Path)" }
    }
    # Archivos que no pertenecen al paquete (p. ej. historical_feedback o emisiones nuevas).
    $known = @{}
    foreach ($e in $expected) { $known[$e.Path] = $true }
    foreach ($pair in @(@($dataDir, 'data'), @($bundleDir, 'bundles'))) {
        $base = (Resolve-Path -LiteralPath $pair[0]).Path
        Get-ChildItem -LiteralPath $base -Recurse -File | Where-Object { $_.Extension -ne '.lock' } | ForEach-Object {
            $rel = $pair[1] + '/' + ($_.FullName.Substring($base.Length + 1) -replace '\\', '/')
            if (-not $known.ContainsKey($rel)) { $errors += "archivo ajeno al paquete: $rel" }
        }
    }
    if ($errors.Count -gt 0) {
        $errors | Select-Object -First 15 | ForEach-Object { Write-Host "  $_" }
        throw "Verificación de $label fallida ($($errors.Count) discrepancia(s))."
    }
    Write-Host "OK  $label coincide con producer-package.sha256 ($($expected.Count) archivos)."
}

foreach ($d in @($SourceDataDir, $SourceBundleRoot)) {
    if (-not (Test-Path -LiteralPath $d -PathType Container)) { throw "No existe el directorio origen: $d" }
}

Test-Tree $SourceDataDir $SourceBundleRoot 'el ORIGEN'

$destData = Join-Path $Destination 'producer-data'
$destBundles = Join-Path $Destination 'producer-bundles'
foreach ($d in @($destData, $destBundles)) {
    if (Test-Path -LiteralPath $d) { Remove-Item -LiteralPath $d -Recurse -Force }
}
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
Copy-Item -LiteralPath $SourceDataDir -Destination $destData -Recurse
Copy-Item -LiteralPath $SourceBundleRoot -Destination $destBundles -Recurse
Get-ChildItem -LiteralPath $Destination -Recurse -Force -File -Filter '*.lock' | Remove-Item -Force
Get-ChildItem -LiteralPath $destData -Recurse -Directory -Filter 'historical_feedback' | Remove-Item -Recurse -Force

Test-Tree $destData $destBundles 'la COPIA'
Write-Host "Copia regenerada en $Destination. Levantá de nuevo producer-backend."
