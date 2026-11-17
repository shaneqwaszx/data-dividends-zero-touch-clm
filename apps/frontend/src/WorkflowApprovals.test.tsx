// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WorkflowApprovals from "./pages/WorkflowApprovals";
import WorkflowCompare, { LEGACY_PROVENANCE_NOTE } from "./pages/WorkflowCompare";
import type { AuthenticatedProfile } from "./types";
import { approvalErrorView, buildDecisionRequest, workflowApprovalQueryKeys } from "./workflowApprovalsApi";
import { ApiError } from "./api";
import {
  PERMANENT_OBLIGATION_WARNING,
  type ApprovalInboxResponse,
  type ComparisonResponse,
  type DecisionRequest,
  type DecisionResponse,
} from "./workflowGovernanceTypes";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// The shared synthetic fixtures, read with node:fs like workflowGovernanceContract.test.ts. The module
// names are not literals so the browser-typed project needs no @types/node.
declare const __dirname: string;
const { readFileSync } = (await import("node:fs" as string)) as { readFileSync: (path: string, encoding: "utf-8") => string };
const { resolve } = (await import("node:path" as string)) as { resolve: (...segments: string[]) => string };
const FIXTURES = resolve(__dirname, "../../../docs/contracts/fixtures/workflow-governance");
const load = <T,>(name: string): T => JSON.parse(readFileSync(resolve(FIXTURES, name), "utf-8")) as T;

const inbox = () => load<ApprovalInboxResponse>("approvals_inbox.json");
const comparison = () => load<ComparisonResponse>("comparison.json");
const approveRequest = () => load<DecisionRequest>("decision_request_approve.json");
const approvedResponse = () => load<DecisionResponse>("decision_response_approved.json");
const errorBody = (name: string) => ({ detail: load<Record<string, unknown>>(name) });

const director: AuthenticatedProfile = {
  user_id: "director-synthetic-1",
  display_name: "Director",
  role: "DIRECTOR",
  team_id: null,
  team_display_name: null,
  team_type: null,
  team_description: "",
  client_scope_label: "",
  capabilities: ["POLICY_APPROVE"],
};

const WID = "corporate-onboarding";
const PID = "0b6f7c2e-1d3a-4c5b-9e8f-7a6b5c4d3e2f";
const COMPARISON_URL = `/api/workflows/${WID}/proposals/${PID}/comparison`;
const DECISION_URL = `/api/workflows/${WID}/proposals/${PID}/decision`;

type Handler = (url: string, init: RequestInit) => Response | Promise<Response>;
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

let container: HTMLDivElement;
let root: Root;
let fetchMock: ReturnType<typeof vi.fn>;

function mockFetch(handler: Handler) {
  fetchMock = vi.fn((input: RequestInfo | URL, init: RequestInit = {}) => handler(String(input), init));
  vi.stubGlobal("fetch", fetchMock);
}

function calls(url: string) {
  return fetchMock.mock.calls.filter(([input]) => String(input).endsWith(url));
}

async function render(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  await act(async () => { root.render(<QueryClientProvider client={client}>{node}</QueryClientProvider>); });
  await settle();
  return client;
}

async function settle(rounds = 6) {
  for (let index = 0; index < rounds; index += 1) {
    await act(async () => { await new Promise(resolveTimer => setTimeout(resolveTimer, 0)); });
  }
}

const text = () => container.textContent ?? "";
const button = (name: string | RegExp) => {
  const match = [...container.querySelectorAll("button")].find(item =>
    typeof name === "string" ? item.textContent?.trim() === name : name.test(item.textContent ?? ""));
  if (!match) throw new Error(`button ${String(name)} not found`);
  return match as HTMLButtonElement;
};
const checkbox = () => container.querySelector<HTMLInputElement>("input[type=checkbox]");
const reasonBox = () => container.querySelector<HTMLTextAreaElement>("textarea")!;

