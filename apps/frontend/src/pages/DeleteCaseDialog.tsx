import { useEffect, useRef, useState } from "react";

const FOCUSABLE = [
  "button:not([disabled])",
  "[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export default function DeleteCaseDialog({
  caseId,
  companyName,
  requestedUen,
  onCancel,
  onConfirm,
}: {
  caseId: string;
  companyName: string;
  requestedUen: string;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const submittedRef = useRef(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    returnFocusRef.current = document.activeElement as HTMLElement | null;
    cancelRef.current?.focus();
    return () => returnFocusRef.current?.focus();
  }, []);

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape" && !pending) {
      event.preventDefault();
      onCancel();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(
      dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [],
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  async function confirmOnce() {
    if (submittedRef.current) return;
    submittedRef.current = true;
    setPending(true);
    setError(null);
    try {
      await onConfirm();
    } catch (requestError) {
      submittedRef.current = false;
      setPending(false);
      setError(requestError instanceof Error ? requestError.message : "The case could not be deleted.");
    }
  }

  return (
    <div className="ds-root dialog-backdrop">
      <div
        ref={dialogRef}
        className="dialog delete-case-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="delete-case-title"
        aria-describedby="delete-case-description"
        onKeyDown={handleKeyDown}
      >
        <h2 id="delete-case-title">Delete case permanently?</h2>
        <p id="delete-case-description">
          This permanently removes {companyName} ({requestedUen}) and all case evidence.
          This action cannot be undone.
        </p>
        <p className="case-identifiers">Case {caseId}</p>
        {error && <div className="ds-banner ds-banner-warn" role="alert">{error}</div>}
        <div className="dialog-actions">
          <button ref={cancelRef} type="button" className="btn btn-secondary" disabled={pending} onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn btn-danger" disabled={pending} onClick={() => void confirmOnce()}>
            {pending ? "Deleting…" : "Delete case"}
          </button>
        </div>
      </div>
    </div>
  );
}
