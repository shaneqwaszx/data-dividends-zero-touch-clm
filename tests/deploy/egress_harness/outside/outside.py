"""R3 G2 harness: the simulated world beyond the harness VM's ens5 uplink.

Runs as root inside the dedicated `clmr3out` network namespace on the harness side (never on a
real host). Every destination the VM can route to is local here (AnyIP), so a leaked packet
gets a real answer, which makes a leak observable instead of silently black-holed.

Roles, chosen by the connection's local (destination) address and port:

* 172.26.0.2:53 UDP/TCP - the simulated VPC resolver, serving a scripted test zone.
* 169.254.169.254:80 - a simulated IMDSv2 endpoint (token PUT and a metadata GET).
* GoldTier fake (GT_IPS):443 - TLS 1.3 only, test-CA certificate, minimal XPI search route.
* Anything else - recorded as a LEAK event and answered with a small banner or echo.

All events are JSON lines on stdout. No payload bodies are logged, only sizes and the first
bytes' type (TLS record or not). Stdlib only.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import selectors
import socket
import ssl
import struct
import sys
import threading
import time
from pathlib import Path

RESOLVER_IP = "172.26.0.2"
IMDS_IP = "169.254.169.254"
TCP_PORTS = (22, 25, 53, 80, 123, 443, 853, 3128, 4750, 8080, 8443)
UDP_PORTS = (53, 123, 443, 853)
_lock = threading.Lock()


def emit(kind: str, **fields: object) -> None:
    record = {"t": round(time.time(), 6), "kind": kind, **fields}
    with _lock:
        sys.stdout.write(json.dumps(record, sort_keys=True) + "\n")
        sys.stdout.flush()


# --------------------------------------------------------------------------- DNS test zone


class Zone:
    """Scripted answers, re-read from a JSON control file on every query.

    Control file keys:
      fqdn: the allowed name (lowercase, no trailing dot)
      mode: "static" | "alternate" | "first_then" | "mixed"
      a: list of A answers for static mode / the allowed answer
      prohibited: list of prohibited answers used by alternate / first_then
      aaaa: list of AAAA answers (any mode)
      ttl: integer TTL (default 0)
    """

    def __init__(self, control: Path) -> None:
        self.control = control
        self.counter: dict[str, int] = {}
        self.last: dict[str, float] = {}

    def config(self) -> dict[str, object]:
        try:
            return json.loads(self.control.read_text())
        except (OSError, ValueError):
            return {"fqdn": "", "mode": "static", "a": []}

    def answers(self, qname: str, qtype: int) -> tuple[int, list[tuple[int, bytes]], int]:
        cfg = self.config()
        fqdn = str(cfg.get("fqdn", "")).lower().rstrip(".")
        ttl = int(cfg.get("ttl", 0))
        if qname.lower().rstrip(".") != fqdn:
            return 3, [], ttl  # NXDOMAIN
        n = self.counter.get(qname, 0)
        self.counter[qname] = n + 1
        now = time.monotonic()
        quiet = now - self.last.get(qname, 0.0) > float(cfg.get("window", 0.5))
        self.last[qname] = now
        if qtype == 28:
            return 0, [(28, socket.inet_pton(socket.AF_INET6, a)) for a in cfg.get("aaaa", [])], ttl
        if qtype != 1:
            return 0, [], ttl
        mode = cfg.get("mode", "static")
        allowed = list(cfg.get("a", []))
        prohibited = list(cfg.get("prohibited", []))
        if mode == "alternate":
            chosen = allowed if n % 2 == 0 else prohibited
        elif mode == "first_then":
            # The first query of each burst gets the allowed answer; any repeat query within
            # `window` seconds (a re-resolution between check and connect) gets a prohibited one.
            chosen = allowed if quiet else prohibited
        elif mode == "then_allowed":
            # P-2b (QG P3-3): the first query of a burst is refused (prohibited answer); a second
            # request on the same connection within `window` would get the allowed answer.
            chosen = prohibited if quiet else allowed
        elif mode == "mixed":
            chosen = prohibited + allowed
        else:
            chosen = allowed
        return 0, [(1, socket.inet_aton(a)) for a in chosen], ttl


def parse_query(data: bytes) -> tuple[int, int, str, int, int]:
    txid, flags, qd = struct.unpack("!HHH", data[:6])
    pos, labels = 12, []
    while True:
        length = data[pos]
        if length == 0:
            pos += 1
            break
        if length & 0xC0:
            raise ValueError("compressed qname")
        labels.append(data[pos + 1 : pos + 1 + length].decode("ascii", "replace"))
        pos += 1 + length
    qtype, qclass = struct.unpack("!HH", data[pos : pos + 4])
    return txid, flags, ".".join(labels) + ".", qtype, pos + 4


def build_reply(data: bytes, zone: Zone) -> tuple[bytes, dict[str, object]]:
    txid, flags, qname, qtype, end = parse_query(data)
    rcode, answers, ttl = zone.answers(qname, qtype)
    rd = flags & 0x0100
    header = struct.pack("!HHHHHH", txid, 0x8000 | 0x0400 | rd | rcode, 1, len(answers), 0, 0)
    body = data[12:end]
    for rtype, rdata in answers:
        body += struct.pack("!HHHIH", 0xC00C, rtype, 1, ttl, len(rdata)) + rdata
    meta = {
        "qname": qname,
        "qtype": qtype,
        "rcode": rcode,
        "answers": [
            socket.inet_ntop(socket.AF_INET if t == 1 else socket.AF_INET6, r) for t, r in answers
        ],
    }
    return header + body, meta


# --------------------------------------------------------------------------- TCP handlers


def gt_tls_context(cert: Path, key: Path) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(cert, key)
    return ctx


def handle_gt(conn: socket.socket, peer: tuple, local: tuple, ctx: ssl.SSLContext) -> None:
    sni: list[str | None] = [None]
    ctx.sni_callback = lambda sock, name, c: sni.__setitem__(0, name)  # type: ignore[assignment]
    try:
        tls = ctx.wrap_socket(conn, server_side=True)
    except (ssl.SSLError, OSError) as exc:
        emit("gt_tls_fail", peer=peer[0], local=local[0], error=type(exc).__name__, sni=sni[0])
        conn.close()
        return
    with tls:
        request = b""
        while b"\r\n\r\n" not in request and len(request) < 16384:
            chunk = tls.recv(4096)
            if not chunk:
                break
            request += chunk
        line = request.split(b"\r\n", 1)[0].decode("ascii", "replace")
        method, _, rest = line.partition(" ")
        path = rest.split(" ", 1)[0].split("?", 1)[0]
        emit(
            "gt_request",
            peer=peer[0],
            local=local[0],
            sni=sni[0],
            version=tls.version(),
            method=method,
            path=path,
        )
        if method == "GET" and path == "/harness/hold":
            # RL rows: a long-lived tunnel that ticks every 0.5 s, so its end is observable.
            tls.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n")
            for _ in range(600):
                try:
                    tls.sendall(b".")
                except OSError:
                    break
                time.sleep(0.5)
            emit("gt_hold_end", peer=peer[0])
            return
        if method == "GET" and path.endswith("/gt-xpi/v1/customers/search"):
            body = json.dumps(
                [{"goldTierID": "900001", "legalName": "R3 HARNESS SYNTHETIC PTE LTD"}]
            ).encode()
            status = "200 OK"
        else:
            body, status = b"{}", "404 Not Found"
        tls.sendall(
            f"HTTP/1.1 {status}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n"  # noqa: E501
            "Connection: close\r\n\r\n".encode()
            + body
        )


def handle_imds(conn: socket.socket, peer: tuple, local: tuple) -> None:
    data = conn.recv(4096)
    line = data.split(b"\r\n", 1)[0].decode("ascii", "replace")
    emit("imds_hit", peer=peer[0], request_line=line[:80])
    body = b"SIMULATED-IMDS-TOKEN" if line.startswith("PUT") else b"simulated-metadata"
    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (len(body), body))
    conn.close()


def handle_dns_tcp(conn: socket.socket, peer: tuple, zone: Zone) -> None:
    try:
        size = struct.unpack("!H", conn.recv(2))[0]
        data = conn.recv(size)
        reply, meta = build_reply(data, zone)
        emit("dns_query", transport="tcp", peer=peer[0], **meta)
        conn.sendall(struct.pack("!H", len(reply)) + reply)
    except (OSError, ValueError, struct.error) as exc:
        emit("dns_error", transport="tcp", peer=peer[0], error=type(exc).__name__)
    conn.close()


def handle_leak(conn: socket.socket, peer: tuple, local: tuple) -> None:
    conn.settimeout(1.0)
    first = b""
    with contextlib.suppress(OSError):
        first = conn.recv(64)
    emit(
        "LEAK_tcp",
        peer=peer[0],
        peer_port=peer[1],
        dst=local[0],
        dport=local[1],
        first_bytes=len(first),
        tls_record=first[:1] == b"\x16",
    )
    with contextlib.suppress(OSError):
        conn.sendall(b"R3-HARNESS-SINK\r\n")
    conn.close()


def tcp_dispatch(
    conn: socket.socket,
    peer: tuple,
    gt_ips: set[str],
    zone: Zone,
    ctx: ssl.SSLContext,
    wrong_ctx: ssl.SSLContext,
    wrong_ips: set[str],
) -> None:
    local = conn.getsockname()
    if local[0] in gt_ips and local[1] == 443:
        handle_gt(conn, peer, local, ctx)
    elif local[0] in wrong_ips and local[1] == 443:
        handle_gt(conn, peer, local, wrong_ctx)
    elif local[0] == IMDS_IP and local[1] == 80:
        handle_imds(conn, peer, local)
    elif local[0] == RESOLVER_IP and local[1] == 53:
        handle_dns_tcp(conn, peer, zone)
    else:
        handle_leak(conn, peer, local)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", type=Path, required=True)
    ap.add_argument("--cert", type=Path, required=True)
    ap.add_argument("--key", type=Path, required=True)
    ap.add_argument("--wrong-cert", type=Path, required=True)
    ap.add_argument("--wrong-key", type=Path, required=True)
    ap.add_argument("--gt-ips", default="34.120.0.10")
    ap.add_argument("--wrong-ips", default="34.120.0.11")
    args = ap.parse_args()
    zone = Zone(args.control)
    gt_ips = set(args.gt_ips.split(","))
    wrong_ips = set(args.wrong_ips.split(","))
    ctx = gt_tls_context(args.cert, args.key)
    wrong_ctx = gt_tls_context(args.wrong_cert, args.wrong_key)
    sel = selectors.DefaultSelector()
    resolver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    resolver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    resolver.bind((RESOLVER_IP, 53))
    sel.register(resolver, selectors.EVENT_READ, ("resolver", socket.AF_INET))
    for family, host in ((socket.AF_INET, "0.0.0.0"), (socket.AF_INET6, "::")):
        for port in TCP_PORTS:
            s = socket.socket(family, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            s.bind((host, port))
            s.listen(256)
            sel.register(s, selectors.EVENT_READ, ("tcp", family))
        for port in UDP_PORTS:
            u = socket.socket(family, socket.SOCK_DGRAM)
            u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET:
                u.setsockopt(socket.IPPROTO_IP, socket.IP_PKTINFO, 1)
            else:
                u.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                u.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_RECVPKTINFO, 1)
            u.bind((host, port))
            sel.register(u, selectors.EVENT_READ, ("udp", family))
    emit("ready", pid=os.getpid(), gt_ips=sorted(gt_ips))
    while True:
        for key, _ in sel.select():
            proto, family = key.data
            sock: socket.socket = key.fileobj  # type: ignore[assignment]
            if proto == "tcp":
                conn, peer = sock.accept()
                threading.Thread(
                    target=tcp_dispatch,
                    args=(conn, peer, gt_ips, zone, ctx, wrong_ctx, wrong_ips),
                    daemon=True,
                ).start()
                continue
            if proto == "resolver":
                data, peer = sock.recvfrom(4096)
                try:
                    reply, meta = build_reply(data, zone)
                except (ValueError, IndexError, struct.error) as exc:
                    emit("dns_error", transport="udp", peer=peer[0], error=type(exc).__name__)
                    continue
                emit("dns_query", transport="udp", peer=peer[0], **meta)
                sock.sendto(reply, peer)
                continue
            data, anc, _flags, peer = sock.recvmsg(4096, socket.CMSG_SPACE(64))
            dst = None
            for _level, ctype, cdata in anc:
                if family == socket.AF_INET and ctype == socket.IP_PKTINFO:
                    dst = socket.inet_ntoa(cdata[8:12])
                elif family == socket.AF_INET6 and ctype == socket.IPV6_PKTINFO:
                    dst = socket.inet_ntop(socket.AF_INET6, cdata[:16])
            port = sock.getsockname()[1]
            emit("LEAK_udp", peer=peer[0], peer_port=peer[1], dst=dst, dport=port, size=len(data))


if __name__ == "__main__":
    raise SystemExit(main())
