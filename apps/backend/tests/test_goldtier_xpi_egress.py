"""D-127 E1: GoldTier Sandbox egress through the R3 proxy (G2 tests B-1 to B-7).

Synthetic values only. No test reaches a real network: the proxy is a local socket server on
127.0.0.1 and every GoldTier name is a reserved `.invalid` name.
"""

from __future__ import annotations

import socket
import ssl
import threading
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import certifi
import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app import composition
from app.config import Settings
from app.connectors import goldtier_xpi
from app.connectors.goldtier_models import GoldTierRequestMetadata
from app.connectors.goldtier_xpi import (
    GoldTierMutationOutcomeUncertainError,
    GoldTierXpiSandboxConnection,
    GoldTierXpiSandboxConnector,
    GoldTierXpiServiceUnavailableError,
    GoldTierXpiTimeoutError,
    HttpxGoldTierXpiTransport,
    goldtier_tls_context,
)
from app.connectors.goldtier_xpi_models import XpiCreateCustomerRequest, XpiCustomerSearchRequest

FQDN = "goldtier.r3-test.invalid"
PROXY = "http://clm-goldtier-egress:4750"
ORIGIN = "https://clm.r3-test.invalid"
APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def _staging(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "staging",
        "clm_persistence_mode": "mongo",
        "mongo_uri": "mongodb://127.0.0.1:1/?tls=true",
        "mongo_database": "clm_staging",
        "phase13_browser_origin": ORIGIN,
        "idp_connector_mode": "mock",
        "goldtier_connector_mode": "sandbox",
        "goldtier_sandbox_base_url": f"https://{FQDN}",
        "goldtier_sandbox_environment": "synthetic",
        "goldtier_sandbox_user_id": "synthetic-user",
        "goldtier_sandbox_egress_proxy_url": PROXY,
        "goldtier_sandbox_egress_fqdn": FQDN,
    }
    return Settings(_env_file=None, **(values | overrides))  # type: ignore[arg-type]


def _metadata() -> GoldTierRequestMetadata:
    return GoldTierRequestMetadata(
        correlation_id=UUID("00000000-0000-4000-8000-0000000d1270"),
        source_case_id="R3-EGRESS-TEST",
        idempotency_key=UUID("00000000-0000-4000-8000-0000000d1271"),
    )


def _connector(
    transport: HttpxGoldTierXpiTransport, *, writes: bool = False
) -> GoldTierXpiSandboxConnector:
    return GoldTierXpiSandboxConnector(
        connection=GoldTierXpiSandboxConnection(
            base_url=f"https://{FQDN}",
            environment="synthetic",
            user_id=SecretStr("synthetic-user"),
            timeout_seconds=2.0,
            allow_writes=writes,
        ),
        transport=transport,
    )


def _record_clients(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    created: list[dict[str, object]] = []
    real = httpx.Client

    def factory(**kwargs: object) -> httpx.Client:
        created.append(kwargs)
        return real(transport=httpx.MockTransport(lambda _r: httpx.Response(200, json=[])))

    monkeypatch.setattr(goldtier_xpi.httpx, "Client", factory)
    return created


# --- B-1: the proxy URL reaches the GoldTier client only ------------------------------------------


def test_b1_proxy_url_is_passed_to_the_goldtier_client(monkeypatch: pytest.MonkeyPatch) -> None:
    created = _record_clients(monkeypatch)
    _connector(HttpxGoldTierXpiTransport(proxy_url=PROXY)).search_party(
        XpiCustomerSearchRequest(goldtier_id="900001"), _metadata()
    )
    assert created[0]["proxy"] == PROXY
    assert created[0]["trust_env"] is False
    assert created[0]["follow_redirects"] is False


def test_b1_composition_wires_the_configured_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, object]] = []

    class Recorder(HttpxGoldTierXpiTransport):
        def __init__(self, **kwargs: object) -> None:
            seen.append(kwargs)
            super().__init__(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(composition, "HttpxGoldTierXpiTransport", Recorder)
    settings = Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="sandbox",
        goldtier_sandbox_base_url=f"https://{FQDN}",
        goldtier_sandbox_environment="synthetic",
        goldtier_sandbox_user_id=SecretStr("synthetic-user"),
        goldtier_sandbox_egress_proxy_url=PROXY,
        goldtier_sandbox_egress_fqdn=FQDN,
        goldtier_sandbox_tls_ca_file=certifi.where(),
    )
    composition.build_onboarding_service(settings=settings)
    assert seen == [{"proxy_url": PROXY, "ca_file": certifi.where()}]


