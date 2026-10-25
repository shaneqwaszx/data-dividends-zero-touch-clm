// @vitest-environment jsdom

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AnswerRecord } from "../aiAssistant";
import KnowledgeReview from "./KnowledgeReview";
import { suggestedCause } from "./RequestPage";

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
  single_reviewer: false,
};

const GUIDANCE = {
  ...PENDING,
  entry_id: "guidance.address-mismatch",
  key: "guidance.address-mismatch@v2",
  version: 2,
  kind: "guidance",
  status: "approved",
  title: "Registered address differs from ACRA",
};

function backend(calls: { url: string; body: unknown }[], decision = () => json({ ...PENDING, status: "approved" })) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST") calls.push({ url, body: JSON.parse(String(init.body)) });
    if (url.endsWith("/knowledge/reviews")) return json({ pending: [PENDING], gaps: [{ id: 7, note: "No proof list.", blocker_codes: [], fields: [], stages: [], created_at: "" }] });
    if (url.endsWith("/knowledge/stats")) {
      return json({
        entries: {},
        feedback: { total: 3, helpful: 2, not_helpful: 1, helpful_rate: 0.667, open_gaps: 1 },
        by_topic: { DOCUMENT_SOURCE_CONFLICT: { helpful: 2, not_helpful: 1 }, UBO_EVIDENCE_REQUIRED: { helpful: 0, not_helpful: 1 } },
      });
    }
    if (url.endsWith("/knowledge/entries")) return json([GUIDANCE]);
    if (url.endsWith("/knowledge/me")) {
      return json({ user_id: "olivia-koh", can_review: true, can_edit_guidance: false, single_reviewer: true });
    }
    if (url.endsWith("/edit")) return json(PENDING);
    if (url.endsWith("/decision")) return decision();
    if (url.endsWith("/close")) return json({ status: "closed" });
    if (url.endsWith("/draft")) return json({ ...PENDING, entry_id: "resolution.new", author: "director-dan" });
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

