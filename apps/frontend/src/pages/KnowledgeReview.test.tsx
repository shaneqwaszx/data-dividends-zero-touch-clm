// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AnswerRecord } from "../aiAssistant";
import KnowledgeReview, { actionFor, age } from "./KnowledgeReview";
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

// D-105: every request is behind a rated conversation; the list and the conversation page
// come from the service like this.
const CONVERSATION_ID = "C".repeat(22);
type Overrides = Record<string, unknown>;

function conversationRow(overrides: Overrides = {}) {
  return {
    conversation_id: CONVERSATION_ID,
    case_id: "case-1",
    title: "Explain the registered address difference",
    created_at: "2026-10-29T01:00:00+00:00",
    updated_at: "2026-10-29T01:05:00+00:00",
    ended_at: "2026-10-29T01:05:00+00:00",
    resolved: false,
    satisfaction: "very_unsatisfied",
    priority: "high",
    review_status: "not_reviewed",
    answers: 1,
    team: "TEAM_A",
    user_id: "maya-lim",
    ...overrides,
  };
}

/** Answers the conversation list and page for ``gap`` (null: no request), else ``rest``. */
function conversations(
  gap: Record<string, unknown> | null,
  rest: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>,
  overrides: Overrides = {},
  detail: Overrides = {},
) {
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/knowledge/conversations?")) {
      return json({ items: [conversationRow(overrides)], total: 1, page: 1, page_size: 10 });
    }
    if (url.endsWith(`/knowledge/conversations/${CONVERSATION_ID}`)) {
      return json({
        ...conversationRow(overrides),
        comment: gap?.note ?? null,
        close_reason: null,
        request: gap,
        draft: null,
        draft_by: null,
        draft_at: null,
        turns: [{ answer_id: "A".repeat(22), created_at: "2026-10-29T01:00:00+00:00", question: "Explain the registered address difference", answer: "I found 1 issue.", notices: [], answered_by: "model" }],
        ...detail,
      });
    }
    return rest(input, init);
  };
}

function backend(calls: { url: string; body: unknown }[], decision = () => json({ ...PENDING, status: "approved" })) {
  return vi.fn(conversations({ id: 7, note: "No proof list.", blocker_codes: [], fields: [], stages: [], created_at: "" }, async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (init?.method === "POST" || init?.method === "PUT") calls.push({ url, body: JSON.parse(String(init.body)) });
    if (init?.method === "DELETE") calls.push({ url, body: null });
    if (url.endsWith("/knowledge/reviews")) return json({ pending: [PENDING], gaps: [] });
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
    if (url.endsWith(`/conversations/${CONVERSATION_ID}/draft`)) {
      return json(init?.method === "DELETE" ? { status: "not_reviewed" } : { status: "draft", draft: JSON.parse(String(init?.body)) });
    }
    if (url.endsWith("/draft")) return json({ ...PENDING, entry_id: "resolution.new", author: "director-dan" });
    return json({}, 404);
  }));
}

function render(): HTMLDivElement {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root?.render(<KnowledgeReview />));
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

/** Open the conversation's page from its row; the section where its fix is written. */
async function openFix(view: HTMLElement, _id: number): Promise<HTMLElement> {
  act(() => view.querySelector<HTMLButtonElement>(`[data-open-conversation="${CONVERSATION_ID}"]`)?.click());
  await flush();
  return view.querySelector('[aria-labelledby="request-page-fix"]') as HTMLElement;
}

