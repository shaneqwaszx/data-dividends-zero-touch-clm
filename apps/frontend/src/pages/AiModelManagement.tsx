import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";

import {
  activateModel,
  AiAssistantError,
  applyClaudeReconciliation,
  fetchClaudeReconciliation,
  previewClaudeReconciliation,
  resolveClaudeReconciliationRun,
  cancelModelQualification,
  clearModelCredential,
  fetchModelAudit,
  fetchModelOverview,
  fetchRecovery,
  readAnthropicWorkspace,
  MODEL_AUDIT_LIMIT,
  refreshProviderLimits,
  rollbackModel,
  saveClaudeLifetimeCap,
  saveClaudeSpendingControls,
  saveAnthropicEnablement,
  saveDataAccessPolicy,
  saveLifetimeCap,
  saveModelCredential,
  saveSpendingControls,
  startModelQualification,
  testModelConnection,
  type ModelAuditEvent,
  type ModelBudgetStatus,
  type AnthropicSetup,
  type ClaudeReconciliationPreview,
  type ClaudeReconciliationRun,
  type CredentialProvider,
  type ModelClaudeBudget,
  type ModelClaudeReconciliation,
  type ModelCredentialStatus,
  type ModelDataAccess,
  type ModelDiagnosis,
  type ModelOverview,
  type ModelProfileView,
  type ModelQualification,
  type RecoveryView,
} from "../aiAssistant";
import { formatTimestamp } from "../shared";
import type { AuthenticatedProfile } from "../types";
import { CONSOLE_SECTIONS, ConsoleDialog, ConsoleShell, consoleSection, sectionSearch, type ConsoleBadge, type ConsoleSection } from "./aiModels/ConsoleShell";
import { GuidedSetup } from "./aiModels/GuidedSetup";
import { RecoveryCentre, recoveryQueryKey } from "./aiModels/RecoveryCentre";

// AI model management (D-093): HR (MODEL_CONFIG_MANAGE) chooses the application-wide model
// from IT's local loopback profiles. The server decides everything; this page only shows it.

export const modelManagementQueryKeys = {
  root: (userId: string) => ["auth", userId, "assistant-models"] as const,
  overview: (userId: string) => ["auth", userId, "assistant-models", "overview"] as const,
  audit: (userId: string) => ["auth", userId, "assistant-models", "audit"] as const,
  // D-110: the reconciliation runs (under root, so every page action re-reads them).
  claudeReconciliation: (userId: string) => ["auth", userId, "assistant-models", "claude-reconciliation"] as const,
};

const STATUS_LABEL: Record<ModelProfileView["status"], string> = {
  selectable: "Available",
  unavailable: "Unavailable",
  pending_authorisation: "Pending authorisation",
  disabled: "Disabled",
};

const REASON_TEXT: Record<string, string> = {
  NOT_LOOPBACK: "Not a local loopback endpoint; remote models need separate authorisation.",
  STREAMING_REQUIRED: "The chat panel needs a model that streams.",
  PROFILE_DISABLED: "Disabled by IT in the profiles file.",
  REMOTE_NOT_AUTHORISED: "Remote inference is not authorised for CLM use (D-091 dormant; D-092 proposed, synthetic evaluation only).",
  MODEL_DISABLED_BY_ENVIRONMENT: "The AI model is switched off on this server.",
  NOT_QUALIFIED: "Needs a passing qualification for the current configuration.",
  PROFILE_CHANGED: "Its settings changed in the profiles file.",
  PROFILE_MISSING: "It is no longer in the profiles file.",
  PROFILE_UNAVAILABLE: "It is no longer available.",
  QUALIFICATION_OUT_OF_DATE: "The assistant's answer code changed since it was qualified.",
  CREDENTIAL_MISSING: "No key is set: no session key was entered and the server has none.",
  CREDENTIAL_SESSION_UNVERIFIED: "The session key is held back: the HR session that entered it cannot be checked now.",
  PROXY_CONFIGURED: "A proxy is configured on the server.",
  // D-094 local synthetic test mode (GPT-OSS 120B via OpenRouter).
  DECISION_INTERLOCK: "The D-091 and D-092 settings the remote model needs are not set on the server.",
  NOT_DEVELOPMENT_ENVIRONMENT: "The server is not a local development set-up (loopback backend and browser origins only).",
  OWNER_ATTESTATION_MISSING: "The owner has not attested that auto top-up and prompt logging are off.",
  ENDPOINT_NOT_APPROVED: "The configured OpenRouter endpoint is not the approved one.",
  // D-099 (proposed): Claude Sonnet 5.5 Balanced and Fast are listed but not usable.
  ANTHROPIC_NOT_AUTHORISED: "Claude is not set up yet. HR enables it in Providers → Anthropic (D-107).",
  ANTHROPIC_NOT_ENABLED: "Claude is disabled. HR enables it in Providers → Anthropic.",
  ANTHROPIC_ENABLEMENT_UNREADABLE: "Claude's setup could not be read, so Claude is off until it can be.",
  ANTHROPIC_PROVIDER_CONTROLS_MISSING: "Not usable: Anthropic does not provide the readable key limit, per-call cost verification and usage reconciliation that remote models require (D-099 proposed).",
  REMOTE_SETTINGS_INVALID: "The remote model's reasoning settings are not valid on the server.",
  REMOTE_MANIFEST_MISSING: "The paid qualification's question list and count are not configured on the server.",
  LEDGER_UNAVAILABLE: "The spending ledger is missing or unhealthy.",
  // D-095 spending view.
  DAILY_ALLOWANCE_EXHAUSTED: "Today's allowance (Singapore day) has no room for another call.",
  DAILY_CAP_INVALID: "The daily cap setting is not valid, so no call is allowed.",
  LIFETIME_CAP_EXHAUSTED: "The lifetime ledger cap has no room for another call.",
  PROVIDER_LIMIT_EXHAUSTED: "The OpenRouter key's own limit has no room for another call. Only the key's owner can raise it at OpenRouter; it is not an HR spending setting.",
  PROVIDER_LIMIT_NOT_CHECKED: "The OpenRouter key's limit has not been checked yet. Run Test connection.",
  PROVIDER_CHECK_FAILED: "The last OpenRouter key check failed. Run Test connection.",
  CREDENTIAL_INVALID: "The configured OpenRouter API key is not valid.",
  // D-098: qualification recovery.
  QUALIFICATION_SUPERSEDED: "A later qualification of this configuration failed on answer quality.",
  INTERRUPTED: "Interrupted: the AI assistant service stopped or restarted during the run.",
  INTERRUPTED_BILLING_UNCERTAIN: "Interrupted while a paid call may have been open: an operator must reconcile the ledger.",
  // D-099 Option B: Claude Sonnet 5.5 through the Anthropic API (its own safeguards).
  ANTHROPIC_ATTESTATION_MISSING: "The owner has not made the four Anthropic confirmations (dedicated workspace, workspace limit set, inference-only key, key revoked at FYP end).",
  ANTHROPIC_SETTINGS_INVALID: "The server's Claude settings are not valid (they may not exceed the Option B ceilings).",
  WORKSPACE_NOT_ATTESTED: "No confirmed Anthropic workspace is set up.",
  WORKSPACE_MISMATCH: "The workspace set on the server differs from the one Claude was set up for, so Claude is off until they agree.",
  WORKSPACE_LIMIT_NOT_ATTESTED: "The Anthropic workspace's monthly limit (at most US$30.00) has not been confirmed.",
  LEDGER_PATH_SHARED: "The Claude ledger file must be separate from the GPT-OSS ledger file.",
  LEDGER_PROFILE_MISMATCH: "The spending ledger belongs to another provider, so no call is allowed.",
  LIFETIME_CEILING_EXCEEDED: "The ledger cap is not valid (above the lifetime ceiling or the attested workspace limit, or not above what was already spent when the ledger opened), so no call is allowed.",
  RECONCILIATION_STALE: "The ledger has not been reconciled with the provider's usage recently enough (an operator reconciles it).",
  CREDENTIAL_ADMIN_REFUSED: "An administrator key was refused: only an inference key may be used.",
};

// Shared codes whose wording names OpenRouter: the Claude meaning (D-099 Option B).
const CLAUDE_REASON_TEXT: Record<string, string> = {
  PROVIDER_LIMIT_NOT_CHECKED: "The Anthropic workspace and model check has not been run in this server process yet. Run Test connection (a free model read).",
  PROVIDER_CHECK_FAILED: "The last Anthropic workspace and model check failed. Run Test connection.",
  CREDENTIAL_MISSING: "No Anthropic inference key is set: no session key was entered and the server has none.",
  CREDENTIAL_SESSION_UNVERIFIED: "The Anthropic session key is held back: the HR session that entered it cannot be checked now.",
  CREDENTIAL_INVALID: "The configured Anthropic key is not a valid inference key.",
  LEDGER_UNAVAILABLE: "The separate Claude spending ledger is missing or unhealthy.",
  // B1: the ledger changed (or could not be checked) while the page read it, so no mixed figures are shown.
  LEDGER_BUSY: "The Claude ledger was changing while this page read it, so its figures are not shown. Refresh in a moment.",
  DAILY_ALLOWANCE_EXHAUSTED: "Claude's own daily allowance (set in Spending & Limits, at most US$5.00 a Singapore day) has no room for another call.",
  LIFETIME_CAP_EXHAUSTED: "The Claude ledger's lifetime cap has no room for another call.",
};

// D-100 (M-1): where the provider is not known (a start-up revert, an audit row without a
// configuration), the shared codes whose usual wording names OpenRouter are said without a provider.
export const ANY_PROVIDER = "*";
const NEUTRAL_REASON_TEXT: Record<string, string> = {
  PROVIDER_LIMIT_EXHAUSTED: "The provider's own key or workspace limit has no room for another call. It is not an HR spending setting.",
  PROVIDER_LIMIT_NOT_CHECKED: "The provider's key or workspace has not been checked yet. Run Test connection.",
  PROVIDER_CHECK_FAILED: "The last provider key or workspace check failed. Run Test connection.",
  CREDENTIAL_INVALID: "The configured provider key is not valid.",
};

// D-098 Recovery Centre: the server classifies each outcome with closed codes; the page names
// them. Nothing here can lower a gate, bypass a guardrail or start a paid run without HR.
const CATEGORY_LABEL: Record<ModelDiagnosis["category"], string> = {
  passed: "Qualified",
  running: "Running",
  cancelled: "Cancelled",
  technical: "Technical problem",
  budget: "Budget or limit",
  configuration: "Server configuration",
  quality: "Answer quality",
  billing_uncertain: "Billing not reconciled",
};

// An earlier pass for another configuration or answer code: requalification, not a fault.
const OUT_OF_DATE = "OUT_OF_DATE";
const REQUALIFY_TEXT = "Run a new qualification with the current configuration and code. A paid run asks you to confirm its calls first, and the spending limits still apply. Activation stays blocked until it passes.";

function categoryLabel(diagnosis: ModelDiagnosis): string {
  return diagnosis.cause === OUT_OF_DATE ? "Qualification out of date" : CATEGORY_LABEL[diagnosis.category];
}

function actionText(diagnosis: ModelDiagnosis, deployment?: string): string {
  if (diagnosis.cause === OUT_OF_DATE) return REQUALIFY_TEXT;
  return (deployment === ANTHROPIC_DEPLOYMENT && CLAUDE_ACTION_TEXT[diagnosis.action]) || ACTION_TEXT[diagnosis.action];
}

function causeText(diagnosis: ModelDiagnosis, deployment?: string): string {
  return (deployment === ANTHROPIC_DEPLOYMENT && CLAUDE_CAUSE_TEXT[diagnosis.cause]) || CAUSE_TEXT[diagnosis.cause] || readable(diagnosis.cause, deployment);
}
const CAUSE_TEXT: Record<string, string> = {
  PASSED: "The configuration passed every gating check.",
  OUT_OF_DATE: "This pass was for an earlier configuration or answer code, so it can no longer be activated. The current configuration needs its own passing qualification.",
  RUNNING: "The qualification is running on the server. You may leave this page; it keeps going.",
  CANCELLED: "The run was cancelled before it finished.",
  INTERRUPTED: "The run stopped because the AI assistant service stopped or restarted. It was not restarted automatically.",
  INTERRUPTED_BILLING_UNCERTAIN: "The run stopped while a paid call may have been open. That call stays in the spending ledger until an operator reconciles it.",
  STALE: "The run stopped reporting progress. It says nothing about the model.",
  PROCESS_EXITED: "The run's process ended before it finished. It says nothing about the model.",
  SUPERVISOR_FAILED: "The service could not supervise the run. It says nothing about the model.",
  HARNESS_ERROR: "The run hit an internal error. It says nothing about the model.",
  DEADLINE: "The run overran its time limit. It says nothing about the model.",
  CONFIG_MISMATCH: "The model settings or the assistant's answer code changed while it ran. The current configuration needs a new qualification.",
  LEDGER_NOT_RECONCILED: "The spending ledger is stopped or does not match OpenRouter's reported usage.",
  SERVER_SETTINGS: "A server setting, the OpenRouter key's own limit or an owner attestation is not in place.",
  NO_ROOM_FOR_CALLS: "The spending limits had no room for a paid call.",
  PROVIDER_UNAVAILABLE: "The model provider (or the local model) could not be reached or checked.",
  UNSAFE_LINE: "At least one line shown was not an allowed line, so the exact-line guardrail failed the run.",
  CALLS_NOT_VERIFIED: "Some paid calls could not be verified against OpenRouter's records (provider, model and cost).",
  LOW_LINE_VALIDITY: "Too few of the lines the model wrote passed the exact-line check (the gate needs 70%).",
  CALLS_REFUSED: "Paid calls were refused before anything was sent (daily allowance, lifetime limit, call limit or the key's own limit). The answers were not judged.",
  PROVIDER_REFUSED: "OpenRouter refused the calls (key, payment or provider routing). Paid calls are stopped until an operator checks the account.",
  MODEL_UNAVAILABLE: "The model did not answer (timeout, rate limit or provider error). This is usually temporary.",
  ANSWERS_CUT_SHORT: "Too many answers were cut short by the token limits.",
  CAPACITY_NOT_VERIFIED: "The model's context capacity could not be verified for the qualification prompts.",
  UNKNOWN: "The run failed for a reason this page cannot name.",
  KEY_LIMIT_EXHAUSTED: "The OpenRouter key's own spending limit has no room for a call. HR spending controls cannot change it.",
  CREDENTIAL_REVOKED: "The session key the run was given ended (its HR session signed out or expired, or the key was cleared or replaced), so the run was stopped. It says nothing about the model.",
};
const ACTION_TEXT: Record<ModelDiagnosis["action"], string> = {
  NONE: "Nothing to do.",
  WAIT: "Wait for it to finish. Signing out or leaving the page does not stop it.",
  RUN_AGAIN: "Run the qualification again.",
  RETRY_LATER: "Check the provider's status, run Test connection, then retry.",
  TEST_CONNECTION: "Run Test connection again and retry once it passes.",
  REVIEW_SPENDING: "Review the spending limits (or wait for the Singapore-day reset), then retry.",
  ESCALATE_IT: "Ask IT to correct the server configuration. Nothing on this page can override it.",
  ESCALATE_DEVELOPER: "Ask a developer to review the answers. This configuration cannot be qualified again until it is changed.",
  ESCALATE_KEY_OWNER: "Ask the OpenRouter key's owner to raise the key's own limit at OpenRouter (never changed from this page), then run Test connection.",
  ESCALATE_OPERATOR: "Ask an operator to reconcile the spending ledger with OpenRouter (scripts/budget_ledger.py). Paid calls stay stopped until then.",
};

// D-099 with D-100: the Recovery texts above that name OpenRouter, in Claude's terms.
const CLAUDE_CAUSE_TEXT: Record<string, string> = {
  LEDGER_NOT_RECONCILED: "Claude's spending ledger is stopped or has not been reconciled with the Anthropic Console's usage.",
  SERVER_SETTINGS: "A server setting, the attested Anthropic workspace or its limit, or an owner attestation is not in place.",
  CALLS_NOT_VERIFIED: "Some paid calls could not be verified in-band (workspace, model, standard routing and complete usage in the reply).",
  PROVIDER_REFUSED: "The Anthropic API refused the calls (key, workspace spend limit or routing). Paid calls are stopped until an operator checks the workspace.",
  KEY_LIMIT_EXHAUSTED: "The Anthropic workspace's spend limit has no room for a call. HR spending controls cannot change it.",
  CALLS_REFUSED: "Paid calls were refused before anything was sent (Claude's daily allowance, lifetime cap, call limit or the reconciliation window). The answers were not judged.",
};
const CLAUDE_ACTION_TEXT: Partial<Record<ModelDiagnosis["action"], string>> = {
  REVIEW_SPENDING: "Review Claude's own limits in Spending & Limits (separate from GPT-OSS's), wait for the Singapore-day reset, or ask an operator to reconcile the Claude ledger, then retry.",
  ESCALATE_KEY_OWNER: "Ask the Anthropic workspace's owner to check its spend limit in the Anthropic Console (never changed from this page), then run Test connection.",
  ESCALATE_OPERATOR: "Ask an operator to reconcile the Claude ledger with the Anthropic Console's usage (scripts/budget_ledger.py --anthropic). Paid calls stay stopped until then.",
};

function microUsd(micro: number | null | undefined): string {
  return typeof micro === "number" ? `US$${(micro / 1_000_000).toFixed(6)}` : "—";
}

export function escalationSummary(item: ModelProfileView): string {
  const run = item.qualification;
  const diagnosis = run?.diagnosis;
  const failed = (run?.gates ?? []).filter((gate) => gate.gating && !gate.passed).map((gate) => gate.gate);
  return [
    "AI model qualification: escalation",
    `Configuration: ${profileName(item)} (${item.profile_id}, fingerprint ${item.fingerprint})`,
    `Run: ${run?.qualification_id ?? "none"}, ${run?.status ?? "not run"}${run?.code ? ` (${run.code})` : ""}`,
    `Category: ${diagnosis ? categoryLabel(diagnosis) : "unknown"}; cause: ${diagnosis?.cause ?? "unknown"}`,
    `Failed gates: ${failed.length ? failed.join(", ") : "none"}`,
    `Earlier pass still valid: ${item.eligible_qualification && !item.eligible_qualification.is_latest ? item.eligible_qualification.qualification_id : "no"}`,
    `Recommended: ${diagnosis ? actionText(diagnosis, item.deployment) : "review"}`,
  ].join("\n");
}

// D-100 Phase 3: what to check for each provider before a retry. General guidance only; the
// server's own codes on the card say what actually happened.
const TROUBLESHOOTING: Record<"openrouter" | "anthropic" | "local", { title: string; steps: string[] }> = {
  openrouter: {
    title: "Troubleshooting GPT-OSS 120B (OpenRouter)",
    steps: [
      "Providers: check that an OpenRouter key is configured (a session key or the server key) and that Test connection passes (it reads the key's own limit; no model call).",
      "Spending & Limits: check that today's allowance, the lifetime headroom and the key's own limit leave room for every paid call.",
      "If paid calls are stopped, an operator reconciles the ledger with OpenRouter (scripts/budget_ledger.py) before any retry.",
      "A key limit with no room is raised only by the key's owner at OpenRouter, never from this page.",
    ],
  },
  anthropic: {
    title: "Troubleshooting Claude Sonnet 5.5 (Anthropic API)",
    steps: [
      "Run Test connection: it reads the attested Anthropic workspace and the model (free; no case data).",
      "Providers: enter a session inference key, or rely on the server key; either must belong to the workspace Claude was set up for. HR sets Claude up there (workspace read, the owner's four confirmations and monthly limit); no server decision settings are needed.",
      "HR sets Claude's daily allowance, chat calls per paid session and lifetime limit in Spending & Limits (at most US$5.00 a day, 20 calls, and the lower of US$30.00 and the workspace limit). Raising one needs the Claude ledger reconciled with the Anthropic Console within 24 hours; on a provider-capped ledger (D-118) a paid qualification and chat do not.",
      "The workspace's monthly spend limit is changed only by its owner in the Anthropic Console, never from this page.",
    ],
  },
  local: {
    title: "Troubleshooting a local model",
    steps: [
      "Check that the model server this configuration uses is running and has the model loaded, then run Test connection.",
      "IT changes the configuration (the model profiles file, or the server environment for the baseline); any change needs a new qualification.",
    ],
  },
};