def test_b1_and_b7_egress_settings_are_read_only_by_the_goldtier_path() -> None:
    readers = sorted(
        str(path.relative_to(APP_ROOT)).replace("\\", "/")
        for path in APP_ROOT.rglob("*.py")
        if "goldtier_sandbox_egress_" in path.read_text(encoding="utf-8")
        or "goldtier_sandbox_tls_ca_file" in path.read_text(encoding="utf-8")
    )
    assert readers == ["composition.py", "config.py"]
    acra = [p for p in (APP_ROOT / "connectors").glob("acra*.py")]
    assert acra and all("proxy" not in p.read_text(encoding="utf-8").lower() for p in acra)


# --- B-2: hostile environment is ignored ----------------------------------------------------------

HOSTILE_ENV = {
    "HTTP_PROXY": "http://10.0.0.66:3128",
    "HTTPS_PROXY": "http://10.0.0.66:3128",
    "ALL_PROXY": "socks5://10.0.0.66:1080",
    "NO_PROXY": "*",
    "SSL_CERT_FILE": "/nonexistent/hostile-ca.pem",
    "SSL_CERT_DIR": "/nonexistent/hostile-ca-dir",
}


def test_b2_hostile_proxy_and_tls_environment_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in HOSTILE_ENV.items():
        monkeypatch.setenv(key, value)
    created = _record_clients(monkeypatch)
    _connector(HttpxGoldTierXpiTransport()).search_party(
        XpiCustomerSearchRequest(goldtier_id="900001"), _metadata()
    )
    assert created[0]["trust_env"] is False
    assert created[0]["proxy"] is None
    context = created[0]["verify"]
    assert isinstance(context, ssl.SSLContext)
    assert context.minimum_version == context.maximum_version == ssl.TLSVersion.TLSv1_3


def test_b2_trust_store_is_explicit_and_never_from_openssl_default_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", "/nonexistent/hostile-ca.pem")
    monkeypatch.setenv("SSL_CERT_DIR", "/nonexistent/hostile-ca-dir")

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the environment-sensitive default trust loader was called")

    monkeypatch.setattr(ssl.SSLContext, "set_default_verify_paths", forbidden)
    monkeypatch.setattr(ssl.SSLContext, "load_default_certs", forbidden)
    default = goldtier_tls_context()
    reference = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    reference.load_verify_locations(cafile=certifi.where())
    assert default.cert_store_stats() == reference.cert_store_stats()
    assert default.cert_store_stats()["x509_ca"] > 0


# --- B-3: TLS verification can never be disabled --------------------------------------------------


@pytest.mark.parametrize("ca_file", [None, certifi.where()])
def test_b3_tls_context_always_verifies(ca_file: str | None) -> None:
    context = goldtier_tls_context(ca_file)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version == context.maximum_version == ssl.TLSVersion.TLSv1_3


def test_b3_explicit_ca_file_replaces_rather_than_extends_the_bundle(tmp_path: Path) -> None:
    single = tmp_path / "one-ca.pem"
    bundle = Path(certifi.where()).read_text(encoding="ascii")
    first = bundle[bundle.index(ssl.PEM_HEADER) :]
    end = first.index(ssl.PEM_FOOTER) + len(ssl.PEM_FOOTER)
    single.write_text(first[:end] + "\n", encoding="ascii")
    assert goldtier_tls_context(str(single)).cert_store_stats()["x509_ca"] == 1


# --- B-4: unsafe egress configuration refuses to start --------------------------------------------


