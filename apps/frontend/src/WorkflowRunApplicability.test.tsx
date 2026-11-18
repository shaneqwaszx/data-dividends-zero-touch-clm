// @vitest-environment jsdom
// ADR-018 run applicability basis in the case and workflow-run views, and the audited escalation (§3.5 F6).
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, type JSX } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import runApplicabilityView from "../../../docs/contracts/fixtures/workflow-governance/run_applicability_view.json";
import { CaseWorkflowRuns, CaseWorkflowStages } from "./pages/CaseWorkflowPanel";
import type { WorkflowRun, WorkflowRunStage } from "./workflowApi";
import type { RunApplicabilityView } from "./workflowGovernanceTypes";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const stage = (overrides: Partial<WorkflowRunStage> = {}): WorkflowRunStage => ({
  stage_id: "partnership", name: "Partnership checks", after_node_id: "DOCUMENT_IDP", status: "OPEN", blocks_send: true,
  confirmed_by: null, confirmed_at: null,
  fields: [{ field_id: "deed", label: "Partnership deed", kind: "TEXT", required: true, options: [], value: null, source: null, page_number: null }],
  ...overrides,
});
const view = (overrides: Partial<RunApplicabilityView> = {}): RunApplicabilityView => ({
  ...(structuredClone(runApplicabilityView) as unknown as RunApplicabilityView), ...overrides,
});
const unescalated = () => view({
  effective_legal_form: "LLP",
  conflict: { ...view().conflict!, escalated: false, escalated_by: null, escalated_at: null },
});
const run = (overrides: Partial<WorkflowRun> = {}): WorkflowRun => ({
  run_id: "00000000-0000-4000-8000-000000000001", case_id: "case-1", workflow_id: "corporate-onboarding",
  workflow_name: "Corporate onboarding", use_case: "Onboarding", workflow_version: 2, revision: 7, is_onboarding: true,
  is_complete: false, stages: [stage()], ...overrides,
});
const shared = { caseId: "case-1", userId: "user", scopeKey: "scope" };
const ESCALATION_URL = "/api/clm/cases/case-1/workflow/applicability-escalation";

let root: Root | null = null;
let client: QueryClient;
afterEach(() => {
  act(() => root?.unmount());
  root = null;
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
});

