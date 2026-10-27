import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  activateModel,
  AiAssistantError,
  cancelModelQualification,
  fetchModelAudit,
  fetchModelOverview,
  rollbackModel,
  startModelQualification,
  testModelConnection,
  type ModelOverview,
  type ModelProfileView,
  type ModelQualification,
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
};

function readable(code: string | null | undefined): string {
  if (!code) return "";
  return REASON_TEXT[code] ?? code.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase());
}

function safeError(error: unknown): string {
  return error instanceof AiAssistantError ? error.message : "The AI assistant service could not complete this request.";
}

function value(item: unknown): string {
  if (item === null || item === undefined) return "—";
  if (typeof item === "number") return Number.isInteger(item) ? item.toLocaleString() : item.toFixed(3);
  if (typeof item === "object") return Object.entries(item as Record<string, unknown>).map(([key, entry]) => `${readable(key)}: ${value(entry)}`).join(" · ");
  return String(item);
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

export default function AiModelManagement({ actor }: { actor: AuthenticatedProfile }) {
  const queryClient = useQueryClient();
  const overviewQuery = useQuery({
    queryKey: modelManagementQueryKeys.overview(actor.user_id),
    queryFn: ({ signal }) => fetchModelOverview(signal),
    retry: false,
    // Follow a running qualification without manual refresh.
    refetchInterval: (query) => (query.state.data?.running ? 3000 : false),
  });
  const auditQuery = useQuery({
    queryKey: modelManagementQueryKeys.audit(actor.user_id),
    queryFn: ({ signal }) => fetchModelAudit(signal),
    retry: false,
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<{ kind: "activate" | "rollback"; profileId: string; name: string } | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
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
            <div><dt>Name</dt><dd>{overview.active.display_name}</dd></div>
            <div><dt>Model</dt><dd>{overview.active.model_id ?? "None (case-data answers only)"}</dd></div>
            <div><dt>Changed</dt><dd>{overview.active.changed_at ? `${formatTimestamp(overview.active.changed_at)} by ${overview.active.changed_by}` : "Never (environment baseline)"}</dd></div>
            <div><dt>Prompt bound</dt><dd>{overview.active.prompt_limit ? `${overview.active.prompt_limit.toLocaleString()} (verified capacity)` : "Not applied (baseline)"}</dd></div>
            <div><dt>Revision</dt><dd>{overview.revision}</dd></div>
          </dl>
          {overview.configured && (
            <button type="button" className="btn btn-secondary" disabled={!overview.last_good || busy}
              onClick={() => overview.last_good && setConfirming({ kind: "rollback", profileId: overview.last_good.profile_id, name: overview.last_good.display_name })}>
              {overview.last_good ? `Roll back to ${overview.last_good.display_name}` : "No earlier model to roll back to"}
            </button>
          )}
        </section>
      )}

      {confirming && overview && (
        <section className="card" role="dialog" aria-labelledby="confirm-heading">
          <h2 id="confirm-heading">{confirming.kind === "rollback" ? "Roll back" : "Activate"} {confirming.name}?</h2>
          <p>This changes the AI model for every user at once. Answers already being written finish with the current model.</p>
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
                      <td><strong>{item.display_name}</strong>{item.active && <> <span className="tag tag-accent">Active</span></>}<br /><small>{item.model_id ?? "—"}{item.model_version ? ` · ${item.model_version}` : ""}</small></td>
                      <td>{readable(item.deployment)}</td>
                      <td>{item.endpoint ?? "Not shown"}</td>
                      <td><small>Context {item.context_window_tokens ? `${item.context_window_tokens.toLocaleString()} (declared)` : "—"} · answer {value(item.max_answer_tokens)} · temp {value(item.temperature)}</small></td>
                      <td><span className={`tag ${item.status === "selectable" ? "tag-accent" : "tag-warn"}`}>{STATUS_LABEL[item.status]}</span>{item.reason && <><br /><small>{readable(item.reason)}</small></>}</td>
                      <td>{item.connection_test ? <>{readable(item.connection_test.outcome)}{item.connection_test.code && <><br /><small>{readable(item.connection_test.code)}</small></>}</> : "Not tested"}</td>
                      <td>{qualification ? <button type="button" className="btn btn-secondary" onClick={() => setSelected(item.profile_id)}>{readable(qualification.status)}{!qualification.current ? " (out of date)" : ""}</button> : "Not run"}</td>
                      <td>
                        <button type="button" className="btn btn-secondary" disabled={!usable || busy} onClick={() => action.mutate(() => testModelConnection(item.profile_id))}>Test connection</button>{" "}
                        <button type="button" className="btn btn-secondary" disabled={!usable || busy || !item.endpoint} onClick={() => { setSelected(item.profile_id); action.mutate(() => startModelQualification(item.profile_id)); }}>Run qualification</button>{" "}
                        <button type="button" className="btn btn-primary" disabled={!usable || busy || item.active || item.activation_blockers.length > 0}
                          title={item.activation_blockers.map(readable).join(" ")}
                          onClick={() => setConfirming({ kind: "activate", profileId: item.profile_id, name: item.display_name })}>Activate</button>
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
          <h2 id="qualification-heading">Qualification: {detail.display_name}</h2>
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
