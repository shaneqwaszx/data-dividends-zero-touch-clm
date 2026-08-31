import { useEffect, useRef, useState } from "react";

import {
  ApiError,
  fetchZeroTouchCase,
  resolveZeroTouchException,
  resubmitCase,
} from "../api";
import { startAutomationPolling } from "../automationPolling";
import { formatTimestamp, shouldPollAutomation, STAGE_BANDS } from "../shared";
import type { AutomationStage, ZeroTouchCaseSummary, ZeroTouchException } from "../types";
import AssignReviewerDialog from "./AssignReviewerDialog";
import ReturnForReworkDialog from "./ReturnForReworkDialog";

function bandState(summary: ZeroTouchCaseSummary, stages: AutomationStage[]): "done" | "now" | "" {
  if (stages.every((stage) => summary.completed_stages.includes(stage))) return "done";
  if (stages.includes(summary.current_stage)) return "now";
  return "";
}

export default function CaseDetail({
  caseId,
  onBack,
}: {
  caseId: string;
  onBack: () => void;
}) {
  const [summary, setSummary] = useState<ZeroTouchCaseSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogException, setDialogException] = useState<{
    exception: ZeroTouchException;
    kind: "assign" | "rework";
  } | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const generation = useRef(0);

  useEffect(() => {
    generation.current += 1;
    const current = generation.current;
    setSummary(null);
    setError(null);
    void fetchZeroTouchCase(caseId)
      .then((value) => {
        if (current === generation.current) setSummary(value);
      })
      .catch((requestError) => {
        if (current !== generation.current) return;
        setError(
          requestError instanceof ApiError ? requestError.message : "The case is unavailable.",
        );
      });
  }, [caseId]);

  useEffect(() => {
    if (!summary || !shouldPollAutomation(summary.status)) return;
    const activeGeneration = generation.current;
    return startAutomationPolling({
      caseId,
      generation: activeGeneration,
      currentGeneration: () => generation.current,
      fetchCase: fetchZeroTouchCase,
      onUpdate: setSummary,
      onWarning: () => undefined,
      shouldContinue: shouldPollAutomation,
    });
  }, [caseId, summary?.status, summary?.version]);

  async function handleClearFalsePositive(exception: ZeroTouchException) {
    if (!summary) return;
    setIsBusy(true);
    try {
      setSummary(
        await resolveZeroTouchException(
          summary,
          exception.exception_id,
          "CLEAR_AS_FALSE_POSITIVE",
          exception.evidence_version,
        ),
      );
    } catch (resolveError) {
      setError(resolveError instanceof Error ? resolveError.message : "Resolution failed.");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleResubmit() {
    if (!summary) return;
    setIsBusy(true);
    try {
      setSummary(await resubmitCase(summary));
    } catch (resubmitError) {
      setError(resubmitError instanceof Error ? resubmitError.message : "Resubmit failed.");
    } finally {
      setIsBusy(false);
    }
  }

  if (error) {
    return (
      <div className="ds-root ds-page">
        <button type="button" className="btn btn-ghost" onClick={onBack}>
          ← Back to Cases
        </button>
        <div className="ds-banner ds-banner-warn">{error}</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="ds-root ds-page">
        <p className="text-muted">Loading case…</p>
      </div>
    );
  }

  const entity = summary.case.entity;
  const acquisition = summary.case.registry_acquisition;

  return (
    <div className="ds-root" style={{ display: "flex", alignItems: "stretch" }}>
      <div style={{ width: 260, padding: "22px 20px", background: "#faf9f8", borderRight: "1px solid var(--color-divider)" }}>
        <button type="button" className="btn btn-ghost" onClick={onBack} style={{ paddingLeft: 0 }}>
          ← Back to Cases
        </button>
        <h4 style={{ marginTop: 16 }}>Pipeline</h4>
        <div className="ds-stage-rail">
          {STAGE_BANDS.map((band, index) => {
            const state = bandState(summary, band.stages);
            return (
              <div className="ds-stage" key={band.label}>
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                  <span className={`ds-stage-node ${state}`}>
                    {state === "done" ? "✓" : index + 1}
                  </span>
                  {index < STAGE_BANDS.length - 1 && (
                    <span className={`ds-stage-line ${state === "done" ? "done" : ""}`} />
                  )}
                </div>
                <div style={{ paddingBottom: 14 }}>
                  <div style={{ fontSize: 12.5 }}>{band.label}</div>
                  <div className="text-muted" style={{ fontSize: 11 }}>
                    {state === "done" ? "Cleared" : state === "now" ? "In progress" : "Pending"}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <hr className="hr" />
        <div className="text-muted" style={{ fontSize: 11.5 }}>
          Loop {summary.loop_number}
          {summary.loop_history.length > 0 && ` · ${summary.loop_history.length} prior loop(s)`}
        </div>
      </div>

      <div className="ds-page" style={{ flex: 1 }}>
        <div className="ds-page-header">
          <div>
            <p className="card-kicker">
              {summary.case.requested_uen} · {summary.case.jurisdiction_resolution?.resolved_jurisdiction ?? "—"}
            </p>
            <h1>{entity?.legal_name ?? summary.case.requested_uen}</h1>
          </div>
          <span className="tag tag-accent-2">{summary.status.replaceAll("_", " ")}</span>
        </div>

        {summary.active_exceptions.map((exception) => (
          <div className="ds-banner ds-banner-warn" key={exception.exception_id} style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <h3 style={{ margin: 0 }}>{exception.exception_type.replaceAll("_", " ")}</h3>
              <span className="text-muted" style={{ fontSize: 11 }}>
                {formatTimestamp(exception.created_at)}
              </span>
            </div>
            <p style={{ marginTop: 8, fontSize: 12.5 }}>{exception.explanation}</p>
            {exception.assignee && (
              <p className="text-muted" style={{ fontSize: 11.5 }}>Assigned to {exception.assignee}</p>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
              {exception.available_actions.includes("CLEAR_AS_FALSE_POSITIVE") && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={isBusy}
                  onClick={() => void handleClearFalsePositive(exception)}
                >
                  Clear as false positive
                </button>
              )}
              {exception.available_actions.includes("ASSIGN_REVIEWER") && (
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={isBusy}
                  onClick={() => setDialogException({ exception, kind: "assign" })}
                >
                  Assign reviewer
                </button>
              )}
              {exception.available_actions.includes("RETURN_FOR_REWORK") && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  disabled={isBusy}
                  onClick={() => setDialogException({ exception, kind: "rework" })}
                >
                  Return for rework
                </button>
              )}
            </div>
          </div>
        ))}

        {summary.status === "REWORK_REQUIRED" && (
          <div className="ds-banner" style={{ marginBottom: 16 }}>
            <p style={{ margin: 0, fontSize: 12.5 }}>
              Resubmission restarts the pipeline at stage 1. Stages 1 to 3 re-run automatically.
            </p>
            <button
              type="button"
              className="btn btn-primary"
              style={{ marginTop: 10 }}
              disabled={isBusy}
              onClick={() => void handleResubmit()}
            >
              Resubmit
            </button>
          </div>
        )}

        <div className="ds-two-col">
          <div style={{ flex: 1 }}>
            <h4>Corporate particulars</h4>
            <div>
              <div className="kv-row"><span className="kv-label">Company name</span><span className="kv-value">{entity?.legal_name ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registration ID</span><span className="kv-value">{entity?.registration_number ?? summary.case.requested_uen}</span></div>
              <div className="kv-row"><span className="kv-label">Entity type</span><span className="kv-value">{entity?.party_type ?? "—"}</span></div>
              <div className="kv-row"><span className="kv-label">Registry status</span><span className="kv-value">{entity?.entity_status ?? "—"}</span></div>
            </div>
          </div>
          <div style={{ width: 330 }}>
            <h4>Directors</h4>
            {acquisition && acquisition.officers.length > 0 ? (
              <div className="table-card">
                <table className="table">
                  <tbody>
                    {acquisition.officers.map((officer) => (
                      <tr key={officer.officer_id}>
                        <td>{officer.name}</td>
                        <td>{officer.role}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-muted" style={{ fontSize: 12 }}>Not available.</p>
            )}
          </div>
        </div>
      </div>

      {dialogException?.kind === "assign" && (
        <AssignReviewerDialog
          summary={summary}
          exception={dialogException.exception}
          onClose={() => setDialogException(null)}
          onAssigned={(updated) => {
            setSummary(updated);
            setDialogException(null);
          }}
        />
      )}
      {dialogException?.kind === "rework" && (
        <ReturnForReworkDialog
          summary={summary}
          exception={dialogException.exception}
          onClose={() => setDialogException(null)}
          onReturned={(updated) => {
            setSummary(updated);
            setDialogException(null);
          }}
        />
      )}
    </div>
  );
}
