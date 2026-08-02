$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env. The app will use NASA DEMO_KEY until you add a rotated personal key." -ForegroundColor Yellow
}

python -m nasa_data_hub health
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m nasa_data_hub serve --open
