$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& docker compose `
  -f docker-compose.yml `
  -f docker-compose.investor-demo.yml `
  down
