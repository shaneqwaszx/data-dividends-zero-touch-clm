// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { RecoveryProblem, RecoveryView } from "../../aiAssistant";
import { configureAuthenticatedTransport } from "../../api";
import { RecoveryCentre } from "./RecoveryCentre";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  if (root) act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
  configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function waitFor(assertion: () => void): Promise<void> {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      assertion();
      return;
    } catch (error) {
      if (attempt === 39) throw error;
      await act(async () => new Promise((resolve) => setTimeout(resolve, 0)));
    }
  }
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const unverified: RecoveryProblem = {
  code: "CLAUDE_UNVERIFIED_CALLS", severity: "blocking", provider: "anthropic",
  title: "Claude: 2 closed call(s) not yet verified", cause: "Closed calls are checked in-band.",
  evidence: [{ label: "Unverified calls", value: "2" }],
  actions: [{ kind: "TEST_CONNECTION", label: "Verify calls with Test connection", authority: "HR", permitted: true,
    section: "qualifications", verify: "no call is unverified", profile_id: "claude_fast", run_id: null, blocked_by: [] }],
  owner_request_allowed: false,
};
const breaker: RecoveryProblem = {
  code: "CLAUDE_BREAKER_OPEN", severity: "blocking", provider: "anthropic",
  title: "Claude: the spending breaker is open", cause: "D-110 R8: HR cannot reset it.",
  evidence: [{ label: "Breaker code", value: "reconcile_drift" }],
  actions: [{ kind: "OWNER_REQUEST", label: "Request owner reconciliation and breaker reset", authority: "OWNER", permitted: false,
    section: "overview", verify: "the breaker shows closed", profile_id: null, run_id: null, blocked_by: [] }],
  owner_request_allowed: true,
};
const chat: RecoveryProblem = {
  code: "CLAUDE_CHAT_WINDOW_EXPIRED", severity: "blocking", provider: "anthropic",
  title: "Claude: the 7-day chat window has expired", cause: "Reconcile to renew.",
  evidence: [],
  actions: [{ kind: "RECONCILE", label: "Reconcile with the Anthropic Console figure", authority: "HR", permitted: false,
    section: "spending", verify: "new deadlines", profile_id: null, run_id: null, blocked_by: ["CLAUDE_BREAKER_OPEN"] }],
  owner_request_allowed: false,
};

function view(problems: RecoveryProblem[], requests: RecoveryView["requests"] = []): RecoveryView {
  return {
    generated_at: "2026-11-06T02:00:00+00:00",
    healthy: !problems.some((item) => item.severity === "blocking"),
    problems,
    expiries: {
      claude_chat_deadline_at: "2026-11-07T01:42:37+00:00",
      claude_paid_deadline_at: "2026-11-01T01:42:37+00:00",
      qualifications: [{ profile_id: "claude_fast", display_name: "Claude Sonnet 5.5 Fast", active: true, status: "passed", finished_at: null, current: false }],
    },
    requests,
  };
}

function mount(fetchMock: ReturnType<typeof vi.fn>): HTMLDivElement {
  vi.stubGlobal("fetch", fetchMock);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  act(() => root?.render(<MemoryRouter><QueryClientProvider client={client}><RecoveryCentre userId="biz-ops" onChanged={() => undefined} /></QueryClientProvider></MemoryRouter>));
  return container;
}

function button(scope: ParentNode, label: string): HTMLButtonElement {
  const found = [...scope.querySelectorAll("button")].find((item) => item.textContent === label);
  if (!found) throw new Error(`no button ${label}`);
  return found as HTMLButtonElement;
}

describe("RecoveryCentre", () => {
  it("shows each problem with its cause, evidence, separate deadlines and blocked fixes", async () => {
    const page = mount(vi.fn(async () => json(view([breaker, chat]))));
    await waitFor(() => expect(page.textContent).toContain("the spending breaker is open"));
    expect(page.textContent).toContain("reconcile_drift");
    expect(page.querySelector("[data-testid=recovery-action-blocked]")?.textContent).toContain("first clear CLAUDE_BREAKER_OPEN");
    // The chat window and the paid window are shown apart, never as one expiry.
    const expiries = page.querySelector("[data-testid=recovery-expiries]")?.textContent ?? "";
    expect(expiries).toContain("Claude chat (7-day reconciliation window)");
    expect(expiries).toContain("Claude paid operations (24-hour window)");
    expect(expiries).toContain("out of date");
    // HR is never offered a breaker reset, only an owner request.
    expect(page.textContent).not.toMatch(/reset the breaker now/i);
    expect(button(page, "Request owner reconciliation and breaker reset")).toBeTruthy();
  });

  it("runs the free Test connection only after confirmation, then verifies the recovery", async () => {
    let cleared = false;
    const posts: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (init?.method === "POST") {
        posts.push(url);
        cleared = true;
        return json({ outcome: "passed" });
      }
      return json(view(cleared ? [] : [unverified]));
    });
    const page = mount(fetchMock);
    await waitFor(() => expect(page.textContent).toContain("not yet verified"));
    act(() => button(page, "Verify calls with Test connection").click());
    expect(posts).toHaveLength(0);
    const dialog = document.querySelector("[data-testid=recovery-confirm]") as HTMLElement;
    expect(dialog.textContent).toContain("No inference, no case data and no charge");
    await act(async () => button(dialog, "Confirm").click());
    await waitFor(() => expect(posts).toEqual([expect.stringContaining("/api/assistant/admin/models/claude_fast/connection-test")]));
    await waitFor(() => expect(page.querySelector("[data-testid=recovery-verified]")?.textContent).toContain("CLAUDE_UNVERIFIED_CALLS"));
  });

  it("records an owner request with an optional note and lets HR resolve it only once the problem has gone", async () => {
    const bodies: unknown[] = [];
    const request = {
      request_id: "a".repeat(32), problem_code: "CLAUDE_BREAKER_OPEN", evidence: breaker.evidence, note: "after the demo",
      status: "open" as const, created_at: "2026-11-06T02:00:00+00:00", created_by: "biz-ops", closed_at: null, closed_by: null,
      problem_present: true,
    };
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") {
        bodies.push(JSON.parse(String(init.body)));
        return json(view([breaker], [request]));
      }
      return json(view([breaker], bodies.length ? [request] : []));
    });
    const page = mount(fetchMock);
    await waitFor(() => expect(page.textContent).toContain("the spending breaker is open"));
    act(() => button(page, "Request owner reconciliation and breaker reset").click());
    const dialog = document.querySelector("[data-testid=recovery-confirm]") as HTMLElement;
    expect(dialog.textContent).toContain("does not change the ledger");
    const note = dialog.querySelector("textarea") as HTMLTextAreaElement;
    expect(note.maxLength).toBe(280);
    await act(async () => button(dialog, "Confirm").click());
    await waitFor(() => expect(bodies).toEqual([{ problem_code: "CLAUDE_BREAKER_OPEN", note: null }]));
    await waitFor(() => expect(page.querySelector("[data-testid=recovery-request]")).not.toBeNull());
    expect(button(page, "Still reported").disabled).toBe(true);
  });
});
