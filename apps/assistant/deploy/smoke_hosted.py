"""Stage A smoke: the real assistant image behind the real Caddy, backend and MongoDB.

    python -B apps/assistant/deploy/smoke_hosted.py BACKEND FRONTEND ASSISTANT [report.json]

It runs the reviewed Compose files with the candidate Caddyfile mounted over the frontend's, so
no shared deployment file changes. ACRA and GoldTier are Mock, no provider key exists, and the
assistant has no route to the internet, so no paid inference is possible. The Compose project,
disposable database, volumes and certificates are removed on exit, and each credential is
generated for the run and never printed.
"""

import concurrent.futures
import hashlib
import http.cookiejar
import json
import os
import secrets
import socket
import ssl
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MONGO_IMAGE = "mongo:7"
HASH_VARIABLES = (
    "PHASE13_MAYA_LIM",
    "PHASE13_ETHAN_TAN",
    "PHASE13_SOPHIA_NG",
    "PHASE13_RYAN_LEE",
    "PHASE13_OLIVIA_KOH",
    "PHASE14_5_HR_ADMIN",
    "PHASE13_SUPPORT_USER",
)
SCRIPTED_REPLY = "This case is approved by the regulator and needs no further review."
# A mock OpenAI-compatible provider, started inside the assistant container on the no-model
# port for one step. It proves the real adapter and output checks with no network route.
MOCK_PROVIDER = r"""
import http.server, json
REPLY = "@REPLY@"
class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
        with open("/tmp/mock-provider.calls", "a") as calls:
            calls.write("call\n")
        if request.get("stream"):
            events = [
                {"choices": [{"delta": {"content": REPLY}, "finish_reason": None}]},
                {"choices": [{"delta": {}, "finish_reason": "stop"}]},
            ]
            text = "".join("data: " + json.dumps(e) + "\n\n" for e in events)
            body, kind = (text + "data: [DONE]\n\n").encode(), "text/event-stream"
        else:
            choice = {"message": {"content": REPLY}, "finish_reason": "stop"}
            body, kind = json.dumps({"choices": [choice]}).encode(), "application/json"
        self.send_response(200)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass
http.server.ThreadingHTTPServer(("127.0.0.1", 9), Handler).serve_forever()
""".replace("@REPLY@", SCRIPTED_REPLY)
STOP_MOCK_PROVIDER = """
import os, signal
for name in os.listdir("/proc"):
    if name.isdigit() and int(name) != os.getpid():
        try:
            line = open(f"/proc/{name}/cmdline", "rb").read()
        except OSError:
            continue
        if b"ThreadingHTTPServer" in line:
            os.kill(int(name), signal.SIGKILL)
"""
EGRESS_PROBE = """
import socket
results = {}
for name, target in (("internet", ("1.1.1.1", 443)), ("mongo", ("mongo", 27017))):
    try:
        socket.create_connection(target, timeout=3).close()
        results[name] = "reached"
    except OSError:
        results[name] = "blocked"
try:
    socket.getaddrinfo("openrouter.ai", 443)
    results["public_dns"] = "resolved"
except OSError:
    results["public_dns"] = "blocked"
socket.create_connection(("clm-backend-proxy", 8000), timeout=3).close()
results["backend"] = "reached"
print(results)
"""
READY_PROBE = """
import urllib.request
print(urllib.request.urlopen("http://127.0.0.1:8100/internal/ready", timeout=8).read().decode())
"""
MOCK_CALLS = "print(len(open('/tmp/mock-provider.calls').readlines()))"
DATA_PROBE = (
    "from pathlib import Path; from assistant_hosting.readiness import data_usage;"
    "print(data_usage(Path('/data')))"
)
KILL_WORKER = "import os; os.kill(int(open('/tmp/assistant.pid').read()), {signal})"
SIGKILL = 9
SIGSTOP = 19
# Caddy's `max_size 512KB` (Caddyfile.candidate) is decimal: 512,000 bytes pass, 512,001 do not.
BODY_LIMIT_BYTES = 512_000
# The same over-limit body sent straight to the assistant, behind Caddy's back, on loopback inside
# its container. The assistant has no size limit of its own, so it must answer with its own 422;
# a 413 through Caddy then cannot have come from the assistant. The session is read from stdin.
DIRECT_OVERSIZE_PROBE = """
import http.client, json, sys
given = json.load(sys.stdin)
connection = http.client.HTTPConnection("127.0.0.1", 8100, timeout=30)
connection.request("POST", given["path"], body=given["body"].encode(), headers={
    "Cookie": given["cookie"], "Origin": given["origin"], "X-CSRF-Token": given["csrf"],
    "Content-Type": "application/json"})
response = connection.getresponse()
body = response.read()
try:
    detail = json.loads(body)["detail"][0]
    found = {"type": detail.get("type"), "loc": detail.get("loc")}
except Exception:
    found = None
print(json.dumps({"status": response.status, "detail": found}))
"""


