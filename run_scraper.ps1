# PowerShell wrapper to run the job scraper and save daily CSV
# Usage: Open PowerShell, cd to this script's folder and run: .\run_scraper.ps1

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ProjectRoot

# Ensure .venv exists (optional)
if (-not (Test-Path "$ProjectRoot\.venv")) {
    Write-Host "Virtual environment not found. Creating .venv..."
    python -m venv .venv
}

# Activate venv
$activate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
    Write-Host "Activating virtual environment..."
    . $activate
} else {
    Write-Warning "Activation script not found; running with system Python."
}

# Build command
$date = Get-Date -Format yyyyMMdd
$output = "data\jobs_$date.csv"
$keywordsFile = Join-Path $ProjectRoot "keywords.txt"
$maxPages = 50
$usePlaywright = $true
$followDetails = $true

$cmd = "python scraper.py --output `"$output`" --max-pages $maxPages"
if ($usePlaywright) { $cmd += " --use-playwright" }
if ($followDetails) { $cmd += " --follow-details" }
if (Test-Path $keywordsFile) { $cmd += " --keywords-file `"$keywordsFile`"" } else { $cmd += " -k `"Summer 2026`"" }

Write-Host "Running: $cmd"
try {
    Invoke-Expression $cmd
} catch {
    Write-Error "Scraper failed: $_"
} finally {
    Pop-Location
}
