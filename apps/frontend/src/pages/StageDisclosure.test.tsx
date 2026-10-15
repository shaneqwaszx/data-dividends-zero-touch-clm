// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it } from "vitest";
import StageDisclosure, { revealStage } from "./StageDisclosure";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

describe("stage disclosure", () => {
  it("uses keyboard-operable buttons with labelled controlled content and follows the current stage", async () => {
    const host = document.createElement("div");
    document.body.append(host);
    const root = createRoot(host);
    const render = (active: boolean) => root.render(<StageDisclosure title="Ownership & UBO" active={active}><p id="evidence">Evidence</p></StageDisclosure>);
    await act(async () => render(false));
    const button = host.querySelector("button")!;
    expect(button.type).toBe("button");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(document.getElementById(button.getAttribute("aria-controls")!)?.hidden).toBe(true);
    await act(async () => button.click());
    expect(button.getAttribute("aria-expanded")).toBe("true");
    await act(async () => render(true));
    expect(button.getAttribute("aria-expanded")).toBe("true");
    await act(async () => render(false));
    expect(button.getAttribute("aria-expanded")).toBe("false");
    await act(async () => revealStage(host.querySelector("#evidence")!));
    expect(button.getAttribute("aria-expanded")).toBe("true");
    await act(async () => root.unmount());
    host.remove();
  });
});


function visible(element: Element): boolean {
  for (let node: Element | null = element; node; node = node.parentElement) {
    if (node instanceof HTMLElement && (node.hidden || getComputedStyle(node).display === "none")) return false;
    if (node instanceof HTMLDetailsElement && !node.open
      && !node.querySelector(":scope > summary")?.contains(element)) return false;
  }
  return true;
}

async function fixture() {
  const host = document.createElement("div"); document.body.append(host);
  const root = createRoot(host);
  const render = async (scopeKey = "actor-a:session-a:case-a", active = false, final = false, revision = "one") => {
    await act(async () => root.render(<StageDisclosure title="Submission readiness" active={active} final={final}
      scopeKey={scopeKey} main={<><p id="main-status">Blocked {revision}</p><button id="required">Required correction</button></>}
      moreDetails={<label>Optional draft<input id="draft" defaultValue="retained" /></label>}
      technicalDetails={<button id="diagnostic">Safe diagnostic</button>} />));
  };
  await render();
  const details = () => [...host.querySelectorAll("details")];
  const toggle = async (index: number, open: boolean) => { await act(async () => {
    const target = details()[index]; target.open = open; target.dispatchEvent(new Event("toggle"));
  }); };
  const dispose = async () => { await act(async () => root.unmount()); host.remove(); };
  return { host, render, details, toggle, dispose };
}

