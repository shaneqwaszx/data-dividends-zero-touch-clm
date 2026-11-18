// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import registryLegalFormSource from "../../backend/app/domain/registry_legal_form.py?raw";
import { ApiError, configureAuthenticatedTransport } from "./api";
import {
  CONDITIONAL_APPLICABILITY_OPTIONS,
  CONDITIONS_EXPLANATION,
  ENTITY_APPLICABILITY_OPTIONS,
  OTHER_EXPLANATION,
} from "./components/workflow-governance/EntityApplicability";
import { approvedVersionCount, LEGACY_PROVENANCE_NOTE } from "./components/workflow-governance/GovernancePanels";
import WorkflowManager from "./pages/WorkflowManager";
import type { AuthenticatedProfile } from "./types";
import * as workflowApi from "./workflowApi";
import type { WorkflowDetail, WorkflowStage } from "./workflowApi";
import {
  GOVERNANCE_ERROR_MESSAGES,
  RATCHET_RULE_EXPLANATIONS,
  governanceRefusal,
  issuesByRule,
} from "./workflowGovernanceApi";
import {
  CONDITIONAL_LEGAL_FORMS,
  GOVERNANCE_ERROR_CODES,
  PERMANENT_OBLIGATION_WARNING,
  type ProposalResponse,
  type ValidationReport,
  type WorkflowGovernanceView,
} from "./workflowGovernanceTypes";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// The same synthetic fixtures the backend contract test validates against the Pydantic models.
// Loaded as raw text (like uploadLimits.test.ts) so the file typechecks without Node types.
const FIXTURE_SOURCES = import.meta.glob("../../../docs/contracts/fixtures/workflow-governance/*.json", {
  query: "?raw", import: "default", eager: true,
}) as Record<string, string>;
function fixture<T>(name: string): T {
  const key = Object.keys(FIXTURE_SOURCES).find(path => path.endsWith(`/${name}`));
  if (!key) throw new Error(`Missing fixture ${name}`);
  return JSON.parse(FIXTURE_SOURCES[key]) as T;
}

const DRAFT = fixture<ProposalResponse>("proposal_draft.json");
const VIEW = fixture<WorkflowGovernanceView>("workflow_governance_view.json");
const VALID = fixture<ValidationReport>("validation_report_valid.json");
const REFUSED = fixture<ValidationReport>("validation_report_refused.json");
const WID = DRAFT.workflow_id;
const PID = DRAFT.proposal_id;

const hr: AuthenticatedProfile = {
  user_id: "synthetic-hr", display_name: "Synthetic HR", role: "HR", team_id: null, team_display_name: null,
  team_type: null, team_description: "", client_scope_label: "Global", capabilities: ["POLICY_VIEW", "POLICY_MUTATE"],
};
const director: AuthenticatedProfile = {
  ...hr, user_id: "synthetic-director", display_name: "Synthetic Director", role: "DIRECTOR",
  capabilities: ["POLICY_VIEW", "POLICY_APPROVE"],
};

const ACTIVE_STAGES: WorkflowStage[] = DRAFT.stages;
const CONFLICT_TEXT = "Someone else changed this workflow. Nothing was changed. Use Reload";

