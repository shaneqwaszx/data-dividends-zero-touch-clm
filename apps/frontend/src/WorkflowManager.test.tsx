// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, type JSX } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { canFillOnboardingStages, CaseWorkflowRuns, CaseWorkflowStages } from "./pages/CaseWorkflowPanel";
import { availableCompanies, runProgress } from "./pages/WorkflowTab";
import { ApiError } from "./api";
import { copyStage, editorRows, reorderStages, reusableStages, WorkflowEditor, workflowStatusLabel } from "./pages/WorkflowManager";
import type { ProcessingNode } from "./types";
import { workflowErrorMessage, type WorkflowDetail, type WorkflowRun, type WorkflowRunStage, type WorkflowStage } from "./workflowApi";
import { workflowManagerEnabled } from "./workflowFlags";
import { withWorkflowStages, workflowStageElementId } from "./workflowPipeline";
import { ONBOARDING_STAGE_TEMPLATES } from "./workflowStageTemplates";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const node = (node_id: string): ProcessingNode => ({ node_id, label: node_id, status: "NOT_REACHED", children: [] });
const stage = (overrides: Partial<WorkflowRunStage> = {}): WorkflowRunStage => ({
  stage_id: "signatory",
  name: "Authorised signatory details",
  after_node_id: "DOCUMENT_IDP",
  status: "OPEN",
  blocks_send: true,
  confirmed_by: null,
  confirmed_at: null,
  fields: [{
    field_id: "full-name", label: "Full name", kind: "TEXT", required: true, options: [],
    value: "Suggested Name", source: "DOCUMENT", page_number: 2,
  }],
  ...overrides,
});
const run = (stages: WorkflowRunStage[] = [stage()], overrides: Partial<WorkflowRun> = {}): WorkflowRun => ({
  run_id: "00000000-0000-4000-8000-000000000001",
  case_id: null,
  workflow_id: "workflow",
  workflow_name: "Corporate onboarding",
  use_case: "Onboarding",
  workflow_version: 1,
  revision: 1,
  is_onboarding: true,
  is_complete: false,
  stages,
  ...overrides,
});

describe("withWorkflowStages", () => {
  const pipeline = ["CASE_START", "DOCUMENT_IDP", "RECONCILIATION", "GOLDTIER_DETAILS", "FINAL_REVIEW_SEND"].map(node);

  it("returns the same pipeline when nothing is configured", () => {
    expect(withWorkflowStages(pipeline, null)).toBe(pipeline);
  });

  it("places a stage after its anchor and shows an open stage as needing review", () => {
    const merged = withWorkflowStages(pipeline, run());
    expect(merged.map(item => item.node_id)).toEqual([
      "CASE_START", "DOCUMENT_IDP", "WORKFLOW_STAGE_signatory", "RECONCILIATION", "GOLDTIER_DETAILS", "FINAL_REVIEW_SEND",
    ]);
    expect(merged[2].status).toBe("REVIEW_REQUIRED");
    expect(pipeline).toHaveLength(5);
  });

  it("reports a stage as ready once confirmed, with when, and not ready before that", () => {
    const merged = withWorkflowStages(pipeline, run([
      stage(),
      stage({ stage_id: "done", status: "COMPLETE", confirmed_by: "maya-lim", confirmed_at: "2026-11-05T11:00:00Z" }),
    ]));
    expect(merged[2].status).toBe("REVIEW_REQUIRED");
    expect(merged[2].safe_result).toBe("Action needed");
    expect(merged[3].safe_result).toBe("Ready");
    expect(merged[3].timestamp).toBe("2026-11-05T11:00:00Z");
  });

  it("shows a locked stage as not started, never as needing review", () => {
    const merged = withWorkflowStages(pipeline, run([
      stage({ stage_id: "next", status: "LOCKED" }),
      stage({ stage_id: "open" }),
    ]));
    const locked = merged.find(node => node.node_id === "WORKFLOW_STAGE_next")!;
    const open = merged.find(node => node.node_id === "WORKFLOW_STAGE_open")!;
    expect(locked.status).toBe("NOT_REACHED");
    expect(locked.safe_result).toBe("Opens after the previous stage");
    expect(open.status).toBe("REVIEW_REQUIRED");
    expect(open.safe_result).toBe("Action needed");
  });

  it("keeps stages sharing an anchor in order and shows a confirmed stage as complete", () => {
    const merged = withWorkflowStages(pipeline, run([stage(), stage({ stage_id: "second", status: "COMPLETE" })]));
    expect(merged.map(item => item.node_id).slice(2, 4)).toEqual(["WORKFLOW_STAGE_signatory", "WORKFLOW_STAGE_second"]);
    expect(merged[3].status).toBe("COMPLETE");
  });

  it("falls back when the anchor is not shown", () => {
    const merged = withWorkflowStages(pipeline, run([stage({ after_node_id: "INITIAL_IDENTITY" })]));
    expect(merged[1].node_id).toBe("WORKFLOW_STAGE_signatory");
  });
});