describe("persistent stage Main", () => {
  it("keeps Main visible in all four independent support combinations with stage-qualified native names", async () => {
    const f = await fixture();
    try {
      expect(f.host.querySelector("h2 button")).toBeNull();
      expect(f.details().map(d => d.open)).toEqual([false, false]);
      expect(f.details().map(d => d.querySelector("summary")?.textContent)).toEqual([
        "More details — Submission readiness", "Technical details — Submission readiness",
      ]);
      for (const [more, technical] of [[false, false], [true, false], [true, true], [false, true]]) {
        await f.toggle(0, more); await f.toggle(1, technical);
        expect(visible(f.host.querySelector("#required")!)).toBe(true);
        expect(visible(f.host.querySelector("#draft")!)).toBe(more);
        expect(visible(f.host.querySelector("#diagnostic")!)).toBe(technical);
      }
    } finally { await f.dispose(); }
  });

  it("preserves mounted drafts and support state through toggles, active changes and same-scope evidence refresh", async () => {
    const f = await fixture();
    try {
      await f.toggle(0, true);
      const draft = f.host.querySelector<HTMLInputElement>("#draft")!; draft.value = "unsaved local draft";
      await f.toggle(0, false); await f.toggle(0, true);
      await f.render(undefined, true, false, "two");
      expect(f.details().map(d => d.open)).toEqual([true, false]);
      expect(f.host.querySelector("#draft")).toBe(draft);
      expect(draft.value).toBe("unsaved local draft");
      expect(visible(f.host.querySelector("#main-status")!)).toBe(true);
    } finally { await f.dispose(); }
  });

  it("closes support and returns focused optional content to the visible heading for actor, session and case changes", async () => {
    const f = await fixture();
    try {
      for (const scope of ["actor-b:session-a:case-a", "actor-b:session-b:case-a", "actor-b:session-b:case-b", "actor-b:session-b:case-b:analysis-b"]) {
        await f.toggle(0, true); await f.toggle(1, true);
        f.host.querySelector<HTMLInputElement>("#draft")!.value = "other scope draft";
        f.host.querySelector<HTMLElement>("#diagnostic")!.focus();
        await f.render(scope);
        expect(f.host.querySelector<HTMLInputElement>("#draft")!.value).toBe("retained");
        expect(f.details().map(d => d.open)).toEqual([false, false]);
        expect(document.activeElement).toBe(f.host.querySelector("h2"));
        expect(visible(document.activeElement!)).toBe(true);
      }
    } finally { await f.dispose(); }
  });

  it("returns focus on support collapse and reveals only the explicit diagnostic destination", async () => {
    const f = await fixture();
    try {
      await f.toggle(1, true); f.host.querySelector<HTMLElement>("#diagnostic")!.focus();
      await f.toggle(1, false);
      expect(document.activeElement).toBe(f.details()[1].querySelector("summary"));
      await act(async () => revealStage(f.host.querySelector("#draft")!));
      expect(f.details().map(d => d.open)).toEqual([true, false]);
    } finally { await f.dispose(); }
  });

  it("opens Final support temporarily for print and restores the exact pre-print combination", async () => {
    const f = await fixture();
    try {
      await f.render(undefined, false, true); await f.toggle(1, true);
      await act(async () => window.dispatchEvent(new Event("beforeprint")));
      expect(f.details().map(d => d.open)).toEqual([true, true]);
      await act(async () => window.dispatchEvent(new Event("afterprint")));
      expect(f.details().map(d => d.open)).toEqual([false, true]);
      expect(visible(f.host.querySelector("#required")!)).toBe(true);
    } finally { await f.dispose(); }
  });
});


describe("legacy and empty support compatibility", () => {
  it("keeps legacy Final print opening and native reveal behavior without forcing optional placeholders", async () => {
    const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
    try {
      await act(async () => root.render(<StageDisclosure title="Final review & send" final><p>Retained legacy final</p></StageDisclosure>));
      expect(host.querySelector("button")!.getAttribute("aria-expanded")).toBe("false");
      await act(async () => window.dispatchEvent(new Event("beforeprint")));
      expect(host.querySelector("button")!.getAttribute("aria-expanded")).toBe("true");
      await act(async () => window.dispatchEvent(new Event("afterprint")));
      expect(host.querySelector("button")!.getAttribute("aria-expanded")).toBe("true");
      await act(async () => root.render(<StageDisclosure title="Registry verification" scopeKey="safe-scope" active main={<button>Required correction</button>} />));
      expect(host.querySelectorAll("details")).toHaveLength(0);
      expect(visible(host.querySelector("button")!)).toBe(true);
    } finally { await act(async () => root.unmount()); host.remove(); }
  });
});


describe("scope and external focus boundaries", () => {
  it("does not steal focus from another workspace during scope reset or same-scope refresh", async () => {
    const f = await fixture();
    const outside = document.createElement("button"); outside.textContent = "Other workspace action"; document.body.append(outside);
    try {
      await f.toggle(0, true); await f.toggle(1, true);
      outside.focus();
      await f.render("actor-b:session-b:case-b:analysis-b");
      expect(f.details().map(d => d.open)).toEqual([false, false]);
      expect(document.activeElement).toBe(outside);
      await f.render("actor-b:session-b:case-b:analysis-b", true, false, "current");
      expect(document.activeElement).toBe(outside);
      expect(f.host.querySelector("#main-status")!.textContent).toBe("Blocked current");
      expect(f.details().map(d => d.open)).toEqual([false, false]);
    } finally { await f.dispose(); outside.remove(); }
  });

  it("does not restore an old scope's disclosure state after printing crosses an identity change", async () => {
    const f = await fixture();
    try {
      await f.render(undefined, false, true); await f.toggle(0, true);
      await act(async () => window.dispatchEvent(new Event("beforeprint")));
      expect(f.details().map(d => d.open)).toEqual([true, true]);
      await f.render("actor-b:session-b:case-b:analysis-b", false, true);
      await act(async () => window.dispatchEvent(new Event("afterprint")));
      expect(f.details().map(d => d.open)).toEqual([false, false]);
      expect(visible(f.host.querySelector("#required")!)).toBe(true);
    } finally { await f.dispose(); }
  });
});
