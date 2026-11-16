import { useQuery } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link } from "react-router";

import {
  AiAssistantError,
  activateModel,
  ledgerRefusal,
  fetchSetup,
  readAnthropicWorkspace,
  RESUMABLE_STOPS,
  resumeBreaker,
  saveAnthropicEnablement,
  saveModelCredential,
  savePaidSessionAllowance,
  startModelQualification,
  startPaidSession,
  testModelConnection,
  type ModelConnectionTest,
  type ModelOverview,
  type ModelPaidQualification,
  type ModelProfileView,
  type PaidLimit,
  type PaidProvider,
  type ProviderSetup,
  type ResumableStop,
  type SetupBlocker,
} from "../../aiAssistant";
import { ConsoleDialog } from "./ConsoleShell";

// D-118: the guided setup — choose a model, save and test its key, test & qualify, activate.
// Every decision is the server's: this page shows its answers and sends one action at a time.
// The paid-session allowance is US$5.00 unless HR chooses less; nothing here needs to confirm it.

export const setupQueryKey = (userId: string) => ["auth", userId, "assistant-models", "setup"] as const;

type Kind = PaidProvider | "local";

const kindOf = (item: Pick<ModelProfileView, "deployment" | "source">): Kind =>
  item.deployment === "anthropic" ? "anthropic" : item.source === "code" ? "openrouter" : "local";

const usd = (micro: number | null | undefined) =>
  micro === null || micro === undefined ? "—" : `US$${(micro / 1_000_000).toFixed(2)}`;

/** Whole micro-USD from a typed US$ amount; null unless a plain amount with at most six places. */
function micro(text: string): number | null {
  const match = /^\s*(\d{1,4})(?:\.(\d{1,6}))?\s*$/.exec(text);
  if (!match) return null;
  return Number(match[1]) * 1_000_000 + Number((match[2] ?? "").padEnd(6, "0"));
}

type Describe = (code: string | null | undefined, deployment?: string) => string;

function message(error: unknown, describe?: Describe, deployment?: string): string {
  if (!(error instanceof AiAssistantError)) return "The AI assistant service could not complete this request.";
  // A closed refusal code the page can name says more than the server's generic fallback.
  const named = error.code && describe ? describe(error.code, deployment) : "";
  return named && GENERIC_MESSAGES.has(error.message) ? named : error.message;
}

// The server's catch-all messages: when a refusal carries one of these, the page names its code.
const GENERIC_MESSAGES = new Set([
  "The model could not be prepared on the server.",
  "This model is not ready for a paid run yet. See Set up AI for what is missing. Nothing started.",
]);

/** Thrown when the free connection check answered but did not pass (it is never a paid call). */
class ConnectionNotPassed extends Error {}

const LIMIT_TEXT: Record<PaidLimit, { label: string; short: (left: string) => string }> = {
  session: { label: "Session allowance", short: (left) => `This session's allowance has ${left} left. Start a new session, or choose a larger allowance (up to US$5.00).` },
  daily: { label: "Today's limit", short: (left) => `Today's limit has ${left} left. HR can raise it in Spending & Limits, or wait for the Singapore-day reset.` },
  lifetime: { label: "Lifetime limit", short: (left) => `The lifetime limit has ${left} left. HR can raise it in Spending & Limits.` },
  provider: { label: "Provider key limit", short: (left) => `The provider key's own limit has ${left} left. Only the key's owner can raise it, at the provider.` },
};
const LIMIT_ORDER: PaidLimit[] = ["session", "daily", "lifetime", "provider"];

