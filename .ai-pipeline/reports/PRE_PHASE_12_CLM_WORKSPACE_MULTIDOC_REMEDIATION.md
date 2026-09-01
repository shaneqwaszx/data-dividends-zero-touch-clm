# Pre-Phase 12 — CLM Workspace / Multi-Document Quality-Gate Remediation

## 1. Executive Summary

The four independent quality-gate findings are closed without redesigning the accepted
Pre-Phase 12 workflow. DOCX package-member validation now rejects Windows drive-qualified,
rooted, UNC-like, traversal, backslash, and malformed names before OOXML reads. PDF input
now crosses the existing strict `pypdf` parser before IDP rather than relying on superficial
markers. The Start workspace shows the byte total of accepted selected files against the
25 MiB advisory limit. The Windows lifecycle suite was rerun with its complete `13/13`
result captured and independently clean post-run state.

## 2. Quality Gate Findings Addressed

- P12-QG-001 HIGH: `C:/evil.txt` and equivalent DOCX member paths are rejected.
- P12-QG-002 HIGH: marker-only and corrupt PDF bodies are rejected before IDP with a
  controlled client error rather than provider `503`.
- P12-QG-003 MEDIUM: selected accepted byte total is displayed and tested.
- P12-QG-004 MEDIUM: complete Windows lifecycle output and cleanup evidence are captured.

The earlier execution report's claims that traversal-like DOCX names were rejected and
PDF structure was validated were incomplete. Its POSIX-oriented member check missed drive
prefixes, and its PDF check established only signature/EOF markers. This remediation
strengthens both claims with direct counterexample coverage.

## 3. DOCX Root Cause

`DocumentMediaRouter` checked `PurePosixPath(name).parts`, a leading `/`, and the presence
of backslashes. That caught POSIX traversal and several rooted forms but did not recognize
`^[A-Za-z]:` as a drive-qualified package member. Consequently, a ZIP containing the
required OOXML parts plus `C:/evil.txt` could remain inside the accepted package namespace.
The implementation did not extract it to disk, but acceptance violated the untrusted-media
boundary.

## 4. DOCX Fix

Member names are still treated only as ZIP/OOXML names and are never extracted to a
filesystem. Before any required part is read, validation now:

- creates a validation-only slash-normalized view without converting unsafe input into an
  accepted package name;
- explicitly rejects an ASCII drive prefix matching `^[A-Za-z]:`;
- rejects leading/rooted and UNC-like separators, repeated separators, all backslashes,
  NULs, and any `..` component after validation normalization;
- retains the existing encryption, entry-count, expanded-size, macro, ActiveX, embedded-
  object, required-part, and XML checks.

Failures use the existing safe `DOCUMENT_STRUCTURE_INVALID` response and never echo the
hostile package path.

## 5. DOCX Adversarial Tests

Direct counted-system tests construct otherwise sufficient in-memory OOXML packages with
each of these additional members and prove rejection before IDP:

- `C:/evil.txt`
- `C:\evil.txt`
- `D:/folder/file.xml`
- `Z:\folder\file.xml`
- `../evil.txt`
- `..\evil.txt`
- `/evil.txt`
- `\evil.txt`
- `//server/share/evil.txt`
- `\\server\share\evil.txt`

The endpoint-level `C:/evil.txt` counterexample returns `422
DOCUMENT_STRUCTURE_INVALID` without the malicious path in its body. The existing real
`word/document.xml` DOCX path continues through IDP successfully as part of the normal
PDF/DOCX/TXT and three-document tests.

## 6. PDF Root Cause

The prior router required only `%PDF-` at the start and `%%EOF` at the trimmed end. Those
markers do not establish an xref, trailer, page tree, object graph, or readable PDF. The
local IDP later invoked strict `pypdf`, turning malformed client input into a provider
failure and `503` even though the defect was already present in the uploaded bytes.

## 7. PDF Validation Fix

After the bounded marker check, the media router now creates a strict `PdfReader` over the
transient in-memory bytes, rejects encrypted and zero-page documents, resolves the page
tree, and inspects page contents before constructing provider input. Known parser failures
from malformed data (`PdfReadError`, EOF, or parser value failure) are translated narrowly
to the existing fixed `DOCUMENT_STRUCTURE_INVALID` request error. Parser text, PDF bytes,
and extracted text are not logged, persisted, or returned.

This is structural recognizability for the synthetic POC, not malware scanning, CDR, or
production PDF forensics.