async function typeReason(value: string) {
  const box = reasonBox();
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
  await act(async () => {
    setter.call(box, value);
    box.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function click(element: HTMLElement) {
  await act(async () => { element.click(); });
  await settle();
}

function comparisonHandler(data: ComparisonResponse, decision?: Handler): Handler {
  return (url, init) => {
    if (url.endsWith(COMPARISON_URL)) return json(200, data);
    if (url.endsWith(DECISION_URL) && decision) return decision(url, init);
    return json(500, {});
  };
}

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("workflowApprovalsApi", () => {
  it("builds the approve request with exactly the comparison's obligation keys", () => {
    const request = buildDecisionRequest(comparison(), "APPROVE", "  Required by the sanctions screening procedure.  ");
    expect(request).toEqual(approveRequest());
  });

  it("sends an empty acknowledgement on reject", () => {
    const request = buildDecisionRequest(comparison(), "REJECT", "Not needed for this client segment.");
    expect(request.outcome).toBe("REJECT");
    expect(request.acknowledged_permanent_obligations).toEqual([]);
    expect(request.content_hash).toBe(comparison().proposal.content_hash);
  });

  it("scopes query keys to the signed-in identity", () => {
    const other = { ...director, user_id: "director-synthetic-2" };
    expect(workflowApprovalQueryKeys.inbox(director)).not.toEqual(workflowApprovalQueryKeys.inbox(other));
    expect(workflowApprovalQueryKeys.inbox(director).slice(0, 2)).toEqual(["auth", director.user_id]);
  });

  it.each([
    [409, "WORKFLOW_PROPOSAL_STALE", true, false],
    [409, "WORKFLOW_PROPOSAL_CONTENT_CHANGED", true, false],
    [409, "WORKFLOW_CONFLICT", true, false],
    [409, "WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED", true, false],
    [403, "WORKFLOW_SELF_DECISION_REFUSED", false, true],
    [503, "WORKFLOW_HISTORY_UNAVAILABLE", false, false],
    [422, "WORKFLOW_REQUIRED_OBLIGATION_REMOVED", true, false],
    [422, "WORKFLOW_REQUIRED_OBLIGATION_WEAKENED", true, false],
    [422, "WORKFLOW_PROPOSAL_INVALID", true, false],
    [422, "WORKFLOW_PROPOSAL_TOO_LARGE", true, false],
  ])("maps %s %s", (status, code, reload, refused) => {
    const view = approvalErrorView(new ApiError("server text", status, code));
    expect(view.reload).toBe(reload);
    expect(view.refused).toBe(refused);
    expect(view.message).not.toBe("server text");
  });
});

describe("WorkflowApprovals inbox", () => {
  it("lists pending proposals with their details and opens the comparison", async () => {
    mockFetch(url => (url.endsWith("/api/workflow-approvals") ? json(200, inbox()) : json(500, {})));
    const onOpen = vi.fn();
    await render(<WorkflowApprovals actor={director} onOpen={onOpen} />);
    expect(text()).toContain("Corporate onboarding");
    expect(text()).toContain("Onboarding");
    expect(text()).toContain("hr-synthetic-1");
    expect(text()).toContain("Base v1 = active");
    expect(text()).toContain("1 stage added, 3 fields added");
    expect(text()).toContain("3 permanent obligations");
    expect(container.querySelector("table caption")?.textContent).toMatch(/waiting for a Director decision/);
    expect(container.querySelectorAll("th[scope=col]").length).toBe(7);
    await click(button("Review"));
    expect(onOpen).toHaveBeenCalledWith(WID, PID);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.signal).toBeInstanceOf(AbortSignal);
  });

  it("shows the empty state", async () => {
    mockFetch(() => json(200, { items: [] }));
    await render(<WorkflowApprovals actor={director} onOpen={vi.fn()} />);
    expect(text()).toContain("No workflow proposals are waiting for a decision.");
    expect(container.querySelector("table")).toBeNull();
  });

  it("explains why a self-authored item offers no decision", async () => {
    const data = inbox();
    data.items[0].proposal.can_decide = false;
    data.items[0].proposal.author_id = director.user_id;
    mockFetch(() => json(200, data));
    await render(<WorkflowApprovals actor={director} onOpen={vi.fn()} />);
    expect(text()).toContain("You authored this proposal. Another Director must decide it.");
    expect(button("View")).toBeTruthy();
    expect(() => button("Review")).toThrow();
  });
});

describe("WorkflowCompare", () => {
  const page = () => <WorkflowCompare actor={director} workflowId={WID} proposalId={PID} onBack={vi.fn()} />;

  it("renders the diff, fixed stages, legacy provenance, checks, affected cases and warning", async () => {
    mockFetch(comparisonHandler(comparison()));
    await render(page());
    expect(text()).toContain("Sanctions attestation");
    expect(text()).toContain("Added");
    expect(text()).toContain("after Ownership & UBO");
    expect(text()).toMatch(/Holds the send: No → Yes/);
    expect(text()).toContain("Screening outcome (Choice: Clear, Escalated, required)");
    expect(text()).toContain("Fixed onboarding stages");
    expect(container.querySelectorAll("ol li").length).toBe(11);
    expect(text()).toContain("Pre-governance activation");
    expect(text()).toContain(LEGACY_PROVENANCE_NOTE);
    expect(text()).toContain("director-legacy-1");
    const provenance = container.querySelector("dl[aria-label='Provenance of version 1']")!;
    expect(provenance.textContent).not.toMatch(/Approver|Governed approval/);
    expect(text()).toContain("Passed");
    expect(text()).toContain("4 open cases run on the active version (v1)");
    expect(text()).toContain(PERMANENT_OBLIGATION_WARNING);
    const obligations = container.querySelector("ul[aria-label='Permanent obligations']")!;
    expect(obligations.querySelectorAll("li").length).toBe(3);
    expect(container.querySelectorAll("input[type=checkbox]").length).toBe(1);
  });

  it("keeps Approve disabled until the reason is valid and the obligations are confirmed", async () => {
    mockFetch(comparisonHandler(comparison()));
    await render(page());
    const approve = () => button("Approve and publish");
    expect(approve().disabled).toBe(true);
    expect(container.querySelector("label[for]")?.textContent).toMatch(/Reason/);
    await typeReason("too short");
    expect(text()).toContain("9 / 240");
    expect(reasonBox().getAttribute("aria-invalid")).toBe("true");
    expect(approve().disabled).toBe(true);
    await typeReason("Required by the sanctions screening procedure.");
    expect(approve().disabled).toBe(true);
    expect(button("Reject").disabled).toBe(false);
    await click(checkbox()!);
    expect(approve().disabled).toBe(false);
    await typeReason(`${"x".repeat(241)}`);
    expect(approve().disabled).toBe(true);
    expect(text()).toContain("at most 240 characters");
  });

  it("blocks Approve and lists each issue when the re-run validation fails", async () => {
    const data = comparison();
    data.validation.valid = false;
    data.validation.issues = [{ code: "WORKFLOW_REQUIRED_OBLIGATION_REMOVED", rule: "RR-1", stage_id: "s", field_id: null, message: "The required stage 'S' cannot be removed." }];
    mockFetch(comparisonHandler(data));
    await render(page());
    await typeReason("Required by the sanctions screening procedure.");
    await click(checkbox()!);
    expect(button("Approve and publish").disabled).toBe(true);
    expect(container.querySelector("ul[aria-label='Validation issues']")?.textContent).toContain("RR-1: The required stage 'S' cannot be removed.");
  });

  it("sends the approve request with the exact acknowledgement set and shows the publication", async () => {
    mockFetch(comparisonHandler(comparison(), () => json(200, approvedResponse())));
    await render(page());
    await typeReason("Required by the sanctions screening procedure.");
    await click(checkbox()!);
    await click(button("Approve and publish"));
    const decisionCalls = calls(DECISION_URL);
    expect(decisionCalls.length).toBe(1);
    const init = decisionCalls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    const body = JSON.parse(String(init.body)) as DecisionRequest;
    expect(body).toEqual(approveRequest());
    expect(text()).toContain("Approved · version 2 is now active");
    expect(text()).toContain("Governed approval");
    expect(text()).toContain("hr-synthetic-1");
    expect(text()).toContain("director-synthetic-1");
    const report = container.querySelector("dl[aria-label='Publication report']")!;
    expect(report.textContent).toContain("Possibly authorised");
    expect(report.textContent).toContain("Cases past their first write under an earlier version3");
    expect(report.textContent).toContain("Cases authorised under an earlier version1");
    expect(container.querySelector("[role=status]")).toBeTruthy();
  });

  it("sends an empty acknowledgement on reject", async () => {
    const rejected = approvedResponse();
    rejected.proposal.state = "REJECTED";
    rejected.published_version = null;
    rejected.provenance = null;
    rejected.publication_report = null;
    mockFetch(comparisonHandler(comparison(), () => json(200, rejected)));
    await render(page());
    await typeReason("Not needed for this client segment.");
    await click(button("Reject"));
    const body = JSON.parse(String((calls(DECISION_URL)[0][1] as RequestInit).body)) as DecisionRequest;
    expect(body.outcome).toBe("REJECT");
    expect(body.acknowledged_permanent_obligations).toEqual([]);
    expect(text()).toContain("Rejected · nothing was published");
  });

  it("offers no decision when the proposal cannot be decided by this Director", async () => {
    const data = comparison();
    data.proposal.can_decide = false;
    data.proposal.author_id = director.user_id;
    mockFetch(comparisonHandler(data));
    await render(page());
    expect(text()).toContain("You authored this proposal. Another Director must decide it.");
    expect(container.querySelector("textarea")).toBeNull();
    expect(checkbox()).toBeNull();
    expect(text()).toContain(PERMANENT_OBLIGATION_WARNING);
  });

  it("shows the server's self-decision refusal and removes the decision", async () => {
    mockFetch(comparisonHandler(comparison(), () => json(403, errorBody("error_self_decision.json"))));
    await render(page());
    await typeReason("Not needed for this client segment.");
    await click(button("Reject"));
    expect(container.querySelector("[role=alert]")?.textContent).toMatch(/You authored this proposal, so you cannot decide it/);
    expect(container.querySelector("textarea")).toBeNull();
  });

  it.each([
    ["error_acknowledgement_required.json", "WORKFLOW_PERMANENT_OBLIGATION_ACKNOWLEDGEMENT_REQUIRED", /permanent obligations to confirm no longer match/],
    [null, "WORKFLOW_PROPOSAL_STALE", /now stale/],
    [null, "WORKFLOW_CONFLICT", /changed while you were reviewing/],
  ])("handles 409 %s %s by offering a reload and never retrying", async (fixture, code, message) => {
    const body = fixture ? errorBody(fixture) : { detail: { code, message: "server", rule: null, issues: [] } };
    mockFetch(comparisonHandler(comparison(), () => json(409, body)));
    await render(page());
    await typeReason("Required by the sanctions screening procedure.");
    await click(checkbox()!);
    await click(button("Approve and publish"));
    await settle();
    expect(calls(DECISION_URL).length).toBe(1);
    expect(container.querySelector("[role=alert]")?.textContent).toMatch(message);
    expect(button("Approve and publish").disabled).toBe(true);
    expect(button("Reject").disabled).toBe(true);
    const before = calls(COMPARISON_URL).length;
    await click(button("Reload comparison"));
    expect(calls(COMPARISON_URL).length).toBe(before + 1);
    expect(calls(DECISION_URL).length).toBe(1);
    expect(container.querySelector("[role=alert]")).toBeNull();
    expect(checkbox()!.checked).toBe(false);
    expect(reasonBox().value).toBe("");
  });

  it("says nothing was changed when history is unavailable", async () => {
    mockFetch(comparisonHandler(comparison(), () => json(503, errorBody("error_history_unavailable.json"))));
    await render(page());
    await typeReason("Not needed for this client segment.");
    await click(button("Reject"));
    expect(container.querySelector("[role=alert]")?.textContent).toContain("Nothing was changed.");
    expect(calls(DECISION_URL).length).toBe(1);
  });

  it.each([
    ["error_ratchet_removed.json", null],
    [null, "WORKFLOW_REQUIRED_OBLIGATION_WEAKENED"],
    [null, "WORKFLOW_PROPOSAL_INVALID"],
    [null, "WORKFLOW_PROPOSAL_TOO_LARGE"],
  ])("handles a 422 refusal %s %s by listing issues, blocking a repeat and offering a reload", async (fixture, code) => {
    const issue = { code: code ?? "", rule: "RR-5", stage_id: "sanctions-attestation", field_id: null, message: "A required field would be weakened." };
    const body = fixture ? errorBody(fixture) : { detail: { code, message: "server", rule: "RR-5", issues: [issue] } };
    mockFetch(comparisonHandler(comparison(), () => json(422, body)));
    await render(page());
    await typeReason("Required by the sanctions screening procedure.");
    await click(checkbox()!);
    await click(button("Approve and publish"));
    expect(container.querySelector("ul[aria-label='Refusal issues']")?.textContent).toContain(
      fixture ? "RR-1: The required stage 'Sanctions attestation' cannot be removed." : "RR-5: A required field would be weakened.");
    expect(container.querySelector("[role=alert]")?.textContent).toContain("Nothing was changed.");
    expect(button("Approve and publish").disabled).toBe(true);
    expect(button("Reject").disabled).toBe(true);
    await click(button("Approve and publish"));
    expect(calls(DECISION_URL).length).toBe(1);
    const before = calls(COMPARISON_URL).length;
    await click(button("Reload comparison"));
    expect(calls(COMPARISON_URL).length).toBe(before + 1);
    expect(container.querySelector("[role=alert]")).toBeNull();
    expect(calls(DECISION_URL).length).toBe(1);
  });

  it("shows a governed active version as approved with author and approver", async () => {
    const data = comparison();
    data.active_provenance = approvedResponse().provenance;
    mockFetch(comparisonHandler(data));
    await render(page());
    expect(text()).toContain("Governed approval");
    expect(text()).not.toContain(LEGACY_PROVENANCE_NOTE);
  });
});
