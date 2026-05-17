param(
  [switch]$SkipInstall,
  [switch]$UseCi,
  [switch]$SkipBuild,
  [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Find-WebRoot {
  $current = (Get-Location).Path
  $candidates = @(
    $current,
    (Join-Path $current "web")
  )

  foreach ($candidate in $candidates) {
    if ((Test-Path (Join-Path $candidate "package.json")) -and (Test-Path (Join-Path $candidate "src"))) {
      return (Resolve-Path $candidate).Path
    }
  }

  throw "Nem talalom a UI project rootot. Futtasd a scriptet a web mappabol, vagy abbol a mappabol, amelyik alatt van egy web/package.json."
}

function Invoke-Npm {
  param([string[]]$Arguments)

  Write-Host "`n> npm $($Arguments -join ' ')" -ForegroundColor Cyan
  & npm @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "npm $($Arguments -join ' ') sikertelen volt. Exit code: $LASTEXITCODE"
  }
}

$webRoot = Find-WebRoot
Write-Host "UI project root: $webRoot" -ForegroundColor Green
Set-Location $webRoot

$requiredP2Files = @(
  "src/features/equipment-planner/hooks/useModalFocusTrap.ts"
)

foreach ($relativePath in $requiredP2Files) {
  $fullPath = Join-Path $webRoot $relativePath
  if (-not (Test-Path $fullPath)) {
    Write-Warning "Nem talalom ezt a P2 fajlt: $relativePath. Lehet, hogy a P2 zip tartalma meg nincs bemasolva."
  }
}

$packageJsonPath = Join-Path $webRoot "package.json"
$packageJson = Get-Content $packageJsonPath -Raw | ConvertFrom-Json
if (-not ($packageJson.scripts.PSObject.Properties.Name -contains "typecheck")) {
  Write-Warning "A package.json-ban nincs typecheck script. Lehet, hogy a P2 package.json meg nincs alkalmazva."
}

$filesToDelete = @(
  "src/features/equipment-planner/components/item-editor/DefenceBreakdownPanel.tsx",
  "src/features/equipment-planner/components/item-editor/ItemPropertySummary.tsx",
  "tsconfig.tsbuildinfo"
)

Write-Host "`nRegi / generated fajlok torlese..." -ForegroundColor Cyan
foreach ($relativePath in $filesToDelete) {
  $fullPath = Join-Path $webRoot $relativePath
  if (Test-Path $fullPath) {
    if ($WhatIfOnly) {
      Write-Host "[what-if] Torolnem: $relativePath"
    } else {
      Remove-Item $fullPath -Force
      Write-Host "Torolve: $relativePath"
    }
  } else {
    Write-Host "Nincs mit torolni: $relativePath"
  }
}

if ($WhatIfOnly) {
  Write-Host "`nWhatIfOnly mod: npm parancsokat nem futtatok." -ForegroundColor Yellow
  exit 0
}

if (-not $SkipInstall) {
  if ($UseCi) {
    Invoke-Npm @("ci")
  } else {
    Invoke-Npm @("install")
  }
} else {
  Write-Host "`nSkipInstall megadva, npm install/ci kihagyva." -ForegroundColor Yellow
}

Invoke-Npm @("run", "typecheck")
Invoke-Npm @("run", "test:golden")
Invoke-Npm @("run", "audit:css")

if (-not $SkipBuild) {
  Invoke-Npm @("run", "build")
} else {
  Write-Host "`nSkipBuild megadva, npm run build kihagyva." -ForegroundColor Yellow
}

Write-Host "`nKeszen van: cleanup + ellenorzes sikeres." -ForegroundColor Green
