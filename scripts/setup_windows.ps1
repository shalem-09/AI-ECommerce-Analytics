$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Error 'Virtual environment not found. Create it with: python -m venv .venv'
    exit 1
}
& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $root 'requirements.txt')
Write-Host 'Environment ready.'