interface Call { method: string; url: string; body: unknown }
interface ServerOptions {
  proposal?: ProposalResponse | null;
  governance?: "migrated" | "not-migrated";
  canCreate?: boolean;
  validation?: ValidationReport;
  submitError?: { status: number; name: string };
  /** The next proposal update is refused with 409 WORKFLOW_CONFLICT because someone else moved the revision. */
  putConflictOnce?: boolean;
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

/** A tiny in-memory backend over the frozen fixtures; revisions move like the real CAS. */
function fakeServer(options: ServerOptions = {}) {
  let revision = 4;
  let proposal: ProposalResponse | null = options.proposal ?? null;
  const calls: Call[] = [];
  const control = {
    /** HTTP status for the next detail reads (0 = succeed). */
    failDetail: 0, failList: 0, putConflict: options.putConflictOnce ?? false,
    /** While set, proposal updates wait for it (a save in flight). */
    holdPut: null as Promise<void> | null,
  };
  const failure = (status: number) => status >= 500
    ? json({ detail: fixture("error_history_unavailable.json") }, status)
    : json({ detail: { code: status === 404 ? "WORKFLOW_NOT_FOUND" : "WORKFLOW_FORBIDDEN", message: "Server text." } }, status);
  const workflow = (): WorkflowDetail => ({
    workflow_id: WID, name: "Corporate onboarding", use_case: "Onboarding", country: "Singapore",
    case_source: "EXISTING_CASE", revision, is_onboarding: true, status: "ACTIVE", active_version: 2,
    draft_stages: [], audit: [],
    versions: [{ version: 2, stages: ACTIVE_STAGES, activated_at: "2026-11-17T10:00:00Z", activated_by: "director-synthetic-1" }],
    locked_stages: [
      { node_id: "DOCUMENT_IDP", label: "Document verification" },
      { node_id: "OWNERSHIP_UBO", label: "Ownership & UBO" },
      { node_id: "FINAL_REVIEW_SEND", label: "Final review & send" },
    ],
    governance: options.governance === "not-migrated" ? null : {
      ...VIEW, open_proposal: proposal, can_create_proposal: options.canCreate ?? true,
    },
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input);
    const method = (init.method ?? "GET").toUpperCase();
    const body = init.body ? JSON.parse(String(init.body)) as Record<string, unknown> : null;
    calls.push({ method, url, body });
    const base = `/api/workflows/${WID}`;
    if (method === "GET" && url === "/api/workflows") return control.failList ? failure(control.failList) : json([workflow()]);
    if (method === "GET" && url === "/api/workflows/simulation-scenarios") return json(fixture("simulation_scenarios.json"));
    if (method === "GET" && url === base) {
      if (control.failDetail) return failure(control.failDetail);
      return json(workflow());
    }
    if (method === "POST" && url === `${base}/proposals`) {
      proposal = { ...DRAFT, revision: 1, stages: ACTIVE_STAGES, note: (body?.note as string | undefined) ?? null };
      revision += 1;
      return json(proposal, 201);
    }
    if (method === "PUT" && url === `${base}/proposals/${PID}`) {
      if (control.holdPut) await control.holdPut;
      if (control.putConflict) {
        control.putConflict = false;
        // Someone else saved the same proposal (for example the author in another tab).
        proposal = { ...proposal!, revision: proposal!.revision + 1, stages: [{ ...proposal!.stages[0], name: "Changed elsewhere" }] };
        revision += 1;
        return json({ detail: { code: "WORKFLOW_CONFLICT", message: "Conflict." } }, 409);
      }
      proposal = { ...proposal!, stages: body!.stages as WorkflowStage[], revision: proposal!.revision + 1 };
      revision += 1;
      return json(proposal);
    }
    if (method === "POST" && url === `${base}/proposals/${PID}/validate`) return json(options.validation ?? VALID);
    if (method === "POST" && url === `${base}/proposals/${PID}/simulate`) return json(fixture("simulation_result.json"));
    if (method === "POST" && url === `${base}/proposals/${PID}/submit`) {
      if (options.submitError) return json({ detail: fixture(options.submitError.name) }, options.submitError.status);
      proposal = { ...proposal!, state: "PENDING_APPROVAL", revision: proposal!.revision + 1, can_edit: false, can_submit: false, content_hash: String(body!.content_hash) };
      revision += 1;
      return json(proposal);
    }
    if (method === "POST" && url === `${base}/proposals/${PID}/withdraw`) {
      const ended = { ...proposal!, state: "WITHDRAWN" as const };
      proposal = null;
      revision += 1;
      return json(ended);
    }
    return json({ detail: { code: "WORKFLOW_NOT_FOUND", message: "Not found." } }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, control, mutations: () => calls.filter(call => call.method !== "GET") };
}

let root: Root | null = null;
// M2 shows Release on another author's idle draft (14 days). Pin the clock a day after the fixtures'
// last activity so these M1 tests never start offering it as real time passes.
beforeEach(() => { vi.useFakeTimers({ toFake: ["Date"], now: new Date("2026-11-18T09:30:00Z") }); });
afterEach(() => {
  vi.useRealTimers();
  act(() => root?.unmount());
  root = null;
  document.body.innerHTML = "";
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function settle() {
  for (let index = 0; index < 8; index += 1) {
    await act(async () => { await new Promise(resolveTick => setTimeout(resolveTick, 0)); });
  }
}

async function openEditor(actor: AuthenticatedProfile = hr) {
  const host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  act(() => root!.render(<QueryClientProvider client={client}><WorkflowManager actor={actor} /></QueryClientProvider>));
  await settle();
  await click(host, "Edit");
  return host;
}

const buttons = (host: HTMLElement) => [...host.querySelectorAll("button")];
const buttonTexts = (host: HTMLElement) => buttons(host).map(item => item.textContent?.trim());
function button(host: HTMLElement, text: string): HTMLButtonElement {
  const found = buttons(host).find(item => item.textContent?.trim() === text);
  if (!found) throw new Error(`No button "${text}" in: ${buttonTexts(host).join(" | ")}`);
  return found;
}
async function click(host: HTMLElement, text: string) {
  await act(async () => { button(host, text).click(); });
  await settle();
}
function stageNameInput(host: HTMLElement): HTMLInputElement {
  return [...host.querySelectorAll("label")].find(item => item.textContent?.startsWith("Stage name"))!.querySelector("input")!;
}
function type(input: HTMLInputElement, value: string) {
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("HR proposal authoring (ADR-017 P2-2)", () => {
  it("creates a change, edits the draft, validates and submits it with the validated hash", async () => {
    const server = fakeServer();
    const host = await openEditor();
    expect(host.querySelector('[data-testid="propose-change"]')).not.toBeNull();
    expect(stageNameInput(host).matches(":disabled")).toBe(true);

    await click(host, "Propose a change");
    expect(server.mutations()[0]).toEqual({ method: "POST", url: `/api/workflows/${WID}/proposals`, body: { kind: "CHANGE", expected_workflow_revision: 4 } });
    expect(host.textContent).toContain("Open proposal · Draft");

    type(stageNameInput(host), "Sanctions attestation (updated)");
    expect(host.textContent).toContain("Unsaved changes");
    await click(host, "Save changes");
    const edited = [{ ...ACTIVE_STAGES[0], name: "Sanctions attestation (updated)" }];
    expect(server.mutations()[1]).toEqual({
      method: "PUT", url: `/api/workflows/${WID}/proposals/${PID}`,
      body: { expected_workflow_revision: 5, expected_proposal_revision: 1, stages: edited, note: null },
    });

    expect(button(host, "Submit for approval").disabled).toBe(true);
    await click(host, "Validate");
    expect(server.mutations()[2]).toEqual({ method: "POST", url: `/api/workflows/${WID}/proposals/${PID}/validate`, body: { stages: edited } });
    const report = host.querySelector('[data-testid="validation-report"]')!;
    expect(report.textContent).toContain("Ready to submit");
    expect(host.querySelector('[data-testid="validation-size"]')?.textContent).toContain("612 of 1,048,576 bytes");
    expect(host.querySelector('[data-testid="permanent-obligations"]')?.textContent).toContain(PERMANENT_OBLIGATION_WARNING);
    expect(host.querySelector('[data-testid="permanent-obligations"]')?.textContent).toContain("Screened by");

    expect(button(host, "Submit for approval").disabled).toBe(false);
    await click(host, "Submit for approval");
    expect(server.mutations()[3]).toEqual({
      method: "POST", url: `/api/workflows/${WID}/proposals/${PID}/submit`,
      body: { expected_workflow_revision: 6, expected_proposal_revision: 2, content_hash: VALID.content_hash },
    });
    expect(host.querySelector('[data-testid="proposal-status"]')?.textContent).toContain("Awaiting Director decision");
    expect(buttonTexts(host)).not.toContain("Submit for approval");
    expect(stageNameInput(host).matches(":disabled")).toBe(true);
  });

  it("keeps submit disabled after an edit until the content is validated again", async () => {
    fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    await click(host, "Validate");
    expect(button(host, "Submit for approval").disabled).toBe(false);

    type(stageNameInput(host), "Changed after validating");
    expect(button(host, "Submit for approval").disabled).toBe(true);
    await click(host, "Save changes");
    expect(button(host, "Submit for approval").disabled).toBe(true);
    expect(host.textContent).toContain("You changed the content after validating; validate again.");

    await click(host, "Validate");
    expect(button(host, "Submit for approval").disabled).toBe(false);
  });

  it("shows a validation refusal per rule and never enables submit", async () => {
    fakeServer({ proposal: DRAFT, validation: REFUSED });
    const host = await openEditor();
    await click(host, "Validate");
    const issues = host.querySelector('[data-testid="governance-issues"] [data-rule="RR-1"]');
    expect(issues?.textContent).toContain("RR-1");
    expect(issues?.textContent).toContain(RATCHET_RULE_EXPLANATIONS["RR-1"]);
    expect(issues?.textContent).toContain("The required stage 'Sanctions attestation' cannot be removed.");
    expect(host.textContent).toContain("Not ready to submit");
    expect(button(host, "Submit for approval").disabled).toBe(true);
  });

  it("shows a ratchet refusal on submit per rule id", async () => {
    fakeServer({ proposal: DRAFT, submitError: { status: 422, name: "error_ratchet_removed.json" } });
    const host = await openEditor();
    await click(host, "Validate");
    await click(host, "Submit for approval");
    const refusal = host.querySelector('[data-testid="governance-refusal"]')!;
    expect(refusal.getAttribute("role")).toBe("alert");
    expect(refusal.textContent).toContain(GOVERNANCE_ERROR_MESSAGES.WORKFLOW_REQUIRED_OBLIGATION_REMOVED);
    expect(refusal.querySelector('[data-rule="RR-1"]')?.textContent).toContain(RATCHET_RULE_EXPLANATIONS["RR-1"]);
  });

  it("shows a pending proposal read-only with Awaiting Director decision", async () => {
    const pending: ProposalResponse = { ...DRAFT, state: "PENDING_APPROVAL", can_edit: false, can_submit: false, content_hash: VALID.content_hash };
    fakeServer({ proposal: pending });
    const host = await openEditor();
    expect(host.querySelector('[data-testid="proposal-status"]')?.textContent).toContain("Awaiting Director decision");
    for (const label of ["Save changes", "Validate", "Simulate", "Submit for approval", "Propose a change"]) {
      expect(buttonTexts(host)).not.toContain(label);
    }
    expect(stageNameInput(host).matches(":disabled")).toBe(true);
    expect(buttonTexts(host)).toContain("Withdraw");
  });

  it("withdraws the open proposal after confirmation and offers a new one", async () => {
    const server = fakeServer({ proposal: DRAFT });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const host = await openEditor();
    await click(host, "Withdraw");
    expect(server.mutations()).toEqual([{
      method: "POST", url: `/api/workflows/${WID}/proposals/${PID}/withdraw`,
      body: { expected_workflow_revision: 4, expected_proposal_revision: 3 },
    }]);
    expect(host.textContent).toContain("Proposal withdrawn.");
    expect(buttonTexts(host)).toContain("Propose a change");
  });

  it("sends nothing when the withdrawal is not confirmed", async () => {
    const server = fakeServer({ proposal: DRAFT });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const host = await openEditor();
    await click(host, "Withdraw");
    expect(server.mutations()).toEqual([]);
  });

  it("runs a clearly synthetic simulation and shows whether the send is held", async () => {
    const server = fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    await click(host, "Simulate");
    const panel = host.querySelector('[data-testid="simulation-panel"]')!;
    expect(panel.textContent).toContain("Synthetic simulation");
    expect(panel.textContent).toContain("Company, clear screening (synthetic)");
    await click(host, "Run synthetic simulation");
    expect(server.mutations()).toEqual([{
      method: "POST", url: `/api/workflows/${WID}/proposals/${PID}/simulate`, body: { stages: DRAFT.stages, scenario_ids: [] },
    }]);
    const result = host.querySelector('[data-testid="simulation-result"]')!;
    expect(result.textContent).toContain("Send held");
    expect(result.textContent).toContain("Sanctions attestation");
    expect(result.textContent).toContain("required: Screened by, Screening outcome");
  });

  it("shows a not-migrated workflow without any authoring", async () => {
    const server = fakeServer({ governance: "not-migrated" });
    const host = await openEditor();
    const banner = host.querySelector('[data-testid="governance-not-enabled"]');
    expect(banner?.textContent).toContain("Workflow governance is not yet enabled.");
    for (const label of ["Propose a change", "Save changes", "Validate", "Submit for approval", "Withdraw", "Add after"]) {
      expect(buttonTexts(host)).not.toContain(label);
    }
    expect(stageNameInput(host).matches(":disabled")).toBe(true);
    expect(host.querySelector('[data-testid="version-history"]')).toBeNull();
    expect(server.mutations()).toEqual([]);
  });

  it("offers a Director no authoring, even with the page open", async () => {
    fakeServer({ canCreate: false });
    const host = await openEditor(director);
    expect(buttonTexts(host)).not.toContain("Propose a change");
    expect(host.textContent).toContain("Proposing changes is for HR authors.");
  });

  it("never labels or counts a legacy version as approved", async () => {
    fakeServer();
    const host = await openEditor();
    const legacy = host.querySelector('[data-testid="version-history"] [data-origin="PRE_GOVERNANCE_DIRECTOR_ACTIVATION"]')!;
    expect(legacy.textContent).toContain("Pre-governance · activated by director-legacy-1");
    expect(legacy.textContent).toContain(LEGACY_PROVENANCE_NOTE);
    expect(legacy.textContent).not.toMatch(/approved by/i);
    const governed = host.querySelector('[data-testid="version-history"] [data-origin="GOVERNED_APPROVAL"]')!;
    expect(governed.textContent).toContain("Proposed by hr-synthetic-1 · approved by director-synthetic-1");
    expect(host.querySelector('[data-testid="approved-count"]')?.textContent).toContain("2 versions · 1 approved through governance");
    expect(approvedVersionCount(VIEW.version_provenance)).toBe(1);
  });

  it("has retired Save draft: no button, no client function, no draft or activate request", async () => {
    const server = fakeServer({ proposal: DRAFT });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const host = await openEditor();
    expect(buttonTexts(host)).not.toContain("Save draft");
    expect(host.textContent).not.toContain("Publishing is paused");
    expect(host.querySelector('[data-testid="workflow-publication-paused"]')).toBeNull();
    expect(workflowApi).not.toHaveProperty("saveWorkflowDraft");
    type(stageNameInput(host), "Renamed");
    await click(host, "Save changes");
    await click(host, "Validate");
    await click(host, "Submit for approval");
    expect(server.calls.some(call => call.url.endsWith("/draft") || call.url.endsWith("/activate"))).toBe(false);
  });
});

// The enabled controls each role had in the P2-2 editor, outside the C-5 placeholder, plus the M2
// additions: View per version (both roles) and the Director-only emergency fallback entry point.
const HR_DRAFT_SURFACE = [
  "3. Sanctions attestation", "Add field", "Add stage after Document verification", "Add stage after Ownership & UBO",
  "Add stage after Sanctions attestation", "Confirm stage", "Remove field", "Remove field", "Remove field", "Remove stage",
  "Save changes (disabled)", "Simulate", "Submit for approval (disabled)", "Validate", "Withdraw",
  "input:Field name", "input:Field name", "input:Field name", "input:Options, separated by commas",
  "input:Required", "input:Required", "input:Required", "input:Stage name",
  "input:Try to fill from uploaded documents", "input:Try to fill from uploaded documents", "input:Try to fill from uploaded documents",
  "select:Field type", "select:Field type", "select:Field type", "select:Show after", "← Back to Workflows",
  "View v1", "View v2",
].sort();
const DIRECTOR_READ_ONLY_SURFACE = [
  "3. Sanctions attestation", "Close", "Remove field (disabled)", "Remove field (disabled)", "Remove field (disabled)",
  "input:Field name (disabled)", "input:Field name (disabled)", "input:Field name (disabled)",
  "input:Options, separated by commas (disabled)", "input:Required (disabled)", "input:Required (disabled)",
  "input:Required (disabled)", "input:Stage name (disabled)", "input:Try to fill from uploaded documents (disabled)",
  "input:Try to fill from uploaded documents (disabled)", "input:Try to fill from uploaded documents (disabled)",
  "select:Field type (disabled)", "select:Field type (disabled)", "select:Field type (disabled)",
  "select:Show after (disabled)", "← Back to Workflows",
  "View v1", "View v2", "Start emergency fallback",
].sort();

describe("editor resilience and role shaping (QG P3)", () => {
  it("keeps the editor and unsaved edits when a background refetch fails", async () => {
    const server = fakeServer({ proposal: DRAFT, putConflictOnce: true });
    const host = await openEditor();
    type(stageNameInput(host), "Unsaved edit");
    await click(host, "Save changes");
    expect(host.querySelector('[data-testid="governance-refusal"]')?.textContent).toContain(CONFLICT_TEXT);
    server.control.failDetail = 503;
    await click(host, "Reload");
    expect(host.querySelector('[data-testid="workflow-refresh-error"]')?.textContent).toContain("unsaved changes, is kept");
    expect(stageNameInput(host).value).toBe("Unsaved edit");
    expect(host.textContent).toContain("Unsaved changes");
    expect(buttonTexts(host)).toContain("Save changes");
  });

  async function conflictThenReload() {
    const server = fakeServer({ proposal: DRAFT, putConflictOnce: true });
    const host = await openEditor();
    await click(host, "Validate");
    expect(host.querySelector('[data-testid="validation-report"]')).not.toBeNull();
    type(stageNameInput(host), "Edited");
    await click(host, "Save changes");
    expect(host.querySelector('[data-testid="governance-refusal"]')?.textContent).toContain(CONFLICT_TEXT);
    const detailReads = () => server.calls.filter(call => call.method === "GET" && call.url === `/api/workflows/${WID}`).length;
    const before = detailReads();
    await click(host, "Reload");
    expect(detailReads()).toBe(before + 1);
    expect(host.querySelector('[data-testid="governance-refusal"]')).toBeNull();
    expect(host.querySelector('[data-testid="validation-report"]')).toBeNull();
    return { server, host };
  }

  it("never silently overwrites a proposal changed elsewhere: it shows the saved version and asks", async () => {
    const { server, host } = await conflictThenReload();
    const banner = host.querySelector('[data-testid="proposal-changed-elsewhere"]')!;
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.textContent).toContain("revision 4");
    expect(banner.textContent).toContain("based on revision 3");
    expect(host.querySelector('[data-testid="server-version"]')?.textContent).toContain("Changed elsewhere");
    expect(stageNameInput(host).value).toBe("Edited");
    expect(button(host, "Save changes").disabled).toBe(true);
    const writes = server.mutations().filter(call => call.method === "PUT").length;

    await click(host, "Keep my edits");
    expect(host.querySelector('[data-testid="proposal-changed-elsewhere"]')).toBeNull();
    expect(button(host, "Submit for approval").disabled).toBe(true);
    expect(server.mutations().filter(call => call.method === "PUT")).toHaveLength(writes);
    await click(host, "Save changes");
    expect(server.mutations().at(-1)?.body).toMatchObject({ expected_workflow_revision: 5, expected_proposal_revision: 4 });
    expect(button(host, "Submit for approval").disabled).toBe(true);
    await click(host, "Validate");
    expect(button(host, "Submit for approval").disabled).toBe(false);
  });

  it("can discard local edits and load the version saved elsewhere", async () => {
    const { server, host } = await conflictThenReload();
    const writes = server.mutations().filter(call => call.method === "PUT").length;
    await click(host, "Discard my edits and load the saved version");
    expect(host.querySelector('[data-testid="proposal-changed-elsewhere"]')).toBeNull();
    expect(stageNameInput(host).value).toBe("Changed elsewhere");
    expect(host.textContent).not.toContain("Unsaved changes");
    expect(button(host, "Save changes").disabled).toBe(true);
    expect(server.mutations().filter(call => call.method === "PUT")).toHaveLength(writes);
  });

  it("does not offer Reload as the remedy for a stale proposal", async () => {
    fakeServer({ proposal: DRAFT });
    // A STALE refusal body (frozen code) on submit.
    const stale = { code: "WORKFLOW_PROPOSAL_STALE", message: "Stale.", rule: null, issues: [] };
    const original = globalThis.fetch;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => String(input).endsWith("/submit")
      ? json({ detail: stale }, 409) : original(input, init)));
    const host = await openEditor();
    await click(host, "Validate");
    await click(host, "Submit for approval");
    const refusal = host.querySelector('[data-testid="governance-refusal"]')!;
    expect(refusal.textContent).toContain(GOVERNANCE_ERROR_MESSAGES.WORKFLOW_PROPOSAL_STALE);
    expect([...refusal.querySelectorAll("button")].map(item => item.textContent)).toEqual(["Show current status"]);
  });

  it.each([401, 403, 404])("drops the cached editor when a refetch returns %i", async status => {
    const onUnauthorized = vi.fn();
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized });
    const server = fakeServer({ proposal: DRAFT, putConflictOnce: true });
    const host = await openEditor();
    type(stageNameInput(host), "Unsaved edit");
    await click(host, "Save changes");
    server.control.failDetail = status;
    await click(host, "Reload");
    expect(host.querySelector('[aria-label="Stage settings"]')).toBeNull();
    expect(host.textContent).not.toContain("Unsaved edit");
    const unavailable = host.querySelector('[data-testid="workflow-unavailable"]')!.textContent;
    if (status !== 401) expect(unavailable).toBe("This workflow is not available.");
    // A 401 also goes through the existing session handling, which clears all user state.
    expect(onUnauthorized).toHaveBeenCalledTimes(status === 401 ? 1 : 0);
    configureAuthenticatedTransport({ csrfToken: null, onUnauthorized: null });
  });

  it("keeps the cache when access recovers before leaving", async () => {
    const server = fakeServer({ proposal: DRAFT, putConflictOnce: true });
    const host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    act(() => root!.render(<QueryClientProvider client={client}><WorkflowManager actor={hr} /></QueryClientProvider>));
    await settle();
    await click(host, "Edit");
    type(stageNameInput(host), "x");
    await click(host, "Save changes");
    server.control.failDetail = 404;
    await click(host, "Reload");
    expect(host.querySelector('[data-testid="workflow-unavailable"]')).not.toBeNull();
    server.control.failDetail = 0;
    const detailKey = ["auth", hr.user_id, "workflows", "detail", WID];
    await act(async () => { await client.refetchQueries({ queryKey: detailKey, exact: true }); });
    await settle();
    expect(host.querySelector('[aria-label="Stage settings"]')).not.toBeNull();
    expect(client.getQueryData(detailKey)).toBeDefined();
    await click(host, "← Back to Workflows");
    expect(client.getQueryData(detailKey)).toBeDefined();
  });

  it("keeps an edit made while a save is in flight marked unsaved", async () => {
    const server = fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    let release: () => void = () => undefined;
    server.control.holdPut = new Promise<void>(resolveHold => { release = resolveHold; });
    type(stageNameInput(host), "First");
    await click(host, "Save changes");
    type(stageNameInput(host), "Second");
    server.control.holdPut = null;
    await act(async () => { release(); });
    await settle();
    expect(server.mutations().filter(call => call.method === "PUT").map(call => (call.body as { stages: WorkflowStage[] }).stages[0].name)).toEqual(["First"]);
    expect(stageNameInput(host).value).toBe("Second");
    expect(host.textContent).toContain("Unsaved changes");
    expect(button(host, "Save changes").disabled).toBe(false);
    expect(host.querySelector('[data-testid="proposal-changed-elsewhere"]')).toBeNull();
    await click(host, "Save changes");
    expect(host.textContent).not.toContain("Unsaved changes");
  });

  it("removes the dropped workflow from the cache when leaving", async () => {
    const server = fakeServer({ proposal: DRAFT, putConflictOnce: true });
    const host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    act(() => root!.render(<QueryClientProvider client={client}><WorkflowManager actor={hr} /></QueryClientProvider>));
    await settle();
    await click(host, "Edit");
    type(stageNameInput(host), "x");
    await click(host, "Save changes");
    server.control.failDetail = 404;
    await click(host, "Reload");
    expect(client.getQueryData(["auth", hr.user_id, "workflows", "detail", WID])).toBeDefined();
    await click(host, "← Back to Workflows");
    expect(client.getQueryData(["auth", hr.user_id, "workflows", "detail", WID])).toBeUndefined();
  });

  it("shows a non-destructive banner with Reload when the list refetch fails", async () => {
    const server = fakeServer();
    const host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    act(() => root!.render(<QueryClientProvider client={client}><WorkflowManager actor={hr} /></QueryClientProvider>));
    await settle();
    server.control.failList = 503;
    await act(async () => { await client.refetchQueries({ queryKey: ["auth", hr.user_id, "workflows"], exact: true }); });
    await settle();
    expect(host.querySelector('[data-testid="workflow-list-refresh-error"]')?.textContent).toContain("may be out of date");
    expect(host.textContent).toContain("Corporate onboarding");
    server.control.failList = 0;
    await click(host, "Reload");
    expect(host.querySelector('[data-testid="workflow-list-refresh-error"]')).toBeNull();
    expect(host.textContent).toContain("Corporate onboarding");

    server.control.failList = 403;
    await act(async () => { await client.refetchQueries({ queryKey: ["auth", hr.user_id, "workflows"], exact: true }); });
    await settle();
    expect(host.textContent).not.toContain("Corporate onboarding");
  });

  it("shows New workflow only to holders of POLICY_MUTATE", async () => {
    fakeServer();
    for (const [actor, visible] of [[hr, true], [director, false]] as const) {
      const host = document.createElement("div");
      document.body.append(host);
      root = createRoot(host);
      act(() => root!.render(<QueryClientProvider client={new QueryClient()}><WorkflowManager actor={actor} /></QueryClientProvider>));
      await settle();
      expect(buttonTexts(host).includes("New workflow")).toBe(visible);
      act(() => root?.unmount());
      document.body.innerHTML = "";
    }
  });

  it("links the Simulate toggle to the panel it controls", async () => {
    fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    const toggle = button(host, "Simulate");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    await click(host, "Simulate");
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(document.getElementById(toggle.getAttribute("aria-controls")!)?.getAttribute("data-testid")).toBe("simulation-panel");
  });
});

