# PowerShell script to run Mini GCS backend locally on Windows

Write-Host "Setting up Python virtual environment..." -ForegroundColor Green

# Create venv if it doesn't exist
if (!(Test-Path "venv")) {
    python -m venv venv
    Write-Host "Virtual environment created" -ForegroundColor Green
}

# Activate venv
.\venv\Scripts\Activate.ps1

# Install requirements
Write-Host "Installing requirements..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To run the server:" -ForegroundColor Yellow
Write-Host '  $env:SIM_MODE="SIM"' -ForegroundColor Cyan
Write-Host '  $env:TELEMETRY_RATE="5"' -ForegroundColor Cyan
Write-Host "  python -m app.server" -ForegroundColor Cyan
Write-Host ""
