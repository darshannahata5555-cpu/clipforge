$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$composeArgs = @(
  "-f", "docker-compose.yml",
  "-f", "docker-compose.investor-demo.yml"
)

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example."
  Write-Host "Fill in ANTHROPIC_API_KEY and ASSEMBLYAI_API_KEY, then rerun this script."
  exit 1
}

$envValues = @{}
foreach ($line in Get-Content ".env") {
  if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith("#")) {
    continue
  }

  $parts = $line -split "=", 2
  if ($parts.Count -eq 2) {
    $envValues[$parts[0].Trim()] = $parts[1].Trim()
  }
}

$missing = @()
foreach ($key in @("ANTHROPIC_API_KEY", "ASSEMBLYAI_API_KEY")) {
  $value = $envValues[$key]
  if ([string]::IsNullOrWhiteSpace($value) -or $value -eq "..." -or $value -like "*...*") {
    $missing += $key
  }
}

if ($missing.Count -gt 0) {
  Write-Host "Missing required values in .env:" -ForegroundColor Red
  foreach ($key in $missing) {
    Write-Host " - $key"
  }
  exit 1
}

Write-Host "Starting investor demo stack..."
& docker compose @composeArgs up --build -d

Write-Host ""
Write-Host "Public URL will appear in the cloudflared logs." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop following logs. The demo will keep running until you stop it." -ForegroundColor Cyan
Write-Host ""

& docker compose @composeArgs logs -f cloudflared
