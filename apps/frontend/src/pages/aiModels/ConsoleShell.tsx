import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Link } from "react-router";

import "./aiModelConsole.css";

// D-100 Phase 1: the AI Model Console layout. The browser location names the section
// (`?section=`) on the existing capability-checked AI Models route; it carries no data, and
// changing section never sends a request or starts an action.

// D-118: "Set up AI" (the guided setup) is the landing section; the earlier sections are kept,
// unchanged, under Administration.
export type ConsoleSection = "setup" | "overview" | "providers" | "spending" | "privacy" | "qualifications" | "audit";

export const CONSOLE_SECTIONS: ReadonlyArray<{ id: ConsoleSection; label: string }> = [
  { id: "setup", label: "Set up AI" },
  { id: "overview", label: "Models & Overview" },
  { id: "providers", label: "Providers" },
  { id: "spending", label: "Spending & Limits" },
  { id: "privacy", label: "Data Access & Privacy" },
  { id: "qualifications", label: "Qualifications & Recovery" },
  { id: "audit", label: "Audit History" },
];

/** An unknown or missing value shows the guided setup, so a bad link never hides the page. */
export function consoleSection(value: string | null): ConsoleSection {
  return CONSOLE_SECTIONS.find((item) => item.id === value)?.id ?? "setup";
}

export interface ConsoleBadge { text: string; label: string; tone: "warn" | "info" | "neutral" }

export const sectionSearch = (section: ConsoleSection) => (section === "setup" ? "" : `?section=${section}`);

const ICON_PATHS: Record<ConsoleSection, ReactNode> = {
  setup: <><circle cx="12" cy="12" r="8" /><path d="M8.5 12.5l2.5 2.5 4.5-5" /></>,
  overview: <><rect x="4" y="4" width="7" height="7" rx="1.5" /><rect x="13" y="4" width="7" height="7" rx="1.5" /><rect x="4" y="13" width="7" height="7" rx="1.5" /><rect x="13" y="13" width="7" height="7" rx="1.5" /></>,
  providers: <><rect x="4" y="4" width="16" height="6" rx="1.5" /><rect x="4" y="14" width="16" height="6" rx="1.5" /><path d="M8 7h.01M8 17h.01" /></>,
  spending: <><path d="M4 16a8 8 0 0 1 16 0" /><path d="M12 16l4-5" /></>,
  privacy: <><rect x="5" y="11" width="14" height="9" rx="1.5" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></>,
  qualifications: <><path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" /><path d="M9 12l2 2 4-4" /></>,
  audit: <><path d="M4 6h10M4 12h7M4 18h6" /><circle cx="17" cy="15" r="4" /><path d="M17 13.5V15l1 1" /></>,
};

function SectionIcon({ section }: { section: ConsoleSection }) {
  return (
    <svg className="console-nav__icon" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICON_PATHS[section]}
    </svg>
  );
}

