import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";

import {
  AiAssistantError,
  closeRecoveryRequest,
  fetchRecovery,
  openRecoveryRequest,
  resolveClaudeReconciliationRun,
  testModelConnection,
  type RecoveryAction,
  type RecoveryProblem,
  type RecoveryRequest,
  type RecoveryView,
} from "../../aiAssistant";
import { displayTimestamp } from "../../shared";
import { ConsoleDialog, sectionSearch } from "./ConsoleShell";

// Recovery centre: what stops the AI Assistant now, why, and the fix HR may make. The server
// diagnoses every problem and decides which actions are permitted; this page never infers one.
// Quick, safe actions (the free Test connection, resolving a finished run) run here after a
// confirmation; every other fix opens its existing, guarded control in its own section. Owner-only
// recoveries become a recorded request carrying the server's own evidence.

export const recoveryQueryKey = (userId: string) => ["auth", userId, "assistant-models", "recovery"] as const;

const SEVERITY: Record<RecoveryProblem["severity"], { label: string; tone: string }> = {
  blocking: { label: "Blocking", tone: "block" },
  warning: { label: "Needs attention", tone: "warn" },
  info: { label: "Information", tone: "info" },
};

const AUTHORITY: Record<RecoveryAction["authority"], string> = {
  HR: "HR can do this here",
  OWNER: "Needs the owner",
  IT: "Needs IT",
  NONE: "No action needed",
};

const INLINE: ReadonlySet<RecoveryAction["kind"]> = new Set(["TEST_CONNECTION", "RESOLVE_RUN"]);

const INLINE_TEXT: Partial<Record<RecoveryAction["kind"], string>> = {
  TEST_CONNECTION: "Test connection is free: it reads the provider's key and model status and verifies earlier calls in-band. No inference, no case data and no charge. A call that fails verification is quarantined, never settled.",
  RESOLVE_RUN: "Resolve reads the ledger's own events and records the run as applied, failed or unresolved for the owner. It never writes the ledger.",
};

function message(error: unknown): string {
  return error instanceof AiAssistantError || error instanceof Error ? error.message : "The request failed.";
}

type Pending =
  | { kind: "inline"; problem: RecoveryProblem; action: RecoveryAction }
  | { kind: "request"; problem: RecoveryProblem };

type Outcome = { code: string; cleared: boolean } | null;

