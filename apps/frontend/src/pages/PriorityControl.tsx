import { useState } from "react";

import { ApiError, updateCasePriority } from "../api";
import type { PriorityFilter, PrioritySort } from "../api";

export function PriorityListControls({
  filter,
  sort,
  onFilterChange,
  onSortChange,
}: {
  filter: PriorityFilter;
  sort: PrioritySort;
  onFilterChange: (value: PriorityFilter) => void;
  onSortChange: (value: PrioritySort) => void;
}) {
  return (
    <>
      <select
        className="input"
        aria-label="Priority filter"
        value={filter}
        onChange={(event) => onFilterChange(event.target.value as PriorityFilter)}
      >
        <option value="all">Priority: All</option>
        <option value="prioritised">Prioritised only</option>
        <option value="unset">Unprioritised only</option>
        {Array.from({ length: 10 }, (_, index) => 10 - index).map((priority) => (
          <option key={priority} value={priority}>Priority {priority}</option>
        ))}
      </select>
      <select
        className="input"
        aria-label="Priority sort"
        value={sort}
        onChange={(event) => onSortChange(event.target.value as PrioritySort)}
      >
        <option value="highest_first">Highest priority first</option>
        <option value="lowest_first">Lowest priority first</option>
      </select>
    </>
  );
}

export function PriorityBadge({ priority }: { priority: number | null }) {
  return (
    <span className={priority === null ? "priority-badge priority-badge--unset" : "priority-badge"}>
      {priority === null ? "Unprioritised" : `P${priority}`}
    </span>
  );
}

export async function updatePriorityAndRefresh(
  caseId: string,
  priority: number | null,
  refreshAuthoritativeProjection: () => void | Promise<void>,
): Promise<void> {
  await updateCasePriority(caseId, priority);
  await refreshAuthoritativeProjection();
}

export default function PriorityControl({
  caseId,
  priority,
  onUpdated,
}: {
  caseId: string;
  priority: number | null;
  onUpdated: () => void | Promise<void>;
}) {
  const [selected, setSelected] = useState(priority === null ? "" : String(priority));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await updatePriorityAndRefresh(
        caseId,
        selected === "" ? null : Number(selected),
        onUpdated,
      );
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "Priority could not be updated.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="priority-control" onClick={(event) => event.stopPropagation()}>
      <label>
        <span className="sr-only">Case priority</span>
        <select
          className="input priority-select"
          value={selected}
          disabled={busy}
          onChange={(event) => setSelected(event.target.value)}
        >
          <option value="">Unset</option>
          {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1].map((value) => (
            <option key={value} value={value}>{value}</option>
          ))}
        </select>
      </label>
      <button className="btn btn-secondary" type="button" disabled={busy} onClick={() => void save()}>
        {busy ? "Saving…" : "Set"}
      </button>
      {error && <span className="cell-note cell-note--attention">{error}</span>}
    </div>
  );
}
