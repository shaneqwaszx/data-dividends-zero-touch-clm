import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { flushSync } from "react-dom";

export function revealStage(target: Element): void {
  let ancestor = target.parentElement;
  while (ancestor) {
    if (ancestor.classList.contains("stage-disclosure")) {
      ancestor.dispatchEvent(new Event("reveal-stage"));
    }
    if (ancestor instanceof HTMLDetailsElement) ancestor.open = true;
    ancestor = ancestor.parentElement;
  }
}

function LegacyStageDisclosure({ title, active = false, children, final = false, summary }: {
  title: string; active?: boolean; children: ReactNode; final?: boolean; summary?: string;
}) {
  const [open, setOpen] = useState(active);
  const id = useId();
  const ref = useRef<HTMLElement>(null);
  // Settle backend-driven stage changes before view focus/scroll handoff.
  useLayoutEffect(() => setOpen(active), [active]);
  useEffect(() => {
    const element = ref.current;
    const reveal = () => flushSync(() => setOpen(true));
    element?.addEventListener("reveal-stage", reveal);
    const beforePrint = () => { if (final) setOpen(true); };
    window.addEventListener("beforeprint", beforePrint);
    return () => {
      element?.removeEventListener("reveal-stage", reveal);
      window.removeEventListener("beforeprint", beforePrint);
    };
  }, [final]);
  return <section ref={ref} className={`stage-disclosure${final ? " stage-disclosure--final" : ""}`} aria-labelledby={`${id}-title`}>
    <h2 id={`${id}-title`}>
      <button type="button" aria-expanded={open} aria-controls={`${id}-content`} aria-describedby={summary ? `${id}-summary` : undefined} onClick={() => setOpen(!open)}>
        <span>{title}</span><span aria-hidden="true">{open ? "−" : "+"}</span>
      </button>
    </h2>
    {summary && <p id={`${id}-summary`} className="stage-disclosure__summary">{summary}</p>}
    <div id={`${id}-content`} hidden={!open}>{children}</div>
  </section>;
}

/** The caller supplies its existing actor/session/case presentation identity. */
type PersistentStageProps = Omit<Parameters<typeof LegacyStageDisclosure>[0], "children"> & {
  scopeKey: string;
  main: ReactNode;
  moreDetails?: ReactNode;
  technicalDetails?: ReactNode;
  children?: never;
};

export default function StageDisclosure(props: Parameters<typeof LegacyStageDisclosure>[0] | PersistentStageProps) {
  return "scopeKey" in props ? <PersistentStageDisclosure {...props} /> : <LegacyStageDisclosure {...props} />;
}

function PersistentStageDisclosure({ title, main, moreDetails, technicalDetails, scopeKey, final = false, summary }: PersistentStageProps) {
  const id = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  const more = useRef<HTMLDetailsElement>(null);
  const technical = useRef<HTMLDetailsElement>(null);
  const previousScope = useRef(scopeKey);
  const sectionHasFocus = useRef(false);
  const printedState = useRef<boolean[] | null>(null);

  useLayoutEffect(() => {
    if (previousScope.current === scopeKey) return;
    previousScope.current = scopeKey;
    if (sectionHasFocus.current) heading.current?.focus();
    for (const element of [more.current, technical.current]) if (element) element.open = false;
    sectionHasFocus.current = false;
    printedState.current = null;
  }, [scopeKey]);

  useEffect(() => {
    const beforePrint = () => {
      if (!final || printedState.current) return;
      printedState.current = [more.current?.open ?? false, technical.current?.open ?? false];
      for (const element of [more.current, technical.current]) if (element) element.open = true;
    };
    const afterPrint = () => {
      const retained = printedState.current;
      if (!retained) return;
      [more.current, technical.current].forEach((element, index) => { if (element) element.open = retained[index]; });
      printedState.current = null;
    };
    window.addEventListener("beforeprint", beforePrint);
    window.addEventListener("afterprint", afterPrint);
    return () => {
      afterPrint();
      window.removeEventListener("beforeprint", beforePrint);
      window.removeEventListener("afterprint", afterPrint);
    };
  }, [final]);

  const restoreFocus = (element: HTMLDetailsElement) => {
    if (!element.open && element.contains(document.activeElement)) element.querySelector("summary")?.focus();
  };
  return <section className={`stage-disclosure${final ? " stage-disclosure--final" : ""}`} aria-labelledby={`${id}-title`}
    onFocusCapture={() => { sectionHasFocus.current = true; }}
    onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) sectionHasFocus.current = false; }}>
    <h2 ref={heading} id={`${id}-title`} tabIndex={-1}>{title}</h2>
    {summary && <p className="stage-disclosure__summary">{summary}</p>}
    <div key={scopeKey}>{main}</div>
    {moreDetails != null && <details ref={more} className="evidence-details" onToggle={(event) => restoreFocus(event.currentTarget)}>
      <summary>More details — {title}</summary><div key={scopeKey}>{moreDetails}</div>
    </details>}
    {technicalDetails != null && <details ref={technical} className="evidence-details" onToggle={(event) => restoreFocus(event.currentTarget)}>
      <summary>Technical details — {title}</summary><div key={scopeKey}>{technicalDetails}</div>
    </details>}
  </section>;
}