def prefer_ipv4() -> None:
    # On Windows a refused ::1 attempt adds two seconds to each new connection to "localhost",
    # which would be measured as assistant latency.
    resolve = socket.getaddrinfo

    def ipv4_only(host: Any, port: Any, family: int = 0, *args: Any, **kwargs: Any) -> Any:
        return resolve(host, port, socket.AF_INET, *args, **kwargs)

    socket.getaddrinfo = ipv4_only


def peak_memory(samples: list[dict[str, dict[str, str]]]) -> dict[str, str]:
    def mib(text: str) -> float:
        value = text.split("/")[0].strip()
        scale = {"KiB": 1 / 1024, "MiB": 1.0, "GiB": 1024.0}[value[-3:]]
        return float(value[:-3]) * scale

    names = {name for row in samples for name in row}
    return {
        name: f"{max(mib(row[name]['memory']) for row in samples if name in row):.1f}MiB"
        for name in names
    }


def peak_cpu(samples: list[dict[str, dict[str, str]]]) -> dict[str, str]:
    names = {name for row in samples for name in row}
    return {
        name: f"{max(float(row[name]['cpu'].rstrip('%')) for row in samples if name in row):.1f}%"
        for name in names
    }


def check(condition: object, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def padded_body(size: int) -> bytes:
    """A chat body of exactly ``size`` bytes: a short valid question plus an unknown field.

    The assistant refuses the unknown field with its own 422 ``extra_forbidden`` at any size, so
    neither its 4,000-character message limit nor anything else in it can return 413."""

    head = b'{"message":"What is blocking this case?","pad":"'
    tail = b'"}'
    body = head + b"x" * (size - len(head) - len(tail)) + tail
    check(len(body) == size, "padded body has the wrong size")
    return body


def capped_post(
    origin: str,
    context: ssl.SSLContext,
    path: str,
    headers: dict[str, str],
    body: bytes,
    *,
    chunked: bool,
) -> tuple[bool, int, bytes]:
    """POST through Caddy over raw TLS and return (body_sent, final status, response body).

    With a declared length the request carries ``Expect: 100-continue``, so Caddy answers before
    any body byte is sent and its decision is read as a status, never inferred from a dropped
    connection. A chunked body is streamed and the final status read after it. Every connection
    error, timeout or unparseable reply propagates and fails the smoke."""

    host, port = origin.removeprefix("https://").rsplit(":", 1)
    lines = [f"POST {path} HTTP/1.1", f"Host: {host}:{port}", "Connection: close"]
    lines += [f"{name}: {value}" for name, value in headers.items()]
    lines += (
        ["Transfer-Encoding: chunked"]
        if chunked
        else [
            f"Content-Length: {len(body)}",
            "Expect: 100-continue",
        ]
    )
    head = ("\r\n".join(lines) + "\r\n\r\n").encode("ascii")

    def framed() -> bytes:
        if not chunked:
            return body
        pieces = [body[start : start + 16384] for start in range(0, len(body), 16384)]
        return b"".join(f"{len(p):x}\r\n".encode() + p + b"\r\n" for p in pieces) + b"0\r\n\r\n"

    with (
        socket.create_connection(("127.0.0.1", int(port)), timeout=30) as plain,
        context.wrap_socket(plain, server_hostname=host) as tls,
    ):
        tls.sendall(head)
        received = b""
        sent = False
        if chunked:
            tls.sendall(framed())
            sent = True
        else:
            while b"\r\n\r\n" not in received:
                chunk = tls.recv(65536)
                check(chunk, "Caddy closed the connection before answering")
                received += chunk
            if received.split(b"\r\n", 1)[0].split(b" ")[1] == b"100":
                received = received.split(b"\r\n\r\n", 1)[1]
                tls.sendall(framed())
                sent = True
        while chunk := tls.recv(65536):
            received += chunk
    check(b"\r\n\r\n" in received, "no complete HTTP response")
    while received.split(b"\r\n", 1)[0].split(b" ")[1].startswith(b"1"):
        received = received.split(b"\r\n\r\n", 1)[1]
    status_line, rest = received.split(b"\r\n", 1)
    response_headers, response_body = rest.split(b"\r\n\r\n", 1)
    if b"transfer-encoding: chunked" in response_headers.lower():
        decoded = b""
        while response_body:
            size_text, response_body = response_body.split(b"\r\n", 1)
            length = int(size_text.split(b";")[0], 16)
            if length == 0:
                break
            decoded += response_body[:length]
            response_body = response_body[length + 2 :]
        response_body = decoded
    return sent, int(status_line.split(b" ")[1]), response_body


def assistant_validation(body: bytes) -> object:
    """The assistant's own 422 for the padded body's unknown field, or None."""

    try:
        detail = json.loads(body)["detail"][0]
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    if detail.get("type") == "extra_forbidden" and detail.get("loc") == ["body", "pad"]:
        return detail["type"]
    return None


class Browser:
    """One signed-in person: their own cookie jar, and the page's Origin on every request."""

    def __init__(self, origin: str, context: ssl.SSLContext) -> None:
        self.origin = origin
        self.csrf: str | None = None
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=context),
            urllib.request.HTTPCookieProcessor(self.jar),
        )

    def cookie_header(self) -> str:
        return "; ".join(f"{cookie.name}={cookie.value}" for cookie in self.jar)

    def request(
        self,
        path: str,
        expected: int = 200,
        data: Any = None,
        *,
        method: str | None = None,
        origin: str | None = "page",
    ) -> bytes:
        headers: dict[str, str] = {}
        if origin is not None:
            headers["Origin"] = self.origin if origin == "page" else origin
        if self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        payload = None
        if data is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(data).encode()
        request = urllib.request.Request(
            self.origin + path, headers=headers, data=payload, method=method
        )
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body: bytes = response.read()
            if response.status != expected:
                raise RuntimeError(f"{path}: expected {expected}, received {response.status}")
            return body

    def json(self, path: str, expected: int = 200, data: Any = None, **options: Any) -> Any:
        return json.loads(self.request(path, expected, data, **options))

    def stream(self, path: str, data: Any) -> tuple[list[dict[str, Any]], float]:
        started = time.perf_counter()
        body = self.request(path, 200, data)
        lines = [json.loads(line) for line in body.splitlines() if line.strip()]
        return lines, time.perf_counter() - started


