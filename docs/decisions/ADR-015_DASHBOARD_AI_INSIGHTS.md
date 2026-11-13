# ADR-015 — Read-only AI insights on the Onboarding Dashboard

## Status

Proposed. Owner-directed on 2026-11-13 (D-128); not sponsor-confirmed.

## Date

2026-11-13

## Context

The owner asked for an "AI insights" panel on the Onboarding Dashboard Manager view. It shows a
short summary plus "What to note" and "What to do" pointers written by the existing local
Ollama model. It is display-only: no chat, question box or per-case action. When the model
cannot produce insights, the panel stays hidden and the rest of the dashboard is unchanged.
The owner chose that the panel describe what the dashboard shows, including the fixed demo
sample portfolio that the browser adds on top of live data (ARCHITECTURE section 13).

Current boundaries this must respect:

- The CLM backend contains no model client. All model calls run in the separate AI Assistant
  service (`apps/assistant`), which reads CLM through authenticated GET calls with the user's
  session and has no case mutation endpoint, persistence owner or business-rule engine
  (ARCHITECTURE "Read-only AI Assistant main-integration candidate").
- The browser reaches the assistant only through `aiAssistant.ts`, which reuses the
  authenticated `api.ts` transport with sanitized errors and bounded JSON reads.
- Dashboard metrics are factual. D-127 SLA and attention rules are provisional and
  display-only, and nothing on the dashboard is a sponsor SLA, compliance result or
  staff-performance rating.
- The brief requires the existing local model only, no new provider or download, numbers
  calculated outside the model, no unnecessary personal data in prompts, and advisory output
  only.

## Decision

1. **Findings (browser, deterministic).** A pure frontend module turns the all-time dashboard
   snapshot for the viewer's scope and team filter into at most eight findings. With a shorter
   date range selected, the panel reads that all-time snapshot through the existing dashboard
   query; with "All time" selected it reuses the snapshot on screen. A finding is a fixed topic, a severity, display-ready
   facts and whether it warrants an action. Severity, facts and affected-case links come from
   fixed rules, never from the model. Affected-case names and identifiers stay in the browser
   and are never sent.
2. **Insight writing (assistant service, new module `ai_assistant/dashboard_insights.py`).**
   `POST /assistant/dashboard/insights` accepts only the findings in a strict, size-bounded
   schema. It requires a signed-in actor with `CASE_ACCESS`, loaded through the existing
   `backend.load_actor` session check, and the existing origin check. It calls the active model
   only when that model is the configured local baseline on a literal loopback URL
   (`is_local_model_url`) and not a remote or test profile. Otherwise it returns `503` and the
   panel stays hidden. The model must return JSON (`summary`, `notes`, `actions`) that
   references finding ids.
3. **Output checks (same module).** Each item must reference a supplied finding (actions only
   for actionable findings). It may contain only numbers present in that finding's facts (the
   summary: in any finding), and must stay within length limits. It may not use approval,
   rejection, deletion, closure or override wording, or company-name suffixes. Failing items
   are dropped. If no summary or note survives, the response is `502` and the panel stays
   hidden.
4. **Caching.** The service keeps an in-process, bounded cache per user and findings
   fingerprint. The browser keys the query by signed-in user and findings fingerprint under the
   existing session query owner, so unchanged figures never call the model again. The service
   runs one model request at a time; a request whose identical findings were written while it
   waited reuses that answer, so a burst of dashboard views cannot queue past the model timeout.
   For the Director only, the rules add the decisions only a Director can take (GoldTier
   recovery cases waiting, policy changes awaiting their decision) and rank them, with the team
   comparison, ahead of the other findings.
5. **Unchanged.** The chat assistant, its guardrails, knowledge loop, model selection, budget
   and answer records; CLM backend APIs, authorization and persistence; and every existing
   dashboard figure.

## Alternatives considered

- **Model calls in the CLM backend.** This would break the boundary that keeps the core
  backend model-free, and add a provider to the regulated service. Not selected.
- **A new third service.** It would duplicate the model adapter, timeouts and loopback rules,
  and add another process to host. Not selected; the existing assistant service owns model
  access.
- **Extending the case chat or general chat.** The owner asked for a separate,
  non-interactive feature, and chat guardrails select from approved lines for one case or
  question. Not selected.
- **Findings from backend live data only.** This would be backend-verified, but the panel
  would contradict the charts while the demo sample is shown. Not selected for this POC, by
  owner choice. Revisit when the sample is removed.
- **Rule-based text when the model fails.** The owner chose to hide the panel instead.
- **No change.** This would not meet the requested feature.

## Consequences

- The panel describes all the data in the viewer's scope, whatever date range is shown, and the
  model cannot add, change or compute a number. A shorter range costs one extra read-only
  dashboard request.
- Findings are browser-supplied, so the insights are presentation help, not backend-verified
  facts. A user who alters their own request can only change their own panel. By owner
  request (2026-11-13) the panel carries no "AI-written · advisory" badge, footnote or period
  line; its heading is "AI insights", and it has no actions, so it stays advisory in effect.
- A local model call adds seconds of latency on first view of new figures; the panel shows a
  "Loading insights…" placeholder until then, and hides if the request fails.
- One more endpoint and module in the assistant service. No new dependency, persistence,
  configuration mode or provider.

## Architecture invariants affected

- Preserved: the CLM backend stays model-free and authoritative for data and RBAC. The
  assistant stays read-only towards CLM, with no new CLM call beyond the existing actor
  check. One transport owner (`aiAssistant.ts`) and one session query owner
  (`caseQueries.ts`) remain.
- Added: dashboard insight writing is owned by `ai_assistant/dashboard_insights.py`, uses the
  local baseline model only, and only phrases supplied findings.

## Security and persistence implications

- Prompts contain topics, counts, durations, step and exception labels and team names. They
  contain no customer names, registration numbers, documents, evidence or case identifiers.
- Request fields use strict types, enums and character sets, with bounded counts and lengths.
  Facts are untrusted data inside the prompt, never instructions.
- Logs record outcome, counts and latency only. Prompt and answer text is not stored. Nothing
  is persisted; the cache lives in process memory and is lost on restart.
- Authorization: an authenticated actor with `CASE_ACCESS`. No case is read, so case RBAC is
  not involved.

## Migration and retirement implications

There is no stored data or schema to migrate. The feature is additive. Rolling back removes
the endpoint, module and panel; a missing endpoint already results in a hidden panel. When the
demo sample portfolio is retired, revisit decision 1 so findings come from backend data.

## Verification

- Assistant: focused tests for schema bounds, auth and origin, local-only model refusal,
  number, id, wording and name checks, partial-drop, all-dropped `502`, model failure, cache
  reuse, and that the prompt carries only supplied facts.
- Frontend: findings rules over the sample portfolio and edge cases (no cases, Director, empty
  team data); panel rendering, hidden on loading or failure, and links from rules only; query
  key identity.
- Full assistant and frontend suites, `check_architecture`, `check_project_state`, secret
  scan, and an independent quality gate.

## Revisit conditions

Removal of the demo sample. Any request for interaction, remote models or per-case
recommendations. Sponsor guidance on AI use in management reporting. Evidence that the output
checks let an unsupported number or claim through.

## Related contracts and sponsor questions

D-127 (provisional SLA/attention), D-128 (this feature), ADR-012 (assistant knowledge loop
boundaries), `contracts/CASE_ACCESS_AND_PRIORITY_PROFILE.md#dashboard-contract`. Q-016 and
Q-017 remain open.
