"""Summarise an S2 gate run directory into a pass/fail table (stdout, Markdown).

  python3 -I analyse_gates.py <run-dir>

Hard-gate rules (handoff section 5, owner decision G2-P2 option B):
  P-2: only the exact control row may tunnel; every other row must be refused
       (403 by the R3 head gate or 407/400 by Smokescreen) with no SYN.
  P-4: every prohibited answer refused.  P-5/P-6/P-7: zero SYNs from the proxy to anything
  but the GoldTier IP:443 and the R3 resolver:53.  P-10/D-7: no DNS to anything but the R3
  resolver.  D-2: upstream sees only `A <fqdn>`.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

GT = ("34.120.0.10", "443")
RESOLVER = ("172.30.241.4", "53")
UPSTREAM = ("172.26.0.2", "53")
PROXY_IPS = {"172.30.241.2", "172.30.242.2", "127.0.0.1"}
RESOLVER_IPS = {"172.30.241.4", "172.30.242.3"}
FQDN = "goldtier.r3-harness.invalid."


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.startswith("{")]


def captures(path: Path) -> tuple[collections.Counter, collections.Counter]:
    syn: collections.Counter = collections.Counter()
    udp: collections.Counter = collections.Counter()
    if not path.exists():
        return syn, udp
    for line in path.read_text().splitlines():
        m = re.search(r" (\S+)\.(\d+) > (\S+)\.(\d+): Flags \[S\],", line)
        if m:
            syn[(m.group(1), m.group(3), m.group(4))] += 1
            continue
        m = re.search(r" (\S+)\.(\d+) > (\S+)\.(\d+): (?:UDP|\d+\+? )", line)
        if m:
            udp[(m.group(1), m.group(3), m.group(4))] += 1
    return syn, udp


def main() -> int:
    d = Path(sys.argv[1])
    verdicts: list[tuple[str, bool, str]] = []

    p1 = rows(d / "P-1.jsonl")
    verdicts.append(
        (
            "P-1",
            bool(p1)
            and p1[0].get("tunnel")
            and p1[0].get("tls") == "TLSv1.3"
            and p1[0].get("upstream_status", "").endswith("200 OK"),
            json.dumps(p1[:1]),
        )
    )

    p2 = rows(d / "P-2.jsonl")
    bad = [r for r in p2 if (r["gate"] == "P-2/exact-control") != (r.get("code") == "200")]
    refused_codes = collections.Counter(
        r.get("code") for r in p2 if r["gate"] != "P-2/exact-control"
    )
    verdicts.append(
        (
            "P-2",
            len(p2) >= 35 and not bad,
            f"{len(p2)} rows; non-control codes {dict(refused_codes)}; violations {[r['gate'] for r in bad]}",  # noqa: E501
        )
    )

    p2b = rows(d / "P-2b.jsonl")
    p2b_ev = rows(d / "P-2b.events.jsonl")
    bad_b = [
        r["gate"]
        for r in p2b
        if " 407 " not in r.get("first_status", "") + " "
        or not r.get("closed_by_proxy")
        or r.get("second_response")
    ]
    gt_conn = sum(1 for r in p2b_ev if r["kind"] in ("gt_request", "gt_tls_fail"))
    lookups = sum(1 for r in p2b_ev if r["kind"] == "dns_query")
    verdicts.append(
        (
            "P-2b (QG P3-3)",
            len(p2b) == 8 and not bad_b and gt_conn == 0 and lookups <= len(p2b),
            f"{len(p2b)} rows; violations {bad_b}; upstream lookups {lookups} "
            f"(first requests only); GoldTier connections {gt_conn}",
        )
    )

    p3 = rows(d / "P-3.jsonl")
    verdicts.append(
        (
            "P-3",
            bool(p3) and all(r.get("code") != "200" for r in p3),
            str(collections.Counter(r.get("code") for r in p3)),
        )
    )

    p4 = rows(d / "P-4.jsonl")
    verdicts.append(
        (
            "P-4",
            len(p4) >= 24 and not any(r.get("tunnel") for r in p4),
            f"{len(p4)} prohibited answers, tunnels={sum(bool(r.get('tunnel')) for r in p4)}",
        )
    )

    for name, files in (
        ("P-5", ["P-5.169.254.169.254.jsonl", "P-5.127.0.0.1.jsonl"]),
        ("P-6", ["P-6.jsonl"]),
    ):
        detail = []
        for f in files:
            c = collections.Counter(bool(r.get("tunnel")) for r in rows(d / f))
            detail.append(f"{f}: tunnels={c[True]} refused={c[False]}")
        verdicts.append((name + " (client view)", True, "; ".join(detail)))

    syn, udp = captures(d / "gates.cap.txt")
    illegal_syn = {
        k: v for k, v in syn.items() if k[0] in PROXY_IPS and (k[1], k[2]) not in {GT, RESOLVER}
    }
    illegal_syn.update(
        {k: v for k, v in syn.items() if k[0] in RESOLVER_IPS and (k[1], k[2]) != UPSTREAM}
    )
    verdicts.append(
        (
            "P-5/P-6/P-7 (capture)",
            not illegal_syn and sum(syn.values()) > 0,
            f"pure SYNs {dict(syn)}; prohibited {illegal_syn}",
        )
    )
    illegal_dns = {
        k: v
        for k, v in udp.items()
        if (k[0] in PROXY_IPS and (k[1], k[2]) != RESOLVER)
        or (k[0] in RESOLVER_IPS and (k[1], k[2]) != UPSTREAM and k[1] != "172.30.241.2")
    }
    verdicts.append(
        ("P-10/D-7 (capture)", not illegal_dns, f"UDP flows {dict(udp)}; prohibited {illegal_dns}")
    )

    p7 = rows(d / "P-7.jsonl")
    verdicts.append(
        (
            "P-7 (client view)",
            bool(p7),
            str(collections.Counter((r.get("answers"), bool(r.get("tunnel"))) for r in p7)),
        )
    )

    p10 = rows(d / "P-10.jsonl")
    verdicts.append(
        ("P-10 resolver down", bool(p10) and not p10[0].get("tunnel"), json.dumps(p10[:1]))
    )

    upstream = collections.Counter()
    leaks = collections.Counter()
    for f in sorted(d.glob("*.events.jsonl")):
        for r in rows(f):
            if r["kind"] == "dns_query":
                upstream[(r["qname"], r["qtype"])] += 1
            if r["kind"] in {"LEAK_tcp", "LEAK_udp", "imds_hit"}:
                leaks[(r["kind"], r.get("dst"), r.get("dport"))] += 1
    verdicts.append(("D-2 upstream", set(upstream) == {(FQDN, 1)}, str(dict(upstream))))
    verdicts.append(("Sink LEAK/IMDS events", not leaks, str(dict(leaks))))

    d2 = (d / "D-2.txt").read_text() if (d / "D-2.txt").exists() else ""
    lines = [line for line in d2.splitlines() if "->" in line]

    def exact_a(line: str) -> bool:
        query = line.split("->")[0].split()
        return query[-2:] == [FQDN.rstrip("."), "A"]

    ok_d2 = bool(lines) and all(("NOERROR" in line) == exact_a(line) for line in lines)
    verdicts.append(("D-2 resolver answers", ok_d2, " | ".join(lines)))

    p8 = rows(d / "P-8.hostile.jsonl")
    argv = (d / "P-8.argv.txt").read_text() if (d / "P-8.argv.txt").exists() else ""
    syn8, _ = captures(d / "p8.cap.txt")
    ok8 = (
        "unsafe" not in argv
        and bool(p8)
        and p8[0].get("tunnel")
        and not any(r.get("code") == "200" for r in p8[1:])
        and all((k[1], k[2]) in {GT, RESOLVER, ("172.30.241.2", "4750")} for k in syn8)
    )
    verdicts.append(
        (
            "P-8",
            ok8,
            f"hostile rows {[(r.get('gate'), r.get('code') or r.get('status')) for r in p8]}; SYNs {dict(syn8)}",  # noqa: E501
        )
    )

    print("| Gate | Verdict | Detail |\n|---|---|---|")
    for name, ok, detail in verdicts:
        print(f"| {name} | {'PASS' if ok else '**FAIL**'} | {detail[:900]} |")
    return 0 if all(ok for _, ok, _ in verdicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
