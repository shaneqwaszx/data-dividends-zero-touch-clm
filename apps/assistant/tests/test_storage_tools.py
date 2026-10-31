"""B0 (D-109): the operator storage tools in scripts/storage, on synthetic stores only.

Every store here is created in pytest's temporary folder from the real schema owners; the
tools run as child processes (as an operator runs them) and never see a live root.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from ai_assistant.budget import BudgetLedger
from ai_assistant.knowledge.store import KnowledgeStore
from ai_assistant.model_admin_store import ModelAdminStore

ASSISTANT_DIR = Path(__file__).resolve().parents[1]
TOOLS = ASSISTANT_DIR / "scripts" / "storage"
BACKUP = TOOLS / "backup_stores.py"
FINGERPRINT = TOOLS / "store_fingerprint.py"
CHECK = TOOLS / "check_data_root.py"
TEMPLATE = TOOLS / "start_assistant.example.ps1"


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AI_ASSISTANT_")}
    env.update(extra)
    return env


def _run(*args: object, cwd: Path | None = None, env: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, *map(str, args)],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env or _env(),
        timeout=120,
    )


def _sqlite(path: Path, rows: int = 3) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE t (x INTEGER)")
        db.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(rows)])
    return path


def _stores(root: Path) -> list[Path]:
    # The six SQLite stores in the fingerprint's argument order, from their real schema owners.
    state = root / "models" / "model_admin.sqlite3"
    ModelAdminStore(state)
    ledgers = []
    for name in ("anthropic_fyp_ledger", "archive_ledger", "ledger"):
        path = root / "budget" / f"{name}.sqlite3"
        path.parent.mkdir(parents=True, exist_ok=True)
        BudgetLedger.initialise(
            path, cap_micro_usd=1_000_000, opening_usage_micro_usd=0, key_alias="key-01"
        )
        ledgers.append(path)
    knowledge = root / "knowledge" / "knowledge.sqlite3"
    KnowledgeStore(knowledge)
    chroma = root / "knowledge" / "chroma" / "chroma.sqlite3"
    chroma.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(chroma) as db:
        db.executescript(
            "CREATE TABLE collections (name TEXT, dimension INTEGER);"
            "CREATE TABLE segments (type TEXT, scope TEXT);"
            "CREATE TABLE max_seq_id (seq_id INTEGER);"
            "INSERT INTO collections VALUES ('official_guidance', NULL);"
        )
    return [state, *ledgers, knowledge, chroma]


# --- backup_stores.py -------------------------------------------------------------------


def test_backup_publishes_verified_copies_and_a_manifest_without_touching_sources(tmp_path):
    db = _sqlite(tmp_path / "src" / "a b.sqlite3")
    profile = tmp_path / "src" / "profiles.json"
    profile.write_text('{"x": 1}', encoding="utf-8")
    before = {p: p.read_bytes() for p in (db, profile)}
    out = tmp_path / "out"
    result = _run(
        BACKUP, tmp_path / "m.json", f"{db}=>{out / 'a.sqlite3'}", f"{profile}=>{out / 'p.json'}"
    )
    assert result.returncode == 0, result.stdout
    manifest = json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))
    assert [e["method"] for e in manifest] == ["sqlite_backup_api", "copy"]
    assert manifest[0]["integrity"] == "ok"
    assert manifest[1]["source_sha256"] == manifest[1]["destination_sha256"]
    with sqlite3.connect(out / "a.sqlite3") as copy:
        assert copy.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 3
    assert {p: p.read_bytes() for p in (db, profile)} == before
    assert not list(out.glob("*.partial"))


@pytest.mark.parametrize("alias", ["duplicate", "case", "dotdot"])
def test_backup_refuses_destinations_that_resolve_to_the_same_file(tmp_path, alias):
    a, b = _sqlite(tmp_path / "a.sqlite3"), _sqlite(tmp_path / "b.sqlite3")
    out = tmp_path / "out"
    second = {
        "duplicate": out / "x.sqlite3",
        "case": out / "X.SQLITE3",
        "dotdot": out / "sub" / ".." / "x.sqlite3",
    }[alias]
    if alias == "case" and os.path.normcase("A") == "A":
        pytest.skip("case-insensitive paths only")
    result = _run(BACKUP, tmp_path / "m.json", f"{a}=>{out / 'x.sqlite3'}", f"{b}=>{second}")
    assert result.returncode == 2
    assert "REFUSED" in result.stdout
    assert not out.exists() or not any(out.rglob("*"))


def test_backup_refuses_existing_destination_partial_manifest_and_source_as_destination(
    tmp_path,
):
    a = _sqlite(tmp_path / "a.sqlite3")
    existing = tmp_path / "out" / "x.sqlite3"
    existing.parent.mkdir()
    existing.write_bytes(b"keep")
    assert _run(BACKUP, tmp_path / "m1.json", f"{a}=>{existing}").returncode == 2
    assert existing.read_bytes() == b"keep"

    partial = tmp_path / "out" / "y.sqlite3.partial"
    partial.write_bytes(b"keep")
    assert (
        _run(BACKUP, tmp_path / "m2.json", f"{a}=>{tmp_path / 'out' / 'y.sqlite3'}").returncode == 2
    )
    assert partial.read_bytes() == b"keep"

    (tmp_path / "m3.json").write_text("[]", encoding="utf-8")
    manifest = _run(BACKUP, tmp_path / "m3.json", f"{a}=>{tmp_path / 'z.sqlite3'}")
    assert manifest.returncode == 2
    assert "REFUSED: manifest exists" in manifest.stdout
    assert not (tmp_path / "z.sqlite3").exists()

    # A destination that is another pair's source: refused even when that file does not exist
    # yet (so the existing-destination check cannot be what refuses it).
    b = _sqlite(tmp_path / "b.sqlite3")
    c = tmp_path / "c.sqlite3"
    as_source = _run(BACKUP, tmp_path / "m4.json", f"{b}=>{c}", f"{c}=>{tmp_path / 'd.sqlite3'}")
    assert as_source.returncode == 2
    assert "REFUSED: destination is a source" in as_source.stdout
    assert not c.exists()
    other = _run(BACKUP, tmp_path / "m5.json", f"{a}=>{b}", f"{b}=>{tmp_path / 'e.sqlite3'}")
    assert other.returncode == 2
    assert "REFUSED: destination is a source" in other.stdout


def test_backup_refuses_a_source_with_a_hot_journal(tmp_path):
    a = _sqlite(tmp_path / "a.sqlite3")
    Path(f"{a}-journal").write_bytes(b"")
    result = _run(BACKUP, tmp_path / "m.json", f"{a}=>{tmp_path / 'out' / 'a.sqlite3'}")
    assert result.returncode == 2
    assert "journal" in result.stdout
    assert not (tmp_path / "out").exists()


def test_backup_failure_publishes_nothing_and_the_same_command_can_be_retried(tmp_path):
    good = _sqlite(tmp_path / "good.sqlite3")
    bad = tmp_path / "bad.sqlite3"
    bad.write_bytes(b"not a database")
    out = tmp_path / "out"
    pairs = [f"{good}=>{out / 'good.sqlite3'}", f"{bad}=>{out / 'bad.sqlite3'}"]
    failed = _run(BACKUP, tmp_path / "m.json", *pairs)
    assert failed.returncode == 1
    assert "nothing published" in failed.stdout
    assert not any(out.rglob("*.sqlite3*"))
    assert not (tmp_path / "m.json").exists()
    assert bad.read_bytes() == b"not a database"

    retried = _run(BACKUP, tmp_path / "m.json", pairs[0])
    assert retried.returncode == 0, retried.stdout


# --- store_fingerprint.py ---------------------------------------------------------------


def test_fingerprint_matches_a_backup_copy_and_sees_a_change_in_any_table(tmp_path):
    sources = _stores(tmp_path / "src")
    copies = [tmp_path / "copy" / s.relative_to(tmp_path / "src") for s in sources]
    pairs = [f"{s}=>{c}" for s, c in zip(sources, copies, strict=True)]
    assert _run(BACKUP, tmp_path / "m.json", *pairs).returncode == 0

    original = _run(FINGERPRINT, *sources)
    assert original.returncode == 0, original.stderr
    assert _run(FINGERPRINT, *copies).stdout == original.stdout
    for section in ("[state]", "[ledger:fyp]", "[ledger:gptoss]", "[knowledge]", "[chroma]"):
        assert section in original.stdout

    # A table the named fields do not cover still shows through the row counts.
    with sqlite3.connect(copies[4]) as db:
        db.execute(
            "INSERT INTO answer_record_views (record_id, viewer, viewed_at) VALUES ('r', 'v', 't')"
        )
    changed = _run(FINGERPRINT, *copies)
    assert changed.returncode == 0, changed.stderr
    differing = set(changed.stdout.splitlines()) ^ set(original.stdout.splitlines())
    assert differing
    assert all("answer_record_views" in line for line in differing)


def test_fingerprint_opens_read_only_and_prints_no_workspace_id(tmp_path):
    sources = _stores(tmp_path / "src")
    with sqlite3.connect(sources[0]) as db:
        db.execute(
            "INSERT INTO anthropic_enablement (id, revision, enabled, workspace_id,"
            " workspace_limit_micro_usd, confirmations, changed_at, changed_by)"
            " VALUES (1, 1, 1, 'SYNTHETICWORKSPACEabcd', 1, '[]', 't', 'u')"
        )
    before = {s: s.read_bytes() for s in sources}
    result = _run(FINGERPRINT, *sources)
    assert result.returncode == 0, result.stderr
    assert "SYNTHETICWORKSPACE" not in result.stdout
    assert "'abcd'" in result.stdout
    assert {s: s.read_bytes() for s in sources} == before


# --- check_data_root.py -----------------------------------------------------------------


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    for rel in (
        "models/model_admin.sqlite3",
        "budget/anthropic_fyp_ledger.sqlite3",
        "budget/ledger.sqlite3",
        "models/profiles.json",
    ):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"")
    (root / "knowledge").mkdir()
    return root


def _check_env(root: Path, **overrides: str) -> dict[str, str]:
    settings = {
        "AI_ASSISTANT_DATA_DIR": str(root),
        "AI_ASSISTANT_MODEL_ADMIN_DB_PATH": "data/models/model_admin.sqlite3",
        "AI_ASSISTANT_MODEL_PROFILES_FILE": "data/models/profiles.json",
        "AI_ASSISTANT_ANTHROPIC_LEDGER_PATH": "data/budget/anthropic_fyp_ledger.sqlite3",
        "AI_ASSISTANT_BUDGET_LEDGER_PATH": "data/budget/ledger.sqlite3",
        "AI_ASSISTANT_KNOWLEDGE_DATA_DIR": "data/knowledge",
    }
    settings.update(overrides)
    return _env(PYTHONPATH=str(ASSISTANT_DIR), CLM_EXPECTED_ROOT=str(root), **settings)


def test_check_data_root_passes_when_every_store_resolves_under_the_root(tmp_path):
    root = _root(tmp_path)
    result = _run(CHECK, cwd=tmp_path, env=_check_env(root))
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("ok ") == 7


def test_check_data_root_fails_on_an_absolute_override_or_a_missing_store(tmp_path):
    root = _root(tmp_path)
    elsewhere = _sqlite(tmp_path / "elsewhere" / "ledger.sqlite3")
    override = _run(
        CHECK, cwd=tmp_path, env=_check_env(root, AI_ASSISTANT_BUDGET_LEDGER_PATH=str(elsewhere))
    )
    assert override.returncode == 1
    assert "FAIL budget_ledger" in override.stdout

    (root / "models" / "profiles.json").unlink()
    missing = _run(CHECK, cwd=tmp_path, env=_check_env(root))
    assert missing.returncode == 1
    assert "FAIL model_profiles_file" in missing.stdout


# --- start_assistant.example.ps1 --------------------------------------------------------


def test_launcher_template_has_no_machine_path_or_workspace_id():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z]:\\Users\\", text)
    assert not re.search(r"wrkspc_[A-Za-z0-9]{6,}", text)
    assert "AI_ASSISTANT_ANTHROPIC_WORKSPACE_ID = $WorkspaceId" in text
    assert "Remove-Item Env:AI_ASSISTANT_ANTHROPIC_API_KEY" in text


def test_launcher_template_sets_every_store_relatively_under_the_data_root():
    text = TEMPLATE.read_text(encoding="utf-8")
    stores = dict(re.findall(r"\$env:(AI_ASSISTANT_\w+)\s*=\s*'(data/[^']+)'", text))
    assert stores == {
        "AI_ASSISTANT_MODEL_ADMIN_DB_PATH": "data/models/model_admin.sqlite3",
        "AI_ASSISTANT_MODEL_PROFILES_FILE": "data/models/profiles.json",
        "AI_ASSISTANT_ANTHROPIC_LEDGER_PATH": "data/budget/anthropic_fyp_ledger.sqlite3",
        "AI_ASSISTANT_BUDGET_LEDGER_PATH": "data/budget/ledger.sqlite3",
        "AI_ASSISTANT_KNOWLEDGE_DATA_DIR": "data/knowledge",
    }
    assert "$env:AI_ASSISTANT_DATA_DIR = $root" in text
    assert "check_data_root.py" in text


def test_launcher_template_parameter_defaults_do_not_use_the_script_root():
    # Windows PowerShell 5.1 leaves $PSScriptRoot empty while parameter defaults are evaluated.
    text = TEMPLATE.read_text(encoding="utf-8")
    params = text[text.index("param(") : text.index("$ErrorActionPreference")]
    assert "$PSScriptRoot" not in params


@pytest.mark.skipif(shutil.which("powershell.exe") is None, reason="Windows PowerShell only")
def test_launcher_template_parses_in_windows_powershell():
    script = (
        "$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
        f"'{TEMPLATE}', [ref]$null, [ref]$e); $e.Count"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.stdout.strip() == "0", result.stdout + result.stderr