function choose(element: Element | null, value: string): void {
  const select = element as HTMLSelectElement;
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(select, value);
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function button(view: HTMLElement, text: string): HTMLButtonElement {
  const found = [...view.querySelectorAll("button")].find((b) => b.textContent === text);
  if (!found) throw new Error(`no button ${text}`);
  return found;
}

describe("KnowledgeReview", () => {
  it("shows the queue, requests and stats, and publishes exactly the content shown after confirming", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    expect(view.textContent).toContain("Waiting for review (1)");
    expect(view.textContent).toContain("3 feedback · 2 helpful · 1 not helpful · 67% helpful");
    expect([...view.querySelectorAll('[aria-label="Confidence by topic"] li')].map((li) => li.textContent)).toEqual([
      "DOCUMENT_SOURCE_CONFLICT: 2 helpful · 1 not helpful",
      "UBO_EVIDENCE_REQUIRED: 0 helpful · 1 not helpful",
    ]);
    expect(view.textContent).toContain("Enhancement requests (1)");
    expect(view.textContent).not.toContain("Gaps");
    expect(view.textContent).toContain("No proof list.");

    // Approve first shows the final text; nothing is sent until it is confirmed.
    act(() => button(view, "Approve").click());
    const confirm = view.querySelector('[aria-label="Confirm publishing"]') as HTMLElement;
    expect(confirm.textContent).toContain("Draft: Document or reconciliation review required");
    expect(confirm.textContent).toContain("Problem: the [COMPANY] address differs from ACRA.");
    expect(confirm.textContent).toContain("What about ownership?");
    expect(confirm.textContent).toContain("goes live for every team");
    expect(confirm.textContent).toContain("recorded as a single-reviewer decision");
    expect(calls).toEqual([]);
    act(() => button(view, "Back").click());
    expect(view.querySelector('[aria-label="Confirm publishing"]')).toBeNull();
    expect(calls).toEqual([]);

    act(() => button(view, "Approve").click());
    act(() => button(view, "Confirm and publish").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([
      "/knowledge/entries/resolution.abc/versions/1/decision",
    ]);
    expect(calls[0].body).toEqual({ approve: true, content_hash: "a".repeat(64), notes: "", confirm_single_reviewer: true });
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

  // PR #99 review on 9cae747: leaving out "replaces" kept the old target, so approving still
  // retired it.
  it("sends replaces: null when the reviewer chooses Does not replace one", async () => {
    const calls: { url: string; body: unknown }[] = [];
    const older = { ...PENDING, entry_id: "resolution.old", key: "resolution.old@v1", status: "approved", title: "Older resolution" };
    const replacing = { ...PENDING, replaces: "resolution.old" };
    const rest = backend(calls);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/knowledge/reviews")) return json({ pending: [replacing], gaps: [] });
        if (url.endsWith("/knowledge/entries")) return json([older, GUIDANCE]);
        return rest(input, init);
      }),
    );
    const view = render();
    await flush();
    const select = view.querySelector("article select") as HTMLSelectElement;
    expect(select.value).toBe("resolution.old");

    choose(select, "");
    act(() => button(view, "Save changes for another reviewer").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([
      "/knowledge/entries/resolution.abc/versions/1/edit",
    ]);
    expect(calls[0].body).toHaveProperty("replaces", null);
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
    expect(calls[0].body).toEqual({ approve: false, content_hash: "a".repeat(64), notes: "", confirm_single_reviewer: false });
    expect(view.querySelector("[role=alert]")?.textContent).toBe(
      "You cannot approve or reject an entry you wrote or edited.",
    );
  });

  it("closes an enhancement request only with a reason", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    const request = view.querySelector('[aria-label="Enhancement request 7"]') as HTMLElement;
    expect(button(request, "Close with reason").disabled).toBe(true);
    const reason = request.querySelector(":scope > label input");
    type(reason, "   ");
    expect(button(request, "Close with reason").disabled).toBe(true);
    type(reason, " Covered by the proof-list guidance. ");
    act(() => button(request, "Close with reason").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual(["/knowledge/feedback/7/close"]);
    expect(calls[0].body).toEqual({ reason: "Covered by the proof-list guidance." });
    expect(view.textContent).toContain("Request closed.");
  });

  it("writes the fix for a request as a past case and saves it for review", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    const request = view.querySelector('[aria-label="Enhancement request 7"]') as HTMLElement;
    const save = () => button(request, "Save the fix for review");
    expect(save().disabled).toBe(true);
    const fields = request.querySelectorAll("fieldset input, fieldset textarea");
    type(fields[0], "Proof list for moved offices");
    expect(save().disabled).toBe(true); // no body yet
    type(fields[1], "Ask for the tenancy agreement before changing the address.");
    type(fields[2], "What about the ownership step?\n\n");
    act(() => save().click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual(["/knowledge/feedback/7/draft"]);
    expect(calls[0].body).toEqual({
      kind: "resolution",
      title: "Proof list for moved offices",
      body: "Ask for the tenancy agreement before changing the address.",
      follow_ups: ["What about the ownership step?"],
    });
    expect(view.textContent).toContain("Fix saved for review. Check it under Waiting for review, then publish it.");
  });

  it("writes the fix as a change to existing guidance, which needs a source reference", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    const request = view.querySelector('[aria-label="Enhancement request 7"]') as HTMLElement;
    choose(request.querySelector("fieldset select"), "guidance");
    choose(request.querySelectorAll("fieldset select")[1], "guidance.address-mismatch");
    const inputs = () => request.querySelectorAll("fieldset input, fieldset textarea");
    type(inputs()[0], "Address differs from ACRA");
    type(inputs()[1], "Keep the registry address until the client confirms the move.");
    expect(button(request, "Save the fix for review").disabled).toBe(true); // no source yet
    type(inputs()[2], "docs/decisions/DECISION_LOG.md#D-030");
    act(() => button(request, "Save the fix for review").click());
    await flush();
    expect(calls[0].body).toEqual({
      kind: "guidance",
      title: "Address differs from ACRA",
      body: "Keep the registry address until the client confirms the move.",
      source_ref: "docs/decisions/DECISION_LOG.md#D-030",
      entry_id: "guidance.address-mismatch",
    });
  });

  it("says nothing about single-reviewer decisions when the mode is off", async () => {
    const rest = backend([]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) =>
        String(input).endsWith("/knowledge/me")
          ? json({ user_id: "director-dan", can_review: true, can_edit_guidance: false, single_reviewer: false })
          : rest(input, init),
      ),
    );
    const view = render();
    await flush();
    act(() => button(view, "Approve").click());
    const confirm = view.querySelector('[aria-label="Confirm publishing"]') as HTMLElement;
    expect(confirm.textContent).toContain("goes live for every team.");
    expect(confirm.textContent).not.toContain("single-reviewer");
  });

  it("lists entries published by a single reviewer and says so after self-publishing", async () => {
    const calls: { url: string; body: unknown }[] = [];
    const single = { ...GUIDANCE, single_reviewer: true, approver: "olivia-koh", approved_at: "2026-10-21T10:00:00+00:00" };
    const rest = backend(calls, () => json({ ...PENDING, status: "approved", single_reviewer: true }));
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) =>
        String(input).endsWith("/knowledge/entries") ? json([single, { ...PENDING, status: "approved" }]) : rest(input, init),
      ),
    );
    const view = render();
    await flush();
    expect(view.textContent).toContain("Published by a single reviewer (1)");
    expect([...view.querySelectorAll('[aria-label="Published by a single reviewer"] li')].map((li) => li.textContent)).toEqual([
      "Guidance: Registered address differs from ACRA · version 2 · approved by olivia-koh, who wrote or edited it · 2026-10-21T10:00:00+00:00",
    ]);
    act(() => button(view, "Approve").click());
    act(() => button(view, "Confirm and publish").click());
    await flush();
    expect(view.textContent).toContain("Published as the only reviewer: recorded as a single-reviewer decision.");
  });

  it("shows the backend's reason when a request was already handled", async () => {
    const calls: { url: string; body: unknown }[] = [];
    const rest = backend(calls);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) =>
        String(input).endsWith("/close")
          ? json({ detail: { code: "CHANGED", message: "This request was already handled. Refresh and try again." } }, 409)
          : rest(input, init),
      ),
    );
    const view = render();
    await flush();
    type(view.querySelector('[aria-label="Enhancement request 7"] > label input'), "Duplicate.");
    act(() => button(view, "Close with reason").click());
    await flush();
    expect(view.querySelector("[role=alert]")?.textContent).toBe("This request was already handled. Refresh and try again.");
  });
});