describe("governance error messages", () => {
  it("maps every frozen governance code to an HR-facing message", () => {
    for (const code of GOVERNANCE_ERROR_CODES) {
      expect(GOVERNANCE_ERROR_MESSAGES[code]).toMatch(/\S/);
      expect(governanceRefusal(new ApiError("raw", 409, code)).message).toBe(GOVERNANCE_ERROR_MESSAGES[code]);
    }
    expect(Object.keys(GOVERNANCE_ERROR_MESSAGES).sort()).toEqual([...GOVERNANCE_ERROR_CODES].sort());
  });

  it("explains every ratchet rule and keeps the issues of a refusal body", () => {
    expect(Object.keys(RATCHET_RULE_EXPLANATIONS)).toEqual(["RR-1", "RR-2", "RR-3", "RR-4", "RR-5", "RR-6", "RR-7", "RR-8", "RR-9", "RR-10"]);
    const body = fixture<{ code: string; message: string }>("error_ratchet_removed.json");
    const refusal = governanceRefusal(new ApiError(body.message, 422, body.code, body as never));
    expect(refusal.rule).toBe("RR-1");
    expect(refusal.issues).toHaveLength(1);
    expect(governanceRefusal(new Error("x")).message).toBe("That did not work. Please try again.");
    expect(governanceRefusal(new ApiError("Some server text.", 500, null)).message).toBe("Some server text.");
  });

  it("groups issues in rule order with structure issues last", () => {
    const issue = (rule: ValidationReport["issues"][number]["rule"]) => ({ code: "X", rule, stage_id: null, field_id: null, message: String(rule) });
    expect(issuesByRule([issue(null), issue("RR-10"), issue("RR-2"), issue("RR-2")]).map(group => [group.rule, group.issues.length]))
      .toEqual([["RR-2", 2], ["RR-10", 1], [null, 1]]);
  });
});