describe("KnowledgeReview", () => {
  it("publishes pending knowledge exactly as shown after confirming", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    // D-105: no Waiting for review or Enhancement requests sections; other pending knowledge
    // (such as HR's guidance proposals) is listed only when there is any.
    expect(view.textContent).not.toContain("Waiting for review");
    expect(view.textContent).not.toContain("Enhancement requests");
    expect(view.querySelector(".knowledge-review-pending summary")?.textContent).toBe("Pending knowledge (1)");

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

  it("saves the reviewer's edits as a new version instead of approving", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();

    type(view.querySelector("article input"), "Address differs from ACRA after an office move");
    expect(() => button(view, "Approve")).toThrow();
    act(() => button(view, "Save changes as a new version").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([
      "/knowledge/entries/resolution.abc/versions/1/edit",
    ]);
    expect(calls[0].body).toMatchObject({
      content_hash: "a".repeat(64),
      title: "Address differs from ACRA after an office move",
    });
    expect(view.textContent).toContain("Changes saved as a new version to review.");
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
        if (url.includes("/knowledge/conversations")) return json({ items: [], total: 0, page: 1, page_size: 10 });
        if (url.endsWith("/knowledge/entries")) return json([older, GUIDANCE]);
        return rest(input, init);
      }),
    );
    const view = render();
    await flush();
    const select = view.querySelector("article select") as HTMLSelectElement;
    expect(select.value).toBe("resolution.old");

    choose(select, "");
    act(() => button(view, "Save changes as a new version").click());
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
    const request = await openFix(view, 7);
    expect(button(request, "Close with reason").disabled).toBe(true);
    const reason = request.querySelector(":scope > label input");
    type(reason, "   ");
    expect(button(request, "Close with reason").disabled).toBe(true);
    type(reason, " Covered by the proof-list guidance. ");
    act(() => button(request, "Close with reason").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual(["/knowledge/feedback/7/close"]);
    expect(calls[0].body).toEqual({ reason: "Covered by the proof-list guidance." });
    expect(view.textContent).toContain("Closed with a reason.");
  });

  it("writes the fix as a new rule, then confirms its final text to publish", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    const request = await openFix(view, 7);
    const save = () => button(request, "Save and publish");
    expect(save().disabled).toBe(true);
    const fields = request.querySelectorAll("fieldset input, fieldset textarea");
    type(fields[0], "Proof list for moved offices");
    expect(save().disabled).toBe(true); // no body yet
    type(fields[1], "Ask for the tenancy agreement before changing the address.");
    expect(save().disabled).toBe(true); // a rule needs its source
    type(fields[2], "docs/decisions/DECISION_LOG.md#D-030");
    act(() => save().click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual(["/knowledge/feedback/7/draft"]);
    expect(calls[0].body).toEqual({
      kind: "guidance",
      title: "Proof list for moved offices",
      body: "Ask for the tenancy agreement before changing the address.",
      source_ref: "docs/decisions/DECISION_LOG.md#D-030",
    });
    // Its final text is shown to confirm before it goes live (Support is the single reviewer).
    const confirm = view.querySelector('[aria-label="Confirm publishing"]') as HTMLElement;
    expect(confirm.textContent).toContain("You are its only reviewer");
    act(() => button(view, "Confirm and publish").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([
      "/knowledge/feedback/7/draft",
      "/knowledge/entries/resolution.new/versions/1/decision",
    ]);
    expect(calls[1].body).toMatchObject({ approve: true, confirm_single_reviewer: true });
  });

  it("writes the fix as a change to existing guidance, which needs a source reference", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    const request = await openFix(view, 7);
    choose(request.querySelector("fieldset select"), "edit");
    // Saving waits until the rule to edit is chosen.
    expect(request.querySelectorAll<HTMLSelectElement>("fieldset select")[1].value).toBe("");
    choose(request.querySelectorAll("fieldset select")[1], "guidance.address-mismatch");
    const inputs = () => request.querySelectorAll("fieldset input, fieldset textarea");
    type(inputs()[0], "Address differs from ACRA");
    type(inputs()[1], "Keep the registry address until the client confirms the move.");
    expect(button(request, "Save and publish").disabled).toBe(true); // no source yet
    type(inputs()[2], "docs/decisions/DECISION_LOG.md#D-030");
    act(() => button(request, "Save and publish").click());
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

  it("says so after publishing as the single reviewer", async () => {
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
    const request = await openFix(view, 7);
    type(request.querySelector(":scope > label input"), "Duplicate.");
    act(() => button(view, "Close with reason").click());
    await flush();
    expect(view.querySelector("[role=alert]")?.textContent).toBe("This request was already handled. Refresh and try again.");
  });
});

// D-103: Knowledge review is the Support tab's page, not a modal dialog.
describe("KnowledgeReview page", () => {
  it("renders as a page with a heading and no dialog, backdrop or close button", async () => {
    vi.stubGlobal("fetch", backend([]));
    const view = render();
    await flush();
    expect(view.querySelector("[role=dialog]")).toBeNull();
    expect(view.querySelector(".knowledge-review-backdrop")).toBeNull();
    expect(view.querySelector("[aria-label='Close knowledge review']")).toBeNull();
    expect(view.querySelector("h1")?.textContent).toBe("Knowledge review");
    expect(view.querySelector("section.knowledge-review")?.getAttribute("aria-labelledby"))
      .toBe("knowledge-review-title");
  });

  it("leaves Escape and Tab to the browser on the review queue", async () => {
    vi.stubGlobal("fetch", backend([]));
    const view = render();
    await flush();
    for (const key of ["Escape", "Tab"]) {
      const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
      act(() => { document.dispatchEvent(event); });
      expect(event.defaultPrevented).toBe(false);
    }
    expect(view.textContent).toContain("Knowledge review");
  });

  it("returns focus to the conversation's row after going back from its page", async () => {
    vi.stubGlobal("fetch", backend([]));
    const view = render();
    await flush();
    await openFix(view, 7);
    act(() => { document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); });
    await flush();
    expect(document.activeElement).toBe(view.querySelector(`[data-open-conversation="${CONVERSATION_ID}"]`));
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
  vi.stubGlobal("fetch", vi.fn(conversations(gap, async (input: RequestInfo | URL) => {
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
  }, {}, {})));
}

function openRequestPage(view: HTMLDivElement): void {
  act(() => view.querySelector<HTMLButtonElement>(`[data-open-conversation="${CONVERSATION_ID}"]`)?.click());
}

function openEarlier(view: HTMLElement): HTMLDetailsElement | null {
  const earlier = view.querySelector<HTMLDetailsElement>(".request-page-earlier");
  act(() => {
    if (earlier) {
      earlier.open = true;
      earlier.dispatchEvent(new Event("toggle"));
    }
  });
  return earlier;
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
    const saw = view.querySelector('[aria-labelledby="request-page-saw"]');
    expect(saw?.querySelector(".request-page-question")?.textContent).toBe("Explain the registered address difference");
    expect(saw?.querySelector(".request-page-answer-text")?.textContent).toBe("I found 1 issue stopping the onboarding of [COMPANY].");
    expect(saw?.querySelector(".request-page-notice")?.textContent).toContain("could not be verified");
    expect(saw?.querySelector(".request-page-note")?.textContent).toBe("It did not show the two addresses.");
    // The earlier answers of the chat, folded under the exchange and closed by default: none is
    // fetched (or logged as viewed) until the Director opens them.
    const earlier = saw?.querySelector<HTMLDetailsElement>(".request-page-earlier");
    expect(earlier?.open).toBe(false);
    expect(earlier?.querySelector("summary")?.textContent).toBe("Earlier in this chat (1)");
    expect(earlier?.previousElementSibling?.classList.contains("request-page-exchange")).toBe(true);
    expect(fetched.some((url) => url.includes("/answers/"))).toBe(false);
    openEarlier(view);
    await flush();
    expect(fetched.filter((url) => url.includes("/answers/"))).toHaveLength(1);
    expect(earlier?.textContent).toContain("What should I do next?");
    // The fix is written on the page, below what happened.
    const fix = view.querySelector('[aria-labelledby="request-page-fix"]');
    expect(fix?.querySelector("legend")?.textContent).toBe("Write the fix");
    expect(view.querySelector(".request-page-columns")?.compareDocumentPosition(fix as Node)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    // Back returns to the list, with focus on the row that opened the page.
    act(() => [...view.querySelectorAll("button")].find((b) => b.textContent?.includes("Back to all conversations"))?.click());
    await flush();
    expect(view.querySelector(".knowledge-review-page")).toBeNull();
    expect(document.activeElement).toBe(view.querySelector(`[data-open-conversation="${CONVERSATION_ID}"]`));
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
    expect(allowed?.querySelector("summary")?.textContent).toBe("All rules offered (3)");
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
    expect(view.querySelector(`[data-open-conversation="${CONVERSATION_ID}"]`)?.textContent).toBe("Review");
  });

  it("says a request has no answer record, shows the note, and loads nothing", async () => {
    const fetched: string[] = [];
    reviewWith({ ...GAP, answer_id: null }, fetched);
    const view = render();
    await flush();
    openRequestPage(view);
    await flush();
    expect(view.querySelector(".knowledge-review-page")).not.toBeNull();
    const page = view.querySelector('[aria-labelledby="request-page-no-record"]');
    expect(page?.querySelector("h3")?.textContent).toBe("No answer record for this request");
    expect(page?.querySelector(".request-page-note")?.textContent).toBe("It did not show the two addresses.");
    // No What happened sections, and no record request (so no view is logged).
    expect(view.querySelector('[aria-labelledby="request-page-why"]')).toBeNull();
    expect(view.querySelector('[aria-labelledby="request-page-saw"]')).toBeNull();
    expect(fetched.some((url) => url.includes("/answer"))).toBe(false);
  });
});

describe("The enhancement request queue and page", () => {
  it("lists each rated conversation as one row with its rating, priority, status and action", async () => {
    reviewWith({ ...GAP, answer_id: "A".repeat(22) }, []);
    const view = render();
    await flush();
    const cells = [...view.querySelectorAll(".knowledge-review-table tbody td")].map((cell) => cell.textContent);
    expect(cells.slice(0, 1)).toEqual(["Explain the registered address difference"]);
    expect(cells.slice(2)).toEqual(["No", "Very unsatisfied", "High", "Not reviewed", "Review"]);
    // The fix form is not in the list.
    expect(view.querySelector("fieldset")).toBeNull();
  });

  it("says when an earlier answer is no longer available", async () => {
    const fetched: string[] = [];
    reviewWith({ ...GAP, answer_id: "A".repeat(22) }, fetched, { ...RECORD, earlier_answer_ids: ["C".repeat(22)] });
    const view = render();
    await flush();
    openRequestPage(view);
    await flush();
    const earlier = openEarlier(view);
    await flush();
    expect(earlier?.textContent).toContain("This earlier answer is no longer available.");
  });

  it("shows a record from the first build of answer records without breaking", async () => {
    // Saved before allowed lines were tagged and thresholds recorded (and repaired with no
    // shown answer): the page still renders.
    const early = {
      ...RECORD,
      shown_answer: "",
      allowed_lines: ["Registry and document differences require the current case decision; neither source automatically overrides the other."],
      knowledge: { confidence: null, degraded: null, entries: [] },
    };
    reviewWith({ ...GAP, answer_id: "A".repeat(22) }, [], early);
    const view = render();
    await flush();
    openRequestPage(view);
    await flush();
    const why = view.querySelector('[aria-labelledby="request-page-why"]');
    expect(why?.textContent).toContain("Thresholds: not recorded");
    expect(why?.querySelector(".request-page-allowed summary")?.textContent).toBe("All rules offered (1)");
    expect(why?.querySelectorAll(".request-page-allowed .request-page-tag")).toHaveLength(0);
    expect(view.querySelector(".request-page-answer-text")?.textContent).toBe("The answer text was not kept for this record.");
  });

  it("writes the fix on a request page without a record too", async () => {
    reviewWith({ ...GAP, answer_id: null }, []);
    const view = render();
    await flush();
    openRequestPage(view);
    await flush();
    expect(view.querySelector('[aria-labelledby="request-page-fix"] legend')?.textContent).toBe("Write the fix");
  });
});

describe("A fix started from the AI's answer", () => {
  const START = { title: "Document source conflict", lines: ["Ask [COMPANY] for the tenancy agreement.", "Then check [ADDRESS] on it."] };
  const CURRENT = { ...GUIDANCE, body: "Keep the registry address until the client confirms the move." };

  function prefillBackend(calls: { url: string; body: unknown }[], gap: Record<string, unknown> = { ...GAP, answer_id: "A".repeat(22) }) {
    const fetched: string[] = [];
    vi.stubGlobal("fetch", vi.fn(conversations(gap, async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      fetched.push(url);
      if (init?.method === "POST") calls.push({ url, body: JSON.parse(String(init.body)) });
      if (url.endsWith("/knowledge/reviews")) return json({ pending: [{ ...PENDING, started_from_answer: true }], gaps: [] });
      if (url.endsWith("/knowledge/stats")) return json({ entries: {}, feedback: { total: 1, helpful: 0, not_helpful: 1, helpful_rate: 0, open_gaps: 1 }, by_topic: {} });
      if (url.endsWith("/knowledge/entries")) return json([CURRENT]);
      if (url.endsWith("/knowledge/me")) return json({ user_id: "olivia-koh", can_review: true, can_edit_guidance: false, single_reviewer: true });
      if (url.endsWith("/knowledge/feedback/7/answer")) return json(RECORD);
      if (url.endsWith("/knowledge/feedback/7/fix-start")) return json(START);
      if (url.endsWith("/draft")) return json({ ...PENDING, entry_id: "resolution.new" });
      return json({}, 404);
    })));
    return fetched;
  }

  async function openWithStart(): Promise<HTMLElement> {
    const view = render();
    await flush();
    act(() => view.querySelector<HTMLButtonElement>(`[data-open-conversation="${CONVERSATION_ID}"]`)?.click());
    await flush();
    return view;
  }

  const fixArea = (view: HTMLElement) => view.querySelector('[aria-labelledby="request-page-fix"]') as HTMLElement;
  const bodyOf = (view: HTMLElement) => fixArea(view).querySelectorAll<HTMLTextAreaElement>("fieldset textarea")[0];

  it("prefills the title and the AI's left-out lines, says so and marks the placeholders", async () => {
    const calls: { url: string; body: unknown }[] = [];
    prefillBackend(calls);
    const view = await openWithStart();
    const fix = fixArea(view);
    expect(fix.querySelector<HTMLInputElement>("fieldset input")?.value).toBe("Document source conflict");
    expect(bodyOf(view).value).toBe("Ask [COMPANY] for the tenancy agreement.\nThen check [ADDRESS] on it.");
    expect(fix.querySelector('[role="note"] p')?.textContent).toBe(
      "Started from the AI's answer. Rewrite it as general guidance and remove anything specific to this client.",
    );
    expect([...fix.querySelectorAll(".knowledge-review-placeholders mark")].map((mark) => mark.textContent)).toEqual(["[COMPANY]", "[ADDRESS]"]);
    // Nothing is saved until Save.
    expect(calls).toEqual([]);
  });

  it("does not allow Save while a placeholder is left, and says which to rewrite", async () => {
    const calls: { url: string; body: unknown }[] = [];
    prefillBackend(calls);
    const view = await openWithStart();
    const save = () => button(fixArea(view), "Save and publish");
    expect(fixArea(view).querySelector(".knowledge-review-placeholders")?.textContent).toBe(
      "Rewrite [COMPANY], [ADDRESS] in general terms before saving.",
    );
    expect(save().disabled).toBe(true);
    act(() => save().click());
    await flush();
    expect(calls).toEqual([]);
    // One left (any [UPPERCASE] token counts, in the title too): still not allowed.
    type(bodyOf(view), "Ask the client for the tenancy agreement for the new address.");
    type(fixArea(view).querySelector("fieldset input"), "Lease for [NAME]");
    expect(fixArea(view).querySelector(".knowledge-review-placeholders")?.textContent).toBe(
      "Rewrite [NAME] in general terms before saving.",
    );
    expect(save().disabled).toBe(true);
    // A knowledge tag is not a placeholder.
    type(fixArea(view).querySelector("fieldset input"), "Lease for a moved office [G1]");
    type(fixArea(view).querySelectorAll("fieldset input")[1], "D-030");
    expect(fixArea(view).querySelector(".knowledge-review-placeholders")).toBeNull();
    expect(save().disabled).toBe(false);
  });

  it("records on Save that the fix started from the AI's answer", async () => {
    const calls: { url: string; body: unknown }[] = [];
    prefillBackend(calls);
    const view = await openWithStart();
    type(bodyOf(view), "Ask the client for the tenancy agreement for the new address.");
    type(fixArea(view).querySelectorAll("fieldset input")[1], "D-030");
    act(() => button(fixArea(view), "Save and publish").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual(["/knowledge/feedback/7/draft"]);
    expect(calls[0].body).toEqual({
      kind: "guidance",
      title: "Document source conflict",
      body: "Ask the client for the tenancy agreement for the new address.",
      source_ref: "D-030",
      started_from_answer: true,
    });
  });

  it("Clear empties the form, and a fix saved after it is not marked", async () => {
    const calls: { url: string; body: unknown }[] = [];
    prefillBackend(calls);
    const view = await openWithStart();
    act(() => button(fixArea(view), "Clear").click());
    expect(bodyOf(view).value).toBe("");
    expect(fixArea(view).querySelector('[role="note"]')).toBeNull();
    const inputs = () => fixArea(view).querySelectorAll("fieldset input, fieldset textarea");
    type(inputs()[0], "Proof list for moved offices");
    type(inputs()[1], "Ask for the tenancy agreement before changing the address.");
    type(inputs()[2], "D-030");
    act(() => button(fixArea(view), "Save and publish").click());
    await flush();
    expect(calls[0].body).not.toHaveProperty("started_from_answer");
  });

  it("starts a guidance change from its current title and approved text, with the AI's lines below", async () => {
    prefillBackend([]);
    const view = await openWithStart();
    const title = () => fixArea(view).querySelector<HTMLInputElement>("fieldset input")?.value;
    choose(fixArea(view).querySelector("fieldset select"), "new");
    // A new rule: what the fix was started with, and no rule to choose.
    expect(title()).toBe("Document source conflict");
    expect(bodyOf(view).value).toBe("Ask [COMPANY] for the tenancy agreement.\nThen check [ADDRESS] on it.");
    expect(fixArea(view).querySelectorAll("fieldset select")).toHaveLength(1);
    choose(fixArea(view).querySelector("fieldset select"), "edit");
    expect([...fixArea(view).querySelectorAll("fieldset select")[1].querySelectorAll("option")].map((o) => o.textContent))
      .toEqual(["Choose a rule…", "Registered address differs from ACRA"]);
    choose(fixArea(view).querySelectorAll("fieldset select")[1], "guidance.address-mismatch");
    // Existing guidance keeps its own title, not the blocker type.
    expect(title()).toBe("Registered address differs from ACRA");
    expect(bodyOf(view).value).toBe(
      "Keep the registry address until the client confirms the move.\nAsk [COMPANY] for the tenancy agreement.\nThen check [ADDRESS] on it.",
    );
    // Back to a new rule: the started title and text again.
    choose(fixArea(view).querySelector("fieldset select"), "new");
    expect(title()).toBe("Document source conflict");
    expect(bodyOf(view).value).toBe("Ask [COMPANY] for the tenancy agreement.\nThen check [ADDRESS] on it.");
  });

  it("keeps what the reviewer rewrote when the kind or the guidance changes", async () => {
    prefillBackend([]);
    const view = await openWithStart();
    const title = () => fixArea(view).querySelector<HTMLInputElement>("fieldset input");
    type(bodyOf(view), "Ask the client for the tenancy agreement for the new address.");
    choose(fixArea(view).querySelector("fieldset select"), "edit");
    choose(fixArea(view).querySelectorAll("fieldset select")[1], "guidance.address-mismatch");
    // The rewritten text stays; the untouched title follows the chosen guidance.
    expect(bodyOf(view).value).toBe("Ask the client for the tenancy agreement for the new address.");
    expect(title()?.value).toBe("Registered address differs from ACRA");
    type(title(), "Moved office proof");
    choose(fixArea(view).querySelector("fieldset select"), "resolution");
    expect(title()?.value).toBe("Moved office proof");
  });

  it("has no follow-up questions field and no Flag for developer", async () => {
    prefillBackend([]);
    const view = await openWithStart();
    expect(fixArea(view).textContent).not.toContain("Follow-up questions");
    expect([...fixArea(view).querySelectorAll("button")].map((b) => b.textContent)).not.toContain("Flag for developer");
  });

  it("does not overwrite what the reviewer typed before the start arrived", async () => {
    let arrive: (value: Response) => void = () => undefined;
    const rest = (() => {
      prefillBackend([]);
      return globalThis.fetch;
    })();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
      String(input).endsWith("/fix-start") ? new Promise<Response>((resolve) => { arrive = resolve; }) : rest(input, init),
    ));
    const view = await openWithStart();
    type(fixArea(view).querySelector("fieldset input"), "My own title");
    await act(async () => {
      arrive(json(START));
    });
    await flush();
    expect(fixArea(view).querySelector<HTMLInputElement>("fieldset input")?.value).toBe("My own title");
    expect(bodyOf(view).value).toBe("");
    expect(fixArea(view).querySelector('[role="note"]')).toBeNull();
  });

  it("gives a request without an answer record an empty form and asks for no start", async () => {
    const fetched = prefillBackend([], { ...GAP, answer_id: null });
    const view = await openWithStart();
    expect(bodyOf(view).value).toBe("");
    expect(fixArea(view).querySelector('[role="note"]')).toBeNull();
    expect(fetched.some((url) => url.includes("/fix-start"))).toBe(false);
  });

  it("shows in pending knowledge that a version started from the AI's answer", async () => {
    prefillBackend([]);
    const view = render();
    await flush();
    const card = view.querySelector('[aria-label="Review Draft: Document or reconciliation review required"]');
    expect(card?.querySelector(".knowledge-review-meta")?.textContent).toContain("· started from the AI's answer");
  });
});