describe("canFillOnboardingStages", () => {
  const open = { status: "WAITING_FOR_REVIEW", current_stage: "READINESS" };

  it("lets only the RM or onboarder fill in a case that has not been sent", () => {
    expect(canFillOnboardingStages("CLIENT_ONBOARDER", open)).toBe(true);
    expect(canFillOnboardingStages("RELATIONSHIP_MANAGER", open)).toBe(true);
    expect(canFillOnboardingStages("DIRECTOR", open)).toBe(false);
  });

  it("closes the stages once the case is sent or being sent", () => {
    expect(canFillOnboardingStages("CLIENT_ONBOARDER", { status: "COMPLETED", current_stage: "COMPLETE" })).toBe(false);
    expect(canFillOnboardingStages("CLIENT_ONBOARDER", { status: "RUNNING", current_stage: "MOCK_GOLDTIER" })).toBe(false);
  });
});

describe("availableCompanies", () => {
  it("leaves out companies that already have a case in this workflow", () => {
    const companies = [{ case_id: "a" }, { case_id: "b" }];
    expect(availableCompanies(companies, [{ case_id: "a" }])).toEqual([{ case_id: "b" }]);
    expect(availableCompanies(companies, [])).toEqual(companies);
  });
});

describe("runProgress", () => {
  it("counts confirmed stages and names the stage to work on", () => {
    const value = run([stage({ status: "COMPLETE" }), stage({ stage_id: "next", name: "Next", status: "OPEN" }), stage({ stage_id: "later", status: "LOCKED" })]);
    const progress = runProgress(value);
    expect([progress.done, progress.total, progress.percent, progress.current?.name]).toEqual([1, 3, 33, "Next"]);
  });

  it("has nothing left to do when every stage is confirmed", () => {
    const progress = runProgress(run([stage({ status: "COMPLETE" })]));
    expect([progress.percent, progress.current]).toEqual([100, null]);
  });
});

describe("reorderStages", () => {
  const stage = (stage_id: string): WorkflowStage => ({ stage_id, name: stage_id, fields: [], after_node_id: null });
  const stages = ["a", "b", "c"].map(stage);
  const order = (items: WorkflowStage[]) => items.map(item => item.stage_id).join("");

  it("moves a stage up or down to the target's position", () => {
    expect(order(reorderStages(stages, "c", "a"))).toBe("cab");
    expect(order(reorderStages(stages, "a", "c"))).toBe("bca");
    expect(order(stages)).toBe("abc");
  });

  it("leaves the order alone for the same or an unknown stage", () => {
    expect(reorderStages(stages, "a", "a")).toBe(stages);
    expect(reorderStages(stages, "x", "a")).toBe(stages);
  });
});

