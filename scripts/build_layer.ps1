# Builds the Lambda layer WITHOUT Docker (Windows PowerShell).
# Run from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\build_layer.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (Test-Path layer\build) { Remove-Item -Recurse -Force layer\build }
New-Item -ItemType Directory -Force layer\build\python | Out-Null
python -m pip install `
  --platform manylinux2014_x86_64 `
  --implementation cp `
  --python-version 3.12 `
  --only-binary=:all: `
  --target layer\build\python `
  -r layer\requirements.txt
Write-Host "Layer built in layer\build\python"
