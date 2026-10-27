# Start SAMANVAY (backend + built frontend) at http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\frontend\app"
if (-not (Test-Path dist)) { npm install; npm run build }
Set-Location "$root\backend"
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created backend\.env from the example - set SECRET_KEY and PII_ENCRYPTION_KEY." }
if (-not (Test-Path data\samanvay.db)) { .\.venv\Scripts\python -m app.cli seed }
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
