# Run from the repository root after cloning.
$ErrorActionPreference = "Stop"

$dirs = @(
    ".ai-pipeline\001_planner",
    ".ai-pipeline\002_contract_analyst",
    ".ai-pipeline\003_builder",
    ".ai-pipeline\004_tester",
    ".ai-pipeline\005_reviewer",
    ".ai-pipeline\006_security_reviewer",
    "apps\backend",
    "apps\frontend",
    "docs\architecture",
    "docs\contracts",
    "docs\decisions",
    "docs\sponsor-questions",
    "docs\test-plan",
    "mocks\acra",
    "mocks\goldtier",
    "tests\contract",
    "tests\integration",
    "tests\e2e",
    "private\sponsor-artifacts"
)

foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$keepDirs = @(
    "apps\backend",
    "apps\frontend",
    "mocks\acra",
    "mocks\goldtier",
    "tests\contract",
    "tests\integration",
    "tests\e2e"
)

foreach ($dir in $keepDirs) {
    $keep = Join-Path $dir ".gitkeep"
    if (-not (Test-Path $keep)) {
        New-Item -ItemType File -Path $keep | Out-Null
    }
}

Write-Host "FYP folder structure created."
Write-Host "Put confidential sponsor files in: private\sponsor-artifacts\"
Write-Host "Do NOT remove private/ from .gitignore."