def write_override(path: Path, nonce: str, certificates: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "services": {
                    "backend": {
                        "container_name": f"clm-assistant-smoke-backend-{nonce}",
                        "environment": {
                            "APP_ENV": "test",
                            "MONGO_DATABASE": f"clm_test_assistant_{nonce}",
                            "MONGO_URI": None,
                        },
                        "volumes": [f"{certificates / 'mongo.crt'}:/certificates/mongo.crt:ro"],
                        "depends_on": {"mongo": {"condition": "service_healthy"}},
                    },
                    "frontend": {
                        "volumes": [f"{HERE / 'Caddyfile.candidate'}:/etc/caddy/Caddyfile:ro"],
                    },
                    "mongo": {
                        "image": MONGO_IMAGE,
                        "command": [
                            "mongod",
                            "--tlsMode",
                            "requireTLS",
                            "--tlsCertificateKeyFile",
                            "/certificates/mongo.pem",
                            "--tlsCAFile",
                            "/certificates/mongo.crt",
                            "--tlsAllowConnectionsWithoutCertificates",
                        ],
                        "volumes": [f"{certificates}:/certificates:ro"],
                        "tmpfs": ["/data/db", "/data/configdb"],
                        "healthcheck": {
                            "test": [
                                "CMD",
                                "mongosh",
                                "--quiet",
                                "--host",
                                "mongo",
                                "--tls",
                                "--tlsCAFile",
                                "/certificates/mongo.crt",
                                "--eval",
                                "db.runCommand({ping:1})",
                            ],
                            "interval": "2s",
                            "timeout": "5s",
                            "retries": 20,
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def smoke(backend: str, frontend: str, assistant: str, report_path: str | None) -> None:
    nonce = uuid.uuid4().hex[:12]
    credential = secrets.token_urlsafe(24)
    # Fed over stdin, so the credential stays out of command lines and logs.
    password_hash = (
        subprocess.check_output(
            [
                "docker", "run", "--rm", "--network", "none", "-i", backend, "python", "-c",
                "from app.services.authentication import generate_scrypt_password_hash as make; "
                "print(make(input()))",
            ],
            input=credential.encode("ascii"),
        )
        .decode("ascii")
        .strip()
    )  # fmt: skip
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    origin = f"https://localhost:{port}"
    data_volume = f"clm-assistant-smoke-{nonce}"
    backup_volume = f"{data_volume}-backup"
    recovery_volume = f"{data_volume}-recovery"
    report: dict[str, Any] = {"steps": []}

    def passed(step: str) -> None:
        report["steps"].append(step)
        print(f"PASS: {step}", flush=True)

    with tempfile.TemporaryDirectory(prefix="clm-assistant-smoke-") as directory:
        work = Path(directory)
        interpolation = work / "interpolation"
        interpolation.touch()
        certificates = work / "certificates"
        certificates.mkdir()
        subprocess.run(
            [
                "docker", "run", "--rm", "--network", "none",
                "--mount", f"type=bind,source={certificates},target=/certificates",
                "--entrypoint", "sh", MONGO_IMAGE, "-ec",
                "openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj /CN=mongo "
                "-addext subjectAltName=DNS:mongo -keyout /tmp/mongo.key "
                "-out /certificates/mongo.crt 2>/dev/null; "
                "cat /tmp/mongo.key /certificates/mongo.crt > /certificates/mongo.pem",
            ],
            check=True,
        )  # fmt: skip
        runtime = work / "runtime"
        runtime.write_text(
            f"PHASE13_BROWSER_ORIGIN={origin}\n"
            + "".join(f"{key}_PASSWORD_HASH={password_hash}\n" for key in HASH_VARIABLES),
            encoding="utf-8",
        )
        override = work / "smoke.json"
        write_override(override, nonce, certificates)
        env = dict(
            os.environ,
            BACKEND_IMAGE=backend,
            FRONTEND_IMAGE=frontend,
            ASSISTANT_IMAGE=assistant,
            ASSISTANT_CONTAINER_NAME=f"clm-assistant-smoke-{nonce}",
            ASSISTANT_DATA_VOLUME=data_volume,
            ASSISTANT_BROWSER_ORIGIN=origin,
            # RD-1: a well-formed list naming no case of this run; set to the run's case below.
            ASSISTANT_ELIGIBLE_CASE_REFS="000000000000",
            ASSISTANT_ELIGIBLE_CREATED_BEFORE="2099-01-01T00:00:00Z",
            BACKEND_ENV_FILE=str(runtime),
            CLM_SITE="localhost",
            MONGO_URI="mongodb://mongo:27017/?tls=true&tlsCAFile=/certificates/mongo.crt",
            HTTP_BIND="127.0.0.1:",
            HTTPS_BIND=f"127.0.0.1:{port}",
        )
        container = env["ASSISTANT_CONTAINER_NAME"]

        def compose_result(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    "docker", "compose", "--env-file", str(interpolation),
                    "-p", f"clm-assistant-smoke-{nonce}",
                    "-f", str(ROOT / "deploy" / "compose.yml"),
                    "-f", str(HERE / "compose.assistant.yml"),
                    "-f", str(override),
                    *args,
                ],
                env=env,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )  # fmt: skip

        def compose(*args: str) -> str:
            result = compose_result(*args)
            if result.returncode != 0:
                raise RuntimeError(f"compose {args[0]} failed: {result.stdout[-1500:]}")
            return result.stdout

        def inside(code: str) -> str:
            return subprocess.check_output(
                ["docker", "exec", container, "python", "-c", code], text=True
            ).strip()

        def inspect(template: str) -> str:
            return subprocess.check_output(
                ["docker", "inspect", "--format", template, container], text=True
            ).strip()

        def restarts() -> int:
            return int(inspect("{{.RestartCount}}"))

        def wait_healthy(seconds: int = 200) -> None:
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                try:
                    if inspect("{{.State.Health.Status}}") == "healthy":
                        return
                except subprocess.CalledProcessError:
                    pass
                time.sleep(2)
            raise RuntimeError("the assistant did not become healthy")

        def stats() -> dict[str, dict[str, str]]:
            rows = subprocess.check_output(
                ["docker", "stats", "--no-stream", "--format", "{{json .}}"], text=True
            )
            found: dict[str, dict[str, str]] = {}
            for row in rows.splitlines():
                item = json.loads(row)
                if nonce in item["Name"]:
                    name = item["Name"].replace(nonce, "").strip("-_")
                    found[name] = {"cpu": item["CPUPerc"], "memory": item["MemUsage"]}
            return found

        for volume in (data_volume, backup_volume, recovery_volume):
            subprocess.run(
                ["docker", "volume", "create", volume], check=True, stdout=subprocess.DEVNULL
            )
        started = time.perf_counter()
        try:
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "240")
            report["startup_seconds"] = round(time.perf_counter() - started, 1)
            ports = json.loads(inspect("{{json .NetworkSettings.Ports}}"))
            check(not any(ports.values()), "the assistant publishes a port")
            networks = json.loads(inspect("{{json .NetworkSettings.Networks}}"))
            check(
                len(networks) == 1 and next(iter(networks)).endswith("_proxy"),
                "the assistant must join only the internal proxy network",
            )
            check(inspect("{{.Config.User}}") == "10001:10001", "the assistant runs as root")
            check(inspect("{{.HostConfig.ReadonlyRootfs}}") == "true", "root filesystem writable")
            check(inspect("{{.HostConfig.CapDrop}}") == "[ALL]", "capabilities not dropped")
            passed("private container: no port, one internal network, non-root, read-only")

            egress = inside(EGRESS_PROBE)
            report["egress"] = egress
            check(
                all(
                    f"'{name}': 'blocked'" in egress for name in ("internet", "mongo", "public_dns")
                ),
                f"egress: {egress}",
            )
            check("'backend': 'reached'" in egress, f"backend not reachable: {egress}")
            passed("no route to the internet, public DNS or Mongo; backend reachable")

            ready = json.loads(inside(READY_PROBE))
            check(ready["status"] == "ready", f"not ready: {ready}")
            passed("readiness: stores, Chroma, model state and backend all ok")

            root_ca = compose(
                "exec", "-T", "frontend", "cat", "/data/caddy/pki/authorities/local/root.crt"
            )
            context = ssl.create_default_context(cadata=root_ca)

            def signed_in(user: str) -> Browser:
                person = Browser(origin, context)
                reply = person.json(
                    "/api/auth/login", data={"user_id": user, "password": credential}
                )
                person.csrf = reply["csrf_token"]
                return person

            anonymous = Browser(origin, context)
            anonymous.request("/api/assistant/health", 401)
            anonymous.request("/api/assistant/admin/models", 401)
            anonymous.request(f"/api/assistant/cases/{uuid.uuid4()}/brief", 401)
            passed("Caddy refuses every assistant route without a session")

            maya = signed_in("maya-lim")
            ryan = signed_in("ryan-lee")
            hr = signed_in("hr-admin")
            created = maya.json(
                "/api/clm/zero-touch/cases",
                201,
                {"uen": "202400001A", "country_of_incorporation": "SG"},
            )
            case_id = created["case"]["case_id"]
            assistant_case = f"/api/assistant/cases/{case_id}"

            # RD-1: the assistant started with no case of this run on its list, so the new
            # case is refused (another team still gets the backend's 404). The assistant alone
            # is then recreated with this case listed, as an R2.1 cutover changes only it.
            refused = maya.json(assistant_case + "/brief", 403)
            check(
                refused["detail"]["code"] == "ASSISTANT_CASE_NOT_ELIGIBLE",
                f"eligibility: {refused}",
            )
            maya.request(assistant_case + "/chat", 403, {"message": "What is blocking this case?"})
            maya.request("/api/assistant/contexts", 403, {"case_id": case_id})
            ryan.request(assistant_case + "/brief", 404)
            env["ASSISTANT_ELIGIBLE_CASE_REFS"] = hashlib.sha256(case_id.encode()).hexdigest()[:12]
            compose(
                "up", "-d", "--no-build", "--no-deps", "--wait", "--wait-timeout", "240",
                "assistant",
            )  # fmt: skip
            passed("RD-1: an unlisted new case gets 403; listed after an assistant-only recreate")

            health = maya.json("/api/assistant/health")
            check(health["llm_enabled"] is False and health["model"] is None, f"health: {health}")
            brief = maya.json(assistant_case + "/brief")
            check(brief["company"] and brief["message"], "the brief has no case data")
            lines, _ = maya.stream(
                assistant_case + "/chat/stream", {"message": "What is blocking this case?"}
            )
            done = lines[-1]
            check(done["type"] == "done" and done["answered_by"] == "case_data", f"chat: {done}")
            check(done.get("answer"), "the stream carried no answer")
            answer_id = done["answer_id"]
            check(answer_id, "the answer has no record")
            passed("deterministic brief and streamed answer through Caddy with no model")

            ryan.request(assistant_case + "/brief", 404)
            ryan.request(assistant_case + "/chat", 404, {"message": "What is blocking this case?"})
            ryan.request(f"/api/assistant/answers/{answer_id}", 404)
            hr.request(assistant_case + "/brief", 404)
            maya.request(f"/api/assistant/answers/{answer_id}")
            passed("case isolation: another team and HR get a safe 404")

            maya.request(assistant_case + "/chat", 403, {"message": "x"}, origin=None)
            maya.request(
                assistant_case + "/chat",
                403,
                {"message": "x"},
                origin="https://evil.example.test",
            )
            for path in (
                "/api/assistant/internal/ready",
                "/api/assistant/docs",
                "/api/assistant/openapi.json",
                "/api/assistant/%2e%2e/internal/ready",
            ):
                maya.request(path, 404)
            # The body limit, proved at Caddy's boundary: at the limit the body reaches the
            # assistant (its own 422 for the unknown field); one byte over, Caddy answers 413
            # (with a declared length, before any body byte is sent); and the same over-limit
            # body sent straight to the assistant still gets the assistant's 422, so the 413 can
            # only be Caddy's. Every other outcome, error or timeout fails the smoke.
            headers = {
                "Origin": origin,
                "X-CSRF-Token": maya.csrf or "",
                "Cookie": maya.cookie_header(),
                "Content-Type": "application/json",
            }
            chat_path = f"/api/assistant/cases/{case_id}/chat"
            limits: dict[str, Any] = {"limit_bytes": BODY_LIMIT_BYTES}
            for chunked in (False, True):
                mode = "chunked" if chunked else "content_length"
                sent, status, body = capped_post(
                    origin, context, chat_path, headers, padded_body(BODY_LIMIT_BYTES),
                    chunked=chunked,
                )  # fmt: skip
                check(
                    sent and status == 422 and assistant_validation(body),
                    f"{mode} at the limit did not reach the assistant: {status}",
                )
                sent, status, body = capped_post(
                    origin, context, chat_path, headers, padded_body(BODY_LIMIT_BYTES + 1),
                    chunked=chunked,
                )  # fmt: skip
                check(status == 413, f"{mode} one byte over the limit: expected 413, got {status}")
                check(not assistant_validation(body), f"{mode} 413 carried an assistant reply")
                if not chunked:
                    check(not sent, "Caddy asked for an over-limit body instead of refusing it")
                limits[mode] = {"at_limit": 422, "over_limit": 413, "body_sent_over": sent}
            direct = json.loads(
                subprocess.run(
                    ["docker", "exec", "-i", container, "python", "-c", DIRECT_OVERSIZE_PROBE],
                    input=json.dumps(
                        {
                            "path": f"/assistant/cases/{case_id}/chat",
                            "body": padded_body(BODY_LIMIT_BYTES + 1).decode("ascii"),
                            "cookie": maya.cookie_header(),
                            "origin": origin,
                            "csrf": maya.csrf or "",
                        }
                    ),
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout
            )
            check(
                direct["status"] == 422
                and direct["detail"] == {"type": "extra_forbidden", "loc": ["body", "pad"]},
                f"the assistant itself answered an over-limit body with {direct}",
            )
            limits["direct_to_assistant_over_limit"] = direct["status"]
            report["body_limit"] = limits
            passed(
                "origin required, internals unreachable, body limit enforced by Caddy at "
                "512,000 bytes (the assistant itself never answers 413)"
            )

            maya.request("/api/assistant/admin/models", 403)
            overview = hr.json("/api/assistant/admin/models")
            check(overview["configured"] is True, "the model console has no state store")
            hr.request(
                "/api/assistant/admin/models/credential",
                403,
                {"api_key": "sk-or-v1-" + "a" * 40},
                method="PUT",
            )
            events = hr.json("/api/assistant/admin/models/audit")["events"]
            check(any(row["action"] == "HOSTED_ACTION_REFUSED" for row in events), "no audit row")
            check("sk-or-v1" not in json.dumps(events), "a key reached the audit log")
            view = hr.json("/api/assistant/admin/models/credential")
            check(view["status"] == "missing", f"credential: {view}")
            passed("HR console reads state and audit; a provider key is refused unread")

            provider = subprocess.Popen(
                ["docker", "exec", container, "python", "-c", MOCK_PROVIDER]
            )
            try:
                time.sleep(3)
                reply = maya.json(
                    assistant_case + "/chat", data={"message": "What is blocking this case?"}
                )
                check(SCRIPTED_REPLY not in reply["answer"], "unchecked model text reached a user")
                streamed, _ = maya.stream(
                    assistant_case + "/chat/stream", {"message": "What is blocking this case?"}
                )
                check(SCRIPTED_REPLY not in json.dumps(streamed), "unchecked text in a stream")
                calls = int(inside(MOCK_CALLS))
                check(calls >= 2, f"the mock provider was not reached: {calls}")
                report["mock_provider"] = {
                    "calls": calls,
                    "answered_by": reply["answered_by"],
                    "notice": reply["notice"],
                    "checks": reply["checks"],
                }
            finally:
                inside(STOP_MOCK_PROVIDER)
                provider.wait(timeout=10)
            passed("mock provider: a claim outside the guardrails never reached the user")

            def one_chat(index: int) -> float:
                _, seconds = maya.stream(
                    assistant_case + "/chat/stream",
                    {"message": f"What should I do next on item {index % 5}?"},
                )
                return seconds

            report["idle"] = stats()
            report["single_answer_seconds"] = [round(one_chat(item), 3) for item in range(5)]
            samples: list[dict[str, dict[str, str]]] = []
            stop = threading.Event()

            def sample() -> None:
                while not stop.is_set():
                    samples.append(stats())

            sampler = threading.Thread(target=sample, daemon=True)
            sampler.start()
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                timings = sorted(pool.map(one_chat, range(120)))
            stop.set()
            sampler.join(timeout=15)
            report["load"] = {
                "requests": len(timings),
                "concurrency": 8,
                "p50_seconds": round(statistics.median(timings), 3),
                "p95_seconds": round(timings[int(len(timings) * 0.95) - 1], 3),
                "max_seconds": round(timings[-1], 3),
                "sample_count": len(samples),
                "peak_memory": peak_memory(samples),
                "peak_cpu": peak_cpu(samples),
            }
            report["data_bytes"] = int(inside(DATA_PROBE))
            check(restarts() == 0, "the assistant restarted under load")
            passed("load: 120 streamed answers at concurrency 8 inside the limits")

            compose("restart", "assistant")
            wait_healthy()
            maya.request(f"/api/assistant/answers/{answer_id}")
            check("'guidance_added': 0" in compose("logs", "assistant"), "guidance loaded twice")
            passed("restart: answer record and knowledge kept, guidance not duplicated")

            before = restarts()
            subprocess.run(
                [
                    "docker", "exec", container, "python", "-c",
                    KILL_WORKER.format(signal=SIGKILL),
                ],
                check=False,
            )  # fmt: skip
            time.sleep(5)
            wait_healthy()
            check(restarts() > before, "the crash did not restart the service")
            maya.request(f"/api/assistant/answers/{answer_id}")
            passed("crash: killed worker restarted by policy, stores intact")

            before = restarts()
            subprocess.run(
                [
                    "docker", "exec", container, "python", "-c",
                    KILL_WORKER.format(signal=SIGSTOP),
                ],
                check=True,
            )  # fmt: skip
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline and restarts() == before:
                time.sleep(5)
            check(restarts() > before, "the hung worker was not recovered")
            wait_healthy()
            maya.request(f"/api/assistant/answers/{answer_id}")
            passed("hang: stopped worker detected by the probe and restarted")

            second = subprocess.run(
                ["docker", "exec", container, "python", "-m", "assistant_hosting.run"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            check(
                second.returncode == 75 and "DATA_ROOT_IN_USE" in second.stdout,
                f"a second writer started: {second.returncode}",
            )
            passed("a second writer on the same data root is refused")

            compose("stop", "assistant")
            body = maya.request("/api/assistant/health", 503)
            check(b"Assistant service is unavailable" in body, "unexpected outage reply")
            maya.request(f"/api/clm/zero-touch/cases/{case_id}")
            passed("outage: fixed 503 from Caddy and onboarding keeps working")

            def one_off(*command: str, restore_to: str = "") -> str:
                mounts = ["-v", f"{backup_volume}:/backup"]
                if restore_to:
                    mounts += ["-v", f"{restore_to}:/restore"]
                return compose(
                    "run", "--rm", "--no-deps", "-T", "--user", "0:0", *mounts,
                    "--name", f"{container}-{uuid.uuid4().hex[:6]}",
                    "assistant", "python", "-m", "assistant_hosting.backup", *command,
                )  # fmt: skip

            one_off("create", "/data", "/backup/first")
            verified = one_off("verify", "/backup/first")
            check("VERIFIED" in verified, "the backup did not verify")
            report["backup"] = verified.strip().splitlines()[-1]
            restored = one_off("restore", "/backup/first", "/restore", restore_to=recovery_volume)
            check("RESTORED" in restored, f"restore failed: {restored[-300:]}")
            subprocess.run(
                [
                    "docker", "run", "--rm", "--network", "none", "--user", "0:0",
                    "-v", f"{recovery_volume}:/restore", "--entrypoint", "chown", assistant,
                    "-R", "10001:10001", "/restore",
                ],
                check=True,
            )  # fmt: skip
            env["ASSISTANT_DATA_VOLUME"] = recovery_volume
            compose("up", "-d", "--no-build", "--no-deps", "--force-recreate", "assistant")
            time.sleep(3)
            wait_healthy()
            maya.request(f"/api/assistant/answers/{answer_id}")
            check(hr.json("/api/assistant/admin/models/audit")["events"], "audit not restored")
            passed("recovery: backup restored to a new volume and the service came back on it")
            report["duration_seconds"] = round(time.perf_counter() - started, 1)
            print("Stage A hosted smoke passed", flush=True)
        except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
            report["failure"] = str(error)
            print(f"FAIL: {error}", flush=True)
            print(compose_result("logs", "--tail", "25", "assistant").stdout, flush=True)
            raise
        finally:
            if report_path:
                Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
            compose_result("down", "--volumes")
            for volume in (data_volume, backup_volume, recovery_volume):
                subprocess.run(
                    ["docker", "volume", "rm", "-f", volume],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )


if __name__ == "__main__":
    prefer_ipv4()
    smoke(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
