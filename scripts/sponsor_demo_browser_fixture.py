"""Explicit offline browser fixture; never imported by normal application startup."""

import secrets
from datetime import UTC, datetime

from pydantic import SecretStr
from pymongo import MongoClient
from scripts.mongo_test_safety import (
    cleanup_ephemeral_mongo_database,
    require_ephemeral_mongo_database,
)
from scripts.s3_sandbox_fixture import OfflineS3SandboxTransport
from scripts.seed_zero_touch_happy_path_companies import manage_fixtures
from scripts.slice_b_registry_fixture import CountingSyntheticRegistry
from scripts.synthetic_company_pack_test_transport import NoMarketplaceRequests
from scripts.zero_touch_happy_path_fixtures import SPONSOR_DEMO_COMPANIES

from app.config import Settings
from app.persistence.composition import build_persistence_bundle

SPONSOR_DEMO_MODES = tuple(
    f"sponsor-{c.code.lower()}" for c in SPONSOR_DEMO_COMPANIES
) + (
    "sponsor-garden",
    "sponsor-merlion",
    "sponsor-multiple",
    "sponsor-multilevel",
)
BLOCKER_IDENTITIES = {
    "sponsor-garden": ("GARDEN BUSINESS", "11111999A"),
    "sponsor-merlion": ("MERLION CIRCULAR LABS PTE. LTD.", "202400001A"),
    "sponsor-multiple": ("MULTIPLE OWNER DEMO PTE. LTD.", "202400008H"),
    "sponsor-multilevel": ("MULTI LEVEL OWNERSHIP DEMO PTE. LTD.", "202400009I"),
}


class SponsorDemoBrowserFixture:
    def __init__(self, settings: Settings, mode: str, database: str, port: int):
        if (
            mode not in SPONSOR_DEMO_MODES
            or settings.app_env != "test"
            or not 1024 <= port <= 65535
        ):
            raise ValueError("Invalid isolated sponsor fixture")
        self.database = require_ephemeral_mongo_database(database)
        self.cleanup_client = MongoClient(
            host="127.0.0.1", port=port, serverSelectionTimeoutMS=3000
        )
        self.mode = mode
        self.settings = settings.model_copy(
            update={
                "clm_persistence_mode": "mongo",
                "mongo_database": self.database,
                "mongo_uri": SecretStr("mongodb" + f"://127.0.0.1:{port}"),
                "acra_connector_mode": "api_marketplace_mock",
                "registry_cache_mode": "auto",
                "acra_api_marketplace_mock_client_id": SecretStr(
                    secrets.token_urlsafe(32)
                ),
                "acra_api_marketplace_mock_secret_key": SecretStr(
                    secrets.token_urlsafe(32)
                ),
            }
        )
        self.target = OfflineS3SandboxTransport("success")
        self.protocol_fixture = mode == "sponsor-garden"
        self.registry = None
        self.marketplace = None
        try:
            happy = next(
                (
                    c
                    for c in SPONSOR_DEMO_COMPANIES
                    if mode == f"sponsor-{c.code.lower()}"
                ),
                None,
            )
            if happy is not None:
                self.target.name, self.target.uen = happy.name, happy.uen
                seed_bundle = build_persistence_bundle(self.settings)
                try:
                    manage_fixtures(
                        seed_bundle.registry_snapshots,
                        now=datetime.now(UTC),
                        seed=True,
                        companies=SPONSOR_DEMO_COMPANIES,
                    )
                finally:
                    seed_bundle.close()
                from app import composition
                from app.connectors import acra_api_marketplace_auth

                self.marketplace = NoMarketplaceRequests()
                composition.HttpxAcraTransport = lambda **_: self.marketplace
                acra_api_marketplace_auth.HttpxAcraMarketplaceTokenTransport = lambda: (
                    self.marketplace
                )
            else:
                self.target.name, self.target.uen = BLOCKER_IDENTITIES[mode]
                if self.protocol_fixture:
                    from scripts.garden_protocol_fixture import (
                        OfflineGardenProtocolTransport,
                    )

                    from app.composition import build_acra_connector

                    self.marketplace = OfflineGardenProtocolTransport()
                    self.registry = build_acra_connector(
                        self.settings,
                        transport=self.marketplace,
                        marketplace_token_transport=self.marketplace,
                    )
                else:
                    self.registry = CountingSyntheticRegistry()
        except Exception:  # noqa: BLE001 - contain fixture setup failures and close owned resources
            self.close()
            raise RuntimeError(
                "Isolated sponsor fixture could not start safely"
            ) from None

    def metadata(self):
        return {
            "persistence": "MONGO",
            "database": self.database,
            "synthetic_only": True,
            "evidence": "AUTOMATED_OFFLINE_SIMULATION",
            "real_sandbox_uat": "NOT_VERIFIED",
            "registry_calls": list(self.registry.calls)
            if isinstance(self.registry, CountingSyntheticRegistry)
            else [],
            "marketplace_calls": list(self.marketplace.calls)
            if self.marketplace is not None
            else [],
        }

    def close(self):
        try:
            cleanup_ephemeral_mongo_database(self.cleanup_client, self.database)
        finally:
            self.cleanup_client.close()
