---
name: ci-failure-triage
description: "Diagnose and, when explicitly requested, fix failing CI checks for this repository. Use when a workflow job, backend/frontend check, contract test, secret scan, dependency check, build, or lint/type check fails and Codex must inspect the actual log, find the first causal failure, reproduce it, distinguish CI configuration from product regression, apply the smallest maintainable correction, and prove the rerun."
---

# CI Failure Triage

Respect the user's requested mode: diagnose only unless a fix is explicitly requested or
clearly included.

## Find the first causal failure

1. Read AGENTS.md, project context, the active planner, and the relevant CI workflow and
   tool configuration.
2. Inspect the actual failing job, step, command, exit code, and log. Do not diagnose from
   a summary badge or a later cascade error when the primary log is available.
3. Identify the earliest failure that explains downstream failures. Preserve a concise
   evidence excerpt without copying secrets, tokens, private payloads, or KYC/PII.
4. Record the CI environment that matters: OS, runtime/tool versions, working directory,
   installed dependency set, environment-variable presence (not values), cache behavior,
   and the exact command.

## Reproduce and classify

1. Reproduce the failing command locally or in the closest configured environment. Start
   with the narrow command, then expand to the owning suite.
2. Classify the cause as product regression, test defect, CI/workflow configuration,
   dependency/toolchain drift, platform/environment restriction, or transient external
   failure. Support the classification with the log and reproduction result.
3. If reproduction differs from CI, compare configuration and versions before changing
   product code. Do not call a failure transient without rerun evidence.

## Correct and verify

1. When authorized to fix, prefer the smallest maintainable correction at the owning
   layer. Preserve phase scope, architecture, contract, and security rules.
2. Never delete, disable, quarantine, loosen, or skip a failing test/check merely to make
   CI green. Change an assertion only when authoritative requirements show the assertion
   is wrong, and retain equivalent coverage.
3. Do not conceal failures with broad exception handling, unconditional success exits,
   mutable environment hacks, or reduced security/TLS checks.
4. Rerun the original failing command, its adjacent suite, and any affected contract,
   regression, type/lint, build, or security checks. Inspect the final diff.
5. Report the first causal failure, classification, reproduction, files changed, why the
   correction is minimal, exact rerun evidence, remaining failures, and CI checks not run.