function render(element: JSX.Element) {
  const host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  act(() => root!.render(<QueryClientProvider client={client}>{element}</QueryClientProvider>));
  return host;
}
async function settle() {
  for (let index = 0; index < 6; index += 1) await act(async () => { await new Promise(resolveTick => setTimeout(resolveTick, 0)); });
}
const buttonByText = (host: HTMLElement, text: string) => [...host.querySelectorAll("button")].find(item => item.textContent?.trim() === text);
async function click(host: HTMLElement, text: string) {
  const found = buttonByText(host, text);
  if (!found) throw new Error(`No button "${text}"`);
  await act(async () => { found.click(); });
  await settle();
}
function typeReason(host: HTMLElement, value: string) {
  const area = host.querySelector<HTMLTextAreaElement>('[data-testid="run-applicability-escalation"] textarea')!;
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!.call(area, value);
    area.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("case onboarding view (CaseWorkflowStages)", () => {
  it("shows nothing new for a run without an applicability view", () => {
    const host = render(<CaseWorkflowStages {...shared} canFill run={run()} anchors={["DOCUMENT_IDP"]} />);
    expect(host.querySelector('[data-testid="run-applicability"]')).toBeNull();
    expect(host.textContent).toContain("Partnership checks");
  });

  it("shows the basis once, before the first added stage only", () => {
    const value = run({ applicability: view(), stages: [stage(), stage({ stage_id: "later", name: "Later", after_node_id: "OWNERSHIP_UBO" })] });
    const first = render(<><CaseWorkflowStages {...shared} canFill={false} run={value} anchors={["DOCUMENT_IDP"]} />
      <CaseWorkflowStages {...shared} canFill={false} run={value} anchors={["OWNERSHIP_UBO"]} /></>);
    expect(first.querySelectorAll('[data-testid="run-applicability"]')).toHaveLength(1);
    const basis = first.querySelector('[data-testid="run-applicability"]')!;
    expect(basis.compareDocumentPosition(first.querySelector(".stage-disclosure")!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(basis.textContent).toContain("Registry-bound (Mock): LLP");
  });

  it("shows the conflict hold, and offers escalation to a filler only while unescalated", () => {
    const host = render(<CaseWorkflowStages {...shared} canFill run={run({ applicability: unescalated() })} anchors={["DOCUMENT_IDP"]} />);
    expect(host.querySelector('[data-testid="run-applicability-conflict"]')!.textContent).toContain("held before send");
    expect(buttonByText(host, "Apply all conditional steps…")).toBeDefined();
    act(() => root?.unmount());
    document.body.innerHTML = "";

    const reader = render(<CaseWorkflowStages {...shared} canFill={false} run={run({ applicability: unescalated() })} anchors={["DOCUMENT_IDP"]} />);
    expect(reader.querySelector('[data-testid="run-applicability-conflict"]')).not.toBeNull();
    expect(reader.querySelector('[data-testid="run-applicability-escalation"]')).toBeNull();
    act(() => root?.unmount());
    document.body.innerHTML = "";

    const escalated = render(<CaseWorkflowStages {...shared} canFill run={run({ applicability: view() })} anchors={["DOCUMENT_IDP"]} />);
    expect(escalated.textContent).toContain("Escalated by rm-synthetic-1");
    expect(escalated.querySelector('[data-testid="run-applicability-escalation"]')).toBeNull();
  });
  it("keeps a held run with no added stage escalatable, once, at the registry step (M3 QG P2-2)", () => {
    const held = run({ applicability: unescalated(), stages: [] });
    const host = render(<><CaseWorkflowStages {...shared} canFill run={held} anchors={["GOLDTIER_SEARCH"]} />
      <CaseWorkflowStages {...shared} canFill run={held} anchors={["ACRA_REGISTRY"]} />
      <CaseWorkflowStages {...shared} canFill run={held} anchors={["DOCUMENT_IDP", "RECONCILIATION"]} /></>);
    expect(host.querySelectorAll('[data-testid="run-applicability"]')).toHaveLength(1);
    expect(host.querySelector('[data-testid="run-applicability-conflict"]')!.textContent).toContain("held before send");
    expect(buttonByText(host, "Apply all conditional steps…")).toBeDefined();
  });
});

describe("escalation (Apply all conditional steps)", () => {
  it("requires a 10–240 character reason and sends run_id, expected_revision and reason once", async () => {
    const fetchMock = vi.fn(async () => json({}));
    vi.stubGlobal("fetch", fetchMock);
    const host = render(<CaseWorkflowStages {...shared} canFill run={run({ applicability: unescalated() })} anchors={["DOCUMENT_IDP"]} />);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await click(host, "Apply all conditional steps…");
    const panel = host.querySelector('[data-testid="run-applicability-escalation"]')!;
    expect(panel.textContent).toContain("This only adds steps");
    expect(panel.textContent).toContain("audited");
    const confirm = () => buttonByText(host, "Apply all conditional steps")!;
    expect(confirm().disabled).toBe(true);
    typeReason(host, "too short");
    expect(confirm().disabled).toBe(true);
    typeReason(host, "x".repeat(241));
    expect(confirm().disabled).toBe(true);
    typeReason(host, "  Registry now reports LP; apply every condition  ");
    expect(confirm().disabled).toBe(false);
    await click(host, "Apply all conditional steps");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(ESCALATION_URL);
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      run_id: "00000000-0000-4000-8000-000000000001", expected_revision: 7, reason: "Registry now reports LP; apply every condition",
    });
    expect(host.textContent).toContain("All conditional steps now apply to this run.");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["auth", "user", "workflows"] });
  });

  it("reloads on 409 and never retries", async () => {
    const fetchMock = vi.fn(async () => json({ detail: { code: "WORKFLOW_CONFLICT", message: "Conflict." } }, 409));
    vi.stubGlobal("fetch", fetchMock);
    const host = render(<CaseWorkflowStages {...shared} canFill run={run({ applicability: unescalated() })} anchors={["DOCUMENT_IDP"]} />);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await click(host, "Apply all conditional steps…");
    typeReason(host, "Registry now reports LP; apply every condition");
    await click(host, "Apply all conditional steps");
    await settle();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(host.textContent).toContain("Nothing was changed. It has been reloaded");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["auth", "user", "workflows"] });
  });

  it("tells a run with no conflict left apart from a changed run", async () => {
    const fetchMock = vi.fn(async () => json({ detail: { code: "WORKFLOW_APPLICABILITY_NOT_IN_CONFLICT", message: "No conflict." } }, 409));
    vi.stubGlobal("fetch", fetchMock);
    const host = render(<CaseWorkflowStages {...shared} canFill run={run({ applicability: unescalated() })} anchors={["DOCUMENT_IDP"]} />);
    await click(host, "Apply all conditional steps…");
    typeReason(host, "Registry now reports LP; apply every condition");
    await click(host, "Apply all conditional steps");
    await settle();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(host.textContent).toContain("no applicability conflict to escalate");
    expect(host.textContent).not.toContain("changed while you were working");
  });

  it("clears the reason on Cancel", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const host = render(<CaseWorkflowStages {...shared} canFill run={run({ applicability: unescalated() })} anchors={["DOCUMENT_IDP"]} />);
    await click(host, "Apply all conditional steps…");
    typeReason(host, "Registry now reports LP; apply every condition");
    await click(host, "Cancel");
    await click(host, "Apply all conditional steps…");
    expect(host.querySelector<HTMLTextAreaElement>('[data-testid="run-applicability-escalation"] textarea')!.value).toBe("");
  });
});

describe("workflow run view (CaseWorkflowRuns, used by WorkflowRunPage)", () => {
  const other = (overrides: Partial<WorkflowRun> = {}) => run({
    is_onboarding: false, workflow_name: "Case refresh", stages: [stage({ after_node_id: null })], ...overrides,
  });

  it("shows the basis before each run's stages only when present", () => {
    const host = render(<CaseWorkflowRuns {...shared} canFill runs={[
      other({ run_id: "r-1", applicability: view({ status: "UNVERIFIED", legal_form: null, effective_legal_form: null, source_environment: null, conflict: null, reason: "NO_BINDING", frozen: false }) }),
      other({ run_id: "r-2" }),
    ]} />);
    const bases = host.querySelectorAll('[data-testid="run-applicability"]');
    expect(bases).toHaveLength(1);
    expect(bases[0].textContent).toContain("Not verified (no registry source): all conditional steps apply");
    expect(bases[0].compareDocumentPosition(host.querySelector(".stage-disclosure")!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows the conflict hold without an escalation when the run has no case", () => {
    const host = render(<CaseWorkflowRuns {...shared} caseId={null} canFill runs={[other({ case_id: null, applicability: unescalated() })]} />);
    expect(host.querySelector('[data-testid="run-applicability-conflict"]')).not.toBeNull();
    expect(host.querySelector('[data-testid="run-applicability-escalation"]')).toBeNull();
  });
});
