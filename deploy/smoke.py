"""Smoke the release pair with a dedicated Docker network and disposable MongoDB."""

import http.cookiejar
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MONGO_IMAGE = "mongo:7"


def expected_versions(summary):
    return {
        "expected_automation_version": summary["version"],
        "expected_case_event_count": len(summary["case"]["events"]),
    }


def smoke(backend, frontend):
    nonce = uuid.uuid4().hex
    credential = secrets.token_urlsafe(24)
    # Feed the transient credential over stdin, without command-line or log exposure.
    password_hash = subprocess.check_output(
        ["docker", "run", "--rm", "--network", "none", "-i", backend, "python", "-c",
         ("from app.services.authentication import generate_scrypt_password_hash as make; "
          "print(make(input()))")],
        input=credential.encode("ascii"),
    ).decode("ascii").strip()
    with socket.socket() as port_reservation:
        port_reservation.bind(("127.0.0.1", 0))
        port = port_reservation.getsockname()[1]
    origin = f"https://localhost:{port}"
    with tempfile.TemporaryDirectory(prefix="clm-release-smoke-") as directory:
        work = Path(directory)
        interpolation = work / "interpolation"
        interpolation.touch()
        certificates = work / "certificates"
        certificates.mkdir()
        subprocess.run(
            ["docker", "run", "--rm", "--network", "none",
             "--mount", f"type=bind,source={certificates},target=/certificates",
             "--entrypoint", "sh", MONGO_IMAGE, "-ec",
             ("openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj /CN=mongo "
             "-addext subjectAltName=DNS:mongo -keyout /tmp/mongo.key -out /certificates/mongo.crt "
             "2>/dev/null; cat /tmp/mongo.key /certificates/mongo.crt > /certificates/mongo.pem")],
            check=True,
        )
        runtime = work / "runtime"
        runtime.write_text(
            f"PHASE13_BROWSER_ORIGIN={origin}\n"
            + "".join(f"{key}_PASSWORD_HASH={password_hash}\n" for key in (
                "PHASE13_MAYA_LIM", "PHASE13_ETHAN_TAN", "PHASE13_SOPHIA_NG",
                "PHASE13_RYAN_LEE", "PHASE13_OLIVIA_KOH", "PHASE14_5_HR_ADMIN",
                "PHASE13_SUPPORT_USER",
            ))
            + "ACRA_CONNECTOR_MODE=mock\nGOLDTIER_CONNECTOR_MODE=mock\n",
            encoding="utf-8",
        )
        override = work / "smoke.json"
        override.write_text(json.dumps({
            "services": {
                "backend": {
                    "container_name": f"clm-smoke-backend-{nonce}",
                    "environment": {
                        "APP_ENV": "test",
                        "MONGO_DATABASE": f"clm_test_release_{nonce}",
                        "MONGO_URI": None,
                    },
                    "volumes": [f"{certificates / 'mongo.crt'}:/certificates/mongo.crt:ro"],
                    "depends_on": {"mongo": {"condition": "service_healthy"}},
                },
                "mongo": {
                    "image": MONGO_IMAGE,
                    "command": ["mongod", "--tlsMode", "requireTLS",
                                "--tlsCertificateKeyFile", "/certificates/mongo.pem",
                                "--tlsCAFile", "/certificates/mongo.crt",
                                "--tlsAllowConnectionsWithoutCertificates"],
                    "volumes": [f"{certificates}:/certificates:ro"],
                    "tmpfs": ["/data/db", "/data/configdb"],
                    "healthcheck": {
                        "test": ["CMD", "mongosh", "--quiet", "--host", "mongo", "--tls",
                                 "--tlsCAFile", "/certificates/mongo.crt", "--eval", "db.runCommand({ping:1})"],
                        "interval": "2s", "timeout": "5s", "retries": 20,
                    },
                },
            },
        }), encoding="utf-8")
        env = dict(os.environ, BACKEND_IMAGE=backend, FRONTEND_IMAGE=frontend,
                   BACKEND_ENV_FILE=str(runtime), CLM_SITE="localhost",
                   MONGO_URI="mongodb://mongo:27017/?tls=true&tlsCAFile=/certificates/mongo.crt",
                   HTTP_BIND="127.0.0.1:", HTTPS_BIND=f"127.0.0.1:{port}")

        def compose(*args, capture=False):
            return subprocess.run(
                ["docker", "compose", "--env-file", str(interpolation),
                 "-p", f"clm-release-smoke-{nonce}", "-f", str(ROOT / "compose.yml"),
                 "-f", str(override), *args], env=env, check=True, text=True,
                stdout=subprocess.PIPE if capture else None,
            ).stdout

        try:
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "120")
            root_ca = compose("exec", "-T", "frontend", "cat",
                              "/data/caddy/pki/authorities/local/root.crt", capture=True)
            context = ssl.create_default_context(cadata=root_ca)
            client = urllib.request.build_opener(
                urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context),
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            )

            def request(path, expected=200, data=None, csrf=None, *, method=None, upload=None):
                headers = {"Origin": origin}
                if data is not None:
                    headers["Content-Type"] = "application/json"
                if csrf is not None:
                    headers["X-CSRF-Token"] = csrf
                payload = json.dumps(data).encode() if data is not None else None
                if upload is not None:
                    headers["Content-Type"] = "application/pdf"
                    headers["X-Document-Name"] = upload.name
                    payload = upload.read_bytes()
                req = urllib.request.Request(origin + path, headers=headers, data=payload, method=method)
                try:
                    response = client.open(req, timeout=10)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    if response.status != expected:
                        raise RuntimeError(f"{path}: expected {expected}, received {response.status}")
                    return response.headers, response.read()

            def login():
                headers, body = request("/api/auth/login", data={
                    "user_id": "maya-lim", "password": credential,
                })
                cookie = headers["Set-Cookie"].lower()
                if not all(attribute in cookie for attribute in ("; secure", "; httponly", "path=/api")):
                    raise RuntimeError("Missing expected session cookie attributes")
                return json.loads(body)["csrf_token"]

            _, html = request("/cases/synthetic-deep-link")
            if b'id="root"' not in html:
                raise RuntimeError("Missing SPA fallback")
            _, health = request("/health")
            if json.loads(health)["environment"] != "test":
                raise RuntimeError("Wrong backend profile")
            csrf = login()
            cases = "/api/clm/zero-touch/cases"
            case = {"uen": "202400001A", "country_of_incorporation": "SG"}
            request(cases, 403, data=case)
            _, body = request(cases, 201, data=case, csrf=csrf)
            case_path = f"{cases}/{json.loads(body)['case']['case_id']}"
            created = json.loads(body)
            document_path = f"/api/onboarding/cases/{created['case']['case_id']}/documents"
            request("/api/workflows/startable")
            _, body = request(case_path + "/workflows")
            if json.loads(body) != {"onboarding": None, "runs": []}:
                raise RuntimeError("Unexpected workflow activation on a fresh case")
            request("/api/assistant/health", 503)
            request(case_path + "/target-classification", method="PUT", csrf=csrf, data={
                "kyc_customer_type": "Company - Private",
                "client_segment": "Corporate",
                **expected_versions(created),
            })
            fixture = ROOT.parent / "apps/backend/tests/fixtures/uat/legal-name-mismatch.pdf"
            request(case_path + "/intake/documents", 201, csrf=csrf, upload=fixture)
            _, body = request(case_path + "/intake/complete", csrf=csrf, data={"expected_document_count": 1})
            current = json.loads(body)
            _, body = request(document_path)
            documents = json.loads(body)
            if len(documents) != 1 or not documents[0]["fields"]:
                raise RuntimeError("IDP did not retain extracted fields")
            print("PASS: authorised RM, case creation, workflow availability and PDF extraction", flush=True)
            discrepancies = current["reconciliation"]["discrepancies"]
            choices = [
                {"discrepancy_id": item["discrepancy_id"], "action": "KEEP_REGISTRY_VALUE",
                 "evidence_fingerprint": item["evidence_fingerprint"]}
                for item in discrepancies if item["status"] == "OPEN"
            ]
            if not choices:
                raise RuntimeError("Expected a document versus registry exception")
            _, body = request(case_path + "/review-decisions", csrf=csrf, data={
                **expected_versions(current),
                "expected_reconciliation_version": current["reconciliation"]["version"],
                "reconciliation": choices,
            })
            current = json.loads(body)
            _, body = request(document_path.removesuffix("/documents") + "/ownership")
            ownership = json.loads(body)
            if ownership["state"] != "ANALYZED" or not ownership["relationships"] or not ownership["candidates"]:
                raise RuntimeError("Missing ownership graph or UBO candidates")
            blockers = {item["blocker_code"] for item in current["active_exceptions"]}
            if blockers != {"TARGET_CONFIRMATION_REQUIRED"}:
                raise RuntimeError(f"Unexpected review blockers: {sorted(blockers)}")
            if current["case"]["goldtier_result"] is not None:
                raise RuntimeError("GoldTier result exists before RM confirmation")
            print("PASS: registry reconciliation, related parties, ownership and UBO review", flush=True)
            _, body = request(case_path + "/target-confirmation", csrf=csrf, data={
                **expected_versions(current), "expected_clm_version": current["clm"]["version"],
            })
            completed = json.loads(body)
            if completed["status"] != "COMPLETED" or not completed["case"]["goldtier_result"]:
                raise RuntimeError("Mock dispatch did not complete")
            print("PASS: Review & Send and Mock GoldTier", flush=True)
            compose("exec", "-T", "backend", "tesseract", "--list-langs")
            original_writer = compose("ps", "--status", "running", "-q", "backend", capture=True).split()
            if len(original_writer) != 1:
                raise RuntimeError("Expected one backend writer before replacement")
            compose("stop", "frontend")
            compose("stop", "backend")
            if compose("ps", "--status", "running", "-q", "backend", capture=True).strip():
                raise RuntimeError("Old backend writer did not stop")
            compose("rm", "--force", "backend")
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "120")
            new_writer = compose("ps", "--status", "running", "-q", "backend", capture=True).split()
            if len(new_writer) != 1 or new_writer == original_writer:
                raise RuntimeError("Expected one new backend writer")
            request("/api/auth/me", 401)
            login()
            _, body = request(case_path)
            persisted = json.loads(body)
            if (
                persisted["status"] != "COMPLETED"
                or persisted["case"]["goldtier_result"] != completed["case"]["goldtier_result"]
                or persisted["target_operations"] != completed["target_operations"]
            ):
                raise RuntimeError("Completed case and target ledger changed after replacement")
            print("PASS: durable completed case and unchanged target ledger after restart", flush=True)
            csrf = login()
            _, body = request(cases, 201, csrf=csrf, data={
                "uen": "209990101A", "country_of_incorporation": "SG",
            })
            ocr_case = json.loads(body)["case"]["case_id"]
            scan = fixture.parent / "zero-touch-database/demo-alpha-scanned.pdf"
            _, body = request(f"{cases}/{ocr_case}/intake/documents", 201, csrf=csrf, upload=scan)
            extracted = json.loads(body)
            if not any(page["extraction_method"] == "LOCAL_TESSERACT_OCR" for page in extracted["pages"]):
                raise RuntimeError("Scanned PDF did not use local OCR")
            if not any(field["original_extracted_value"] for field in extracted["fields"]):
                raise RuntimeError("OCR returned no extracted values")
            print("PASS: scanned PDF produced extracted values via local Tesseract", flush=True)
            print("Local HTTPS and Mongo TLS demo smoke passed", flush=True)
        except subprocess.CalledProcessError:
            compose("logs", "--tail", "12", "mongo")
            raise
        finally:
            compose("down", "--volumes")


if __name__ == "__main__":
    smoke(*sys.argv[1:])
