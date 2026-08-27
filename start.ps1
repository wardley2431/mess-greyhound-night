$ErrorActionPreference = "Stop"

$localPython = Get-Command python -ErrorAction SilentlyContinue
if ($localPython) {
    $env:RACE_HOST = if ($env:RACE_HOST) { $env:RACE_HOST } else { "127.0.0.1" }
    $env:RACE_PORT = if ($env:RACE_PORT) { $env:RACE_PORT } else { "8000" }
    & $localPython.Source "$PSScriptRoot\server.py"
    exit $LASTEXITCODE
}

$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path $bundledPython) {
    $env:RACE_HOST = if ($env:RACE_HOST) { $env:RACE_HOST } else { "127.0.0.1" }
    $env:RACE_PORT = if ($env:RACE_PORT) { $env:RACE_PORT } else { "8000" }
    & $bundledPython "$PSScriptRoot\server.py"
    exit $LASTEXITCODE
}

Write-Error "Python was not found. Install Python 3 and run this script again."
