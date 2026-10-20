// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import KnowledgeReview from "./KnowledgeReview";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.unstubAllGlobals();
});

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

async function flush(): Promise<void> {
  for (let i = 0; i < 6; i += 1) await act(async () => { await Promise.resolve(); });
}

const PENDING = {
  entry_id: "resolution.abc",
  key: "resolution.abc@v1",
  version: 1,
  kind: "resolution",
  status: "pending_review",
  title: "Draft: Document or reconciliation review required",
  body: "Problem: the [COMPANY] address differs from ACRA.",
  blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"],
  fields: ["registered_address"],
  stages: [],
  follow_ups: ["What about ownership?"],
  visibility: { roles: [], teams: [] },
  replaces: null,
  revises: null,
  author: "maya-lim",
  approver: null,
  approved_at: null,
  created_at: null,
  source_ref: "RM feedback",
  illustrative: false,
  content_hash: "a".repeat(64),
};

function backend(calls: { url: string; body: unknown }[], decision = () => json({ ...PENDING, status: "approved" })) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST") calls.push({ url, body: JSON.parse(String(init.body)) });
    if (url.endsWith("/knowledge/reviews")) return json({ pending: [PENDING], gaps: [{ id: 7, note: "No proof list.", blocker_codes: [], fields: [], stages: [], created_at: "" }] });
    if (url.endsWith("/knowledge/stats")) return json({ entries: {}, feedback: { total: 3, helpful: 2, not_helpful: 1, helpful_rate: 0.667, open_gaps: 1 } });
    if (url.includes("/knowledge/entries?kind=resolution")) return json([]);
    if (url.endsWith("/edit")) return json(PENDING);
    if (url.endsWith("/decision")) return decision();
    if (url.endsWith("/close")) return json({ status: "closed" });
    return json({}, 404);
  });
}

function render(): HTMLDivElement {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root?.render(<KnowledgeReview onClose={() => undefined} />));
  return container;
}

function type(element: Element | null, value: string): void {
  const field = element as HTMLInputElement | HTMLTextAreaElement;
  const proto = field instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  act(() => {
    Object.getOwnPropertyDescriptor(proto, "value")?.set?.call(field, value);
    field.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function button(view: HTMLElement, text: string): HTMLButtonElement {
  const found = [...view.querySelectorAll("button")].find((b) => b.textContent === text);
  if (!found) throw new Error(`no button ${text}`);
  return found;
}

describe("KnowledgeReview", () => {
  it("shows the queue, gaps and stats, and approves exactly the content shown", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    expect(view.textContent).toContain("Waiting for review (1)");
    expect(view.textContent).toContain("3 feedback · 2 solved · 1 not helpful · 67% helpful");
    expect(view.textContent).toContain("No proof list.");

    act(() => button(view, "Approve").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([
      "/knowledge/entries/resolution.abc/versions/1/decision",
    ]);
    expect(calls[0].body).toEqual({ approve: true, content_hash: "a".repeat(64), notes: "" });
    expect(view.textContent).toContain("Approved: it can now help answer similar questions.");
  });

  it("saves the Director's edits as a new version for another reviewer instead of approving", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();

    type(view.querySelector("article input"), "Address differs from ACRA after an office move");
    expect(() => button(view, "Approve")).toThrow();
    act(() => button(view, "Save changes for another reviewer").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([
      "/knowledge/entries/resolution.abc/versions/1/edit",
    ]);
    expect(calls[0].body).toMatchObject({
      content_hash: "a".repeat(64),
      title: "Address differs from ACRA after an office move",
    });
    expect(view.textContent).toContain("Changes saved as a new version. Another reviewer must approve it.");
  });

  it("discarding changes brings back Approve and Reject", async () => {
    vi.stubGlobal("fetch", backend([]));
    const view = render();
    await flush();
    type(view.querySelector("article input"), "Something else entirely");
    act(() => button(view, "Discard changes").click());
    expect(button(view, "Approve")).toBeTruthy();
    expect(button(view, "Reject")).toBeTruthy();
  });

  it("rejects without editing and shows the backend's reason when a decision is refused", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal(
      "fetch",
      backend(calls, () =>
        json({ detail: { message: "You cannot approve or reject an entry you wrote or edited." } }, 403),
      ),
    );
    const view = render();
    await flush();
    act(() => button(view, "Reject").click());
    await flush();
    expect(calls).toHaveLength(1);
    expect(calls[0].body).toEqual({ approve: false, content_hash: "a".repeat(64), notes: "" });
    expect(view.querySelector("[role=alert]")?.textContent).toBe(
      "You cannot approve or reject an entry you wrote or edited.",
    );
  });

  it("closes a gap", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    act(() => button(view, "Mark as handled").click());
    await flush();
    expect(calls[0].url).toContain("/knowledge/feedback/7/close");
  });
});
