import { useEffect, useId, useRef, useState, type ReactNode } from "react";
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

export default function StageDisclosure({ title, active = false, children, final = false, summary }: {
  title: string; active?: boolean; children: ReactNode; final?: boolean; summary?: string;
}) {
  const [open, setOpen] = useState(active);
  const id = useId();
  const ref = useRef<HTMLElement>(null);
  useEffect(() => setOpen(active), [active]);
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
