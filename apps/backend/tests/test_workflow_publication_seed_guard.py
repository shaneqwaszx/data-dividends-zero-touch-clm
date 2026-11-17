"""F-6: the physical publication helper refuses every non-disposable database before connecting."""

from unittest.mock import patch

import pytest
from scripts.mongo_test_safety import generate_ephemeral_mongo_database
from workflow_publication_seed import publish_stored_draft_mongo


def _publish(database: str) -> None:
    publish_stored_draft_mongo(
        "mongodb://never-contacted.invalid/",
        database,
        "clm_workflow_definitions",
        "onboarding",
        actor_id="olivia-koh",
    )


@pytest.mark.parametrize(
    "database",
    [
        "clm_poc",
        "clm_staging",
        "clm_staging_restore",
        "admin",
        "local",
        "clm_p16",
        "clm_p16_0123",
        "clm_p16_" + "0" * 23 + "G",
        "clm_p99_" + "0" * 24,
        "clm_p16_" + "0" * 24 + "_x",
        "",
    ],
)
def test_refuses_every_non_disposable_database_before_connecting(database: str) -> None:
    with (
        patch("pymongo.MongoClient") as client,
        pytest.raises(ValueError, match="isolated test database"),
    ):
        _publish(database)
    client.assert_not_called()


def test_a_generated_disposable_name_passes_the_guard() -> None:
    with patch("pymongo.MongoClient") as client:
        definitions = client.return_value.__getitem__.return_value.__getitem__.return_value
        definitions.find_one.return_value = None
        with pytest.raises(LookupError):
            _publish(generate_ephemeral_mongo_database("p16"))
    client.assert_called_once()
