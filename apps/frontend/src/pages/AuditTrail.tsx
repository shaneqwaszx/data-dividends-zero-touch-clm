import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { caseActivityExportUrl, type CaseActivityFilters } from "../api";
import { activityQueryOptions } from "../caseQueries";
import { paths } from "../navigation";
import type {
  AuthenticatedProfile,
  AutomationStage,
  CaseActivityAction,
  EventOutcome,
} from "../types";
import DirectorTeamFilter from "./DirectorTeamFilter";
import { PriorityBadge } from "./PriorityControl";

const ACTIONS: CaseActivityAction[] = [
  "CREATED",
  "DOCUMENT",
  "RECONCILIATION",
  "OWNERSHIP",
  "INTELLIGENCE",
  "TARGET",
  "COMPLETED",
];
const STAGES: AutomationStage[] = [
  "REGISTRY",
  "DOCUMENT",
  "OWNERSHIP",
  "READINESS",
  "MOCK_GOLDTIER",
  "COMPLETE",
];
const OUTCOMES: EventOutcome[] = ["SUCCEEDED", "PARTIAL", "REVIEW_REQUIRED", "FAILED"];
const UTC_TIMESTAMP_PATTERN = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d{1,6})?(?:Z|\+00:00)$/;

export function formatActivityTimestampUtc(value: string): string {
  const match = UTC_TIMESTAMP_PATTERN.exec(value);
  if (!match) return value;
  return `${match[1]}${match[2] ?? ""}Z`;
}

function utcInput(value: string): string | undefined {
  if (!value) return undefined;
  return `${value}${value.length === 16 ? ":00" : ""}Z`;
}

