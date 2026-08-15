# Failure and Recovery Guide

| Situation | Sponsor-visible result | Target calls | Operator/integrator action |
|---|---|---|---|
| Registry not found/incomplete | Registry review or safe failure | none | Confirm synthetic UEN/evidence; do not invent registry data |
| Wrong UEN/malformed/unsafe provenance | `TECHNICAL_FAILURE / ACRA_RESPONSE_*` | none | Fix adapter/contract response; do not turn into business review |
| Document discrepancy | `WAITING_FOR_REVIEW / DOCUMENT_SOURCE_CONFLICT` | none | Use only advertised `KEEP_REGISTRY_VALUE` where the provisional policy permits; system auto-resumes |
| Low confidence/missing evidence | `WAITING_FOR_REVIEW` with no action | none | Obtain corrected/replacement evidence or sponsor policy; do not click through |
| Multiple document blockers | all blockers retained | none | Resolve only supported conflict; independent blocker remains |
| Ownership cycle/incomplete | ownership review | none | Replace/correct hierarchy evidence; no definitive UBO is invented |
| Existing target party | existing-party review | search only | Await sponsor duplicate/selection semantics; no shell/policy/amend |
| Policy/target failure | `TECHNICAL_FAILURE` | ordered prefix only | Correct target/config issue; no false completion |
| Partial amend | target review | all four once | Reconcile optional failed section under confirmed sponsor semantics |
| `RECOVERY_PENDING` | nonterminal retained target outcome | already-executed prefix once | Select safe recovery/resume; Phase 05 finalizes the retained outcome without replay |
| Duplicate Start/resume | current checkpoint/terminal returned | no duplicate operation | Safe to read/re-enter; do not build an external blind retry loop |
| Invalid PDF | request rejected; state remains awaiting input | none | Choose a synthetic fixture with PDF signature/EOF and safe `.pdf` name |

## Recovery boundaries

The accepted target recovery is process-local. A minimal target outcome is recorded
before rich receipt/result/error translation. Later reconciliation reuses the same
submission, correlation, and idempotency identity. It is not a durable transaction,
distributed exactly-once guarantee, or restart recovery mechanism.

Restarting the backend intentionally clears every in-memory case, document, ownership
record, automation record, binding, target ledger, and recovery record. Use restart as
the deterministic demo reset, not as recovery for a case whose evidence must be kept.

## Safe diagnostics

Use case ID, status, stage, correlation ID, fixed code, safe timeline, environment label,
and the UAT export. Never request/log raw PDF/provider/target payloads, authorization,
credentials, private fingerprints, endpoint query data, or stack traces.
