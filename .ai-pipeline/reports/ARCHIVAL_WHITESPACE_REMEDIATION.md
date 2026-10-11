# Scoped archival whitespace remediation

The actual Git whitespace gate passes after the owner's narrow root .gitattributes
correction. All previous403 proposal files remain byte-identical. This is CI_TOOLING,
with additive governance documentation, not DOCS_ONLY or a product/timeout repair.
The new independent reviewer must decide PASS before publication resumes.

## Authority, baseline and boundary

Direct human authorization: Scoped Git Whitespace Remediation and Publication
Continuation, attachment SHA256
`957877382e8a25ac3585a0f93ef03e93f684de95cabf78f13d44257959614d08`.
The task allows CRLF recognition throughout the repository, exactly five archival log
exceptions, immutable evidence, updated derived manifests, fresh independent review,
then previously authorized two scoped commits/normal push/PR/CI assessment. It forbids
general application whitespace exemptions, historical log rewriting, product changes,
persistent Git configuration changes, real provider/protected DB writes and human merge.

Existing worktree: C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm.
Branch: feat/blocker-resolution-idp-ux-optimization. BASE/HEAD/fresh main/merge-base:
`e799d74063678bb0eccbea445d5ab3c8628dd2c0`; no main drift, staged or unmerged path.
Original checkout and other registered worktrees are retained. No new worktree is created.

Historical source68 identity:
`5de89b19dda6964828d87ecf744d7b30df4ea3ee8c872a5a4dd2ffabb9df38df`.
Historical reviewed398 content:
`df9dd08ffc482b60aaa0951899fd20adf72cdc628e370c71ed222b1704cb499a`.
Historical403 publication proposal remains frozen in its original file manifest,
handoff and receipt; it is not renamed or represented as the new proposal.
The preceding stop record remains task-owned ignored tmp/CONTROLLED_PUBLICATION_STOP.md,
SHA256 `3cef62352c802a7bcb50ff72a2ab7fe44e22588c4a953af61f78329181096fa9`.

Only .gitattributes configuration and new governance records change in this task.
All prior application/test/PDF/evidence/report bytes remain unchanged. API/types,
schema/persistence, connectors, runtime configuration, business rules, mappings,
auth/security, architecture owners/dependencies, provider status and runtime behavior
remain unchanged. Git whitespace configuration changes explicitly as detailed below.

## Cause and exact configuration delta

Normal Git add under this host's core.autocrlf=true would normalize reviewed raw bytes.
The preceding disposable-index raw staging preserved them, but the default whitespace
check treated CRLF endings as trailing whitespace. Recognizing CRLF diagnostically
still exposed six immutable log findings: two trailing-space lines and four added EOF
blank lines across five files. Earlier functional acceptance did not waive that
publication gate. No historical file was rewritten to satisfy it.

The existing PDF rule remains:

```gitattributes
# PDF cross-reference tables contain byte offsets and must not be line-ending normalized.
*.pdf binary
```

The exact addition is:

```gitattributes
# Preserve normal whitespace validation while treating CRLF as a line ending.
* whitespace=cr-at-eol

# Immutable historical diagnostic logs: preserve exact archived bytes.
.ai-pipeline/reports/SDQ01_ROUND3_EVIDENCE/logs/sdq01-r3-frontend.log -text whitespace=cr-at-eol,-blank-at-eol,-blank-at-eof
.ai-pipeline/reports/SDQ01_ROUND3_EVIDENCE/logs/sdq01-r3-shard1-missing-ocr.log -text whitespace=cr-at-eol,-blank-at-eol,-blank-at-eof
.ai-pipeline/reports/SDQ01_ROUND3_EVIDENCE/logs/sdq01-r3-typecheck.log -text whitespace=cr-at-eol,-blank-at-eol,-blank-at-eof
.ai-pipeline/reports/SDQ01_ROUND3_EVIDENCE/logs/sponsor-demo-progress-controlled.log -text whitespace=cr-at-eol,-blank-at-eol,-blank-at-eof
.ai-pipeline/reports/SDQ01_ROUND3_EVIDENCE/logs/sponsor-demo-progress-fixed.log -text whitespace=cr-at-eol,-blank-at-eol,-blank-at-eof
```

Final .gitattributes raw SHA256:
`d05c12bd6b01f93474ff48c7e66f5e8faa054dd13ea973d5e1f1ff4ef2484564`.
It has no other new pattern, binary override, source exemption or fallback.

