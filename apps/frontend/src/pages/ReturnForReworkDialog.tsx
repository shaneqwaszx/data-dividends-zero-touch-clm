import { useState } from "react";

import type { ZeroTouchCaseSummary, ZeroTouchException } from "../types";

const REASONS = [
  "Document insufficient or out of date",
  "Registry and document values cannot be reconciled",
  "Additional evidence required",
];

export default function ReturnForReworkDialog({
  summary,
  exception,
  onClose,
  onReturned,
}: {
  summary: ZeroTouchCaseSummary;
  exception: ZeroTouchException;
  onClose: () => void;
  onReturned: (summary: ZeroTouchCaseSummary) => void;
}) {
  const [reason, setReason] = useState(REASONS[0]);
  const [comment, setComment] = useState("");
  const [flaggedFields, setFlaggedFields] = useState<string[]>(
    exception.evidence.map((item) => item.field_key).filter((key): key is string => key !== null),
  );
  void summary;
  void onReturned;

  function toggleField(field: string) {
    setFlaggedFields((current) =>
      current.includes(field) ? current.filter((item) => item !== field) : [...current, field],
    );
  }

  return (
    <div className="ds-root dialog-backdrop" role="dialog" aria-modal="true" aria-labelledby="rework-title">
      <div className="dialog">
        <p className="card-kicker">{exception.stage.replaceAll("_", " ")} · stage exception</p>
        <h2 id="rework-title" className="dialog-title">Return for rework</h2>
        <div className="field">
          <label htmlFor="rework-reason">Reason</label>
          <select
            id="rework-reason"
            className="input"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            disabled
          >
            {REASONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="rework-comment">Comment — required</label>
          <textarea
            id="rework-comment"
            className="input"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            maxLength={500}
            required
            disabled
          />
        </div>
        {exception.evidence.length > 0 && (
          <div className="field">
            <label>Flag for correction</label>
            <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
              {exception.evidence
                .map((item) => item.field_key)
                .filter((key): key is string => key !== null)
                .map((field) => (
                  <button
                    key={field}
                    type="button"
                    className={flaggedFields.includes(field) ? "tag tag-accent" : "tag tag-neutral"}
                    onClick={() => toggleField(field)}
                    disabled
                  >
                    {field.replaceAll("_", " ")} {flaggedFields.includes(field) ? "×" : ""}
                  </button>
                ))}
            </div>
          </div>
        )}
        <div className="ds-banner ds-banner-warn">Return for rework is not available in current POC.</div>
        <div className="dialog-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled
            title="Not available in current POC"
          >
            Return for rework
          </button>
        </div>
      </div>
    </div>
  );
}
