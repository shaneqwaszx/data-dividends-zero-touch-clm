// @vitest-environment jsdom
// M2 recovery and administration (ADR-017 §1.2, §1.4, §4; contract CC-4), against mocked fetch.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { approvedVersionCount } from "./components/workflow-governance/GovernancePanels";
import WorkflowApprovals from "./pages/WorkflowApprovals";
import WorkflowCompare from "./pages/WorkflowCompare";
import WorkflowManager from "./pages/WorkflowManager";
import { governanceFixtures } from "./test-fixtures/workflowGovernance";
import type { AuthenticatedProfile } from "./types";
import type { WorkflowDetail, WorkflowStage } from "./workflowApi";
import { approvalErrorView } from "./workflowApprovalsApi";
import { ApiError } from "./api";
import { GOVERNANCE_ERROR_MESSAGES } from "./workflowGovernanceApi";
import type {
  DecidedProposalSummary,
  DecisionResponse,
  EmergencyFallbackResponse,
  GovernanceNotice,
  NoticeItem,
  ProposalKind,
  ProposalResponse,
  VersionProvenance,
  WorkflowGovernanceView,
  WorkflowVersionResponse,
} from "./workflowGovernanceTypes";
import {
  copyableProposal,
  deactivateRequest,
  emergencyFallbackRequest,
  offerDraftRelease,
  provenanceText,
  reactivateRequest,
  resetToDefaultRequest,
  restoreVersionRequest,
} from "./workflowRecoveryApi";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const NOW = new Date("2026-12-10T09:00:00Z");
const WID = "corporate-onboarding";
const OTHER = "supplier-review";
const PID = "11111111-2222-4333-8444-555555555555";

const hr: AuthenticatedProfile = {
  user_id: "synthetic-hr", display_name: "Synthetic HR", role: "HR", team_id: null, team_display_name: null,
  team_type: null, team_description: "", client_scope_label: "Global", capabilities: ["POLICY_VIEW", "POLICY_MUTATE"],
};
const director: AuthenticatedProfile = {
  ...hr, user_id: "synthetic-director", display_name: "Synthetic Director", role: "DIRECTOR",
  capabilities: ["POLICY_VIEW", "POLICY_APPROVE"],
};

const field = (id: string, label: string) => ({ field_id: id, label, kind: "TEXT" as const, required: true, options: [], autofill: false, document_label: null });
const V1_STAGES: WorkflowStage[] = [{ stage_id: "sanctions", name: "Sanctions attestation", fields: [field("screened-by", "Screened by")], after_node_id: "OWNERSHIP_UBO" }];
const V2_STAGES: WorkflowStage[] = [{ ...V1_STAGES[0], fields: [...V1_STAGES[0].fields, field("screened-on", "Screened on")] }];

const PROVENANCE: VersionProvenance[] = [
  { version: 1, origin: "PRE_GOVERNANCE_DIRECTOR_ACTIVATION", author_id: null, approved_by: null, proposal_id: null, activated_by: "director-legacy-1", published_at: "2026-11-17T09:00:00Z", note: null },
  { version: 2, origin: "GOVERNED_APPROVAL", author_id: "hr-synthetic-1", approved_by: "director-synthetic-1", proposal_id: "p-2", activated_by: null, published_at: "2026-11-17T10:00:00Z", note: null },
];
const EMERGENCY: VersionProvenance = {
  version: 3, origin: "EMERGENCY_FALLBACK", author_id: null, approved_by: null, proposal_id: null, activated_by: "director-synthetic-1", published_at: "2026-11-20T10:00:00Z", note: null,
};

function proposal(overrides: Partial<ProposalResponse> = {}): ProposalResponse {
  return {
    proposal_id: PID, workflow_id: WID, kind: "CHANGE", state: "DRAFT", origin: "GOVERNED", revision: 1, base_version: 2,
    stages: V2_STAGES, note: null, author_id: hr.user_id, legacy_editor: null, created_at: "2026-12-09T09:00:00Z",
    updated_at: "2026-12-09T09:00:00Z", last_activity_at: "2026-12-09T09:00:00Z", submitted_at: null, content_hash: null,
    decided_at: null, decided_by: null, decision_reason: null, published_version: null, stale_by_version: null,
    can_edit: true, can_submit: true, can_withdraw: true, can_decide: false, ...overrides,
  };
}

function decided(overrides: Partial<DecidedProposalSummary>): DecidedProposalSummary {
  return {
    proposal_id: "d-0", kind: "CHANGE", state: "WITHDRAWN", origin: "GOVERNED", author_id: "hr-synthetic-1",
    decided_by: null, decided_at: null, ended_at: "2026-11-18T10:00:00Z", published_version: null, ...overrides,
  };
}

function notice(overrides: Partial<GovernanceNotice> = {}): GovernanceNotice {
  return {
    notice_id: "n-1", kind: "EMERGENCY_FALLBACK", raised_at: "2026-11-20T10:00:00Z", raised_by: "director-synthetic-1",
    version: 3, reason: "Sanctions step blocked every case overnight", acknowledged_by: null, acknowledged_at: null, ...overrides,
  };
}

interface Call { method: string; url: string; body: unknown; signal: AbortSignal | null }
interface Options {
  workflowId?: string;
  onboarding?: boolean;
  activeVersion?: number;
  open?: ProposalResponse | null;
  canCreate?: boolean;
  provenance?: VersionProvenance[];
  decidedProposals?: DecidedProposalSummary[];
  notices?: NoticeItem[] | null;
  /** Status and code for the next request to this route suffix. */
  refuse?: Record<string, { status: number; code: string }>;
}

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const refusal = (status: number, code: string) => json({ detail: { code, message: "Server text.", rule: null, issues: [] } }, status);