// PR #99 panel evidence D5: the aria-modal dialog takes focus, closes on Escape, keeps Tab
// inside and gives focus back to what opened it.
function Opener() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Review
      </button>
      {open && <KnowledgeReview onClose={() => setOpen(false)} />}
    </>
  );
}

async function openFromButton(): Promise<HTMLDivElement> {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root?.render(<Opener />));
  const opener = button(container, "Review");
  opener.focus();
  act(() => opener.click());
  await flush();
  return container;
}

function press(key: string, shiftKey = false): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { key, shiftKey, bubbles: true, cancelable: true });
  act(() => {
    (document.activeElement ?? document.body).dispatchEvent(event);
  });
  return event;
}

function dialogControls(view: HTMLElement): HTMLElement[] {
  const dialog = view.querySelector("[role=dialog]");
  return [...(dialog?.querySelectorAll<HTMLElement>("button, input, select, textarea") ?? [])].filter(
    (control) => !control.hasAttribute("disabled"),
  );
}

describe("KnowledgeReview dialog focus", () => {
  it("moves focus into the dialog when it opens", async () => {
    vi.stubGlobal("fetch", backend([]));
    const view = await openFromButton();
    const dialog = view.querySelector("[role=dialog]");
    expect(document.activeElement?.textContent).toBe("Knowledge review");
    expect(dialog?.contains(document.activeElement)).toBe(true);
  });

  it("closes on Escape and returns focus to the button that opened it", async () => {
    vi.stubGlobal("fetch", backend([]));
    const view = await openFromButton();
    const event = press("Escape");
    expect(event.defaultPrevented).toBe(true);
    expect(view.querySelector("[role=dialog]")).toBeNull();
    expect(document.activeElement).toBe(button(view, "Review"));
  });

  it("returns focus to the button that opened it when closed with the close button", async () => {
    vi.stubGlobal("fetch", backend([]));
    const view = await openFromButton();
    const close = view.querySelector<HTMLButtonElement>("[aria-label='Close knowledge review']");
    close?.focus();
    act(() => close?.click());
    expect(view.querySelector("[role=dialog]")).toBeNull();
    expect(document.activeElement).toBe(button(view, "Review"));
  });

  it("wraps Tab and Shift+Tab around the dialog's controls", async () => {
    vi.stubGlobal("fetch", backend([]));
    const view = await openFromButton();
    const controls = dialogControls(view);
    const [first, last] = [controls[0], controls[controls.length - 1]];
    expect(first.getAttribute("aria-label")).toBe("Close knowledge review");
    // The last enabled control: the request's "Reason for closing" (Close with reason waits for it).
    expect(last).toBe(view.querySelector('[aria-label="Enhancement request 7"] > label input'));

    // Shift+Tab from the heading (where focus starts) goes to the last control, not out.
    expect(press("Tab", true).defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(last);
    // Tab from the last control wraps to the first; Shift+Tab from the first to the last.
    expect(press("Tab").defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(first);
    expect(press("Tab", true).defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(last);
    // Between the ends the browser moves focus as usual.
    controls[1].focus();
    expect(press("Tab").defaultPrevented).toBe(false);
    expect(press("Tab", true).defaultPrevented).toBe(false);
    // Focus that fell out of the dialog (a removed or disabled control) comes back in.
    (document.activeElement as HTMLElement).blur();
    expect(press("Tab").defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(first);
  });
});

const RECORD = {
  answer_id: "A".repeat(22),
  case_id: "case-1",
  created_at: "2026-10-25T00:00:00+00:00",
  question: "Explain the registered address difference",
  earlier_answer_ids: ["B".repeat(22)],
  case_snapshot: { blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"], stage: "Documents", steps_done: 3, steps_total: 10, facts_hash: "f".repeat(64) },
  knowledge: {
    confidence: "low",
    degraded: false,
    thresholds: { guidance: 0.3, resolution: 0.4 },
    entries: [{ tag: "G1", kind: "guidance", entry_id: "guidance.environments", version: 1, score: 0.31, parts: {}, fallback: true }],
  },
  allowed_lines: [
    { text: "Registry and document differences require the current case decision.", source: "policy" },
    { text: 'The current case offers "Keep registry value".', source: "case" },
    { text: "Ask for a certified copy of the register [G1].", source: "knowledge" },
  ],
  chosen_lines: [],
  dropped_lines: ["The document says [ADDRESS] but ACRA says [ADDRESS]."],
  shown_answer: "I found 1 issue stopping the onboarding of [COMPANY].",
  result: {
    answered_by: "case_data",
    notices: ["The model response could not be verified, so this answer comes from the case data."],
    fallback_reason: "nothing_allowed",
    left_out: 1,
    model: "m",
    elapsed_ms: 2300,
  },
  rated: true,
};

const GAP = { id: 7, note: "It did not show the two addresses.", blocker_codes: ["DOCUMENT_SOURCE_CONFLICT"], fields: [], stages: [], created_at: "" };

function reviewWith(gap: Record<string, unknown>, fetched: string[], record: unknown = RECORD) {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    fetched.push(url);
    if (url.endsWith("/knowledge/reviews")) return json({ pending: [], gaps: [gap] });
    if (url.endsWith("/knowledge/stats")) {
      return json({ entries: {}, feedback: { total: 1, helpful: 0, not_helpful: 1, helpful_rate: 0, open_gaps: 1 }, by_topic: {} });
    }
    if (url.endsWith("/knowledge/entries")) return json([]);
    if (url.endsWith("/knowledge/me")) return json({ user_id: "olivia-koh", can_review: true, can_edit_guidance: false, single_reviewer: true });
    if (url.endsWith("/knowledge/feedback/7/answer")) return json(record);
    if (url.endsWith(`/knowledge/feedback/7/answers/${"B".repeat(22)}`)) {
      return json({ ...RECORD, answer_id: "B".repeat(22), question: "What should I do next?", shown_answer: "Keep the registry value.", result: { ...RECORD.result, notices: [] } });
    }
    return json({}, 404);
  }));
}

function openRequestPage(view: HTMLDivElement): void {
  const open = [...view.querySelectorAll("button")].find((b) => b.textContent === "Open request page");
  act(() => open?.click());
}

describe("The enhancement request page", () => {
  it("opens full width, loads the record only then, and shows what the RM saw", async () => {
    const fetched: string[] = [];
    reviewWith({ ...GAP, answer_id: "A".repeat(22) }, fetched);
    const view = render();
    await flush();
    // Nothing is fetched (and so no view is logged) until the Director opens the request.
    expect(fetched.some((url) => url.includes("/answer"))).toBe(false);
    openRequestPage(view);
    await flush();
    expect(fetched.filter((url) => url.endsWith("/knowledge/feedback/7/answer"))).toHaveLength(1);
    expect(view.querySelector(".knowledge-review-page")).not.toBeNull();
    expect(document.activeElement?.textContent).toBe("Enhancement request 7");
    const saw = view.querySelector('[aria-labelledby="request-page-saw"]');
    expect(saw?.querySelector(".request-page-question")?.textContent).toBe("Explain the registered address difference");
    expect(saw?.querySelector(".request-page-answer-text")?.textContent).toBe("I found 1 issue stopping the onboarding of [COMPANY].");
    expect(saw?.querySelector(".request-page-notice")?.textContent).toContain("could not be verified");
    expect(saw?.querySelector(".request-page-note")?.textContent).toBe("It did not show the two addresses.");
    // The earlier answers of the chat, loaded on request.
    act(() => [...(saw?.querySelectorAll("button") ?? [])].find((b) => b.textContent === "Show earlier answer 1")?.click());
    await flush();
    expect(saw?.textContent).toContain("What should I do next?");
    // Back returns to the review window, with focus on the button that opened the page.
    act(() => [...view.querySelectorAll("button")].find((b) => b.textContent?.includes("Back to Knowledge review"))?.click());
    await flush();
    expect(view.querySelector(".knowledge-review-page")).toBeNull();
    expect(document.activeElement?.textContent).toBe("Open request page");
  });

  it("explains why the AI answered this way", async () => {
    reviewWith({ ...GAP, answer_id: "A".repeat(22) }, []);
    const view = render();
    await flush();
    openRequestPage(view);
    await flush();
    const why = view.querySelector('[aria-labelledby="request-page-why"]');
    const cause = why?.querySelector('[aria-label="Suggested cause"]');
    expect(cause?.querySelector(".request-page-cause-label")?.textContent).toBe("Rule-based hint, not a verdict");
    expect(cause?.querySelector(".request-page-cause-title")?.textContent).toBe("Catalog gap: no allowed line matched");
    const dropped = why?.querySelector("del");
    expect(dropped?.textContent).toBe("The document says [ADDRESS] but ACRA says [ADDRESS].");
    expect(dropped?.nextElementSibling?.textContent).toContain("Not an allowed line");
    const rows = [...(why?.querySelectorAll(".request-page-table tbody tr") ?? [])].map((row) => row.textContent);
    expect(rows).toEqual(["G1guidance.environments v1 (stage guidance)0.310.3"]);
    const allowed = why?.querySelector(".request-page-allowed");
    expect(allowed?.querySelector("summary")?.textContent).toBe("All allowed lines (3)");
    expect([...(allowed?.querySelectorAll(".request-page-tag") ?? [])].map((tag) => tag.textContent)).toEqual(["Policy", "Case", "Knowledge"]);
    expect(why?.textContent).toContain("3 of 10 done");
  });

  it("tags the lines shown to the RM by where they come from", async () => {
    const shown = { ...RECORD, chosen_lines: ['The current case offers "Keep registry value".'], dropped_lines: [], result: { ...RECORD.result, answered_by: "model", fallback_reason: null, left_out: 0 } };
    reviewWith({ ...GAP, answer_id: "A".repeat(22) }, [], shown);
    const view = render();
    await flush();
    openRequestPage(view);
    await flush();
    const line = view.querySelector('[aria-labelledby="request-page-why"] .request-page-lines li');
    expect(line?.querySelector(".request-page-tag")?.textContent).toBe("Case");
    expect(line?.textContent).toContain("Keep registry value");
  });

  it("Escape on the request page goes back to the review window", async () => {
    reviewWith({ ...GAP, answer_id: "A".repeat(22) }, []);
    const view = render();
    await flush();
    openRequestPage(view);
    await flush();
    act(() => { document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
    await flush();
    expect(view.querySelector(".knowledge-review-page")).toBeNull();
    expect(view.textContent).toContain("Enhancement requests (1)");
  });

  it("offers no request page for a request without a record", async () => {
    reviewWith(GAP, []);
    const view = render();
    await flush();
    expect(view.textContent).toContain("It did not show the two addresses.");
    expect([...view.querySelectorAll("button")].some((b) => b.textContent === "Open request page")).toBe(false);
  });
});

describe("suggestedCause", () => {
  const base = RECORD as unknown as AnswerRecord;
  const used = { ...base.knowledge };
  const none = { ...base.knowledge, entries: [] };

  it("follows the three rules in order", () => {
    expect(suggestedCause({ ...base, chosen_lines: [], dropped_lines: ["x"], knowledge: none })?.title)
      .toBe("Catalog gap: no allowed line matched");
    expect(suggestedCause({ ...base, chosen_lines: ["a"], dropped_lines: [], result: { ...base.result, left_out: 0, fallback_reason: null }, knowledge: none })?.title)
      .toBe("No knowledge found");
    expect(suggestedCause({ ...base, chosen_lines: ["a"], dropped_lines: ["x"], result: { ...base.result, left_out: 1, fallback_reason: null }, knowledge: used })?.title)
      .toBe("Missing knowledge");
    expect(suggestedCause({ ...base, chosen_lines: ["a"], dropped_lines: [], result: { ...base.result, left_out: 0, fallback_reason: null }, knowledge: used }))
      .toBeNull();
  });

  it("gives no hint when the model was not available", () => {
    expect(suggestedCause({ ...base, chosen_lines: [], dropped_lines: [], result: { ...base.result, left_out: 0, fallback_reason: "model_unavailable" }, knowledge: none }))
      .toBeNull();
  });
});