// D-105: the conversation list, filters, pages, drafts and the View page.
describe("Rated conversations", () => {
  it("names the action from the priority and review status", () => {
    expect(actionFor({ priority: "high", review_status: "not_reviewed" })).toBe("Review");
    expect(actionFor({ priority: "low", review_status: "draft" })).toBe("Edit draft");
    expect(actionFor({ priority: "medium", review_status: "awaiting_publish" })).toBe("Review");
    expect(actionFor({ priority: "high", review_status: "fixed" })).toBe("View");
    expect(actionFor({ priority: null, review_status: "no_review" })).toBe("View");
  });

  it("sends the filters and the page to the service", async () => {
    const fetched: string[] = [];
    reviewWith({ ...GAP, answer_id: "A".repeat(22) }, []);
    const served = globalThis.fetch;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      fetched.push(String(input));
      return served(input, init);
    }));
    const view = render();
    await flush();
    const [resolved, satisfaction, status] = [...view.querySelectorAll<HTMLSelectElement>(".knowledge-review-filters select")];
    choose(resolved, "false");
    await flush();
    choose(satisfaction, "very_unsatisfied");
    await flush();
    choose(status, "draft");
    await flush();
    const listed = fetched.filter((url) => url.includes("/knowledge/conversations?")).map((url) => url.split("?")[1]);
    expect(listed).toEqual([
      "page=1",
      "page=1&resolved=false",
      "page=1&resolved=false&satisfaction=very_unsatisfied",
      "page=1&resolved=false&satisfaction=very_unsatisfied&status=draft",
    ]);
  });

  it("pages ten at a time", async () => {
    const fetched: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      fetched.push(url);
      if (url.includes("/knowledge/conversations?")) return json({ items: [conversationRow()], total: 23, page: 1, page_size: 10 });
      if (url.endsWith("/knowledge/reviews")) return json({ pending: [], gaps: [] });
      if (url.endsWith("/knowledge/entries")) return json([]);
      if (url.endsWith("/knowledge/me")) return json({ user_id: "support-user", can_review: true, can_edit_guidance: false, single_reviewer: true });
      return json({}, 404);
    }));
    const view = render();
    await flush();
    expect(view.textContent).toContain("Page 1 of 3 · 23 conversations");
    expect(button(view, "Previous").disabled).toBe(true);
    act(() => button(view, "Next").click());
    await flush();
    expect(fetched.filter((url) => url.includes("/knowledge/conversations?")).at(-1)).toContain("page=2");
  });

  it("saves the fix as a draft without publishing it", async () => {
    const calls: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", backend(calls));
    const view = render();
    await flush();
    const request = await openFix(view, 7);
    const fields = request.querySelectorAll("fieldset input, fieldset textarea");
    type(fields[0], "Proof list");
    act(() => button(request, "Save as draft").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([`/knowledge/conversations/${CONVERSATION_ID}/draft`]);
    expect(calls[0].body).toEqual({
      kind: "guidance", title: "Proof list", body: "", follow_ups: [], entry_id: null, source_ref: "",
      blocker_codes: [], fields: [], stages: [],
    });
    expect(view.textContent).toContain("Saved as draft. Edit draft from the list to continue.");
  });

  it("opens a saved draft with Edit draft, prefilled, and can discard it", async () => {
    const calls: { url: string; body: unknown }[] = [];
    const draft = { kind: "guidance", title: "Moved offices", body: "Ask for the lease.", follow_ups: [], entry_id: null, source_ref: "D-030" };
    const rest = backend(calls);
    vi.stubGlobal("fetch", vi.fn(conversations(
      { ...GAP, answer_id: "A".repeat(22) },
      rest,
      { review_status: "draft" },
      { draft, draft_by: "support-user", draft_at: "2026-10-30T02:00:00+00:00" },
    )));
    const view = render();
    await flush();
    expect(view.querySelector(`[data-open-conversation="${CONVERSATION_ID}"]`)?.textContent).toBe("Edit draft");
    expect(view.textContent).toContain("Saved as draft");
    const request = await openFix(view, 7);
    expect(request.querySelector<HTMLSelectElement>("fieldset select")?.value).toBe("new");
    expect(request.querySelector<HTMLInputElement>("fieldset input")?.value).toBe("Moved offices");
    expect(request.textContent).toContain("Draft saved by support-user");
    act(() => button(request, "Discard draft").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([`/knowledge/conversations/${CONVERSATION_ID}/draft`]);
    expect(calls[0].body).toBeNull();
  });

  it("views a conversation with no priority without a fix form", async () => {
    vi.stubGlobal("fetch", vi.fn(conversations(null, backend([]), { priority: null, satisfaction: "satisfied", resolved: true, review_status: "no_review" })));
    const view = render();
    await flush();
    const open = view.querySelector<HTMLButtonElement>(`[data-open-conversation="${CONVERSATION_ID}"]`);
    expect(open?.textContent).toBe("View");
    act(() => open?.click());
    await flush();
    expect(view.querySelector("h1")?.textContent).toBe("View conversation");
    expect(view.querySelector(".knowledge-review-rating")?.textContent).toContain("Satisfied");
    expect(view.querySelector(".knowledge-review-transcript")?.textContent).toContain("I found 1 issue.");
    expect(view.querySelector('[aria-labelledby="request-page-fix"]')).toBeNull();
  });

  it("publishes a fix that was saved earlier but not published", async () => {
    const calls: { url: string; body: unknown }[] = [];
    const saved = { ...PENDING, entry_id: "resolution.saved", key: "resolution.saved@v1" };
    const rest = backend(calls);
    vi.stubGlobal("fetch", vi.fn(conversations(
      { ...GAP, entry_id: "resolution.saved" },
      async (input: RequestInfo | URL, init?: RequestInit) =>
        String(input).endsWith("/knowledge/reviews") ? json({ pending: [saved], gaps: [] }) : rest(input, init),
      { review_status: "awaiting_publish" },
    )));
    const view = render();
    await flush();
    const request = await openFix(view, 7);
    act(() => button(request, "Check and publish").click());
    act(() => button(view, "Confirm and publish").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual(["/knowledge/entries/resolution.saved/versions/1/decision"]);
  });
});

// D-105 point 5: investigate the case, edit how the AI responds, try it, or flag a developer.
describe("Editing how the AI should respond", () => {
  function point5Backend(calls: { url: string; body: unknown }[]) {
    const rest = backend(calls);
    vi.stubGlobal("fetch", vi.fn(conversations(
      { ...GAP, answer_id: "A".repeat(22) },
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/knowledge/feedback/7/answer")) return json(RECORD);
        if (url.endsWith(`/conversations/${CONVERSATION_ID}/try`)) {
          calls.push({ url, body: JSON.parse(String(init?.body)) });
          return json({ question: "Explain the registered address difference", answer: "Ask the client for the lease. [G2]", answered_by: "model", notice: null, tag: "G2", offered_lines: ["Ask the client for the lease. [G2]"], used: true });
        }
        if (url.endsWith("/cases/case-1/chat")) {
          calls.push({ url, body: JSON.parse(String(init?.body)) });
          return json({ answer: "ACRA shows the old address.", answered_by: "model", model: "m", notice: null, suggested_questions: [] });
        }
        return rest(input, init);
      },
    )));
  }

  it("shows the information and rules used folded, and says only the rules change", async () => {
    point5Backend([]);
    const view = render();
    await flush();
    await openFix(view, 7);
    const why = view.querySelector('[aria-labelledby="request-page-why"]');
    expect(why?.querySelector("h3")?.textContent).toBe("Information / rules used");
    const parts = [...(why?.querySelectorAll<HTMLDetailsElement>("details.request-page-part") ?? [])];
    expect(parts.map((part) => part.querySelector("summary")?.textContent)).toEqual([
      "How it was answered",
      "Lines shown to the user (0)",
      "Lines the guard left out (1)",
      "Knowledge found (1)",
      "All rules offered (3)",
      "The case at the time",
    ]);
    expect(parts.every((part) => !part.open)).toBe(true);
    const fix = view.querySelector('[aria-labelledby="request-page-fix"]');
    expect(fix?.querySelector("h3")?.textContent).toBe("Edit how the AI should respond");
    expect(fix?.textContent).toContain("No case, case data or onboarding logic is changed.");
  });

  it("opens the AI Assistant on the conversation's case with the user's question", async () => {
    point5Backend([]);
    const asked: [string, string][] = [];
    let left = 0;
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root?.render(<KnowledgeReview onAskAboutCase={(caseId, question) => asked.push([caseId, question])} onLeaveCase={() => { left += 1; }} />));
    const view = container;
    await flush();
    await openFix(view, 7);
    // No chat card on the page: the AI Assistant panel is used.
    expect(view.querySelector('[aria-labelledby="support-case-chat-title"]')).toBeNull();
    act(() => button(view, "Ask the AI Assistant about this case").click());
    expect(asked).toEqual([["case-1", "Explain the registered address difference"]]);
    act(() => [...view.querySelectorAll("button")].find((b) => b.textContent?.includes("Back to all conversations"))?.click());
    await flush();
    expect(left).toBe(1);
  });

  it("tries a rule change and shows the answer before and after, saving nothing", async () => {
    const calls: { url: string; body: unknown }[] = [];
    point5Backend(calls);
    const view = render();
    await flush();
    const request = await openFix(view, 7);
    choose(request.querySelector("fieldset select"), "new");
    const inputs = () => request.querySelectorAll("fieldset input, fieldset textarea");
    type(inputs()[0], "Moved offices");
    type(inputs()[1], "Ask the client for the lease.");
    type(inputs()[3], "DOCUMENT_SOURCE_CONFLICT, ADDRESS_MISMATCH");
    act(() => button(request, "Try with this change").click());
    await flush();
    expect(calls.map((call) => call.url.split("/api/assistant")[1])).toEqual([`/knowledge/conversations/${CONVERSATION_ID}/try`]);
    expect(calls[0].body).toEqual({
      kind: "guidance", title: "Moved offices", body: "Ask the client for the lease.", entry_id: null,
      blocker_codes: ["DOCUMENT_SOURCE_CONFLICT", "ADDRESS_MISMATCH"],
    });
    const trial = view.querySelector('[aria-label="Try with this change"]');
    expect(trial?.textContent).toContain("Before (what the user saw)I found 1 issue.");
    expect(trial?.textContent).toContain("After (with this change)Ask the client for the lease. [G2]");
    expect(trial?.textContent).toContain("The answer used this change (1 sentence offered).");
    // The same tags go with the fix when it is saved.
    type(inputs()[2], "D-030");
    act(() => button(request, "Save and publish").click());
    await flush();
    expect(calls[1].body).toMatchObject({ kind: "guidance", blocker_codes: ["DOCUMENT_SOURCE_CONFLICT", "ADDRESS_MISMATCH"] });
  });
});

describe("age", () => {
  it("says how many whole days ago a request was made", () => {
    const now = Date.parse("2026-10-25T12:00:00Z");
    expect(age("2026-10-25T01:00:00Z", now)).toBe("today");
    expect(age("2026-10-24T11:00:00Z", now)).toBe("1 day ago");
    expect(age("2026-10-20T12:00:00Z", now)).toBe("5 days ago");
    expect(age("", now)).toBe("age unknown");
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