/** Why a paid qualification cannot start, naming the one prerequisite or limit that blocks it. */
function blockedReason(paid: ModelPaidQualification | null | undefined, describe: Describe, deployment: string): string | null {
  if (!paid) return "The server did not report what a paid qualification would cost. Refresh the page.";
  if (paid.sufficient) return null;
  if (paid.unavailable) return describe(paid.unavailable, deployment);
  if (paid.blocking) {
    const left = paid.limits?.[paid.blocking];
    return `${LIMIT_TEXT[paid.blocking].short(usd(left))} The ${paid.calls} paid calls may cost up to ${usd(paid.estimate_micro_usd)}.`;
  }
  return paid.refusal ? describe(paid.refusal, deployment) : "The server did not say why a paid run cannot start now. Refresh the page.";
}

const ALL_CONFIRMATIONS = ["dedicated_workspace", "workspace_limit_set", "inference_key_only", "key_revoked_at_fyp_end"];

const BLOCKER_TEXT: Record<string, string> = {
  LEDGER_CREATED_AT_SETUP: "Its spending ledger is created when you finish step 2 (no script needed).",
  LEGACY_STORE: "The launcher still names a spending store from the earlier design, which this console never uses. The owner archives it and points the launcher at a session store.",
  SESSION_ALLOWANCE_USED: "This session's allowance is used up, so paid calls have stopped. Nothing renews it by itself.",
};

function blockerText(blocker: SetupBlocker, setup: ProviderSetup): string {
  if (blocker.code.startsWith("BREAKER_OPEN")) {
    return blocker.action === "RESUME"
      ? `Paid calls are paused (${setup.breaker_code ?? "unknown"}): a call was interrupted, refused by the provider or cost more than its estimate. Every charge is kept and nothing is retried. Fix the cause (for example the key or the provider limit), then resume.`
      : `Paid calls are stopped for the owner (${setup.breaker_code ?? "unknown"}): a model, provider or workspace mismatch, or a ledger problem. Ask the owner to review it.`;
  }
  return BLOCKER_TEXT[blocker.code] ?? `The owner must act (${blocker.code}).`;
}

function Step({ number, title, state, children }: {
  number: number;
  title: string;
  state: "done" | "current" | "waiting";
  children?: ReactNode;
}) {
  const label = state === "done" ? "Done" : state === "current" ? "Next" : "Waiting";
  return (
    <li className={`guided-step guided-step--${state}`} aria-current={state === "current" ? "step" : undefined}>
      <div className="guided-step__head">
        <span className="guided-step__number" aria-hidden="true">{number}</span>
        <h3>{title}</h3>
        <span className={`console-chip console-chip--${state === "done" ? "neutral" : state === "current" ? "info" : "neutral"}`}>{label}</span>
      </div>
      {state !== "waiting" && children}
    </li>
  );
}