## 8. PDF Adversarial Tests

Direct counted-system tests cover:

- plain arbitrary non-PDF bytes;
- the exact marker-only payload `%PDF-1.4\nobvious non-PDF content\n%%EOF`;
- truncated `%PDF-1.4` content;
- wrong extension/MIME, empty input, and missing EOF through the retained document tests;
- the real 807-byte synthetic UAT PDF as the valid ordinary-PDF fixture.

The endpoint marker-only test returns `422 DOCUMENT_STRUCTURE_INVALID`, explicitly not
`503`. Older tests that used marker-only byte constants as fake success fixtures were
updated to use the existing real synthetic PDF; no validator weakening was introduced.

## 9. IDP Call-Stopping for Invalid Media

For every direct hostile DOCX and malformed PDF parameter, observed calls are:

| Boundary | Calls |
| --- | ---: |
| Registry entity/officers/ownership/relationships | `1/1/1/1` from case creation |
| IDP | 0 |
| Ownership | 0 |
| GoldTier SEARCH/SHELL/POLICY/AMEND | `0/0/0/0` |

The automation remains `PENDING_INPUTS`; no reconciliation or intake-completion work is
started. Existing wrong-media/name/empty/size tests also prove provider call count zero.

## 10. Selected Total Size UI

The selected-document panel now renders, for example, `3 documents selected · 7.4 MiB /
25 MiB`. The total is calculated from the actual accepted `File[]`, not the raw browser
input. Tests prove A+B totals, removal leaves B's total, a folder-derived file contributes,
duplicates contribute once, and rejected media contributes zero. Human-readable B/KiB/MiB
formatting is deterministic. This display is advisory; backend 5 MiB/file, 20 current
files, and 25 MiB/current intake enforcement remains authoritative.

## 11. Lifecycle Reverification

The full elevated Windows suite completed with the captured terminal output:

```text
Ran 13 tests in 146.952s
OK
```

Independent read-only post-run inspection reported:

```text
RuntimeMetadataExists : False
ListenerCount         : 0
ProjectPythonCount    : 0
ProjectNodeCount      : 0
```

No lifecycle implementation change was made.

## 12. Files Changed

Remediation implementation/tests:

- `apps/backend/app/services/document_media.py`
- `apps/backend/tests/test_pre_phase12_workspace_multidoc.py`
- `apps/backend/tests/test_document_processing.py`
- `apps/backend/tests/test_document_api.py`
- `apps/backend/tests/test_clm_orchestration.py`
- `apps/backend/tests/test_ownership_api.py`
- `apps/backend/tests/test_phase06_provider_conformance.py`
- `apps/backend/tests/test_phase09_jurisdiction_gateway.py`
- `apps/backend/tests/test_phase11_remediation.py`
- `apps/backend/tests/test_phase_07_uat.py`
- `apps/backend/tests/test_zero_touch_orchestration.py`
- `apps/frontend/src/App.tsx`
- `apps/frontend/src/App.test.tsx`

Remediation documentation/catalogue:

- `README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/architecture/PRE_PHASE_12_CLM_WORKSPACE_MULTIDOC.md`
- `docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md`
- `docs/sponsor-questions/OPEN_QUESTIONS.md`
- `.agents/skills/poc-regression-check/references/regression-catalogue.md`
- `.ai-pipeline/reports/PRE_PHASE_12_CLM_WORKSPACE_MULTIDOC_REMEDIATION.md`

All original Pre-Phase 12 implementation changes and the independent quality-gate report
remain preserved and unstaged.

## 13. Exact Test Results

| Check | Result |
| --- | --- |
| Pre-Phase 12 focused file | `31 passed` |
| Media/document focused set | `90 passed` |
| Full backend | `690 passed`, 4 existing warnings |
| Ruff `check .` | Passed; one read-only access warning for the pre-existing inaccessible frontend pytest-cache directory |
| strict mypy, no incremental cache | Passed, 65 source files |
| Repository `.venv` dependency check | No broken requirements |
| Contract tests | `44 passed` |
| Frontend typecheck | Passed |
| Frontend tests | `57 passed` |
| Frontend build | Passed, 29 modules transformed |
| Frontend dependency tree | Passed; optional platform/tool dependencies reported as optional |
| Secret unit tests / repository scan | `5 passed` / clean |
| GoldTier validator tests | `5 passed` |
| GoldTier examples | `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48` |
| Delivery assets | `4 passed` |
| Windows lifecycle | `13 passed` in 146.952 seconds |
| Post-lifecycle cleanup | metadata absent; listeners 0; project Python 0; project Node 0 |

