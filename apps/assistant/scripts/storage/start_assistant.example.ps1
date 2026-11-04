# B0 (D-108/D-109) example launcher: the AI Assistant on a persistent data root, port 8100.
# Copy it to an owner-only folder outside the repository and run it with Windows PowerShell 5.1
# ("powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File <copy>"), where an empty
# $env:X = '' removes the variable as the reviewed local launchers expect.
# - Stores come from AI_ASSISTANT_DATA_DIR with RELATIVE store settings set explicitly, so
#   neither .env nor an inherited absolute value can redirect them.
# - Pass -RepoRoot for a copy outside the repository (the default only works from
#   scripts\storage). The loaded code must support the data root (D-108); every store
#   must already exist (nothing is created here); logs go next to the data root.
# - The Anthropic key comes only from <repo>\apps\assistant\.env (an inherited one is dropped)
#   and must belong to the workspace named by -WorkspaceId (server pin).
# Makes NO paid call by itself.
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^wrkspc_[A-Za-z0-9]+$')]
    [string]$WorkspaceId,
    [string]$RepoRoot = '',
    [string]$DataRoot = (Join-Path $env:LOCALAPPDATA 'DataDividendsCLM\assistant'),
    [string]$LogDir = '',
    [switch]$OpenRouterOwnerAttests,
    [switch]$StatusOnly
)
$ErrorActionPreference = 'Stop'
# ValidatePattern ignores case; the server pin is case-sensitive, so check it exactly here.
if ($WorkspaceId -cnotmatch '^wrkspc_[A-Za-z0-9]+$') { throw 'WorkspaceId must start with lower-case wrkspc_.' }
# The empty settings below rely on Windows PowerShell 5.1, where $env:X = '' removes X.
if ($PSVersionTable.PSVersion.Major -ne 5) { throw 'Run this launcher with Windows PowerShell 5.1 (powershell.exe).' }
# Windows PowerShell 5.1 leaves $PSScriptRoot empty in parameter defaults, so default it here.
if (-not $RepoRoot) { $RepoRoot = Join-Path $PSScriptRoot '..\..\..\..' }
$repo = (Resolve-Path -LiteralPath $RepoRoot).Path
$root = (Resolve-Path -LiteralPath $DataRoot).Path
if (-not (Test-Path -LiteralPath "$repo\apps\assistant\ai_assistant\__init__.py")) {
    throw "Not a repository root: $repo"
}
if (-not $LogDir) { $LogDir = Join-Path (Split-Path -Parent $root) 'logs' }
$py = "$repo\.venv\Scripts\python.exe"
$check = "$repo\apps\assistant\scripts\storage\check_data_root.py"

foreach ($p in "$root\models\model_admin.sqlite3", "$root\budget\anthropic_fyp_ledger.sqlite3",
               "$root\budget\ledger.sqlite3", "$root\models\profiles.json",
               "$root\knowledge\knowledge.sqlite3", "$root\knowledge\chroma\chroma.sqlite3") {
    if (-not (Test-Path -LiteralPath $p)) { throw "Missing store (never created by this launcher): $p" }
}

# Baseline: local Ollama (may be off - the chat then uses case data).
$env:AI_ASSISTANT_CLM_BACKEND_URL = 'http://127.0.0.1:8000'
$env:AI_ASSISTANT_LLM_PROFILE = 'local_openai_compatible'
$env:AI_ASSISTANT_LLM_BASE_URL = 'http://127.0.0.1:11435/v1'
$env:AI_ASSISTANT_LLM_MODEL = 'ministral-3:8b'
$env:AI_ASSISTANT_EMBED_BASE_URL = 'http://127.0.0.1:11435'

