param([string]$ImageTag = "experiment-v4-scientific-closure")
$ErrorActionPreference = "Stop"
$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$CommitIdentity = git -C $RepoPath rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $CommitIdentity -notmatch "^[0-9a-f]{40,64}$") {
    throw "Cannot resolve commit"
}
$WorkStatus = git -C $RepoPath status --porcelain --untracked-files=all
if ($LASTEXITCODE -ne 0 -or $WorkStatus) { throw "Build requires clean checkout" }
$IdentityPayload = @{
    schema_version = "controlled_daily_v4_build_identity.v1"
    commit = $CommitIdentity
    dirty = $false
    captured_at_utc = [DateTime]::UtcNow.ToString("o")
} | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $RepoPath ".build_identity.json"),
    $IdentityPayload, [Text.UTF8Encoding]::new($false))
docker build -f (Join-Path $PSScriptRoot "Dockerfile") -t $ImageTag $RepoPath
if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }
docker image inspect --format "{{.Id}}" $ImageTag
if ($LASTEXITCODE -ne 0) { throw "Image identity unavailable" }
