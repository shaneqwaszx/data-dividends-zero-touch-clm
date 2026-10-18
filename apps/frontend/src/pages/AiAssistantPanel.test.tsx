// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import AiAssistantPanel from "./AiAssistantPanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

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

describe("AiAssistantPanel", () => {
  it("shows the answer while it is being written, then the final answer", async () => {
    const stream = ndjsonStream();
    const sent: unknown[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
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
    expect(view.textContent).toContain("Thinking");

    stream.send({ type: "text", text: "Keep the registry value." });
    await flush();
    expect(view.textContent).toContain("Keep the registry value.");
    expect(view.textContent).not.toContain("Thinking");
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
    vi.stubGlobal("fetch", fetchMock);

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
    vi.stubGlobal("fetch", fetchMock);

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
    vi.stubGlobal("fetch", fetchMock);
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
    vi.stubGlobal("fetch", fetchMock);
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
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    const view = render("case-1");
    click(view.querySelector(".ai-assistant-launcher"));
    await flush();

    expect(view.querySelector("[role=alert]")?.textContent).toBe("The AI assistant service is not running.");
  });


  it("removes retained case conversation when the backend says the case is inaccessible", async () => {
    let count = 0;
    vi.stubGlobal("fetch", vi.fn(async () => {
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
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => pending.push(resolve))));
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
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
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
});
