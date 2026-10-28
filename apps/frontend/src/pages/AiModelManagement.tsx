import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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
  type ModelOverview,
  type ModelProfileView,
  type ModelQualification,
  type ModelRecovery,
  type RecoveryCategory,
  type RecoveryFinding,
} from "../aiAssistant";
import { formatTimestamp } from "../shared";
import type { AuthenticatedProfile } from "../types";

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
  REMOTE_SETTINGS_INVALID: "The remote model's reasoning settings are not valid on the server.",
  REMOTE_MANIFEST_MISSING: "The paid qualification's question list and count are not configured on the server.",
  LEDGER_UNAVAILABLE: "The spending ledger is missing or unhealthy.",
  // D-095 spending view.
  DAILY_ALLOWANCE_EXHAUSTED: "Today's allowance (Singapore day) has no room for another call.",
  DAILY_CAP_INVALID: "The daily cap setting is not valid, so no call is allowed.",
  LIFETIME_CAP_EXHAUSTED: "The lifetime ledger cap has no room for another call.",
  PROVIDER_LIMIT_EXHAUSTED: "The OpenRouter key's own limit has no room for another call.",
  PROVIDER_LIMIT_NOT_CHECKED: "The OpenRouter key's limit has not been checked yet. Run Test connection.",
  PROVIDER_CHECK_FAILED: "The last OpenRouter key check failed. Run Test connection.",
  CREDENTIAL_INVALID: "The configured OpenRouter API key is not valid.",
};

