# ACRA API Marketplace Mock Runtime — Reflection

## Outcome

The fail-closed official-Mock placeholder became a bounded opt-in runtime without
changing the local synthetic default or representing Mock evidence as Sandbox or Live.
The critical evidence result was negative as well as positive: entity/shareholder
retrieval works, but the Garden shareholder chain is absent and the capital sample does
not authorize a compatible denominator. Preserving the existing required-data stop is
therefore part of the successful outcome.

## Boundary and complexity closure

- Existing composition and connector ports remain owners; the new modules isolate only
  fixed official-Mock auth and operations.
- The dormant BizFile connector remains uncomposed. Its proven-compatible strict
  decoders are reused; historical speculative OAuth, Bearer behavior, raw debugging,
  Garden fallback, and generic percentage inference remain retired.
- No fallback or compatibility branch was added between provider modes.
- Complexity budget: within budget. New auth/provider owners are cohesive and focused;
  composition received wiring only; source DTO growth is bounded to provider evidence.
- Completion-time decision: no extraction or follow-up complexity repair required.

## Security closure

Credentials are backend-only `SecretStr` values, token responses suppress the token
from representation, and cached tokens live only in process memory. Fixed HTTPS hosts,
OS trust-store verification, no redirects, disabled environment proxy trust, bounded
timeouts/bodies, strict identities, safe errors, and query-free provenance hold the
external boundary. Sanitized evidence contains no raw payload or credential material.

The first independent review exposed two useful boundary gaps. A field-level receipt
validator was insufficient because individually valid values could still tell a false
whole-record success story; the validator and JSON Schema now encode coherent outcome
combinations. Likewise, an HTTP status alone cannot establish provider not-found
semantics while Q-012 remains open, so 404 now fails closed. Activating the local Mock
mode also revealed that ordinary tests needed an explicit synthetic-mode owner rather
than implicit dependence on developer `.env` state.

The backend evidence blocker proved to be a baseline test-harness regression, not an
ACRA runtime defect: clean accepted main failed 7 of 20 isolated executions. Timed stack
capture showed the connected HTTP client blocked while Uvicorn and AnyIO were idle.
Proxy removal, client cleanup, manually supplied socket ownership, and Uvicorn-owned
binding did not eliminate recurrence. The deepest confirmed repository cause was the
in-thread Windows harness selecting Uvicorn's default Proactor loop. A Selector-loop
counterfactual and the minimal permanent harness repair both passed 20 of 20 exact-test
executions, followed by 10 of 10 containing-module runs and the complete affected
Windows lifecycle selection. Application networking, request timeouts, assertions, and
the Phase 13 one-backend/two-seeder contract remain unchanged.

The second independent review also showed that outcome-level receipt binding was still
too broad. The current schema and validator therefore bind each operation to its exact
safe endpoint and current authority: entity/shareholder operations permit strict
success or explicit empty; capital permits schema-observation-only; sanitized failure
remains available for each operation.

## Residual risk and next evidence

Q-012 remains open. The next valuable provider evidence is a same-entity shareholder
and capital pair with authoritative share-class/issued-unit semantics, followed by
provider error/not-found/rate guidance. None of that is required to truthfully run the
current partial Mock retrieval. Both failed independent gates remain immutable
remediation evidence. The lifecycle blocker is now resolved, so the exact frozen
candidate proceeds to a third, fresh independent verdict.