describe("editorRows", () => {
  const added = { stage_id: "new", name: "Background check", fields: [], after_node_id: "DOCUMENT_IDP" };
  const locked = [{ node_id: "CASE_START", label: "Case created" }, { node_id: "DOCUMENT_IDP", label: "Document verification" }, { node_id: "RECONCILIATION", label: "Data reconciliation" }];

  it("puts an added onboarding stage in the list straight after the stage it follows", () => {
    const rows = editorRows({ is_onboarding: true, locked_stages: locked }, [added]);
    expect(rows.map(row => row.kind === "existing" ? row.label : row.stage.name)).toEqual([
      "Case created", "Document verification", "Background check", "Data reconciliation",
    ]);
  });

  it("lists a new workflow's stages in their own order", () => {
    const rows = editorRows({ is_onboarding: false, locked_stages: [] }, [{ ...added, after_node_id: null }]);
    expect(rows).toEqual([{ kind: "added", stage: { ...added, after_node_id: null } }]);
  });
});

describe("reusing stages", () => {
  const field = { field_id: "f1", label: "Reference", kind: "TEXT" as const, required: true, options: [], autofill: false, document_label: null };
  const built = (name: string, fields = [field]): WorkflowStage => ({ stage_id: name, name, fields, after_node_id: null });
  const workflow = (workflow_id: string, name: string, draft_stages: WorkflowStage[]) => ({ workflow_id, name, draft_stages }) as WorkflowDetail;
  const all = [
    workflow("mine", "Case refresh", [built("Own stage")]),
    workflow("a", "Corporate onboarding", [built("Background check"), built("Empty", [])]),
    workflow("b", "Hong Kong", [built("background check"), built("Own stage"), built("Contact person")]),
  ];

  it("suggests other workflows' stages once each, skipping empty ones and names already here", () => {
    const suggestions = reusableStages(all[0], all, all[0].draft_stages);
    expect(suggestions.map(item => `${item.stage.name}/${item.source}`)).toEqual([
      "Background check/Corporate onboarding", "Contact person/Hong Kong",
    ]);
  });

  it("lists every onboarding stage in order, with existing ones offering mock fields", () => {
    const onboarding = {
      ...workflow("onboarding", "Corporate onboarding", [{ ...built("Background check"), after_node_id: "DOCUMENT_IDP" }]),
      is_onboarding: true,
      locked_stages: [{ node_id: "DOCUMENT_IDP", label: "Document verification" }, { node_id: "FINAL_REVIEW_SEND", label: "Final review & send" }],
    };
    const suggestions = reusableStages(all[0], [all[0], onboarding], all[0].draft_stages);
    expect(suggestions.map(item => [item.stage.name, item.mock])).toEqual([
      ["Document verification", true], ["Background check", false], ["Final review & send", true],
    ]);
    expect(suggestions[0].stage.fields.map(item => item.label)).toEqual(["Document name", "Document reviewed?"]);
    expect(suggestions[0].stage.stage_id).toMatch(/^[a-z0-9][a-z0-9-]*$/);
  });

  it("has mock fields for all eleven onboarding stages, each valid to activate", () => {
    const ids = ["CASE_START", "INITIAL_IDENTITY", "JURISDICTION", "GOLDTIER_SEARCH", "ACRA_REGISTRY", "DOCUMENT_IDP", "RECONCILIATION", "OWNERSHIP_UBO", "ADVISORY", "GOLDTIER_DETAILS", "FINAL_REVIEW_SEND"];
    expect(Object.keys(ONBOARDING_STAGE_TEMPLATES).sort()).toEqual([...ids].sort());
    for (const fields of Object.values(ONBOARDING_STAGE_TEMPLATES)) {
      expect(fields.length).toBeGreaterThan(0);
      expect(new Set(fields.map(item => item.field_id)).size).toBe(fields.length);
      for (const item of fields) {
        expect(item.field_id).toMatch(/^[a-z0-9][a-z0-9-]*$/);
        if (item.kind === "CHOICE") expect(item.options.length).toBeGreaterThan(0);
        if (item.autofill) expect(item.document_label).toBeTruthy();
      }
    }
  });

  it("makes an independent copy with new identifiers", () => {
    const source = built("Background check");
    const copy = copyStage(source, "DOCUMENT_IDP");
    expect(copy.name).toBe("Background check");
    expect(copy.after_node_id).toBe("DOCUMENT_IDP");
    expect(copy.stage_id).not.toBe(source.stage_id);
    expect(copy.fields[0].field_id).not.toBe(source.fields[0].field_id);
    expect(copy.fields[0].label).toBe("Reference");
  });
});