// Remote configurations (GPT-OSS 120B): the server sends closed codes, the page names them.
// "Fast" and "Balanced" are reasoning settings of one model, not separate models.
export const REASONING_LABEL: Record<string, string> = { low: "Fast", medium: "Balanced", high: "Thorough" };
const PROVIDER_LABEL: Record<string, string> = { OPENROUTER_DEEPINFRA: "OpenRouter / DeepInfra" };
const SCOPE_LABEL: Record<string, string> = {
  VERIFIED_SYNTHETIC_CASES: "Verified synthetic cases only",
  APPROVED_SYNTHETIC_CASE: "The approved synthetic test case only",
  NOT_AUTHORISED: "Not authorised",
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

export function readable(code: string | null | undefined): string {
  if (!code) return "";
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
  if (!/^\d{1,4}(\.\d{1,6})?$/.test(trimmed)) return null;
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
      setPending(false);
      onChanged();
    }
  }

  return (
    <section className="card" aria-labelledby="spending-heading">
      <h2 id="spending-heading">OpenRouter daily spending limit, lifetime limit and calls</h2>
      <p className="ds-banner ds-banner-warn" role="note">
        At most {usd(dollars(budget.daily_cap_micro_usd))} of reserved plus settled OpenRouter spending per Singapore calendar day ({budget.timezone}), for qualification and chat together. The lowest of this allowance, the lifetime ledger limit and the key's own OpenRouter limit applies. It does not rule out unexpected provider billing; a mismatch stops further calls.
      </p>
      <dl className="acra-detail-list">
        <div><dt>Settled today</dt><dd>{usd(daily?.settled_today_usd)}</dd></div>
        <div><dt>In flight</dt><dd>{daily ? `${usd(daily.in_flight_usd)} (${daily.in_flight_calls} call${daily.in_flight_calls === 1 ? "" : "s"})` : "—"}</dd></div>
        <div><dt>Remaining today</dt><dd>{usd(daily?.remaining_usd)}</dd></div>
        <div><dt>Lifetime headroom</dt><dd>{usd(budget.ledger?.headroom_usd)}</dd></div>
        <div><dt>OpenRouter key limit</dt><dd>{budget.provider ? <>{usd(budget.provider.remaining_usd)} remaining ({budget.provider.passed ? "checks passed" : "checks failed"}, read {formatTimestamp(budget.provider.checked_at)})</> : "Not checked yet"}</dd></div>
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
          if (!controlsValid || formRevision === null) return;
          const revision = formRevision;
          void run(() => saveSpendingControls(revision, dailyMicro!, calls!), "Limits saved. They apply to the active model now.");
        }}>
          <h3>Daily and call limits</h3>
          <p className="control-help">
            {controls.daily_cap_source === "hr" || controls.max_calls_source === "hr"
              ? `Set by ${controls.changed_by ?? "HR"}${controls.changed_at ? ` ${formatTimestamp(controls.changed_at)}` : ""}.`
              : "Not set here yet: the server's defaults apply."}
            {" "}Lowering a limit never resets today's spending or the activation's call count.
          </p>
          <label className="control-help" htmlFor="daily-limit-input">Daily limit (US$0.00 to US${dollars(controls.daily_cap_max_micro_usd)})</label>{" "}
          <input id="daily-limit-input" inputMode="decimal" value={dailyText} onChange={(event) => setDailyText(event.target.value)} disabled={disabled} />{" "}
          <label className="control-help" htmlFor="call-limit-input">Calls per activation ({lowCalls} to {highCalls})</label>{" "}
          <input id="call-limit-input" inputMode="numeric" value={callsText} onChange={(event) => setCallsText(event.target.value)} disabled={disabled} />{" "}
          <button type="submit" className="btn btn-primary" disabled={disabled || !controlsValid || !controls.readable}>Save Limits</button>
          {!controlsValid && <p className="control-help" role="status">Enter a daily limit from US$0.00 to US${dollars(controls.daily_cap_max_micro_usd)} and {lowCalls} to {highCalls} calls.</p>}
        </form>
      )}

      {lifetime && (
        <form aria-label="Lifetime limit" onSubmit={(event) => {
          event.preventDefault();
          if (!capValid || (raising && !confirmed)) return;
          const cap = capMicro!;
          void run(() => saveLifetimeCap(cap, raising ? cap : null), "Lifetime limit updated.");
        }}>
          <h3>Lifetime limit (ledger)</h3>
          <p className="control-help">
            The key's usage when the ledger was created: {usd(exactDollars(lifetime.opening_usage_micro_usd))}. Current limit {usd(exactDollars(lifetime.cap_micro_usd))}; committed {usd(exactDollars(lifetime.committed_micro_usd))}. It may be set from the opening usage up to {usd(exactDollars(lifetime.max_cap_micro_usd))} (US$1.00 above it). The ledger keeps every charge and is never replaced.
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
          {!capValid && <p className="control-help" role="status">Enter an amount from {usd(exactDollars(lifetime.opening_usage_micro_usd))} to {usd(exactDollars(lifetime.max_cap_micro_usd))}.</p>}
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
    <section className="card" aria-labelledby="openrouter-key-heading">
      <h2 id="openrouter-key-heading">OpenRouter API Key — {label}</h2>
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
          onClick={() => void run(() => testModelConnection(remoteProfileId), "Connection test finished; see the model table.")}>Test Connection</button>
      )}
      {message && <p className={message.kind === "error" ? "ds-banner ds-banner-warn" : "control-help"} role={message.kind === "error" ? "alert" : "status"}>{message.text}</p>}
    </section>
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

// --- D-098: recovery (the server classifies; this page words its closed codes) -------------

export const CATEGORY_TEXT: Record<RecoveryCategory, { label: string; tag: string; text: string }> = {
  HEALTHY: { label: "Healthy", tag: "tag-accent", text: "Nothing stops the active model." },
  QUALIFICATION_REQUIRED: { label: "Qualification required", tag: "tag-warn", text: "A configuration needs a new passing qualification before it can be used." },
  RECOVERABLE_BY_HR: { label: "Recoverable by HR", tag: "tag-warn", text: "HR can fix this on this page." },
  TEMPORARILY_UNAVAILABLE: { label: "Temporarily unavailable", tag: "tag-warn", text: "Usually clears by itself; check again or retry later." },
  OPERATOR_REQUIRED: { label: "Operator intervention required", tag: "tag-warn", text: "The owner or IT must act; nothing on this page can override it." },
  POLICY_BLOCKED: { label: "Security or policy blocked", tag: "tag-warn", text: "A safety or authorisation rule stops this. It cannot be bypassed from this page; contact IT." },
};

