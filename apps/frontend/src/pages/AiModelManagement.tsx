import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";

import {
  activateModel,
  AiAssistantError,
  cancelModelQualification,
  clearModelCredential,
  fetchModelAudit,
  fetchModelOverview,
  refreshProviderLimits,
  rollbackModel,
  saveLifetimeCap,
  saveModelCredential,
  saveSpendingControls,
  startModelQualification,
  testModelConnection,
  type ModelBudgetStatus,
  type ModelDiagnosis,
  type ModelOverview,
  type ModelProfileView,
  type ModelQualification,
} from "../aiAssistant";
import { formatTimestamp } from "../shared";
import type { AuthenticatedProfile } from "../types";
import { CONSOLE_SECTIONS, ConsoleDialog, ConsoleShell, consoleSection, sectionSearch, type ConsoleBadge, type ConsoleSection } from "./aiModels/ConsoleShell";

// AI model management (D-093): HR (MODEL_CONFIG_MANAGE) chooses the application-wide model
// from IT's local loopback profiles. The server decides everything; this page only shows it.

export const modelManagementQueryKeys = {
  root: (userId: string) => ["auth", userId, "assistant-models"] as const,
  overview: (userId: string) => ["auth", userId, "assistant-models", "overview"] as const,
  audit: (userId: string) => ["auth", userId, "assistant-models", "audit"] as const,
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
  CREDENTIAL_MISSING: "Its server-side key is not set.",
  PROXY_CONFIGURED: "A proxy is configured on the server.",
  // D-094 local synthetic test mode (GPT-OSS 120B via OpenRouter).
  DECISION_INTERLOCK: "The D-091 and D-092 settings the remote model needs are not set on the server.",
  NOT_DEVELOPMENT_ENVIRONMENT: "The server is not a local development set-up (loopback backend and browser origins only).",
  OWNER_ATTESTATION_MISSING: "The owner has not attested that auto top-up and prompt logging are off.",
  ENDPOINT_NOT_APPROVED: "The configured OpenRouter endpoint is not the approved one.",
  // D-099 (proposed): Claude Sonnet 5.5 Balanced and Fast are listed but not usable.
  ANTHROPIC_NOT_AUTHORISED: "Claude through the Anthropic API is not authorised for CLM use (D-099 proposed).",
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
  ANTHROPIC_ATTESTATION_MISSING: "The owner has not made the four Anthropic attestations (dedicated workspace, workspace limit set, inference-only key, key revoked at FYP end).",
  ANTHROPIC_SETTINGS_INVALID: "The server's Claude settings are not valid (they may not exceed the Option B ceilings).",
  WORKSPACE_NOT_ATTESTED: "No owner-attested Anthropic workspace id is set on the server.",
  WORKSPACE_LIMIT_NOT_ATTESTED: "The Anthropic workspace's monthly limit (at most US$5.00) is not attested on the server.",
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
  CREDENTIAL_MISSING: "The server-side Anthropic inference key is not set.",
  CREDENTIAL_INVALID: "The configured Anthropic key is not a valid inference key.",
  LEDGER_UNAVAILABLE: "The separate Claude spending ledger is missing or unhealthy.",
  DAILY_ALLOWANCE_EXHAUSTED: "Claude's own daily allowance (at most US$1.00 a Singapore day) has no room for another call.",
  LIFETIME_CAP_EXHAUSTED: "The Claude ledger's lifetime cap has no room for another call.",
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
  REVIEW_SPENDING: "Claude's limits are fixed on the server (not on this page): wait for the Singapore-day reset or ask an operator to reconcile the Claude ledger, then retry.",
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

function RecoveryCard({ item, busy, onRetry, onTest }: {
  item: ModelProfileView;
  busy: boolean;
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
  return (
    <article className="model-recovery-card" data-testid={`recovery-${item.profile_id}`}>
      <h3>{profileName(item)}</h3>
      {!run ? <p>Not qualified yet. {item.activation_blockers.map((code) => readable(code, item.deployment)).join(" ")}</p> : (
        <>
          <p>
            <strong>{diagnosis ? categoryLabel(diagnosis) : readable(run.status)}</strong>
            {run.code && <> · {readable(run.code)}</>}
            {!run.current && <> · <span className="tag tag-warn">Out of date</span></>}
          </p>
          {diagnosis && <p>{causeText(diagnosis, item.deployment)}</p>}
          {failedGates.length > 0 && (
            <p className="control-help">Failed gates: {failedGates.map((gate) => `${gate.gate} (${gate.rule})`).join("; ")}</p>
          )}
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
      <div>
        {diagnosis?.retryable && usable && (
          <button type="button" className="btn btn-primary" disabled={busy} onClick={onRetry}>
            {diagnosis.cause === OUT_OF_DATE ? "Run new qualification…" : "Retry qualification…"}
          </button>
        )}{" "}
        {(diagnosis?.action === "TEST_CONNECTION" || diagnosis?.action === "RETRY_LATER") && usable && (
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={onTest}>Test connection</button>
        )}{" "}
        {diagnosis?.action === "REVIEW_SPENDING" && paid?.refusal !== "PROVIDER_LIMIT_EXHAUSTED" && <Link className="btn btn-secondary" to={{ search: sectionSearch("spending") }}>Review spending controls</Link>}{" "}
        {paid?.refusal === "PROVIDER_LIMIT_EXHAUSTED" && (
          <p className="ds-banner ds-banner-warn" role="note" data-testid="key-owner-action">
            {ACTION_TEXT.ESCALATE_KEY_OWNER}
          </p>
        )}
        {escalate && (
          <button type="button" className="btn btn-secondary" onClick={() => {
            void navigator.clipboard?.writeText(escalationSummary(item)).then(() => setCopied(true), () => setCopied(false));
          }}>Copy escalation summary</button>
        )}
        {copied && <small role="status"> Copied.</small>}
      </div>
      {escalate && <details><summary>Escalation summary</summary><pre className="control-help">{escalationSummary(item)}</pre></details>}
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

const CREDENTIAL_SOURCE: Record<string, string> = {
  environment: "Set on the server in the process environment (OPENROUTER_API_KEY). Managed outside this page.",
  env_file: "Set on the server in apps/assistant/.env. Managed outside this page.",
  hr_memory: "Entered on this page. Kept in the AI Assistant's memory only: enter it again after the service restarts.",
  none: "No key is set on the server.",
};

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
        {controls && <div><dt>Calls this activation</dt><dd>{controls.calls_used === null ? `GPT-OSS is not the active model (limit ${controls.max_calls} per activation)` : `${controls.calls_used} used, ${controls.calls_remaining} remaining of ${controls.max_calls} (counted since activation or the service's last start)`}</dd></div>}
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
          <label className="control-help" htmlFor="call-limit-input">Calls per activation ({lowCalls} to {highCalls})</label>{" "}
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

function OpenRouterKey({ budget, remoteProfileId, busy, onChanged }: {
  budget: ModelBudgetStatus;
  remoteProfileId: string | null;
  busy: boolean;
  onChanged: () => void;
}) {
  // The key lives only in this input until it is sent; it is never stored in the browser.
  const [key, setKey] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const credential = budget.credential;
  const label = credential.status === "configured" ? "Configured" : credential.status === "invalid" ? "Invalid" : "Not Configured";

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
    <section className="console-subcard" aria-labelledby="openrouter-key-heading">
      <h3 id="openrouter-key-heading">OpenRouter API Key — {label}</h3>
      <p>
        <span className={`tag ${credential.status === "configured" ? "tag-accent" : "tag-warn"}`} role="status">{label}</span>{" "}
        {CREDENTIAL_SOURCE[credential.source]}
        {credential.source === "hr_memory" && credential.set_by && <> Entered by {credential.set_by}.</>}
      </p>
      {credential.hr_editable && (
        <form onSubmit={(event) => { event.preventDefault(); const value = key; void run(() => saveModelCredential(value), "Key saved on the server."); }}>
          <label className="control-help" htmlFor="openrouter-key-input">API key</label>{" "}
          <input id="openrouter-key-input" type="password" autoComplete="off" spellCheck={false} value={key}
            onChange={(event) => setKey(event.target.value)} disabled={pending || busy} />{" "}
          <button type="submit" className="btn btn-primary" disabled={pending || busy || !key}>Save Key</button>{" "}
          {credential.source === "hr_memory" && (
            <button type="button" className="btn btn-secondary" disabled={pending || busy}
              onClick={() => void run(clearModelCredential, "Key cleared.")}>Clear Key</button>
          )}
        </form>
      )}
      {remoteProfileId && (
        <button type="button" className="btn btn-secondary" disabled={pending || busy || credential.status !== "configured"}
          onClick={() => void run(() => testModelConnection(remoteProfileId), "Connection test finished; see Models & Overview.")}>Test Connection</button>
      )}
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
  { who: "hr", text: "Set the daily limit and calls per activation; lowering needs no confirmation, raising the daily limit does." },
  { who: "hr", text: "Raise or lower the lifetime ledger limit (a raise needs your confirmation and a ledger that reconciles)." },
  { who: "operator", text: "Reconcile the ledger with OpenRouter when calls are stopped (scripts/budget_ledger.py)." },
  { who: "owner", text: "Set the key's own lifetime limit at OpenRouter. It is never shown or changed here." },
];

const OPENROUTER_DUTIES = (hrKey: boolean): Duty[] => [
  hrKey
    ? { who: "hr", text: "Enter or clear the OpenRouter key (kept in the AI Assistant's memory only)." }
    : { who: "operator", text: "Set the OpenRouter key on the server (process environment or apps/assistant/.env)." },
  { who: "hr", text: "Run Test connection (a free preflight that reads the key's limit; no model call, no case data)." },
  { who: "hr", text: "Change the GPT-OSS limits in Spending & Limits." },
  { who: "operator", text: "Authorise the remote test mode and reconcile the ledger." },
  { who: "owner", text: "Set the key's own lifetime limit at OpenRouter." },
];

const ANTHROPIC_DUTIES: Duty[] = [
  { who: "hr", text: "Run Test connection (a free workspace and model read), confirm a paid qualification and activate, from Models & Overview." },
  { who: "operator", text: "Set the Anthropic inference key on the server (AI_ASSISTANT_ANTHROPIC_API_KEY or apps/assistant/.env). There is no HR key entry." },
  { who: "operator", text: "Keep Claude's fixed limits within the Option B ceilings and reconcile its ledger (scripts/budget_ledger.py --anthropic)." },
  { who: "owner", text: "Keep the dedicated Anthropic workspace's monthly spend limit (attested at most US$5.00) in the Anthropic Console." },
];

const LOCAL_DUTIES: Duty[] = [
  { who: "hr", text: "Run Test connection, qualify and activate, from Models & Overview." },
  { who: "operator", text: "Add or change local profiles in the model profiles file and keep the local model server running." },
];

// Codes that say the Anthropic key itself is the problem (all from the server).
const ANTHROPIC_KEY_CODES = ["CREDENTIAL_MISSING", "CREDENTIAL_INVALID", "CREDENTIAL_ADMIN_REFUSED"];

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
              <OpenRouterKey budget={budget} busy={busy}
                remoteProfileId={openrouter.find((item) => item.deployment === REMOTE_DEPLOYMENT && item.status === "selectable")?.profile_id ?? null}
                onChanged={onChanged} />
            </>
          ) : <p className="ds-banner" role="status">The remote test mode is not configured on this server, so there is no provider key to manage here.</p>}
          <Responsibilities label="Who manages OpenRouter" duties={OPENROUTER_DUTIES(budget?.credential.hr_editable ?? false)} />
        </ProviderCard>
      )}

      {anthropic.length > 0 && (
        <ProviderCard kind="anthropic" title="Anthropic API" subtitle="One provider for Claude Sonnet 5.5 Balanced and Fast · external, paid · D-099 proposed">
          <p className="console-help">Balanced and Fast are two configurations (reasoning settings) of one model on one Anthropic provider: they share the key, the workspace and Claude's single ledger, and each needs its own passing qualification.</p>
          <ProviderConfigurations items={anthropic} />
          <dl className="acra-detail-list">
            <div><dt>Availability</dt><dd>{claudeUsable} of {anthropic.length} configuration{anthropic.length === 1 ? "" : "s"} available</dd></div>
            <div><dt>Inference key</dt><dd>{keyIssue
              ? readable(keyIssue, ANTHROPIC_DEPLOYMENT)
              : "Its status is not sent to this page. An operator sets it on the server; any key problem appears among the server's codes below."}</dd></div>
            <div><dt>Workspace check</dt><dd>Test connection reads the attested workspace and the model (free; no case data). Each configuration's last result is listed above.</dd></div>
            <div><dt>Spending</dt><dd>Claude's own ledger with fixed limits (at most US$5.00 lifetime, US$1.00 a Singapore day and 20 calls an activation, within the attested workspace limit). Not changeable on this page; the GPT-OSS controls never apply to it. <Link to={{ search: sectionSearch("spending") }}>View Claude's limits</Link>.</dd></div>
            <div><dt>Reconciliation</dt><dd>{stale
              ? readable("RECONCILIATION_STALE", ANTHROPIC_DEPLOYMENT)
              : "An operator reconciles Claude's ledger with the Anthropic Console. The time of the last reconciliation is not sent to this page; a paid call is refused when it is out of date."}</dd></div>
          </dl>
          <h3 className="console-subheading">Codes reported by the server</h3>
          <ReportedCodes codes={anthropicCodes} deployment={ANTHROPIC_DEPLOYMENT} />
          <Responsibilities label="Who manages the Anthropic API" duties={ANTHROPIC_DUTIES} />
        </ProviderCard>
      )}

      {local.length > 0 && (
        <ProviderCard kind="local" title="Local models" subtitle="Loopback model servers set up by IT · no key, no paid calls">
          <ProviderConfigurations items={local} />
          <p className="console-help">Local models run on this server's loopback address, so they need no key and have no spending limits. Their availability depends on the local model server IT runs.</p>
          <Responsibilities label="Who manages local models" duties={LOCAL_DUTIES} />
        </ProviderCard>
      )}
    </>
  );
}