export default function AuditTrail({
  actor,
  caseId,
}: {
  actor: AuthenticatedProfile;
  caseId?: string | null;
}) {
  const [action, setAction] = useState<CaseActivityAction | "">("");
  const [stage, setStage] = useState<AutomationStage | "">("");
  const [outcome, setOutcome] = useState<EventOutcome | "">("");
  const [fromUtc, setFromUtc] = useState("");
  const [toUtc, setToUtc] = useState("");
  const [teamFilter, setTeamFilter] = useState("all");
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [refreshFromFirst, setRefreshFromFirst] = useState(false);
  const [queryEnabled, setQueryEnabled] = useState(false);

  useEffect(() => {
    setQueryEnabled(true);
  }, []);

  useEffect(() => {
    setOffset(0);
    setExpanded(null);
  }, [caseId]);

  const filters = useMemo<CaseActivityFilters>(() => ({
    caseId: caseId ?? undefined,
    teamFilter,
    action: action || undefined,
    stage: stage || undefined,
    outcome: outcome || undefined,
    from: utcInput(fromUtc),
    to: utcInput(toUtc),
    limit,
    offset,
  }), [action, caseId, fromUtc, limit, offset, outcome, stage, teamFilter, toUtc]);
  const query = useQuery({
    ...activityQueryOptions(actor.user_id, filters),
    enabled: queryEnabled,
  });
  useEffect(() => {
    if (refreshFromFirst && offset === 0) {
      setRefreshFromFirst(false);
      void query.refetch();
    }
  }, [offset, query, refreshFromFirst]);
  const page = query.data;
  const resetPage = () => {
    setOffset(0);
    setExpanded(null);
  };
  const nextOffset = offset + limit;
  const offsetCapReached = Boolean(page?.has_more && nextOffset > 10_000);

  return (
    <div className="ds-root ds-page activity-page">
      <div className="ds-page-header">
        <div>
          <p className="section-label">Retained automation timeline</p>
          <h1>Case activity</h1>
          <p className="text-muted">
            {page ? `${page.items.length} events returned on this page` : "Authorized retained events"}
            {caseId ? ` for case ${caseId}` : " across accessible cases"}.
          </p>
        </div>
        <div className="activity-header-actions">
          {caseId && <Link className="btn btn-ghost" to={paths.audit}>Clear case filter</Link>}
          <button className="btn btn-secondary" type="button" onClick={() => {
            if (offset === 0) void query.refetch();
            else {
              setRefreshFromFirst(true);
              setOffset(0);
            }
          }}>Refresh from page one</button>
          <a
            className="btn btn-secondary"
            href={caseActivityExportUrl(filters)}
            download="case-activity.csv"
          >Export current page CSV</a>
        </div>
      </div>

      {!caseId && <DirectorTeamFilter actor={actor} value={teamFilter} onChange={(value) => {
        setTeamFilter(value);
        resetPage();
      }} />}

      <div className="ds-toolbar" aria-label="Activity action filter">
        <button type="button" className={action === "" ? "tag tag-accent" : "tag tag-neutral"} onClick={() => {
          setAction("");
          resetPage();
        }}>All</button>
        {ACTIONS.map((item) => (
          <button key={item} type="button" className={action === item ? "tag tag-accent" : "tag tag-neutral"} onClick={() => {
            setAction(item);
            resetPage();
          }}>{item.toLowerCase()}</button>
        ))}
      </div>

      <div className="activity-filters">
        <label>Stage<select value={stage} onChange={(event) => {
          setStage(event.target.value as AutomationStage | "");
          resetPage();
        }}><option value="">All stages</option>{STAGES.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label>Outcome<select value={outcome} onChange={(event) => {
          setOutcome(event.target.value as EventOutcome | "");
          resetPage();
        }}><option value="">All outcomes</option>{OUTCOMES.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label>From (UTC, inclusive)<input type="datetime-local" step="1" value={fromUtc} onChange={(event) => {
          setFromUtc(event.target.value);
          resetPage();
        }} /></label>
        <label>To (UTC, exclusive)<input type="datetime-local" step="1" value={toUtc} onChange={(event) => {
          setToUtc(event.target.value);
          resetPage();
        }} /></label>
        <label>Events per page<select value={limit} onChange={(event) => {
          setLimit(Number(event.target.value));
          resetPage();
        }}>{[25, 50, 100].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      </div>

      <div className="ds-banner activity-boundary-note">
        This view covers currently retained automation timeline events only. Actor attribution is not
        recorded. Priority and client scope are current case metadata, not values captured at event time.
        Pages are a live view: concurrent inserts or deletion can move page boundaries. Case deletion
        removes the available history. Timestamps and date filters use UTC.
      </div>

      {query.isFetching && page && <p className="refreshing-indicator">Refreshing this page…</p>}
      {query.isError && page && <div className="ds-banner ds-banner-warn" role="alert">Refresh failed; the last result for these exact filters remains visible.</div>}
      {query.isPending && <p className="text-muted">Loading retained activity…</p>}
      {query.isError && !page && <div className="ds-banner ds-banner-warn" role="alert">{query.error instanceof Error ? query.error.message : "Case activity is unavailable."}</div>}
      {page && page.items.length === 0 && <p className="text-muted">No retained automation events match this page and filter.</p>}
      {page && page.items.length > 0 && (
        <div className="table-card table-scroll activity-table-scroll" tabIndex={0} aria-label="Case activity events">
          <table className="table activity-table">
            <thead><tr><th>Timestamp (UTC)</th><th>Case</th><th>Event</th><th>Stage</th><th>Outcome</th><th>Current priority</th><th>Current client scope</th><th>Detail</th></tr></thead>
            <tbody>{page.items.map((item) => {
              const key = `${item.case_id}-${item.sequence}`;
              const isExpanded = expanded === key;
              return [
                <tr key={key}>
                  <td><time dateTime={item.timestamp}>{formatActivityTimestampUtc(item.timestamp)}</time></td>
                  <td><Link to={paths.caseDetail(item.case_id)}>{item.case_id}</Link></td>
                  <td><span className="tag tag-accent-2">{item.event_type.toLowerCase()}</span></td>
                  <td>{item.stage}</td><td>{item.outcome}</td>
                  <td><PriorityBadge priority={item.current_priority} /></td>
                  <td>{item.current_client_scope_label ?? "Legacy unassigned"}</td>
                  <td><button className="btn btn-ghost" type="button" aria-expanded={isExpanded} onClick={() => setExpanded(isExpanded ? null : key)}>{isExpanded ? "Hide" : "Inspect"}</button></td>
                </tr>,
                isExpanded && <tr className="activity-detail-row" key={`${key}-detail`}><td colSpan={8}><strong>{item.code ?? "No event code"}</strong><p>{item.message}</p><small>Source-local sequence {item.sequence}; timestamps do not prove cross-case causal order.</small></td></tr>,
              ];
            })}</tbody>
          </table>
        </div>
      )}

      {page && <nav className="activity-pagination" aria-label="Activity pages">
        <button className="btn btn-secondary" type="button" disabled={offset === 0} onClick={() => {
          setOffset(Math.max(0, offset - limit));
          setExpanded(null);
        }}>Previous</button>
        <span>Offset {page.offset}; {page.items.length} returned</span>
        <button className="btn btn-secondary" type="button" disabled={!page.has_more || offsetCapReached} onClick={() => {
          setOffset(nextOffset);
          setExpanded(null);
        }}>Next</button>
      </nav>}
      {offsetCapReached && <p className="control-help" role="status">More retained events may exist beyond the paging safety bound. Narrow the filters and refresh from page one.</p>}
    </div>
  );
}
