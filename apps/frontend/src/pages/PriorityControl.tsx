import { useEffect, useState } from "react";

import { ApiError, updateCasePriority } from "../api";
import type { PriorityFilter, PrioritySort } from "../api";
import { priorityTierControlValue, priorityTierLabel } from "../priority";

/** A labelled filter select. Pass `id` when a visible `<label htmlFor>` names it. */
export function PriorityFilterSelect({ value, onChange, id, allLabel = "Priority: All" }: {
  value: PriorityFilter;
  onChange: (value: PriorityFilter) => void;
  id?: string;
  allLabel?: string;
}) {
  return (
    <select
      className="input"
      id={id}
      aria-label={id ? undefined : "Priority filter"}
      value={value}
      onChange={(event) => onChange(event.target.value as PriorityFilter)}
    >
      <option value="all">{allLabel}</option>
      <option value="prioritised">Prioritised only</option>
      <option value="unset">Unprioritised only</option>
    </select>
  );
}

export function PrioritySortSelect({ value, onChange, id }: {
  value: PrioritySort;
  onChange: (value: PrioritySort) => void;
  id?: string;
}) {
  return (
    <select
      className="input"
      id={id}
      aria-label={id ? undefined : "Priority sort"}
      value={value}
      onChange={(event) => onChange(event.target.value as PrioritySort)}
    >
      <option value="highest_first">Highest priority first</option>
      <option value="lowest_first">Lowest priority first</option>
    </select>
  );
}

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
      <PriorityFilterSelect value={filter} onChange={onFilterChange} />
      <PrioritySortSelect value={sort} onChange={onSortChange} />
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
  saveOnChange = false,
  label = "Case priority",
}: {
  caseId?: string;
  priority: number | null;
  onUpdated?: () => void | Promise<void>;
  disabled?: boolean;
  onSave?: (priority: number | null) => Promise<void>;
  /** Save as soon as a tier is chosen (no Set button); a failure restores the saved tier. */
  saveOnChange?: boolean;
  label?: string;
}) {
  const [selected, setSelected] = useState(priorityTierControlValue(priority));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSelected(priorityTierControlValue(priority));
  }, [priority]);

  async function save(value: "" | "1" | "5" | "10" = selected) {
    setBusy(true);
    setError(null);
    try {
      const nextPriority = value === "" ? null : Number(value);
      if (onSave) await onSave(nextPriority);
      else if (caseId && onUpdated) await updatePriorityAndRefresh(caseId, nextPriority, onUpdated);
      else throw new Error("Priority control is not configured.");
    } catch (requestError) {
      if (saveOnChange) setSelected(priorityTierControlValue(priority));
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
        <span className="sr-only">{label}</span>
        <select
          className="input priority-select"
          value={selected}
          disabled={busy || disabled}
          aria-busy={busy || undefined}
          onChange={(event) => {
            const value = event.target.value as "" | "1" | "5" | "10";
            setSelected(value);
            if (saveOnChange) void save(value);
          }}
        >
          <option value="">Unset</option>
          <option value="1">Low</option>
          <option value="5">Medium</option>
          <option value="10">High</option>
        </select>
      </label>
      {!saveOnChange && (
        <button className="btn btn-secondary" type="button" disabled={busy || disabled} onClick={() => void save()}>
          {busy ? "Saving…" : "Set"}
        </button>
      )}
      {saveOnChange && busy && <span className="cell-note" role="status">Saving…</span>}
      {error && <span className="cell-note cell-note--attention">{error}</span>}
    </div>
  );
}
