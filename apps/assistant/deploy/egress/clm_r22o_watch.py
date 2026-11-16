"""Hosted GPT-OSS egress host-table watcher (D-138 A1 PROPOSED, LOCAL DESIGN CANDIDATE).
Install: /usr/local/lib/clm-r22o/. Stdlib only. A copy of E1's clm_r22_watch.py (itself adapted
from R3's clm_r3_watch.py, D-127 E7); only the table, the container list and the event names
differ (tests/test_openrouter_egress.py asserts that).

Expected state: `table inet clm_r22o` exactly as /etc/clm/r22o/clm_r22o.nft defines it. The expected
hash is computed at start by loading that file into a throwaway network namespace, so a table
already tampered with at start is never mistaken for the reference.

Detection: `nft monitor` events trigger an immediate check, and a check also runs every second.
A check compares the live table's normalised hash (handles and counter values removed) with the
expected one.

Response to absence or mismatch: stop the egress proxy and resolver (docker stop --time 0), log
CLM_R22O_FIREWALL_LOSS, and keep stopping them while the table stays wrong. The watcher never
re-applies the table and never starts a container. Logs carry event names and timings only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time

TABLE = ("inet", "clm_r22o")
_lock = threading.Lock()


def log(event: str, **fields: object) -> None:
    with _lock:
        sys.stdout.write(
            json.dumps({"t": round(time.time(), 6), "event": event, **fields}, sort_keys=True)
            + "\n"
        )
        sys.stdout.flush()


def normalised_hash(nft_json: str) -> str:
    def strip(node: object) -> object:
        if isinstance(node, dict):
            return {
                k: ({} if k == "counter" and isinstance(v, dict) else strip(v))
                for k, v in node.items()
                if k != "handle"
            }
        if isinstance(node, list):
            return [strip(i) for i in node if not (isinstance(i, dict) and "metainfo" in i)]
        return node

    return hashlib.sha256(
        json.dumps(strip(json.loads(nft_json)), sort_keys=True).encode()
    ).hexdigest()


def expected_hash(table_file: str) -> str:
    out = subprocess.run(
        [
            "/usr/bin/unshare",
            "--net",
            "/bin/sh",
            "-ec",
            f'/usr/sbin/nft -f "$1" && /usr/sbin/nft -j list table {TABLE[0]} {TABLE[1]}',
            "sh",
            table_file,
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    ).stdout
    return normalised_hash(out)


def live_hash() -> str | None:
    result = subprocess.run(
        ["/usr/sbin/nft", "-j", "list", "table", *TABLE], capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return None
    try:
        return normalised_hash(result.stdout)
    except ValueError:
        return None


def running(containers: list[str]) -> list[str]:
    result = subprocess.run(
        [
            "/usr/bin/docker",
            "ps",
            "--format",
            "{{.Names}}",
            *sum((["--filter", f"name=^{c}$"] for c in containers), []),
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return [n for n in result.stdout.split() if n in containers]


class Watcher:
    def __init__(self, expected: str, containers: list[str]) -> None:
        self.expected = expected
        self.containers = containers
        self.check_lock = threading.Lock()
        self.tripped = False

    def check(self, trigger: str) -> None:
        with self.check_lock:
            seen = time.time()
            live = live_hash()
            if live == self.expected:
                if self.tripped:
                    log("CLM_R22O_TABLE_RESTORED_CONTAINERS_LEFT_STOPPED", trigger=trigger)
                    self.tripped = False
                return
            up = running(self.containers)
            if not up and self.tripped:
                return
            # --time 0: SIGKILL at once (fail closed within the Amendment A bounds). Docker never
            # restarts it (restart "no", P2-1); only clm-r22o-egress.service starts them.
            stop = subprocess.run(
                ["/usr/bin/docker", "stop", "--time", "0", *self.containers],
                capture_output=True,
                text=True,
                timeout=30,
            )
            log(
                "CLM_R22O_FIREWALL_LOSS",
                trigger=trigger,
                table="absent" if live is None else "mismatch",
                were_running=up,
                stop_rc=stop.returncode,
                detect_to_stopped_s=round(time.time() - seen, 3),
            )
            self.tripped = True

    def monitor(self) -> None:
        while True:
            try:
                # `nft monitor` accepts a single object filter only; unfiltered covers tables,
                # chains, rules, sets and elements in every table.
                proc = subprocess.Popen(
                    ["/usr/sbin/nft", "monitor"], stdout=subprocess.PIPE, text=True
                )
                assert proc.stdout is not None
                for _line in proc.stdout:
                    self.check("event")
                proc.wait()
            except OSError:
                pass
            log("CLM_R22O_MONITOR_RESTART")
            time.sleep(0.5)

    def periodic(self) -> None:
        while True:
            self.check("periodic")
            time.sleep(1.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table-file", required=True)
    ap.add_argument("--containers", required=True)
    ap.add_argument("--check-only", action="store_true", help="exit 0 if the live table matches")
    args = ap.parse_args()
    containers = [c for c in args.containers.split(",") if c]
    expected = expected_hash(args.table_file)
    if args.check_only:
        live = live_hash()
        print(json.dumps({"expected": expected, "live": live, "match": live == expected}))
        return 0 if live == expected else 1
    watcher = Watcher(expected, containers)
    log("CLM_R22O_WATCH_START", expected=expected, containers=containers)
    watcher.check("start")
    threading.Thread(target=watcher.monitor, name="monitor", daemon=True).start()
    watcher.periodic()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
