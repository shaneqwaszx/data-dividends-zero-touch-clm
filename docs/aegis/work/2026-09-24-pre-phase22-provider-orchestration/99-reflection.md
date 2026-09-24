# Pre-Phase 22 provider orchestration and sandbox testing - Reflection

## Key judgment

GoldTier Search is an immutable read checkpoint owned by CLM; every external mutation
remains a separate transition in the existing target ledger. This preserves early
resolution without introducing a second write or replay owner.

## Avoided misfixes

- Did not treat no candidates, failed Search, and ambiguous candidates as equivalent.
- Did not let an exact existing customer receive Shell.
- Did not guess ACRA OAuth or a credential header from an HTTP 401.
- Did not copy sponsor examples into global business defaults.
- Did not let an HR testing route bypass the case-bound target ledger.
- Did not fabricate a related-party child ID, expand Q-016, or start Phase 22.

## Baseline and governance closure

- Product / Requirement Baseline: aligned to the assigned Pre-Phase-22 instruction,
  D-051/D-052, current contracts, and recorded unresolved questions.
- Architecture / Runtime Boundary Baseline: aligned to ADR-005 and the existing provider,
  ledger, resolver, repository, capability, and React Query owners.
- Result: `aligned` for implemented POC behavior; `missing-authority` remains explicit for
  ACRA auth, seven GoldTier policy fields, and related-party child-ID lifecycle.
- Governance repair track: refreshed stale post-merge baseline metadata, restored the
  official Marketplace Mock name as a distinct fail-closed mode, and made status/matrix
  documentation match source and tests.
- Retirement track: old local Mock behavior remains as the supported default; dormant
  BizFile runtime composition remains retired. No duplicate official-Mock alias or
  speculative auth path is retained.

## Residual learning

The largest verification risk was not provider logic but intermittent Windows loopback
response acquisition. Instrumented failures occurred before headers and before target
dispatch, while exact reruns and the full backend/browser suites passed. Keeping this
history visible prevents a host-level flake from being converted into either a hidden
green claim or an unrelated product workaround.

The first independent gate also exposed a concrete anti-entropy failure: the domain stage
order and creation path had advanced, while two generic service helpers retained the old
Registry-to-Document transition. The repair collapses both helpers onto the same explicit
Search checkpoint and adds restart/codec evidence. The other findings were projection
truth defects, repaired by deriving classification from active mode and using the existing
resolver rather than adding console-owned decision logic.

Physical Mongo remains the highest-value unavailable check. The next valuable evidence
is a fresh independent exact-content quality gate, followed by publication CI. This
work record is advisory evidence and does not authorize merge.

The repaired candidate's fresh browser and Windows lifecycle reruns close the risk that
the generic stage-order repair was verified only in focused unit tests. No new provider
evidence record was created merely to satisfy a command-line validator: the bounded 401
observation remains classified in the report, while the evidence schema and validator
are verified by their existing negative and positive governance tests.

The second gate exposed a different cross-owner drift: document semantic requiredness
had changed, but reconciliation still treated every missing field as required. The
repair makes requiredness explicit in the reconciliation result and derives a narrow
`REGISTRY_ONLY` state instead of pretending the sources match or auto-selecting a value.
Fingerprint-domain invalidation prevents stale retained reconciliation from inheriting
the new meaning without recomputation. This is distinct from the first gate's Search
ordering/projection defects, so the repeated-design convergence stop did not trigger.

The third gate's direct probe was itself malformed because a normal API-oriented model
dump omits a backend-only persistence binding. Re-running through the canonical encoder
separated that false symptom from the real defect: old v5 state was readable but could
not be safely transitioned after the stage-order change. Explicit workflow-version
metadata is the smaller truthful boundary. It lets decode preserve historical facts,
lets one CAS rebase safe non-terminal work to the earliest unproved stage, and avoids
retroactively claiming Search for terminal or uncertain target records.

The fourth gate then found the complementary trust-boundary omission: write-side and
recovery-side validation existed, but strict read reconstruction did not run the same
cross-field automation validator. The fix is deliberately at that single repository
boundary, after compatibility conversion and strict field/identity checks. Reusing the
domain validator closes explicit stage-order/status tampering without a second migration
owner, decoder-specific workflow rules, or any change to provider behavior. This is a
distinct defect from the third gate's valid legacy-continuation problem, so the repeated-
design convergence stop does not trigger.
