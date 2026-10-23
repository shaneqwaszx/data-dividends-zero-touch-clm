// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";
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
  const render = async (scopeKey = "actor-a:session-a:case-a", active = true, final = false, revision = "one") => {
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

describe("collapsible stage Main", () => {
  it("toggles the parent independently of all four supporting combinations with stage-qualified native names", async () => {
    const f = await fixture();
    try {
      await f.render(undefined, true);
      const parent = f.host.querySelector<HTMLButtonElement>("h2 button")!;
      expect(parent.type).toBe("button");
      expect(parent.getAttribute("aria-expanded")).toBe("true");
      expect(f.details().map(d => d.open)).toEqual([false, false]);
      expect(f.details().map(d => d.querySelector("summary")?.textContent)).toEqual([
        "More details — Submission readiness", "Technical details — Submission readiness",
      ]);
      for (const [more, technical] of [[false, false], [true, false], [true, true], [false, true]]) {
        await f.toggle(0, more); await f.toggle(1, technical);
        expect(visible(f.host.querySelector("#required")!)).toBe(true);
        expect(visible(f.host.querySelector("#draft")!)).toBe(more);
        expect(visible(f.host.querySelector("#diagnostic")!)).toBe(technical);
        await act(async () => parent.click());
        expect(parent.getAttribute("aria-expanded")).toBe("false");
        for (const id of ["required", "draft", "diagnostic"]) expect(visible(f.host.querySelector(`#${id}`)!)).toBe(false);
        await f.render(undefined, true, false, "refreshed");
        expect(parent.getAttribute("aria-expanded")).toBe("false");
        await act(async () => parent.click());
        expect(f.details().map(d => d.open)).toEqual([more, technical]);
      }
    } finally { await f.dispose(); }
  });

  it("preserves mounted drafts and support state through toggles, active changes and same-scope evidence refresh", async () => {
    const f = await fixture();
    try {
      await f.render(undefined, true);
      await f.toggle(0, true);
      const draft = f.host.querySelector<HTMLInputElement>("#draft")!; draft.value = "unsaved local draft";
      await f.toggle(0, false); await f.toggle(0, true);
      const parent = f.host.querySelector<HTMLButtonElement>("h2 button")!;
      await act(async () => parent.click());
      await act(async () => parent.click());
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
      await f.render(undefined, false, true);
      await act(async () => f.host.querySelector<HTMLButtonElement>("h2 button")!.click());
      await f.toggle(1, true);
      await act(async () => window.dispatchEvent(new Event("beforeprint")));
      expect(f.details().map(d => d.open)).toEqual([true, true]);
      await act(async () => window.dispatchEvent(new Event("afterprint")));
      expect(f.details().map(d => d.open)).toEqual([false, true]);
      expect(visible(f.host.querySelector("#required")!)).toBe(false);
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
  it.each(["more", "technical"] as const)("preserves newer external focus after focused %s content is removed before an identity change", async (removed) => {
    const host = document.createElement("div"), outside = document.createElement("button");
    outside.textContent = "Other workspace action"; document.body.append(host, outside);
    const root = createRoot(host);
    const render = async (scopeKey: string, present: boolean) => {
      await act(async () => root.render(<StageDisclosure title="Removal boundary" scopeKey={scopeKey}
        main={<button>Required Main action</button>}
        moreDetails={removed === "more" && !present ? undefined : <input id="removal-more" />}
        technicalDetails={removed === "technical" && !present ? undefined : <input id="removal-technical" />} />));
    };
    try {
      let scope = "actor-a:session-a:case-a";
      for (const nextScope of ["actor-b:session-a:case-a", "actor-b:session-b:case-a", "actor-b:session-b:case-b"]) {
        await render(scope, true);
        const control = host.querySelector<HTMLInputElement>(`#removal-${removed}`)!;
        const details = control.closest("details")!;
        await act(async () => { details.open = true; });
        control.focus(); expect(document.activeElement).toBe(control);
        await render(scope, false);
        expect(control.isConnected).toBe(false);
        expect(document.activeElement).toBe(document.body);
        outside.focus(); expect(document.activeElement).toBe(outside);
        await render(nextScope, false);
        expect(document.activeElement).toBe(outside);
        expect(visible(host.querySelector("button")!)).toBe(true);
        expect([...host.querySelectorAll("details")].every(element => !element.open)).toBe(true);
        scope = nextScope;
      }
    } finally { await act(async () => root.unmount()); host.remove(); outside.remove(); }
  });

  it.each(["more", "technical"] as const)("retires removed %s focus on same-scope refresh even when focus remains on body", async (removed) => {
    const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
    const render = async (scopeKey: string, present: boolean) => {
      await act(async () => root.render(<StageDisclosure title="Removed focus" scopeKey={scopeKey} main={<p>Current Main</p>}
        moreDetails={removed === "more" && present ? <input /> : undefined}
        technicalDetails={removed === "technical" && present ? <input /> : undefined} />));
    };
    try {
      await render("actor-a:session-a:case-a", true);
      await act(async () => { host.querySelector("details")!.open = true; });
      host.querySelector("input")!.focus(); expect(document.activeElement).toBe(host.querySelector("input"));
      await render("actor-a:session-a:case-a", false);
      expect(document.activeElement).toBe(document.body);
      await render("actor-b:session-b:case-b", false);
      expect(document.activeElement).toBe(document.body);
    } finally { await act(async () => root.unmount()); host.remove(); }
  });

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
      expect(visible(f.host.querySelector("#required")!)).toBe(false);
    } finally { await f.dispose(); }
  });
});


describe("outer stage focus and reveal", () => {
  it("returns hidden focus to the outer toggle, reopens for explicit navigation and preserves optional state", async () => {
    const f = await fixture();
    try {
      await f.render(undefined, true); await f.toggle(0, true);
      const draft = f.host.querySelector<HTMLInputElement>("#draft")!; draft.value = "unsaved"; draft.focus();
      const parent = f.host.querySelector<HTMLButtonElement>("h2 button")!;
      await act(async () => parent.click());
      expect(document.activeElement).toBe(parent);
      expect(visible(draft)).toBe(false);
      await act(async () => revealStage(draft));
      expect(parent.getAttribute("aria-expanded")).toBe("true");
      expect(visible(draft)).toBe(true); expect(draft.value).toBe("unsaved");
      expect(f.details().map(d => d.open)).toEqual([true, false]);
      const controlled = parent.getAttribute("aria-controls")!.split(" ");
      expect(controlled.every(id => document.getElementById(id) !== null)).toBe(true);
    } finally { await f.dispose(); }
  });
  it("restores every parent/More/Technical print combination", async () => {
    const f = await fixture();
    try {
      await f.render(undefined, true, true);
      const parent = f.host.querySelector<HTMLButtonElement>("h2 button")!;
      for (const expanded of [false, true]) for (const more of [false, true]) for (const technical of [false, true]) {
        if ((parent.getAttribute("aria-expanded") === "true") !== expanded) await act(async () => parent.click());
        await f.toggle(0, more); await f.toggle(1, technical);
        await act(async () => window.dispatchEvent(new Event("beforeprint")));
        expect(parent.getAttribute("aria-expanded")).toBe("true");
        expect(visible(f.host.querySelector("#required")!)).toBe(true);
        expect(f.details().map(d => d.open)).toEqual([true, true]);
        await act(async () => window.dispatchEvent(new Event("afterprint")));
        expect(parent.getAttribute("aria-expanded")).toBe(String(expanded));
        expect(f.details().map(d => d.open)).toEqual([more, technical]);
      }
    } finally { await f.dispose(); }
  });
});


it("returns focus from print-expanded content before restoring a collapsed parent", async () => {
  const f = await fixture();
  try {
    await f.render(undefined, true, true);
    const parent = f.host.querySelector<HTMLButtonElement>("h2 button")!;
    await act(async () => parent.click());
    await act(async () => window.dispatchEvent(new Event("beforeprint")));
    f.host.querySelector<HTMLElement>("#required")!.focus();
    await act(async () => window.dispatchEvent(new Event("afterprint")));
    expect(document.activeElement).toBe(parent);
    expect(visible(document.activeElement!)).toBe(true);
  } finally { await f.dispose(); }
});

describe("completed sections", () => {
  it.each([
    ["done", "false"], ["attention", "true"], ["current", "true"], ["pending", "true"],
  ] as const)("a %s section starts with aria-expanded=%s, and navigation can still reveal it", async (tone, expanded) => {
    const host = document.createElement("div"); document.body.append(host);
    const root = createRoot(host);
    await act(async () => root.render(<StageDisclosure title="Document verification" scopeKey="case-a"
      status={{ tone, label: tone }} main={<p id="main">Evidence</p>} />));
    const button = host.querySelector<HTMLButtonElement>("button[data-stage-toggle]")!;
    expect(button.getAttribute("aria-expanded")).toBe(expanded);
    await act(async () => revealStage(host.querySelector("#main")!));
    expect(button.getAttribute("aria-expanded")).toBe("true");
    await act(async () => root.unmount()); host.remove();
  });
});

describe("sticky header focus clearance", () => {
  it("aligns a control focused under the sticky header just below it and leaves visible controls alone", async () => {
    const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
    await act(async () => root.render(<StageDisclosure title="Document verification" scopeKey="case-a" active
      main={<><input id="covered" aria-label="Covered" /><input id="clear" aria-label="Clear" /></>} />));
    const rect = (top: number, bottom: number) => ({ top, bottom, left: 0, right: 10, width: 10, height: bottom - top, x: 0, y: top, toJSON: () => ({}) }) as DOMRect;
    host.querySelector("h2")!.getBoundingClientRect = () => rect(12, 83);
    const covered = host.querySelector<HTMLInputElement>("#covered")!; const clear = host.querySelector<HTMLInputElement>("#clear")!;
    covered.getBoundingClientRect = () => rect(23, 130); clear.getBoundingClientRect = () => rect(200, 230);
    const scrolled: Array<[string, ScrollIntoViewOptions | boolean | undefined]> = [];
    covered.scrollIntoView = (options) => { scrolled.push(["covered", options]); };
    clear.scrollIntoView = (options) => { scrolled.push(["clear", options]); };
    act(() => covered.focus()); act(() => clear.focus());
    expect(scrolled).toEqual([["covered", { block: "start" }]]);
    await act(async () => root.unmount()); host.remove();
  });

  async function renderCovered() {
    const host = document.createElement("div"); document.body.append(host); const root = createRoot(host);
    await act(async () => root.render(<StageDisclosure title="Document verification" scopeKey="case-a" active
      main={<><input id="covered" aria-label="Covered" /><input id="other" aria-label="Other" /></>} />));
    const rect = (top: number, bottom: number) => ({ top, bottom, left: 0, right: 10, width: 10, height: bottom - top, x: 0, y: top, toJSON: () => ({}) }) as DOMRect;
    host.querySelector("h2")!.getBoundingClientRect = () => rect(12, 83);
    const covered = host.querySelector<HTMLInputElement>("#covered")!; const other = host.querySelector<HTMLInputElement>("#other")!;
    covered.getBoundingClientRect = () => rect(23, 130); other.getBoundingClientRect = () => rect(200, 230);
    const scroll = { count: 0 };
    covered.scrollIntoView = () => { scroll.count++; };
    const press = (pointerType: string) => {
      const event = new Event("pointerdown", { bubbles: true }); Object.defineProperty(event, "pointerType", { value: pointerType });
      covered.dispatchEvent(event);
    };
    const refocus = () => { other.focus(); covered.focus(); };
    return { root, host, covered, scroll, press, refocus };
  }

  it("leaves focus from a mouse press in place and aligns again once the press ends", async () => {
    const { root, host, covered, scroll, press, refocus } = await renderCovered();
    act(() => { press("mouse"); covered.focus(); });
    expect(scroll.count).toBe(0);
    act(() => { window.dispatchEvent(new Event("pointerup")); refocus(); });
    expect(scroll.count).toBe(1);
    await act(async () => root.unmount()); host.remove();
  });

  it.each(["touch", "pen"])("keeps a %s tap's focus in place until its click, which focus after pointerup follows", async (pointerType) => {
    const { root, host, covered, scroll, press, refocus } = await renderCovered();
    // Touch/pen order: pointerdown, pointerup, then the compatibility mousedown moves focus, then click.
    act(() => { press(pointerType); window.dispatchEvent(new Event("pointerup")); covered.focus(); });
    expect(scroll.count).toBe(0);
    act(() => { window.dispatchEvent(new Event("click")); refocus(); });
    expect(scroll.count).toBe(1);
    await act(async () => root.unmount()); host.remove();
  });

  it("ends a press whose release never arrives after the bounded fallback", async () => {
    vi.useFakeTimers();
    try {
      const { root, host, scroll, press, refocus } = await renderCovered();
      act(() => press("touch"));
      act(() => { vi.advanceTimersByTime(999); refocus(); });
      expect(scroll.count).toBe(0);
      act(() => { vi.advanceTimersByTime(1); refocus(); });
      expect(scroll.count).toBe(1);
      await act(async () => root.unmount()); host.remove();
    } finally {
      vi.useRealTimers();
    }
  });
});
