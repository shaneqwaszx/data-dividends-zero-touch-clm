// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import CopilotPanel from "./CopilotPanel";

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
  act(() => root?.render(<CopilotPanel caseId={caseId} onOpenCases={onOpenCases} />));
  return container;
}

function rerender(caseId: string | null): void {
  act(() => root?.render(<CopilotPanel caseId={caseId} onOpenCases={noop} />));
}

function click(element: Element | null | undefined): void {
  if (!element) throw new Error("missing element");
  act(() => (element as HTMLElement).click());
}

function brief(company: string, message: string) {
  return { company, message, suggested_questions: ["Why is this case blocked?"], blocker_count: 1, steps_done: 5, steps_total: 12 };
}

describe("CopilotPanel", () => {
  it("opens with the case brief and answers a suggested question", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/assistant/cases/case-1/brief") {
        return json(brief("GARDEN BUSINESS", "I found 1 issue stopping the onboarding of GARDEN BUSINESS:"));
      }
      if (url === "/api/assistant/cases/case-1/chat") {
        const body = JSON.parse(String(init?.body));
        expect(body.message).toBe("Why is this case blocked?");
        expect(body.history).toEqual([
          { role: "assistant", content: "I found 1 issue stopping the onboarding of GARDEN BUSINESS:" },
        ]);
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
    click(view.querySelector(".copilot-launcher"));
    await flush();

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "GET", credentials: "include" });
    expect(view.textContent).toContain("I found 1 issue stopping the onboarding of GARDEN BUSINESS");
    expect(view.querySelector(".copilot-subtitle")?.textContent).toBe("GARDEN BUSINESS · read-only");

    click([...view.querySelectorAll(".copilot-chip")].find((b) => b.textContent === "Why is this case blocked?"));
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
    click(view.querySelector(".copilot-launcher"));
    await flush();
    expect(view.textContent).toContain("About Garden.");

    rerender(null);
    await flush();
    expect(view.querySelector(".copilot-panel")).not.toBeNull();
    expect(view.querySelector(".copilot-panel-compact")).not.toBeNull();
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
    click(view.querySelector(".copilot-launcher"));
    await flush();

    expect(view.textContent).toContain("Open a case and I'll explain where it stands");
    expect(view.querySelector("textarea")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
    click(view.querySelector(".copilot-open-cases"));
    expect(onOpenCases).toHaveBeenCalledTimes(1);
  });

  it("asks for the company details on New onboarding before the case exists", async () => {
    const fetchMock = vi.fn(async () => json({}, 404));
    vi.stubGlobal("fetch", fetchMock);
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root?.render(<CopilotPanel caseId={null} onboardingWithoutCase onOpenCases={noop} />));
    click(container.querySelector(".copilot-launcher"));
    await flush();

    expect(container.textContent).toContain("Enter the company's details to start");
    expect(container.querySelector(".copilot-open-cases")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("explains when the copilot service is not running", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));

    const view = render("case-1");
    click(view.querySelector(".copilot-launcher"));
    await flush();

    expect(view.querySelector("[role=alert]")?.textContent).toBe("The copilot service is not running.");
  });
});