function server(options: Options = {}) {
  const wid = options.workflowId ?? WID;
  let revision = 4;
  let open = options.open ?? null;
  let notices = options.notices === undefined ? [] : options.notices;
  const refuse = { ...(options.refuse ?? {}) };
  const calls: Call[] = [];
  const governance = (): WorkflowGovernanceView => ({
    migrated: true, latest_version: (options.provenance ?? PROVENANCE).length, open_proposal: open,
    decided_proposals: options.decidedProposals ?? [], version_provenance: options.provenance ?? PROVENANCE,
    baseline: { seeded_from_version: 1, updated_at_version: 2, required_stages: 1, required_fields: 2 },
    recent_events: [], unacknowledged_notices: [], can_create_proposal: (options.canCreate ?? true) && open === null,
  });
  const onboarding = options.onboarding ?? true;
  const workflow = (): WorkflowDetail => ({
    workflow_id: wid, name: onboarding ? "Corporate onboarding" : "Supplier review", use_case: "Use case", country: "Singapore",
    case_source: "EXISTING_CASE", revision, is_onboarding: onboarding, status: "ACTIVE", active_version: options.activeVersion ?? 2,
    draft_stages: [], audit: [],
    versions: [{ version: 2, stages: V2_STAGES, activated_at: "2026-11-17T10:00:00Z", activated_by: "director-synthetic-1" }],
    locked_stages: onboarding ? [
      { node_id: "DOCUMENT_IDP", label: "Document verification" },
      { node_id: "OWNERSHIP_UBO", label: "Ownership & UBO" },
      { node_id: "FINAL_REVIEW_SEND", label: "Final review & send" },
    ] : [],
    governance: governance(),
  });
  const version = (n: number): WorkflowVersionResponse => ({
    workflow_id: wid, is_active: n === (options.activeVersion ?? 2),
    version: { version: n, stages: n === 1 ? V1_STAGES : V2_STAGES, activated_at: "2026-11-17T10:00:00Z", activated_by: "director-legacy-1" },
    provenance: (options.provenance ?? PROVENANCE).find(item => item.version === n) ?? null,
  });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input);
    const method = (init.method ?? "GET").toUpperCase();
    const body = init.body ? JSON.parse(String(init.body)) as Record<string, unknown> : null;
    calls.push({ method, url, body, signal: init.signal ?? null });
    const base = `/api/workflows/${wid}`;
    const suffix = url.startsWith(base) ? url.slice(base.length) : url;
    if (method !== "GET" && refuse[suffix]) {
      const { status, code } = refuse[suffix];
      delete refuse[suffix];
      return refusal(status, code);
    }
    if (method === "GET" && url === "/api/workflows") return json([workflow()]);
    if (method === "GET" && url === "/api/workflows/notices") return notices === null ? json({ detail: { code: "WORKFLOW_NOT_FOUND", message: "x" } }, 404) : json({ items: notices });
    if (method === "POST" && url.startsWith("/api/workflows/notices/")) {
      if (refuse.ack) { const { status, code } = refuse.ack; delete refuse.ack; return refusal(status, code); }
      notices = (notices ?? []).filter(item => !url.includes(item.notice.notice_id));
      return json({});
    }
    if (method === "GET" && url === base) return json(workflow());
    const versionMatch = /^\/versions\/(\d+)$/.exec(suffix);
    if (method === "GET" && versionMatch) return json(version(Number(versionMatch[1])));
    if (method === "POST" && suffix === "/proposals") {
      const kind = body!.kind as ProposalKind;
      const stages = kind === "DEACTIVATE" ? [] : kind === "RESTORE_VERSION" ? V1_STAGES : kind === "REACTIVATE" ? body!.stages as WorkflowStage[] : V2_STAGES;
      // Mirrors the backend: fixed-content kinds are not editable but their author may submit.
      const computed = kind === "RESTORE_VERSION" || kind === "RESET_TO_DEFAULT" || kind === "DEACTIVATE";
      open = proposal({ kind, stages, author_id: hr.user_id, can_edit: !computed, can_submit: true });
      revision += 1;
      return json(open, 201);
    }
    if (method === "POST" && suffix === `/proposals/${open?.proposal_id}/validate`) {
      return json({ ...governanceFixtures.validationReportValid(), content_hash: "hash-m2", permanent_obligations: [] });
    }
    if (method === "POST" && suffix === `/proposals/${open?.proposal_id}/submit`) {
      open = { ...open!, state: "PENDING_APPROVAL", revision: open!.revision + 1, can_edit: false, can_submit: false, content_hash: "hash-m2" };
      revision += 1;
      return json(open);
    }
    if (method === "POST" && suffix === `/proposals/${open?.proposal_id}/release`) {
      const released = { ...open!, state: "WITHDRAWN" as const };
      open = null;
      revision += 1;
      return json(released);
    }
    const copyMatch = /^\/proposals\/([^/]+)\/copy$/.exec(suffix);
    if (method === "POST" && copyMatch) {
      open = proposal({ proposal_id: "copied-1", author_id: hr.user_id });
      revision += 1;
      return json(open, 201);
    }
    if (method === "POST" && suffix === "/emergency-fallback") {
      const response: EmergencyFallbackResponse = {
        workflow_revision: revision + 1, active_version: 3, published_version: 3, provenance: EMERGENCY,
        notice: notice(), staled_proposal_ids: open ? [open.proposal_id] : [], publication_report: null,
      };
      open = null;
      revision += 1;
      return json(response);
    }
    return json({ detail: { code: "WORKFLOW_NOT_FOUND", message: "Not found." } }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return {
    calls,
    mutations: () => calls.filter(call => call.method !== "GET").map(({ method, url, body }) => ({ method, url, body })),
    setNotices: (next: NoticeItem[]) => { notices = next; },
  };
}