export const ACTION_TEXT: Record<string, string> = {
  NONE: "No action needed.",
  ENTER_KEY: "Enter or replace the OpenRouter API key.",
  REVIEW_BUDGET: "Review the spending limits (daily, lifetime and calls).",
  REFRESH_LIMITS: "Refresh the OpenRouter limits (free, no model call).",
  TEST_CONNECTION: "Run Test connection (free preflight, no model call).",
  RUN_QUALIFICATION: "Run the qualification again (paid calls; you confirm first).",
  CONTACT_IT: "Contact IT: a server setting, safety result or provider listing needs review.",
  CONTACT_OPERATOR: "Contact the owner/operator: the ledger, the provider's own key limit or a verification needs reconciling.",
};

// What each gate means for HR (model_qualification.py). G-3, G-6, G-7 and G-8 are never retried away.
export const GATE_TEXT: Record<string, string> = {
  "G-1": "Connection: the free preflight failed before any question (see the checks below).",
  "G-2": "Completion: not every question got an answer in time.",
  "G-3": "Unsafe display: a line that should never be shown got through. This is a safety result; IT must review it.",
  "G-4": "Availability: too many questions had no model answer (often limits or a provider outage).",
  "G-6": "Answer validity: too few answer lines were valid. A model-quality result; IT must review it.",
  "G-7": "Context capacity: the model could not take the prompt size needed.",
  "G-8": "Provider verification: a call could not be matched with OpenRouter's own record. The owner must reconcile.",
};

const CHECK_TEXT: Record<string, string> = {
  "key.status": "OpenRouter's key status could not be read (provider down or network).",
  "endpoint.listing": "OpenRouter's endpoint listing could not be read.",
  "ledger.headroom_for_one_call": "The lifetime ledger limit has no room for a call.",
  "ledger.daily_room_for_one_call": "Today's allowance has no room for a call.",
  "ledger.cap_within_allocation": "The lifetime limit is outside its allowed range.",
  "ledger.healthy": "The spending ledger is not healthy.",
  "ledger.breaker_closed_no_open_calls": "The ledger is stopped or has an unsettled call.",
  "ledger.usage_reconciled": "The ledger does not match OpenRouter's reported usage.",
  "ledger.earlier_calls_verified": "An earlier call is not verified yet.",
};

const findingText = (finding: RecoveryFinding) =>
  (finding.gate && finding.gate !== "G-1" ? GATE_TEXT[finding.gate] : null)
  ?? CHECK_TEXT[finding.code ?? ""]
  ?? readable(finding.code);

function Finding({ finding }: { finding: RecoveryFinding }) {
  const category = CATEGORY_TEXT[finding.category];
  return (
    <li>
      {finding.gate && <strong>{finding.gate}: </strong>}{findingText(finding)}{" "}
      <span className={`tag ${category.tag}`}>{category.label}</span>{" "}
      <small className="control-help">
        {finding.retryable ? "Retryable." : "Not retryable."}{" "}
        {finding.category === "RECOVERABLE_BY_HR" || finding.category === "QUALIFICATION_REQUIRED" ? "HR can resolve this." : "HR cannot resolve this alone."}{" "}
        Next: {ACTION_TEXT[finding.action] ?? readable(finding.action)}
      </small>
    </li>
  );
}