export function GuidedSetup({ userId, overview, busy, nameOf, describe = (code) => code ?? "", onChanged }: {
  userId: string;
  overview: ModelOverview;
  busy: boolean;
  nameOf: (profileId: string, fallback: string) => string;
  /** Plain text for a closed server code (AiModelManagement's readable). */
  describe?: Describe;
  onChanged: () => void;
}) {
  const setupQuery = useQuery({ queryKey: setupQueryKey(userId), queryFn: ({ signal }) => fetchSetup(signal) });
  const choosable = overview.profiles.filter((item) => item.status === "selectable" || kindOf(item) !== "local");
  const [choice, setChoice] = useState<string | null>(null);
  const item = overview.profiles.find((entry) => entry.profile_id === choice)
    ?? overview.profiles.find((entry) => entry.active)
    ?? null;
  const kind = item ? kindOf(item) : null;
  const paid = kind === "anthropic" || kind === "openrouter";
  const provider = paid ? (kind as PaidProvider) : null;
  const providerSetup = provider ? setupQuery.data?.providers[provider] ?? null : null;
  const claude = overview.anthropic_setup;
  const storedLimit = claude?.record?.workspace_limit_micro_usd;

  const [key, setKey] = useState("");
  const [pending, setPending] = useState(false);
  const [note, setNote] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  // null: untouched, so the field shows the stored record's limit (re-confirming an existing
  // record never changes it silently), else US$5.00 for a first setup.
  const [limitEdit, setLimitEdit] = useState<string | null>(null);
  const limitText = limitEdit ?? (typeof storedLimit === "number" && storedLimit > 0
    ? (storedLimit / 1_000_000).toFixed(2) : "5.00");
  const [workspaceOwned, setWorkspaceOwned] = useState(false);
  const [revokeAtEnd, setRevokeAtEnd] = useState(false);
  const [allowanceText, setAllowanceText] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"qualify" | "activate" | "new-session" | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);

  /** One action at a time; true when it finished without an error. */
  async function run(action: () => Promise<unknown>, done: string): Promise<boolean> {
    setPending(true);
    setNote(null);
    let ok = false;
    try {
      const said = await action();
      setNote({ kind: "ok", text: typeof said === "string" && said ? said : done });
      ok = true;
    } catch (error) {
      setNote({ kind: "error", text: error instanceof ConnectionNotPassed ? error.message : message(error, describe, item?.deployment) });
    } finally {
      setKey("");
      setPending(false);
      setDialog(null);
      onChanged();
    }
    return ok;
  }

  /** The free connection check; it throws (so nothing advances) unless it passed. */
  async function checkConnection(profileId: string): Promise<void> {
    const result: ModelConnectionTest = await testModelConnection(profileId);
    if (result.outcome !== "passed") {
      throw new ConnectionNotPassed(`The connection check did not pass: ${describe(result.code ?? "CONNECTION_FAILED", item?.deployment)}`);
    }
  }

  const working = busy || pending;
  // Claude needs its one-time setup until it is enabled and its session store exists (an
  // enablement record from before D-118 has no store: confirming the setup again creates it).
  const claudeStoreMissing = kind === "anthropic" && (claude?.enabled ?? false) && providerSetup?.ledger === "missing";
  const claudeNeedsSetup = kind === "anthropic" && (!(claude?.enabled ?? false) || claudeStoreMissing);
  const lastTest = item?.connection_test ?? null;
  const connected = lastTest?.outcome === "passed" && !claudeNeedsSetup;
  const qualified = Boolean(item?.eligible_qualification);
  const session = providerSetup?.session ?? null;
  const paidEstimate = item?.paid_qualification ?? null;
  const reservation = paidEstimate?.reservation_micro_usd ?? null;
  // Step 3's own prerequisites: a passed connection and, for a paid model, a nameable cost.
  const qualifyBlocker = !item || !paid || !connected ? null
    : paidEstimate?.unavailable ? describe(paidEstimate.unavailable, item.deployment)
    : !paidEstimate ? "The server did not report what a paid qualification would cost. Refresh the page."
    : null;
  const unscored = overview.quality.status !== "SCORED" && item?.profile_id !== "env_default";

  function saveAndTest(): void {
    if (!item || !provider) return;
    const value = key;
    void run(async () => {
      await saveModelCredential(value, provider);
      if (provider === "anthropic" && claudeNeedsSetup) {
        const read = await readAnthropicWorkspace();
        if (read.outcome !== "passed") throw new ConnectionNotPassed(`The key's workspace could not be read: ${describe(read.code ?? "WORKSPACE_NOT_READ", item.deployment)} Check the key, then try again.`);
        return "Key saved for this session (never stored in the browser) and its workspace read. Finish the one-time setup below.";
      }
      await checkConnection(item.profile_id);
      return "Key saved for this session (never stored in the browser). The connection check passed.";
    }, "Key saved.");
  }

  function enableClaude(): void {
    if (!item || !claude?.workspace_read) return;
    const limit = micro(limitText);
    void run(async () => {
      await saveAnthropicEnablement({
        expected_revision: claude.record?.revision ?? 0,
        enabled: true,
        workspace_id: claude.workspace_read!.workspace_id,
        workspace_limit_micro_usd: limit ?? -1,
        confirmations: ALL_CONFIRMATIONS,
      });
      await checkConnection(item.profile_id);
    }, "Claude is set up and the connection check passed.");
  }

  function openQualification(): void {
    if (!item) return;
    // The free connection check first (after a restart too), then the one paid consent; a
    // failed check never opens it.
    void run(() => checkConnection(item.profile_id), "The connection check passed.").then((ok) => { if (ok) setDialog("qualify"); });
  }

  function saveAllowance(): void {
    if (!provider || allowanceText === null) return;
    const amount = micro(allowanceText);
    if (amount === null || amount < 1 || amount > (providerSetup?.allowance_max_micro_usd ?? 5_000_000)) {
      setNote({ kind: "error", text: "Enter an amount above US$0.00 and no more than US$5.00." });
      return;
    }
    void run(
      () => (session ? savePaidSessionAllowance(provider, amount, session.revision) : startPaidSession(provider, amount, null)),
      `Session allowance set to ${usd(amount)}.`,
    ).then(() => setAllowanceText(null));
  }

  const claudeReady = workspaceOwned && revokeAtEnd && micro(limitText) !== null;

  return (
    <section className="card guided-setup" aria-labelledby="guided-setup-heading">
      <p className="card-kicker">Set up AI</p>
      <h2 id="guided-setup-heading">Choose a model, connect it, qualify it, then activate it</h2>
      <p className="text-muted">
        External models (Claude, GPT-OSS) answer onboarding questions on any case the user may read. Each paid model gets a session allowance of US$5.00 by default;
        qualification and chat share it. Local models need no key and no allowance.
      </p>

      <SessionStrip overview={overview} setup={setupQuery.data?.providers ?? null} nameOf={nameOf} working={working}
        onResume={(target) => {
          const code = setupQuery.data?.providers[target].breaker_code;
          if (code && (RESUMABLE_STOPS as readonly string[]).includes(code)) {
            void run(() => resumeBreaker(target, code as ResumableStop), "Paid calls resumed; every charge was kept.");
          }
        }}
        onNewSession={() => setDialog("new-session")} focus={provider} />

      {note && <p className={note.kind === "ok" ? "ds-banner ds-banner-info" : "ds-banner ds-banner-warn"} role={note.kind === "ok" ? "status" : "alert"}>{note.text}</p>}

      <ol className="guided-steps">
        <Step number={1} title="Select a model" state={item ? "done" : "current"}>
          <div className="guided-choices" role="radiogroup" aria-label="Model">
            {choosable.map((entry) => {
              const entryKind = kindOf(entry);
              return (
                <label key={entry.profile_id} className={entry.profile_id === item?.profile_id ? "guided-choice is-selected" : "guided-choice"}>
                  <input type="radio" name="guided-model" value={entry.profile_id} checked={entry.profile_id === item?.profile_id}
                    onChange={() => { setChoice(entry.profile_id); setNote(null); }} />
                  <span className="guided-choice__name">{nameOf(entry.profile_id, entry.display_name)}</span>
                  <span className="guided-choice__meta">
                    {entryKind === "local" ? "Local · free" : "Paid · every authorised case"}
                    {entry.active ? " · active" : ""}
                  </span>
                </label>
              );
            })}
          </div>
        </Step>

        <Step number={2} title={paid ? "Enter the API key and test the connection" : "Test the connection"}
          state={!item ? "waiting" : connected ? "done" : "current"}>
          {paid && provider ? (
            <>
              <form className="guided-row" onSubmit={(event) => { event.preventDefault(); saveAndTest(); }}>
                <label className="control-help" htmlFor="guided-key">{provider === "anthropic" ? "Anthropic inference API key" : "OpenRouter API key"}</label>
                <input id="guided-key" type="password" autoComplete="off" spellCheck={false} value={key}
                  onChange={(event) => setKey(event.target.value)} />
                <button type="submit" className="btn btn-primary" disabled={working || key.trim() === ""}>Save &amp; test</button>
              </form>
              <p className="control-help">The key is held by the server for your sign-in session only; it is never shown again or kept in the browser.</p>
              {lastTest && !claudeNeedsSetup && (
                <p className={lastTest.outcome === "passed" ? "control-help" : "ds-banner ds-banner-warn"} role="status" data-testid="guided-connection">
                  {lastTest.outcome === "passed"
                    ? "Connection check passed."
                    : `Connection check failed: ${describe(lastTest.code ?? "CONNECTION_FAILED", item?.deployment)}${ledgerRefusal(lastTest) ? ` Spending store: ${describe(ledgerRefusal(lastTest) ?? "", item?.deployment)}` : ""} Fix it, then test again (or save a new key).`}
                </p>
              )}
              {/* After a failed check too: a stored failure must never need the key retyped. */}
              {lastTest && !claudeNeedsSetup && <button type="button" className="btn btn-secondary" disabled={working}
                onClick={() => void run(() => checkConnection(item!.profile_id), "The connection check passed.")}>Test again</button>}
              {claudeNeedsSetup && claude?.workspace_read && (
                <fieldset className="guided-claude-setup">
                  <legend>{claudeStoreMissing ? "Finish Claude setup (creates its session store) for workspace " : "One-time Claude setup for workspace "}<code className="console-code">{claude.workspace_read.workspace_id}</code></legend>
                  <p className="control-help">These are the owner's statements; the app cannot read them from Anthropic.</p>
                  <label><input type="checkbox" checked={workspaceOwned} onChange={(event) => setWorkspaceOwned(event.target.checked)} />{" "}
                    This inference key belongs to an Anthropic workspace used only for this FYP project, with a monthly spend limit set in the Anthropic Console no higher than:</label>
                  <label className="guided-inline" htmlFor="guided-limit">US$</label>
                  <input id="guided-limit" inputMode="decimal" value={limitText} onChange={(event) => setLimitEdit(event.target.value)} />
                  <label><input type="checkbox" checked={revokeAtEnd} onChange={(event) => setRevokeAtEnd(event.target.checked)} />{" "}
                    The key will be revoked when the FYP ends.</label>
                  <button type="button" className="btn btn-primary" disabled={working || !claudeReady} onClick={enableClaude}>{claudeStoreMissing ? "Confirm and create the session store" : "Enable Claude"}</button>
                </fieldset>
              )}
            </>
          ) : (
            item && <button type="button" className="btn btn-primary" disabled={working}
              onClick={() => void run(() => checkConnection(item.profile_id), "The connection check passed.")}>Test connection</button>
          )}
        </Step>

        <Step number={3} title="Run qualification" state={!connected ? "waiting" : qualified ? "done" : "current"}>
          {paid && (
            <>
              <p className="control-help" data-testid="guided-cost">
                {paidEstimate?.calls
                  ? <>Qualification makes {paidEstimate.calls} paid calls, reserving at most {usd(paidEstimate.estimate_micro_usd)} ({usd(reservation)} each) until they settle.</>
                  : <>One answer reserves at most {usd(reservation)} until it settles.</>}
              </p>
              <p className="control-help">
                Session allowance {usd(session?.allowance_micro_usd ?? providerSetup?.allowance_default_micro_usd ?? 5_000_000)}
                {session ? `, ${usd(session.remaining_micro_usd)} left` : " (starts with the first paid call)"}.{" "}
                {allowanceText === null
                  ? <button type="button" className="btn btn-secondary" onClick={() => setAllowanceText("")}>{session ? "Change the allowance" : "Use a smaller amount"}</button>
                  : (
                    <span className="guided-inline">
                      <label htmlFor="guided-allowance">US$</label>
                      <input id="guided-allowance" inputMode="decimal" value={allowanceText} onChange={(event) => setAllowanceText(event.target.value)} />
                      <button type="button" className="btn btn-secondary" disabled={working} onClick={saveAllowance}>Save</button>
                      <button type="button" className="btn btn-secondary" onClick={() => setAllowanceText(null)}>Cancel</button>
                    </span>
                  )}
              </p>
            </>
          )}
          {qualifyBlocker && <p className="ds-banner ds-banner-warn" role="alert" data-testid="guided-qualify-blocker">Qualification cannot start yet: {qualifyBlocker}</p>}
          <button type="button" className="btn btn-primary" disabled={working || !item || !connected || qualifyBlocker !== null}
            onClick={() => (paid
              ? openQualification()
              : void run(() => startModelQualification(item!.profile_id), "Qualification started."))}>
            {paid ? "Run qualification…" : "Run qualification"}
          </button>
          {overview.running && <p className="control-help" role="status">Qualifying {nameOf(overview.running.profile_id, overview.running.profile_id)}: {overview.running.done_turns} of {overview.running.total_turns || "?"} questions.</p>}
        </Step>

        <Step number={4} title="Activate & chat" state={!qualified ? "waiting" : item?.active ? "done" : "current"}>
          {item?.active
            ? <p className="control-help">Active. Case users can now ask the AI Assistant on an open case.</p>
            : <button type="button" className="btn btn-primary" disabled={working || (item?.activation_blockers.length ?? 1) > 0}
              onClick={() => { setAcknowledged(false); setDialog("activate"); }}>Activate…</button>}
        </Step>
      </ol>

      <p className="control-help">
        Limits, accounting records, the recovery centre and the audit trail are under{" "}
        <Link to={{ search: "?section=overview" }}>Administration</Link>.
      </p>

      {dialog === "qualify" && item && (
        <ConsoleDialog labelledBy="guided-qualify-heading" testId="guided-qualify" onClose={() => setDialog(null)}>
          <h2 id="guided-qualify-heading">{paidEstimate?.calls ? `Run ${paidEstimate.calls} paid test calls?` : "Run the paid test calls?"}</h2>
          <p>
            They ask {nameOf(item.profile_id, item.display_name)} the approved synthetic test questions, with nothing retried automatically.
            {paidEstimate?.estimate_micro_usd != null
              ? ` Together they reserve at most ${usd(paidEstimate.estimate_micro_usd)} (${usd(reservation)} each); what they actually cost is charged when they settle.`
              : ""}
          </p>
          {paidEstimate?.limits && Object.keys(paidEstimate.limits).length > 0 && (
            <dl className="guided-limits" data-testid="guided-limits">
              {LIMIT_ORDER.filter((name) => paidEstimate.limits?.[name] !== undefined).map((name) => (
                <div key={name}><dt>{LIMIT_TEXT[name].label}</dt><dd>{usd(paidEstimate.limits?.[name])} left{paidEstimate.blocking === name ? " (too little)" : ""}</dd></div>
              ))}
            </dl>
          )}
          {!paidEstimate?.sufficient && (
            <p className="ds-banner ds-banner-warn" role="alert">It cannot start now. {blockedReason(paidEstimate, describe, item.deployment)}</p>
          )}
          <div className="console-dialog__actions">
            <button type="button" className="btn btn-secondary" onClick={() => setDialog(null)}>Cancel</button>
            <button type="button" className="btn btn-primary" disabled={working || !paidEstimate?.sufficient}
              onClick={() => void run(() => startModelQualification(item.profile_id, paidEstimate?.calls ?? undefined), "Qualification started.")}>
              Run paid test calls
            </button>
          </div>
        </ConsoleDialog>
      )}

      {dialog === "activate" && item && (
        <ConsoleDialog labelledBy="guided-activate-heading" testId="guided-activate" onClose={() => setDialog(null)}>
          <h2 id="guided-activate-heading">Activate {nameOf(item.profile_id, item.display_name)}?</h2>
          {paid && <p className="ds-banner ds-banner-warn">This is an external, paid API. It receives the case facts and ownership data, and its answers count against the session allowance.</p>}
          {unscored && (
            <label><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />{" "}
              I understand this model passed technical qualification only; its answer quality is not scored.</label>
          )}
          <div className="console-dialog__actions">
            <button type="button" className="btn btn-secondary" onClick={() => setDialog(null)}>Cancel</button>
            <button type="button" className="btn btn-primary" disabled={working || (unscored && !acknowledged)}
              onClick={() => void run(() => activateModel(item.profile_id, overview.revision, unscored && acknowledged), "Activated.")}>
              Activate
            </button>
          </div>
        </ConsoleDialog>
      )}

      {dialog === "new-session" && provider && (
        <ConsoleDialog labelledBy="guided-session-heading" testId="guided-new-session" onClose={() => setDialog(null)}>
          <h2 id="guided-session-heading">Start a new US$5.00 session?</h2>
          <p>
            The current session used {usd(session?.committed_micro_usd)} of {usd(session?.allowance_micro_usd)}. It is kept on record;
            the daily and lifetime limits still apply to the new one.
          </p>
          <div className="console-dialog__actions">
            <button type="button" className="btn btn-secondary" onClick={() => setDialog(null)}>Cancel</button>
            <button type="button" className="btn btn-primary" disabled={working}
              onClick={() => void run(() => startPaidSession(provider, 5_000_000, session?.session_id ?? null), "A new session started.")}>
              Start new session
            </button>
          </div>
        </ConsoleDialog>
      )}
    </section>
  );
}

