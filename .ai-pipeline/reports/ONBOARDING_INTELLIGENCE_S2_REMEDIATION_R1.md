# Session 2 remediation round 1 — P2-01

Status: bounded repair implemented and required current verification PASS; new freeze
and fresh independent gate pending. Session 3/external acceptance remains gated.
One of two permitted rounds used.

Branch: `feat/onboarding-intelligence-goldtier-sandbox`; BASE_SHA / HEAD / last fetched
origin/main: `1d426e0ceddc32d80b0aaec293c62fb761f2fecf`. No Git publication or private
configuration change. Initial failed candidate was
`0a002f10fc37244cd009854aab8b6e007d2de3d4112a98dca4d48304c0008d20`.
Its manifest and complete independent FAIL are preserved byte-for-byte as
ONBOARDING_INTELLIGENCE_S2_R0_MANIFEST.json and
ONBOARDING_INTELLIGENCE_S2_R0_QUALITY_GATE.md (raw hashes
`4926880658ea26447c433b8594fc5d3807aa11bac4daf71e2e9d531031f6a23d` and
`b679b042274855429d17c9c4bd1b30e6e17e3aae388525d2d851a2f907f740c7`).

## Assigned defect and repair

The independent reviewer and coordinator both reproduced a supported pipe table with
`Shares | Shares` or `Shares | Share count`: explicit synthetic values 250 and 300
became one AMBIGUOUS/PROPOSED value 300. The earlier dictionary conversion silently
lost 250. Blocking prevented false target success but did not preserve original evidence.

Only the table branch of the existing `document_ownership_parser.py` changes. It retains
bounded distinct conflicting variants and propagates later explicit row cells to prior
variants. All stay AMBIGUOUS/PROPOSED at evidence score at most 0.4, with the same opaque
page/row provenance. It performs no arithmetic, source choice or canonical mutation.
The existing 128-observation limit applies before partial retention; overflow fails
without truncating or picking a winner.

Five new local regressions cover exact/normalized-alias duplicates, later type/date/
explicit-denominator cells, no invented percentage, distinct server observation IDs,
unchanged document version/page/source bindings, exactly128 accepted observations and
129 rejected observations. All five failed against the original parser (1.05s) and
passed after repair (0.82s). One guarded physical regression additionally creates
both proposals through the current document service/Mongo adapter, closes/reopens the
store, and checks exact originals and document-event bindings with disposable cleanup.

## Current evidence

| Check | Result and scope |
|---|---|
| New duplicate-table regression focus | 5 passed, 31 deselected; 0.82s |
| Affected OCR/ownership/persistence security pack | 216 passed, 6 explicit Windows host-Tesseract skips; 46.49s |
| Current-source actual offline OCR pack | 36/36 passed, zero skips; 15.29s; current backend read-only mount and explicit PYTHONPATH, network none, same hardened task image/limits |
| Affected physical Mongo suite | 19/19 passed, zero skips; 4.42s, including duplicate originals through restart; allowlisted new disposable databases/cleanup only |
| Focused Ruff | PASS for the parser and owning local/physical tests; one configured import-order fix in the new physical test |
| Current S2 real-HTTP browser journeys | 2/2 passed, zero skips; 7.4s; original guarded harness and 60-second deadline. All twelve E2E files retain digest 1cc6c01e379b4726413c5bcb752ea167887ea82815ba0510855c2e23a4de07b7; ports 18765/14173 released |
| Strict mypy | PASS, 124 backend files; no incremental cache; 6.56s |
| Configured full Ruff | PASS for backend app/tests and repository scripts/tests; no cache |
| Contracts | 44 passed; 1.368s |
| Six governance scanners | Architecture, project state, policy authority, secrets, tooling configuration and external provider readiness all PASS |
| Complete backend | 2,257 passed, 115 opt-in skips, 4 warnings; 818.74s; complete unfiltered suite including both unchanged100-run stability checks. The skips are109 physical cases plus6 actual-OCR cases, separately exercised |
| Broad physical Mongo | 109/109 passed across15 guarded suites, zero failures/errors/skips; fresh allowlisted disposable databases and cleanup proof; executed serially after backend completion |
| Fresh independent round 1 review | Pending new candidate freeze |

The current browser command was `python -B -u scripts/run_e2e.py --backend-port 18765
--frontend-port 14173 --timeout-seconds 60 --garden-protocol --grep 'S2 '`, using the
task virtual environment, original real HTTP/Chromium harness and guarded Mock target.
The two cases exercise creator multi-level editing/freeze/calculation and deliberate
document-proposal/source bindings. Neither frontend nor E2E fixture bytes changed.
Comparison with the initial manifest confirms only the parser, its local/physical
tests, planner and implementation receipt changed; the two exact initial archives and
this remediation receipt are the three added paths. No candidate path was removed.
All149 current task text paths (111 tracked changes, 38 new paths including the current
manifest/gate) passed explicit whitespace checks; index remains empty.

The pre-remediation 2,252-test backend and full 56-selector/63-execution browser receipts
remain attributed to their initial source. Unchanged frontend unit/type/build and root
governance source retain their exact recorded content; changed parser behavior receives
current local/OCR/physical/browser coverage. The final combined program still requires
the owner's full final verification after Session 3. No stale failed run becomes PASS.

## Change control and next action

Production delta: one existing parser branch. Test delta: its local and physical
regressions. Evidence/planner documents and R0 archives also change. API/type, schema,
connector composition, configuration, target mapping, auth/security, architecture,
provider status and business policy are unchanged by this remediation. Runtime parsing
now preserves all distinct supported duplicate-column originals; the original source
decision and ambiguity guards remain authoritative.

Current verification and complete round 1 delta inspection pass. Freeze a new
cumulative manifest after final hygiene and obtain fresh independent review.
Only exact PASS authorizes automatic Session 3 continuation under the existing program.
