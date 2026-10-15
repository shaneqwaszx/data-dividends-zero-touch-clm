# Progressive-disclosure foundation

This bounded presentation foundation starts from post-PR87 main `87bb5537d1764ca16c3aef5d7a1f7560e62b6131`. It adds an opt-in composition to the existing StageDisclosure owner and exposes current intervention requirements. Existing CaseDetail stages retain their legacy composition. Adoption by all seven stages requires a separate assignment.

## Composition and compatibility

Legacy callers continue using `title`, `active`, `summary`, `final` and `children`. Their whole-stage toggle, current-stage expansion, stable child IDs, revealStage navigation and Final before-print opening retain existing behavior.

New callers opt in with a required `scopeKey` and `main`, plus optional `moreDetails` and `technicalDetails`:

```tsx
<StageDisclosure
  title="Submission readiness"
  scopeKey={presentationIdentity}
  main={currentRequiredInputsAndActions}
  moreDetails={passiveBusinessContext}
  technicalDetails={safeDiagnostics}
/>
```

Main remains visible independently of both optional native details sections. More and Technical start collapsed, expand independently and use stage-qualified accessible names. Becoming active does not open them. Missing slots produce no placeholder controls. The stage remains a labelled section with an h2; callers preserve their existing child IDs and meaningful nested heading levels. No separate layout framework, stage registry, storage or server state is introduced.

## Scope, drafts, focus and print

The caller supplies its existing opaque presentation identity from the current lifecycle owner. It must distinguish actor, authenticated session generation and case; include an analysis/binding identity when replacement invalidates local drafts. Never use a credential or raw session token as presentation identity. Keep the key stable for ordinary same-scope GET refreshes. This component does not derive authorization, cache identity, currentness or business state.

Support toggles keep content mounted and retain unsaved local input. Same-scope refresh updates current supplied content without clearing drafts or moving focus. A real scope-key change closes optional sections and remounts scoped child content. If this section owned focus, it returns to the visible current heading; focus in another workspace is preserved. Closing a support section with focus inside returns focus to its native summary. No old actor/case input or delayed focus request is retained by this component.

Existing revealStage opens only ancestors needed to reach its explicit target. It does not auto-expand the other optional sibling. Business action focus remains owned by existing guarded navigation. PR87 focus intent, case/actor/session/generation/version protections remain unchanged.

For `final` in the opt-in composition, before-print temporarily opens present optional sections, and after-print restores their exact earlier combination. A scope change retires an old print snapshot. Legacy Final retains its original before-print opening behavior. Neither print nor disclosure expansion invokes a business mutation.

## Current intervention visibility

HumanInterventionPanel now renders each backend-authored required-evidence/input, expected-next-step and resolution-condition record outside the collapsed diagnostics. The existing Why disclosure retains safe code/class/dependent-stage and decision-history context. Informational grouping, distinct retained records and exception identities, candidate comparison, rationale, explicit confirmation, no-action reasons and denied/busy/frozen controls remain with their existing owners. This change invents no corrective action or automatic resolution and duplicates no mutation form.

## Evidence boundary

Owning component tests cover persistent Main, independent combinations, legacy behavior, scope reset, same-scope draft retention, external focus and print. The canonical authenticated browser owner exercises actual components through Vite and real intervention projections at desktop/narrow viewports, including1280px and360px, genuine native keyboard activation, accessible names, visible focus, contained controls, draft retention and zero POST/PUT/PATCH/DELETE during inspection. The test fixture uses the default exports of the installed Vite-optimized React/CommonJS bundles; runtime namespace import is not the application's static-import interop.

Current full frontend and complete guarded browser evidence, source identities, failures and independent verdict belong to the task gate and `tmp/disclosure-foundation/` receipts. A passing fixture does not claim all CaseDetail stages adopted this mode. Full backend and physical Mongo suites are not required solely for this presentation change and are not inferred from browser fixture databases.

API/type contracts, durable schema, connectors, configuration, business rules, mappings, RBAC/security authority, architecture owners and provider classifications are unchanged. Runtime presentation/accessibility changes only. Mock/Local/synthetic sandbox evidence is not Live interoperability, hierarchy creation, compliance or final approval. Hosted billing-refused jobs are NOT_EXECUTED; only the human owner may decide a release exception and merge.