function Expiries({ view }: { view: RecoveryView }) {
  const rows: Array<[string, string | null | undefined]> = [
    ["Claude chat (7-day reconciliation window)", view.expiries.claude_chat_deadline_at],
    ["Claude paid operations (24-hour window)", view.expiries.claude_paid_deadline_at],
    ["Claude HR session key ends", view.expiries.claude_hr_key_ends_at],
    ["Claude daily limit resets", view.expiries.claude_daily_reset_at],
    ["GPT-OSS HR session key ends", view.expiries.gpt_oss_hr_key_ends_at],
  ];
  const shown = rows.filter(([, value]) => value !== undefined);
  return (
    <section className="card" aria-labelledby="recovery-expiries-heading">
      <h3 id="recovery-expiries-heading">Separate deadlines</h3>
      <p className="text-muted">Each window is independent: renewing one never extends another. Times are Singapore time.</p>
      <dl className="acra-detail-list" data-testid="recovery-expiries">
        {shown.map(([label, value]) => (
          <div key={label}><dt>{label}</dt><dd>{displayTimestamp(value, "Not set")}</dd></div>
        ))}
        {view.expiries.qualifications.map((item) => (
          <div key={item.profile_id}>
            <dt>Qualification: {item.display_name}{item.active ? " (active)" : ""}</dt>
            <dd>{item.status}{item.status === "passed" ? (item.current ? ", current (valid until the code or configuration changes)" : ", out of date") : ""}{item.finished_at ? `, finished ${displayTimestamp(item.finished_at)}` : ""}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function ActionControl({ problem, action, busy, onInline, onRequest }: {
  problem: RecoveryProblem;
  action: RecoveryAction;
  busy: boolean;
  onInline: () => void;
  onRequest: () => void;
}) {
  if (action.kind === "OWNER_REQUEST") {
    return problem.owner_request_allowed
      ? <button type="button" className="btn btn-secondary" disabled={busy} onClick={onRequest}>{action.label}</button>
      : null;
  }
  if (action.kind === "WAIT") return <span className="console-help">{action.label}.</span>;
  if (!action.permitted) {
    return (
      <span className="console-help" data-testid="recovery-action-blocked">
        {action.label}: {action.blocked_by.length > 0 ? `first clear ${action.blocked_by.join(", ")}` : AUTHORITY[action.authority].toLowerCase()}.
      </span>
    );
  }
  if (INLINE.has(action.kind) && (action.run_id ?? action.profile_id)) {
    return <button type="button" className="btn btn-primary" disabled={busy} onClick={onInline}>{action.label}</button>;
  }
  return <Link className="btn btn-primary" to={{ search: sectionSearch(action.section) }}>{action.label}</Link>;
}

function ProblemCard({ problem, busy, outcome, onInline, onRequest }: {
  problem: RecoveryProblem;
  busy: boolean;
  outcome: Outcome;
  onInline: (action: RecoveryAction) => void;
  onRequest: () => void;
}) {
  const severity = SEVERITY[problem.severity];
  return (
    <li className="console-recovery__item" data-testid={`recovery-problem-${problem.code}`}>
      <div className="console-recovery__head">
        <span className={`console-chip console-chip--${severity.tone}`}>{severity.label}</span>
        <h3>{problem.title}</h3>
      </div>
      <p>{problem.cause}</p>
      {problem.evidence.length > 0 && (
        <dl className="acra-detail-list">
          {problem.evidence.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
        </dl>
      )}
      <p className="console-help">Code <code className="console-code">{problem.code}</code>. After fixing: {problem.actions[0]?.verify ?? "check again"}.</p>
      {outcome?.code === problem.code && !outcome.cleared && (
        <p className="ds-banner ds-banner-warn" role="status">Checked again: the problem is still reported.</p>
      )}
      <div className="console-recovery__actions">
        {problem.actions.map((action, index) => (
          <ActionControl key={`${action.kind}-${index}`} problem={problem} action={action} busy={busy}
            onInline={() => onInline(action)} onRequest={onRequest} />
        ))}
      </div>
    </li>
  );
}

function Requests({ requests, busy, onClose }: {
  requests: RecoveryRequest[];
  busy: boolean;
  onClose: (request: RecoveryRequest, status: "resolved" | "withdrawn") => void;
}) {
  if (requests.length === 0) return null;
  return (
    <section className="card" aria-labelledby="recovery-requests-heading">
      <h3 id="recovery-requests-heading">Owner recovery requests</h3>
      <p className="text-muted">A request records the problem and the server's evidence for the owner. It changes nothing by itself. It can be marked resolved only once the server no longer reports the problem.</p>
      <ul className="console-recovery__list">
        {requests.map((request) => (
          <li key={request.request_id} className="console-recovery__item" data-testid="recovery-request">
            <div className="console-recovery__head">
              <span className={`console-chip console-chip--${request.status === "open" ? "warn" : "neutral"}`}>{request.status}</span>
              <h4><code className="console-code">{request.problem_code}</code></h4>
            </div>
            <p className="console-help">Requested by {request.created_by} on {displayTimestamp(request.created_at)}{request.closed_at ? `; ${request.status} by ${request.closed_by} on ${displayTimestamp(request.closed_at)}` : ""}.</p>
            {request.note && <p>Note: {request.note}</p>}
            {request.status === "open" && (
              <div className="console-recovery__actions">
                <button type="button" className="btn btn-primary" disabled={busy || request.problem_present}
                  title={request.problem_present ? "The problem is still reported" : undefined}
                  onClick={() => onClose(request, "resolved")}>{request.problem_present ? "Still reported" : "Mark resolved"}</button>
                <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => onClose(request, "withdrawn")}>Withdraw</button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function RecoveryCentre({ userId, onChanged }: { userId: string; onChanged: () => void }) {
  const queryClient = useQueryClient();
  // A request change answers with the whole view: show it at once.
  const show = (fresh: RecoveryView) => queryClient.setQueryData(recoveryQueryKey(userId), fresh);
  const query = useQuery({
    queryKey: recoveryQueryKey(userId),
    queryFn: ({ signal }) => fetchRecovery(signal),
    retry: false,
    refetchInterval: 60_000,
  });
  const [pending, setPending] = useState<Pending | null>(null);
  const [note, setNote] = useState("");
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [announcement, setAnnouncement] = useState("");

  const run = useMutation({
    mutationFn: async (work: () => Promise<unknown>) => await work(),
    retry: false,
    onSettled: onChanged,
  });

  async function verify(code: string): Promise<void> {
    const fresh = await query.refetch();
    const cleared = !fresh.data?.problems.some((item) => item.code === code);
    setOutcome({ code, cleared });
    setAnnouncement(cleared ? "Recovery verified: the problem is no longer reported." : "The problem is still reported.");
  }

  function confirmPending(): void {
    const current = pending;
    setPending(null);
    if (!current) return;
    if (current.kind === "inline") {
      const { action, problem } = current;
      const target = action.kind === "RESOLVE_RUN" ? action.run_id : action.profile_id;
      if (!target) return;
      const work = action.kind === "RESOLVE_RUN"
        ? () => resolveClaudeReconciliationRun(target)
        : () => testModelConnection(target);
      run.mutate(work, { onSuccess: () => void verify(problem.code) });
      return;
    }
    const text = note.trim();
    setNote("");
    run.mutate(() => openRecoveryRequest(current.problem.code, text || null), {
      onSuccess: (fresh) => { show(fresh as RecoveryView); setAnnouncement("Owner recovery request recorded."); },
    });
  }

  const view = query.data;
  const busy = run.isPending || query.isFetching;
  return (
    <section className="card console-recovery" aria-labelledby="recovery-centre-heading" data-testid="recovery-centre">
      <div className="console-recovery__head">
        <h2 id="recovery-centre-heading">Recovery centre</h2>
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => void query.refetch().then(() => setAnnouncement("Checked again."))}>Check again</button>
      </div>
      <p className="sr-only" role="status" aria-live="polite">{announcement}</p>
      {query.isPending && <p role="status">Checking the AI Assistant…</p>}
      {query.isError && <p className="ds-banner ds-banner-warn" role="alert">{message(query.error)}</p>}
      {run.isError && <p className="ds-banner ds-banner-warn" role="alert">{message(run.error)}</p>}
      {outcome?.cleared && <p className="ds-banner" role="status" data-testid="recovery-verified">Recovery verified: <code className="console-code">{outcome.code}</code> is no longer reported.</p>}
      {view && (
        <>
          <p className={view.healthy ? "ds-banner" : "ds-banner ds-banner-warn"} data-testid="recovery-summary">
            {view.problems.length === 0
              ? "No problem is reported. The AI Assistant can answer within its limits."
              : `${view.problems.length} ${view.problems.length === 1 ? "item needs" : "items need"} attention${view.healthy ? "; none stops the AI Assistant now" : ""}. Checked ${displayTimestamp(view.generated_at)}.`}
          </p>
          {view.problems.length > 0 && (
            <ul className="console-recovery__list">
              {view.problems.map((problem) => (
                <ProblemCard key={`${problem.code}-${problem.title}`} problem={problem} busy={busy} outcome={outcome}
                  onInline={(action) => setPending({ kind: "inline", problem, action })}
                  onRequest={() => setPending({ kind: "request", problem })} />
              ))}
            </ul>
          )}
          <Expiries view={view} />
          <Requests requests={view.requests} busy={busy}
            onClose={(request, status) => run.mutate(() => closeRecoveryRequest(request.request_id, status), {
              onSuccess: (fresh) => { show(fresh as RecoveryView); setAnnouncement(status === "resolved" ? "Request marked resolved." : "Request withdrawn."); },
            })} />
        </>
      )}

      {pending && (
        <ConsoleDialog labelledBy="recovery-confirm-heading" testId="recovery-confirm" focusFallbackIds={["recovery-centre-heading"]}
          onClose={() => { setPending(null); setNote(""); }}>
          {pending.kind === "inline" ? (
            <>
              <h2 id="recovery-confirm-heading">{pending.action.label}?</h2>
              <p>{INLINE_TEXT[pending.action.kind]}</p>
              <p className="console-help">Afterwards the page checks again whether <code className="console-code">{pending.problem.code}</code> is still reported.</p>
            </>
          ) : (
            <>
              <h2 id="recovery-confirm-heading">Request owner recovery?</h2>
              <p>This records a request for the owner with the server's evidence below. It does not change the ledger, a limit, a key or a model, and HR cannot reset or release anything through it.</p>
              <dl className="acra-detail-list">
                <div><dt>Problem</dt><dd><code className="console-code">{pending.problem.code}</code></dd></div>
                {pending.problem.evidence.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
              </dl>
              <label htmlFor="recovery-note">Note for the owner (optional; never a key or secret)</label>
              <textarea id="recovery-note" maxLength={280} rows={3} value={note} onChange={(event) => setNote(event.target.value)} />
            </>
          )}
          <div className="console-dialog__actions">
            <button type="button" className="btn btn-secondary" onClick={() => { setPending(null); setNote(""); }}>Cancel</button>
            <button type="button" className="btn btn-primary" onClick={confirmPending}>Confirm</button>
          </div>
        </ConsoleDialog>
      )}
    </section>
  );
}
