param(
    [Parameter(Mandatory = $true)][string]$SourceDataDir,
    [Parameter(Mandatory = $true)][string]$DemoDataDir
)

$source = (Resolve-Path -LiteralPath $SourceDataDir).Path
$destination = [IO.Path]::GetFullPath($DemoDataDir)
$demoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\.demo-defense-data'))
if (-not $destination.StartsWith($demoRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "El destino demo debe estar dentro de $demoRoot."
}
if ((Test-Path -LiteralPath $demoRoot) -and
    ((Get-Item -LiteralPath $demoRoot).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'El directorio demo no puede ser un enlace o punto de reanálisis.'
}
if ($destination.Equals($source, [StringComparison]::OrdinalIgnoreCase) -or
    $destination.StartsWith($source + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'El almacenamiento demo debe estar separado de los datos originales.'
}
if (Test-Path -LiteralPath $destination) { throw "El destino ya existe: $destination. Usá otro directorio para conservar el anterior." }
$sensor = 'pergamino-ensemble-demo'
$reading = Join-Path $source "sensor__$sensor.parquet"
$emission = Join-Path $source "ui_metadata/operational_v2__$sensor.json"
if (-not (Test-Path -LiteralPath $reading) -or -not (Test-Path -LiteralPath $emission)) {
    throw 'Faltan las lecturas o emisiones persistidas del recorrido Pergamino.'
}
$expectedReadingSha256 = 'F6F9E19AE19C0835D6DA57CFDA490DE4E81D84F0657ED0118D609F3A9DA3F98C'
$expectedEmissionSha256 = 'FCD7AC529B6CE300905EBA805E4655AB8BAFAF1E63CBE7B2E7316D37BF535DCD'
if ((Get-FileHash -LiteralPath $reading -Algorithm SHA256).Hash -ne $expectedReadingSha256 -or
    (Get-FileHash -LiteralPath $emission -Algorithm SHA256).Hash -ne $expectedEmissionSha256) {
    throw 'Los hashes de las lecturas o emisiones no coinciden con el recorrido persistido autorizado.'
}
New-Item -ItemType Directory -Path (Join-Path $destination 'ui_metadata') -Force | Out-Null
Copy-Item -LiteralPath $reading -Destination $destination
Copy-Item -LiteralPath $emission -Destination (Join-Path $destination 'ui_metadata')
Write-Output "Copia demo aislada: $destination"
Write-Output 'Se copiaron lecturas y emisiones ya persistidas. Las revisiones históricas se crearán solo en el destino.'