function RecoveryCard({ item, configured, busy, onRetry, onTest }: {
  item: ModelProfileView;
  configured: boolean;
  busy: boolean;
  /** Starts a qualification; a paid one always opens the confirmation first. */
  onRetry: () => void;
  onTest: () => void;
}) {
  const run = item.qualification;
  const diagnosis = run?.diagnosis;
  const paid = item.paid_qualification;
  const [copied, setCopied] = useState(false);
  const failedGates = (run?.gates ?? []).filter((gate) => gate.gating && !gate.passed);
  const usable = item.status === "selectable";
  const escalate = diagnosis?.action.startsWith("ESCALATE_") ?? false;
  const kind = providerKind(item);
  const claude = kind === "anthropic";
  const paidRun = isPaidRemote(item.deployment);
  const help = TROUBLESHOOTING[kind];
  const technical = technicalState(item);
  return (
    <article className="model-recovery-card" data-testid={`recovery-${item.profile_id}`}>
      <div className="model-recovery-card__head">
        <h3>{profileName(item)}</h3>
        <span className="console-help">{item.details?.provider ? PROVIDER_LABEL[item.details.provider] ?? item.details.provider : readable(item.deployment)}</span>
      </div>
      <dl className="console-recovery-states">
        <div><dt>Technical qualification</dt><dd><Chip state={technical} /></dd></div>
        <div><dt>Answer quality</dt><dd><Chip state={qualityState(run?.quality)} /></dd></div>
        <div><dt>Availability</dt><dd><Chip state={availabilityState(item)} /></dd></div>
      </dl>
      {!usable && (
        <p className="console-note console-note--block">
          Not available now: {item.reason ? readable(item.reason, item.deployment) : STATUS_LABEL[item.status]}. Retry and Test connection are offered once the server makes it available again.
        </p>
      )}
      {!run ? (
        <>
          <p><strong>Not qualified yet.</strong> No qualification has been run for this configuration. Activation needs a passing technical qualification of its current settings.</p>
          {item.activation_blockers.length > 0 && <p className="control-help">Activation blocked: {item.activation_blockers.map((code) => readable(code, item.deployment)).join(" ")}</p>}
        </>
      ) : (
        <>
          <p>
            <strong>{diagnosis ? categoryLabel(diagnosis) : readable(run.status)}</strong>
            {run.code && <> · {readable(run.code, item.deployment)}</>}
            {!run.current && <> · <span className="tag tag-warn">Out of date</span></>}
          </p>
          {diagnosis && <p>{causeText(diagnosis, item.deployment)}</p>}
          {failedGates.length > 0 && (
            <p className="control-help">Failed gates: {failedGates.map((gate) => `${gate.gate} (${gate.rule})`).join("; ")}</p>
          )}
          <p className="console-help console-codes-line">
            Server codes: <code>{run.status}</code>{run.code && <> <code>{run.code}</code></>}
            {diagnosis && <> <code>{diagnosis.category}</code> <code>{diagnosis.cause}</code> <code>{diagnosis.action}</code></>}
          </p>
          <dl className="acra-detail-list">
            <div><dt>Last attempted</dt><dd>{formatTimestamp(run.started_at)} by {run.started_by}</dd></div>
            <div><dt>Retry worthwhile now</dt><dd>{diagnosis ? (diagnosis.retryable ? "Yes" : "No") : "—"}</dd></div>
            <div><dt>Earlier qualification still valid</dt><dd>{item.eligible_qualification
              ? (item.eligible_qualification.is_latest ? "This run is the valid qualification" : `Yes (passed ${formatTimestamp(item.eligible_qualification.finished_at ?? "")})`)
              : diagnosis?.supersedes_pass ? "No: this quality failure replaces any earlier pass" : "No"}</dd></div>
            {paid && <div><dt>Paid calls if retried</dt><dd>Up to {paid.calls ?? "—"} (reserved up to {microUsd(paid.estimate_micro_usd)}); available under the strictest limit {microUsd(paid.effective_remaining_micro_usd)}{paid.refusal ? ` · ${readable(paid.refusal, item.deployment)}` : ""}</dd></div>}
            {diagnosis && <div><dt>Recommended action</dt><dd>{actionText(diagnosis, item.deployment)}</dd></div>}
          </dl>
        </>
      )}
      {!run && paid && <p className="control-help">A first paid qualification makes up to {paid.calls ?? "—"} calls (reserved up to {microUsd(paid.estimate_micro_usd)}){paid.refusal ? `; refused now: ${readable(paid.refusal, item.deployment)}` : ""}.</p>}
      <div className="console-recovery-actions">
        {!run && usable && configured && item.endpoint && (
          <button type="button" className="btn btn-primary" disabled={busy} onClick={onRetry}>
            {paidRun ? "Run first qualification…" : "Run first qualification"}
          </button>
        )}
        {diagnosis?.retryable && usable && (
          <button type="button" className="btn btn-primary" disabled={busy} onClick={onRetry}>
            {diagnosis.cause === OUT_OF_DATE ? "Run new qualification…" : "Retry qualification…"}
          </button>
        )}
        {(diagnosis?.action === "TEST_CONNECTION" || diagnosis?.action === "RETRY_LATER") && usable && (
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={onTest}>Test connection</button>
        )}
        {/* D-102: Claude's limits are HR settings of their own, on the same Spending section. */}
        {diagnosis?.action === "REVIEW_SPENDING" && paid?.refusal !== "PROVIDER_LIMIT_EXHAUSTED" && (
          <Link className="btn btn-secondary" to={{ search: sectionSearch("spending") }}>{claude ? "Review Claude's limits" : "Review spending controls"}</Link>
        )}
        {escalate && (
          <button type="button" className="btn btn-secondary" onClick={() => {
            void navigator.clipboard?.writeText(escalationSummary(item)).then(() => setCopied(true), () => setCopied(false));
          }}>Copy escalation summary</button>
        )}
        {copied && <small role="status">Copied.</small>}
      </div>
      {paid?.refusal === "PROVIDER_LIMIT_EXHAUSTED" && (
        <p className="ds-banner ds-banner-warn" role="note" data-testid="key-owner-action">
          {(claude && CLAUDE_ACTION_TEXT.ESCALATE_KEY_OWNER) || ACTION_TEXT.ESCALATE_KEY_OWNER}
        </p>
      )}
      {escalate && <details><summary>Escalation summary</summary><pre className="control-help">{escalationSummary(item)}</pre></details>}
      {run && run.status !== "running" && (
        <details className="console-details">
          <summary>Gates and measures of the latest run</summary>
          <QualificationDetail qualification={run} deployment={item.deployment} />
        </details>
      )}
      <details className="console-details">
        <summary>{help.title}</summary>
        <ol className="console-troubleshooting">{help.steps.map((step) => <li key={step}>{step}</li>)}</ol>
      </details>
    </article>
  );
}

// Remote configurations (GPT-OSS 120B): the server sends closed codes, the page names them.
// "Fast" and "Balanced" are reasoning settings of one model, not separate models.
export const REASONING_LABEL: Record<string, string> = { low: "Fast", medium: "Balanced", high: "Thorough" };
const PROVIDER_LABEL: Record<string, string> = { OPENROUTER_DEEPINFRA: "OpenRouter / DeepInfra", ANTHROPIC: "Anthropic API" };
const THINKING_LABEL: Record<string, string> = { adaptive: "adaptive", between_tools: "between tool calls only" };
const SCOPE_LABEL: Record<string, string> = {
  VERIFIED_SYNTHETIC_CASES: "Verified synthetic cases only",
  APPROVED_SYNTHETIC_CASE: "The approved synthetic test case only",
  NOT_AUTHORISED: "Not authorised",
  PROVIDER_CONTROLS_MISSING: "Not available (provider spending controls missing)",
};

export function profileName(profile: Pick<ModelProfileView, "display_name" | "details">): string {
  const details = profile.details;
  if (!details?.model) return profile.display_name;
  const label = REASONING_LABEL[details.reasoning_effort ?? ""];
  return label ? `${details.model} — ${label}` : details.model;
}

function RemoteDetails({ details }: { details: Record<string, string> }) {
  const effort = details.reasoning_effort;
  return (
    <small className="control-help">
      Model: {details.model} · Provider: {PROVIDER_LABEL[details.provider] ?? details.provider} · Framework: Case-grounded Assistant
      {effort && <> · Reasoning: {effort.charAt(0).toUpperCase() + effort.slice(1)}</>}
      {details.thinking && <> · Thinking: {THINKING_LABEL[details.thinking] ?? details.thinking}</>}
      {" "}· External inference: {SCOPE_LABEL[details.scope] ?? details.scope}
      {details.decision && <> ({details.decision})</>}
    </small>
  );
}

// "GATES_FAILED:G-6,G-7" from a failed qualification: the gate ids keep their own spelling.
const GATES_FAILED = "GATES_FAILED:";
// "PREFLIGHT_FAILED:key.limit_set,..." from the remote model's connection test.
const PREFLIGHT_FAILED = "PREFLIGHT_FAILED:";
const REMOTE_DEPLOYMENT = "openrouter";
// D-099: Claude is also an external, paid API, under its own Anthropic safeguards.
const ANTHROPIC_DEPLOYMENT = "anthropic";
const isPaidRemote = (deployment: string | undefined) => deployment === REMOTE_DEPLOYMENT || deployment === ANTHROPIC_DEPLOYMENT;

export function readable(code: string | null | undefined, deployment?: string): string {
  if (!code) return "";
  if (deployment === ANTHROPIC_DEPLOYMENT && CLAUDE_REASON_TEXT[code]) return CLAUDE_REASON_TEXT[code];
  if (deployment === ANY_PROVIDER && NEUTRAL_REASON_TEXT[code]) return NEUTRAL_REASON_TEXT[code];
  if (code.startsWith(GATES_FAILED)) return `Gates failed: ${code.slice(GATES_FAILED.length).split(",").join(", ")}`;
  if (code.startsWith(PREFLIGHT_FAILED)) return `Preflight failed: ${code.slice(PREFLIGHT_FAILED.length).split(",").join(", ")}`;
  return REASON_TEXT[code] ?? code.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase());
}

// How often the page follows a running qualification, and how often the audit history is
// re-read while the page is open (events can come from other administrators or users).
export const RUNNING_REFRESH_MS = 3000;
export const AUDIT_REFRESH_MS = 15000;

function safeError(error: unknown): string {
  return error instanceof AiAssistantError ? error.message : "The AI assistant service could not complete this request.";
}

function value(item: unknown): string {
  if (item === null || item === undefined) return "—";
  if (typeof item === "number") return Number.isInteger(item) ? item.toLocaleString() : item.toFixed(3);
  if (typeof item === "object") return Object.entries(item as Record<string, unknown>).map(([key, entry]) => `${readable(key)}: ${value(entry)}`).join(" · ");
  return String(item);
}

const usd = (amount: string | null | undefined) => (amount ? `US$${amount}` : "—");


// Whole micro-USD from a US$ amount typed by HR ("0.25" -> 250000); null when not a plain amount.
export function toMicroUsd(text: string): number | null {
  const trimmed = text.trim();
  // D-098: no US$1 ceiling; up to US$999,999.999999 (inside the ledger's technical bound).
  if (!/^\d{1,6}(\.\d{1,6})?$/.test(trimmed)) return null;
  const [whole, fraction = ""] = trimmed.split(".");
  return Number(whole) * 1_000_000 + Number(fraction.padEnd(6, "0"));
}

const dollars = (micro: number) => (micro / 1_000_000).toFixed(2);
const exactDollars = (micro: number) => (micro / 1_000_000).toFixed(6);
// A stored amount as an input value, exact (never rounded), so saving it unchanged keeps it.
export const amountText = (micro: number) =>
  micro % 10_000 === 0 ? dollars(micro) : exactDollars(micro).replace(/0+$/, "");