describe("Entity applicability (ADR-018 §5, functional successor of C-5)", () => {
  const stageControl = (host: HTMLElement) => host.querySelector<HTMLFieldSetElement>('[data-testid="entity-stage-applies-to"]')!;
  const fieldControls = (host: HTMLElement) => [...host.querySelectorAll<HTMLFieldSetElement>('[data-testid="entity-field-applies-to"]')];
  const radio = (scope: Element, value: "ALL" | "ONLY") => scope.querySelector<HTMLInputElement>(`input[type="radio"][value="${value}"]`)!;
  const boxes = (scope: Element) => [...scope.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')];
  const box = (scope: Element, form: string) => boxes(scope).find(item => item.value === form)!;
  async function toggle(input: HTMLElement) {
    await act(async () => { input.click(); });
    await settle();
  }
  const describedBy = (item: Element) => (item.getAttribute("aria-describedby") ?? "").split(" ").filter(Boolean)
    .map(id => document.getElementById(id)?.textContent ?? "").join(" ");

  // (1) Sections render, with the fixed explanations and without "Coming soon".
  it("renders the workflow section and the step conditions with the fixed explanations", async () => {
    fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    const section = host.querySelector('[data-testid="entity-applicability"]')!;
    expect(section.textContent).toContain("Entity applicability");
    expect(section.textContent).toContain(CONDITIONS_EXPLANATION);
    expect(section.textContent).toContain(OTHER_EXPLANATION);
    expect(section.textContent).toContain("Every step and field applies to all entities.");
    const conditions = host.querySelector('[data-testid="entity-conditions"]')!;
    expect(conditions.textContent).toContain("Entity-specific conditions");
    expect(host.textContent).not.toContain("Coming soon");
  });

  // (2) Set selection and canonical request bodies: sorted, no duplicates, no key for All, field within stage.
  it("selects legal-form sets per stage and per field and sends the canonical bodies", async () => {
    const server = fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    await toggle(host.querySelector<HTMLButtonElement>('[aria-label="Add stage after Document verification"]')!);
    await click(host, "Add field");
    await toggle(radio(stageControl(host), "ONLY"));
    expect(boxes(stageControl(host)).map(item => item.value)).toEqual(["COMPANY", "BUSINESS_PARTNERSHIP", "LLP", "LP", "GOVERNMENT"]);
    for (const form of ["LP", "LLP", "COMPANY", "GOVERNMENT"]) await toggle(box(stageControl(host), form));
    // The full set is never offered: that is All entities.
    const fifth = box(stageControl(host), "BUSINESS_PARTNERSHIP");
    expect(fifth.disabled).toBe(true);
    expect(describedBy(fifth)).toContain("same as All entities");
    for (const form of ["COMPANY", "GOVERNMENT"]) await toggle(box(stageControl(host), form));

    await toggle(radio(fieldControls(host)[0], "ONLY"));
    expect(boxes(fieldControls(host)[0]).map(item => item.value)).toEqual(["LLP", "LP"]);
    await toggle(box(fieldControls(host)[0], "LP"));
    // A form used by a field stays selected on the stage (field within stage).
    expect(box(stageControl(host), "LP").disabled).toBe(true);

    await click(host, "Save changes");
    const saved = server.mutations()[0].body as { stages: WorkflowStage[] };
    expect(saved.stages[0]).not.toHaveProperty("applies_to");
    for (const item of saved.stages[0].fields) expect(item).not.toHaveProperty("applies_to");
    expect(saved.stages[1].applies_to).toEqual(["LLP", "LP"]);
    expect(saved.stages[1].after_node_id).toBe("DOCUMENT_IDP");
    expect(saved.stages[1].fields[0].applies_to).toEqual(["LP"]);
    expect(host.querySelector('[data-testid="entity-applicability"]')!.textContent).toContain("LLP, LP");

    await toggle(radio(stageControl(host), "ALL"));
    await click(host, "Save changes");
    const cleared = server.mutations()[1].body as { stages: WorkflowStage[] };
    expect(cleared.stages[1]).not.toHaveProperty("applies_to");
    expect(cleared.stages[1].fields[0].applies_to).toEqual(["LP"]);
    for (const call of server.calls) expect(JSON.stringify(call.body ?? {})).not.toContain("OTHER");
  });

  // (3) Request snapshot: unchanged content carries no applicability data.
  it("sends exactly the contract bodies, with no applies_to for unconditional content", async () => {
    const server = fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    type(stageNameInput(host), "Sanctions attestation 2");
    await click(host, "Save changes");
    await click(host, "Validate");
    await click(host, "Submit for approval");
    const stages = [{ ...DRAFT.stages[0], name: "Sanctions attestation 2" }];
    expect(server.mutations().map(call => call.body)).toEqual([
      { expected_workflow_revision: 4, expected_proposal_revision: 3, stages, note: DRAFT.note },
      { stages },
      { expected_workflow_revision: 5, expected_proposal_revision: 4, content_hash: VALID.content_hash },
    ]);
    for (const call of server.calls) {
      expect(call.url).not.toMatch(/applicab|entity|legal/i);
      expect(JSON.stringify(call.body ?? {})).not.toMatch(/applies_to|legal_form|ALL_ENTITIES/i);
    }
  });

  // (4) Parity with the backend enums; OTHER is never selectable.
  it("lists exactly the backend RegistryLegalForm values and offers only ConditionalLegalForm", async () => {
    const source = registryLegalFormSource;
    const values = (name: string) => [...source.split(`class ${name}(StrEnum):`)[1].split(/\n(?=\S)/)[0]
      .matchAll(/^\s+([A-Z_]+) = (?:"([A-Z_]+)"|RegistryLegalForm\.([A-Z_]+)\.value)/gm)].map(match => match[2] ?? match[3]);
    const registry = values("RegistryLegalForm");
    const conditional = values("ConditionalLegalForm");
    expect(registry.length).toBeGreaterThan(0);
    expect(ENTITY_APPLICABILITY_OPTIONS.map(item => item.value)).toEqual(registry);
    expect(CONDITIONAL_APPLICABILITY_OPTIONS.map(item => item.value)).toEqual(conditional);
    expect([...conditional].sort()).toEqual([...CONDITIONAL_LEGAL_FORMS]);
    expect(conditional).not.toContain("OTHER");

    fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    await toggle(host.querySelector<HTMLButtonElement>('[aria-label="Add stage after Document verification"]')!);
    await toggle(radio(stageControl(host), "ONLY"));
    expect(boxes(host).some(item => item.value === "OTHER")).toBe(false);
  });

  // (5) Roles and the ratchet: Directors read only; HR is refused RR-8 narrowing of published required content.
  it("shapes HR by RR-8 and shows Directors read-only controls, leaving other controls as they were", async () => {
    const surface = (host: HTMLElement) => [...host.querySelectorAll<HTMLElement>("button, input, select")]
      .filter(item => !item.closest('[data-testid^="entity-"]'))
      .map(item => {
        const name = item.getAttribute("aria-label")
          ?? (item.tagName === "BUTTON" ? item.textContent?.trim() : `${item.tagName.toLowerCase()}:${[...(item.closest("label")?.childNodes ?? [])].find(child => child.nodeType === Node.TEXT_NODE && child.textContent?.trim())?.textContent?.trim() ?? ""}`);
        return `${name}${item.matches(":disabled") ? " (disabled)" : ""}`;
      })
      .sort();

    fakeServer({ proposal: DRAFT });
    const hrHost = await openEditor(hr);
    expect(surface(hrHost)).toEqual(HR_DRAFT_SURFACE);
    // The published stage holds required fields: making it conditional would narrow it (RR-8).
    expect(radio(stageControl(hrHost), "ONLY").disabled).toBe(true);
    expect(describedBy(radio(stageControl(hrHost), "ONLY"))).toContain("RR-8");
    const [screenedBy, outcome, comment] = fieldControls(hrHost);
    expect(radio(screenedBy, "ONLY").disabled).toBe(true);
    expect(radio(outcome, "ONLY").disabled).toBe(true);
    expect(radio(comment, "ONLY").disabled).toBe(false);
    act(() => root?.unmount());
    document.body.innerHTML = "";

    fakeServer({ proposal: { ...DRAFT, can_edit: false, can_submit: false, can_withdraw: false }, canCreate: false });
    const directorHost = await openEditor(director);
    expect(surface(directorHost)).toEqual(DIRECTOR_READ_ONLY_SURFACE);
    const controls = [...directorHost.querySelectorAll<HTMLInputElement>('[data-testid^="entity-"] input')];
    expect(controls.length).toBeGreaterThan(0);
    expect(controls.every(item => item.disabled)).toBe(true);
  });

  // (6) Accessibility: named sections, legends, and every disabled control is described.
  it("is accessible", async () => {
    fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    const section = host.querySelector<HTMLElement>('[data-testid="entity-applicability"]')!;
    expect(document.getElementById(section.getAttribute("aria-labelledby")!)?.textContent).toBe("Entity applicability");
    expect(stageControl(host).querySelector("legend")?.textContent).toBe("Show this step for");
    expect(fieldControls(host).map(item => item.querySelector("legend")?.textContent)).toEqual([
      'Collect "Screened by" for', 'Collect "Screening outcome" for', 'Collect "Comment" for',
    ]);
    const disabled = [...host.querySelectorAll<HTMLElement>('[data-testid^="entity-"] [aria-disabled="true"]')];
    expect(disabled.length).toBeGreaterThan(0);
    for (const item of disabled) {
      expect((item as HTMLInputElement).disabled).toBe(true);
      expect(describedBy(item).trim().length).toBeGreaterThan(0);
      expect(item.getAttribute("tabindex")).toBeNull();
    }
  });

  // (7) Regression: the existing editor behaviour around the controls is unchanged.
  it("keeps the existing stage editor order and reuse controls", async () => {
    fakeServer({ proposal: DRAFT });
    const host = await openEditor();
    const rows = [...host.querySelectorAll('[aria-label="Pipeline stages"] li')].map(item => item.textContent);
    expect(rows[0]).toContain("1. Document verification");
    expect(rows[1]).toContain("2. Ownership & UBO");
    expect(rows[2]).toContain("3. Sanctions attestation");
    expect(rows[3]).toContain("4. Final review & send");
    expect(host.querySelector('[aria-label="Add stage after Ownership & UBO"]')).not.toBeNull();
    expect(buttonTexts(host)).toContain("Add field");
  });
});