function Recovery({ overview, busy, onAction, onRetry }: {
  overview: ModelOverview;
  busy: boolean;
  onAction: (run: () => Promise<unknown>) => void;
  onRetry: (profileId: string) => void;
}) {
  const recovery = overview.recovery as ModelRecovery;
  const category = CATEGORY_TEXT[recovery.status];
  const nameOf = (profileId: string) => {
    const found = overview.profiles.find((item) => item.profile_id === profileId);
    return found ? profileName(found) : profileId;
  };
  const cost = recovery.qualification_cost;
  const remoteTarget = recovery.remote_profiles.find((item) => item.active)?.profile_id
    ?? recovery.remote_profiles[0]?.profile_id ?? null;
  const noneUsable = !recovery.remote_active && recovery.remote_profiles.length > 0
    && !recovery.remote_profiles.some((item) => item.qualified);
  return (
    <section className="card" aria-labelledby="recovery-heading">
      <h2 id="recovery-heading">AI model status and recovery</h2>
      <p>
        <span className={`tag ${category.tag}`} role="status">{category.label}</span>{" "}
        {category.text}
      </p>
      <dl className="acra-detail-list">
        <div><dt>Active model</dt><dd>{nameOf(overview.active.profile_id)}{recovery.remote_active ? " (external, paid)" : " (no external model)"}</dd></div>
        <div><dt>Next action</dt><dd>{ACTION_TEXT[recovery.action] ?? readable(recovery.action)}</dd></div>
        {recovery.last_failure && (
          <div><dt>Last failure</dt><dd>{recovery.last_failure.source === "QUALIFICATION" ? "Qualification" : "Connection test"} of {nameOf(recovery.last_failure.profile_id)}: {readable(recovery.last_failure.code)}{recovery.last_failure.at ? ` (${formatTimestamp(recovery.last_failure.at)})` : ""}</dd></div>
        )}
        {recovery.remote_active && (
          <div><dt>Other qualified configuration</dt><dd>{recovery.other_qualified.length ? recovery.other_qualified.map(nameOf).join(", ") + " (switching is a manual HR activation; nothing switches automatically)" : "None"}</dd></div>
        )}
      </dl>
      {noneUsable && (
        <p className="ds-banner ds-banner-warn" role="status">No GPT-OSS 120B configuration is qualified now, so the AI model is not used. Relationship managers still get the case-data answer with any approved guidance; no other AI model is substituted.</p>
      )}
      {recovery.issues.length > 0 && (
        <ul aria-label="What stops the model now">{recovery.issues.map((issue, index) => <Finding key={`${issue.code}-${index}`} finding={issue} />)}</ul>
      )}
      {overview.running && (
        <p className="control-help" role="note">The qualification runs on the AI Assistant server, not in this page. You can leave, refresh or sign in again: it keeps running, is not repeated, and its result appears here. Signing in elsewhere with the same account ends this page's session but not the qualification.</p>
      )}

      <h3>GPT-OSS 120B configurations</h3>
      <ul aria-label="Configurations">
        {recovery.remote_profiles.map((item) => {
          const state = CATEGORY_TEXT[item.state.category];
          const canRetry = item.qualification?.retryable ?? item.state.action === "RUN_QUALIFICATION";
          return (
            <li key={item.profile_id}>
              <strong>{nameOf(item.profile_id)}</strong>{item.active && <> <span className="tag tag-accent">Active</span></>}{" "}
              <span className={`tag ${state.tag}`}>{item.qualified ? "Qualified" : state.label}</span>{" "}
              <small className="control-help">
                {item.previous_pass_current ? "An earlier pass is still valid for this configuration." : "No pass is valid for the current configuration and code."}
                {item.state.code && <> Reason: {readable(item.state.code)}.</>}
              </small>
              {item.qualification && (
                <ul aria-label={`Why ${nameOf(item.profile_id)} did not pass`}>
                  {item.qualification.findings.map((finding, index) => <Finding key={`${finding.code}-${index}`} finding={finding} />)}
                </ul>
              )}
              {!item.qualified && canRetry && (
                <>{" "}<button type="button" className="btn btn-secondary" disabled={busy || !cost} onClick={() => onRetry(item.profile_id)}>Retry Qualification</button></>
              )}
              {item.qualification && !item.qualification.retryable && (
                <p className="control-help">This result cannot be retried away: thresholds, safety filters and model settings are not HR settings. Send IT the profile and the result code above.</p>
              )}
            </li>
          );
        })}
      </ul>
      <div>
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => onAction(refreshProviderLimits)}>Refresh Limits</button>{" "}
        {remoteTarget && <><button type="button" className="btn btn-secondary" disabled={busy} onClick={() => onAction(() => testModelConnection(remoteTarget))}>Test Connection</button>{" "}</>}
        <button type="button" className="btn btn-secondary" disabled={!overview.budget?.configured}
          onClick={() => document.getElementById("daily-limit-input")?.focus()}>Review Budget</button>
      </div>
    </section>
  );
}

