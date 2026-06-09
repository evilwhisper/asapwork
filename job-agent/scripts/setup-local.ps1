# Job Agent — Local Native Setup (Windows PowerShell)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "==> Job Agent — Local Native Setup (Windows)" -ForegroundColor Cyan

Write-Host "==> Installing Python deps..."
pip install -r requirements.txt

Write-Host "==> Installing Playwright Chromium..."
playwright install chromium

Write-Host "==> Installing Node deps..."
npm install
Set-Location frontend
npm install
Set-Location ..

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env — ENCRYPTION_KEY will be auto-generated on first run."
}

Write-Host ""
Write-Host "Setup complete. Start the app with:" -ForegroundColor Green
Write-Host "  npm run dev" -ForegroundColor Yellow
