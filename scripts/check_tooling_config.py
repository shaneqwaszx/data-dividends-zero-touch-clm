"""Validate the exact public, project-scoped Codex MCP configuration offline."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import tomllib

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".codex" / "config.toml"
SCHEMA_COMMENT = "#:schema https://developers.openai.com/codex/config-schema.json"
DOCS_URL = "https://camunda-docs.mcp.kapa.ai"

_SERVER_COMMON_KEYS = {
    "enabled",
    "required",
    "default_tools_approval_mode",
    "startup_timeout_sec",
    "tool_timeout_sec",
    "enabled_tools",
    "tools",
}
_EXPECTED_SERVERS = {"camunda_docs", "camunda_cluster"}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_tool_prompts(
    server_name: str,
    tools: object,
    expected: tuple[str, ...],
    errors: list[str],
) -> None:
    if not isinstance(tools, dict):
        errors.append(f"{server_name}.tools must be a table")
        return
    if set(tools) != set(expected):
        errors.append(f"{server_name}.tools must contain only its approved tools")
        return
    for name in expected:
        value = tools.get(name)
        if not isinstance(value, dict) or value != {"approval_mode": "prompt"}:
            errors.append(f"{server_name}.tools.{name} must require prompt approval")


def _validate_common(
    server_name: str,
    server: Mapping[str, Any],
    *,
    expected_keys: set[str],
    enabled: bool,
    startup_timeout: int,
    tool_timeout: int,
    enabled_tools: tuple[str, ...],
    errors: list[str],
) -> None:
    if set(server) != expected_keys:
        errors.append(f"{server_name} contains missing or unapproved keys")
    if server.get("enabled") is not enabled:
        errors.append(f"{server_name}.enabled has the wrong value or type")
    if server.get("required") is not False:
        errors.append(f"{server_name}.required must be false")
    if server.get("default_tools_approval_mode") != "prompt":
        errors.append(f"{server_name} must use prompt approval")
    if not _is_int(server.get("startup_timeout_sec")) or server.get(
        "startup_timeout_sec"
    ) != startup_timeout:
        errors.append(f"{server_name}.startup_timeout_sec is invalid")
    if not _is_int(server.get("tool_timeout_sec")) or server.get(
        "tool_timeout_sec"
    ) != tool_timeout:
        errors.append(f"{server_name}.tool_timeout_sec is invalid")
    tools = server.get("enabled_tools")
    if not isinstance(tools, list) or tuple(tools) != enabled_tools or not all(
        isinstance(item, str) for item in tools
    ):
        errors.append(f"{server_name}.enabled_tools is invalid")
    _validate_tool_prompts(server_name, server.get("tools"), enabled_tools, errors)


def validate_text(text: str) -> list[str]:
    errors: list[str] = []
    if not text.startswith(f"{SCHEMA_COMMENT}\n"):
        errors.append("the official Codex schema comment must be the first line")
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return [*errors, "configuration is not valid TOML"]
    if set(document) != {"mcp_servers"}:
        errors.append("only the mcp_servers top-level table is allowed")
    servers = document.get("mcp_servers")
    if not isinstance(servers, dict):
        return [*errors, "mcp_servers must be a table"]
    if set(servers) != _EXPECTED_SERVERS:
        errors.append("the exact camunda_docs and camunda_cluster servers are required")

    docs = servers.get("camunda_docs")
    if not isinstance(docs, dict):
        errors.append("camunda_docs must be a table")
    else:
        _validate_common(
            "camunda_docs",
            docs,
            expected_keys=_SERVER_COMMON_KEYS | {"url"},
            enabled=True,
            startup_timeout=15,
            tool_timeout=60,
            enabled_tools=("search_camunda_knowledge_sources",),
            errors=errors,
        )
        if docs.get("url") != DOCS_URL:
            errors.append("camunda_docs.url is not the approved public endpoint")

    cluster = servers.get("camunda_cluster")
    if not isinstance(cluster, dict):
        errors.append("camunda_cluster must be a table")
    else:
        _validate_common(
            "camunda_cluster",
            cluster,
            expected_keys=_SERVER_COMMON_KEYS | {"command", "args"},
            enabled=False,
            startup_timeout=10,
            tool_timeout=30,
            enabled_tools=("getClusterStatus", "getTopology"),
            errors=errors,
        )
        if cluster.get("command") != "c8":
            errors.append("camunda_cluster.command must be c8")
        if cluster.get("args") != ["mcp-proxy", "--profile", "fyp-camunda"]:
            errors.append("camunda_cluster.args must use only the approved local profile")
    return errors


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=root)
    args = parser.parse_args(argv)
    config_path = args.root.resolve() / ".codex" / "config.toml"
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        print("TOOLING_CONFIG=FAIL: project config is unavailable")
        return 1
    errors = validate_text(text)
    if errors:
        print("TOOLING_CONFIG=FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("TOOLING_CONFIG=PASS: exact optional Docs and disabled cluster MCP policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
