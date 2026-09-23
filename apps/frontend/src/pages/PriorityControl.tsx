import { useEffect, useState } from "react";

import { ApiError, updateCasePriority } from "../api";
import type { PriorityFilter, PrioritySort } from "../api";
import { priorityTierControlValue, priorityTierLabel } from "../priority";

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
      {priorityTierLabel(priority)}
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
  disabled = false,
  onSave,
}: {
  caseId?: string;
  priority: number | null;
  onUpdated?: () => void | Promise<void>;
  disabled?: boolean;
  onSave?: (priority: number | null) => Promise<void>;
}) {
  const [selected, setSelected] = useState(priorityTierControlValue(priority));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelected(priorityTierControlValue(priority));
  }, [priority]);

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const nextPriority = selected === "" ? null : Number(selected);
      if (onSave) await onSave(nextPriority);
      else if (caseId && onUpdated) await updatePriorityAndRefresh(caseId, nextPriority, onUpdated);
      else throw new Error("Priority control is not configured.");
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
          disabled={busy || disabled}
          onChange={(event) => setSelected(event.target.value as "" | "1" | "5" | "10")}
        >
          <option value="">Unset</option>
          <option value="1">Low</option>
          <option value="5">Medium</option>
          <option value="10">High</option>
        </select>
      </label>
      <button className="btn btn-secondary" type="button" disabled={busy || disabled} onClick={() => void save()}>
        {busy ? "Saving…" : "Set"}
      </button>
      {error && <span className="cell-note cell-note--attention">{error}</span>}
    </div>
  );
}