let root: Root | null = null;
let host: HTMLDivElement;
beforeEach(() => { vi.useFakeTimers({ toFake: ["Date"], now: NOW }); });
afterEach(() => {
  act(() => root?.unmount());
  root = null;
  document.body.innerHTML = "";
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function settle() {
  for (let index = 0; index < 10; index += 1) {
    await act(async () => { await new Promise(resolveTick => setTimeout(resolveTick, 0)); });
  }
}

async function render(node: ReactNode) {
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  act(() => root!.render(<QueryClientProvider client={client}>{node}</QueryClientProvider>));
  await settle();
}

async function openEditor(actor: AuthenticatedProfile = hr) {
  await render(<WorkflowManager actor={actor} />);
  await click("Edit");
}

const buttons = () => [...host.querySelectorAll("button")];
const texts = () => buttons().map(item => item.textContent?.trim());
function button(text: string, scope: ParentNode = host): HTMLButtonElement {
  const found = [...scope.querySelectorAll("button")].find(item => item.textContent?.trim() === text);
  if (!found) throw new Error(`No button "${text}" in: ${texts().join(" | ")}`);
  return found;
}
async function click(text: string, scope: ParentNode = host) {
  await act(async () => { button(text, scope).click(); });
  await settle();
}
function setValue(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  act(() => {
    Object.getOwnPropertyDescriptor(prototype, "value")!.set!.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}
const section = (testId: string) => host.querySelector<HTMLElement>(`[data-testid="${testId}"]`);

describe("request builders (CC-4)", () => {
  it("never puts stages on restore, reset or deactivate, and trims or omits the note", () => {
    expect(restoreVersionRequest(4, 1)).toEqual({ kind: "RESTORE_VERSION", expected_workflow_revision: 4, restore_target_version: 1 });
    expect(resetToDefaultRequest(4, "  back to default  ")).toEqual({ kind: "RESET_TO_DEFAULT", expected_workflow_revision: 4, note: "back to default" });
    expect(deactivateRequest(4, "   ")).toEqual({ kind: "DEACTIVATE", expected_workflow_revision: 4 });
    expect(reactivateRequest(4, V2_STAGES)).toEqual({ kind: "REACTIVATE", expected_workflow_revision: 4, stages: V2_STAGES });
    expect(emergencyFallbackRequest(4, "  urgent reason text ", "DEFAULT")).toEqual({ reason: "urgent reason text", expected_workflow_revision: 4, target: "DEFAULT" });
    expect(emergencyFallbackRequest(4, "urgent reason text", { version: 1 })).toEqual({ reason: "urgent reason text", expected_workflow_revision: 4, target: "VERSION", target_version: 1 });
  });

  it("labels only governed approvals as approved", () => {
    expect(provenanceText(PROVENANCE[0])).toBe("Pre-governance · activated by director-legacy-1");
    expect(provenanceText(EMERGENCY)).toBe("Emergency fallback by director-synthetic-1 — not approved");
    expect(provenanceText(PROVENANCE[1])).toBe("Proposed by hr-synthetic-1 · approved by director-synthetic-1");
    expect(approvedVersionCount([...PROVENANCE, EMERGENCY])).toBe(1);
  });

  it("shapes release and copy offers only (the backend decides)", () => {
    const idle = proposal({ author_id: "hr-other", last_activity_at: "2026-11-26T09:00:00Z" });
    expect(offerDraftRelease(idle, hr, NOW.getTime())).toBe(true);
    expect(offerDraftRelease({ ...idle, last_activity_at: "2026-11-27T09:00:01Z" }, hr, NOW.getTime())).toBe(false);
    expect(offerDraftRelease({ ...idle, author_id: hr.user_id }, hr, NOW.getTime())).toBe(false);
    expect(offerDraftRelease(idle, director, NOW.getTime())).toBe(false);
    expect(offerDraftRelease({ ...idle, state: "PENDING_APPROVAL" }, hr, NOW.getTime())).toBe(false);
    expect(copyableProposal({ state: "WITHDRAWN", origin: "GOVERNED" })).toBe(true);
    expect(copyableProposal({ state: "STALE", origin: "GOVERNED" })).toBe(true);
    expect(copyableProposal({ state: "WITHDRAWN", origin: "PRE_GOVERNANCE_DRAFT" })).toBe(true);
    expect(copyableProposal({ state: "APPROVED", origin: "GOVERNED" })).toBe(false);
    expect(copyableProposal({ state: "REJECTED", origin: "GOVERNED" })).toBe(false);
  });

  it("has an M2 message for every new code and treats RUN_CONFIRMATION_IN_PROGRESS as retry-later", () => {
    for (const code of ["WORKFLOW_DRAFT_NOT_RELEASABLE", "WORKFLOW_NOTICES_UNACKNOWLEDGED", "WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS", "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE"] as const) {
      expect(GOVERNANCE_ERROR_MESSAGES[code]).toMatch(/Nothing was changed/);
    }
    const view = approvalErrorView(new ApiError("x", 409, "WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS"));
    expect(view).toMatchObject({ reload: false, retryLater: true, refused: false });
    expect(view.message).toMatch(/Try again in a moment/);
    expect(approvalErrorView(new ApiError("x", 409, "WORKFLOW_CONFLICT"))).toMatchObject({ reload: true, retryLater: false });
  });
});

describe("History & recovery (HR)", () => {
  it("shows provenance and never calls legacy or emergency versions approved", async () => {
    server({ provenance: [...PROVENANCE, EMERGENCY], activeVersion: 3 });
    await openEditor();
    const history = section("version-history")!;
    const legacy = history.querySelector('[data-origin="PRE_GOVERNANCE_DIRECTOR_ACTIVATION"]')!;
    expect(legacy.textContent).toContain("Activated by a Director before approval governance; not independently approved.");
    expect(legacy.textContent).not.toMatch(/approved by/i);
    const emergency = history.querySelector('[data-origin="EMERGENCY_FALLBACK"]')!;
    expect(emergency.textContent).toContain("Emergency fallback by director-synthetic-1 — not approved");
    expect(emergency.textContent).not.toMatch(/approved by/i);
    expect(section("approved-count")!.textContent).toContain("3 versions · 1 approved through governance");
  });

  it("views a version read-only through versions/{n} with an AbortSignal", async () => {
    const api = server();
    await openEditor();
    await click("View v1");
    const view = section("version-view")!;
    expect(view.textContent).toContain("Version 1 (read-only)");
    expect(view.textContent).toContain("Sanctions attestation · 1 field");
    expect(view.textContent).toContain("Pre-governance · activated by director-legacy-1");
    expect(view.textContent).not.toMatch(/approved/i);
    const read = api.calls.find(call => call.url === `/api/workflows/${WID}/versions/1`)!;
    expect(read.signal).toBeInstanceOf(AbortSignal);
    expect(api.mutations()).toEqual([]);
  });

  it("proposes restore of v1 with no stages, then validates and submits the backend-computed content", async () => {
    const api = server();
    await openEditor();
    expect(texts()).not.toContain("Propose restore of v2"); // v2 is active
    await click("Propose restore of v1");
    const confirm = section("recovery-confirm")!;
    expect(confirm.textContent).toContain("safe target");
    expect(confirm.textContent).toContain("No required obligation is dropped");
    expect(confirm.textContent).toContain("one Director must approve it");
    expect(api.mutations()).toEqual([]);
    await click("Create proposal");
    expect(api.mutations()).toEqual([{ method: "POST", url: `/api/workflows/${WID}/proposals`, body: { kind: "RESTORE_VERSION", expected_workflow_revision: 4, restore_target_version: 1 } }]);
    expect(Object.keys(api.mutations()[0].body as object)).not.toContain("stages");

    expect(section("proposal-kind")!.textContent).toBe("Restore an earlier version");
    expect(section("proposal-status")!.textContent).toContain("safe target");
    // Backend-computed content: no editing, only validate and submit.
    expect(texts()).not.toContain("Save changes");
    expect(texts()).not.toContain("Add field");
    expect(button("Submit for approval").disabled).toBe(true);
    await click("Validate");
    await click("Submit for approval");
    expect(api.mutations().slice(1)).toEqual([
      { method: "POST", url: `/api/workflows/${WID}/proposals/${PID}/validate`, body: {} },
      { method: "POST", url: `/api/workflows/${WID}/proposals/${PID}/submit`, body: { expected_workflow_revision: 5, expected_proposal_revision: 1, content_hash: "hash-m2" } },
    ]);
  });

  it("proposes reset to default with an optional note and no stages", async () => {
    const api = server();
    await openEditor();
    await click("Propose reset to default");
    setValue(section("recovery-confirm")!.querySelector("input")!, "  Back to the built-in steps  ");
    await click("Create proposal");
    expect(api.mutations()).toEqual([{ method: "POST", url: `/api/workflows/${WID}/proposals`, body: { kind: "RESET_TO_DEFAULT", expected_workflow_revision: 4, note: "Back to the built-in steps" } }]);
  });

  it("hides every create action while a proposal is open (one open proposal)", async () => {
    server({ open: proposal(), decidedProposals: [decided({ proposal_id: "d-1" })] });
    await openEditor();
    expect(section("recovery-blocked")!.textContent).toContain("Only one proposal can be open per workflow");
    for (const label of ["Propose restore of v1", "Propose reset to default", "Copy into new draft", "Propose deactivate"]) {
      expect(texts()).not.toContain(label);
    }
  });

  it("offers onboarding no deactivate or reactivate", async () => {
    server();
    await openEditor();
    expect(texts()).not.toContain("Propose deactivate");
    expect(texts()).not.toContain("Propose reactivate");
  });

  it("proposes deactivate of an active non-onboarding workflow with no stages", async () => {
    const api = server({ workflowId: OTHER, onboarding: false });
    await openEditor();
    await click("Propose deactivate");
    expect(section("recovery-confirm")!.textContent).toContain("Existing runs keep their stages and stay completable");
    await click("Create proposal");
    expect(api.mutations()).toEqual([{ method: "POST", url: `/api/workflows/${OTHER}/proposals`, body: { kind: "DEACTIVATE", expected_workflow_revision: 4 } }]);
    expect(section("proposal-kind")!.textContent).toBe("Deactivate");
    await click("Validate");
    expect(api.mutations()[1]).toEqual({ method: "POST", url: `/api/workflows/${OTHER}/proposals/${PID}/validate`, body: {} });
  });

  it("proposes reactivate from the latest version's stages and opens the editor", async () => {
    const api = server({ workflowId: OTHER, onboarding: false, activeVersion: 0 });
    await openEditor();
    expect(section("workflow-deactivated")!.textContent).toContain("new runs are blocked");
    expect(texts()).not.toContain("Propose deactivate");
    await click("Propose reactivate");
    await click("Create proposal");
    expect(api.calls.some(call => call.method === "GET" && call.url === `/api/workflows/${OTHER}/versions/2`)).toBe(true);
    expect(api.mutations()).toEqual([{ method: "POST", url: `/api/workflows/${OTHER}/proposals`, body: { kind: "REACTIVATE", expected_workflow_revision: 4, stages: V2_STAGES } }]);
    // Reactivate is edited like a change: Save, Validate, Simulate, Submit.
    expect(section("proposal-kind")!.textContent).toBe("Reactivate");
    expect(texts()).toContain("Save changes");
    expect(texts()).toContain("Add stage");
  });

  it("shows a refusal and changes nothing locally on 422 KIND_NOT_AVAILABLE", async () => {
    server({ workflowId: OTHER, onboarding: false, refuse: { "/proposals": { status: 422, code: "WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE" } } });
    await openEditor();
    await click("Propose deactivate");
    await click("Create proposal");
    expect(section("governance-refusal")!.textContent).toContain(GOVERNANCE_ERROR_MESSAGES.WORKFLOW_PROPOSAL_KIND_NOT_AVAILABLE);
    expect(section("proposal-status")).toBeNull();
  });

  it("copies withdrawn, stale and legacy proposals only, into a new draft", async () => {
    const api = server({
      decidedProposals: [
        decided({ proposal_id: "d-withdrawn", ended_at: "2026-11-21T10:00:00Z" }),
        decided({ proposal_id: "d-legacy", origin: "PRE_GOVERNANCE_DRAFT", author_id: null, ended_at: "2026-11-17T08:00:00Z" }),
        decided({ proposal_id: "d-approved", state: "APPROVED", decided_by: "director-synthetic-1", published_version: 2, ended_at: "2026-11-17T10:00:00Z" }),
        decided({ proposal_id: "d-stale", state: "STALE", ended_at: "2026-11-20T10:00:00Z" }),
      ],
    });
    await openEditor();
    const earlier = section("earlier-proposals")!;
    expect(earlier.querySelector('[data-origin="PRE_GOVERNANCE_DRAFT"]')!.textContent).toContain("Pre-governance draft (never approved)");
    const copyable = [...earlier.querySelectorAll("li")].filter(item => [...item.querySelectorAll("button")].some(b => b.textContent === "Copy into new draft"));
    expect(copyable.map(item => item.getAttribute("data-state"))).toEqual(["WITHDRAWN", "STALE", "WITHDRAWN"]);
    await act(async () => { (copyable[1].querySelector("button") as HTMLButtonElement).click(); });
    await settle();
    expect(api.mutations()).toEqual([{ method: "POST", url: `/api/workflows/${WID}/proposals/d-stale/copy`, body: { expected_workflow_revision: 4 } }]);
    expect(host.textContent).toContain("Copied into a new draft authored by you");
  });

  it("offers a Director no restore, reset or copy", async () => {
    server({ canCreate: false, decidedProposals: [decided({ proposal_id: "d-1" })] });
    await openEditor(director);
    expect(section("recovery-actions")).toBeNull();
    expect(texts()).not.toContain("Copy into new draft");
    expect(texts()).toContain("View v1");
  });
});

describe("Release draft (ADR-017 §1.2)", () => {
  const idle = () => proposal({ author_id: "hr-other", can_edit: false, can_submit: false, can_withdraw: false, last_activity_at: "2026-11-20T09:00:00Z" });

  it("offers Release to another HR user after 14 idle days, with a required reason", async () => {
    const api = server({ open: idle() });
    await openEditor();
    const panel = section("release-draft")!;
    expect(panel.textContent).toContain("no activity for 20 days");
    expect(panel.textContent).toContain("never submits or publishes");
    expect(button("Release draft").disabled).toBe(true);
    setValue(panel.querySelector("input")!, "   ");
    expect(button("Release draft").disabled).toBe(true);
    setValue(panel.querySelector("input")!, "  Author left the team  ");
    await click("Release draft");
    expect(api.mutations()).toEqual([{
      method: "POST", url: `/api/workflows/${WID}/proposals/${PID}/release`,
      body: { reason: "Author left the team", expected_workflow_revision: 4, expected_proposal_revision: 1 },
    }]);
    expect(host.textContent).toContain("Draft released");
  });

  it("is not offered to the author, on a recent draft, or to a Director", async () => {
    server({ open: { ...idle(), author_id: hr.user_id } });
    await openEditor();
    expect(section("release-draft")).toBeNull();
    act(() => root?.unmount());
    document.body.innerHTML = "";

    server({ open: { ...idle(), last_activity_at: "2026-12-01T09:00:00Z" } });
    await openEditor();
    expect(section("release-draft")).toBeNull();
    act(() => root?.unmount());
    document.body.innerHTML = "";

    server({ open: idle(), canCreate: false });
    await openEditor(director);
    expect(section("release-draft")).toBeNull();
  });

  it("shows the backend's 409 DRAFT_NOT_RELEASABLE refusal", async () => {
    server({ open: idle(), refuse: { [`/proposals/${PID}/release`]: { status: 409, code: "WORKFLOW_DRAFT_NOT_RELEASABLE" } } });
    await openEditor();
    setValue(section("release-draft")!.querySelector("input")!, "Author left the team");
    await click("Release draft");
    expect(section("governance-refusal")!.textContent).toContain(GOVERNANCE_ERROR_MESSAGES.WORKFLOW_DRAFT_NOT_RELEASABLE);
  });
});

async function chooseVersion(panel: HTMLElement, value: string) {
  await act(async () => {
    const select = panel.querySelector("select")!;
    select.value = value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

describe("Emergency fallback (Director)", () => {
  async function startFallback() {
    await openEditor(director);
    await click("Start emergency fallback");
    return section("emergency-fallback")!;
  }

  it("is hidden for HR", async () => {
    server();
    await openEditor(hr);
    expect(section("emergency-fallback")).toBeNull();
    expect(texts()).not.toContain("Start emergency fallback");
  });

  it("requires a 10–240 character reason and explicit confirmation, then publishes a version", async () => {
    const api = server({ open: proposal({ state: "PENDING_APPROVAL", can_edit: false, can_submit: false, can_withdraw: false }), canCreate: false });
    const panel = await startFallback();
    expect(panel.textContent).toContain("single-actor emergency publication");
    expect(panel.textContent).toContain("HR is notified");
    const publish = () => button("Publish emergency fallback");
    expect(publish().disabled).toBe(true);
    setValue(panel.querySelector("textarea")!, "too short");
    (panel.querySelector('input[type="checkbox"]') as HTMLInputElement).click();
    await settle();
    expect(publish().disabled).toBe(true);
    setValue(panel.querySelector("textarea")!, "x".repeat(241));
    expect(publish().disabled).toBe(true);
    setValue(panel.querySelector("textarea")!, "Sanctions step blocked every case overnight");
    // No target is preselected: the Director must choose one, and a version, explicitly.
    expect([...panel.querySelectorAll<HTMLInputElement>('input[type="radio"]')].some(radio => radio.checked)).toBe(false);
    expect(publish().disabled).toBe(true);
    await act(async () => { panel.querySelectorAll<HTMLInputElement>('input[type="radio"]')[0].click(); });
    expect(panel.querySelector("select")!.value).toBe("");
    expect(publish().disabled).toBe(true);
    await chooseVersion(panel, "1");
    expect(publish().disabled).toBe(false);
    await click("Publish emergency fallback");
    expect(api.mutations()).toEqual([{
      method: "POST", url: `/api/workflows/${WID}/emergency-fallback`,
      body: { reason: "Sanctions step blocked every case overnight", expected_workflow_revision: 4, target: "VERSION", target_version: 1 },
    }]);
    expect(host.textContent).toContain("Emergency fallback published: version 3 is now active (Emergency fallback by director-synthetic-1 — not approved)");
    expect(host.textContent).toContain("HR has been notified");
    expect(host.textContent).toContain("1 open proposal is now out of date");
  });

  it("clears the reason, target and confirmation on Cancel and on reopening", async () => {
    server({ canCreate: false });
    let panel = await startFallback();
    await act(async () => { panel.querySelectorAll<HTMLInputElement>('input[type="radio"]')[0].click(); });
    await chooseVersion(panel, "2");
    setValue(panel.querySelector("textarea")!, "Sanctions step blocked every case overnight");
    await act(async () => { (panel.querySelector('input[type="checkbox"]') as HTMLInputElement).click(); });
    expect(button("Publish emergency fallback").disabled).toBe(false);
    await click("Cancel", panel);
    await click("Start emergency fallback");
    panel = section("emergency-fallback")!;
    expect(panel.querySelector("textarea")!.value).toBe("");
    expect((panel.querySelector('input[type="checkbox"]') as HTMLInputElement).checked).toBe(false);
    expect([...panel.querySelectorAll<HTMLInputElement>('input[type="radio"]')].some(radio => radio.checked)).toBe(false);
    expect(panel.querySelector("select")).toBeNull();
    expect(button("Publish emergency fallback").disabled).toBe(true);
  });

  it("names the form it opens with aria-controls", async () => {
    server({ canCreate: false });
    await openEditor(director);
    const start = button("Start emergency fallback");
    const controlled = document.getElementById(start.getAttribute("aria-controls")!);
    expect(controlled).not.toBeNull();
    await click("Start emergency fallback");
    expect(controlled!.querySelector("textarea")).not.toBeNull();
  });

  it("publishes the default with target DEFAULT and no target_version", async () => {
    const api = server({ canCreate: false });
    const panel = await startFallback();
    const radios = panel.querySelectorAll<HTMLInputElement>('input[type="radio"]');
    await act(async () => { radios[1].click(); });
    setValue(panel.querySelector("textarea")!, "Reset everything to the default now");
    await act(async () => { (panel.querySelector('input[type="checkbox"]') as HTMLInputElement).click(); });
    await click("Publish emergency fallback");
    expect(api.mutations()).toEqual([{
      method: "POST", url: `/api/workflows/${WID}/emergency-fallback`,
      body: { reason: "Reset everything to the default now", expected_workflow_revision: 4, target: "DEFAULT" },
    }]);
  });

  it("shows 409 NOTICES_UNACKNOWLEDGED as a refusal", async () => {
    server({ canCreate: false, refuse: { "/emergency-fallback": { status: 409, code: "WORKFLOW_NOTICES_UNACKNOWLEDGED" } } });
    const panel = await startFallback();
    await act(async () => { panel.querySelectorAll<HTMLInputElement>('input[type="radio"]')[1].click(); });
    setValue(panel.querySelector("textarea")!, "Sanctions step blocked every case overnight");
    await act(async () => { (panel.querySelector('input[type="checkbox"]') as HTMLInputElement).click(); });
    await click("Publish emergency fallback");
    expect(section("governance-refusal")!.textContent).toContain(GOVERNANCE_ERROR_MESSAGES.WORKFLOW_NOTICES_UNACKNOWLEDGED);
  });
});

describe("Notices (RD-6)", () => {
  const item = (overrides: Partial<NoticeItem> = {}): NoticeItem => ({
    workflow_id: WID, workflow_name: "Corporate onboarding", workflow_revision: 7, notice: notice(), ...overrides,
  });

  it("lets HR acknowledge with the expected workflow revision", async () => {
    const api = server({ notices: [item()] });
    await render(<WorkflowManager actor={hr} />);
    const panel = section("workflow-notices")!;
    expect(panel.textContent).toContain("Emergency fallback on Corporate onboarding: version 3 by director-synthetic-1");
    expect(panel.textContent).toContain("not approved");
    expect(panel.textContent).toContain("Reason: Sanctions step blocked every case overnight");
    await click("Acknowledge");
    expect(api.mutations()).toEqual([{ method: "POST", url: "/api/workflows/notices/n-1/acknowledge", body: { workflow_id: WID, expected_workflow_revision: 7 } }]);
    // The last notice is gone: no alert banner, only a polite dismissible status.
    expect(section("workflow-notices")).toBeNull();
    expect(host.querySelector(".ds-banner-warn")).toBeNull();
    const cleared = section("workflow-notices-cleared")!;
    expect(cleared.getAttribute("role")).toBe("status");
    expect(cleared.className).not.toMatch(/warn|danger|critical/);
    expect(cleared.textContent).toContain("All notices acknowledged.");
    expect(host.textContent).not.toMatch(/Workflow notices \(0\)|published an emergency fallback/);
    expect(host.textContent).not.toContain("Reason: Sanctions step blocked");
    await click("Dismiss", cleared);
    expect(section("workflow-notices-cleared")).toBeNull();
  });

  it("renders nothing on a fresh load with zero notices", async () => {
    server({ notices: [] });
    await render(<WorkflowManager actor={hr} />);
    expect(section("workflow-notices")).toBeNull();
    expect(section("workflow-notices-cleared")).toBeNull();
    expect(section("workflow-notices-error")).toBeNull();
  });

  it("keeps the remaining notice in the banner when one of two is acknowledged", async () => {
    server({ notices: [item(), item({ notice: notice({ notice_id: "n-2", version: 4, reason: "Second emergency reason text" }) })] });
    await render(<WorkflowManager actor={hr} />);
    expect(section("workflow-notices")!.textContent).toContain("Workflow notices (2)");
    await act(async () => { (section("workflow-notices")!.querySelector('[data-notice-id="n-1"] button') as HTMLButtonElement).click(); });
    await settle();
    const panel = section("workflow-notices")!;
    expect(panel.textContent).toContain("Workflow notices (1)");
    expect(panel.textContent).toContain("Second emergency reason text");
    expect(panel.textContent).toContain("Notice acknowledged.");
    expect(panel.querySelector('[data-notice-id="n-1"]')).toBeNull();
    expect(section("workflow-notices-cleared")).toBeNull();
  });

  it("reloads the notices on 409", async () => {
    const api = server({ notices: [item()], refuse: { ack: { status: 409, code: "WORKFLOW_CONFLICT" } } });
    await render(<WorkflowManager actor={hr} />);
    const reads = () => api.calls.filter(call => call.method === "GET" && call.url === "/api/workflows/notices").length;
    const before = reads();
    api.setNotices([item({ workflow_revision: 8 })]);
    await click("Acknowledge");
    expect(host.textContent).toContain("The notices were reloaded");
    expect(reads()).toBeGreaterThan(before);
    await click("Acknowledge");
    expect(api.mutations()[1]).toEqual({ method: "POST", url: "/api/workflows/notices/n-1/acknowledge", body: { workflow_id: WID, expected_workflow_revision: 8 } });
  });

  it("uses generic wording for notices that are not emergency fallbacks", async () => {
    server({ notices: [item({ notice: notice({ kind: "DEACTIVATED" }) })] });
    await render(<WorkflowManager actor={hr} />);
    const panel = section("workflow-notices")!;
    expect(panel.textContent).toContain("These workflow events need HR attention.");
    expect(panel.textContent).not.toMatch(/emergency fallback|not approved/i);
  });

  it("tells HR when notices could not be loaded, without blocking the page, and retries", async () => {
    let fail = true;
    const api = server({ notices: [item()] });
    const inner = (globalThis.fetch as ReturnType<typeof vi.fn>).getMockImplementation()!;
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/workflows/notices" && fail) return json({ detail: { code: "WORKFLOW_UNAVAILABLE", message: "x" } }, 503);
      return inner(input, init);
    }));
    await render(<WorkflowManager actor={hr} />);
    expect(section("workflow-notices-error")!.textContent).toContain("Notices could not be loaded.");
    expect(host.textContent).toContain("Corporate onboarding");
    fail = false;
    await click("Retry");
    expect(section("workflow-notices-error")).toBeNull();
    expect(section("workflow-notices")!.textContent).toContain("Workflow notices (1)");
    expect(api.mutations()).toEqual([]);
  });

  it("shows Directors notices read-only", async () => {
    const api = server({ notices: [item()], canCreate: false });
    await render(<WorkflowManager actor={director} />);
    const panel = section("workflow-notices")!;
    expect(panel.textContent).toContain("Read-only: an HR user must acknowledge these notices.");
    expect(panel.querySelector("button")).toBeNull();
    expect(api.mutations()).toEqual([]);
  });

  it("shows only the open workflow's notices in the editor and nothing when notices are unavailable", async () => {
    server({ notices: [item(), item({ workflow_id: "elsewhere", workflow_name: "Elsewhere", notice: notice({ notice_id: "n-2" }) })] });
    await openEditor();
    const panel = section("workflow-notices")!;
    expect(panel.textContent).toContain("Workflow notices (1)");
    expect(panel.textContent).not.toContain("Elsewhere");
    act(() => root?.unmount());
    document.body.innerHTML = "";
    server({ notices: null });
    await render(<WorkflowManager actor={hr} />);
    expect(section("workflow-notices")).toBeNull();
  });
});

describe("Director comparison of recovery proposals", () => {
  const DECISION_URL = (wid: string, pid: string) => `/api/workflows/${wid}/proposals/${pid}/decision`;

  function comparisonOf(kind: ProposalKind) {
    const data = governanceFixtures.comparison();
    data.proposal = { ...data.proposal, kind };
    if (kind === "DEACTIVATE") {
      data.proposal.stages = [];
      data.permanent_obligations = [];
      data.validation = { ...data.validation, permanent_obligations: [], issues: [], valid: true };
    }
    return data;
  }

  function mockCompare(kind: ProposalKind, decisions: Array<() => Response>) {
    const data = comparisonOf(kind);
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/comparison")) return json(data);
      if (url.endsWith("/decision")) return decisions.shift()!();
      return json({ detail: { code: "WORKFLOW_NOT_FOUND", message: "x" } }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    return { data, fetchMock };
  }

  it("explains deactivate, retries after 409 RUN_CONFIRMATION_IN_PROGRESS and shows the result", async () => {
    const decided: DecisionResponse = {
      ...governanceFixtures.decisionResponseApproved(), published_version: null, provenance: null, publication_report: null, active_version: 0,
    };
    const { data, fetchMock } = mockCompare("DEACTIVATE", [
      () => refusal(409, "WORKFLOW_RUN_CONFIRMATION_IN_PROGRESS"),
      () => json({ ...decided, proposal: { ...decided.proposal, kind: "DEACTIVATE", state: "APPROVED" } }),
    ]);
    await render(<WorkflowCompare actor={director} workflowId={data.workflow_id} proposalId={data.proposal.proposal_id} onBack={vi.fn()} />);
    expect(section("compare-kind")!.textContent).toBe("Deactivate");
    const effects = section("deactivate-effects")!.textContent!;
    expect(effects).toContain("stay completable");
    expect(effects).toContain("New runs of this workflow are blocked");
    setValue(host.querySelector("textarea")!, "No longer used by any team");
    await click("Approve and deactivate");
    expect(host.textContent).toContain("so it can't be deactivated yet. Nothing was changed. Try again in a moment.");
    expect(host.textContent).toContain("You can try the same decision again.");
    expect(texts()).not.toContain("Reload comparison");
    expect(button("Approve and deactivate").disabled).toBe(false);
    await click("Approve and deactivate");
    const decisions = fetchMock.mock.calls.filter(([input]) => String(input).endsWith(DECISION_URL(data.workflow_id, data.proposal.proposal_id)));
    expect(decisions).toHaveLength(2);
    expect(JSON.parse(String(decisions[1][1]?.body))).toMatchObject({ outcome: "APPROVE", acknowledged_permanent_obligations: [] });
    expect(host.textContent).toContain("Approved · the workflow is deactivated: new runs are blocked and existing runs stay completable");
  });

  it.each([
    ["RESTORE_VERSION", "Restore an earlier version"],
    ["RESET_TO_DEFAULT", "Reset to default"],
    ["REACTIVATE", "Reactivate"],
  ] as const)("labels a %s proposal plainly", async (kind, label) => {
    const { data } = mockCompare(kind, []);
    await render(<WorkflowCompare actor={director} workflowId={data.workflow_id} proposalId={data.proposal.proposal_id} onBack={vi.fn()} />);
    expect(section("compare-kind")!.textContent).toBe(label);
    expect(section("compare-kind-explanation")!.textContent).toContain(label);
    if (kind !== "REACTIVATE") expect(section("compare-kind-explanation")!.textContent).toContain("safe target");
    expect(texts()).toContain("Approve and publish");
  });

  it("shows the kind in the inbox for recovery proposals only", async () => {
    const inbox = governanceFixtures.approvalsInbox();
    inbox.items = [inbox.items[0], { ...inbox.items[0], workflow_id: OTHER, proposal: { ...inbox.items[0].proposal, proposal_id: "p-x", kind: "DEACTIVATE" } }];
    vi.stubGlobal("fetch", vi.fn(async () => json(inbox)));
    await render(<WorkflowApprovals actor={director} onOpen={vi.fn()} />);
    expect([...host.querySelectorAll('[data-testid="inbox-kind"]')].map(item => item.textContent)).toEqual(["Deactivate"]);
  });
});
