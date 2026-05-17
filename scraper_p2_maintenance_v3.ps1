<#
PoE2DB scraper P2 maintenance helper.

What it does:
- Detects the scraper root whether you run it from repo root or the scraper folder.
- Archives Python/test caches into .maintenance_backup/<timestamp> when -Apply is used.
- Keeps generated payload JSON files by default, because some regression tests still read scraper/out/poe2db_poc_ui.json.
- Keeps source data and HTTP cache by default, because those are useful for offline/dev builds.
- Runs compile/tests/help checks.
- Optionally rebuilds the payload.

Common usage:
  # Preview cleanup only, then run checks
  .\scraper_p2_maintenance.ps1

  # Archive Python/test caches and run checks, while keeping existing generated payloads
  .\scraper_p2_maintenance.ps1 -Apply

  # Restore generated payloads from the latest maintenance backup, then run checks
  .\scraper_p2_maintenance.ps1 -Apply -RestoreLatestGeneratedOutput

  # Archive Python/test caches, run checks, then rebuild full dev payload
  .\scraper_p2_maintenance.ps1 -Apply -RunBuild

  # Rebuild smaller UI payload
  .\scraper_p2_maintenance.ps1 -Apply -RunBuild -SlimUiPayload

  # More aggressive cleanup, still archived not permanently deleted
  .\scraper_p2_maintenance.ps1 -Apply -RemoveLegacyPoc -ArchiveSnapshots

  # Only use this if you want a fresh remote scrape; it may be slow.
  .\scraper_p2_maintenance.ps1 -Apply -ClearHttpCache -RunBuild -ForceRefresh
#>

