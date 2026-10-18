"""Import-order changes retain isolated fixture guards and missing-OCR containment."""

import importlib
from unittest.mock import Mock

import pytest
from phase13_test_settings import ordinary_test_settings
from scripts.mongo_test_safety import generate_ephemeral_mongo_database


@pytest.mark.parametrize("module_name,class_name,mode", [
    ("sponsor_demo_browser_fixture", "SponsorDemoBrowserFixture", "sponsor-garden"),
    ("zero_touch_classification_browser_fixture",
     "DatabaseClassificationFixture", "database-alpha"),
])
@pytest.mark.parametrize("invalid", ["mode", "environment", "port"])
def test_browser_fixture_guards_reject_before_mongo(
    monkeypatch, module_name, class_name, mode, invalid,
):
    module = importlib.import_module("scripts." + module_name)
    mongo = Mock(side_effect=AssertionError("fixture guard attempted a database connection"))
    monkeypatch.setattr(module, "MongoClient", mongo)
    settings = ordinary_test_settings()
    if invalid == "environment":
        settings = settings.model_copy(update={"app_env": "production"})
    with pytest.raises(ValueError):
        getattr(module, class_name)(
            settings, "unknown-fixture" if invalid == "mode" else mode,
            generate_ephemeral_mongo_database("p13"), 1 if invalid == "port" else 27028,
        )
    mongo.assert_not_called()


def test_classification_missing_native_ocr_closes_client_and_fails_truthfully(monkeypatch):
    from scripts import zero_touch_classification_browser_fixture as fixture

    client = Mock()
    monkeypatch.setattr(fixture, "MongoClient", Mock(return_value=client))
    monkeypatch.setattr(fixture.shutil, "which", lambda _: None)
    monkeypatch.setattr(fixture.Path, "is_file", lambda _: False)
    with pytest.raises(RuntimeError, match="requires actual local Tesseract"):
        fixture.DatabaseClassificationFixture(
            ordinary_test_settings(), "database-alpha", generate_ephemeral_mongo_database("p13"),
        )
    client.close.assert_called_once_with()
