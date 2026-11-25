"""R3 G2 E-row client (harness VM host, run as root). The real product path:

  browser-equivalent client -> Caddy (https://localhost, published on all addresses, as on
  the host) -> backend
  -> HR GoldTier Sandbox Search -> R3 egress proxy -> fake GoldTier (test CA)

  python3 -I e_client.py search [goldtier_id]   HR Sandbox Search; prints status/outcome only
  python3 -I e_client.py health                  backend /health through Caddy
  python3 -I e_client.py mockcase                RM login and one Mock-lane zero-touch case

The per-run credential is read from the harness work directory and never printed. Output is the
HTTP status, the API's status/error_code/upstream_status/count fields and timings only.
"""

from __future__ import annotations

import http.cookiejar
import json
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ORIGIN = "https://localhost"
CREDENTIAL = Path("/var/lib/clm-r3-harness/credential")


def client() -> urllib.request.OpenerDirector:
    root = subprocess.run(
        [
            "docker",
            "exec",
            "clm-staging-frontend-1",
            "cat",
            "/data/caddy/pki/authorities/local/root.crt",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    context = ssl.create_default_context(cadata=root)
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=context),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )


def call(
    opener, path: str, data: object | None = None, csrf: str | None = None
) -> tuple[int, dict]:
    headers = {"Origin": ORIGIN}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()
    if csrf:
        headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(ORIGIN + path, data=body, headers=headers)
    try:
        resp = opener.open(req, timeout=30)
    except urllib.error.HTTPError as err:
        resp = err
    with resp:
        raw = resp.read()
        try:
            return resp.status, json.loads(raw)
        except ValueError:
            return resp.status, {}


def login(opener, user: str) -> str:
    status, body = call(
        opener, "/api/auth/login", {"user_id": user, "password": CREDENTIAL.read_text().strip()}
    )
    if status != 200:
        raise SystemExit(f"login {user}: HTTP {status}")
    return body["csrf_token"]


def main(argv: list[str]) -> int:
    opener = client()
    start = time.monotonic()
    if argv[1] == "health":
        status, body = call(opener, "/health")
        out = {"row": "health", "http": status, "environment": body.get("environment")}
    elif argv[1] == "search":
        csrf = login(opener, "biz-ops")
        status, body = call(
            opener,
            "/api/admin/goldtier-sandbox/search",
            {"goldtier_id": argv[2] if len(argv) > 2 else "900001"},
            csrf,
        )
        out = {
            "row": "search",
            "http": status,
            "status": body.get("status"),
            "count": body.get("count"),
            "error_code": body.get("error_code"),
            "upstream_status": body.get("upstream_status"),
            "candidate_ids": [c.get("party_id") for c in body.get("candidates", [])],
        }
    elif argv[1] == "mockcase":
        csrf = login(opener, "maya-lim")
        status, body = call(
            opener,
            "/api/clm/zero-touch/cases",
            {"uen": "202400001A", "country_of_incorporation": "SG"},
            csrf,
        )
        out = {
            "row": "mockcase",
            "http": status,
            "case_created": bool(body.get("case", {}).get("case_id")),
        }
    else:
        raise SystemExit("unknown row")
    out["seconds"] = round(time.monotonic() - start, 3)
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