describe("workflowStageElementId", () => {
  it("links an added stage to its form and ignores every other stage", () => {
    expect(workflowStageElementId("WORKFLOW_STAGE_abc")).toBe("workflow-stage-abc");
    expect(workflowStageElementId("DOCUMENT_IDP")).toBeNull();
  });
});

describe("workflowStatusLabel", () => {
  it("always shows onboarding as active and other workflows as active or draft", () => {
    expect(workflowStatusLabel({ active_version: 1, is_onboarding: false })).toBe("Active");
    expect(workflowStatusLabel({ active_version: null, is_onboarding: true })).toBe("Active");
    expect(workflowStatusLabel({ active_version: 2, is_onboarding: true })).toBe("Active");
    expect(workflowStatusLabel({ active_version: null, is_onboarding: false })).toBe("Draft");
  });
});

describe("workflowManagerEnabled", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("is on unless explicitly switched off", () => {
    vi.stubEnv("VITE_WORKFLOW_MANAGER_ENABLED", "");
    expect(workflowManagerEnabled()).toBe(true);
    vi.stubEnv("VITE_WORKFLOW_MANAGER_ENABLED", "false");
    expect(workflowManagerEnabled()).toBe(false);
  });
});

describe("case workflow sections", () => {
  let root: Root | null = null;
  afterEach(() => { act(() => root?.unmount()); root = null; document.body.innerHTML = ""; });
  const shared = { caseId: "case", userId: "user", scopeKey: "scope" };

  function render(element: JSX.Element) {
    const host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    act(() => root!.render(<QueryClientProvider client={new QueryClient()}>{element}</QueryClientProvider>));
    return host;
  }

  it("shows a stage as a normal section with its document suggestion", () => {
    const host = render(<CaseWorkflowStages {...shared} canFill run={run()} anchors={["DOCUMENT_IDP"]} />);
    expect(host.querySelector(".stage-disclosure")?.getAttribute("data-tone")).toBe("attention");
    expect(host.textContent).toContain("Authorised signatory details");
    expect(host.textContent).toContain("Found in document, page 2. Please check.");
    expect(host.querySelector("input")?.value).toBe("Suggested Name");
    expect(host.textContent).toContain("Must be confirmed before the case can be sent");
    expect(host.textContent).not.toContain("(required)");
    expect([...host.querySelectorAll("button")].map(item => item.textContent)).toContain("Confirm");
  });

  it("shows only the status on a completed stage", () => {
    const value = run([stage({ status: "COMPLETE", confirmed_by: "maya-lim" })]);
    const host = render(<CaseWorkflowStages {...shared} canFill run={value} anchors={["DOCUMENT_IDP"]} />);
    expect(host.textContent).not.toContain("maya-lim");
    expect(host.querySelector(".stage-disclosure__summary")?.textContent).toBe("Status: Complete.");
  });

  it("only shows the stages that follow the given existing stages", () => {
    const host = render(<CaseWorkflowStages {...shared} canFill run={run()} anchors={["OWNERSHIP_UBO"]} />);
    expect(host.querySelector(".stage-disclosure")).toBeNull();
  });

  it("is read-only for the Director", () => {
    const host = render(<CaseWorkflowStages {...shared} canFill={false} run={run()} anchors={["DOCUMENT_IDP"]} />);
    expect(host.querySelector("input")?.disabled).toBe(true);
    expect([...host.querySelectorAll("button")].map(item => item.textContent)).not.toContain("Confirm");
  });

  it("hides the fields of a workflow stage that is not open yet", () => {
    const value = run([stage({ status: "LOCKED", after_node_id: null })], { is_onboarding: false, workflow_name: "Case refresh" });
    const host = render(<CaseWorkflowRuns {...shared} canFill runs={[value]} />);
    expect(host.textContent).toContain("Case refresh. Opens after the previous stage.");
    expect(host.querySelector("input")).toBeNull();
  });
});