export function ConsoleShell({ section, badges, children }: {
  section: ConsoleSection;
  /** Short, server-derived counts or states shown beside a section name; `label` is what a
   * screen reader hears instead of the bare text. */
  badges: Partial<Record<ConsoleSection, ConsoleBadge>>;
  children: ReactNode;
}) {
  // The section list folds behind one button on narrow screens.
  const [open, setOpen] = useState(false);
  const listId = useId();
  const current = CONSOLE_SECTIONS.find((item) => item.id === section)!;
  return (
    <div className="console-layout">
      <aside className={open ? "console-nav is-open" : "console-nav"} aria-label="AI Model Console sections">
        <div className="console-nav__title">
          <p className="card-kicker">HR administration</p>
          <p className="console-nav__name">AI Model Console</p>
        </div>
        <button type="button" className="console-nav__toggle" aria-expanded={open} aria-controls={listId}
          onClick={() => setOpen((value) => !value)}>
          <SectionIcon section={section} />
          <span className="console-nav__toggle-label"><span className="sr-only">Section: </span>{current.label}</span>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={open ? "M6 15l6-6 6 6" : "M6 9l6 6 6-6"} /></svg>
        </button>
        <ul id={listId} className="console-nav__list">
          {CONSOLE_SECTIONS.map((item) => {
            const badge = badges[item.id];
            return (
              <li key={item.id}>
                {item.id === "overview" && <p className="console-nav__group">Administration</p>}
                <Link className="console-nav__link" to={{ search: sectionSearch(item.id) }}
                  aria-current={item.id === section ? "page" : undefined} onClick={() => setOpen(false)}>
                  <SectionIcon section={item.id} />
                  <span className="console-nav__label">{item.label}</span>
                  {badge && (
                    <span className={`console-chip console-chip--${badge.tone} console-nav__badge`}>
                      <span aria-hidden="true">{badge.text}</span><span className="sr-only">, {badge.label}</span>
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
        <p className="console-nav__permission">
          <span className="console-label">Your permission</span>
          Model configuration (<code>MODEL_CONFIG_MANAGE</code>). The server checks every action; this console only shows its answer.
        </p>
      </aside>
      <div className="console-main">{children}</div>
    </div>
  );
}

const FOCUSABLE = "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";

/** D-100 (D3): everything outside the open dialog is made inert and the page stops scrolling,
 * so neither a screen reader nor a pointer reaches the background. Returns the undo; only the
 * elements this call made inert are released. */
function isolate(element: HTMLElement): () => void {
  const made: HTMLElement[] = [];
  for (let node: HTMLElement | null = element; node && node !== document.body; node = node.parentElement) {
    for (const sibling of node.parentElement?.children ?? []) {
      if (sibling !== node && sibling instanceof HTMLElement && !sibling.hasAttribute("inert")) {
        sibling.setAttribute("inert", "");
        made.push(sibling);
      }
    }
  }
  const overflow = document.body.style.overflow;
  document.body.style.overflow = "hidden";
  return () => {
    for (const sibling of made) sibling.removeAttribute("inert");
    document.body.style.overflow = overflow;
  };
}

/** Where focus goes when a dialog closes: the control that opened it, or, when that control
 * is gone or now disabled (an action started), the first fallback element that exists. */
function restoreFocus(previous: HTMLElement | null, fallbackIds: readonly string[]): void {
  const usable = (element: HTMLElement | null) => element?.isConnected && !element.matches(":disabled");
  const target = usable(previous)
    ? previous
    : fallbackIds.map((id) => document.getElementById(id)).find((element) => usable(element)) ?? null;
  target?.focus();
}

/** A modal confirmation (a bottom sheet on narrow screens). Escape or the backdrop cancels. */
export function ConsoleDialog({ labelledBy, testId, onClose, focusFallbackIds = [], children }: {
  labelledBy: string;
  testId?: string;
  onClose: () => void;
  /** Focusable elements (tabIndex -1 headings) to land on when the opener is unusable. */
  focusFallbackIds?: readonly string[];
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDivElement>(null);
  const fallbacks = useRef(focusFallbackIds);
  fallbacks.current = focusFallbackIds;
  // The opener is read once; a pending restore is cancelled if the effect runs again
  // (React StrictMode mounts effects twice in development).
  const opener = useRef<HTMLElement | null | undefined>(undefined);
  const restoreTimer = useRef<number | null>(null);
  useEffect(() => {
    if (restoreTimer.current !== null) window.clearTimeout(restoreTimer.current);
    restoreTimer.current = null;
    if (opener.current === undefined) {
      opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    }
    const node = dialog.current;
    const release = node?.parentElement ? isolate(node.parentElement) : () => undefined;
    node?.focus();
    // Restore after the re-render that closing caused (a confirmed action disables its opener).
    return () => {
      release();
      restoreTimer.current = window.setTimeout(() => {
        restoreTimer.current = null;
        // D-100 (D5): only when focus was left behind by this dialog, never out of a newer one.
        const active = document.activeElement;
        if (active && active !== document.body && active.isConnected && !node?.contains(active)) return;
        restoreFocus(opener.current ?? null, fallbacks.current);
      }, 0);
    };
  }, []);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (event.key === "Escape") {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab" || !dialog.current) return;
    const items = [...dialog.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="console-dialog-backdrop" onMouseDown={(event) => {
      if (event.target !== event.currentTarget) return;
      event.preventDefault(); // keep the browser from moving focus to the page body
      onClose();
    }}>
      <div ref={dialog} className="console-dialog" role="dialog" aria-modal="true" aria-labelledby={labelledBy}
        data-testid={testId} tabIndex={-1} onKeyDown={onKeyDown}>
        {children}
      </div>
    </div>
  );
}
