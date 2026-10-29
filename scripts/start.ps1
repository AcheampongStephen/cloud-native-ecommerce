$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path '.venv/Scripts/python.exe')) { throw 'Create .venv and install requirements first; see README.md' }
& ./.venv/Scripts/python.exe -m commerce.manage init
if ($LASTEXITCODE -ne 0) { throw 'Configuration failed' }
& ./.venv/Scripts/python.exe -m commerce.manage migrate --all
if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
& ./.venv/Scripts/python.exe -m commerce.manage seed --all
if ($LASTEXITCODE -ne 0) { throw 'Seeding failed' }
& ./.venv/Scripts/python.exe -m scripts.dev