function SpendingLimits({ budget, busy, onChanged }: { budget: ModelBudgetStatus; busy: boolean; onChanged: () => void }) {
  const daily = budget.daily;
  const controls = budget.controls;
  const lifetime = controls?.lifetime ?? null;
  const dailySeed = () => amountText(controls?.daily_cap_micro_usd ?? budget.daily_cap_micro_usd);
  const callsSeed = () => String(controls?.max_calls ?? "");
  const capSeed = () => (lifetime ? amountText(lifetime.cap_micro_usd) : "");
  const [dailyText, setDailyText] = useState(dailySeed);
  const [callsText, setCallsText] = useState(callsSeed);
  const [capText, setCapText] = useState(capSeed);
  // The revision and cap the inputs were filled from. When the stored values change (another
  // administrator, another tab), the inputs are refilled, so a save never sends values read
  // under an older revision with the newer one (which would bypass the server's check).
  const [formRevision, setFormRevision] = useState(controls?.revision ?? null);
  const [formCap, setFormCap] = useState(lifetime?.cap_micro_usd ?? null);
  const [confirmed, setConfirmed] = useState(false);
  const [dailyConfirmed, setDailyConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  if ((controls?.revision ?? null) !== formRevision) {
    setFormRevision(controls?.revision ?? null);
    setDailyText(dailySeed());
    setCallsText(callsSeed());
  }
  if ((lifetime?.cap_micro_usd ?? null) !== formCap) {
    setFormCap(lifetime?.cap_micro_usd ?? null);
    setCapText(capSeed());
    setConfirmed(false);
  }

  const dailyMicro = toMicroUsd(dailyText);
  const calls = /^\d{1,3}$/.test(callsText.trim()) ? Number(callsText.trim()) : null;
  const [lowCalls, highCalls] = controls?.max_calls_range ?? [1, 200];
  const controlsValid = dailyMicro !== null && dailyMicro <= (controls?.daily_cap_max_micro_usd ?? 1_000_000)
    && calls !== null && calls >= lowCalls && calls <= highCalls;
  // D-098: a higher daily limit needs HR's explicit confirmation (and the server checks the
  // key's own finite OpenRouter limit first); a lower one never does.
  const dailyRaising = controlsValid && controls !== undefined && dailyMicro! > controls.daily_cap_micro_usd;
  const capMicro = toMicroUsd(capText);
  const capValid = lifetime !== null && capMicro !== null
    && capMicro >= lifetime.opening_usage_micro_usd && capMicro <= lifetime.max_cap_micro_usd;
  const raising = capValid && lifetime !== null && capMicro! > lifetime.cap_micro_usd;
  const disabled = pending || busy;

  async function run(action: () => Promise<unknown>, done: string): Promise<void> {
    setPending(true);
    setMessage(null);
    try {
      await action();
      setMessage({ kind: "ok", text: done });
    } catch (error) {
      setMessage({ kind: "error", text: safeError(error) });
    } finally {
      setConfirmed(false);
      setDailyConfirmed(false);
      setPending(false);
      onChanged();
    }
  }

  return (
    <section className="card" aria-labelledby="spending-heading">
      <p className="card-kicker">GPT-OSS 120B · OpenRouter ledger</p>
      <h2 id="spending-heading">OpenRouter daily spending limit, lifetime limit and calls</h2>
      <Responsibilities label="Who can change the GPT-OSS limits" duties={GPT_OSS_SPENDING_DUTIES} />
      <p className="ds-banner ds-banner-warn" role="note">
        At most {usd(dollars(budget.daily_cap_micro_usd))} of reserved plus settled OpenRouter spending per Singapore calendar day ({budget.timezone}), for qualification and chat together. The lowest of this allowance, the lifetime ledger limit and the key's own OpenRouter limit applies. It does not rule out unexpected provider billing; a mismatch stops further calls.
      </p>
      <dl className="acra-detail-list">
        <div><dt>Settled today</dt><dd>{daily ? usd(daily.settled_today_usd) : LEDGER_UNREAD}</dd></div>
        <div><dt>In flight</dt><dd>{daily ? `${usd(daily.in_flight_usd)} (${daily.in_flight_calls} call${daily.in_flight_calls === 1 ? "" : "s"})` : LEDGER_UNREAD}</dd></div>
        <div><dt>Remaining today</dt><dd>{daily ? usd(daily.remaining_usd) : LEDGER_UNREAD}</dd></div>
        <div><dt>Lifetime headroom</dt><dd>{budget.ledger ? usd(budget.ledger.headroom_usd) : LEDGER_UNREAD}</dd></div>
        <div><dt>OpenRouter key limit</dt><dd>{budget.provider ? <>{usd(budget.provider.remaining_usd)} remaining{budget.provider.limit_usd ? ` of ${usd(budget.provider.limit_usd)}` : ""}{budget.provider.usage_usd ? `, ${usd(budget.provider.usage_usd)} used` : ""} ({budget.provider.passed ? "checks passed" : "checks failed"}, read {formatTimestamp(budget.provider.checked_at)})</> : "Not checked yet"}</dd></div>
        {budget.provider && <div><dt>Key limit resets</dt><dd>{budget.provider.limit_reset ? `Yes (${budget.provider.limit_reset}): not accepted, a lifetime key limit is required` : "Never (a lifetime key limit, as required)"}</dd></div>}
        {budget.provider && <div><dt>Account credits</dt><dd>Not read. The key's own limit above is what applies; only the key's owner can change it at OpenRouter.</dd></div>}
        <div><dt>Available now</dt><dd><strong>{usd(budget.effective_remaining_usd)}</strong> (the strictest of today's allowance, the lifetime headroom and the OpenRouter key limit)</dd></div>
        {controls && <div><dt>Chat calls this session</dt><dd>{controls.calls_used === null ? `GPT-OSS is not the active model (limit ${controls.max_calls} per session)` : `${controls.calls_used} used, ${controls.calls_remaining} remaining of ${controls.max_calls} (counted in the open paid session; a restart does not reset them)`}</dd></div>}
        <div><dt>Next daily reset</dt><dd>{formatTimestamp(budget.next_reset_at)} (midnight, Singapore)</dd></div>
        <div><dt>Status</dt><dd>{budget.ledger?.breaker_open ? `Stopped: ${readable(budget.ledger.breaker_code)} (an operator must reconcile)` : budget.refusal ? readable(budget.refusal) : "Calls allowed"}</dd></div>
      </dl>
      <button type="button" className="btn btn-secondary" disabled={disabled}
        onClick={() => void run(refreshProviderLimits, "OpenRouter limits refreshed.")}>Refresh OpenRouter Limits</button>
      <p className="control-help">Reads the key's limit only (no model call, no case data). The API key and its OpenRouter limit are never shown or changed here.</p>

      {controls && (
        <form aria-label="Daily and call limits" onSubmit={(event) => {
          event.preventDefault();
          if (!controlsValid || formRevision === null || (dailyRaising && !dailyConfirmed)) return;
          const revision = formRevision;
          const confirm = dailyRaising ? dailyMicro! : null;
          void run(() => saveSpendingControls(revision, dailyMicro!, calls!, confirm), "Limits saved. They apply to the active model now.");
        }}>
          <h3>Daily and call limits</h3>
          <p className="control-help">
            {controls.daily_cap_source === "hr" || controls.max_calls_source === "hr"
              ? `Set by ${controls.changed_by ?? "HR"}${controls.changed_at ? ` ${formatTimestamp(controls.changed_at)}` : ""}.`
              : "Not set here yet: the server's defaults apply."}
            {" "}Lowering a limit never resets today's spending or the activation's call count.
          </p>
          <label className="control-help" htmlFor="daily-limit-input">Daily limit (US$; default US${dollars(controls.daily_cap_default_micro_usd ?? 1_000_000)}, may be higher or lower)</label>{" "}
          <input id="daily-limit-input" inputMode="decimal" value={dailyText} onChange={(event) => { setDailyText(event.target.value); setDailyConfirmed(false); }} disabled={disabled} />{" "}
          <label className="control-help" htmlFor="call-limit-input">Chat calls per paid session ({lowCalls} to {highCalls})</label>{" "}
          <input id="call-limit-input" inputMode="numeric" value={callsText} onChange={(event) => setCallsText(event.target.value)} disabled={disabled} />{" "}
          {dailyRaising && (
            <label className="control-help">
              <input type="checkbox" checked={dailyConfirmed} onChange={(event) => setDailyConfirmed(event.target.checked)} disabled={disabled} data-testid="daily-raise-confirm" />
              {" "}I confirm raising the daily limit to {usd(exactDollars(dailyMicro!))}. The server first checks that the OpenRouter key has its own finite limit; the lifetime and key limits still apply.
            </label>
          )}{" "}
          <button type="submit" className="btn btn-primary" disabled={disabled || !controlsValid || !controls.readable || (dailyRaising && !dailyConfirmed)}>Save Limits</button>
          {!controlsValid && <p className="control-help" role="status">Enter a daily limit in US$ (0 or more) and {lowCalls} to {highCalls} calls.</p>}
        </form>
      )}

      {lifetime && (
        <form aria-label="Lifetime limit" onSubmit={(event) => {
          event.preventDefault();
          if (!capValid || (raising && !confirmed)) return;
          const cap = capMicro!;
          const shown = lifetime.cap_micro_usd;
          void run(() => saveLifetimeCap(cap, raising ? cap : null, shown), "Lifetime limit updated.");
        }}>
          <h3>Lifetime limit (ledger)</h3>
          <p className="control-help">
            The key's usage when the ledger was created: {usd(exactDollars(lifetime.opening_usage_micro_usd))}. Current limit {usd(exactDollars(lifetime.cap_micro_usd))}; committed {usd(exactDollars(lifetime.committed_micro_usd))}. It may be set at or above the opening usage, with no fixed ceiling; raising it needs your confirmation, a finite OpenRouter key limit and a ledger that reconciles with OpenRouter. The ledger keeps every charge and is never replaced.
          </p>
          <label className="control-help" htmlFor="lifetime-limit-input">New lifetime limit (US$)</label>{" "}
          <input id="lifetime-limit-input" inputMode="decimal" value={capText} onChange={(event) => { setCapText(event.target.value); setConfirmed(false); }} disabled={disabled} />{" "}
          {raising && (
            <label className="control-help">
              <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} disabled={disabled} />
              {" "}I confirm raising the lifetime limit to {usd(exactDollars(capMicro!))}. The server first checks the ledger against OpenRouter's reported usage.
            </label>
          )}{" "}
          <button type="submit" className="btn btn-primary" disabled={disabled || !capValid || capMicro === lifetime.cap_micro_usd || (raising && !confirmed)}>Update Lifetime Limit</button>
          {!capValid && <p className="control-help" role="status">Enter an amount of at least {usd(exactDollars(lifetime.opening_usage_micro_usd))}.</p>}
        </form>
      )}
      {message && <p className={message.kind === "error" ? "ds-banner ds-banner-warn" : "control-help"} role={message.kind === "error" ? "alert" : "status"}>{message.text}</p>}
    </section>
  );
}

const KEY_VARIABLE: Record<CredentialProvider, string> = {
  openrouter: "OPENROUTER_API_KEY",
  anthropic: "AI_ASSISTANT_ANTHROPIC_API_KEY",
};

function credentialSource(credential: ModelCredentialStatus, provider: CredentialProvider): string {
  switch (credential.source) {
    case "hr_session":
      return "Session key entered on this page. Kept in the AI Assistant's memory only and used first; it ends when the HR session that entered it signs out or expires, when it is cleared, or when the service restarts.";
    case "environment":
      return `Server key from the process environment (${KEY_VARIABLE[provider]}). A session key entered here is used instead while it lasts.`;
    case "env_file":
      return "Server key from apps/assistant/.env. A session key entered here is used instead while it lasts.";
    default:
      return "No key is set on the server and none was entered for this session.";
  }
}

const FALLBACK_TEXT: Record<string, string> = {
  environment: "the server key from the process environment",
  env_file: "the server key from apps/assistant/.env",
  none: "no key (the provider's models become unavailable)",
};

function credentialLabel(credential: ModelCredentialStatus): string {
  if (credential.status === "configured") return "Configured";
  if (credential.status === "invalid") return "Invalid";
  if (credential.status === "unverified") return "Session Not Verified";
  return "Not Configured";
}

const secondsText = (seconds: number | null | undefined) =>
  typeof seconds === "number" ? formatTimestamp(new Date(seconds * 1000).toISOString()) : "—";

/** D-106: one provider's API key: the server key's source, and a key HR enters for this session. */
export function ProviderKey({ provider, title, credential, testProfileId, busy, onChanged }: {
  provider: CredentialProvider;
  title: string;
  credential: ModelCredentialStatus | null;
  testProfileId: string | null;
  busy: boolean;
  onChanged: () => void;
}) {
  // The key lives only in this input until it is sent; it is never stored in the browser.
  const [key, setKey] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const label = credential ? credentialLabel(credential) : "Status Unavailable";
  const inputId = `${provider}-key-input`;
  const headingId = `${provider}-key-heading`;

  async function run(action: () => Promise<unknown>, done: string): Promise<void> {
    setPending(true);
    setMessage(null);
    try {
      await action();
      setMessage({ kind: "ok", text: done });
    } catch (error) {
      setMessage({ kind: "error", text: safeError(error) });
    } finally {
      setKey("");
      setPending(false);
      onChanged();
    }
  }

  return (
    <section className="console-subcard" aria-labelledby={headingId} data-testid={`${provider}-key`}>
      <h3 id={headingId}>{title} — {label}</h3>
      {credential ? (
        <dl className="acra-detail-list">
          <div><dt>Status</dt><dd><span className={`tag ${credential.status === "configured" ? "tag-accent" : "tag-warn"}`} role="status">{label}</span></dd></div>
          <div><dt>Source</dt><dd>{credentialSource(credential, provider)}{credential.source === "hr_session" && credential.set_by && <> Entered by {credential.set_by} at {secondsText(credential.set_at)}.</>}</dd></div>
          {credential.source === "hr_session" && (
            <>
              <div><dt>Expiry</dt><dd>Ends with the HR session that entered it, and no later than {secondsText(credential.expires_at)}.{credential.verified_at ? <> Session last checked {secondsText(credential.verified_at)}.</> : null}</dd></div>
              <div><dt>After it ends</dt><dd>The AI Assistant uses {FALLBACK_TEXT[credential.fallback ?? "none"]}, only after a fresh preflight confirms the same provider account or workspace. Models never switch automatically.</dd></div>
            </>
          )}
          {credential.status === "unverified" && (
            <div><dt>Why not used</dt><dd>The AI Assistant cannot check the HR session that entered this key right now, so the key is held back and no server key is used in its place.</dd></div>
          )}
        </dl>
      ) : <p className="console-help">The server did not send this key's status.</p>}
      <form onSubmit={(event) => { event.preventDefault(); const value = key; void run(() => saveModelCredential(value, provider), "Key saved for this session on the server."); }}>
        <label className="control-help" htmlFor={inputId}>API key for this session</label>{" "}
        <input id={inputId} type="password" autoComplete="off" spellCheck={false} value={key}
          onChange={(event) => setKey(event.target.value)} disabled={pending || busy} />{" "}
        <button type="submit" className="btn btn-primary" disabled={pending || busy || !key}>Save for Session</button>{" "}
        {credential?.source === "hr_session" && (
          <button type="button" className="btn btn-secondary" disabled={pending || busy}
            onClick={() => void run(() => clearModelCredential(provider), "Session key cleared.")}>Clear Session Key</button>
        )}{" "}
        {testProfileId && (
          <button type="button" className="btn btn-secondary" disabled={pending || busy || credential?.status !== "configured"}
            onClick={() => void run(() => testModelConnection(testProfileId), "Connection test finished; see the configuration's result above.")}>Test Connection</button>
        )}
      </form>
      <p className="console-help">Never stored in the browser. Test Connection is a free preflight (no model call, no case data).</p>
      {message && <p className={message.kind === "error" ? "ds-banner ds-banner-warn" : "control-help"} role={message.kind === "error" ? "alert" : "status"}>{message.text}</p>}
    </section>
  );
}

// D-107: the owner's four confirmations, in words (the server checks the codes).
export const CONFIRMATION_TEXT: Record<string, string> = {
  dedicated_workspace: "This key belongs to an Anthropic workspace used only for this FYP project.",
  workspace_limit_set: "That workspace has a monthly spend limit set in the Anthropic Console, no higher than the amount below.",
  inference_key_only: "It is an inference API key, not an Admin key.",
  key_revoked_at_fyp_end: "The key will be revoked when the FYP ends.",
};

/** D-107: HR sets Claude up here (no decision or attestation settings on the server). */
export function ClaudeSetup({ setup, busy, onChanged }: { setup: AnthropicSetup; busy: boolean; onChanged: () => void }) {
  const record = setup.record;
  const [limit, setLimit] = useState("");
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [read, setRead] = useState<{ outcome: string; code: string | null; workspace_id: string | null } | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const workspace = setup.workspace_read?.workspace_id ?? null;
  const limitMicro = toMicroUsd(limit);
  const allConfirmed = setup.confirmations_required.every((code) => checked[code]);
  const limitValid = limitMicro !== null && limitMicro >= 1 && limitMicro <= setup.workspace_limit_max_micro_usd;
  const revision = record?.revision ?? 0;

  async function run(action: () => Promise<unknown>, done: string): Promise<void> {
    setPending(true);
    setMessage(null);
    try {
      await action();
      setMessage({ kind: "ok", text: done });
    } catch (error) {
      setMessage({ kind: "error", text: safeError(error) });
    } finally {
      setPending(false);
      onChanged();
    }
  }

  async function readWorkspace(): Promise<void> {
    setPending(true);
    setMessage(null);
    try {
      setRead(await readAnthropicWorkspace());
    } catch (error) {
      setMessage({ kind: "error", text: safeError(error) });
    } finally {
      setPending(false);
      onChanged();
    }
  }

  const disabled = pending || busy || !setup.managed || !setup.readable;
  return (
    <section className="console-subcard" aria-labelledby="claude-setup-heading" data-testid="claude-setup">
      <h3 id="claude-setup-heading">Claude setup — {setup.enabled ? "Enabled for verified synthetic cases" : "Not enabled"}</h3>
      {!setup.managed && <p className="console-help">Model management is not configured on this server, so Claude cannot be set up here.</p>}
      {!setup.readable && <p className="ds-banner ds-banner-warn" role="alert">Claude's setup could not be read, so Claude is off until it can be.</p>}
      {!setup.local_deployment && <p className="ds-banner ds-banner-warn" role="note">This server is not the approved local development set-up (loopback CLM backend and local browser origins), so Claude cannot be enabled here.</p>}
      {setup.source === "environment" && <p className="console-help">Claude is currently configured on the server (D-099 settings). Setting it up here replaces that configuration.</p>}
      {record && (
        <dl className="acra-detail-list">
          <div><dt>Status</dt><dd>{record.enabled ? "Enabled" : "Disabled"} by {record.changed_by}, {formatTimestamp(record.changed_at)}</dd></div>
          <div><dt>Workspace</dt><dd><code className="console-code">{record.workspace_id}</code> (as the key reported it; every reply must name it)</dd></div>
          <div><dt>Monthly limit</dt><dd>US${dollars(record.workspace_limit_micro_usd)}, owner-confirmed. It is not read from Anthropic, and the app cannot verify it.</dd></div>
          <div><dt>Readiness</dt><dd>{setup.readiness ? readable(setup.readiness, ANTHROPIC_DEPLOYMENT) : "Ready: run Test connection, qualify Balanced on Models & Overview, then activate."}</dd></div>
        </dl>
      )}
      {!record?.enabled && (
        <ol className="console-troubleshooting">
          <li>
            Enter the Anthropic key above for this session (or rely on the server key), then read the workspace it reports. This is a free model read, with no model call and no case data.{" "}
            <button type="button" className="btn btn-secondary" disabled={disabled || !setup.local_deployment} onClick={() => void readWorkspace()}>Read Workspace</button>
            {read && read.outcome !== "passed" && <span className="control-help"> {read.code ? readable(read.code, ANTHROPIC_DEPLOYMENT) : "The read did not pass."}</span>}
          </li>
          <li>
            Workspace the key reports: {workspace ? <code className="console-code">{workspace}</code> : "not read yet with the key now in use"}
            {record && workspace && record.workspace_id !== workspace && <span className="ds-banner ds-banner-warn" role="note"> This differs from the workspace Claude was set up for; it cannot be changed here.</span>}
          </li>
          <li>
            <fieldset className="console-fieldset">
              <legend>The owner confirms</legend>
              {setup.confirmations_required.map((code) => (
                <label key={code} className="control-help console-check">
                  <input type="checkbox" data-testid={`confirm-${code}`} checked={Boolean(checked[code])} disabled={disabled}
                    onChange={(event) => setChecked({ ...checked, [code]: event.target.checked })} />{" "}
                  {CONFIRMATION_TEXT[code] ?? code}
                </label>
              ))}
              <label className="control-help" htmlFor="claude-workspace-limit">Workspace monthly limit (US$, at most {dollars(setup.workspace_limit_max_micro_usd)})</label>{" "}
              <input id="claude-workspace-limit" inputMode="decimal" value={limit} disabled={disabled}
                onChange={(event) => setLimit(event.target.value)} />
            </fieldset>
          </li>
          <li>
            <button type="button" className="btn btn-primary"
              disabled={disabled || !setup.local_deployment || !workspace || !allConfirmed || !limitValid}
              onClick={() => void run(() => saveAnthropicEnablement({
                expected_revision: revision, enabled: true, workspace_id: workspace ?? "",
                workspace_limit_micro_usd: limitMicro ?? 0, confirmations: setup.confirmations_required,
              }), "Claude enabled for verified synthetic cases.")}>Enable Claude for Verified Synthetic Cases</button>
          </li>
        </ol>
      )}
      {setup.enabled && (
        <button type="button" className="btn btn-secondary" disabled={disabled}
          onClick={() => void run(() => saveAnthropicEnablement({ expected_revision: revision, enabled: false }), "Claude disabled. Claude calls stop at the next question; no other model is switched in.")}>Disable Claude</button>
      )}
      <p className="console-help">Claude only ever receives verified synthetic cases (see Data Access &amp; Privacy). The workspace check, Claude's own ledger, its daily, lifetime and call limits, and reconciliation still apply.</p>
      {message && <p className={message.kind === "error" ? "ds-banner ds-banner-warn" : "control-help"} role={message.kind === "error" ? "alert" : "status"}>{message.text}</p>}
    </section>
  );
}

// --- D-100 Phase 2: Providers and Spending & Limits ---------------------------------------------
// Presentation only, from the overview the page already reads (no new request). The server sends
// GPT-OSS's key and spending view in `budget`. For Claude it sends only each configuration's
// status, codes, connection test and paid-qualification estimate, so nothing more is shown: no
// Claude key status, usage, ledger headroom or reconciliation time is inferred.

type ProviderKind = "openrouter" | "anthropic" | "local";

/** Built-in remote configurations (`source` "code") other than Claude are GPT-OSS via OpenRouter. */
function providerKind(item: Pick<ModelProfileView, "deployment" | "source">): ProviderKind {
  if (item.deployment === ANTHROPIC_DEPLOYMENT) return "anthropic";
  return item.source === "code" ? "openrouter" : "local";
}

const LEDGER_UNREAD = "Unavailable: the ledger could not be read";

type DutyHolder = "hr" | "operator" | "owner";
interface Duty { who: DutyHolder; text: string }
const DUTY_LABEL: Record<DutyHolder, string> = {
  hr: "You (HR), on this page",
  operator: "An operator or IT, on the server",
  owner: "The key or workspace owner, at the provider",
};

/** Who may change what: HR on this page, an operator on the server, the owner at the provider. */
function Responsibilities({ label, duties }: { label: string; duties: Duty[] }) {
  return (
    <div className="console-duties" role="group" aria-label={label}>
      {(["hr", "operator", "owner"] as const).map((who) => {
        const items = duties.filter((duty) => duty.who === who);
        if (items.length === 0) return null;
        return (
          <div key={who} className={`console-duty console-duty--${who}`}>
            <span className="console-label">{DUTY_LABEL[who]}</span>
            <ul>{items.map((duty) => <li key={duty.text}>{duty.text}</li>)}</ul>
          </div>
        );
      })}
    </div>
  );
}

const GPT_OSS_SPENDING_DUTIES: Duty[] = [
  { who: "hr", text: "Set the daily limit and chat calls per paid session; lowering needs no confirmation, raising the daily limit does." },
  { who: "hr", text: "Raise or lower the lifetime ledger limit (a raise needs your confirmation and a ledger that reconciles)." },
  { who: "operator", text: "Reconcile the ledger with OpenRouter when calls are stopped (scripts/budget_ledger.py)." },
  { who: "owner", text: "Set the key's own lifetime limit at OpenRouter. It is never shown or changed here." },
];

const OPENROUTER_DUTIES: Duty[] = [
  { who: "hr", text: "Enter or clear a session key (memory only, used first, ends with your session)." },
  { who: "operator", text: "Optionally set a server key (process environment or apps/assistant/.env), used when no session key is live." },
  { who: "hr", text: "Run Test connection (a free preflight that reads the key's limit; no model call, no case data)." },
  { who: "hr", text: "Change the GPT-OSS limits in Spending & Limits." },
  { who: "operator", text: "Authorise the remote test mode and reconcile the ledger." },
  { who: "owner", text: "Set the key's own lifetime limit at OpenRouter." },
];

const ANTHROPIC_DUTIES: Duty[] = [
  { who: "hr", text: "Run Test connection (a free workspace and model read), confirm a paid qualification and activate, from Models & Overview." },
  { who: "hr", text: "Enter or clear a session inference key for Balanced and Fast (memory only, used first, ends with your session; it must belong to the attested workspace)." },
  { who: "hr", text: "Set Claude up here: read the workspace the key reports (free), confirm it with the owner's four confirmations and monthly limit, and enable Claude for verified synthetic cases. Disable it at any time." },
  { who: "operator", text: "Optionally set a server inference key (AI_ASSISTANT_ANTHROPIC_API_KEY or apps/assistant/.env), used when no session key is live. No decision or attestation settings are needed." },
  { who: "hr", text: "Change Claude's own daily, call and lifetime limits in Spending & Limits." },
  { who: "operator", text: "Reconcile Claude's ledger with the Anthropic Console (scripts/budget_ledger.py --anthropic) before any raise or paid run." },
  { who: "owner", text: "Keep the dedicated Anthropic workspace's monthly spend limit (attested at most US$30.00) in the Anthropic Console." },
];

const LOCAL_DUTIES: Duty[] = [
  { who: "hr", text: "Run Test connection, qualify and activate, from Models & Overview." },
  { who: "operator", text: "Set the environment baseline on the server, add or change profiles in the model profiles file, and keep the model servers running." },
];

// Codes that say the Anthropic key itself is the problem (all from the server).
const ANTHROPIC_KEY_CODES = ["CREDENTIAL_MISSING", "CREDENTIAL_INVALID", "CREDENTIAL_ADMIN_REFUSED", "CREDENTIAL_SESSION_UNVERIFIED"];

/** Every closed code the server reported for these configurations, once each, in order. */
function reportedCodes(items: ModelProfileView[]): string[] {
  const codes = new Set<string>();
  for (const item of items) {
    for (const code of [item.reason, ...item.activation_blockers, item.paid_qualification?.refusal, item.connection_test?.code]) {
      if (code) codes.add(code);
    }
  }
  return [...codes];
}

function connectionText(item: ModelProfileView): string {
  const test = item.connection_test;
  if (!test) return "Not run";
  const when = test.at ? `, ${formatTimestamp(test.at)}${test.by_user ? ` by ${test.by_user}` : ""}` : "";
  return `${readable(test.outcome)}${test.code ? ` · ${readable(test.code, item.deployment)}` : ""}${when}`;
}

/** The provider's configurations, each with its own availability and last connection test. */
function ProviderConfigurations({ items }: { items: ModelProfileView[] }) {
  return (
    <ul className="console-config-list" aria-label="Configurations">
      {items.map((item) => (
        <li key={item.profile_id}>
          <span className="console-config-list__name">
            {profileName(item)}
            {item.active && <> <Chip state={{ label: "Active", tone: "active" }} /></>}
          </span>
          <Chip state={availabilityState(item)} />
          <span className="console-config-list__detail">
            Connection test: {connectionText(item)}
            {item.reason && <><br />{readable(item.reason, item.deployment)}</>}
          </span>
        </li>
      ))}
    </ul>
  );
}

function ReportedCodes({ codes, deployment }: { codes: string[]; deployment: string }) {
  if (codes.length === 0) return <p className="console-help">The server reports no refusal or readiness code for these configurations.</p>;
  return (
    <ul className="console-codes" aria-label="Codes reported by the server">
      {codes.map((code) => <li key={code}><code>{code}</code> {readable(code, deployment)}</li>)}
    </ul>
  );
}

function ProviderCard({ kind, title, subtitle, children }: { kind: ProviderKind; title: string; subtitle: string; children: ReactNode }) {
  const headingId = `provider-${kind}-heading`;
  return (
    <section className="card console-provider" aria-labelledby={headingId} data-testid={`provider-${kind}`}>
      <div className="console-provider__head">
        <h2 id={headingId}>{title}</h2>
        <span>{subtitle}</span>
      </div>
      {children}
    </section>
  );
}

function ProvidersSection({ overview, busy, onChanged }: { overview: ModelOverview; busy: boolean; onChanged: () => void }) {
  const byKind = (kind: ProviderKind) => overview.profiles.filter((item) => providerKind(item) === kind);
  const openrouter = byKind("openrouter");
  const anthropic = byKind("anthropic");
  const local = byKind("local");
  const budget = overview.budget?.configured ? overview.budget : null;
  const anthropicCodes = reportedCodes(anthropic);
  const keyIssue = anthropicCodes.find((code) => ANTHROPIC_KEY_CODES.includes(code));
  const stale = anthropicCodes.includes("RECONCILIATION_STALE");
  const claudeUsable = anthropic.filter((item) => item.status === "selectable").length;
  // D-106: the shared Anthropic key, and the configuration its free connection test reads.
  const claudeCredential = overview.budget?.claude?.credential ?? null;
  const claudeSelectable = anthropic.filter((item) => item.status === "selectable");
  const claudeTestId = (claudeSelectable.find((item) => item.profile_id.endsWith("_medium")) ?? claudeSelectable[0])?.profile_id ?? null;
  return (
    <>
      {(openrouter.length > 0 || budget) && (
        <ProviderCard kind="openrouter" title="OpenRouter" subtitle="GPT-OSS 120B through OpenRouter / DeepInfra · external, paid">
          <ProviderConfigurations items={openrouter} />
          {budget ? (
            <>
              <dl className="acra-detail-list">
                <div><dt>Key limit check</dt><dd>{budget.provider ? `${budget.provider.passed ? "Checks passed" : "Checks failed"}, read ${formatTimestamp(budget.provider.checked_at)}` : "Not checked yet in this server process. Run Test connection."}</dd></div>
                <div><dt>Spending</dt><dd>Its own ledger and HR-managed limits: see <Link to={{ search: sectionSearch("spending") }}>Spending &amp; Limits</Link>.</dd></div>
              </dl>
              <ProviderKey provider="openrouter" title="OpenRouter API Key" credential={budget.credential} busy={busy}
                testProfileId={openrouter.find((item) => item.deployment === REMOTE_DEPLOYMENT && item.status === "selectable")?.profile_id ?? null}
                onChanged={onChanged} />
            </>
          ) : <p className="ds-banner" role="status">The remote test mode is not configured on this server, so there is no provider key to manage here.</p>}
          <Responsibilities label="Who manages OpenRouter" duties={OPENROUTER_DUTIES} />
        </ProviderCard>
      )}

      {anthropic.length > 0 && (
        <ProviderCard kind="anthropic" title="Anthropic API" subtitle="One provider for Claude Sonnet 5.5 Balanced and Fast · external, paid · set up by HR (D-107)">
          <p className="console-help">Balanced and Fast are two configurations (reasoning settings) of one model on one Anthropic provider: they share the key, the workspace and Claude's single ledger, and each needs its own passing qualification.</p>
          <ProviderConfigurations items={anthropic} />
          <dl className="acra-detail-list">
            <div><dt>Availability</dt><dd>{claudeUsable} of {anthropic.length} configuration{anthropic.length === 1 ? "" : "s"} available</dd></div>
            <div><dt>Inference key</dt><dd>{keyIssue
              ? readable(keyIssue, ANTHROPIC_DEPLOYMENT)
              : "Shared by Balanced and Fast; its source and status are below."}</dd></div>
            <div><dt>Workspace check</dt><dd>Test connection reads the attested workspace and the model (free; no case data). Each configuration's last result is listed above.</dd></div>
            <div><dt>Spending</dt><dd>Claude's own ledger and its own HR limits (at most US$30.00 lifetime within the attested workspace limit, US$5.00 a Singapore day and 20 chat calls a paid session). The GPT-OSS controls never apply to it. <Link to={{ search: sectionSearch("spending") }}>Review Claude's limits</Link>.</dd></div>
            <div><dt>Reconciliation</dt><dd>{stale
              ? readable("RECONCILIATION_STALE", ANTHROPIC_DEPLOYMENT)
              : "An operator reconciles Claude's ledger with the Anthropic Console; Spending & Limits shows when it was last done. A raise or a paid call is refused when it is out of date."}</dd></div>
          </dl>
          <ProviderKey provider="anthropic" title="Anthropic API Key" credential={claudeCredential} busy={busy}
            testProfileId={claudeTestId}
            onChanged={onChanged} />
          {overview.anthropic_setup && <ClaudeSetup setup={overview.anthropic_setup} busy={busy} onChanged={onChanged} />}
          <h3 className="console-subheading">Codes reported by the server</h3>
          <ReportedCodes codes={anthropicCodes} deployment={ANTHROPIC_DEPLOYMENT} />
          <Responsibilities label="Who manages the Anthropic API" duties={ANTHROPIC_DUTIES} />
        </ProviderCard>
      )}

      {local.length > 0 && (
        <ProviderCard kind="local" title="Server-configured models" subtitle="The environment baseline and IT's model profiles · no spending ledger, no paid-run confirmation">
          <ProviderConfigurations items={local} />
          <p className="console-help">IT sets the environment baseline in the server environment. Profiles from the model profiles file must use a local loopback endpoint; any other is listed as not available. Neither has a key managed on this page or a spending ledger, and their availability depends on the model servers IT runs.</p>
          <Responsibilities label="Who manages local models" duties={LOCAL_DUTIES} />
        </ProviderCard>
      )}
    </>
  );
}

/** D-102: Claude's own HR limits on its separate Anthropic ledger (never GPT-OSS's). */
function ClaudeLimits({ claude, busy, onChanged }: { claude: ModelClaudeBudget; busy: boolean; onChanged: () => void }) {
  const controls = claude.controls;
  const lifetime = controls.lifetime;
  const daily = claude.daily;
  const dailySeed = () => amountText(controls.daily_cap_micro_usd);
  const callsSeed = () => String(controls.max_calls);
  const capSeed = () => (lifetime ? amountText(lifetime.cap_micro_usd) : "");
  const [dailyText, setDailyText] = useState(dailySeed);
  const [callsText, setCallsText] = useState(callsSeed);
  const [capText, setCapText] = useState(capSeed);
  // As for GPT-OSS: when the stored values change (another administrator, another tab), the
  // inputs are refilled, so a save never sends values read under an older revision.
  const [formRevision, setFormRevision] = useState(controls.revision);
  const [formCap, setFormCap] = useState(lifetime?.cap_micro_usd ?? null);
  const [dailyConfirmed, setDailyConfirmed] = useState(false);
  const [callsConfirmed, setCallsConfirmed] = useState(false);
  const [capConfirmed, setCapConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  if (controls.revision !== formRevision) {
    setFormRevision(controls.revision);
    setDailyText(dailySeed());
    setCallsText(callsSeed());
    setDailyConfirmed(false);
    setCallsConfirmed(false);
  }
  if ((lifetime?.cap_micro_usd ?? null) !== formCap) {
    setFormCap(lifetime?.cap_micro_usd ?? null);
    setCapText(capSeed());
    setCapConfirmed(false);
  }

  const [lowDaily, highDaily] = controls.daily_cap_range;
  const [lowCalls, highCalls] = controls.max_calls_range;
  const dailyMicro = toMicroUsd(dailyText);
  const calls = /^\d{1,2}$/.test(callsText.trim()) ? Number(callsText.trim()) : null;
  const controlsValid = dailyMicro !== null && dailyMicro >= lowDaily && dailyMicro <= highDaily
    && calls !== null && calls >= lowCalls && calls <= highCalls;
  const dailyRaising = controlsValid && dailyMicro! > controls.daily_cap_micro_usd;
  // QG L1: more calls per activation needs the same confirmation and reconciliation.
  const callsRaising = controlsValid && calls! > controls.max_calls;
  const unconfirmed = (dailyRaising && !dailyConfirmed) || (callsRaising && !callsConfirmed);
  const capMicro = toMicroUsd(capText);
  // QG L2: a strictly lower cap is always allowed (above the opening usage), even when no
  // workspace limit is attested; anything else stays within the attested ceiling.
  const capValid = lifetime !== null && capMicro !== null && capMicro > lifetime.opening_usage_micro_usd
    && (capMicro < lifetime.cap_micro_usd || capMicro <= lifetime.max_cap_micro_usd);
  const capRaising = capValid && capMicro! > lifetime!.cap_micro_usd;
  const disabled = pending || busy;

  async function run(action: () => Promise<unknown>, done: string): Promise<void> {
    setPending(true);
    setMessage(null);
    try {
      await action();
      setMessage({ kind: "ok", text: done });
    } catch (error) {
      setMessage({ kind: "error", text: safeError(error) });
    } finally {
      setDailyConfirmed(false);
      setCallsConfirmed(false);
      setCapConfirmed(false);
      setPending(false);
      onChanged();
    }
  }

  return (
    <>
      <dl className="acra-detail-list" aria-label="Claude spending">
        <div><dt>Settled today</dt><dd>{daily ? usd(exactDollars(daily.settled_today_micro_usd)) : LEDGER_UNREAD}</dd></div>
        <div><dt>Remaining today</dt><dd>{daily ? usd(daily.remaining_usd) : LEDGER_UNREAD}</dd></div>
        <div><dt>Lifetime headroom</dt><dd>{claude.ledger ? usd(claude.ledger.headroom_usd) : LEDGER_UNREAD}</dd></div>
        <div><dt>Anthropic workspace limit</dt><dd>{claude.workspace_limit_micro_usd > 0 ? `${usd(dollars(claude.workspace_limit_micro_usd))} a month (owner-confirmed, not read from Anthropic; changed only in the Anthropic Console)` : "Not confirmed yet (set up Claude in Providers → Anthropic)"}</dd></div>
        <div><dt>Last reconciled</dt><dd>{claude.ledger?.reconciled_at ? formatTimestamp(claude.ledger.reconciled_at) : "Never (an operator reconciles the Claude ledger)"}</dd></div>
        <div><dt>Available now</dt><dd><strong>{usd(claude.effective_remaining_usd)}</strong> (the stricter of today's allowance and the lifetime headroom)</dd></div>
        <div><dt>Chat calls this session</dt><dd>{controls.calls_used !== null
          ? `${controls.calls_used} used, ${controls.calls_remaining} remaining of ${controls.max_calls}`
          : claude.ledger === null
            ? `${LEDGER_UNREAD} (limit ${controls.max_calls} per session)`
            : `No Claude configuration is active (limit ${controls.max_calls} per session)`}</dd></div>
        <div><dt>Next daily reset</dt><dd>{formatTimestamp(claude.next_reset_at)} (midnight, Singapore)</dd></div>
        <div><dt>Status</dt><dd>{claude.ledger?.breaker_open ? `Stopped: ${readable(claude.ledger.breaker_code, ANTHROPIC_DEPLOYMENT)} (an operator must reconcile)` : claude.refusal ? readable(claude.refusal, ANTHROPIC_DEPLOYMENT) : "Calls allowed"}</dd></div>
      </dl>

      <form aria-label="Claude daily and call limits" onSubmit={(event) => {
        event.preventDefault();
        if (!controlsValid || formRevision === null || unconfirmed) return;
        const revision = formRevision;
        const confirm = dailyRaising ? dailyMicro! : null;
        const confirmCalls = callsRaising ? calls! : null;
        void run(() => saveClaudeSpendingControls(revision, dailyMicro!, calls!, confirm, confirmCalls), "Claude's limits saved. They apply to an active Claude configuration now.");
      }}>
        <h3>Claude daily and call limits</h3>
        <p className="control-help">
          {controls.daily_cap_source === "hr" || controls.max_calls_source === "hr"
            ? `Set by ${controls.changed_by ?? "HR"}${controls.changed_at ? ` ${formatTimestamp(controls.changed_at)}` : ""}.`
            : "Not set here yet: the server's defaults apply."}
          {" "}Lowering a limit never resets today's spending or the activation's call count.
        </p>
        <label className="control-help" htmlFor="claude-daily-limit-input">Daily limit (US$; at most US${dollars(highDaily)})</label>{" "}
        <input id="claude-daily-limit-input" inputMode="decimal" value={dailyText} onChange={(event) => { setDailyText(event.target.value); setDailyConfirmed(false); }} disabled={disabled} />{" "}
        <label className="control-help" htmlFor="claude-call-limit-input">Chat calls per paid session ({lowCalls} to {highCalls})</label>{" "}
        <input id="claude-call-limit-input" inputMode="numeric" value={callsText} onChange={(event) => { setCallsText(event.target.value); setCallsConfirmed(false); }} disabled={disabled} />{" "}
        {dailyRaising && (
          <label className="control-help">
            <input type="checkbox" checked={dailyConfirmed} onChange={(event) => setDailyConfirmed(event.target.checked)} disabled={disabled} data-testid="claude-daily-raise-confirm" />
            {" "}I confirm raising Claude's daily limit to {usd(exactDollars(dailyMicro!))}. The server first checks that the Claude ledger was reconciled with the Anthropic Console within 24 hours.
          </label>
        )}{" "}
        {callsRaising && (
          <label className="control-help">
            <input type="checkbox" checked={callsConfirmed} onChange={(event) => setCallsConfirmed(event.target.checked)} disabled={disabled} data-testid="claude-calls-raise-confirm" />
            {" "}I confirm raising Claude's call limit to {calls} chat calls per paid session. The server first checks that the Claude ledger was reconciled with the Anthropic Console within 24 hours.
          </label>
        )}{" "}
        <button type="submit" className="btn btn-primary" disabled={disabled || !controlsValid || !controls.readable || unconfirmed}>Save Claude Limits</button>
        {!controlsValid && <p className="control-help" role="status">Enter a daily limit above US$0.00 and at most US${dollars(highDaily)}, and {lowCalls} to {highCalls} calls.</p>}
      </form>

      {lifetime ? (
        <form aria-label="Claude lifetime limit" onSubmit={(event) => {
          event.preventDefault();
          if (!capValid || (capRaising && !capConfirmed)) return;
          const cap = capMicro!;
          const shown = lifetime.cap_micro_usd;
          void run(() => saveClaudeLifetimeCap(cap, capRaising ? cap : null, shown), "Claude's lifetime limit updated.");
        }}>
          <h3>Claude lifetime limit (Anthropic ledger)</h3>
          <p className="control-help">
            The workspace's usage when the ledger was created: {usd(exactDollars(lifetime.opening_usage_micro_usd))}. Current limit {usd(exactDollars(lifetime.cap_micro_usd))}; committed {usd(exactDollars(lifetime.committed_micro_usd))}. It may be set above the opening usage and at most {usd(dollars(lifetime.max_cap_micro_usd))} (the lower of US$30.00 and the attested workspace limit); lowering it is always allowed. Raising it needs your confirmation and a reconciliation within 24 hours; the ledger keeps every charge and is never replaced.
          </p>
          <label className="control-help" htmlFor="claude-lifetime-limit-input">New Claude lifetime limit (US$)</label>{" "}
          <input id="claude-lifetime-limit-input" inputMode="decimal" value={capText} onChange={(event) => { setCapText(event.target.value); setCapConfirmed(false); }} disabled={disabled} />{" "}
          {capRaising && (
            <label className="control-help">
              <input type="checkbox" checked={capConfirmed} onChange={(event) => setCapConfirmed(event.target.checked)} disabled={disabled} data-testid="claude-cap-raise-confirm" />
              {" "}I confirm raising Claude's lifetime limit to {usd(exactDollars(capMicro!))}.
            </label>
          )}{" "}
          <button type="submit" className="btn btn-primary" disabled={disabled || !capValid || capMicro === lifetime.cap_micro_usd || (capRaising && !capConfirmed)}>Update Claude Lifetime Limit</button>
          {!capValid && <p className="control-help" role="status">Enter an amount above {usd(exactDollars(lifetime.opening_usage_micro_usd))} and either below the current limit or at most {usd(dollars(lifetime.max_cap_micro_usd))}.</p>}
        </form>
      ) : <p className="control-help" role="status">The Claude ledger is not set up yet, so its lifetime limit cannot be shown or changed here (an operator creates it with scripts/budget_ledger.py --anthropic init).</p>}
      {message && <p className={message.kind === "error" ? "ds-banner ds-banner-warn" : "control-help"} role={message.kind === "error" ? "alert" : "status"}>{message.text}</p>}
    </>
  );
}

const DUE_SOON_MS = 24 * 60 * 60 * 1000;

/** A time in Singapore time (formatTimestamp's zone), labelled so it is never read as local. */
const sgtTime = (value: string) => `${formatTimestamp(value)} SGT`;

/** One reconciliation window: when it ends and whether it has ended (or ends within a day). */
function windowText(deadline: string | null, fresh: boolean, now: number): string {
  if (deadline === null) return "Not open: the Claude ledger has never been reconciled";
  const at = sgtTime(deadline);
  if (!fresh) return `Ended ${at}: reconciliation required`;
  const left = Date.parse(deadline) - now;
  return left <= DUE_SOON_MS ? `Open until ${at} (ends within a day)` : `Open until ${at}`;
}

/** B1 Phase A: the Claude ledger's accounting and reconciliation windows, read-only. Nothing
 *  here reconciles, resets or changes the ledger (an operator reconciles it). */
function ClaudeReconciliation({ reconciliation }: { reconciliation: ModelClaudeReconciliation | null | undefined }) {
  if (reconciliation === undefined) return null;  // an older server
  if (reconciliation === null) {
    return <p className="control-help" role="status" data-testid="claude-reconciliation">{LEDGER_UNREAD}, so its reconciliation figures are not shown.</p>;
  }
  const now = Date.now();
  const calls = reconciliation.calls;
  const overdue = !reconciliation.chat_fresh;
  // QG L2: the ledger's baseline is the provider's usage at the last reconciliation plus any
  // overcount the ledger kept (it never lowers spend it already counted), and the estimate is
  // the baseline plus what it charged since. The page shows every term so the sums can be checked.
  const provider = reconciliation.last_provider_usage_micro_usd;
  const baseline = reconciliation.baseline_micro_usd;
  const kept = baseline - provider;
  const addsUp = kept >= 0 && baseline + reconciliation.local_charged_micro_usd === reconciliation.estimate_micro_usd;
  return (
    <div className="console-subcard" data-testid="claude-reconciliation">
      <h3>Claude ledger and reconciliation (read-only)</h3>
      {overdue && (
        <p className="ds-banner ds-banner-warn" role="alert">
          The Claude ledger is not reconciled within the last 7 days, so Claude chat is refused until it is reconciled with the Anthropic Console (below, or by an operator).
        </p>
      )}
      <dl className="acra-detail-list" aria-label="Claude ledger accounting">
        <div><dt>Key</dt><dd>{reconciliation.key_alias} (alias only; the key itself is never shown)</dd></div>
        <div><dt>Last reconciled</dt><dd>{reconciliation.reconciled_at ? sgtTime(reconciliation.reconciled_at) : "Never"}</dd></div>
        <div><dt>Chat window (7 days)</dt><dd>{windowText(reconciliation.chat_deadline_at, reconciliation.chat_fresh, now)}</dd></div>
        <div><dt>Paid qualification and activation window (24 hours)</dt><dd>{windowText(reconciliation.paid_deadline_at, reconciliation.paid_fresh, now)}</dd></div>
        <div><dt>Anthropic usage reported at the last reconciliation</dt><dd>{usd(exactDollars(provider))}</dd></div>
        <div><dt>Overcount kept by the ledger</dt><dd data-testid="claude-overcount">{kept > 0
          ? `${usd(exactDollars(kept))}: at the last reconciliation the ledger had counted more than Anthropic reported, and it keeps the higher figure (spend already counted is never lowered without an operator), so headroom is never overstated`
          : "None (the ledger matched or was below Anthropic's report)"}</dd></div>
        <div><dt>Ledger baseline (reported usage + overcount kept)</dt><dd>{usd(exactDollars(baseline))}</dd></div>
        <div><dt>Charged by the ledger since the last reconciliation</dt><dd>{usd(exactDollars(reconciliation.local_charged_micro_usd))}</dd></div>
        <div><dt>Ledger estimate of the workspace's cumulative cost (baseline + charged since)</dt><dd><strong>{usd(exactDollars(reconciliation.estimate_micro_usd))}</strong> (compare with the Anthropic Console; a difference above {usd(exactDollars(reconciliation.tolerance_micro_usd))} stops Claude when reconciled)</dd></div>
        {!addsUp && (
          <div><dt>Check</dt><dd role="alert">These ledger figures do not add up as expected. Refresh; if it persists, ask an operator to check the ledger (scripts/budget_ledger.py --anthropic status).</dd></div>
        )}
        <div><dt>Reserved by open calls</dt><dd>{usd(exactDollars(reconciliation.open_reserved_micro_usd))}{calls.open > 0 ? ` (${calls.open} open)` : ""}</dd></div>
        <div><dt>Calls in this ledger</dt><dd>{calls.total} ({calls.settled} settled, {calls.unsettled} unsettled, {calls.abandoned} abandoned, {calls.open} open)</dd></div>
        <div><dt>Call verification</dt><dd>{calls.verified} verified, {calls.quarantined} quarantined, {calls.unverified} not yet verified</dd></div>
        <div><dt>Charged in this ledger</dt><dd>{usd(exactDollars(calls.charged_micro_usd))}</dd></div>
      </dl>
    </div>
  );
}

/** D-110: what each reconciliation refusal means (the server returns closed codes only). */
const RECONCILE_REFUSAL_TEXT: Record<string, string> = {
  PREREQUISITE_MISSING: "HR reconciliation is not available yet: the owner must first record that every earlier copy of the operator's script and every earlier launcher is retired (budget_ledger.py attest-legacy-retired). Nothing changed.",
  SCOPE_UNCONFIRMED: "Confirm all three statements about the Console figure. Nothing changed.",
  USAGE_CONFIRMATION_REQUIRED: "The figure you typed again does not match the preview. Nothing changed.",
  LEDGER_PROFILE_MISMATCH: "The Claude ledger is not the one this preview was made for. Preview again. Nothing changed.",
  LEDGER_UNAVAILABLE: "The Claude ledger is missing or not usable. Nothing changed.",
  LEDGER_BUSY: "The Claude ledger or its reconciliation lock is busy (another reconciliation, an operator, or a call in progress). Wait a moment and try again. Nothing changed.",
  BREAKER_OPEN: "Claude is stopped (its breaker is open), so HR cannot reconcile now: the owner reconciles with the operator's script and resets the breaker. Nothing changed.",
  CALL_OPEN: "A Claude call is open (or was left open by a stopped service). Wait for it to finish, or ask an operator to run budget_ledger.py --anthropic status. Nothing changed.",
  CALLS_UNVERIFIED: "Some Claude calls are not yet verified. The next chat answer or a Test connection verifies them (or an operator runs verify). Nothing changed.",
  CALLS_QUARANTINED: "A Claude call was quarantined after the last reconciliation. The owner must reconcile with the operator's script. Nothing changed.",
  RUN_UNRESOLVED: "Another reconciliation run is not finished, or its marker remains. If the run below shows Resolve, use it; otherwise the owner closes it with the operator's script (owner-close). Nothing changed.",
  USAGE_LOWER: "The Console figure is lower than at the last reconciliation. Cumulative cost never falls: check the figure and its scope, or wait until the Console has caught up. Nothing changed.",
  USAGE_BEHIND: "The Console figure is too far below what the ledger charged since the last reconciliation, so it is probably an older or lagging reading. Take a newer reading. Nothing changed.",
  EVIDENCE_FUTURE: "The reading's time is in the future. Check the times entered. Nothing changed.",
  EVIDENCE_STALE: "The reading is too old (viewed more than two hours ago, or refreshed more than about a day ago). Take a newer reading. Nothing changed.",
  CALL_TOO_RECENT: "A Claude call finished too close to the reading for the Console to be sure to include it. Take a reading refreshed later. Nothing changed.",
  PREVIEW_UNKNOWN: "This preview is no longer available (it was used, replaced, or made by someone else). Preview again. Nothing changed.",
  PREVIEW_EXPIRED: "This preview expired (five minutes). Preview again. Nothing changed.",
  CONTROLS_CONFLICT: "The Claude ledger changed after the preview (a call, a limit change or another reconciliation). Preview again. Nothing changed.",
  RECONCILE_REFUSED: "The ledger refused or rolled back the reconciliation. Preview again later; if it persists, ask the owner to check the ledger. Nothing changed.",
  RESOLVE_NOT_YET: "This run cannot be resolved yet.",
  RUN_UNKNOWN: "No such reconciliation run.",
  RUN_STORE_UNAVAILABLE: "The reconciliation records could not be read. Nothing changed.",
  INVALID_INPUT: "Check the amount and the times entered. Nothing changed.",
};

function reconcileError(error: unknown): string {
  if (!(error instanceof AiAssistantError) || !error.code || !RECONCILE_REFUSAL_TEXT[error.code]) return safeError(error);
  const facts = error.facts;
  const parts = [RECONCILE_REFUSAL_TEXT[error.code]];
  if (typeof facts.earliest_as_of === "string") parts.push(`The Console data must be refreshed at or after ${sgtTime(facts.earliest_as_of)}.`);
  if (typeof facts.latest_refresh_needed === "string") parts.push(`The Console data must be refreshed after ${sgtTime(facts.latest_refresh_needed)}.`);
  if (typeof facts.retry_after === "string") parts.push(`Try again after ${sgtTime(facts.retry_after)}.`);
  if (typeof facts.ledger_ahead_micro_usd === "number") parts.push(`The ledger is ${usd(exactDollars(facts.ledger_ahead_micro_usd))} ahead of the increase.`);
  if (typeof facts.last_usage_micro_usd === "number") parts.push(`Last reconciled figure: ${usd(exactDollars(facts.last_usage_micro_usd))}.`);
  if (typeof facts.run_id === "string") parts.push(`Run ${facts.run_id.slice(0, 8)}.`);
  return parts.join(" ");
}

/** A datetime-local value (this computer's time zone) as ISO 8601 with its offset, or null. */
export function localToIso(value: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(value)) return null;
  const at = new Date(value);
  return Number.isNaN(at.getTime()) ? null : at.toISOString();
}

function nowLocal(): string {
  const at = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}T${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

const RUN_STATUS_TEXT: Record<ClaudeReconciliationRun["status"], string> = {
  requested: "Not finished (resolve it)",
  applied: "Applied",
  refused: "Refused (nothing changed)",
  failed: "Failed (nothing changed)",
  unresolved: "Unresolved: the owner must check and close it",
  owner_closed: "Closed by the owner",
};

/** D-110: HR reconciles the Claude ledger with the Anthropic Console: preview, confirm with the
 *  figure typed again, apply. The server checks everything again; nothing is reset or released. */
function ClaudeReconcile({ userId, busy, onChanged }: { userId: string; busy: boolean; onChanged: () => void }) {
  const runsQuery = useQuery({
    queryKey: modelManagementQueryKeys.claudeReconciliation(userId),
    queryFn: ({ signal }) => fetchClaudeReconciliation(signal),
    retry: false,
  });
  const [usageText, setUsageText] = useState("");
  const [kind, setKind] = useState<"console_refreshed" | "viewed">("console_refreshed");
  const [asOfText, setAsOfText] = useState("");
  const [viewedText, setViewedText] = useState(nowLocal);
  const [scopes, setScopes] = useState({ workspace: false, only: false, cumulative: false });
  const [preview, setPreview] = useState<ClaudeReconciliationPreview | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [echoText, setEchoText] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  const usage = toMicroUsd(usageText);
  const viewedIso = localToIso(viewedText);
  const asOfIso = kind === "viewed" ? viewedIso : localToIso(asOfText);
  const allScopes = scopes.workspace && scopes.only && scopes.cumulative;
  // Only a well-formed listing is trusted (an older server may answer this path differently).
  const data = runsQuery.data;
  const listing = data && Array.isArray(data.runs) && typeof data.prerequisite_recorded === "boolean" ? data : undefined;
  const blocked = listing ? !listing.prerequisite_recorded : false;
  const ready = usage !== null && viewedIso !== null && asOfIso !== null && allScopes && !blocked;
  const disabled = pending || busy;
  const echo = toMicroUsd(echoText);

  function changed(update: () => void) {
    update();
    setPreview(null);
    setMessage(null);
  }

  async function run(action: () => Promise<void>) {
    setPending(true);
    setMessage(null);
    try {
      await action();
    } catch (error) {
      setMessage({ kind: "error", text: reconcileError(error) });
    } finally {
      setPending(false);
      onChanged();
    }
  }

  const askPreview = () => run(async () => {
    setPreview(null);
    setPreview(await previewClaudeReconciliation({
      usage_micro_usd: usage!,
      as_of: asOfIso!,
      as_of_kind: kind,
      viewed_at: viewedIso!,
      scope_workspace: scopes.workspace,
      scope_only: scopes.only,
      scope_cumulative: scopes.cumulative,
    }));
  });

  const apply = (shown: ClaudeReconciliationPreview) => run(async () => {
    setConfirming(false);
    setPreview(null);
    const result = await applyClaudeReconciliation({
      preview_id: shown.preview_id,
      confirm_usage_micro_usd: echo ?? -1,
      scope_workspace: scopes.workspace,
      scope_only: scopes.only,
      scope_cumulative: scopes.cumulative,
    });
    setEchoText("");
    if (result.outcome === "applied") {
      setMessage({ kind: "ok", text: `Reconciled. The Claude ledger now records ${usd(exactDollars(shown.inputs.usage_micro_usd))} reported by the Anthropic Console; the chat and paid windows were renewed from now.${shown.breaker_opens ? " Claude is now stopped (breaker open) until the owner reconciles again with the operator's script and resets it." : ""}` });
    } else {
      setMessage({ kind: "error", text: "The outcome could not be confirmed, so the run stays open. Use Resolve on it below after the time shown; it is marked applied only when the ledger proves it." });
    }
  });

  const resolve = (runId: string) => run(async () => {
    const result = await resolveClaudeReconciliationRun(runId);
    setMessage({ kind: result.outcome === "applied" ? "ok" : "error", text: `Run ${runId.slice(0, 8)}: ${RUN_STATUS_TEXT[result.run?.status ?? "requested"] ?? result.outcome}.` });
  });

  return (
    <div className="console-subcard" data-testid="claude-reconcile">
      <h3>Reconcile with the Anthropic Console (HR, D-110)</h3>
      <p className="control-help">
        Enter the Anthropic Console's cumulative cost of the Claude workspace since it was created, and the time the Console says its data was refreshed. Preview first: nothing changes until you confirm. Reconciling never resets the breaker, releases an overcount or raises a limit.
      </p>
      {runsQuery.isError && <p className="ds-banner ds-banner-warn" role="alert">{reconcileError(runsQuery.error)}</p>}
      {blocked && <p className="ds-banner ds-banner-warn" role="alert" data-testid="reconcile-prerequisite">{RECONCILE_REFUSAL_TEXT.PREREQUISITE_MISSING}</p>}
      {listing?.marker_overridden && <p className="ds-banner ds-banner-warn" role="alert">An operator overrode an unfinished HR reconciliation run. Only the owner can close it (owner-close).</p>}
      <form aria-label="Reconcile Claude ledger" onSubmit={(event) => { event.preventDefault(); if (ready && !disabled) void askPreview(); }}>
        <label className="control-help" htmlFor="reconcile-usage">Cumulative workspace cost in the Console (US$)</label>{" "}
        <input id="reconcile-usage" inputMode="decimal" value={usageText} onChange={(event) => changed(() => setUsageText(event.target.value))} disabled={disabled || blocked} />
        <fieldset className="control-help">
          <legend>Time of the reading (this computer's time zone)</legend>
          <label><input type="radio" name="reconcile-kind" checked={kind === "console_refreshed"} onChange={() => changed(() => setKind("console_refreshed"))} disabled={disabled || blocked} /> The Console shows when its data was refreshed</label>{" "}
          <label><input type="radio" name="reconcile-kind" checked={kind === "viewed"} onChange={() => changed(() => setKind("viewed"))} disabled={disabled || blocked} data-testid="reconcile-kind-viewed" /> The Console shows no refresh time (use the time I looked; needs one hour without Claude calls before it)</label>
          {kind === "console_refreshed" && (
            <>
              <br /><label htmlFor="reconcile-as-of">Console data refreshed at</label>{" "}
              <input id="reconcile-as-of" type="datetime-local" value={asOfText} onChange={(event) => changed(() => setAsOfText(event.target.value))} disabled={disabled || blocked} />
            </>
          )}
          <br /><label htmlFor="reconcile-viewed">I looked at the Console at</label>{" "}
          <input id="reconcile-viewed" type="datetime-local" value={viewedText} onChange={(event) => changed(() => setViewedText(event.target.value))} disabled={disabled || blocked} />
        </fieldset>
        <fieldset className="control-help">
          <legend>Scope of the figure</legend>
          <label><input type="checkbox" checked={scopes.workspace} onChange={(event) => changed(() => setScopes({ ...scopes, workspace: event.target.checked }))} disabled={disabled || blocked} data-testid="reconcile-scope-workspace" /> It is for the Anthropic workspace Claude is set up with in Providers → Anthropic.</label><br />
          <label><input type="checkbox" checked={scopes.only} onChange={(event) => changed(() => setScopes({ ...scopes, only: event.target.checked }))} disabled={disabled || blocked} data-testid="reconcile-scope-only" /> It covers that workspace only (no other workspace or organisation total).</label><br />
          <label><input type="checkbox" checked={scopes.cumulative} onChange={(event) => changed(() => setScopes({ ...scopes, cumulative: event.target.checked }))} disabled={disabled || blocked} data-testid="reconcile-scope-cumulative" /> It is the cumulative cost since the workspace was created, not a monthly or daily figure.</label>
        </fieldset>
        <button type="submit" className="btn btn-secondary" disabled={disabled || !ready} data-testid="reconcile-preview">Preview reconciliation</button>
        {!ready && !blocked && <p className="control-help" role="status">Enter an amount, the times, and tick all three statements to preview.</p>}
      </form>

      {preview && (
        <div className="console-subcard" data-testid="reconcile-preview-result">
          <h4>Preview (nothing has changed yet)</h4>
          {preview.fallback && <p className="ds-banner ds-banner-warn" role="note">This reading uses the time you looked at the Console, because the Console showed no refresh time. The Console may still lag; the ledger keeps the higher figure if it does, and the next reconciliation corrects it.</p>}
          {preview.breaker_opens && <p className="ds-banner ds-banner-warn" role="alert" data-testid="reconcile-breaker-warning">The Console shows {usd(exactDollars(preview.drift_micro_usd))} more than the ledger estimated (more than {usd(exactDollars(preview.tolerance_micro_usd))}). Applying adopts it and stops Claude (breaker open) until the owner reconciles again with the operator's script and resets it.</p>}
          <dl className="acra-detail-list" aria-label="Reconciliation preview">
            <div><dt>Console figure</dt><dd><strong>{usd(exactDollars(preview.inputs.usage_micro_usd))}</strong> ({preview.fallback ? "viewed" : "refreshed"} {sgtTime(preview.inputs.as_of)})</dd></div>
            <div><dt>Ledger estimate now</dt><dd>{usd(exactDollars(preview.before.estimate_micro_usd))} (baseline {usd(exactDollars(preview.before.baseline_micro_usd))} + charged since {usd(exactDollars(preview.before.local_charged_micro_usd))})</dd></div>
            <div><dt>Difference (Console − ledger)</dt><dd data-testid="reconcile-drift">{preview.drift_micro_usd >= 0 ? "" : "−"}{usd(exactDollars(Math.abs(preview.drift_micro_usd)))}{preview.drift_micro_usd < 0 ? " (the ledger keeps its higher figure)" : preview.drift_micro_usd === 0 ? " (match)" : " (the ledger adopts the Console's higher figure)"}</dd></div>
            <div><dt>Ledger baseline after</dt><dd>{usd(exactDollars(preview.after.baseline_micro_usd))}</dd></div>
            <div><dt>Chat window after</dt><dd>Until about {sgtTime(preview.chat_deadline_at)}</dd></div>
            <div><dt>Paid qualification and activation window after</dt><dd>Until about {sgtTime(preview.paid_deadline_at)}</dd></div>
            <div><dt>Preview expires</dt><dd>{sgtTime(preview.expires_at)}</dd></div>
          </dl>
          <button type="button" className="btn btn-primary" disabled={disabled} onClick={() => { setEchoText(""); setConfirming(true); }} data-testid="reconcile-apply-open">Apply reconciliation…</button>
        </div>
      )}

      {confirming && preview && (
        <ConsoleDialog labelledBy="reconcile-confirm-heading" testId="reconcile-confirm" focusFallbackIds={FOCUS_FALLBACKS} onClose={() => setConfirming(false)}>
          <h2 id="reconcile-confirm-heading">Reconcile the Claude ledger to {usd(exactDollars(preview.inputs.usage_micro_usd))}?</h2>
          <p>The server checks again that the ledger is exactly as previewed and applies the ledger's own reconciliation. It never resets the breaker or releases an overcount. Type the Console figure again to confirm.</p>
          <label htmlFor="reconcile-echo">Console figure again (US$)</label>{" "}
          <input id="reconcile-echo" inputMode="decimal" value={echoText} onChange={(event) => setEchoText(event.target.value)} autoComplete="off" data-testid="reconcile-echo" />
          <div className="console-dialog__actions">
            <button type="button" className="btn btn-secondary" onClick={() => setConfirming(false)}>Cancel</button>
            <button type="button" className="btn btn-primary" disabled={disabled || echo !== preview.inputs.usage_micro_usd} onClick={() => void apply(preview)} data-testid="reconcile-apply">Apply</button>
          </div>
        </ConsoleDialog>
      )}

      {message && <p className={message.kind === "error" ? "ds-banner ds-banner-warn" : "control-help"} role={message.kind === "error" ? "alert" : "status"} data-testid="reconcile-message">{message.text}</p>}

      {listing && listing.runs.length > 0 && (
        <table className="console-table" aria-label="Reconciliation runs" data-testid="reconcile-runs">
          <thead><tr><th>Started</th><th>By</th><th>Figure</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {listing.runs.map((item) => (
              <tr key={item.run_id}>
                <td>{sgtTime(item.intent_at)}</td>
                <td>{item.actor}</td>
                <td>{usd(exactDollars(item.usage_micro_usd))}</td>
                <td>{RUN_STATUS_TEXT[item.status]}{item.status === "requested" && item.resolvable_after ? ` (from ${sgtTime(item.resolvable_after)})` : ""}</td>
                <td>{item.status === "requested" && (
                  <button type="button" className="btn btn-secondary" disabled={disabled} onClick={() => void resolve(item.run_id)}>Resolve</button>
                )}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/** Claude's spending: its own HR limits (D-102) and what a paid qualification may spend. */
function ClaudeSpending({ userId, items, claude, busy, onChanged }: {
  userId: string;
  items: ModelProfileView[];
  claude: ModelClaudeBudget | undefined;
  busy: boolean;
  onChanged: () => void;
}) {
  return (
    <section className="card" aria-labelledby="claude-spending-heading" data-testid="claude-spending">
      <p className="card-kicker">Claude Sonnet 5.5 · Anthropic ledger</p>
      <h2 id="claude-spending-heading">Claude daily spending limit, lifetime limit and calls</h2>
      <p className="ds-banner" role="note">
        Claude has its own separate ledger and limits: at most US$5.00 a Singapore day and 20 calls an activation, and a lifetime limit of at most the lower of US$30.00 and the owner-attested Anthropic workspace limit. The GPT-OSS limits never apply to Claude, and Claude's never apply to GPT-OSS.
      </p>
      {claude ? <ClaudeLimits claude={claude} busy={busy} onChanged={onChanged} /> : (
        <p className="console-help">This server does not send Claude's spending or limits, so they cannot be changed here.</p>
      )}
      {claude && <ClaudeReconciliation reconciliation={claude.reconciliation} />}
      {claude && claude.reconciliation !== undefined && <ClaudeReconcile userId={userId} busy={busy} onChanged={onChanged} />}
      {items.map((item) => {
        const paid = item.paid_qualification;
        return (
          <div key={item.profile_id} className="console-subcard">
            <h3>{profileName(item)}</h3>
            {paid ? (
              <dl className="console-facts" aria-label={`${profileName(item)} paid qualification`}>
                <div><dt>Available under the strictest Claude limit</dt><dd className="console-number">{microUsd(paid.effective_remaining_micro_usd)}</dd></div>
                <div><dt>Reserved per call</dt><dd className="console-number">{microUsd(paid.reservation_micro_usd)}</dd></div>
                <div><dt>Paid qualification</dt><dd className="console-number">Up to {paid.calls ?? "—"} calls, {microUsd(paid.estimate_micro_usd)}</dd></div>
                <div><dt>Paid calls now</dt><dd>{paid.refusal ? `Refused: ${readable(paid.refusal, ANTHROPIC_DEPLOYMENT)}` : paid.sufficient ? "Allowed" : paid.estimate_micro_usd === null ? "Not allowed: the paid question count is not known" : "Not allowed: the limits do not leave room for every call"}</dd></div>
              </dl>
            ) : (
              <p className="console-help">Not reported: this configuration is not available{item.reason ? ` (${readable(item.reason, ANTHROPIC_DEPLOYMENT)})` : ""}, so the server sends no Claude spending figure for it.</p>
            )}
          </div>
        );
      })}
      <Responsibilities label="Who can change Claude's limits" duties={[
        { who: "hr", text: "Change Claude's daily, call and lifetime limits above, within the D-102 ceilings." },
        { who: "hr", text: "Reconcile Claude's ledger with the Anthropic Console above (D-110) before any raise or paid run, and at least every 7 days for chat." },
        { who: "operator", text: "Reconcile with scripts/budget_ledger.py --anthropic when HR cannot, release an overcount, reset the breaker and verify calls." },
        { who: "owner", text: "Keep the Anthropic workspace's monthly spend limit in the Anthropic Console (attested at most US$30.00)." },
        { who: "owner", text: "Close unresolved reconciliation runs with the operator's script (owner-close), and record that earlier script copies and launchers are retired (attest-legacy-retired)." },
      ]} />
    </section>
  );
}

function SpendingSection({ userId, overview, busy, onChanged }: { userId: string; overview: ModelOverview; busy: boolean; onChanged: () => void }) {
  const budget = overview.budget?.configured ? overview.budget : null;
  const anthropic = overview.profiles.filter((item) => providerKind(item) === "anthropic");
  if (!budget && anthropic.length === 0) {
    return <p className="ds-banner" role="status">The remote test mode is not configured on this server, so no paid spending limits apply here.</p>;
  }
  return (
    <>
      {budget ? (
        <>
          {anthropic.length > 0 && (
            <p className="ds-banner" role="note">These limits apply to GPT-OSS 120B only. Claude Sonnet 5.5 (D-099 and D-102 proposed) has its own separate ledger and limits, set further down this page.</p>
          )}
          <SpendingLimits budget={budget} busy={busy} onChanged={onChanged} />
        </>
      ) : <p className="ds-banner" role="status">The OpenRouter test mode is not configured on this server, so no GPT-OSS spending limits apply here.</p>}
      {anthropic.length > 0 && <ClaudeSpending userId={userId} items={anthropic} claude={overview.budget?.claude} busy={busy} onChanged={onChanged} />}
    </>
  );
}

function QualificationDetail({ qualification, deployment }: { qualification: ModelQualification; deployment: string }) {
  const metrics = qualification.metrics ?? {};
  return (
    <div className="model-qualification">
      <p>
        <strong>Qualification {readable(qualification.status)}</strong>
        {qualification.code && <> · {readable(qualification.code, deployment)}</>}
        {!qualification.current && <> · <span className="tag tag-warn">Out of date</span></>}
        {" "}· {qualification.done_turns}/{qualification.total_turns} turns · started by {qualification.started_by} {formatTimestamp(qualification.started_at)}
      </p>
      <p className="ds-banner ds-banner-warn">
        Technical qualification only. Answer quality: <strong>{qualification.quality?.status === "SCORED" ? "SCORED (reported, not gated)" : "NOT SCORED"}</strong>
        {qualification.quality?.reason && <> ({readable(qualification.quality.reason)})</>}. A pass is not proof of answer quality.
      </p>
      {qualification.gates && (
        <div className="table-card">
          <table className="table">
            <caption>Gates</caption>
            <thead><tr><th>Gate</th><th>Rule</th><th>Value</th><th>Result</th></tr></thead>
            <tbody>
              {qualification.gates.map((gate) => (
                <tr key={gate.gate}>
                  <td>{gate.gate}</td>
                  <td>{gate.rule}</td>
                  <td>{value(gate.value)}</td>
                  <td>{!gate.gating ? <span className="tag tag-neutral">Reported only</span> : gate.passed ? <span className="tag tag-accent">Pass</span> : <span className="tag tag-warn">Fail</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {qualification.lines && (
        <dl className="acra-detail-list">
          <div><dt>Model-selected lines</dt><dd>{value(qualification.lines.model_selected_lines)}</dd></div>
          <div><dt>Guard-withheld lines</dt><dd>{value(qualification.lines.guard_withheld_lines)}</dd></div>
          <div><dt>Application-required lines</dt><dd>{value(qualification.lines.application_required_lines)}</dd></div>
          <div><dt>Deterministic fallbacks</dt><dd>{value(qualification.lines.deterministic_fallbacks)}</dd></div>
          <div><dt>Fallback reasons</dt><dd>{value(metrics.fallback_reasons)}</dd></div>
          <div><dt>Latency total p50 / p95 (ms)</dt><dd>{value(metrics.latency_total_ms_p50)} / {value(metrics.latency_total_ms_p95)}</dd></div>
          <div><dt>First line p50 / p95 (ms)</dt><dd>{value(metrics.latency_first_shown_ms_p50)} / {value(metrics.latency_first_shown_ms_p95)}</dd></div>
          <div><dt>Context capacity</dt><dd>{value(qualification.capacity)}</dd></div>
        </dl>
      )}
      {qualification.reproducibility && (
        <details><summary>Reproducibility</summary><p className="control-help">{value(qualification.reproducibility)}</p></details>
      )}
    </div>
  );
}

// --- D-100 Phase 1: Models & Overview ------------------------------------------------------------
// Presentation only. Availability, technical qualification, answer quality and activation are
// shown apart, each read from the server's own fields; the page infers no status of its own.

type Tone = "ok" | "warn" | "block" | "neutral" | "info" | "active";
type ViewState = { label: string; tone: Tone };

function Chip({ state }: { state: ViewState }) {
  return <span className={`console-chip console-chip--${state.tone}`}>{state.label}</span>;
}

const AVAILABILITY_TONE: Record<ModelProfileView["status"], Tone> = {
  selectable: "ok", unavailable: "warn", pending_authorisation: "neutral", disabled: "neutral",
};
const CATEGORY_TONE: Record<ModelDiagnosis["category"], Tone> = {
  passed: "ok", running: "info", cancelled: "neutral", technical: "warn", budget: "warn",
  configuration: "warn", quality: "block", billing_uncertain: "block",
};
// Balanced first, then Fast, then any other reasoning setting.
const REASONING_ORDER = ["medium", "low", "high"];
const FAST_NOTICE = "Fast is the same model, endpoint and limits with less reasoning. It needs its own passing qualification; the Balanced qualification does not count for it, and its answer quality is not established.";

function availabilityState(item: ModelProfileView): ViewState {
  return { label: STATUS_LABEL[item.status], tone: AVAILABILITY_TONE[item.status] };
}

function technicalState(item: ModelProfileView): ViewState {
  const run = item.qualification;
  if (!run) return { label: "Not run", tone: "neutral" };
  if (run.status === "running") return { label: `Running ${run.done_turns}/${run.total_turns}`, tone: "info" };
  if (run.diagnosis) {
    return { label: run.diagnosis.cause === OUT_OF_DATE ? "Out of date" : CATEGORY_LABEL[run.diagnosis.category], tone: CATEGORY_TONE[run.diagnosis.category] };
  }
  if (run.status === "passed") return run.current ? { label: "Qualified", tone: "ok" } : { label: "Out of date", tone: "warn" };
  return { label: readable(run.status), tone: run.status === "cancelled" ? "neutral" : "block" };
}

function qualityState(quality: ModelQualification["quality"] | ModelOverview["quality"] | null | undefined): ViewState {
  return quality?.status === "SCORED" ? { label: "Scored · reported only", tone: "info" } : { label: "Not scored", tone: "neutral" };
}

function activationState(item: ModelProfileView, usable: boolean): ViewState {
  if (item.active) return { label: "Active", tone: "active" };
  if (!usable) return { label: "Not available", tone: "neutral" };
  return item.activation_blockers.length > 0 ? { label: "Blocked", tone: "block" } : { label: "Ready", tone: "ok" };
}

function remoteNotice(item: ModelProfileView, mode: ModelBudgetStatus["mode"] | undefined): string | null {
  if (item.deployment === ANTHROPIC_DEPLOYMENT) {
    return "External API (Anthropic, set up by HR, D-107): answers only on synthetic development cases inside the same boundary as GPT-OSS; every other case gets the case-data answer. Its own safeguards apply: a separate ledger with its own HR limits on Spending & Limits (at most US$30.00 lifetime within the owner-attested workspace limit, US$5.00 a day, 20 calls an activation; D-102 proposed) and manual reconciliation. The GPT-OSS spending controls never apply to it. Test connection is a free model read; qualification makes paid calls.";
  }
  if (item.deployment !== REMOTE_DEPLOYMENT) return null;
  return mode === "D-095"
    ? "External API: answers only on verified synthetic development cases; every other case gets the case-data answer. Within the daily, lifetime and OpenRouter key limits. Test connection is a free preflight; qualification makes paid calls."
    : "External API: answers only on the approved synthetic test case; every other case gets the case-data answer. Test connection is a free preflight; qualification makes paid calls.";
}

interface ConfigurationGroup { key: string; title: string; subtitle: string; items: ModelProfileView[] }

/** One group per model family the server names (its configurations side by side); every
 * other profile goes in one group, each qualified and activated on its own. */
function configurationGroups(profiles: ModelProfileView[]): ConfigurationGroup[] {
  const groups: ConfigurationGroup[] = [];
  for (const item of profiles) {
    const family = item.details?.model;
    const provider = item.details?.provider;
    const key = family ? `family:${family}:${provider ?? ""}` : "other";
    let group = groups.find((entry) => entry.key === key);
    if (!group) {
      group = family
        ? { key, title: family, subtitle: (provider && PROVIDER_LABEL[provider]) || readable(item.deployment), items: [] }
        : { key, title: "Other configurations", subtitle: "Each qualified and activated on its own", items: [] };
      groups.push(group);
    }
    group.items.push(item);
  }
  const rank = (item: ModelProfileView) => {
    const index = REASONING_ORDER.indexOf(item.details?.reasoning_effort ?? "");
    return index < 0 ? REASONING_ORDER.length : index;
  };
  for (const group of groups) group.items.sort((left, right) => rank(left) - rank(right));
  return groups;
}

function ActiveModelBand({ overview, busy, nameOf, onRollback }: {
  overview: ModelOverview;
  busy: boolean;
  nameOf: (profileId: string, fallback: string) => string;
  onRollback: () => void;
}) {
  const current = overview.active;
  const profile = overview.profiles.find((item) => item.active);
  const remote = isPaidRemote(profile?.deployment);
  return (
    <section className="console-band" aria-labelledby="active-model-heading">
      <div className="console-band__identity">
        <h2 id="active-model-heading">Active model · for all users · revision {overview.revision}</h2>
        <p className="console-band__name">{nameOf(current.profile_id, current.display_name)}</p>
        <p className="console-band__meta">
          Model {current.model_id ?? "None (case-data answers only)"}
          {" · "}Changed {current.changed_at ? `${formatTimestamp(current.changed_at)} by ${current.changed_by}` : "Never (environment baseline)"}
          {" · "}Prompt bound {current.prompt_limit ? `${current.prompt_limit.toLocaleString()} (${remote ? "enforced byte limit" : "verified capacity"})` : "Not applied (baseline)"}
        </p>
        {profile?.details && <p className="console-band__meta"><RemoteDetails details={profile.details} /></p>}
      </div>
      {overview.configured && (
        <button type="button" className="btn btn-secondary" disabled={!overview.last_good || busy} onClick={onRollback}>
          {overview.last_good ? `Roll back to ${nameOf(overview.last_good.profile_id, overview.last_good.display_name)}` : "No earlier model to roll back to"}
        </button>
      )}
      <dl className="console-band__states">
        <div><dt>Availability</dt><dd>{profile ? STATUS_LABEL[profile.status] : "No model answers"}</dd></div>
        <div><dt>Technical qualification</dt><dd>{profile ? technicalState(profile).label : "—"}</dd></div>
        <div><dt>Answer quality</dt><dd>{qualityState(profile?.qualification?.quality ?? overview.quality).label}<small>Reported, never a gate</small></dd></div>
        <div><dt>Activation</dt><dd>{current.unavailable ? "AI unavailable" : "Active"}<small>{current.changed_at ? `Since ${formatTimestamp(current.changed_at)}` : "Environment baseline"}</small></dd></div>
      </dl>
    </section>
  );
}

// --- Data Access & Privacy: "Restrict AI to verified synthetic cases" ----------------------------

const CLASS_LABEL: Record<ModelDataAccess["classes"][number]["provider_class"], string> = {
  openrouter: "GPT-OSS 120B through OpenRouter (external)",
  anthropic: "Claude Sonnet 5.5 through Anthropic (external)",
  it_configured: "Model IT configured on a non-loopback address",
  local_internal: "Local model on a literal loopback address",
};

const VERIFICATION_TEXT: Record<ModelDataAccess["verification"], string> = {
  "D-095": "D-095 verified synthetic cases: an approved synthetic company with Mock ACRA evidence, every document byte-identical (SHA-256) to a tracked synthetic fixture, grounded values, a seeded synthetic user, approved knowledge, an identifier screen on what is typed, and a single-use admission ticket for the exact messages.",
  "D-094": "D-094 fixed synthetic fixture only (D-095 mode is off on this server): every word and value must come from the saved Garden fixtures, so a case created in the app is normally refused.",
};

const POLICY_STATUS_TEXT: Record<ModelDataAccess["status"], string> = {
  default: "Not set here yet: local models answer every case the user is authorised to see (the existing behaviour).",
  stored: "Set by HR.",
  unavailable: "The stored policy could not be read, so local models are restricted until IT repairs it.",
  not_managed: "Model management is not configured on this server, so the policy cannot be changed here.",
};

// D-107: whether each external provider is set up, shown apart from what it may receive.
function providerState(overview: ModelOverview | undefined, providerClass: ModelDataAccess["classes"][number]["provider_class"]): string {
  if (providerClass === "anthropic") {
    const setup = overview?.anthropic_setup;
    if (!setup) return "Not reported by this server";
    if (!setup.enabled) return "Not enabled (set it up in Providers → Anthropic)";
    return setup.source === "hr" ? "Enabled by HR (Providers → Anthropic)" : "Enabled by the server configuration (D-099); HR can take it over in Providers → Anthropic";
  }
  if (providerClass === "openrouter") {
    const usable = overview?.profiles.some((item) => item.deployment === REMOTE_DEPLOYMENT && item.status === "selectable");
    return usable ? "Configured on the server" : "Not configured on this server";
  }
  return "Configured by IT in the model profiles file, if any";
}

function DataAccessSection({ policy, overview, busy, onChanged }: { policy: ModelDataAccess | undefined; overview?: ModelOverview; busy: boolean; onChanged: () => void }) {
  const local = policy?.classes.find((item) => item.provider_class === "local_internal");
  const [draft, setDraft] = useState<boolean | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [formRevision, setFormRevision] = useState(policy?.revision ?? null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  // Refilled when the stored policy changes (another administrator, another tab), so a save is
  // never sent with a choice made under an older revision.
  if ((policy?.revision ?? null) !== formRevision) {
    setFormRevision(policy?.revision ?? null);
    setDraft(null);
    setConfirmed(false);
  }
  if (!policy || !local) {
    return <section className="card"><p className="control-help">This server does not report a data access policy.</p></section>;
  }
  const stored = local.restricted;
  const chosen = draft ?? stored;
  const widening = stored && !chosen;
  const editable = !local.locked && policy.status !== "unavailable" && policy.revision !== null;
  const disabled = pending || busy || !editable;

  async function save(): Promise<void> {
    if (formRevision === null) return;
    setPending(true);
    setMessage(null);
    try {
      await saveDataAccessPolicy(formRevision, chosen, widening && confirmed);
      setMessage({ kind: "ok", text: "Data access policy saved. It applies to the next question." });
    } catch (error) {
      setMessage({ kind: "error", text: safeError(error) });
    } finally {
      setDraft(null);
      setConfirmed(false);
      setPending(false);
      onChanged();
    }
  }

  const activeLabel = policy.active_class ? CLASS_LABEL[policy.active_class] : "No model (case-data guidance only)";
  return (
    <section className="card" aria-labelledby="data-access-heading" data-testid="data-access">
      <p className="card-kicker">Data access policy · enforced by the AI Assistant server</p>
      <h2 id="data-access-heading">Restrict AI to verified synthetic cases</h2>
      <p className="control-help">{POLICY_STATUS_TEXT[policy.status]}{policy.changed_at ? ` Last changed ${formatTimestamp(policy.changed_at)}.` : ""}</p>
      <ul className="console-list" aria-label="Policy by provider">
        {policy.classes.filter((item) => item.provider_class !== "local_internal").map((item) => (
          <li key={item.provider_class} data-testid={`access-${item.provider_class}`}>
            <strong>{CLASS_LABEL[item.provider_class]}</strong>
            <dl className="acra-detail-list">
              <div><dt>Provider</dt><dd>{providerState(overview, item.provider_class)}</dd></div>
              <div><dt>Data access</dt><dd><span className="tag tag-accent">{item.restricted ? "Verified synthetic cases only" : "Every authorised case"}</span>{" "}
                {item.locked ? "Fixed for external providers: only cases that pass the D-095 provenance and document SHA-256 checks, approved case access and identifier screening, each with a one-use admission ticket. This does not stop the provider from being used." : ""}</dd></div>
            </dl>
          </li>
        ))}
        {policy.classes.filter((item) => item.provider_class === "local_internal").map((item) => (
          <li key={item.provider_class}>
            <label className="control-help">
              <input type="checkbox" data-testid={`restrict-${item.provider_class}`}
                checked={chosen} disabled={disabled}
                onChange={(event) => { setDraft(event.target.checked); setConfirmed(false); }} />
              {" "}<strong>{CLASS_LABEL[item.provider_class]}</strong>: {item.restricted ? "verified synthetic cases only" : "every case the user is authorised to see"}
            </label>
          </li>
        ))}
      </ul>
      <p className="ds-banner ds-banner-warn" role="note">
        External models are locked to verified synthetic cases on this deployment. Sending real customer data to OpenRouter or Anthropic needs a separately approved external-data policy and deployment controls; it cannot be enabled on this page. A model IT configured on any address other than a literal loopback address (127.0.0.1 or ::1) is treated the same way. Unchecking applies only to a local model on a literal loopback address, and only within the user's existing case access.
      </p>
      <dl className="acra-detail-list">
        <div><dt>Active model now</dt><dd>{activeLabel}: {policy.active_restricted ? "verified synthetic cases only" : policy.active_class ? "every case the user is authorised to see" : "no model answers"}</dd></div>
        <div><dt>Verification in force</dt><dd>{VERIFICATION_TEXT[policy.verification]}</dd></div>
        <div><dt>Refusals</dt><dd>A case or question that fails the check gets the case-data answer, and nothing is sent to the model.</dd></div>
      </dl>
      {widening && (
        <label className="control-help">
          <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} disabled={pending || busy} data-testid="data-access-widen-confirm" />
          {" "}I confirm that the local model on a literal loopback address may answer every case a user is authorised to see, not only verified synthetic cases.
        </label>
      )}
      <button type="button" className="btn btn-primary" disabled={disabled || chosen === stored || (widening && !confirmed)} onClick={() => void save()}>Save Data Access Policy</button>
      {message && <p className={message.kind === "error" ? "ds-banner ds-banner-warn" : "control-help"} role={message.kind === "error" ? "alert" : "status"}>{message.text}</p>}
    </section>
  );
}

function OverviewSummary({ overview }: { overview: ModelOverview }) {
  const budget = overview.budget?.configured ? overview.budget : null;
  const controls = budget?.controls;
  const current = overview.profiles.filter((item) => item.qualification?.status === "passed" && item.qualification.current).length;
  const outOfDate = overview.profiles.filter((item) => item.qualification && !item.qualification.current).length;
  const available = overview.profiles.filter((item) => item.status === "selectable").length;
  const pending = overview.profiles.filter((item) => item.status === "pending_authorisation").length;
  // D-099 with D-100: these figures are the GPT-OSS ledger's; say so when Claude is listed too.
  const gptOnly = overview.profiles.some((item) => item.deployment === ANTHROPIC_DEPLOYMENT) ? " (GPT-OSS)" : "";
  // With Claude active, its own ledger's figures (already on the page's spending view).
  const claudeActive = overview.profiles.find((item) => item.profile_id === overview.active.profile_id)?.deployment === ANTHROPIC_DEPLOYMENT;
  // QG L2: Claude's figures do not depend on GPT-OSS's spending view being configured.
  const claude = claudeActive && overview.budget?.claude?.configured ? overview.budget.claude : null;
  return (
    <div className="console-summary">
      {claude && (
        <Link className="console-stat" to={{ search: sectionSearch("spending") }}>
          <span className="console-label">Available now (Claude)</span>
          <span className="console-stat__value console-number">{usd(claude.effective_remaining_usd)}</span>
          <span className="console-stat__note">The strictest of today's allowance and the Anthropic ledger's headroom</span>
        </Link>
      )}
      {claude && (
        <Link className="console-stat" to={{ search: sectionSearch("spending") }}>
          <span className="console-label">Chat calls this session (Claude)</span>
          <span className="console-stat__value console-number">{claude.controls.calls_used ?? "—"} <small>/ {claude.controls.max_calls}</small></span>
          <span className="console-stat__note">{claude.controls.calls_used === null ? "Claude is not the active model" : `${claude.controls.calls_remaining} remaining`}</span>
        </Link>
      )}
      {budget && !claude && (
        <Link className="console-stat" to={{ search: sectionSearch("spending") }}>
          <span className="console-label">Available now{gptOnly}</span>
          <span className="console-stat__value console-number">{usd(budget.effective_remaining_usd)}</span>
          <span className="console-stat__note">The strictest of today's allowance, the lifetime headroom and the key's own limit</span>
        </Link>
      )}
      {controls && !claude && (
        <Link className="console-stat" to={{ search: sectionSearch("spending") }}>
          <span className="console-label">Chat calls this session{gptOnly}</span>
          <span className="console-stat__value console-number">{controls.calls_used ?? "—"} <small>/ {controls.max_calls}</small></span>
          <span className="console-stat__note">{controls.calls_used === null ? "GPT-OSS is not the active model" : `${controls.calls_remaining} remaining`}</span>
        </Link>
      )}
      <Link className="console-stat" to={{ search: sectionSearch("qualifications") }}>
        <span className="console-label">Qualifications</span>
        <span className="console-stat__value console-number">{current} <small>current</small></span>
        <span className="console-stat__note">{outOfDate} out of date · {overview.running ? "1 running" : "none running"}</span>
      </Link>
      <div className="console-stat">
        <span className="console-label">Configurations</span>
        <span className="console-stat__value console-number">{available} <small>available</small></span>
        <span className="console-stat__note">{pending} pending authorisation · {overview.profiles.length} in total</span>
      </div>
    </div>
  );
}

const PROVIDER_OF: Record<ProviderKind, string> = { openrouter: "OpenRouter", anthropic: "Anthropic API", local: "Server-configured (local)" };

// D-106 (progress): how a finished run ended, from the server's own status and code only.
export function runOutcome(run: Pick<ModelQualification, "status" | "code">): ViewState {
  if (run.status === "passed") return { label: "Passed", tone: "ok" };
  if (run.status === "failed") return { label: "Failed", tone: "block" };
  if (run.status === "cancelled") return { label: "Cancelled", tone: "neutral" };
  if (run.status === "running") return { label: "Running", tone: "info" };
  return { label: run.code?.startsWith("INTERRUPTED") ? "Interrupted" : "Stopped (error)", tone: "warn" };
}

/** D-106: a running qualification's progress, as the server reports it (polled every 3 s). */
export function QualificationProgress({ overview, pending, nameOf, onCancel }: {
  overview: ModelOverview;
  pending: boolean;
  nameOf: (profileId: string, fallback: string) => string;
  onCancel: () => void;
}) {
  const running = overview.running;
  if (!running) return null;
  const item = overview.profiles.find((profile) => profile.profile_id === running.profile_id);
  const run = item?.qualification?.qualification_id === running.qualification_id ? item.qualification : null;
  const total = running.total_turns;
  const done = Math.min(running.done_turns, total);
  // Only the server's own counts: with no total yet the bar is indeterminate (no estimate).
  const measurable = total > 0;
  const percent = measurable ? Math.round((done / total) * 100) : null;
  const active = overview.profiles.find((profile) => profile.active);
  return (
    <section className="console-running console-progress" role="status" aria-live="polite" aria-labelledby="qualification-progress-heading" data-testid="qualification-progress">
      <div className="console-progress__head">
        <span className="console-spinner" aria-hidden="true" />
        <h2 id="qualification-progress-heading">Qualification running: {nameOf(running.profile_id, running.profile_id)}</h2>
      </div>
      {measurable ? (
        <progress className="console-progress__bar" max={total} value={done} aria-label={`${done} of ${total} qualification turns completed`} />
      ) : (
        <progress className="console-progress__bar" aria-label="Qualification progress not reported yet" />
      )}
      <dl className="acra-detail-list">
        <div><dt>Progress</dt><dd>{measurable ? `${done} of ${total} turns completed (${percent}%)` : "The server has not reported the number of turns yet."}</dd></div>
        <div><dt>Provider</dt><dd>{item ? PROVIDER_OF[providerKind(item)] : "—"}</dd></div>
        <div><dt>Server stage</dt><dd>{run?.cancel_requested ? "Cancel requested; stopping" : "Running"}{run?.diagnosis ? ` (${causeText(run.diagnosis, item?.deployment)})` : ""}</dd></div>
        <div><dt>Started</dt><dd>{run ? `${formatTimestamp(run.started_at)} by ${running.started_by}` : `by ${running.started_by}`}</dd></div>
        <div><dt>Active model now</dt><dd>{active ? `${profileName(active)} (${PROVIDER_OF[providerKind(active)]})` : overview.active.unavailable ? "None: AI unavailable" : "—"}. It does not change until you activate a configuration.</dd></div>
      </dl>
      <p className="console-help">Refreshed from the server every {RUNNING_REFRESH_MS / 1000} seconds. You may leave this page; the run keeps going, and other model actions wait until it ends. No time estimate is shown because the server does not report one.</p>
      <button type="button" className="btn btn-secondary" disabled={pending || Boolean(run?.cancel_requested)} onClick={onCancel}>Cancel qualification</button>
    </section>
  );
}

/** D-106: how the run this page was following ended, with the recovery to take. */
function FinishedRun({ item, onResults }: { item: ModelProfileView; onResults: () => void }) {
  const run = item.qualification;
  if (!run || run.status === "running") return null;
  const outcome = runOutcome(run);
  const diagnosis = run.diagnosis;
  return (
    <section className="card console-progress" role="status" aria-labelledby="qualification-finished-heading" data-testid="qualification-finished">
      <h2 id="qualification-finished-heading">Qualification finished: {profileName(item)} <Chip state={outcome} /></h2>
      <p>
        {run.done_turns} of {run.total_turns} turns completed{run.code ? <> · {readable(run.code, item.deployment)}</> : null}
        {run.finished_at ? <> · ended {formatTimestamp(run.finished_at)}</> : null}
      </p>
      {diagnosis && <p>{causeText(diagnosis, item.deployment)} <strong>Next:</strong> {actionText(diagnosis, item.deployment)}</p>}
      <button type="button" className="btn btn-secondary" onClick={onResults}>Show technical results</button>
    </section>
  );
}

function ConfigurationTile({ item, configured, selected, onSelect }: {
  item: ModelProfileView;
  configured: boolean;
  selected: boolean;
  onSelect: () => void;
}) {
  const usable = item.status === "selectable" && configured;
  const classes = ["console-tile", item.active ? "console-tile--active" : "", item.status !== "selectable" ? "console-tile--muted" : ""].filter(Boolean).join(" ");
  return (
    <button type="button" className={classes} aria-pressed={selected} data-config-tile={item.profile_id} onClick={onSelect}>
      <span className="console-tile__head"><span>{profileName(item)}</span><Chip state={activationState(item, usable)} /></span>
      <span className="console-tile__state"><span>Availability</span><Chip state={availabilityState(item)} /></span>
      <span className="console-tile__state"><span>Technical</span><Chip state={technicalState(item)} /></span>
      <span className="console-tile__state"><span>Answer quality</span><Chip state={qualityState(item.qualification?.quality)} /></span>
    </button>
  );
}

function ModelInspector({ item, overview, busy, inspectorRef, onTest, onQualify, onActivate, onResults }: {
  item: ModelProfileView;
  overview: ModelOverview;
  busy: boolean;
  inspectorRef: RefObject<HTMLElement>;
  onTest: () => void;
  onQualify: () => void;
  onActivate: () => void;
  onResults: () => void;
}) {
  const usable = item.status === "selectable" && overview.configured;
  const run = item.qualification;
  const paid = item.paid_qualification;
  const technical = technicalState(item);
  const blockers = item.activation_blockers.map((code) => readable(code, item.deployment)).join(" ");
  const notice = remoteNotice(item, overview.budget?.mode);
  const remote = isPaidRemote(item.deployment);
  return (
    <aside ref={inspectorRef} className="console-inspector" aria-labelledby="inspector-heading" data-testid="model-inspector">
      <div>
        <p className="card-kicker">Selected configuration</p>
        <h2 id="inspector-heading" tabIndex={-1}>{profileName(item)}</h2>
        <small>{item.model_id ?? "No model"}{item.model_version ? ` · ${item.model_version}` : ""} · {readable(item.deployment)}</small>
        {/* D-099 with D-100: provider, reasoning and thinking of a remote configuration. */}
        {item.details && <p><RemoteDetails details={item.details} /></p>}
      </div>
      {item.active
        ? <p className="console-note console-note--active">Active for every user.</p>
        : !usable
          ? <p className="console-note console-note--block">Not available: {item.reason ? readable(item.reason, item.deployment) : STATUS_LABEL[item.status]}</p>
          : item.activation_blockers.length > 0
            ? <p className="console-note console-note--block">Activation blocked: {blockers}</p>
            : <p className="console-note console-note--ok">Ready to activate.</p>}
      <ol className="console-steps" aria-label="Readiness">
        <li><span className="console-label">Availability</span><strong>{STATUS_LABEL[item.status]}</strong>{item.reason && <> · {readable(item.reason, item.deployment)}</>}</li>
        <li>
          <span className="console-label">Connection test</span>
          {item.connection_test ? <><strong>{readable(item.connection_test.outcome)}</strong>{item.connection_test.code && <> · {readable(item.connection_test.code, item.deployment)}</>}</> : "Not tested"}
        </li>
        <li className={technical.tone === "warn" || technical.tone === "block" ? "is-attention" : undefined}>
          <span className="console-label">Technical qualification</span>
          <strong>{technical.label}</strong>
          {run && <> · {run.done_turns}/{run.total_turns} turns, started {formatTimestamp(run.started_at)}</>}
          {run && <div><button type="button" className="btn btn-secondary" onClick={onResults}>View qualification results</button></div>}
        </li>
        <li><span className="console-label">Answer quality</span><strong>{qualityState(run?.quality).label}</strong> · reported, never a gate</li>
        <li><span className="console-label">Activation</span><strong>{activationState(item, usable).label}</strong></li>
      </ol>
      {notice && <p className="console-help">{notice}</p>}
      {item.details?.reasoning_effort === "low" && <p className="console-help">{FAST_NOTICE}</p>}
      {paid && (
        <dl className="console-facts" aria-label="If you run a paid qualification">
          <div><dt>Paid calls</dt><dd className="console-number">Up to {paid.calls ?? "—"}</dd></div>
          <div><dt>Reserved at most</dt><dd className="console-number">{microUsd(paid.estimate_micro_usd)}</dd></div>
          <div><dt>Available under the strictest limit</dt><dd className="console-number">{microUsd(paid.effective_remaining_micro_usd)}</dd></div>
          {paid.refusal && <div><dt>Refused now</dt><dd>{readable(paid.refusal, item.deployment)}</dd></div>}
        </dl>
      )}
      <div className="console-actions">
        <button type="button" className="btn btn-secondary" disabled={!usable || busy} onClick={onTest}>Test connection</button>
        <button type="button" className="btn btn-secondary" disabled={!usable || busy || !item.endpoint} onClick={onQualify}>{remote ? "Run qualification…" : "Run qualification"}</button>
        <button type="button" className="btn btn-primary" disabled={!usable || busy || item.active || item.activation_blockers.length > 0}
          title={blockers} onClick={onActivate}>Activate</button>
      </div>
      <p className="console-help">
        {remote
          ? "A paid run always asks you to confirm its calls and cost first. Nothing is retried automatically, and the spending limits still apply."
          : "Activation asks you to confirm first; the server re-checks your permission, the revision and the qualification."}
      </p>
    </aside>
  );
}

/** Every configuration's full technical record, folded away below the catalogue. */
function ConfigurationDetails({ overview }: { overview: ModelOverview }) {
  return (
    <details className="console-details">
      <summary>Technical details for every configuration</summary>
      <div className="table-card table-scroll">
        <table className="table">
          <caption className="sr-only">Each configuration's deployment, endpoint, limits, status, connection test and qualification</caption>
          <thead><tr><th>Configuration</th><th>Deployment</th><th>Endpoint</th><th>Limits</th><th>Status</th><th>Connection</th><th>Qualification</th></tr></thead>
          <tbody>
            {overview.profiles.map((item) => {
              const qualification = item.qualification;
              const notice = remoteNotice(item, overview.budget?.mode);
              return (
                <tr key={item.profile_id}>
                  <td><strong>{profileName(item)}</strong>{item.active && <> <span className="tag tag-accent">Active</span></>}<br /><small>{item.model_id ?? "—"}{item.model_version ? ` · ${item.model_version}` : ""}</small>
                    {item.details && <><br /><RemoteDetails details={item.details} /></>}
                    {notice && <><br /><small className="control-help">{notice}</small></>}
                    {item.details?.reasoning_effort === "low" && <><br /><small className="control-help">{FAST_NOTICE}</small></>}</td>
                  <td>{readable(item.deployment)}</td>
                  <td>{item.endpoint ?? "Not shown"}</td>
                  <td><small>Context {item.context_window_tokens ? `${item.context_window_tokens.toLocaleString()} (declared)` : "—"} · answer {value(item.max_answer_tokens)} · temp {value(item.temperature)}</small></td>
                  <td><span className={`tag ${item.status === "selectable" ? "tag-accent" : "tag-warn"}`}>{STATUS_LABEL[item.status]}</span>{item.reason && <><br /><small>{readable(item.reason, item.deployment)}</small></>}</td>
                  <td>{item.connection_test ? <>{readable(item.connection_test.outcome)}{item.connection_test.code && <><br /><small>{readable(item.connection_test.code, item.deployment)}</small></>}</> : "Not tested"}</td>
                  <td>{qualification ? `${readable(qualification.status)}${!qualification.current ? " (out of date)" : ""}` : "Not run"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}

// --- D-100 Phase 4: Audit History ----------------------------------------------------------------
// The server sends the most recent events (newest first, at most MODEL_AUDIT_LIMIT). Search and
// filters run in the browser over those loaded events only, and the page says so.

function AuditHistory({ query, profiles }: { query: UseQueryResult<{ events: ModelAuditEvent[] }>; profiles: ModelProfileView[] }) {
  const [search, setSearch] = useState("");
  const [outcome, setOutcome] = useState("");
  const [kind, setKind] = useState("");
  const events = query.data?.events ?? [];
  const profileOf = (profileId: string | null) => (profileId ? profiles.find((item) => item.profile_id === profileId) : undefined);
  // A code is worded for the configuration's provider; with none (or one no longer listed), for any provider.
  const codeText = (event: ModelAuditEvent) => (event.code ? readable(event.code, profileOf(event.profile_id)?.deployment ?? ANY_PROVIDER) : "");
  const outcomes = [...new Set(events.map((event) => event.outcome))].sort();
  const actions = [...new Set(events.map((event) => event.action))].sort();
  const needle = search.trim().toLowerCase();
  const filtering = needle !== "" || outcome !== "" || kind !== "";
  const shown = events.filter((event) => {
    if (outcome && event.outcome !== outcome) return false;
    if (kind && event.action !== kind) return false;
    if (!needle) return true;
    const profile = profileOf(event.profile_id);
    return [event.actor, event.role, event.action, readable(event.action), event.outcome, event.profile_id, profile && profileName(profile), event.code, codeText(event), String(event.seq)]
      .some((text) => text?.toLowerCase().includes(needle));
  });
  const clear = () => { setSearch(""); setOutcome(""); setKind(""); };
  const plural = (count: number) => `${count} event${count === 1 ? "" : "s"}`;

  return (
    <section className="card console-audit" aria-labelledby="model-audit-heading">
      <div className="console-audit__head">
        <h2 id="model-audit-heading">Audit history</h2>
        {query.data && (
          <p className="console-help">Read {formatTimestamp(new Date(query.dataUpdatedAt).toISOString())}; read again every {AUDIT_REFRESH_MS / 1000} seconds while this page is open.</p>
        )}
      </div>
      {query.isPending && <p role="status">Loading audit history…</p>}
      {query.isError && (
        <div className="console-audit__error">
          <p className="ds-banner ds-banner-warn" role="alert">
            {safeError(query.error)}{query.data ? " The events below are the ones read before; they may be out of date." : ""}
          </p>
          <button type="button" className="btn btn-secondary" disabled={query.isFetching} onClick={() => void query.refetch()}>Try again</button>
        </div>
      )}
      {query.data && (events.length === 0 ? (
        <p>No model events recorded yet. Activations, qualifications, connection tests, key and limit changes, and refused requests appear here.</p>
      ) : (
        <>
          <div className="console-filters" role="search" aria-label="Filter the loaded audit events">
            <div>
              <label htmlFor="audit-search">Search loaded events</label>
              <input id="audit-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)}
                placeholder="Person, action, configuration or code" autoComplete="off" />
            </div>
            <div>
              <label htmlFor="audit-action">Action</label>
              <select id="audit-action" value={kind} onChange={(event) => setKind(event.target.value)}>
                <option value="">All actions</option>
                {actions.map((item) => <option key={item} value={item}>{readable(item)}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="audit-outcome">Outcome</label>
              <select id="audit-outcome" value={outcome} onChange={(event) => setOutcome(event.target.value)}>
                <option value="">All outcomes</option>
                {outcomes.map((item) => <option key={item} value={item}>{readable(item)}</option>)}
              </select>
            </div>
            {filtering && <button type="button" className="btn btn-secondary" onClick={clear}>Clear filters</button>}
          </div>
          <p className="console-help" data-testid="audit-scope">
            The server sent the {plural(events.length)} most recently recorded{events.length >= MODEL_AUDIT_LIMIT ? ` (the most this page asks for; older events are not loaded)` : ""}. Search and filters look only at these loaded events.
          </p>
          <p className="console-audit__count" role="status" aria-live="polite">
            {filtering ? `${shown.length} of ${plural(events.length)} loaded match.` : `Showing all ${plural(events.length)} loaded.`}
          </p>
          {shown.length === 0 ? (
            <p>No loaded event matches these filters. Older events are not loaded, so they are not searched.</p>
          ) : (
            <div className="table-card table-scroll">
              <table className="table console-audit__table" role="table">
                <caption className="sr-only">Model audit events, newest first</caption>
                <thead role="rowgroup"><tr role="row">{["When", "Who", "Action", "Configuration", "Outcome", "Code", "Revision"].map((name) => <th key={name} scope="col" role="columnheader">{name}</th>)}</tr></thead>
                <tbody role="rowgroup">
                  {shown.map((event) => {
                    const profile = profileOf(event.profile_id);
                    return (
                      <tr key={event.seq} role="row">
                        <td role="cell" data-label="When"><time dateTime={event.at}>{formatTimestamp(event.at)}</time><small className="console-raw">Event #{event.seq}</small></td>
                        <td role="cell" data-label="Who">{event.actor}{event.role && <small className="console-raw">{event.role}</small>}</td>
                        <td role="cell" data-label="Action">{readable(event.action)}<small className="console-raw"><code>{event.action}</code></small></td>
                        <td role="cell" data-label="Configuration">{event.profile_id
                          ? <>{profile ? profileName(profile) : "No longer listed"}<small className="console-raw"><code>{event.profile_id}</code></small></>
                          : "—"}</td>
                        <td role="cell" data-label="Outcome">{readable(event.outcome)}</td>
                        <td role="cell" data-label="Code">{event.code ? <>{codeText(event)}<small className="console-raw"><code>{event.code}</code></small></> : "—"}</td>
                        <td role="cell" data-label="Revision">{event.revision ?? "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      ))}
    </section>
  );
}

// After a confirmed action the opener is disabled while it runs: focus the inspector, else the page heading.
const FOCUS_FALLBACKS = ["inspector-heading", "model-management-heading"] as const;

const SECTION_LABEL = Object.fromEntries(CONSOLE_SECTIONS.map((item) => [item.id, item.label])) as Record<ConsoleSection, string>;
const SECTION_INTRO: Record<ConsoleSection, string> = {
  setup: "Choose a model, enter its key, test and qualify it, then activate it. Paid models get a US$5.00 session allowance by default, shared by qualification and chat; local models need neither.",
  overview: "Choose the model the AI Assistant uses for everyone, from the configurations IT has set up on the server. Prompts, approved lines, guardrails and knowledge permissions do not change with the model.",
  providers: "Which provider each configuration uses, its key and checks, and who manages what. Keys are never shown on this page.",
  privacy: "Which cases each kind of model may answer, as the AI Assistant server enforces it. Role and case access are unchanged; this only narrows what a model may receive.",
  spending: "Each paid provider's ledger and limits. HR changes the GPT-OSS limits and, separately, Claude's limits here. Neither provider's limits apply to the other, nothing switches between them automatically, and server-configured models have no spending ledger here.",
  qualifications: "What the latest qualification of each configuration means, whether an earlier pass still counts, and what to do next.",
  audit: "Model events recorded by the AI Assistant service: activations, qualifications, connection tests, key and limit changes, and refused requests.",
};

export default function AiModelManagement({ actor }: { actor: AuthenticatedProfile }) {
  const queryClient = useQueryClient();
  const overviewQuery = useQuery({
    queryKey: modelManagementQueryKeys.overview(actor.user_id),
    queryFn: ({ signal }) => fetchModelOverview(signal),
    retry: false,
    // Follow a running qualification without manual refresh.
    refetchInterval: (query) => (query.state.data?.running ? RUNNING_REFRESH_MS : false),
  });
  const auditQuery = useQuery({
    queryKey: modelManagementQueryKeys.audit(actor.user_id),
    queryFn: ({ signal }) => fetchModelAudit(signal),
    retry: false,
    refetchInterval: AUDIT_REFRESH_MS,
  });
  // A qualification finishes in the background: re-read the audit history when the run the
  // page was following ends, so its outcome appears without another page action.
  const runningId = overviewQuery.data?.running?.qualification_id ?? null;
  const runningProfile = overviewQuery.data?.running?.profile_id ?? null;
  const followedRun = useRef<string | null>(null);
  // The configuration whose run this page saw end (its final result is shown until another starts).
  const [finishedProfile, setFinishedProfile] = useState<string | null>(null);
  const followedProfile = useRef<string | null>(null);
  useEffect(() => {
    if (followedRun.current !== null && followedRun.current !== runningId) {
      void queryClient.invalidateQueries({ queryKey: modelManagementQueryKeys.audit(actor.user_id), exact: true });
      if (runningId === null) setFinishedProfile(followedProfile.current);
    }
    if (runningId !== null) setFinishedProfile(null);
    followedRun.current = runningId;
    followedProfile.current = runningProfile;
  }, [runningId, runningProfile, queryClient, actor.user_id]);
  const [selected, setSelected] = useState<string | null>(null);
  // D-100: the section comes from the browser location; the configuration shown in the
  // inspector is local view state (it falls back to the active one).
  const [searchParams] = useSearchParams();
  const section = consoleSection(searchParams.get("section"));
  const [inspected, setInspected] = useState<string | null>(null);
  const inspectorRef = useRef<HTMLElement>(null);
  const [confirming, setConfirming] = useState<{ kind: "activate" | "rollback"; profileId: string; name: string } | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  // D-098: a paid qualification starts only after HR confirms its calls and estimate here.
  const [paidConfirm, setPaidConfirm] = useState<ModelProfileView | null>(null);
  const refresh = () => void queryClient.invalidateQueries({ queryKey: modelManagementQueryKeys.root(actor.user_id) });
  const action = useMutation({
    mutationFn: async (run: () => Promise<unknown>) => await run(),
    retry: false,
    onSettled: refresh,
  });

  const overview: ModelOverview | undefined = overviewQuery.data;
  const unscored = overview?.quality.status !== "SCORED";
  const busy = action.isPending || Boolean(overview?.running);
  const detail = overview?.profiles.find((item) => item.profile_id === selected);
  const finishedItem = overview?.running ? undefined : overview?.profiles.find((item) => item.profile_id === finishedProfile);
  // A profile's page name (remote configurations by model and reasoning setting).
  const nameOf = (profileId: string, fallback: string) => {
    const found = overview?.profiles.find((item) => item.profile_id === profileId);
    return found ? profileName(found) : fallback;
  };

  function confirm(): void {
    if (!overview || !confirming) return;
    const revision = overview.revision;
    const acknowledge = acknowledged;
    action.mutate(() => confirming.kind === "rollback"
      ? rollbackModel(revision, acknowledge)
      : activateModel(confirming.profileId, revision, acknowledge));
    setConfirming(null);
    setAcknowledged(false);
  }

  function runQualification(item: ModelProfileView): void {
    setSelected(item.profile_id);
    if (isPaidRemote(item.deployment)) {
      setPaidConfirm(item);  // never starts a paid run without the dialog
      return;
    }
    action.mutate(() => startModelQualification(item.profile_id));
  }

  function startPaid(): void {
    const item = paidConfirm;
    const calls = item?.paid_qualification?.calls;
    setPaidConfirm(null);
    if (!item || typeof calls !== "number") return;
    action.mutate(() => startModelQualification(item.profile_id, calls));
  }

  // D-100 (I-1): every external configuration is listed, Claude included, even before its first run.
  const recoverable = overview?.profiles.filter((item) => item.profile_id !== "env_default" && (item.qualification || isPaidRemote(item.deployment))) ?? [];
  const paidPending = paidConfirm ? overview?.profiles.find((item) => item.profile_id === paidConfirm.profile_id) ?? paidConfirm : null;
  const inspectedItem = overview?.profiles.find((item) => item.profile_id === inspected)
    ?? overview?.profiles.find((item) => item.active)
    ?? overview?.profiles[0];

  // Narrow screens stack the inspector below the catalogue: bring it into view on selection.
  function inspect(profileId: string): void {
    setInspected(profileId);
    if (typeof window.matchMedia === "function" && window.matchMedia("(max-width: 900px)").matches) {
      window.setTimeout(() => inspectorRef.current?.scrollIntoView?.({ block: "start" }), 0);
    }
  }

  function showResults(profileId: string): void {
    setSelected(profileId);
    window.setTimeout(() => document.getElementById("qualification-heading")?.scrollIntoView?.({ block: "start" }), 0);
  }

  const attention = overview?.profiles.filter((item) => {
    const run = item.qualification;
    if (!run || run.status === "running") return false;
    return run.diagnosis ? run.diagnosis.action !== "NONE" && run.diagnosis.action !== "WAIT" : run.status !== "passed" || !run.current;
  }).length ?? 0;
  const credential = overview?.budget?.configured ? overview.budget.credential : null;
  // The recovery centre's own query (under root, so every page action re-reads it).
  const recovery: RecoveryView | undefined = useQuery({
    queryKey: recoveryQueryKey(actor.user_id),
    queryFn: ({ signal }) => fetchRecovery(signal),
    retry: false,
    // Read on the overview only; other sections show the badge from the last reading.
    enabled: section === "overview",
  }).data;
  const blocking = recovery?.problems.filter((item) => item.severity === "blocking").length ?? 0;
  const badges: Partial<Record<ConsoleSection, ConsoleBadge>> = {
    ...(blocking > 0 ? { overview: { text: String(blocking), label: `${blocking} blocking ${blocking === 1 ? "problem" : "problems"} in the recovery centre`, tone: "warn" as const } } : {}),
    ...(credential && credential.status !== "configured" ? { providers: credential.status === "invalid"
      ? { text: "Key invalid", label: "the OpenRouter key is not valid", tone: "warn" as const }
      : { text: "No key", label: "no OpenRouter key is set", tone: "warn" as const } } : {}),
    ...(overview?.budget?.configured && (overview.budget.ledger?.breaker_open || overview.budget.refusal) ? { spending: overview.budget.ledger?.breaker_open
      ? { text: "Stopped", label: "paid calls are stopped until an operator reconciles", tone: "warn" as const }
      : { text: "Calls refused", label: "paid calls are refused now", tone: "warn" as const } } : {}),
    ...(overview?.running
      ? { qualifications: { text: "Running", label: "a qualification is running", tone: "info" as const } }
      : attention > 0 ? { qualifications: { text: String(attention), label: `${attention} ${attention === 1 ? "needs" : "need"} attention`, tone: "warn" as const } } : {}),
  };
  const cancelRun = () => overview?.running && action.mutate(() => cancelModelQualification(overview.running!.qualification_id));

  return (
    <section className="ds-root ds-page model-management model-console" aria-labelledby="model-management-heading">
      <ConsoleShell section={section} badges={badges}>
        <div className="console-stack">
          <header className="console-header">
            <p className="card-kicker">HR administration · AI Model Console</p>
            <h1 id="model-management-heading" tabIndex={-1}>{SECTION_LABEL[section]}</h1>
            <p className="text-muted">{SECTION_INTRO[section]}</p>
          </header>

          {overviewQuery.isPending && <p role="status">Loading model settings…</p>}
          {overviewQuery.isError && (
            <div className="console-audit__error">
              <p className="ds-banner ds-banner-warn" role="alert">{safeError(overviewQuery.error)}{overview ? " The settings below are the ones read before; they may be out of date." : ""}</p>
              <button type="button" className="btn btn-secondary" disabled={overviewQuery.isFetching} onClick={() => void overviewQuery.refetch()}>Try again</button>
            </div>
          )}
          {action.isError && <p className="ds-banner ds-banner-warn" role="alert">{safeError(action.error)}</p>}

          {overview && !overview.configured && (
            <p className="ds-banner ds-banner-warn" role="status">
              {overview.model_enabled
                ? "Model management is not configured on this server. IT must provide a model profiles file; until then the environment baseline is used."
                : "The AI model is switched off on this server; answers come from case data only."}
            </p>
          )}
          {overview?.file_status === "invalid" && (
            <p className="ds-banner ds-banner-warn" role="alert">The model profiles file is invalid, so no IT profile is listed. Fields to check: {overview.file_errors.join(", ")}.</p>
          )}
          {overview?.active.unavailable && (
            <p className="ds-banner ds-banner-warn" role="alert" data-testid="ai-unavailable">
              AI is unavailable: the external model configuration that was active (GPT-OSS or Claude) can no longer be used{overview.active.reverted ? ` (${readable(overview.active.reverted, ANY_PROVIDER)})` : ""}. No other model was put in its place. Onboarding users get clearly labelled case-data guidance until you activate a qualified configuration.
              {overview.active.reverted && <> Server code: <code className="console-code">{overview.active.reverted}</code>.</>}
            </p>
          )}
          {overview?.file_status === "missing" && <p className="ds-banner ds-banner-warn" role="alert">The model profiles file named by IT was not found.</p>}

          {section === "overview" && overview && (
            <>
              {overview.active.reverted && !overview.active.unavailable && <p className="ds-banner ds-banner-warn" role="alert">The saved model could not be used at start-up ({readable(overview.active.reverted, ANY_PROVIDER)}), so the environment baseline is active.</p>}
              {overview.active.config_changed && <p className="ds-banner ds-banner-warn" role="status">IT changed this model's settings since it was activated. It keeps its activated settings until the service restarts, then the baseline is used until it is qualified again.</p>}

              <RecoveryCentre userId={actor.user_id} onChanged={refresh} />
              <ActiveModelBand overview={overview} busy={busy} nameOf={nameOf}
                onRollback={() => overview.last_good && setConfirming({ kind: "rollback", profileId: overview.last_good.profile_id, name: nameOf(overview.last_good.profile_id, overview.last_good.display_name) })} />
              <OverviewSummary overview={overview} />
              <QualificationProgress overview={overview} pending={action.isPending} nameOf={nameOf} onCancel={cancelRun} />

              <div className="console-overview">
                <section className="console-catalog" aria-labelledby="available-models-heading">
                  <h2 id="available-models-heading">Model catalogue</h2>
                  <p className="text-muted">Select a configuration to see its readiness and actions. Fast and Balanced are reasoning settings of one model, each qualified on its own.</p>
                  {configurationGroups(overview.profiles).map((group) => (
                    <section key={group.key} className="console-group" aria-label={group.title}>
                      <div className="console-group__title"><h3>{group.title}</h3><span>{group.subtitle}</span></div>
                      <div className="console-group__tiles">
                        {group.items.map((item) => (
                          <ConfigurationTile key={item.profile_id} item={item} configured={overview.configured}
                            selected={item.profile_id === inspectedItem?.profile_id} onSelect={() => inspect(item.profile_id)} />
                        ))}
                      </div>
                    </section>
                  ))}
                  <ConfigurationDetails overview={overview} />
                </section>
                {inspectedItem && (
                  <ModelInspector item={inspectedItem} overview={overview} busy={busy} inspectorRef={inspectorRef}
                    onTest={() => action.mutate(() => testModelConnection(inspectedItem.profile_id))}
                    onQualify={() => runQualification(inspectedItem)}
                    onActivate={() => setConfirming({ kind: "activate", profileId: inspectedItem.profile_id, name: profileName(inspectedItem) })}
                    onResults={() => showResults(inspectedItem.profile_id)} />
                )}
              </div>

              {detail?.qualification && (
                <section className="card" aria-labelledby="qualification-heading">
                  <h2 id="qualification-heading">Qualification: {profileName(detail)}</h2>
                  <QualificationDetail qualification={detail.qualification} deployment={detail.deployment} />
                </section>
              )}
            </>
          )}

          {section === "setup" && overview && (
            <GuidedSetup userId={actor.user_id} overview={overview} busy={busy} nameOf={nameOf} onChanged={refresh} />
          )}

          {section === "providers" && overview && <ProvidersSection overview={overview} busy={busy} onChanged={refresh} />}

          {section === "spending" && overview && <SpendingSection userId={actor.user_id} overview={overview} busy={busy} onChanged={refresh} />}

          {section === "privacy" && overview && <DataAccessSection policy={overview.data_access} overview={overview} busy={busy} onChanged={refresh} />}

          {section === "qualifications" && overview && (
            <>
              <QualificationProgress overview={overview} pending={action.isPending} nameOf={nameOf} onCancel={cancelRun} />
              {finishedItem && <FinishedRun item={finishedItem} onResults={() => showResults(finishedItem.profile_id)} />}
              {finishedItem?.qualification && selected === finishedItem.profile_id && (
                <section className="card" aria-labelledby="qualification-heading">
                  <h2 id="qualification-heading">Qualification: {profileName(finishedItem)}</h2>
                  <QualificationDetail qualification={finishedItem.qualification} deployment={finishedItem.deployment} />
                </section>
              )}
              {recoverable.length > 0 ? (
                <section className="card" aria-labelledby="recovery-heading">
                  <h2 id="recovery-heading">Model health and recovery</h2>
                  <p className="text-muted">Every external configuration is listed, including those not qualified yet. Starting or retrying a paid qualification always asks you to confirm its calls first; nothing is retried automatically.</p>
                  <p className="console-help" data-testid="qualification-kinds">The technical qualification checks connection, safety filtering, availability and context capacity; it gates activation. Answer quality is reported only, never a gate, and a technical pass does not establish it.</p>
                  <div className="model-recovery-grid">
                    {recoverable.map((item) => (
                      <RecoveryCard key={item.profile_id} item={item} configured={overview.configured} busy={busy}
                        onRetry={() => runQualification(item)}
                        onTest={() => action.mutate(() => testModelConnection(item.profile_id))} />
                    ))}
                  </div>
                </section>
              ) : <p className="ds-banner" role="status">No configuration has a qualification to review yet.</p>}
            </>
          )}

          {section === "audit" && <AuditHistory query={auditQuery} profiles={overview?.profiles ?? []} />}
        </div>
      </ConsoleShell>

      {confirming && overview && (
        <ConsoleDialog labelledBy="confirm-heading" focusFallbackIds={FOCUS_FALLBACKS} onClose={() => { setConfirming(null); setAcknowledged(false); }}>
          <h2 id="confirm-heading">{confirming.kind === "rollback" ? `Roll back to ${confirming.name}?` : `Activate ${confirming.name}?`}</h2>
          <p>This changes the AI model for every user at once. Answers already being written finish with the current model.</p>
          {overview.profiles.find((item) => item.profile_id === confirming.profileId)?.deployment === ANTHROPIC_DEPLOYMENT && (
            <p className="ds-banner ds-banner-warn">This is an external, paid API (Claude Sonnet 5.5 through the Anthropic API, set up by HR under D-107). It is used only on synthetic development cases inside the same boundary as GPT-OSS; on every other case the assistant gives the case-data answer and sends nothing. Spending stays within Claude's own separate ledger, daily allowance, call limit and the attested workspace limit. Nothing switches to or from Claude automatically.</p>
          )}
          {overview.profiles.find((item) => item.profile_id === confirming.profileId)?.deployment === REMOTE_DEPLOYMENT && (
            <p className="ds-banner ds-banner-warn">{overview.budget?.mode === "D-095"
              ? "This is an external, paid API (D-095 development mode). It is used only on verified synthetic development cases; on every other case the assistant gives the case-data answer and sends nothing. Spending stays within the daily, lifetime and OpenRouter key limits in Spending & Limits (the strictest applies)."
              : "This is an external, paid API (D-094 local synthetic test mode). It is used only on the approved synthetic test case; on every other case the assistant gives the case-data answer and sends nothing."}</p>
          )}
          {confirming.profileId !== "env_default" && unscored && (
            <label className="control-help">
              <input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />
              {" "}I understand this model passed technical qualification only (connection, safety filtering, availability and context capacity). Its answer quality is NOT SCORED and the qualification is not proof of answer quality.
            </label>
          )}
          <div className="console-dialog__actions">
            <button type="button" className="btn btn-secondary" onClick={() => { setConfirming(null); setAcknowledged(false); }}>Cancel</button>
            <button type="button" className="btn btn-primary" disabled={confirming.profileId !== "env_default" && unscored && !acknowledged} onClick={confirm}>Confirm</button>
          </div>
        </ConsoleDialog>
      )}

      {paidPending && (
        <ConsoleDialog labelledBy="paid-confirm-heading" testId="paid-confirm" focusFallbackIds={FOCUS_FALLBACKS} onClose={() => setPaidConfirm(null)}>
          <h2 id="paid-confirm-heading">Run a paid qualification of {profileName(paidPending)}?</h2>
          <p>{paidPending.deployment === ANTHROPIC_DEPLOYMENT
            ? "This asks Claude Sonnet 5.5 the configured synthetic questions through the Anthropic API. Each question is one paid call charged to Claude's separate ledger (the GPT-OSS limits do not apply); nothing is retried automatically. The calls count against the open US$5.00 paid session (D-118)."
            : "This asks GPT-OSS 120B the configured synthetic questions through OpenRouter. Each question is one paid call; nothing is retried automatically."}</p>
          <dl className="acra-detail-list">
            <div><dt>Paid calls</dt><dd>Up to {paidPending.paid_qualification?.calls ?? "—"}</dd></div>
            <div><dt>Reserved at most</dt><dd>{microUsd(paidPending.paid_qualification?.estimate_micro_usd)} ({microUsd(paidPending.paid_qualification?.reservation_micro_usd)} a call)</dd></div>
            <div><dt>Available under the strictest limit</dt><dd>{microUsd(paidPending.paid_qualification?.effective_remaining_micro_usd)}</dd></div>
          </dl>
          {paidPending.paid_qualification && !paidPending.paid_qualification.sufficient && (
            <p className="ds-banner ds-banner-warn" role="alert">
              It cannot start now: {paidPending.paid_qualification.refusal ? readable(paidPending.paid_qualification.refusal, paidPending.deployment) : "the spending limits do not leave room for every paid call."}{" "}
              {paidPending.deployment === ANTHROPIC_DEPLOYMENT
                ? "Review Claude's own limits in Spending & Limits, run Test connection, wait for the Singapore-day reset, or ask an operator to reconcile the Claude ledger."
                : "Review the GPT-OSS spending controls or run Test connection first."}
            </p>
          )}
          <div className="console-dialog__actions">
            <button type="button" className="btn btn-secondary" onClick={() => setPaidConfirm(null)}>Cancel</button>
            <button type="button" className="btn btn-primary" disabled={busy || !paidPending.paid_qualification?.sufficient} onClick={startPaid}>Start paid qualification</button>
          </div>
        </ConsoleDialog>
      )}
    </section>
  );
}
