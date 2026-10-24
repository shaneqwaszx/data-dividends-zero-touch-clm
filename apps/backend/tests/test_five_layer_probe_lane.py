"""Offline check of the owner-run bounded five-layer Marketplace Mock probe lane.

The allowlisted in-process transport stands in for the provider, so these tests verify
how the tool derives its labels from recorded receipts; they observe nothing live.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from scripts import phase24_acra_mock_discovery as probe
from scripts.five_layer_hybrid_fixture import OfflineFiveLayerProtocolTransport

from app.connectors.acra_api_marketplace_auth import HttpxAcraMarketplaceTokenTransport
from app.connectors.acra_sandbox import HttpxAcraTransport

SECRETS = ("synthetic-offline-client", "synthetic-offline-key")


def run_lane(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    offline: OfflineFiveLayerProtocolTransport,
    get: Callable[..., Any] | None = None,
    lane: str = "five-layer-hybrid",
) -> tuple[dict[str, Any], str]:
    def offline_get(_self: Any, url: str, *, headers: Any, timeout_seconds: float) -> Any:
        return offline.get(url, headers=headers, timeout_seconds=timeout_seconds)

    def offline_post(_self: Any, url: str, **kwargs: Any) -> Any:
        return offline.post(url, **kwargs)

    monkeypatch.setattr(HttpxAcraTransport, "get", get or offline_get)
    monkeypatch.setattr(HttpxAcraMarketplaceTokenTransport, "post", offline_post)
    for name in ("ACRA_API_MARKETPLACE_MOCK_CLIENT_ID", "ACRA_API_MARKETPLACE_MOCK_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / "probe.env"
    env.write_text(
        f"ACRA_API_MARKETPLACE_MOCK_CLIENT_ID={SECRETS[0]}\n"
        f"ACRA_API_MARKETPLACE_MOCK_SECRET_KEY={SECRETS[1]}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["probe", "--config-env-path", str(env), "--lane", lane])
    assert probe.main() == 0
    output = capsys.readouterr().out
    for secret in (*SECRETS, offline._token):
        assert secret not in output
    return json.loads(output), output


def reads(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in result["receipts"]
        if item["classification"] == "OFFICIAL_ACRA_MARKETPLACE_MOCK_READ"
    ]


def test_five_layer_lane_is_bounded_sanitized_and_never_promotes_unbound_shareholders(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    offline = OfflineFiveLayerProtocolTransport()
    offline.profiles["200811111M"] = {
        "entities": [
            {
                "uen": "200811111M",
                "name": "OFFLINE COMPANY (SYNTHETIC)",
                "entityConstnDetailsAndType": {"constitution": "PRIVATE COMPANY LIMITED BY SHARES"},
            }
        ]
    }
    result, _ = run_lane(monkeypatch, tmp_path, capsys, offline)
    # Derived from recorded HTTP 200 data reads (here supplied by the offline stand-in).
    assert result["evidence_class"] == "MOCK_INTEROPERABILITY_OBSERVED"
    samples = {item["uen"]: item for item in result["samples"]}
    assert len(samples) == 8
    assert (samples["201511222D"]["identity"], samples["201511222D"]["legal_form"]) == (
        "SAME_UEN_VERIFIED",
        "OTHER",
    )
    assert samples["201511222D"]["ownership"] == "COMPANY_SHAREHOLDERS_NOT_APPLICABLE"
    assert samples["111111111K"]["identity"] == "EMPTY"
    sim_lim = samples["111111111M"]
    assert (sim_lim["identity"], sim_lim["diagnostic_shareholders"]) == (
        "EMPTY",
        "UNBOUND_NOT_CANONICAL",
    )
    assert samples["200811111M"]["legal_form"] == "COMPANY"
    assert samples["200811111M"]["ownership_party_count"] == 0
    assert all(item["derived_percentage"] is False for item in samples.values())
    # 8 entity reads + Garden embedded officers + SIM LIM diagnostic + one COMPANY
    # shareholder read; within the 24-GET ceiling and the lane's 16-read bound.
    assert len(reads(result)) == 11 and result["actual_call_count"] == 12
    assert offline.token_requests == 1


def test_token_rejection_is_reported_as_authentication_failure_with_zero_reads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    offline = OfflineFiveLayerProtocolTransport(token_status=401)
    result, _ = run_lane(monkeypatch, tmp_path, capsys, offline)
    assert result["evidence_class"] == "AUTHENTICATION_FAILED"
    assert reads(result) == [] and offline.get_count == 0
    assert result["samples"][0]["result"] == "UNAVAILABLE_OR_CONTRACT_REJECTED"


def test_transport_failure_is_never_labelled_as_observed_interoperability(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def unreachable(_self: Any, url: str, *, headers: Any, timeout_seconds: float) -> Any:
        raise httpx.ConnectError("synthetic offline outage")

    result, _ = run_lane(
        monkeypatch, tmp_path, capsys, OfflineFiveLayerProtocolTransport(), get=unreachable
    )
    assert result["evidence_class"] == "TRANSPORT_FAILURE"
    assert [item.get("transport") for item in reads(result)] == ["UNAVAILABLE"]
    assert not any(item.get("http_status") == 200 for item in reads(result))


def test_failed_or_absent_reads_never_claim_interoperability_and_label_is_lane_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert probe.evidence_class([]) == "NO_SUCCESSFUL_READ"
    assert (
        probe.evidence_class(
            [{"classification": "OFFICIAL_ACRA_MARKETPLACE_MOCK_READ", "http_status": 429}]
        )
        == "NO_SUCCESSFUL_READ"
    )
    # Pre-existing lanes keep main's output shape: no evidence_class key at all.
    result, _ = run_lane(
        monkeypatch, tmp_path, capsys, OfflineFiveLayerProtocolTransport(), lane="garden-normalized"
    )
    assert "evidence_class" not in result
