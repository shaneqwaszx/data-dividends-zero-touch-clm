"""Read-only logical fingerprints of the assistant stores (no keys, no case/answer/entry text).

Usage: store_fingerprint.py <state_db> <fyp_ledger> <hist_ledger> <gptoss_ledger>
                            <knowledge_db> <chroma_db>
Used before cutover (on the sources) and after (on the destination); outputs must match.
Every table in every store is also row-counted, so a change in any table is visible.
"""

import sqlite3
import sys
from pathlib import Path


def ro(path):
    return sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True, timeout=2)


def rows(con, sql):
    return [tuple(r) for r in con.execute(sql)]


def counts(con, label):
    tables = [
        r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    ]
    print(
        f" table_counts[{label}]",
        [(t, con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]) for t in tables],
    )
    print(
        f" pragmas[{label}]",
        rows(con, "SELECT * FROM pragma_user_version"),
        rows(con, "PRAGMA quick_check"),
    )


state, fyp, hist, gptoss, knowledge, chroma = sys.argv[1:7]

con = ro(state)
print("[state]")
print(
    " activation",
    rows(
        con,
        "SELECT revision, active_profile_id, active_fingerprint,"
        " active_qualification_id, active_prompt_limit, last_good_profile_id,"
        " last_good_qualification_id, changed_at FROM activation",
    ),
)
print(
    " enablement",
    rows(
        con,
        "SELECT revision, enabled, substr(workspace_id,-4),"
        " workspace_limit_micro_usd, changed_at FROM anthropic_enablement",
    ),
)
print(
    " qualifications",
    rows(
        con,
        "SELECT qualification_id, profile_id, basis, status, code,"
        " done_turns, total_turns, finished_at FROM qualifications"
        " ORDER BY started_at",
    ),
)
print(
    " spending_controls",
    rows(con, "SELECT revision, daily_cap_micro_usd, max_calls, changed_at FROM spending_controls"),
)
print(
    " claude_spending_controls",
    rows(
        con,
        "SELECT revision, daily_cap_micro_usd, max_calls, changed_at FROM claude_spending_controls",
    ),
)
print(
    " data_access_policy",
    rows(con, "SELECT revision, local_restricted, changed_at FROM data_access_policy"),
)
print(" events", rows(con, "SELECT COUNT(*), MAX(seq), MAX(at) FROM events"))
print(" connection_tests", rows(con, "SELECT COUNT(*), MAX(at) FROM connection_tests"))
counts(con, "state")
con.close()

for name, path in (("fyp", fyp), ("historical", hist), ("gptoss", gptoss)):
    con = ro(path)
    print(f"[ledger:{name}]")
    print(
        " meta",
        rows(
            con,
            "SELECT schema_version, ledger_id, profile_id, key_alias, cap_micro_usd,"
            " opening_usage_micro_usd, baseline_micro_usd, last_provider_usage_micro_usd,"
            " local_charged_micro_usd, open_reserved_micro_usd, breaker_open, breaker_code,"
            " breaker_opened_at, last_reconciled_at, created_at FROM ledger_meta",
        ),
    )
    print(
        " calls",
        rows(
            con,
            "SELECT state, COUNT(*), SUM(charged_micro_usd), SUM(reserved_micro_usd)"
            " FROM calls GROUP BY state ORDER BY state",
        ),
    )
    print(" calls_max", rows(con, "SELECT MAX(id), MAX(created_at), MAX(closed_at) FROM calls"))
    print(
        " operator_events",
        rows(
            con,
            "SELECT id, created_at, event, amount_micro_usd, code FROM operator_events ORDER BY id",
        ),
    )
    counts(con, name)
    con.close()

con = ro(knowledge)
print("[knowledge]")
print(
    " answer_records",
    rows(con, "SELECT COUNT(*), MAX(id), MAX(created_at), COUNT(rated_at) FROM answer_records"),
)
print(" answer_record_views", rows(con, "SELECT COUNT(*), MAX(viewed_at) FROM answer_record_views"))
print(" answer_record_keeps", rows(con, "SELECT COUNT(*) FROM answer_record_keeps"))
print(
    " conversations",
    rows(con, "SELECT COUNT(*), MAX(updated_at), COUNT(ended_at) FROM conversations"),
)
print(
    " entries",
    rows(con, "SELECT COUNT(*), MAX(created_at), COUNT(DISTINCT content_hash) FROM entries"),
)
print(
    " reviews/feedback/retire/index_tasks",
    rows(
        con,
        "SELECT (SELECT COUNT(*) FROM reviews),"
        " (SELECT COUNT(*) FROM feedback),"
        " (SELECT COUNT(*) FROM retire_requests),"
        " (SELECT COUNT(*) FROM index_tasks)",
    ),
)
print(" meta", rows(con, "SELECT key, value FROM meta ORDER BY key"))
counts(con, "knowledge")
con.close()

con = ro(chroma)
print("[chroma]")
print(" collections", rows(con, "SELECT name, dimension FROM collections ORDER BY name"))
print(" segments", rows(con, "SELECT type, scope FROM segments ORDER BY type, scope"))
print(" max_seq_id", rows(con, "SELECT COUNT(*), MAX(seq_id) FROM max_seq_id"))
counts(con, "chroma")
con.close()
