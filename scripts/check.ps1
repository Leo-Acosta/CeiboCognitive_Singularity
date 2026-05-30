$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Frontend = Join-Path $Root "frontend"

function Invoke-Checked {
  param(
    [string]$Label,
    [scriptblock]$Command
  )

  Write-Host "`n$Label" -ForegroundColor Cyan
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Label failed with exit code $LASTEXITCODE"
  }
}

Write-Host "== CEIBO release checks ==" -ForegroundColor Cyan

Push-Location $Root
Invoke-Checked "[1/3] Backend tests" { python -m pytest backend\tests }
Pop-Location

Push-Location $Frontend
Invoke-Checked "[2/3] Frontend production build" { npm run build }
Pop-Location

Write-Host "`n[3/3] Configuration files" -ForegroundColor Cyan
$RequiredFiles = @(
  ".env.example",
  "README.md",
  "docker-compose.yml",
  "docs\release-readiness.md",
  "docs\security.md",
  "docs\architecture.md"
)

foreach ($File in $RequiredFiles) {
  $Path = Join-Path $Root $File
  if (-not (Test-Path $Path)) {
    throw "Missing required release file: $File"
  }
  Write-Host "ok $File"
}

Write-Host "`nAll release checks passed." -ForegroundColor Green