# GPT-OSS settings (D-091/D-092/D-094/D-095); the ledger path is set in the store block below.
$env:AI_ASSISTANT_REMOTE_INFERENCE_DECISION = 'D-091'
$env:AI_ASSISTANT_REMOTE_LIVE_DECISION = 'D-092'
$env:AI_ASSISTANT_OPENROUTER_ENDPOINT = 'deepinfra/bf16'
$env:AI_ASSISTANT_LLM_REASONING_EFFORT = 'medium'
$env:AI_ASSISTANT_LLM_REASONING_ALLOWANCE_TOKENS = '1400'
$env:AI_ASSISTANT_BUDGET_DAILY_CAP_MICRO_USD = '5000000'
$env:AI_ASSISTANT_LOCAL_API_TEST_DECISION = 'D-094'
$env:AI_ASSISTANT_SYNTHETIC_DEV_DECISION = 'D-095'
$env:AI_ASSISTANT_LOCAL_API_TEST_OWNER_ATTESTS = $(if ($OpenRouterOwnerAttests) { 'auto_topup_off,prompt_logging_off' } else { '' })
$env:AI_ASSISTANT_LOCAL_API_TEST_MAX_CALLS = '20'
$env:AI_ASSISTANT_LOCAL_API_TEST_PREFLIGHT_SECONDS = '300'
$env:AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_QUESTIONS = 'P01#1,P02#0'
$env:AI_ASSISTANT_LOCAL_API_TEST_QUALIFICATION_COUNT = '2'

# Claude (D-107): the HR enablement record decides; decision/attests empty; server workspace pin.
$env:AI_ASSISTANT_ANTHROPIC_DECISION = ''
$env:AI_ASSISTANT_ANTHROPIC_OWNER_ATTESTS = ''
$env:AI_ASSISTANT_ANTHROPIC_WORKSPACE_ID = $WorkspaceId
Remove-Item Env:AI_ASSISTANT_ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
$env:AI_ASSISTANT_ANTHROPIC_DAILY_CAP_MICRO_USD = '5000000'
$env:AI_ASSISTANT_ANTHROPIC_MAX_CALLS = '20'

# Stores (D-108): one root, relative names, all set explicitly (process env beats .env).
$env:AI_ASSISTANT_DATA_DIR = $root
$env:AI_ASSISTANT_MODEL_ADMIN_DB_PATH   = 'data/models/model_admin.sqlite3'
$env:AI_ASSISTANT_MODEL_PROFILES_FILE   = 'data/models/profiles.json'
# D-118 amendment P2: the POC session stores (created from AI Models on first use). The earlier
# design's ledgers (budget/ledger.sqlite3, budget/anthropic_fyp_ledger.sqlite3) are not used;
# archive them first with scripts/storage/archive_accounting_stores.py (non-destructive).
$env:AI_ASSISTANT_ANTHROPIC_LEDGER_PATH = 'data/budget/sessions/anthropic.sqlite3'
$env:AI_ASSISTANT_BUDGET_LEDGER_PATH    = 'data/budget/sessions/openrouter.sqlite3'
$env:AI_ASSISTANT_KNOWLEDGE_DATA_DIR    = 'data/knowledge'

$env:PYTHONPATH = "$repo\apps\assistant"
Set-Location "$repo\apps\assistant"
& $py -c "import ai_assistant, sys; p = ai_assistant.__file__; print('assistant code:', p); sys.exit(0 if p.startswith(r'$repo\apps\assistant\ai_assistant') else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Assistant would load code outside the repository root.' }
$env:CLM_EXPECTED_ROOT = $root
& $py $check
if ($LASTEXITCODE -ne 0) { throw 'Store resolution check failed (code without the data root, or a path outside it).' }
Remove-Item Env:CLM_EXPECTED_ROOT
if ($StatusOnly) { 'paths ok; not starting'; exit 0 }
if (-not (Test-Path -LiteralPath $LogDir)) { throw "Missing restricted log folder: $LogDir" }
$log = "$LogDir\assistant-$(Get-Date -Format yyyyMMdd-HHmmss).log"
Start-Transcript -LiteralPath $log | Out-Null
try { & $py -m uvicorn ai_assistant.main:app --host 127.0.0.1 --port 8100 --no-access-log } finally { Stop-Transcript | Out-Null }