/** Claude's spending, read-only: only what the server sends for a paid qualification. */
function ClaudeSpending({ items }: { items: ModelProfileView[] }) {
  return (
    <section className="card" aria-labelledby="claude-spending-heading" data-testid="claude-spending">
      <p className="card-kicker">Claude Sonnet 5.5 · Anthropic ledger</p>
      <h2 id="claude-spending-heading">Claude's limits (fixed on the server, read-only)</h2>
      <p className="ds-banner" role="note">
        Claude has its own separate ledger and fixed limits: at most US$5.00 lifetime, US$1.00 a Singapore day and 20 calls an activation, within the owner-attested Anthropic workspace limit. Nothing on this page changes them, and the GPT-OSS limits never apply to Claude.
      </p>
      <p className="console-help">The server does not send Claude's spending today, lifetime usage or ledger headroom to this page. It sends only what a paid qualification of each available configuration may spend, against the strictest Claude limit.</p>
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
        { who: "operator", text: "Change Claude's settings within the Option B ceilings, and reconcile its ledger (scripts/budget_ledger.py --anthropic)." },
        { who: "owner", text: "Keep the Anthropic workspace's monthly spend limit in the Anthropic Console." },
      ]} />
    </section>
  );
}

function SpendingSection({ overview, busy, onChanged }: { overview: ModelOverview; busy: boolean; onChanged: () => void }) {
  const budget = overview.budget?.configured ? overview.budget : null;
  const anthropic = overview.profiles.filter((item) => providerKind(item) === "anthropic");
  if (!budget && anthropic.length === 0) {
    return <p className="ds-banner" role="status">The remote test mode is not configured on this server, so no paid spending limits apply here.</p>;
  }
  return (
    <>
      <p className="text-muted">Each paid provider has its own ledger and limits. Neither provider's limits apply to the other, and nothing switches between them automatically. Local models make no paid calls.</p>
      {budget ? (
        <>
          {anthropic.length > 0 && (
            <p className="ds-banner" role="note">These limits apply to GPT-OSS 120B only. Claude Sonnet 5.5 (D-099 proposed) has its own fixed safeguards that nothing on this page changes: a separate ledger with at most US$5.00 lifetime, US$1.00 a day and 20 calls an activation.</p>
          )}
          <SpendingLimits budget={budget} busy={busy} onChanged={onChanged} />
        </>
      ) : <p className="ds-banner" role="status">The OpenRouter test mode is not configured on this server, so no GPT-OSS spending limits apply here.</p>}
      {anthropic.length > 0 && <ClaudeSpending items={anthropic} />}
    </>
  );
}

