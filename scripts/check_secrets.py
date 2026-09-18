"""Fail when common secret shapes appear in tracked or non-ignored untracked files.

Findings intentionally omit the matched value so CI output cannot leak a secret.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_TEXT_SIZE = 2 * 1024 * 1024
PLACEHOLDERS = {
    "",
    "changeme",
    "example",
    "placeholder",
    "redacted",
    "replace_me",
    "token",
    "todo",
    "your_value_here",
}
SENSITIVE_FILE_SUFFIXES = {
    ".cer",
    ".crt",
    ".der",
    ".jks",
    ".key",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
}
SOURCE_CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}
RUNTIME_VALUE_REFERENCE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*$")


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    captured_value_group: int | None = None


RULES = (
    Rule("private-key-material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    Rule("certificate-material", re.compile(r"-----BEGIN (?:X509 )?CERTIFICATE-----")),
    Rule("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    Rule("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b")),
    Rule("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    Rule("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    Rule("stripe-live-secret", re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b")),
    Rule(
        "credential-uri",
        re.compile(
            r"(?i)\b(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis)://[^\s/:@]+:[^\s@]+@"
        ),
    ),
    Rule(
        "jwt-token",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
    Rule(
        "bearer-authorization",
        re.compile(r"(?i)\bauthorization\b\s*[:=]\s*[\"']?bearer\s+([^\"'\s#]+)"),
        captured_value_group=1,
    ),
    Rule(
        "sensitive-assignment",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|client_secret|api_key|access_token|bearer_token)"
            r"\b\s*[:=]\s*[\"']?([^\"'\s#]+)"
        ),
        captured_value_group=1,
    ),
)


def candidate_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def is_placeholder(value: str) -> bool:
    normalized = value.strip().strip("{}<>[]").lower()
    return normalized in PLACEHOLDERS or normalized.startswith(("your_", "example_", "test_"))


def is_runtime_sensitive_forwarding(path: Path, value: str) -> bool:
    """Allow source-code references while continuing to reject committed literals."""

    if path.suffix.lower() not in SOURCE_CODE_SUFFIXES:
        return False
    normalized = value.strip().rstrip(",;)]}")
    normalized = normalized.split("[", maxsplit=1)[0]
    return bool(RUNTIME_VALUE_REFERENCE.fullmatch(normalized))


def scan_file(path: Path) -> list[tuple[str, int]]:
    if path.suffix.lower() in SENSITIVE_FILE_SUFFIXES:
        return [("sensitive-file-type", 0)]

    if not path.is_file() or path.stat().st_size > MAX_TEXT_SIZE:
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    findings: list[tuple[str, int]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule in RULES:
            match = rule.pattern.search(line)
            if match is None:
                continue
            if rule.captured_value_group is not None:
                value = match.group(rule.captured_value_group)
                if is_placeholder(value) or (
                    rule.name == "sensitive-assignment"
                    and re.search(r"[:=]\s*[\"']", match.group(0)) is None
                    and is_runtime_sensitive_forwarding(path, value)
                ):
                    continue
            findings.append((rule.name, line_number))
    return findings


def main() -> int:
    findings: list[tuple[Path, str, int]] = []
    for path in candidate_files():
        findings.extend((path, rule, line) for rule, line in scan_file(path))

    if findings:
        print("Potential secret material detected (matched values suppressed):")
        for path, rule, line in findings:
            location = f":{line}" if line else ""
            print(f"- {path.relative_to(ROOT)}{location} [{rule}]")
        return 1

    print("Secret scan passed: no supported secret patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