def test_b4_complete_staging_egress_configuration_starts() -> None:
    settings = _staging()
    assert settings.goldtier_sandbox_egress_fqdn == FQDN
    assert (
        _staging(goldtier_sandbox_base_url=f"https://{FQDN}:443/").goldtier_sandbox_egress_fqdn
        == FQDN
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"goldtier_sandbox_egress_proxy_url": ""},
        {"goldtier_sandbox_egress_fqdn": ""},
        {"goldtier_sandbox_egress_proxy_url": "https://clm-goldtier-egress:4750"},
        {"goldtier_sandbox_egress_proxy_url": "http://clm-goldtier-egress"},
        {"goldtier_sandbox_egress_proxy_url": "http://user:pw@clm-goldtier-egress:4750"},
        {"goldtier_sandbox_egress_proxy_url": "http://clm-goldtier-egress:4750/path"},
        {"goldtier_sandbox_egress_proxy_url": "http://clm-goldtier-egress:4750?x=1"},
        {"goldtier_sandbox_egress_proxy_url": "http://clm-goldtier-egress:4750#f"},
        {"goldtier_sandbox_egress_proxy_url": "http://CLM-GOLDTIER-EGRESS:4750"},
        {"goldtier_sandbox_egress_proxy_url": "http://clm-goldtier-egress:99999"},
        {"goldtier_sandbox_egress_fqdn": "GOLDTIER.r3-test.invalid"},
        {"goldtier_sandbox_egress_fqdn": f"{FQDN}."},
        {"goldtier_sandbox_egress_fqdn": "34.120.0.10"},
        {"goldtier_sandbox_egress_fqdn": "other.r3-test.invalid"},
        {"goldtier_sandbox_base_url": "https://other.r3-test.invalid"},
        {"goldtier_sandbox_base_url": f"https://{FQDN}:8443"},
        {"goldtier_sandbox_tls_ca_file": "relative/ca.pem"},
    ],
)
def test_b4_unsafe_staging_egress_refuses_to_start(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        _staging(**overrides)


def test_b4_write_refusal_is_still_evaluated_first() -> None:
    with pytest.raises(ValidationError, match="staging does not permit GoldTier sandbox writes"):
        _staging(goldtier_sandbox_allow_writes=True, goldtier_sandbox_egress_proxy_url="")


@pytest.mark.parametrize(
    "overrides",
    [{"goldtier_sandbox_egress_fqdn": ""}, {"goldtier_sandbox_egress_proxy_url": ""}],
)
def test_b4_half_configured_local_egress_refuses_to_start(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            app_env="test",
            goldtier_connector_mode="sandbox",
            goldtier_sandbox_base_url=f"https://{FQDN}",
            goldtier_sandbox_environment="synthetic",
            goldtier_sandbox_user_id=SecretStr("synthetic-user"),
            **(
                {"goldtier_sandbox_egress_proxy_url": PROXY, "goldtier_sandbox_egress_fqdn": FQDN}
                | overrides
            ),
        )


# --- B-5: proxy failure is controlled, and only the proxy is ever contacted -----------------------


class _Proxy:
    """A local stand-in for the egress proxy answering every CONNECT with a fixed status."""

    def __init__(self, status: bytes | None) -> None:
        self.status = status
        self.requests: list[bytes] = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                head = b""
                while b"\r\n\r\n" not in head:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    head += chunk
                self.requests.append(head.split(b"\r\n", 1)[0])
                if self.status is not None:
                    conn.sendall(b"HTTP/1.1 " + self.status + b"\r\nContent-Length: 0\r\n\r\n")


@pytest.fixture()
def contacts(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    seen: list[str] = []
    real_getaddrinfo = socket.getaddrinfo

    def spy(host: object, *args: object, **kwargs: object) -> object:
        seen.append(str(host))
        return real_getaddrinfo(host, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(socket, "getaddrinfo", spy)
    yield seen


@pytest.mark.parametrize("status", [b"403 Forbidden", b"503 Service Unavailable", b"407 Denied"])
def test_b5_proxy_refusal_is_a_controlled_unavailable(status: bytes, contacts: list[str]) -> None:
    proxy = _Proxy(status)
    transport = HttpxGoldTierXpiTransport(proxy_url=f"http://127.0.0.1:{proxy.port}")
    with pytest.raises(GoldTierXpiServiceUnavailableError) as caught:
        _connector(transport).search_party(
            XpiCustomerSearchRequest(goldtier_id="900001"), _metadata()
        )
    assert "synthetic-user" not in str(caught.value)
    assert proxy.requests == [f"CONNECT {FQDN}:443 HTTP/1.1".encode()]
    assert FQDN not in contacts
    assert set(contacts) <= {"127.0.0.1"}


def test_b5_unreachable_proxy_is_a_controlled_failure(contacts: list[str]) -> None:
    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    port = closed.getsockname()[1]
    closed.close()
    transport = HttpxGoldTierXpiTransport(proxy_url=f"http://127.0.0.1:{port}")
    # A refused connect is "unavailable"; on platforms that retry a refused SYN it is a timeout.
    with pytest.raises((GoldTierXpiServiceUnavailableError, GoldTierXpiTimeoutError)):
        _connector(transport).search_party(
            XpiCustomerSearchRequest(goldtier_id="900001"), _metadata()
        )
    assert FQDN not in contacts


def test_b5_mutation_through_a_failing_proxy_is_uncertain_not_replayed(contacts: list[str]) -> None:
    proxy = _Proxy(b"403 Forbidden")
    transport = HttpxGoldTierXpiTransport(proxy_url=f"http://127.0.0.1:{proxy.port}")
    request = XpiCreateCustomerRequest.model_construct()
    with pytest.raises(GoldTierMutationOutcomeUncertainError):
        _connector(transport, writes=True).create_shell_customer(request, _metadata())
    assert len(proxy.requests) == 1
    assert FQDN not in contacts


# --- B-6: Mock ignores egress settings entirely ---------------------------------------------------


def test_b6_mock_mode_builds_no_sandbox_client(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(**_kwargs: object) -> None:
        raise AssertionError("a GoldTier Sandbox transport was built in Mock mode")

    monkeypatch.setattr(composition, "HttpxGoldTierXpiTransport", refuse)
    settings = Settings(
        _env_file=None,
        app_env="test",
        goldtier_connector_mode="mock",
        goldtier_sandbox_egress_proxy_url="not a url",
        goldtier_sandbox_egress_fqdn="NOT VALID",
    )
    service = composition.build_onboarding_service(settings=settings)
    assert service is not None