param(
    [string]$ProjectRoot = "",
    [string]$Python = "python",
    [switch]$Apply,
    [switch]$InstallRequirements,
    [switch]$RunBuild,
    [switch]$StrictBuild,
    [switch]$SlimUiPayload,
    [switch]$CopyWeb,
    [switch]$ForceRefresh,
    [switch]$RemoveLegacyPoc,
    [switch]$ArchiveGeneratedOutput,
    [switch]$RestoreLatestGeneratedOutput,
    [switch]$ArchiveSnapshots,
    [switch]$ClearHttpCache,
    [switch]$ClearModifierHtmlCache,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-ScraperRoot {
    param([string]$InputRoot)

    if ([string]::IsNullOrWhiteSpace($InputRoot)) {
        $InputRoot = (Get-Location).Path
    }

    $candidate = (Resolve-Path -LiteralPath $InputRoot).Path

    if ((Test-Path -LiteralPath (Join-Path $candidate "run_poc.py")) -and
        (Test-Path -LiteralPath (Join-Path $candidate "poe2db_scraper"))) {
        return $candidate
    }

    $nested = Join-Path $candidate "scraper"
    if ((Test-Path -LiteralPath (Join-Path $nested "run_poc.py")) -and
        (Test-Path -LiteralPath (Join-Path $nested "poe2db_scraper"))) {
        return (Resolve-Path -LiteralPath $nested).Path
    }

    throw "Could not find scraper root. Run from repo root or scraper folder, or pass -ProjectRoot <path>."
}

function Get-RelativePathSafe {
    param(
        [string]$BasePath,
        [string]$FullPath
    )

    # PowerShell 5.1 / older .NET Framework does not have
    # [System.IO.Path]::GetRelativePath, so use it only when available.
    $hasGetRelativePath = [System.IO.Path].GetMethods() |
        Where-Object { $_.Name -eq "GetRelativePath" -and $_.GetParameters().Count -eq 2 } |
        Select-Object -First 1

    if ($null -ne $hasGetRelativePath) {
        return [System.IO.Path]::GetRelativePath($BasePath, $FullPath)
    }

    $resolvedBase = (Resolve-Path -LiteralPath $BasePath).Path
    $resolvedFull = (Resolve-Path -LiteralPath $FullPath).Path

    $directorySeparator = [System.IO.Path]::DirectorySeparatorChar
    $altDirectorySeparator = [System.IO.Path]::AltDirectorySeparatorChar

    if ((-not $resolvedBase.EndsWith($directorySeparator)) -and
        (-not $resolvedBase.EndsWith($altDirectorySeparator))) {
        $resolvedBase = $resolvedBase + $directorySeparator
    }

    $baseUri = New-Object System.Uri($resolvedBase)
    $fullUri = New-Object System.Uri($resolvedFull)
    $relativeUri = $baseUri.MakeRelativeUri($fullUri)

    $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
    return ($relativePath -replace '/', $directorySeparator)
}

function Archive-Path {
    param(
        [string]$Path,
        [string]$RepoRoot,
        [string]$BackupRoot,
        [string]$Reason
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $rel = Get-RelativePathSafe -BasePath $RepoRoot -FullPath $resolved
    $dest = Join-Path $BackupRoot $rel

    Write-Host ("  - {0} ({1})" -f $rel, $Reason)

    if (-not $Apply) {
        return
    }

    $destParent = Split-Path -Parent $dest
    New-Item -ItemType Directory -Force -Path $destParent | Out-Null

    if (Test-Path -LiteralPath $dest) {
        $leaf = Split-Path -Leaf $dest
        $parent = Split-Path -Parent $dest
        $dest = Join-Path $parent ("{0}.{1}" -f $leaf, (Get-Random))
    }

    Move-Item -LiteralPath $resolved -Destination $dest
}


function Restore-PathsFromLatestBackup {
    param(
        [string[]]$RelativePaths,
        [string]$RepoRoot,
        [string]$BackupParent
    )

    if (-not (Test-Path -LiteralPath $BackupParent)) {
        Write-Host "No maintenance backup folder found; nothing to restore."
        return
    }

    $latestBackup = Get-ChildItem -LiteralPath $BackupParent -Directory -Force |
        Sort-Object Name -Descending |
        Select-Object -First 1

    if ($null -eq $latestBackup) {
        Write-Host "No maintenance backup folder found; nothing to restore."
        return
    }

    Write-Host ""
    Write-Host ("Restoring generated payloads from latest backup: {0}" -f $latestBackup.FullName)

    foreach ($rel in $RelativePaths) {
        $source = Join-Path $latestBackup.FullName $rel
        $destination = Join-Path $RepoRoot $rel

        if (-not (Test-Path -LiteralPath $source)) {
            continue
        }

        $destinationParent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
        Write-Host ("  restored {0}" -f $rel)
    }
}


function Invoke-Step {
    param(
        [string]$Title,
        [string[]]$Command
    )

    Write-Host ""
    Write-Host ("==> {0}" -f $Title)
    Write-Host ("    {0}" -f ($Command -join " "))

    $exe = $Command[0]
    $args = @()
    if ($Command.Count -gt 1) {
        $args = $Command[1..($Command.Count - 1)]
    }

    & $exe @args
    $exitCode = $LASTEXITCODE
    if ($null -ne $exitCode -and $exitCode -ne 0) {
        throw ("Step failed with exit code {0}: {1}" -f $exitCode, $Title)
    }
}

$ScraperRoot = Resolve-ScraperRoot -InputRoot $ProjectRoot
$RepoRoot = Split-Path -Parent $ScraperRoot
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupRoot = Join-Path $ScraperRoot (Join-Path ".maintenance_backup" $Timestamp)

Write-Host "Scraper root: $ScraperRoot"
Write-Host "Repo root:    $RepoRoot"
if ($Apply) {
    Write-Host "Cleanup mode: APPLY. Matching files will be archived to: $BackupRoot"
} else {
    Write-Host "Cleanup mode: DRY RUN. Add -Apply to archive matching files."
}

Write-Host ""
Write-Host "Cleanup candidates:"

# Generated output files. These are intentionally kept by default because some
# regression tests still read scraper/out/poe2db_poc_ui.json directly.
$generatedOutFiles = @(
    "scraper\out\poe2db_poc_ui.json",
    "scraper\out\poe2db_poc_debug.json",
    "scraper\out\poe2db_poc_schema.json",
    "scraper\out\poe2db_payload_health_report.json",
    "scraper\out\poe2db_snapshot_update_report.json",
    "scraper\out\poe2_ui_asset_import_report.json",
    "scraper\out\poe2db_poc_diagnostics.json"
)

# Legacy web copies generated by old/default flows. Only exact generated JSON filenames are targeted.
$webGeneratedFiles = @(
    "web\public\data\poe2db_poc_ui.json",
    "web\public\data\poe2db_payload_health_report.json",
    "web\public\data\poe2db_poc_diagnostics.json",
    "web\src\data\poe2db_poc_ui.json"
)

if ($RestoreLatestGeneratedOutput) {
    Restore-PathsFromLatestBackup -RelativePaths ($generatedOutFiles + $webGeneratedFiles) -RepoRoot $RepoRoot -BackupParent (Join-Path $ScraperRoot ".maintenance_backup")
}

if ($ArchiveGeneratedOutput) {
    foreach ($rel in $generatedOutFiles) {
        Archive-Path -Path (Join-Path $RepoRoot $rel) -RepoRoot $RepoRoot -BackupRoot $BackupRoot -Reason "generated output"
    }
    foreach ($rel in $webGeneratedFiles) {
        Archive-Path -Path (Join-Path $RepoRoot $rel) -RepoRoot $RepoRoot -BackupRoot $BackupRoot -Reason "generated web copy"
    }
} else {
    foreach ($rel in $generatedOutFiles) {
        $path = Join-Path $RepoRoot $rel
        if (Test-Path -LiteralPath $path) {
            Write-Host ("  - {0} (generated output; kept by default, add -ArchiveGeneratedOutput to archive)" -f $rel)
        }
    }
    foreach ($rel in $webGeneratedFiles) {
        $path = Join-Path $RepoRoot $rel
        if (Test-Path -LiteralPath $path) {
            Write-Host ("  - {0} (generated web copy; kept by default, add -ArchiveGeneratedOutput to archive)" -f $rel)
        }
    }
}

# Python/test caches.
$cacheDirs = @()
$cacheDirs += Get-ChildItem -LiteralPath $ScraperRoot -Directory -Recurse -Force -Filter "__pycache__" -ErrorAction SilentlyContinue
$cacheDirs += Get-ChildItem -LiteralPath $ScraperRoot -Directory -Recurse -Force -Filter ".pytest_cache" -ErrorAction SilentlyContinue
foreach ($dir in $cacheDirs | Sort-Object FullName -Unique) {
    if ($dir.FullName -like (Join-Path $ScraperRoot ".maintenance_backup") + "*") {
        continue
    }
    Archive-Path -Path $dir.FullName -RepoRoot $RepoRoot -BackupRoot $BackupRoot -Reason "python/test cache"
}

$miscCachePaths = @(
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    "htmlcov"
)
foreach ($rel in $miscCachePaths) {
    Archive-Path -Path (Join-Path $ScraperRoot $rel) -RepoRoot $RepoRoot -BackupRoot $BackupRoot -Reason "tool cache/report"
}

# Optional legacy/archive candidates.
if ($RemoveLegacyPoc) {
    Archive-Path -Path (Join-Path $ScraperRoot "legacy_poc") -RepoRoot $RepoRoot -BackupRoot $BackupRoot -Reason "legacy POC archive"
} else {
    if (Test-Path -LiteralPath (Join-Path $ScraperRoot "legacy_poc")) {
        Write-Host "  - legacy_poc (legacy POC; kept by default, add -RemoveLegacyPoc to archive it)"
    }
}

if ($ArchiveSnapshots) {
    Archive-Path -Path (Join-Path $ScraperRoot "data\snapshots") -RepoRoot $RepoRoot -BackupRoot $BackupRoot -Reason "old generated snapshots"
} else {
    if (Test-Path -LiteralPath (Join-Path $ScraperRoot "data\snapshots")) {
        Write-Host "  - data\snapshots (kept by default; add -ArchiveSnapshots to archive old generated snapshots)"
    }
}

if ($ClearHttpCache) {
    Archive-Path -Path (Join-Path $ScraperRoot ".cache\poe2db") -RepoRoot $RepoRoot -BackupRoot $BackupRoot -Reason "HTTP cache"
} else {
    if (Test-Path -LiteralPath (Join-Path $ScraperRoot ".cache\poe2db")) {
        Write-Host "  - .cache\poe2db (kept by default; add -ClearHttpCache only for a fresh remote scrape)"
    }
}

if ($ClearModifierHtmlCache) {
    Archive-Path -Path (Join-Path $ScraperRoot "data\modifiers_calc_full") -RepoRoot $RepoRoot -BackupRoot $BackupRoot -Reason "modifier HTML cache"
} else {
    if (Test-Path -LiteralPath (Join-Path $ScraperRoot "data\modifiers_calc_full")) {
        Write-Host "  - data\modifiers_calc_full (kept by default; add -ClearModifierHtmlCache if you want to refresh fixtures)"
    }
}

if ($Apply) {
    New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
    Write-Host ""
    Write-Host "Archived cleanup candidates to $BackupRoot"
} else {
    Write-Host ""
    Write-Host "No files were moved. Re-run with -Apply to archive cleanup candidates."
}

Push-Location $ScraperRoot
try {
    if ($InstallRequirements) {
        Invoke-Step -Title "Install Python requirements" -Command @($Python, "-m", "pip", "install", "-r", "requirements.txt")
    }

    Invoke-Step -Title "Show Python version" -Command @($Python, "--version")
    Invoke-Step -Title "Compile Python modules" -Command @($Python, "-m", "compileall", "-q", "poe2db_scraper", "run_poc.py")
    Invoke-Step -Title "Check CLI help" -Command @($Python, "run_poc.py", "--help")

    if (-not $SkipTests) {
        Invoke-Step -Title "Run tests" -Command @($Python, "-m", "pytest", "tests", "-q")
    } else {
        Write-Host ""
        Write-Host "Skipping tests because -SkipTests was passed."
    }

    if ($RunBuild) {
        $mode = "dev"
        if ($StrictBuild) {
            $mode = "strict"
        }

        $buildCommand = @($Python, "run_poc.py", "--build-mode", $mode, "--debug", "--write-schema")
        if ($SlimUiPayload) {
            $buildCommand += "--slim-ui-payload"
        }
        if ($CopyWeb) {
            $buildCommand += "--copy-web"
        }
        if ($ForceRefresh) {
            $buildCommand += "--force-refresh"
        }

        Invoke-Step -Title "Build payload" -Command $buildCommand
    } else {
        Write-Host ""
        Write-Host "Skipping payload build. Add -RunBuild to generate out\poe2db_poc_ui.json and diagnostics."
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done. If cleanup was applied, backups are under: $BackupRoot"
