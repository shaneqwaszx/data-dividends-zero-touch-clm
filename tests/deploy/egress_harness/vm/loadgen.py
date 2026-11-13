"""R3 G2 disallowed-destination load generator (RL rows) and socket fuzzer (AC-1).

Fed on stdin into a running R3 container (`docker exec -i [-u 65532:65532] <c> python3 -I -`),
so it runs with that container's real credentials and network namespace.

  loadgen <role> <seconds>   keep trying every disallowed target for <seconds>
  fuzz <role>                one pass over a broad destination x port x protocol matrix

Prints one JSON summary line: attempts and successes per target. A "success" is a completed TCP
handshake or a UDP reply, i.e. an escape. The authoritative leak count is the harness sink.
"""

import json
import socket
import sys
import threading
import time

ROLE = sys.argv[2]
ALLOWED = {"proxy": ("34.120.0.10", 443, "tcp"), "resolver": ("172.26.0.2", 53, "udp")}[ROLE]
ALLOWED_TCP = {"proxy": ("34.120.0.10", 443), "resolver": ("172.26.0.2", 53)}[ROLE]
LOAD = [
    ("169.254.169.254", 80, "tcp"),
    ("169.254.169.254", 80, "udp"),
    ("172.26.5.5", 22, "tcp"),
    ("172.26.0.1", 22, "tcp"),
    ("172.30.242.1", 22, "tcp"),
    ("172.30.241.1", 22, "tcp"),
    ("172.26.4.119", 22, "tcp"),
    ("1.1.1.1", 80, "tcp"),
    ("1.1.1.1", 53, "udp"),
    ("2001:db8::9", 443, "tcp"),
    ("34.120.0.10", 80, "tcp"),
    ("172.17.0.1", 80, "tcp"),
]
LOAD += (
    [("172.26.0.2", 53, "udp"), ("172.26.0.2", 53, "tcp")]
    if ROLE == "proxy"
    else [("34.120.0.10", 443, "tcp")]
)


def attempt(dst: str, port: int, proto: str, timeout: float = 0.4) -> bool:
    fam = socket.AF_INET6 if ":" in dst else socket.AF_INET
    s = socket.socket(fam, socket.SOCK_STREAM if proto == "tcp" else socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        if proto == "tcp":
            s.connect((dst, port))
            return True
        s.sendto(b"r3-loadgen", (dst, port))
        s.recvfrom(64)
        return True
    except OSError:
        return False
    finally:
        s.close()


def run(targets: list[tuple[str, int, str]], seconds: float, workers: int = 6) -> dict:
    """Stream one JSON line per second (so a SIGKILLed container still leaves a record)."""
    stats: dict[str, list[int]] = {f"{d}:{p}/{t}": [0, 0] for d, p, t in targets}
    lock = threading.Lock()
    stop = time.monotonic() + seconds
    queue = list(targets)
    done = threading.Event()

    def worker(index: int) -> None:
        i = index
        while True:
            if seconds and time.monotonic() > stop:
                return
            if not seconds and i >= len(queue):
                return
            d, p, t = queue[i % len(queue)]
            ok = attempt(d, p, t)
            with lock:
                stats[f"{d}:{p}/{t}"][0] += 1
                stats[f"{d}:{p}/{t}"][1] += int(ok)
            i += workers

    def reporter() -> None:
        while not done.wait(1.0):
            with lock:
                line = {
                    "t": round(time.time(), 3),
                    "progress": True,
                    "role": ROLE,
                    "attempts": sum(v[0] for v in stats.values()),
                    "escapes": {k: v[1] for k, v in stats.items() if v[1]},
                }
            print(json.dumps(line, sort_keys=True), flush=True)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(workers)]
    rep = threading.Thread(target=reporter, daemon=True)
    rep.start()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    done.set()
    return stats


def fuzz_targets() -> list[tuple[str, int, str]]:
    dsts = [
        "1.1.1.1",
        "8.8.8.8",
        "34.120.0.10",
        "34.120.0.11",
        "169.254.169.254",
        "169.254.169.253",
        "172.26.0.1",
        "172.26.0.2",
        "172.26.5.5",
        "172.26.4.119",
        "172.30.242.1",
        "172.30.241.1",
        "172.30.241.3",
        "172.17.0.1",
        "172.18.0.1",
        "10.0.0.1",
        "100.64.0.1",
        "192.168.1.1",
        "198.18.0.1",
        "192.0.2.1",
        "203.0.113.1",
        "224.0.0.251",
        "240.0.0.1",
        "2001:db8::9",
        "2001:db8:26::1",
        "fe80::1%eth0",
    ]
    ports = [21, 22, 25, 53, 80, 123, 443, 853, 3128, 4750, 8000, 8080, 8443, 27017, 65535]
    out = []
    for d in dsts:
        for p in ports:
            for t in ("tcp", "udp"):
                if (d, p, t) == ALLOWED or (t == "tcp" and (d, p) == ALLOWED_TCP):
                    continue
                out.append((d, p, t))
    return out


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "loadgen":
        stats = run(LOAD, float(sys.argv[3]))
    else:
        stats = run(fuzz_targets(), 0, workers=12)
    escapes = {k: v[1] for k, v in stats.items() if v[1]}
    print(
        json.dumps(
            {
                "mode": mode,
                "role": ROLE,
                "attempts": sum(v[0] for v in stats.values()),
                "targets": len(stats),
                "escapes": escapes,
            },
            sort_keys=True,
        ),
        flush=True,
    )
