"""Standalone contract imports refuse ambient owner dotenv/Mongo/provider configuration."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTestIsolation(unittest.TestCase):
    def test_hostile_configuration_is_cleared_before_application_import(self):
        code = """
import sys
sys.path.insert(0,'tests/contract')
from app.config import Settings
Settings.model_config = {**Settings.model_config,'env_file':'DO_NOT_READ_OWNER_ENV'}
from pydantic_settings.sources.providers.dotenv import DotEnvSettingsSource
def forbid_dotenv(*args, **kwargs):
    raise AssertionError('Standalone composition must not invoke dotenv reading')
DotEnvSettingsSource._read_env_file = forbid_dotenv
import pymongo
def forbid(*args,**kwargs):
    raise AssertionError('Contract import must not construct MongoClient')
pymongo.MongoClient=forbid
from phase13_contract_credentials import provision_contract_hash_environment
provision_contract_hash_environment()
assert Settings.model_config['env_file'] is None
s=Settings()
assert s.clm_persistence_mode=='memory'
assert s.acra_connector_mode==s.goldtier_connector_mode=='mock'
assert s.mongo_database=='clm_contract_tests'
assert not s.garden_supplement_enabled
from app.main import app
assert app is not None
"""
        env = {
            **os.environ,
            "PYTHONPATH": str(ROOT / "apps/backend"),
            "CLM_PERSISTENCE_MODE": "mongo",
            "MONGO_DATABASE": "clm_poc",
            "MONGO_URI": "mongodb" + ":" + "//127.0.0.1:1",
            "ACRA_CONNECTOR_MODE": "sandbox",
            "GOLDTIER_CONNECTOR_MODE": "sandbox",
            "GARDEN_SUPPLEMENT_ENABLED": "true",
        }
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            result.returncode, 0, "Standalone contract environment isolation failed"
        )
