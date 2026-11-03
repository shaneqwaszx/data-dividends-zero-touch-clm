// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import AiAssistantPanel, { AnswerActivity } from "./AiAssistantPanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// jsdom has no ResizeObserver (assistant-ui uses it to keep the newest message in view).
class TestResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: typeof TestResizeObserver }).ResizeObserver ??= TestResizeObserver;
// jsdom elements cannot scroll either.
Element.prototype.scrollTo ??= function scrollTo() {};

type FetchImpl = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

/** Answers the review-permission check, and passes every other request to the test's fetch. */
function stubFetch(impl: FetchImpl, access = { user_id: "maya-lim", can_review: false, can_edit_guidance: false }): void {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
      String(input).endsWith("/api/assistant/knowledge/me")
        ? Promise.resolve(new Response(JSON.stringify(access), { status: 200, headers: { "Content-Type": "application/json" } }))
        : impl(input, init),
    ),
  );
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function flush(): Promise<void> {
  for (let i = 0; i < 5; i += 1) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

const noop = () => undefined;

function render(caseId: string | null, onOpenCases: () => void = noop, canChatWithoutCase = false): HTMLDivElement {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root?.render(<AiAssistantPanel caseId={caseId} onOpenCases={onOpenCases} canChatWithoutCase={canChatWithoutCase} />));
  return container;
}

