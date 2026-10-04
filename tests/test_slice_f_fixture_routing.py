"""Exact, isolated local target ambiguity fixture routing."""

from unittest.mock import patch

import pytest

from scripts import run_e2e


def test_slice_f_ambiguity_discovery_is_explicit_and_exclusive():
    modes = {}
    spec = {
        "ok": True,
        "file": "slice-b-registry-demo.e2e.ts",
        "line": 180,
        "tags": ["@slice-f-target-ambiguity"],
    }
    payload = {"suites": [{"specs": [spec]}]}
    selected = run_e2e._selectors_from_listing(payload, registry_selectors=modes)
    assert modes == {selected[0]: "synthetic-target-ambiguity"}
    spec["tags"].append("@slice-b-synthetic-cache")
    with pytest.raises(RuntimeError, match="conflicting fixture"):
        run_e2e._selectors_from_listing(payload)


def test_slice_f_fixture_cannot_run_unfocused():
    with patch.object(run_e2e, "OwnedProcess") as process:
        with pytest.raises(ValueError):
            run_e2e.run(
                backend_port=8779,
                frontend_port=4187,
                timeout_seconds=240,
                registry_demo="synthetic-target-ambiguity",
            )
        process.assert_not_called()


def test_slice_f_unknown_target_tag_cannot_silently_use_default_composition():
    payload = {
        "suites": [
            {
                "specs": [
                    {
                        "ok": True,
                        "file": "demo.e2e.ts",
                        "line": 1,
                        "tags": ["@slice-f-target-unknown"],
                    }
                ]
            }
        ]
    }
    with pytest.raises(RuntimeError, match="unknown target fixture"):
        run_e2e._selectors_from_listing(payload)