// F-2 (ADR-017 P2-0): publication is frozen until P2-1, P2-2 and P3-1; the editor only saves drafts.
describe("workflow editor while publication is frozen", () => {
  let root: Root | null = null;
  afterEach(() => { act(() => root?.unmount()); root = null; document.body.innerHTML = ""; vi.unstubAllGlobals(); });

  const draftStage: WorkflowStage = {
    stage_id: "refresh-review", name: "Refresh review", after_node_id: null,
    fields: [{ field_id: "notes", label: "Notes", kind: "TEXT", required: true, options: [], autofill: false, document_label: null }],
  } as WorkflowStage;
  const workflow: WorkflowDetail = {
    workflow_id: "wf-refresh", name: "Case refresh", use_case: "Case refresh", country: "Singapore",
    case_source: "EXISTING_CASE", revision: 7, is_onboarding: false, status: "DRAFT", active_version: null,
    draft_stages: [draftStage], audit: [], locked_stages: [],
  };

  function render(element: JSX.Element) {
    const host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    act(() => root!.render(<QueryClientProvider client={new QueryClient()}>{element}</QueryClientProvider>));
    return host;
  }
  const buttons = (host: HTMLElement) => [...host.querySelectorAll("button")].map(item => item.textContent?.trim());

  it("offers no activate action and explains that publishing is paused", () => {
    const host = render(<WorkflowEditor workflow={workflow} workflows={[workflow]} onBack={() => {}} onSaved={() => {}} />);
    expect(buttons(host)).not.toContain("Save and activate");
    expect(host.textContent).not.toMatch(/activate/i);
    const notice = host.querySelector('[data-testid="workflow-publication-paused"]');
    expect(notice?.getAttribute("role")).toBe("note");
    expect(notice?.textContent).toContain("Publishing is paused.");
    expect(notice?.textContent).toContain("HR proposals and Director approval");
    const save = [...host.querySelectorAll("button")].find(item => item.textContent === "Save draft");
    expect(save?.disabled).toBe(true);
  });

  it("saves only the draft, with the same request body, and never calls the activation route", async () => {
    const saved: WorkflowDetail = { ...workflow, revision: 8, draft_stages: [{ ...draftStage, name: "Refresh review 2" }] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(saved), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const onSaved = vi.fn();
    const host = render(<WorkflowEditor workflow={workflow} workflows={[workflow]} onBack={() => {}} onSaved={onSaved} />);
    const nameInput = [...host.querySelectorAll("label")].find(item => item.textContent?.startsWith("Stage name"))!.querySelector("input")!;
    act(() => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(nameInput, "Refresh review 2");
      nameInput.dispatchEvent(new Event("input", { bubbles: true }));
    });
    const save = [...host.querySelectorAll("button")].find(item => item.textContent === "Save draft")!;
    expect(save.disabled).toBe(false);
    await act(async () => { save.click(); });
    await act(async () => { await Promise.resolve(); });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/workflows/wf-refresh/draft");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(String(init.body))).toEqual({ expected_revision: 7, stages: [{ ...draftStage, name: "Refresh review 2" }] });
    expect(fetchMock.mock.calls.some(call => String(call[0]).endsWith("/activate"))).toBe(false);
    expect(onSaved).toHaveBeenCalledWith(saved);
    expect(host.textContent).toContain("Draft saved. It is not published.");
  });

  it("explains a frozen-publication refusal in plain words and passes other messages through", () => {
    expect(workflowErrorMessage(new ApiError("raw", 409, "WORKFLOW_PUBLICATION_FROZEN")))
      .toBe("Publishing is paused while approval governance is introduced. Your draft is kept.");
    expect(workflowErrorMessage(new ApiError("This action is not permitted.", 403, "WORKFLOW_FORBIDDEN")))
      .toBe("This action is not permitted.");
    expect(workflowErrorMessage(new Error("x"))).toBe("That did not work. Please try again.");
  });
});