function QualificationDetail({ qualification }: { qualification: ModelQualification }) {
  const metrics = qualification.metrics ?? {};
  return (
    <div className="model-qualification">
      <p>
        <strong>Qualification {readable(qualification.status)}</strong>
        {qualification.code && <> · {readable(qualification.code)}</>}
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
    return "External API (Anthropic, D-099 proposed): answers only on synthetic development cases inside the same boundary as GPT-OSS; every other case gets the case-data answer. Its own fixed safeguards apply: a separate ledger (at most US$5.00 lifetime, US$1.00 a day, 20 calls an activation), the owner-attested workspace limit and manual reconciliation. The GPT-OSS spending controls never apply to it. Test connection is a free model read; qualification makes paid calls.";
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

function OverviewSummary({ overview }: { overview: ModelOverview }) {
  const budget = overview.budget?.configured ? overview.budget : null;
  const controls = budget?.controls;
  const current = overview.profiles.filter((item) => item.qualification?.status === "passed" && item.qualification.current).length;
  const outOfDate = overview.profiles.filter((item) => item.qualification && !item.qualification.current).length;
  const available = overview.profiles.filter((item) => item.status === "selectable").length;
  const pending = overview.profiles.filter((item) => item.status === "pending_authorisation").length;
  // D-099 with D-100: these figures are the GPT-OSS ledger's; say so when Claude is listed too.
  const gptOnly = overview.profiles.some((item) => item.deployment === ANTHROPIC_DEPLOYMENT) ? " (GPT-OSS)" : "";
  return (
    <div className="console-summary">
      {budget && (
        <Link className="console-stat" to={{ search: sectionSearch("spending") }}>
          <span className="console-label">Available now{gptOnly}</span>
          <span className="console-stat__value console-number">{usd(budget.effective_remaining_usd)}</span>
          <span className="console-stat__note">The strictest of today's allowance, the lifetime headroom and the key's own limit</span>
        </Link>
      )}
      {controls && (
        <Link className="console-stat" to={{ search: sectionSearch("spending") }}>
          <span className="console-label">Calls this activation{gptOnly}</span>
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

function RunningStatus({ overview, pending, nameOf, onCancel }: {
  overview: ModelOverview;
  pending: boolean;
  nameOf: (profileId: string, fallback: string) => string;
  onCancel: () => void;
}) {
  const running = overview.running;
  if (!running) return null;
  return (
    <p className="console-running" role="status">
      <span>
        <strong>Qualification running</strong> for {nameOf(running.profile_id, running.profile_id)}: {running.done_turns}/{running.total_turns} turns (started by {running.started_by}). You may leave this page; it keeps going, and other model actions wait until it ends.
      </span>
      <button type="button" className="btn btn-secondary" disabled={pending} onClick={onCancel}>Cancel qualification</button>
    </p>
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

// After a confirmed action the opener is disabled while it runs: focus the inspector, else the page heading.
const FOCUS_FALLBACKS = ["inspector-heading", "model-management-heading"] as const;

const SECTION_LABEL = Object.fromEntries(CONSOLE_SECTIONS.map((item) => [item.id, item.label])) as Record<ConsoleSection, string>;

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
  const followedRun = useRef<string | null>(null);
  useEffect(() => {
    if (followedRun.current !== null && followedRun.current !== runningId) {
      void queryClient.invalidateQueries({ queryKey: modelManagementQueryKeys.audit(actor.user_id), exact: true });
    }
    followedRun.current = runningId;
  }, [runningId, queryClient, actor.user_id]);
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

  const recoverable = overview?.profiles.filter((item) => item.profile_id !== "env_default" && (item.qualification || item.deployment === REMOTE_DEPLOYMENT)) ?? [];
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
  const badges: Partial<Record<ConsoleSection, ConsoleBadge>> = {
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
            {section === "overview" && (
              <p className="text-muted">Choose the model the AI Assistant uses for everyone, from the configurations IT has set up on the server. Prompts, approved lines, guardrails and knowledge permissions do not change with the model.</p>
            )}
          </header>

          {overviewQuery.isPending && <p>Loading model settings…</p>}
          {overviewQuery.isError && <p className="ds-banner ds-banner-warn" role="alert">{safeError(overviewQuery.error)}</p>}
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
              AI is unavailable: the external model configuration that was active (GPT-OSS or Claude) can no longer be used{overview.active.reverted ? ` (${readable(overview.active.reverted)})` : ""}. No other model was put in its place. Onboarding users get clearly labelled case-data guidance until you activate a qualified configuration.
            </p>
          )}
          {overview?.file_status === "missing" && <p className="ds-banner ds-banner-warn" role="alert">The model profiles file named by IT was not found.</p>}

          {section === "overview" && overview && (
            <>
              {overview.active.reverted && !overview.active.unavailable && <p className="ds-banner ds-banner-warn" role="alert">The saved model could not be used at start-up ({readable(overview.active.reverted)}), so the environment baseline is active.</p>}
              {overview.active.config_changed && <p className="ds-banner ds-banner-warn" role="status">IT changed this model's settings since it was activated. It keeps its activated settings until the service restarts, then the baseline is used until it is qualified again.</p>}

              <ActiveModelBand overview={overview} busy={busy} nameOf={nameOf}
                onRollback={() => overview.last_good && setConfirming({ kind: "rollback", profileId: overview.last_good.profile_id, name: nameOf(overview.last_good.profile_id, overview.last_good.display_name) })} />
              <OverviewSummary overview={overview} />
              <RunningStatus overview={overview} pending={action.isPending} nameOf={nameOf} onCancel={cancelRun} />

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
                  <QualificationDetail qualification={detail.qualification} />
                </section>
              )}
            </>
          )}

          {section === "providers" && overview && <ProvidersSection overview={overview} busy={busy} onChanged={refresh} />}

          {section === "spending" && overview && <SpendingSection overview={overview} busy={busy} onChanged={refresh} />}

          {section === "qualifications" && overview && (
            <>
              <RunningStatus overview={overview} pending={action.isPending} nameOf={nameOf} onCancel={cancelRun} />
              {recoverable.length > 0 ? (
                <section className="card" aria-labelledby="recovery-heading">
                  <h2 id="recovery-heading">Model health and recovery</h2>
                  <p className="text-muted">What the latest qualification of each configuration means, whether an earlier pass still counts, and what to do next. Retrying a paid qualification always asks first.</p>
                  <div className="model-recovery-grid">
                    {recoverable.map((item) => (
                      <RecoveryCard key={item.profile_id} item={item} busy={busy}
                        onRetry={() => runQualification(item)}
                        onTest={() => action.mutate(() => testModelConnection(item.profile_id))} />
                    ))}
                  </div>
                </section>
              ) : <p className="ds-banner" role="status">No configuration has a qualification to review yet.</p>}
            </>
          )}

          {section === "audit" && (
            <section className="card" aria-labelledby="model-audit-heading">
              <h2 id="model-audit-heading">Audit history</h2>
              {auditQuery.isPending && <p>Loading audit history…</p>}
              {auditQuery.isError && <p className="ds-banner ds-banner-warn" role="alert">{safeError(auditQuery.error)}</p>}
              {auditQuery.data && (auditQuery.data.events.length === 0 ? <p>No model events recorded yet.</p> : (
                <div className="table-card">
                  <table className="table">
                    <thead><tr><th>When</th><th>Who</th><th>Action</th><th>Model</th><th>Outcome</th><th>Code</th></tr></thead>
                    <tbody>
                      {auditQuery.data.events.map((event) => (
                        <tr key={event.seq}>
                          <td>{formatTimestamp(event.at)}</td>
                          <td>{event.actor}{event.role ? ` (${event.role})` : ""}</td>
                          <td>{readable(event.action)}</td>
                          <td>{event.profile_id ?? "—"}</td>
                          <td>{readable(event.outcome)}</td>
                          <td>{event.code ? readable(event.code) : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </section>
          )}
        </div>
      </ConsoleShell>

      {confirming && overview && (
        <ConsoleDialog labelledBy="confirm-heading" focusFallbackIds={FOCUS_FALLBACKS} onClose={() => { setConfirming(null); setAcknowledged(false); }}>
          <h2 id="confirm-heading">{confirming.kind === "rollback" ? `Roll back to ${confirming.name}?` : `Activate ${confirming.name}?`}</h2>
          <p>This changes the AI model for every user at once. Answers already being written finish with the current model.</p>
          {overview.profiles.find((item) => item.profile_id === confirming.profileId)?.deployment === ANTHROPIC_DEPLOYMENT && (
            <p className="ds-banner ds-banner-warn">This is an external, paid API (Claude Sonnet 5.5 through the Anthropic API, D-099 proposed). It is used only on synthetic development cases inside the same boundary as GPT-OSS; on every other case the assistant gives the case-data answer and sends nothing. Spending stays within Claude's own separate ledger, daily allowance, call limit and the attested workspace limit. Nothing switches to or from Claude automatically.</p>
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
            ? "This asks Claude Sonnet 5.5 the configured synthetic questions through the Anthropic API. Each question is one paid call charged to Claude's separate ledger (the GPT-OSS limits do not apply); nothing is retried automatically. The ledger must have been reconciled within 24 hours."
            : "This asks GPT-OSS 120B the configured synthetic questions through OpenRouter. Each question is one paid call; nothing is retried automatically."}</p>
          <dl className="acra-detail-list">
            <div><dt>Paid calls</dt><dd>Up to {paidPending.paid_qualification?.calls ?? "—"}</dd></div>
            <div><dt>Reserved at most</dt><dd>{microUsd(paidPending.paid_qualification?.estimate_micro_usd)} ({microUsd(paidPending.paid_qualification?.reservation_micro_usd)} a call)</dd></div>
            <div><dt>Available under the strictest limit</dt><dd>{microUsd(paidPending.paid_qualification?.effective_remaining_micro_usd)}</dd></div>
          </dl>
          {paidPending.paid_qualification && !paidPending.paid_qualification.sufficient && (
            <p className="ds-banner ds-banner-warn" role="alert">
              It cannot start now: {paidPending.paid_qualification.refusal ? readable(paidPending.paid_qualification.refusal, paidPending.deployment) : "the spending limits do not leave room for every paid call."} Review the spending controls or run Test connection first.
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