The first focused remediation run intentionally exposed 51 failures because legacy tests
still supplied marker-only fake PDFs and one new assertion referenced a nonexistent read
method. Those tests were corrected to use the real synthetic PDF and the existing list
read; the final focused and full results above are clean. A delivery-asset command was
also initially invoked from the frontend directory, then rerun from repository root and
passed 4/4.

## 14. Phase 09–11 Regression

- Phase 11 reconciliation/remediation: `58 passed`.
- Phase 10 registry acquisition: `52 passed`.
- Phase 09 jurisdiction gateway: `39 passed`.
- Accepted POC/provider regression: `197 passed`.

The warnings are the existing Starlette/httpx deprecation and three deliberate malformed-
provider Pydantic serialization warnings. No accepted assertion was removed or weakened.

## 15. Existing Pre-Phase 12 Regression

The focused 31-test Pre-Phase 12 file preserves process-local history, defensive read-only
listing, multi-case queue isolation, PDF/DOCX/TXT independent processing, folder-compatible
file validation, explicit intake completion, same-case retry, multi-document provenance,
missing-with-usable aggregation, ambiguous no-winner behavior, replacement isolation, and
call stopping.

Normal three-document calls remain Registry `1/1/1/1`, IDP `3`, Ownership `1`, and
GoldTier `SEARCH/SHELL/POLICY/AMEND = 1/1/1/1`. Blocked reconciliation remains Ownership
`0` and GoldTier `0`.

## 16. Security Review

No Critical or High finding remains. The IDP/upload trust transition was retraced from
request metadata/body through media parsing, transient provider input, safe document
record, API error projection, and frontend. Hostile paths and parser exceptions are not
echoed; raw bytes/text are not persisted or logged; no filesystem extraction, credential,
TLS, auth, outbound connector, target mapping, or KYC logging behavior changed. Secret
tests and the repository scan are clean.

Accepted POC limitations remain Low/architecture dependencies: no antivirus/CDR, no
production sandboxing of document parsers, synthetic inputs only, process-local state,
and no production reviewer RBAC/retention policy.

## 17. Documentation Updated

README, architecture, intake contract, project context, Q-013 wording, and the regression
catalogue now state the strict PDF parser boundary, explicit DOCX package-member namespace
rules, advisory selected-byte display, authoritative backend limits, and non-production
security limitation. The remediation report explicitly records why the earlier PDF/DOCX
claims were incomplete rather than hiding the quality-gate counterexamples.

## 18. Q-012 / Q-015

- Q-012 remains OPEN for the authoritative subscribed ACRA contract, access, auth, and
  sandbox/TLS details.
- Q-015 remains OPEN for evidence authority, authenticated reviewer roles, conflict
  governance, durable audit/persistence, and restart/resume semantics.

Q-003/Q-013/Q-014 also continue to govern final document scope, privacy/security, and
confidence/reviewer policy. No sponsor answer was invented.

## 19. Non-Goals Confirmation

No Phase 12 work, MongoDB application persistence, live ACRA/ACRA+, foreign registry,
real GoldTier/PingFed, source precedence, new reconciliation policy, ownership/UBO redesign,
reviewer authorization, related-party write, lifecycle redesign, antivirus/CDR, or
Ready-for-Approval behavior was added. Nothing was staged, committed, pushed, merged,
rebased, stashed, reset, or cleaned.

## 20. Remaining Risks

- Strict parser recognition is not malware scanning, CDR, or production parser isolation.
- All case/evidence/queue/retry guarantees remain process-local and are lost on restart.
- Q-012 and Q-015 block live integration and production governance claims.
- The existing Starlette/httpx deprecation and deliberate provider-conformance warnings
  remain non-blocking technical debt.
- Browser folder selection remains dependent on browser `webkitdirectory` support; it
  supplies ordinary files only and never grants backend path authority.

## 21. Re-Quality-Gate Readiness

All assigned remediation acceptance criteria and required checks pass. No Critical or High
finding remains. The branch is ready for a new independent Pre-Phase 12 quality-gate review;
this remediation did not perform that review and did not begin Phase 12.

READY FOR PRE-PHASE 12 RE-QUALITY GATE
