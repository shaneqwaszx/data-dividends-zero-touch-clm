"""R3 G2 gate client. Runs inside the stand-in backend container on goldtier-control.

Speaks raw HTTP proxy protocol to the egress proxy so that hostile request forms can be sent
exactly as written. One JSON line per attempt on stdout. Stdlib only; no payload is logged.

  python3 gate_client.py p1 <fqdn> <ca>        tunnel + TLS 1.3 handshake with the test CA
  python3 gate_client.py raw <request-line> [host-header]
  python3 gate_client.py p2 <fqdn>             the full P-2 request matrix
  python3 gate_client.py p3 <fqdn>
  python3 gate_client.py loop <fqdn> <ca> <n> <gap-seconds>   repeated P-1 attempts (P-5/P-6)
"""

from __future__ import annotations

import json
import socket
import ssl
import sys
import time

PROXY = ("172.30.241.2", 4750)


def out(**fields: object) -> None:
    print(json.dumps(fields, sort_keys=True), flush=True)


def send_raw(request: bytes, timeout: float = 8.0) -> tuple[socket.socket | None, str, float]:
    start = time.monotonic()
    s = socket.create_connection(PROXY, timeout=timeout)
    s.sendall(request)
    buf = b""
    try:
        while b"\r\n\r\n" not in buf and len(buf) < 8192:
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
    except OSError as exc:
        return None, f"recv-error:{type(exc).__name__}", time.monotonic() - start
    status = buf.split(b"\r\n", 1)[0].decode("ascii", "replace")
    return s, status, time.monotonic() - start


def raw(label: str, request_line: str, host: str | None) -> None:
    req = request_line.encode("utf-8") + b"\r\n"
    if host is not None:
        req += b"Host: " + host.encode("utf-8") + b"\r\n"
    req += b"\r\n"
    try:
        s, status, took = send_raw(req)
    except OSError as exc:
        out(
            gate=label,
            request=request_line,
            host=host,
            status=f"connect-error:{type(exc).__name__}",
        )
        return
    if s is not None:
        s.close()
    code = status.split(" ")[1] if status.startswith("HTTP/") and " " in status else status
    out(
        gate=label,
        request=request_line,
        host=host,
        status=status,
        code=code,
        seconds=round(took, 3),
    )


def tunnel(fqdn: str, ca: str, label: str) -> dict[str, object]:
    req = f"CONNECT {fqdn}:443 HTTP/1.1\r\nHost: {fqdn}:443\r\n\r\n".encode()
    result: dict[str, object] = {"gate": label}
    try:
        s, status, took = send_raw(req)
    except OSError as exc:
        result.update(status=f"connect-error:{type(exc).__name__}")
        return result
    result.update(status=status, connect_seconds=round(took, 3))
    if s is None or " 200" not in status:
        if s is not None:
            s.close()
        result["tunnel"] = False
        return result
    ctx = ssl.create_default_context(cafile=ca)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    try:
        with ctx.wrap_socket(s, server_hostname=fqdn) as tls:
            tls.sendall(
                f"GET /harness/gt-xpi/v1/customers/search?goldTierID=900001 HTTP/1.1\r\n"
                f"Host: {fqdn}\r\nConnection: close\r\n\r\n".encode()
            )
            first = tls.recv(64).split(b"\r\n", 1)[0].decode("ascii", "replace")
            result.update(
                tunnel=True,
                tls=tls.version(),
                upstream_status=first,
                peer_cert_cn=dict(x[0] for x in tls.getpeercert()["subject"]).get("commonName"),
            )
    except (ssl.SSLError, OSError) as exc:
        result.update(tunnel=True, tls_error=type(exc).__name__)
    return result