Git2.56.0.windows.1 execution was checked against matching official documentation:
[per-path whitespace semantics](https://git-scm.com/docs/gitattributes#_checking_whitespace_errors)
and [default whitespace rules/CRLF](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corewhitespace).
CRLF recognition retains default trailing-space, EOF-blank and space-before-tab checks
on ordinary files. The five exact paths alone disable the first two and disable text
conversion. PDF binary behavior remains. Actual negative probes establish effective
behavior rather than relying solely on the proposed attribute syntax.

## Preserved five log hashes

Paths below .ai-pipeline/reports/SDQ01_ROUND3_EVIDENCE/logs/:

| Immutable file | Unchanged SHA256 |
|---|---|
| sdq01-r3-frontend.log | c2ae6961add2edcfc017268257ed19700c647355f0a0cc277204505494fcb04b |
| sdq01-r3-shard1-missing-ocr.log | 6166bef8a81f72f3b158b338772272197fa1ead2befa267fe638c4aee807e0f7 |
| sdq01-r3-typecheck.log | e509183f941e75d75acd2730534462d1053bf5d19f4ff51e5e43e834cd2adc5d |
| sponsor-demo-progress-controlled.log | 5f57d445c76a7ceafc7a2b8713e135f6aeac89b6d989c058e33afb645d398e49 |
| sponsor-demo-progress-fixed.log | 5395ab0eb378acbcd9d48a17ae158d77314e2844c405c03786e5847fafe6dbb1 |

All29 prior reviewed safe logs, all prior PDFs, source68 and the entire historical403
proposal are rehashed. Prior FAIL/PASS reports retain their original verdicts and bytes.

## Verification and falsification

Full safe commands/results and raw identities are recorded in
ARCHIVAL_WHITESPACE_VERIFICATION.json. Initial focused canonical Git execution staged
all403 prior proposal paths plus .gitattributes in a disposable GIT_INDEX_FILE. Every
indexed blob matched its raw file SHA256 and the actual unfiltered
`git diff --cached --check` returned0. New governance members must also be staged and
checked by the independent reviewer against the new full review manifest.

Command-scoped core.autocrlf=false preserves raw bytes, and core.longpaths=true supports
the existing Windows filenames. Persistent Git configuration is neither edited nor
used to hide failures; its actual pre/post values are independently read without the
command overrides. Real index SHA256 remains unchanged and empty throughout diagnostics.

Sixteen disposable-index cases cover ordinary LF/CRLF success; ordinary trailing spaces,
extra EOF blank lines and space-before-tab rejection; success for synthetic retained
space/EOF data at each exact archival path; preserved space-before-tab rejection even
on an archival path; and rejection at five unlisted neighboring filenames. No probe
modifies a real source or archived file. Each synthetic blob exists only in the temporary
index; the accepted tree is restored before the final full canonical check. Only the
newly created task-owned temporary index/pathspec files are removed afterward.

Attribute lookup covered1749 tracked/candidate/probe/neighbor paths at the initial
404-path test snapshot. Exactly five have the archival exception; all ordinary paths
use cr-at-eol. Binary PDF text/diff/merge flags remain unset. All source/evidence/PDF
hashes and the real index are rechecked after probes. No secret/confidential/protected
path is staged and no provider/database/browser/forensic execution occurs.

Affected checks:69 tests in tests.test_pre_pr_check, tests.test_check_secrets and
tests.test_check_tooling_config PASS; configured backend Ruff PASS; six current
project-state/architecture/tooling/policy/provider-readiness/secret checks PASS.
Two early temporary-probe classifier assertions expected a generic whitespace label
where Git correctly reported space-before-tab; labels were corrected in the ignored
helper only. A pre/post configuration classifier was also corrected to read actual
persistent settings rather than the command override. Candidate attributes/source/log
bytes did not change during those evidence corrections.

Applicable class CI_TOOLING requires focused checks, Ruff, secret scanner/tests,
project-state/architecture, fresh independent QG and committed-state pre-PR. Unaffected
backend/mypy/frontend/contracts/browser/physical lanes are not rerun solely for this
attributes delta. Their preserved owning-byte evidence remains explicitly attributable:
current complete89/112 browser, eight offline journeys,109 backend/576 frontend and
the earlier applicable broad/physical/contract evidence. No historical root count is
relabeled as a fresh current run. Clean committed pre-PR and candidate CI remain
NOT_RUN before independent acceptance/authorized commits.

## Review freeze and publication sequence

The new ARCHIVAL_WHITESPACE_REVIEW_MANIFEST.json freezes the complete prior403 proposal,
.gitattributes, this report, verification and candidate-specific risk continuation.
The new reviewed407 membership is additive. Only its own index, the assigned new gate
and three final publication derivatives are excluded, without any source/test/criteria
exclusion. Final revised proposal therefore contains412 files when those derivatives
are complete; exact current counts/hashes belong to the revised manifest.

The independent reviewer did not implement/remediate this task, may FAIL and writes
only ARCHIVAL_WHITESPACE_INDEPENDENT_GATE.md. They must challenge the exact exception
boundary, actual unfiltered Git check, normal-source negatives, unchanged historical
bytes, full membership and applicable functional evidence. No report-only self-verdict
or old PASS authorizes the new configuration.

After fresh exact PASS, freeze content, fetch/recheck main, finalize revised manifest,
stage only exact paths with individual safe-log force-adds, inspect canonical staged
whitespace and full diff, then create the two authorized commits. Preserve original388
implementation/evidence scope; put .gitattributes and new remediation/governance metadata
in the governance commit. On the required clean committed state run pre_pr_check.py
and finish the checklist. Only its PASS permits normal push/PR, actual push and PR CI
assessment, reviews and mergeability inspection. Never merge or enable auto-merge.
Any further issue outside this exact scope stops for separate owner review.

SDQ-01 remains historical root cause unresolved - owner-accepted residual risk, categoryF.
SDQ-02 remains independently closed. Real Sandbox/UAT remains NOT_VERIFIED. This archival
exception changes publication tooling only and supplies no historical causal proof.