function RetryDialog({ name, cost, onConfirm, onCancel }: {
  name: string;
  cost: NonNullable<ModelRecovery["qualification_cost"]>;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [agreed, setAgreed] = useState(false);
  const fits = cost.budget_ok && cost.call_limit_ok;
  return (
    <section className="card" role="dialog" aria-labelledby="retry-heading">
      <h2 id="retry-heading">Run the qualification of {name}?</h2>
      <p className="ds-banner ds-banner-warn">
        This makes {cost.paid_calls} paid OpenRouter call{cost.paid_calls === 1 ? "" : "s"} on synthetic questions only, one after another. Each call holds up to {cost.reservation_micro_usd === null ? "—" : usd(exactDollars(cost.reservation_micro_usd))} until it settles; at most {cost.needed_micro_usd === null ? "—" : usd(exactDollars(cost.needed_micro_usd))} in all. Available now {cost.available_micro_usd === null ? "—" : usd(exactDollars(cost.available_micro_usd))}{cost.provider_checked ? "" : " (the OpenRouter key limit has not been read yet; the qualification reads it first)"}. It runs once; a failed or interrupted run is never repeated automatically.
      </p>
      {!fits && <p className="ds-banner ds-banner-warn" role="alert">The spending limits do not leave room for a paid call, so the server will not start it. Review the budget first.</p>}
      {fits && !cost.worst_case_ok && <p className="control-help" role="note">If every call cost its whole reservation the limits would run out part-way; the run would then stop (no call is made beyond the limits) and need a new confirmed run.</p>}
      <label className="control-help">
        <input type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} />
        {" "}I confirm {cost.paid_calls} paid call{cost.paid_calls === 1 ? "" : "s"}.
      </label>
      <div>
        <button type="button" className="btn btn-primary" disabled={!agreed || !fits} onClick={onConfirm}>Run Qualification</button>{" "}
        <button type="button" className="btn btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </section>
  );
}

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
  const [confirming, setConfirming] = useState<{ kind: "activate" | "rollback"; profileId: string; name: string } | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  // D-098: the paid qualification waiting for HR's confirmation (never started without it).
  const [retrying, setRetrying] = useState<string | null>(null);
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

  return (
    <section className="ds-root ds-page model-management" aria-labelledby="model-management-heading">
      <div className="ds-page-header"><div>
        <p className="card-kicker">HR administration · AI Assistant</p>
        <h1 id="model-management-heading">AI model management</h1>
        <p className="text-muted">Choose the model the AI Assistant uses for everyone, from the local models IT has configured on the server. Prompts, approved lines, guardrails and knowledge permissions do not change with the model.</p>
      </div></div>

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
      {overview?.file_status === "missing" && <p className="ds-banner ds-banner-warn" role="alert">The model profiles file named by IT was not found.</p>}

      {overview && (
        <section className="card" aria-labelledby="active-model-heading">
          <h2 id="active-model-heading">Active model</h2>
          {overview.active.reverted && <p className="ds-banner ds-banner-warn" role="alert">The saved model could not be used at start-up ({readable(overview.active.reverted)}), so the environment baseline is active.</p>}
          {overview.active.config_changed && <p className="ds-banner ds-banner-warn" role="status">IT changed this model's settings since it was activated. It keeps its activated settings until the service restarts, then the baseline is used until it is qualified again.</p>}
          <dl className="acra-detail-list">
            <div><dt>Name</dt><dd>{nameOf(overview.active.profile_id, overview.active.display_name)}</dd></div>
            <div><dt>Model</dt><dd>{overview.active.model_id ?? "None (case-data answers only)"}</dd></div>
            <div><dt>Changed</dt><dd>{overview.active.changed_at ? `${formatTimestamp(overview.active.changed_at)} by ${overview.active.changed_by}` : "Never (environment baseline)"}</dd></div>
            <div><dt>Prompt bound</dt><dd>{overview.active.prompt_limit ? `${overview.active.prompt_limit.toLocaleString()} (${overview.profiles.find((item) => item.active)?.deployment === REMOTE_DEPLOYMENT ? "enforced byte limit" : "verified capacity"})` : "Not applied (baseline)"}</dd></div>
            <div><dt>Revision</dt><dd>{overview.revision}</dd></div>
          </dl>
          {overview.configured && (
            <button type="button" className="btn btn-secondary" disabled={!overview.last_good || busy}
              onClick={() => overview.last_good && setConfirming({ kind: "rollback", profileId: overview.last_good.profile_id, name: nameOf(overview.last_good.profile_id, overview.last_good.display_name) })}>
              {overview.last_good ? `Roll back to ${nameOf(overview.last_good.profile_id, overview.last_good.display_name)}` : "No earlier model to roll back to"}
            </button>
          )}
        </section>
      )}

      {overview?.recovery && (
        <Recovery overview={overview} busy={busy} onAction={(run) => action.mutate(run)} onRetry={setRetrying} />
      )}

      {retrying && overview?.recovery?.qualification_cost && (
        <RetryDialog name={nameOf(retrying, retrying)} cost={overview.recovery.qualification_cost}
          onCancel={() => setRetrying(null)}
          onConfirm={() => {
            const profileId = retrying;
            const calls = overview.recovery!.qualification_cost!.paid_calls;
            setRetrying(null);
            setSelected(profileId);
            action.mutate(() => startModelQualification(profileId, calls));
          }} />
      )}

      {overview?.budget?.configured && (
        <>
          <OpenRouterKey budget={overview.budget} busy={busy}
            remoteProfileId={overview.profiles.find((item) => item.deployment === REMOTE_DEPLOYMENT && item.status === "selectable")?.profile_id ?? null}
            onChanged={refresh} />
          <SpendingLimits budget={overview.budget} busy={busy} onChanged={refresh} />
        </>
      )}

      {confirming && overview && (
        <section className="card" role="dialog" aria-labelledby="confirm-heading">
          <h2 id="confirm-heading">{confirming.kind === "rollback" ? `Roll back to ${confirming.name}?` : `Activate ${confirming.name}?`}</h2>
          <p>This changes the AI model for every user at once. Answers already being written finish with the current model.</p>
          {overview.profiles.find((item) => item.profile_id === confirming.profileId)?.deployment === REMOTE_DEPLOYMENT && (
            <p className="ds-banner ds-banner-warn">{overview.budget?.mode === "D-095"
              ? "This is an external, paid API (D-095 development mode). It is used only on verified synthetic development cases; on every other case the assistant gives the case-data answer and sends nothing. At most US$1.00 per Singapore day."
              : "This is an external, paid API (D-094 local synthetic test mode). It is used only on the approved synthetic test case; on every other case the assistant gives the case-data answer and sends nothing."}</p>
          )}
          {confirming.profileId !== "env_default" && unscored && (
            <label className="control-help">
              <input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />
              {" "}I understand this model passed technical qualification only (connection, safety filtering, availability and context capacity). Its answer quality is NOT SCORED and the qualification is not proof of answer quality.
            </label>
          )}
          <div>
            <button type="button" className="btn btn-primary" disabled={confirming.profileId !== "env_default" && unscored && !acknowledged} onClick={confirm}>Confirm</button>
            {" "}
            <button type="button" className="btn btn-secondary" onClick={() => { setConfirming(null); setAcknowledged(false); }}>Cancel</button>
          </div>
        </section>
      )}

      {overview && (
        <section className="card" aria-labelledby="available-models-heading">
          <h2 id="available-models-heading">Available models</h2>
          {overview.running && (
            <p role="status">
              Qualification running for {overview.running.profile_id}: {overview.running.done_turns}/{overview.running.total_turns} turns (started by {overview.running.started_by}).{" "}
              <button type="button" className="btn btn-secondary" disabled={action.isPending} onClick={() => action.mutate(() => cancelModelQualification(overview.running!.qualification_id))}>Cancel qualification</button>
            </p>
          )}
          <div className="table-card">
            <table className="table">
              <thead><tr><th>Model</th><th>Deployment</th><th>Endpoint</th><th>Limits</th><th>Status</th><th>Connection</th><th>Qualification</th><th>Actions</th></tr></thead>
              <tbody>
                {overview.profiles.map((item) => {
                  const usable = item.status === "selectable" && overview.configured;
                  const qualification = item.qualification;
                  return (
                    <tr key={item.profile_id}>
                      <td><strong>{profileName(item)}</strong>{item.active && <> <span className="tag tag-accent">Active</span></>}<br /><small>{item.model_id ?? "—"}{item.model_version ? ` · ${item.model_version}` : ""}</small>
                        {item.details && <><br /><RemoteDetails details={item.details} /></>}
                        {item.deployment === REMOTE_DEPLOYMENT && <><br /><small className="control-help">{overview.budget?.mode === "D-095"
                          ? "External API: answers only on verified synthetic development cases; every other case gets the case-data answer. At most US$1.00 per Singapore day. Test connection is a free preflight; qualification makes paid calls."
                          : "External API: answers only on the approved synthetic test case; every other case gets the case-data answer. Test connection is a free preflight; qualification makes paid calls."}</small></>}
                        {item.details?.reasoning_effort === "low" && <><br /><small className="control-help">Fast is the same model, endpoint and limits with less reasoning. It needs its own passing qualification; the Balanced qualification does not count for it, and its answer quality is not established.</small></>}</td>
                      <td>{readable(item.deployment)}</td>
                      <td>{item.endpoint ?? "Not shown"}</td>
                      <td><small>Context {item.context_window_tokens ? `${item.context_window_tokens.toLocaleString()} (declared)` : "—"} · answer {value(item.max_answer_tokens)} · temp {value(item.temperature)}</small></td>
                      <td><span className={`tag ${item.status === "selectable" ? "tag-accent" : "tag-warn"}`}>{STATUS_LABEL[item.status]}</span>{item.reason && <><br /><small>{readable(item.reason)}</small></>}</td>
                      <td>{item.connection_test ? <>{readable(item.connection_test.outcome)}{item.connection_test.code && <><br /><small>{readable(item.connection_test.code)}</small></>}</> : "Not tested"}</td>
                      <td>{qualification ? <button type="button" className="btn btn-secondary" onClick={() => setSelected(item.profile_id)}>{readable(qualification.status)}{!qualification.current ? " (out of date)" : ""}</button> : "Not run"}</td>
                      <td>
                        <button type="button" className="btn btn-secondary" disabled={!usable || busy} onClick={() => action.mutate(() => testModelConnection(item.profile_id))}>Test connection</button>{" "}
                        <button type="button" className="btn btn-secondary" disabled={!usable || busy || !item.endpoint} onClick={() => {
                          // A paid (remote) run is confirmed first; a local one starts at once.
                          if (item.deployment === REMOTE_DEPLOYMENT) { setRetrying(item.profile_id); return; }
                          setSelected(item.profile_id);
                          action.mutate(() => startModelQualification(item.profile_id));
                        }}>Run qualification</button>{" "}
                        <button type="button" className="btn btn-primary" disabled={!usable || busy || item.active || item.activation_blockers.length > 0}
                          title={item.activation_blockers.map(readable).join(" ")}
                          onClick={() => setConfirming({ kind: "activate", profileId: item.profile_id, name: profileName(item) })}>Activate</button>
                        {item.activation_blockers.length > 0 && usable && <><br /><small>{item.activation_blockers.map(readable).join(" ")}</small></>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {detail?.qualification && (
        <section className="card" aria-labelledby="qualification-heading">
          <h2 id="qualification-heading">Qualification: {profileName(detail)}</h2>
          <QualificationDetail qualification={detail.qualification} />
        </section>
      )}

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
    </section>
  );
}
