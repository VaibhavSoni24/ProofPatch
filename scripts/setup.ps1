# ProofPatch Setup Script for PowerShell
Write-Host "Setting up ProofPatch environment..." -ForegroundColor Cyan

# 1. Virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
}

# 2. Activate and install backend
Write-Host "Installing backend in editable mode..." -ForegroundColor Yellow
& .venv\Scripts\pip.exe install -e backend

# 3. Setup frontend
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location frontend
npm install
Set-Location ..

Write-Host "Setup complete! Run ./scripts/check.ps1 to verify the environment." -ForegroundColor Green