function SessionStrip({ overview, setup, nameOf, working, focus, onResume, onNewSession }: {
  overview: ModelOverview;
  setup: Record<PaidProvider, ProviderSetup> | null;
  nameOf: (profileId: string, fallback: string) => string;
  working: boolean;
  focus: PaidProvider | null;
  onResume: (provider: PaidProvider) => void;
  onNewSession: () => void;
}) {
  const shown = setup ? (focus ? [setup[focus]] : Object.values(setup).filter((entry) => entry.session || entry.blockers.length > 0)) : [];
  return (
    <div className="guided-strip" data-testid="session-strip">
      <p><span className="console-label">Active model</span>{overview.active.unavailable ? "None (AI unavailable)" : nameOf(overview.active.profile_id, overview.active.display_name)}</p>
      {shown.map((entry) => (
        <div key={entry.provider} className="guided-strip__provider">
          <p>
            <span className="console-label">{entry.provider === "anthropic" ? "Claude session" : "GPT-OSS session"}</span>
            {entry.session
              ? `${usd(entry.session.settled_micro_usd)} used, ${usd(entry.session.held_micro_usd)} held, ${usd(entry.session.remaining_micro_usd)} left of ${usd(entry.session.allowance_micro_usd)}`
              : `Not started (US$${(entry.allowance_default_micro_usd / 1_000_000).toFixed(2)} at the first paid action)`}
          </p>
          {entry.blockers.map((blocker) => (
            <p key={blocker.code} className={blocker.who === "owner" ? "ds-banner ds-banner-warn" : "ds-banner ds-banner-info"} role="status">
              {blockerText(blocker, entry)}{" "}
              {blocker.action === "RESUME" && <button type="button" className="btn btn-secondary" disabled={working} onClick={() => onResume(entry.provider)}>Resume, keeping the charge</button>}
              {blocker.action === "NEW_SESSION" && <button type="button" className="btn btn-secondary" disabled={working} onClick={onNewSession}>Start a new session…</button>}
              {blocker.action === "OWNER" && <Link to={{ search: "?section=overview" }}>Open the recovery centre</Link>}
            </p>
          ))}
        </div>
      ))}
      <p className="control-help">
        The app never admits a paid call whose worst case would exceed what is left. Real charges can still go slightly over: one call above its
        worst case, or use of the same key outside this app. The provider's own limit is the hard ceiling (the OpenRouter key's limit; the Anthropic
        workspace's monthly limit, which resets each month).
      </p>
    </div>
  );
}
