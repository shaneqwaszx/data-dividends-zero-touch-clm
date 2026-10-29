// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import AiAssistantPanel, { AnswerActivity, AnswerUsed } from "./AiAssistantPanel";

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

function render(caseId: string | null, onOpenCases: () => void = noop): HTMLDivElement {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => root?.render(<AiAssistantPanel caseId={caseId} onOpenCases={onOpenCases} />));
  return container;
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
    // Answer ready: the progress stages are gone; how the answer was produced is one click away.
    expect(view.querySelector(".ai-assistant-activity")).toBeNull();
    const used = view.querySelector(".ai-assistant-used");
    expect(used?.textContent).toContain("What this answer used");
    expect(used?.textContent).toContain("Model: ministral-3:8b");
    expect(used?.textContent).toContain("checked against this case's approved wording");
    expect(used?.textContent).toMatch(/Time to answer: \d+\.\d s \(measured in this browser\)/);

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

  it("shows cited sources and sends Yes, helpful as a rating only, without the conversation", async () => {
    const sent: unknown[] = [];
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
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
      if (url.endsWith("/feedback")) {
        sent.push(JSON.parse(String(init?.body)));
        return json({ feedback_id: 1, message: "Thanks for your feedback." });
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
    // The summary counts what the chips show: one cited source, not both retrieved ones.
    expect(view.querySelector(".ai-assistant-used")?.textContent).toContain("Approved sources cited: 1");

    // One click: an RM is not asked to write anything when the answer helped.
    click([...view.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Yes, helpful"));
    await flush();
    expect(view.querySelector(".ai-assistant-feedback-form")).toBeNull();

    expect(sent).toEqual([{ helpful: true, note: "" }]);
    expect(view.textContent).toContain("Thanks for your feedback.");
    // The opening summary has no feedback buttons.
    expect([...view.querySelectorAll(".ai-assistant-feedback-button")]).toHaveLength(0);
  });

  it("asks Not helpful for a required note and sends it as an enhancement request", async () => {
    const sent: unknown[] = [];
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        return new Response(
          `${JSON.stringify({ type: "done", answer: "Keep the registry value.", answered_by: "model", model: "m", notice: null, suggested_questions: [], answer_id: ANSWER_ID })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      if (url.endsWith("/feedback")) {
        sent.push(JSON.parse(String(init?.body)));
        return json({ feedback_id: 2, message: "Thanks. This has been flagged so the answer can be improved." });
      }
      return json({}, 404);
    });

    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    click([...view.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Not helpful"));
    await flush();

    const form = view.querySelector(".ai-assistant-feedback-form");
    expect(form?.querySelector("label")?.textContent).toBe("What was missing?");
    expect(form?.textContent).not.toContain("optional");
    expect(form?.querySelector(".ai-assistant-hint")?.textContent).toBe(
      "Your note goes to a Director. Client names, UENs and addresses are removed first.",
    );
    const note = form?.querySelector("textarea") as HTMLTextAreaElement;
    expect(note.required).toBe(true);
    const send = [...(form?.querySelectorAll("button") ?? [])].find((b) => b.textContent?.trim() === "Send");
    // Nothing typed, or only whitespace: Send stays disabled and nothing is sent.
    expect(send?.disabled).toBe(true);
    const type = (value: string) => act(() => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set?.call(note, value);
      note.dispatchEvent(new Event("input", { bubbles: true }));
    });
    type("   ");
    expect(send?.disabled).toBe(true);
    click(send);
    await flush();
    expect(sent).toEqual([]);

    type("  It did not list the proof to ask for. ");
    expect(send?.disabled).toBe(false);
    click(send);
    await flush();
    // The answer's record id goes with the note, so a Director can see what happened.
    expect(sent).toEqual([{ helpful: false, note: "It did not list the proof to ask for.", answer_id: ANSWER_ID }]);
    expect(view.textContent).toContain("Thanks. This has been flagged so the answer can be improved.");
  });

  it("keeps each answer's record id, sends earlier ids with the next question and with feedback", async () => {
    const asked: Record<string, unknown>[] = [];
    const rated: unknown[] = [];
    const ids = [ANSWER_ID, "B".repeat(22)];
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        asked.push(JSON.parse(String(init?.body)) as Record<string, unknown>);
        const answerId = ids[asked.length - 1];
        return new Response(
          `${JSON.stringify({ type: "done", answer: `Answer ${asked.length}.`, answered_by: "model", model: "m", notice: null, suggested_questions: ["Next?"], answer_id: answerId })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      if (url.endsWith("/feedback")) {
        rated.push(JSON.parse(String(init?.body)));
        return json({ feedback_id: 3, message: "Thanks for your feedback." });
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
    // The first question has no earlier answers; the second names the first answer only.
    expect(asked[0].earlier_answer_ids).toBeUndefined();
    expect(asked[1].earlier_answer_ids).toEqual([ANSWER_ID]);
    const helpful = [...view.querySelectorAll("button")].filter((b) => b.textContent?.trim() === "Yes, helpful");
    click(helpful[1]);
    await flush();
    expect(rated).toEqual([{ helpful: true, note: "", answer_id: "B".repeat(22) }]);
  });

  it("still offers Not helpful when the answer has no record, and says only the note is sent", async () => {
    const sent: unknown[] = [];
    stubFetch(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        // The record could not be saved (or small talk, or the knowledge store off).
        return new Response(
          `${JSON.stringify({ type: "done", answer: "From ACRA (MOCK).", answered_by: "case_data", model: null, notice: null, suggested_questions: [], answer_id: null })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      if (url.endsWith("/feedback")) {
        sent.push(JSON.parse(String(init?.body)));
        return json({ feedback_id: 3, message: "Thanks. This has been flagged so the answer can be improved." });
      }
      return json({}, 404);
    });
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    const labels = [...view.querySelectorAll(".ai-assistant-rate button")].map((b) => b.textContent?.trim());
    expect(labels).toEqual(["Yes, helpful", "Not helpful"]);
    click([...view.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Not helpful"));
    await flush();
    const form = view.querySelector(".ai-assistant-feedback-form");
    expect(form?.querySelector('[role="note"]')?.textContent).toBe(
      "We couldn't save the details of this answer, so the Director will only see your note.",
    );
    const note = form?.querySelector("textarea") as HTMLTextAreaElement;
    act(() => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set?.call(note, "It did not show the two addresses.");
      note.dispatchEvent(new Event("input", { bubbles: true }));
    });
    click([...(form?.querySelectorAll("button") ?? [])].find((b) => b.textContent?.trim() === "Send"));
    await flush();
    // The note alone: no answer_id is made up.
    expect(sent).toEqual([{ helpful: false, note: "It did not show the two addresses." }]);
    expect(view.textContent).toContain("Thanks. This has been flagged so the answer can be improved.");
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

  it("does not say a record failed after small talk, which never has one", async () => {
    stubFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary of Garden."));
      if (url.endsWith("/chat/stream")) {
        return new Response(
          `${JSON.stringify({ type: "done", answer: "Hello!", answered_by: "case_data", model: null, notice: null, suggested_questions: [], answer_id: null, small_talk: true })}\n`,
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
    click([...view.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Not helpful"));
    await flush();
    const form = view.querySelector(".ai-assistant-feedback-form");
    expect(form?.querySelector("textarea")).not.toBeNull();
    expect(form?.querySelector('[role="note"]')).toBeNull();
  });

  it("offers Not helpful on every answer, including a one-line answer after a rated one", async () => {
    const answers = [
      "The current case offers \"Keep registry value\".",
      "Document or reconciliation review required: this is for the document reviewer.",
    ];
    stubFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("MERLION CIRCULAR LABS PTE. LTD.", "Summary of Merlion."));
      if (url.endsWith("/chat/stream")) {
        const answer = answers.shift();
        return new Response(
          `${JSON.stringify({ type: "done", answer, answered_by: "model", model: "m", notice: null, suggested_questions: ["Who should I call about this?"] })}\n`,
          { status: 200, headers: { "Content-Type": "application/x-ndjson" } },
        );
      }
      if (url.endsWith("/feedback")) return json({ feedback_id: 1, message: "Thanks for your feedback." });
      return json({}, 404);
    });
    const buttons = (label: string) =>
      [...view.querySelectorAll(".ai-assistant-feedback-button")].filter((b) => b.textContent?.trim() === label);

    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    expect(buttons("Yes, helpful")).toHaveLength(1);
    expect(buttons("Not helpful")).toHaveLength(1);
    click(buttons("Yes, helpful")[0]);
    await flush();
    expect(view.textContent).toContain("Thanks for your feedback.");

    click(view.querySelector(".ai-assistant-chip"));
    await flush();
    expect(view.textContent).toContain("this is for the document reviewer.");
    // The new one-line answer has no answer record and is not small talk: both buttons show.
    expect(buttons("Yes, helpful")).toHaveLength(1);
    expect(buttons("Not helpful")).toHaveLength(1);
  });

  it("offers Knowledge review only to someone the backend allows to review", async () => {
    stubFetch(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/brief")) return json(brief("GARDEN BUSINESS", "Summary."));
      if (url.endsWith("/knowledge/reviews")) return json({ pending: [], gaps: [] });
      if (url.endsWith("/knowledge/stats")) return json({ entries: {}, feedback: { total: 0, helpful: 0, not_helpful: 0, helpful_rate: null, open_gaps: 0 }, by_topic: {} });
      if (url.includes("/knowledge/entries")) return json([]);
      return json({}, 404);
    }, { user_id: "director-dan", can_review: true, can_edit_guidance: false });
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    click(view.querySelector(".ai-assistant-review-open"));
    await flush();
    expect(view.querySelector('[role="dialog"]')?.textContent).toContain("Knowledge review");
    expect(view.textContent).toContain("Nothing to review.");
  });

  it("hides Knowledge review from an RM", async () => {
    stubFetch(async (input: RequestInfo | URL) =>
      String(input).endsWith("/brief") ? json(brief("GARDEN BUSINESS", "Summary.")) : json({}, 404),
    );
    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();
    expect(view.querySelector(".ai-assistant-review-open")).toBeNull();
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

  it("summarises a case-data answer without claiming a model wrote it", () => {
    const html = shown(<AnswerUsed answeredBy="case_data" model={null} sources={0} elapsedMs={640} />);
    expect(html).toContain("No AI model wrote this answer: it comes from this case's data and any approved guidance cited.");
    expect(html).not.toContain("Model:");
    expect(html).not.toContain("sources cited");
    expect(html).toContain("0.6 s");
  });

  it("names GPT-OSS 120B and counts cited sources for a model answer", () => {
    const html = shown(<AnswerUsed answeredBy="model" model="openai/gpt-oss-120b" sources={2} elapsedMs={12_437} />);
    expect(html).toContain("Model: GPT-OSS 120B");
    expect(html).toContain("Approved sources cited: 2");
    expect(html).toContain("12 s");
  });
});