function typeInto(field: Element | null, value: string): void {
  const box = field as HTMLTextAreaElement;
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set?.call(box, value);
    box.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function buttonNamed(view: HTMLElement, text: string): HTMLButtonElement | undefined {
  return [...view.querySelectorAll("button")].find((b) => b.textContent?.trim() === text);
}

function choiceLabels(fieldset: Element | null | undefined): string[] {
  return [...(fieldset?.querySelectorAll("label") ?? [])].map((label) => label.textContent?.trim() ?? "");
}

function rerender(caseId: string | null): void {
  act(() => root?.render(<AiAssistantPanel caseId={caseId} onOpenCases={noop} />));
}

function click(element: Element | null | undefined): void {
  if (!element) throw new Error("missing element");
  act(() => (element as HTMLElement).click());
}

function brief(company: string, message: string) {
  return { company, message, suggested_questions: ["Why is this case blocked?"], blocker_count: 1, steps_done: 5, steps_total: 12 };
}

function ndjsonStream(): { response: Response; send: (event: unknown) => void; end: () => void } {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({ start: (c) => { controller = c; } });
  const encoder = new TextEncoder();
  return {
    response: new Response(body, { status: 200, headers: { "Content-Type": "application/x-ndjson" } }),
    send: (event) => controller.enqueue(encoder.encode(`${JSON.stringify(event)}\n`)),
    end: () => controller.close(),
  };
}

const ANSWER_ID = "A".repeat(22);
const CONVERSATION_ID = "C".repeat(22);

describe("AiAssistantPanel", () => {
  it("shows the answer while it is being written, then the final answer", async () => {
    const stream = ndjsonStream();
    const sent: unknown[] = [];
    stubFetch(vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        sent.push(JSON.parse(String(init?.body)));
        return stream.response;
      }
      return json({}, 404);
    }));

    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    // The reply has started (the service read the case): that stage is done, the model is awaited.
    expect(view.textContent).toContain("✓ Preparing case information");
    expect(view.textContent).toContain("Checking model readiness and waiting for the answer");
    expect(view.textContent).not.toContain("Thinking");

    stream.send({ type: "text", text: "Keep the registry value." });
    await flush();
    expect(view.textContent).toContain("Keep the registry value.");
    expect(view.textContent).toContain("✓ Checking model readiness and waiting for the answer");
    expect(view.textContent).toContain("Showing lines that passed the check");
    expect(view.querySelector("textarea + button")?.hasAttribute("disabled")).toBe(true);

    stream.send({
      type: "done",
      answer: "Keep the registry value. Then upload ownership evidence.",
      answered_by: "model",
      model: "ministral-3:8b",
      notice: null,
      suggested_questions: ["Where are we now?"],
    });
    stream.end();
    await flush();
    expect(view.textContent).toContain("Then upload ownership evidence.");
    expect(view.querySelectorAll(".ai-assistant-assistant")).toHaveLength(2);
    expect(view.textContent).toContain("Where are we now?");
    // Answer ready: the progress stages are gone, and there is no "What this answer used" (D-105).
    expect(view.querySelector(".ai-assistant-activity")).toBeNull();
    expect(view.querySelector(".ai-assistant-used")).toBeNull();
    expect(view.textContent).not.toContain("What this answer used");

    // The next question sends the earlier exchange, but not the opening summary.
    act(() => {
      const box = view.querySelector("textarea") as HTMLTextAreaElement;
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
      setter?.call(box, "And after that?");
      box.dispatchEvent(new Event("input", { bubbles: true }));
    });
    click(view.querySelector(".ai-assistant-send"));
    await flush();
    expect(sent[1]).toEqual({
      message: "And after that?",
      history: [
        { role: "user", content: "Why is this case blocked?" },
        { role: "assistant", content: "Keep the registry value. Then upload ownership evidence." },
      ],
    });
  });

  it("opens with the case brief and answers a suggested question", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/assistant/cases/case-1/brief") {
        return json(brief("GARDEN BUSINESS", "I found 1 issue stopping the onboarding of GARDEN BUSINESS:"));
      }
      if (url === "/api/assistant/cases/case-1/chat/stream") {
        const body = JSON.parse(String(init?.body));
        expect(body.message).toBe("Why is this case blocked?");
        // The opening summary is not sent back: the service re-reads the case anyway.
        expect(body.history).toEqual([]);
        return json({
          answer: "The document address differs from ACRA.",
          answered_by: "case_data",
          model: null,
          notice: "The AI model is not available, so this answer comes straight from the case data.",
          suggested_questions: ["What should I do next?"],
        });
      }
      return json({}, 404);
    });
    stubFetch(fetchMock);

    const view = render("case-1");
    await flush();
    expect(fetchMock).not.toHaveBeenCalled();
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "GET", credentials: "include" });
    expect(view.textContent).toContain("I found 1 issue stopping the onboarding of GARDEN BUSINESS");
    expect(view.querySelector(".ai-assistant-subtitle")?.textContent).toBe("GARDEN BUSINESS · read-only");

    click([...view.querySelectorAll(".ai-assistant-chip")].find((b) => b.textContent === "Why is this case blocked?"));
    await flush();

    expect(view.textContent).toContain("The document address differs from ACRA.");
    expect(view.textContent).toContain("comes straight from the case data");
    expect(view.textContent).toContain("What should I do next?");
  });

  it("only explains the case on screen and keeps each case's conversation", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/assistant/cases/case-1/brief") return json(brief("GARDEN BUSINESS", "About Garden."));
      if (url === "/api/assistant/cases/case-2/brief") return json(brief("MERLION", "About Merlion."));
      return json({}, 404);
    });
    stubFetch(fetchMock);

    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    expect(view.textContent).toContain("About Garden.");

    rerender(null);
    await flush();
    expect(view.querySelector(".ai-assistant-panel")).not.toBeNull();
    expect(view.querySelector(".ai-assistant-panel-compact")).not.toBeNull();
    expect(view.textContent).toContain("Open a case and I'll explain");
    expect(view.textContent).not.toContain("About Garden.");
    expect(view.querySelector("textarea")).toBeNull();

    rerender("case-2");
    await flush();
    expect(view.textContent).toContain("About Merlion.");

    rerender("case-1");
    await flush();
    expect(view.textContent).toContain("About Garden.");
    expect(view.textContent).not.toContain("About Merlion.");
    expect(fetchMock.mock.calls.every(([url]) => String(url).includes("/cases/"))).toBe(true);
  });

  it("asks the RM to open a case when none has been opened", async () => {
    const fetchMock = vi.fn(async () => json({}, 404));
    stubFetch(fetchMock);
    const onOpenCases = vi.fn();

    const view = render(null, onOpenCases);
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();

    expect(view.textContent).toContain("Open a case and I'll explain where it stands");
    expect(view.querySelector("textarea")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
    click(view.querySelector(".ai-assistant-open-cases"));
    expect(onOpenCases).toHaveBeenCalledTimes(1);
  });

  it("asks for the company details on New onboarding before the case exists", async () => {
    const fetchMock = vi.fn(async () => json({}, 404));
    stubFetch(fetchMock);
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root?.render(<AiAssistantPanel caseId={null} onboardingWithoutCase onOpenCases={noop} />));
    click(container.querySelector(".ai-assistant-launcher"));
    await flush();

    expect(container.textContent).toContain("Enter the company's details to start");
    expect(container.querySelector(".ai-assistant-open-cases")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("explains when the AI assistant service is not running", async () => {
    stubFetch(vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();

    expect(view.querySelector("[role=alert]")?.textContent).toBe("The AI assistant service is not running.");
  });


  it("removes retained case conversation when the backend says the case is inaccessible", async () => {
    let count = 0;
    stubFetch(vi.fn(async () => {
      count += 1;
      return count === 1 ? json(brief("OLD CASE", "Previously accessible case summary."))
        : json({ detail: { message: "This case was not found." } }, 404);
    }));
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    expect(view.textContent).toContain("Previously accessible case summary.");
    click(view.querySelector('[aria-label="Refresh the summary"]'));
    await flush();
    expect(view.querySelector("[role=alert]")?.textContent).toBe("This case was not found.");
    expect(view.textContent).not.toContain("Previously accessible case summary.");
    expect(view.querySelector(".ai-assistant-subtitle")?.textContent).not.toContain("OLD CASE");
  });

  it("does not publish an aborted earlier brief over the current evidence refresh", async () => {
    const pending: ((response: Response) => void)[] = [];
    stubFetch(vi.fn(() => new Promise<Response>((resolve) => pending.push(resolve))));
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector('[aria-label="Refresh the summary"]'));
    await flush();
    pending[0](json(brief("OLD CASE", "Old classification is ready.")));
    await flush();
    expect(view.textContent).not.toContain("Old classification is ready.");
    pending[1](json(brief("CURRENT CASE", "Current classification requires conflict review.")));
    await flush();
    expect(view.textContent).toContain("Current classification requires conflict review.");
  });

  it.each(["brief", "chat"])("does not restore inaccessible conversation from a late peer after %s returns 404", async (denied) => {
    const briefs: { resolve: (response: Response) => void; signal: AbortSignal }[] = [];
    let chat: { resolve: (response: Response) => void; signal: AbortSignal } | undefined;
    let briefCount = 0;
    stubFetch(vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      // D-115: a service without chat contexts; the chat then sends its history as before.
      if (String(input).endsWith("/contexts")) return Promise.resolve(json({}, 404));
      if (String(input).endsWith("/brief")) {
        briefCount += 1;
        if (briefCount === 1) return Promise.resolve(json(brief("OLD CASE", "Previously accessible summary.")));
        return new Promise<Response>((resolve) => briefs.push({ resolve, signal: init?.signal as AbortSignal }));
      }
      return new Promise<Response>((resolve) => { chat = { resolve, signal: init?.signal as AbortSignal }; });
    }));
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    click(view.querySelector('[aria-label="Refresh the summary"]'));
    await flush();
    if (!chat) throw new Error("missing pending chat");
    const inaccessible = json({ detail: { message: "This case was not found." } }, 404);
    (denied === "brief" ? briefs[0] : chat).resolve(inaccessible);
    await flush();
    expect(view.textContent).not.toContain("Previously accessible summary.");
    const peer = denied === "brief" ? chat : briefs[0];
    peer.resolve(denied === "brief"
      ? json({ answer: "Late inaccessible answer.", answered_by: "case_data", model: null, notice: null, suggested_questions: [] })
      : json(brief("OLD CASE", "Late inaccessible summary.")));
    await flush();
    expect(view.textContent).not.toContain("Late inaccessible");
    expect(view.querySelector(".ai-assistant-subtitle")?.textContent).not.toContain("OLD CASE");
    expect(peer.signal.aborted).toBe(true);
    expect(view.textContent).not.toContain("Thinking");
    expect(view.querySelector("[role=alert]")?.textContent).toBe("This case was not found.");

    click(view.querySelector('[aria-label="Refresh the summary"]'));
    await flush();
    briefs[1].resolve(json(brief("CURRENT CASE", "Fresh authorized summary.")));
    await flush();
    expect(view.textContent).toContain("Fresh authorized summary.");
    expect(view.querySelector("[role=alert]")).toBeNull();
  });

  it("shows cited sources and no per-answer helpful buttons (D-105)", async () => {
    stubFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        return new Response(
          `${JSON.stringify({
            type: "done",
            answer: "Only Keep registry value is offered [G1].",
            answered_by: "model",
            model: "m",
            notice: null,
            suggested_questions: [],
            sources: [
              { tag: "G1", kind: "guidance", version: 1, title: "Registered address differs from ACRA", approved_at: null, illustrative: false, fallback: false, cited: true },
              { tag: "P1", kind: "resolution", version: 1, title: "Not cited", approved_at: null, illustrative: true, fallback: false, cited: false },
            ],
          })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      return json({}, 404);
    });

    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();

    const sources = view.querySelector('[aria-label="Sources"]');
    expect(sources?.textContent).toContain("G1");
    expect(sources?.textContent).toContain("Registered address differs from ACRA");
    expect(sources?.textContent).not.toContain("Not cited");
    expect(buttonNamed(view, "Yes, helpful")).toBeUndefined();
    expect(buttonNamed(view, "Not helpful")).toBeUndefined();
  });

  it("keeps the conversation and sends it, with the earlier answer ids, on the next question", async () => {
    const asked: Record<string, unknown>[] = [];
    const ids = [ANSWER_ID, "B".repeat(22)];
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        asked.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
        return new Response(
          `${JSON.stringify({ type: "done", answer: `Answer ${asked.length}.`, answered_by: "model", model: "m", notice: null, suggested_questions: ["Next?"], answer_id: ids[asked.length - 1], conversation_id: CONVERSATION_ID })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      return json({}, 404);
    });
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    expect(asked[0].earlier_answer_ids).toBeUndefined();
    expect(asked[0].conversation_id).toBeUndefined();
    expect(asked[1].earlier_answer_ids).toEqual([ANSWER_ID]);
    expect(asked[1].conversation_id).toBe(CONVERSATION_ID);
  });

  it("ends the conversation with the feedback form: resolved first, then the ratings it allows", async () => {
    const ended: unknown[] = [];
    const asked: Record<string, unknown>[] = [];
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        asked.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
        return new Response(
          `${JSON.stringify({ type: "done", answer: "Keep the registry value.", answered_by: "model", model: "m", notice: null, suggested_questions: ["Why?"], answer_id: ANSWER_ID, conversation_id: CONVERSATION_ID })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      if (url.endsWith(`/conversations/${CONVERSATION_ID}/end`)) {
        ended.push(JSON.parse(String(init?.body)));
        return json({ conversation_id: CONVERSATION_ID, message: "Thanks. Your feedback has been sent so the answers can be improved." });
      }
      return json({}, 404);
    });
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    // Nothing to rate before an answer.
    expect(buttonNamed(view, "End conversation")).toBeUndefined();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    click(buttonNamed(view, "End conversation"));
    await flush();

    const form = view.querySelector('form[aria-label="End conversation"]');
    const fieldsets = () => [...(form?.querySelectorAll("fieldset") ?? [])];
    expect(fieldsets().map((item) => item.querySelector("legend")?.textContent)).toEqual(["Was this issue resolved?"]);
    const submit = () => buttonNamed(view, "Submit and end");
    expect(submit()?.disabled).toBe(true);

    // Yes: very satisfied, satisfied or neutral, and optional comments.
    click(fieldsets()[0].querySelectorAll("input")[0]);
    expect(choiceLabels(fieldsets()[1])).toEqual(["Very satisfied", "Satisfied", "Neutral"]);
    expect(form?.querySelector(".ai-assistant-end-comment")?.textContent).toContain("Additional comments (optional)");
    click(fieldsets()[1].querySelectorAll("input")[0]); // very satisfied
    expect(submit()?.disabled).toBe(false);

    // No: neutral, unsatisfied or very unsatisfied; "very satisfied" is no longer chosen; the
    // improvement text is required.
    click(fieldsets()[0].querySelectorAll("input")[1]);
    expect(choiceLabels(fieldsets()[1])).toEqual(["Neutral", "Unsatisfied", "Very unsatisfied"]);
    expect([...fieldsets()[1].querySelectorAll("input")].some((input) => (input as HTMLInputElement).checked)).toBe(false);
    expect(form?.querySelector(".ai-assistant-end-comment")?.textContent).toContain("How should it be improved?");
    click(fieldsets()[1].querySelectorAll("input")[2]); // very unsatisfied
    expect(submit()?.disabled).toBe(true);
    typeInto(form?.querySelector("textarea") ?? null, "  Show the two addresses. ");
    expect(submit()?.disabled).toBe(false);
    click(submit());
    await flush();

    expect(ended).toEqual([{ resolved: false, satisfaction: "very_unsatisfied", comment: "Show the two addresses." }]);
    expect(view.textContent).toContain("Thanks. Your feedback has been sent so the answers can be improved.");
    // The chat starts again: no End conversation until the next answer, and a new conversation.
    expect(buttonNamed(view, "End conversation")).toBeUndefined();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    expect(asked[1].conversation_id).toBeUndefined();
  });

  it("reopens a past chat from History in the same chat, to continue it", async () => {
    const asked: Record<string, unknown>[] = [];
    const opened: string[] = [];
    const past = (caseId: string, ended: boolean) => ({
      conversation_id: CONVERSATION_ID, case_id: caseId, title: "Why is this case blocked?", created_at: "2026-10-30T01:00:00+00:00", updated_at: "2026-10-30T01:05:00+00:00", ended_at: ended ? "2026-10-30T01:05:00+00:00" : null, resolved: ended ? true : null, satisfaction: ended ? "satisfied" : null, priority: null, review_status: ended ? "no_review" : "open", answers: 1, team: "TEAM_A", user_id: "maya-lim", comment: null,
      turns: [{ answer_id: ANSWER_ID, created_at: "2026-10-30T01:00:00+00:00", question: "Why is this case blocked?", answer: "[COMPANY] needs ownership evidence.", notices: [], answered_by: "model" }],
    });
    let detail = past("case-1", true);
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/conversations?page=1")) {
        const { comment: _c, turns: _t, ...row } = detail;
        return json({ items: [row], total: 1, page: 1, page_size: 10 });
      }
      if (url.endsWith(`/conversations/${CONVERSATION_ID}`)) return json(detail);
      if (url.endsWith("/chat/stream")) {
        asked.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
        return new Response(
          `${JSON.stringify({ type: "done", answer: "Upload it under Ownership.", answered_by: "model", model: "m", notice: null, suggested_questions: [], answer_id: "B".repeat(22), conversation_id: "D".repeat(22) })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      return json({}, 404);
    });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root?.render(<AiAssistantPanel caseId="case-1" onOpenCases={noop} onOpenCase={(id) => opened.push(id)} />));
    const view = container;
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(buttonNamed(view, "History"));
    await flush();
    const item = view.querySelector(".ai-assistant-history-item");
    expect(item?.textContent).toContain("Why is this case blocked?");
    expect(item?.textContent).toContain("Satisfied");
    click(item);
    await flush();
    // Back in the chat with the past exchange, and the composer to continue.
    expect(view.textContent).toContain("[COMPANY] needs ownership evidence.");
    expect(view.textContent).toContain("You rated this chat. New questions continue it as a new conversation.");
    expect(view.querySelector("textarea")).not.toBeNull();
    expect(opened).toEqual([]); // same case: no navigation
    typeInto(view.querySelector("textarea"), "Where do I upload it?");
    click(view.querySelector(".ai-assistant-send"));
    await flush();
    // A rated chat continues as a new conversation, with the past exchange as context.
    expect(asked[0].conversation_id).toBeUndefined();
    expect(asked[0].history).toEqual([
      { role: "user", content: "Why is this case blocked?" },
      { role: "assistant", content: "[COMPANY] needs ownership evidence." },
    ]);
    expect(asked[0].earlier_answer_ids).toEqual([ANSWER_ID]);

    // An open chat about another case continues as itself, on that case's page.
    detail = past("case-2", false);
    click(buttonNamed(view, "History"));
    await flush();
    click(view.querySelector(".ai-assistant-history-item"));
    await flush();
    expect(opened).toEqual(["case-2"]);
  });

  it("opens on the case Support asked about, with the user's question first (D-105)", async () => {
    stubFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/cases/case-9/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      return json({}, 404);
    });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    const panel = (nonce: number) => (
      <AiAssistantPanel caseId="case-9" onOpenCases={noop} canChatWithoutCase askAbout={{ caseId: "case-9", question: "Explain the address difference", nonce }} />
    );
    act(() => root?.render(panel(1)));
    await flush();
    // Opened by itself, on the case, with the user's question as the first suggestion.
    expect(container.querySelector(".ai-assistant-launcher")).toBeNull();
    expect(container.textContent).toContain("Summary of Garden.");
    expect([...container.querySelectorAll(".ai-assistant-chip")].map((chip) => chip.textContent)).toEqual([
      "Explain the address difference",
      "Why is this case blocked?",
    ]);
    // Support keeps no history and has nothing to rate.
    expect(buttonNamed(container, "History")).toBeUndefined();
    expect(buttonNamed(container, "End conversation")).toBeUndefined();
  });

  it("lets Support chat about the rules and policy without a case (D-105)", async () => {
    const sent: unknown[] = [];
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/support/chat")) {
        sent.push(JSON.parse(String(init?.body)));
        return json({ answer: "UBO threshold: 25. [ownership.ubo_threshold_percent]", answered_by: "model", model: "m", notice: null, suggested_questions: [] });
      }
      return json({}, 404);
    });
    const view = render(null, noop, true);
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    expect(view.textContent).toContain("Ask me about the approved rules");
    expect(view.textContent).not.toContain("Go to Cases");
    expect(buttonNamed(view, "History")).toBeUndefined();
    typeInto(view.querySelector("textarea"), "What is the UBO threshold?");
    click(view.querySelector(".ai-assistant-send"));
    await flush();
    expect(sent).toEqual([{ message: "What is the UBO threshold?", history: [] }]);
    expect(view.textContent).toContain("UBO threshold: 25.");
    expect(buttonNamed(view, "End conversation")).toBeUndefined();
  });

  it("labels a case-data answer as not AI-generated where it is read (D-098)", async () => {
    const reply = (answeredBy: string, smallTalk = false) => async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        return new Response(
          `${JSON.stringify({ type: "done", answer: "From ACRA (MOCK).", answered_by: answeredBy, model: answeredBy === "model" ? "openai/gpt-oss-120b" : null, notice: null, suggested_questions: [], answer_id: null, small_talk: smallTalk })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      return json({}, 404);
    };
    for (const [answeredBy, smallTalk, labelled] of [["case_data", false, true], ["model", false, false], ["case_data", true, false]] as const) {
      stubFetch(reply(answeredBy, smallTalk));
      const view = render("case-1");
      click(view.querySelector(".ai-assistant-launcher"));
      await flush();
      click(view.querySelector(".ai-assistant-chip"));
      await flush();
      const label = view.querySelector("[data-testid=case-data-label]");
      expect(Boolean(label)).toBe(labelled);
      if (labelled) expect(label?.textContent).toContain("Case-data guidance, not AI-generated.");
      act(() => root?.unmount());
      root = null;
    }
  });

  it("no longer opens Knowledge review, even for someone the backend allows to review (D-103)", async () => {
    const fetched: string[] = [];
    stubFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      fetched.push(url);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary."));
      return json({}, 404);
    }, { user_id: "support-user", can_review: true, can_edit_guidance: false });
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    expect(view.querySelector(".ai-assistant-review-open")).toBeNull();
    expect(view.querySelector('[role="dialog"]')).toBeNull();
    // The Knowledge Review tab owns review; the panel does not ask who may review.
    expect(fetched.some((url) => url.endsWith("/knowledge/me"))).toBe(false);
  });
});

// Text as a reader sees it (tags between the mark and its label removed).
function shown(element: Parameters<typeof renderToStaticMarkup>[0]): string {
  const holder = document.createElement("div");
  holder.innerHTML = renderToStaticMarkup(element);
  return holder.textContent ?? "";
}

describe("AiAssistantPanel answer progress and summary", () => {
  it("shows only observed stages: before the reply starts nothing is marked done", () => {
    const html = shown(<AnswerActivity activity={{ startedAt: 0, connected: false }} writing={false} now={2_500} />);
    expect(html).toContain("… Preparing case information");
    expect(html).not.toContain("✓");
    expect(html).not.toContain("Checking model readiness");
    expect(html).not.toContain("%");
    expect(html).toContain("2.5 s");
  });

  it("marks a stage done only after the event that ends it", () => {
    const waiting = shown(<AnswerActivity activity={{ startedAt: 0, connected: true }} writing={false} now={12_400} />);
    expect(waiting).toContain("✓ Preparing case information");
    expect(waiting).toContain("… Checking model readiness and waiting for the answer");
    expect(waiting).toContain("12 s");
    const showing = shown(<AnswerActivity activity={{ startedAt: 0, connected: true }} writing now={13_000} />);
    expect(showing).toContain("✓ Checking model readiness and waiting for the answer");
    expect(showing).toContain("… Showing lines that passed the check");
  });
});

describe("AiAssistantPanel case memory (D-115)", () => {
  const CONTEXT_A = "a".repeat(32);
  const CONTEXT_B = "b".repeat(32);
  const done = (answer: string) => new Response(
    `${JSON.stringify({ type: "done", answer, answered_by: "model", model: "m", notice: null, suggested_questions: ["Next?"] })}\n`,
    { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
  );

  function server(log: { url: string; body: Record<string, unknown> | null; keepalive?: boolean }[]) {
    let opened = 0;
    return async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      log.push({ url, body: init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : null, keepalive: init?.keepalive });
      if (url.endsWith("/brief")) return json(brief(url.includes("case-2") ? "MERLION" : "GARDEN BUSINESS", "Summary."));
      if (url.endsWith("/api/assistant/contexts")) {
        opened += 1;
        return json({ context_id: opened === 1 ? CONTEXT_A : CONTEXT_B, scope: "case", case_id: null, idle_seconds: 1800 });
      }
      if (url.includes("/contexts/") && url.endsWith("/close")) return new Response(null, { status: 204 });
      if (url.endsWith("/chat/stream")) return done("Answer.");
      return json({}, 404);
    };
  }

  it("opens a context on the first question, sends no history text, and closes it when the case is left", async () => {
    const log: { url: string; body: Record<string, unknown> | null; keepalive?: boolean }[] = [];
    stubFetch(server(log));
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    expect(log.some((item) => item.url.endsWith("/contexts"))).toBe(false);  // nothing until a question
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    const asks = log.filter((item) => item.url.endsWith("/chat/stream"));
    expect(asks.map((item) => item.body?.context_id)).toEqual([CONTEXT_A, CONTEXT_A]);
    expect(asks[1].body?.history).toEqual([]);
    expect(log.filter((item) => item.url.endsWith("/api/assistant/contexts"))).toHaveLength(1);
    expect(log.find((item) => item.url.endsWith("/api/assistant/contexts"))?.body).toEqual({ case_id: "case-1" });

    rerender("case-2");
    await flush();
    const close = log.find((item) => item.url.endsWith(`/contexts/${CONTEXT_A}/close`));
    expect(close?.keepalive).toBe(true);
    expect(view.textContent).not.toContain("Answer.");  // case-1's chat is gone here
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    const later = log.filter((item) => item.url.endsWith("/chat/stream")).at(-1);
    expect(later?.url).toContain("/cases/case-2/");
    expect(later?.body?.context_id).toBe(CONTEXT_B);

    rerender("case-1");  // coming back starts afresh
    await flush();
    expect(view.textContent).not.toContain("Answer.");
  });

  it("closes every open context when the panel unmounts (sign-out, user change) or the page is hidden", async () => {
    const log: { url: string; body: Record<string, unknown> | null; keepalive?: boolean }[] = [];
    stubFetch(server(log));
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    act(() => window.dispatchEvent(new Event("pagehide")));
    expect(log.some((item) => item.url.endsWith(`/contexts/${CONTEXT_A}/close`))).toBe(true);
  });

  it("ignores a late answer for a case that was left", async () => {
    let finish: ((response: Response) => void) | undefined;
    stubFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary."));
      if (url.endsWith("/api/assistant/contexts")) return json({ context_id: CONTEXT_A, scope: "case", case_id: "case-1", idle_seconds: 1800 });
      if (url.endsWith("/close")) return new Response(null, { status: 204 });
      if (url.endsWith("/chat/stream")) return await new Promise<Response>((resolve) => { finish = resolve; });
      return json({}, 404);
    });
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    rerender("case-2");
    await flush();
    finish?.(done("LATE CASE-1 ANSWER."));
    await flush();
    expect(view.textContent).not.toContain("LATE CASE-1 ANSWER.");
  });

  it("starts a new chat when the service says the context ended", async () => {
    stubFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary."));
      if (url.endsWith("/api/assistant/contexts")) return json({ context_id: CONTEXT_A, scope: "case", case_id: "case-1", idle_seconds: 1800 });
      if (url.endsWith("/close")) return new Response(null, { status: 204 });
      if (url.endsWith("/chat/stream")) return json({ detail: { code: "CONTEXT_UNKNOWN", message: "This chat has ended." } }, 409);
      return json({}, 404);
    });
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    expect(view.querySelector("[role=alert]")?.textContent).toContain("its memory was cleared");
  });

  it("offers the general onboarding chat to a case user with no case open, when the service does", async () => {
    const log: { url: string; body: Record<string, unknown> | null }[] = [];
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      log.push({ url, body: init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : null });
      if (url.endsWith("/health")) return json({ status: "ok", llm_enabled: true, model: "local", answer_mode: "copilot", general_chat: true });
      if (url.endsWith("/api/assistant/contexts")) return json({ context_id: CONTEXT_A, scope: "general", case_id: null, idle_seconds: 1800 });
      if (url.endsWith("/general/chat/stream")) return done("A UBO is a natural person.");
      return json({}, 404);
    });
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root?.render(<AiAssistantPanel caseId={null} onOpenCases={noop} canGeneralChat />));
    click(container.querySelector(".ai-assistant-launcher"));
    await flush();
    expect(container.textContent).toContain("General onboarding help");
    typeInto(container.querySelector("textarea"), "What is a UBO?");
    act(() => (container?.querySelector(".ai-assistant-send") as HTMLButtonElement).click());
    await flush();
    expect(container.textContent).toContain("A UBO is a natural person.");
    expect(log.find((item) => item.url.endsWith("/api/assistant/contexts"))?.body).toEqual({});
    expect(log.find((item) => item.url.endsWith("/general/chat/stream"))?.body).toEqual({ message: "What is a UBO?", context_id: CONTEXT_A });
  });
});