def p2(fqdn: str) -> None:
    up = fqdn.upper()
    rows = [
        ("exact-control", f"CONNECT {fqdn}:443 HTTP/1.1", f"{fqdn}:443"),
        ("other-name", "CONNECT example.invalid:443 HTTP/1.1", "example.invalid:443"),
        ("subdomain", f"CONNECT x.{fqdn}:443 HTTP/1.1", f"x.{fqdn}:443"),
        ("suffix-append", f"CONNECT {fqdn}.evil.invalid:443 HTTP/1.1", None),
        ("prefix-append", f"CONNECT evil{fqdn}:443 HTTP/1.1", None),
        ("uppercase", f"CONNECT {up}:443 HTTP/1.1", None),
        ("trailing-dot", f"CONNECT {fqdn}.:443 HTTP/1.1", None),
        ("double-dot", f"CONNECT {fqdn}..:443 HTTP/1.1", None),
        ("ip-literal-gt", "CONNECT 34.120.0.10:443 HTTP/1.1", None),
        ("ip-literal-imds", "CONNECT 169.254.169.254:443 HTTP/1.1", None),
        ("ip-literal-v6-mapped", "CONNECT [::ffff:34.120.0.10]:443 HTTP/1.1", None),
        ("ip-literal-v6-loop", "CONNECT [::1]:443 HTTP/1.1", None),
        ("ip-decimal", "CONNECT 578813962:443 HTTP/1.1", None),
        ("ip-octal", "CONNECT 042.0170.0.012:443 HTTP/1.1", None),
        ("userinfo", f"CONNECT user:pw@{fqdn}:443 HTTP/1.1", None),
        ("userinfo-at-other", f"CONNECT {fqdn}@example.invalid:443 HTTP/1.1", None),
        ("no-port", f"CONNECT {fqdn} HTTP/1.1", None),
        ("pct-encoded", f"CONNECT {fqdn.replace('.', '%2e', 1)}:443 HTTP/1.1", None),
        (
            "unicode-fullwidth-dot",
            f"CONNECT {fqdn.replace('.', chr(0xFF0E), 1)}:443 HTTP/1.1",
            None,
        ),
        ("host-header-mismatch", "CONNECT example.invalid:443 HTTP/1.1", f"{fqdn}:443"),
        ("absolute-form-http", f"GET http://{fqdn}/ HTTP/1.1", fqdn),
        ("absolute-form-http-443", f"GET http://{fqdn}:443/ HTTP/1.1", f"{fqdn}:443"),
        ("absolute-form-https", f"GET https://{fqdn}/ HTTP/1.1", fqdn),
        ("origin-form-host", "GET / HTTP/1.1", f"{fqdn}:443"),
        ("post-absolute", f"POST http://{fqdn}:443/ HTTP/1.1", f"{fqdn}:443"),
        ("mixed-case", f"CONNECT {fqdn[:1].upper() + fqdn[1:]}:443 HTTP/1.1", f"{fqdn}:443"),
        ("exact-conflicting-host", f"CONNECT {fqdn}:443 HTTP/1.1", "example.invalid:443"),
        ("exact-uppercase-host", f"CONNECT {fqdn}:443 HTTP/1.1", f"{up}:443"),
        ("exact-no-host", f"CONNECT {fqdn}:443 HTTP/1.1", None),
        ("exact-http10", f"CONNECT {fqdn}:443 HTTP/1.0", f"{fqdn}:443"),
        ("pct-encoded-colon", f"CONNECT {fqdn}%3a443 HTTP/1.1", f"{fqdn}:443"),
        ("ip-literal-imds-host", "CONNECT 169.254.169.254:443 HTTP/1.1", "169.254.169.254:443"),
        ("port-80-with-host", f"CONNECT {fqdn}:80 HTTP/1.1", f"{fqdn}:80"),
        ("trailing-dot-with-host", f"CONNECT {fqdn}.:443 HTTP/1.1", f"{fqdn}.:443"),
        ("userinfo-with-host", f"CONNECT user:pw@{fqdn}:443 HTTP/1.1", f"{fqdn}:443"),
    ]
    for label, line, host in rows:
        raw(f"P-2/{label}", line, host)


