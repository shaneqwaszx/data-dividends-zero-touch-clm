"""Fail-closed test fixture selection for focused and discovered browser journeys."""

from unittest.mock import patch

import pytest

from scripts import run_e2e


def test_discovery_records_exact_slice_b_composition_and_rejects_mixed_modes():
    registry = {}
    garden = set()
    payload = {
        "suites": [
            {
                "specs": [
                    {
                        "ok": True,
                        "file": "slice-b-registry-demo.e2e.ts",
                        "line": 1,
                        "tags": ["@slice-b-garden-partnership"],
                    },
                    {
                        "ok": True,
                        "file": "slice-b-registry-demo.e2e.ts",
                        "line": 2,
                        "tags": ["@slice-b-synthetic-cache"],
                    },
                    {
                        "ok": True,
                        "file": "zero-touch-exception.e2e.ts",
                        "line": 3,
                        "tags": ["@garden-protocol"],
                    },
                ]
            }
        ]
    }
    selectors = run_e2e._selectors_from_listing(
        payload,
        garden_selectors=garden,
        registry_selectors=registry,
    )
    assert registry == {
        selectors[0]: "garden-partnership",
        selectors[1]: "synthetic-cache",
    }
    assert garden == {selectors[2]}
    payload["suites"][0]["specs"][0]["tags"].append("@slice-b-synthetic-cache")
    with pytest.raises(RuntimeError, match="conflicting fixture"):
        run_e2e._selectors_from_listing(payload)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--registry-demo", "garden-partnership"],
        [
            "--registry-demo",
            "synthetic-cache",
            "--garden-protocol",
            "--grep",
            "Slice B",
        ],
    ],
)
def test_cli_rejects_broad_or_combined_registry_demo_before_any_process(arguments):
    with patch.object(run_e2e, "OwnedProcess") as process:
        with pytest.raises(SystemExit):
            run_e2e.main(arguments)
        process.assert_not_called()


def test_runtime_rejects_unknown_mode_before_any_process():
    with patch.object(run_e2e, "OwnedProcess") as process:
        with pytest.raises(ValueError, match="Unknown"):
            run_e2e.run(
                backend_port=8037,
                frontend_port=5207,
                timeout_seconds=60,
                registry_demo="unapproved",
                grep="Slice B",
            )
        process.assert_not_called()