def p3(fqdn: str) -> None:
    for port in ("80", "8443", "22", "53", "0443", "443 ", "65536"):
        raw(f"P-3/port-{port.strip() or 'blank'}", f"CONNECT {fqdn}:{port} HTTP/1.1", None)


def second_request(label: str, fqdn: str, follow: str, pipelined: bool) -> None:
    """P-2b (QG P3-3): an exact CONNECT that Smokescreen refuses, then a second, NON-exact head
    on the same connection. The second head must never be processed (no response, no lookup)."""
    first = f"CONNECT {fqdn}:443 HTTP/1.1\r\nHost: {fqdn}:443\r\n\r\n".encode()
    second = follow.encode() + b"\r\n\r\n"
    s = socket.create_connection(PROXY, timeout=8)
    s.sendall(first + second if pipelined else first)
    buf, closed, error = b"", False, None
    deadline = time.monotonic() + 8
    try:
        while b"\r\n\r\n" not in buf and time.monotonic() < deadline:
            chunk = s.recv(4096)
            if not chunk:
                closed = True
                break
            buf += chunk
        status1 = buf.split(b"\r\n", 1)[0].decode("ascii", "replace")
        rest = buf.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in buf else b""
        if not pipelined and not closed:
            try:
                s.sendall(second)
            except OSError as exc:
                error = f"send:{type(exc).__name__}"
        s.settimeout(4)
        while not closed:
            try:
                chunk = s.recv(4096)
            except TimeoutError:
                break
            except OSError as exc:
                error = f"recv:{type(exc).__name__}"
                closed = True
                break
            if not chunk:
                closed = True
                break
            rest += chunk
    finally:
        s.close()
    # `rest` holds the first response's body; a second response would start a new status line.
    later = rest.find(b"HTTP/1.")
    second_status = (
        rest[later:].split(b"\r\n", 1)[0].decode("ascii", "replace") if later >= 0 else ""
    )
    out(
        gate=f"P-2b/{label}",
        first_status=status1,
        second_request=follow.split("\r\n")[0],
        second_response=second_status,
        closed_by_proxy=closed,
        error=error,
    )


def p2b(fqdn: str) -> None:
    up = fqdn.upper()
    follows = {
        "uppercase-connect": f"CONNECT {up}:443 HTTP/1.1\r\nHost: {up}:443",
        "userinfo-connect": f"CONNECT u:p@{fqdn}:443 HTTP/1.1\r\nHost: {fqdn}:443",
        "absolute-get": f"GET http://{fqdn}:443/ HTTP/1.1\r\nHost: {fqdn}:443",
        "ip-literal-imds": "CONNECT 169.254.169.254:443 HTTP/1.1\r\nHost: 169.254.169.254:443",
    }
    for name, follow in follows.items():
        for pipelined in (False, True):
            time.sleep(2.5)  # start outside the zone window, so the first answer is prohibited
            second_request(
                f"{name}-{'pipelined' if pipelined else 'after-response'}", fqdn, follow, pipelined
            )


def main(argv: list[str]) -> int:
    cmd = argv[1]
    if cmd == "p2b":
        p2b(argv[2])
        return 0
    if cmd == "p1":
        out(**tunnel(argv[2], argv[3], "P-1"))
    elif cmd == "raw":
        raw("raw", argv[2], argv[3] if len(argv) > 3 else None)
    elif cmd == "p2":
        p2(argv[2])
    elif cmd == "p3":
        p3(argv[2])
    elif cmd == "loop":
        fqdn, ca, n, gap = argv[2], argv[3], int(argv[4]), float(argv[5])
        for i in range(n):
            row = tunnel(fqdn, ca, "loop")
            row["i"] = i
            out(**row)
            time.sleep(gap)
    else:
        raise SystemExit(f"unknown command {cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
