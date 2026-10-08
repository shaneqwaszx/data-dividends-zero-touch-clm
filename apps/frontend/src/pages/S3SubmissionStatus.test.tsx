// @vitest-environment jsdom

import { act, StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../api";
import { caseQueryKeys } from "../caseQueries";
import { clearSessionQueries } from "../queryClient";
import type { AuthenticatedProfile, ZeroTouchCaseSummary } from "../types";
import CaseDetail from "./CaseDetail";
import ReviewAndSend from "./ReviewAndSend";
import TargetRecoveryPanel from "./TargetRecoveryPanel";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
HTMLElement.prototype.scrollIntoView ??= () => undefined;
const NOW = "2026-10-04T01:00:00Z";
const CASE_A = "00000000-0000-4000-8000-00000000031a";
const CASE_B = "00000000-0000-4000-8000-00000000031b";
const SUBMISSION = "00000000-0000-4000-8000-00000000033a";
type SubmissionState = NonNullable<ZeroTouchCaseSummary["target_submission"]>["state"];
const actor: AuthenticatedProfile = {
  user_id: "synthetic-s3-user", display_name: "Synthetic S3 User", role: "CLIENT_ONBOARDER",
  team_id: "TEAM_A", team_display_name: "Synthetic Team", team_type: "CLIENT",
  team_description: "Synthetic test scope", client_scope_label: "Synthetic", capabilities: ["CASE_ACCESS"],
};

function fixture(state: SubmissionState = "SUBMISSION_OUTCOME_UNCERTAIN", caseId = CASE_A): ZeroTouchCaseSummary {
  return {
    version: 7, automation_id: "synthetic-automation", status: "TECHNICAL_FAILURE", current_stage: "MOCK_GOLDTIER",
    completed_stages: ["REGISTRY", "DOCUMENT", "OWNERSHIP", "READINESS"], active_exceptions: [],
    historical_exceptions: [], non_blocking_decisions: [], interventions: [], reconciliation: null,
    evidence_decision_authorized: false, ownership_edit_authorized: false,
    technical_failure: { code: "CLM_TARGET_OUTCOME_UNCERTAIN", message: "Retained target evidence requires inspection." },
    target_submission: { submission_id: SUBMISSION, state, goldtier_id: "synthetic-target-31", status_check_available: state === "SUBMISSION_OUTCOME_UNCERTAIN" },
    case: {
      case_id: caseId, requested_uen: "202600031A", team_id: "TEAM_A", client_scope_label: "Synthetic", priority: null,
      initial_identity: { legal_name: "SYNTHETIC S3 PTE. LTD.", registration_number: "202600031A", country_of_incorporation: "SG" },
      entity: { legal_name: "SYNTHETIC S3 PTE. LTD.", registration_number: "202600031A", country_of_incorporation: "SG", party_type: "Organisation", source: null },
      events: [], registry_acquisition: null, jurisdiction_resolution: null, goldtier_result: null,
      target_dispatch_confirmation: {
        confirmation_id: "synthetic-confirmation", actor_id: actor.user_id, confirmed_at: NOW,
        case_event_count: 0, clm_version: 4, destination: "GOLDTIER_XPI_SANDBOX", warnings: [],
        review_digest: "a".repeat(64), classification: "USER_AUTHORIZED_POC",
      },
    },
    clm: {
      version: 4, status: "SUBMITTING", submission: { snapshot_id: "synthetic-snapshot", submission_id: SUBMISSION, readiness_policy_version: "v1" },
      submission_plan: { environment: "SANDBOX", provider_classification: "SANDBOX_PARTIAL", base_operations: [], real_ready_for_approval: "NOT_AVAILABLE", request_preview: null },
      target_search_checkpoint: null,
      readiness: { registry: { status: "READY" }, document: { status: "READY" }, ownership: { status: "READY" }, goldtier: { status: "NOT_SUBMITTED" }, blockers: [], warnings: [] },
    },
    classification_consistency: { status: "COMPATIBLE", title: "Consistent", explanation: "Consistent", blocking: false, authority: "PROJECT_ADVISORY_ONLY" },
    target_operations: [], processing_pipeline: [], timeline: [],
    metrics: { automated_stages_completed: 4, human_interventions: 1, exceptions_raised: 0, exceptions_resolved: 0, final_outcome: null, total_duration_ms: null, stage_durations_ms: {} },
    timing: { observed_at: NOW, case_elapsed_ms: 0, time_since_last_update_ms: 0, automation_elapsed_ms: null, recorded_total_duration_ms: null },
    created_at: NOW, updated_at: NOW,
  } as unknown as ZeroTouchCaseSummary;
}

function markup(summary: ZeroTouchCaseSummary, options: {
  checking?: boolean; result?: api.TargetSearchObservation; error?: string; canCheck?: boolean;
} = {}): string {
  return renderToStaticMarkup(<ReviewAndSend summary={summary} documents={[]} ownership={null} actor={actor} busy={false}
    onConfirm={() => undefined} onSaveDraft={() => undefined} onReviewOutstanding={() => undefined}
    onEditIdentity={() => undefined} onEditClassification={() => undefined} onEditDocuments={() => undefined} onEditOwnership={() => undefined}
    statusChecking={options.checking} statusCheckResult={options.result} statusCheckError={options.error}
    onCheckStatus={options.canCheck ? () => undefined : undefined} />);
}

function result(message = "Customer identity verified; retained submission outcome remains uncertain."): api.TargetStatusCheckResult {
  return { submission_id: SUBMISSION, checked_at: NOW, result: "CUSTOMER_IDENTITY_VERIFIED", message };
}

let host: HTMLDivElement | null = null;
let root: Root | null = null;
let client: QueryClient | null = null;
afterEach(async () => {
  if (root) await act(async () => root!.unmount());
  host?.remove(); client?.clear(); root = null; host = null; client = null;
  vi.restoreAllMocks(); vi.unstubAllGlobals();
});

function seed(queryClient: QueryClient, summary: ZeroTouchCaseSummary, profile = actor) {
  const caseId = summary.case.case_id;
  queryClient.setQueryData(caseQueryKeys.detail(profile.user_id, caseId), summary);
  queryClient.setQueryData(caseQueryKeys.documents(profile.user_id, caseId), []);
  queryClient.setQueryData(caseQueryKeys.ownership(profile.user_id, caseId), null);
  queryClient.setQueryData(caseQueryKeys.intelligence(profile.user_id, caseId), null);
}
async function mount(summary = fixture(), profile = actor, strict = false) {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false }, mutations: { retry: false } } });
  seed(client, summary, profile);
  await renderCase(summary.case.case_id, profile, strict);
}
async function renderCase(caseId = CASE_A, profile = actor, strict = false) {
  const view = <QueryClientProvider client={client!}><CaseDetail caseId={caseId} actor={profile} onBack={() => undefined} onViewOnboarded={() => undefined} onViewAudit={() => undefined} /></QueryClientProvider>;
  await act(async () => root!.render(strict ? <StrictMode>{view}</StrictMode> : view));
}
async function settle() {
  await act(async () => { await new Promise<void>((resolve) => setTimeout(resolve, 0)); });
  await act(async () => { await new Promise<void>((resolve) => requestAnimationFrame(() => resolve())); });
}
function pendingCheck() {
  let complete!: (value: api.TargetStatusCheckResult) => void;
  const promise = new Promise<api.TargetStatusCheckResult>((resolve) => { complete = resolve; });
  const check = vi.spyOn(api, "checkZeroTouchTargetStatus").mockReturnValue(promise);
  return { check, complete };
}

// Render states from the backend projection even when legacy automation codes disagree.
describe("S3 backend-derived final submission state", () => {
  it.each([
    ["NOT_SUBMITTED", "Submission not started"], ["SENDING", "Sending to GoldTier"],
    ["SUBMISSION_CONFIRMED", "Submission confirmed"], ["SUBMISSION_FAILED", "Submission failed"],
    ["SUBMISSION_OUTCOME_UNCERTAIN", "Submission outcome uncertain"], ["FINALIZATION_PENDING", "Submission finalization pending"],
  ] as const)("presents %s without another local approval or retry", (state, title) => {
    const text = markup(fixture(state));
    expect(text).toContain(title);
    expect(text).toContain("Frozen server review projection");
    expect(text).toContain(state === "SUBMISSION_CONFIRMED"
      ? "<dt>GoldTier ID</dt><dd>synthetic-target-31</dd>"
      : "Retained GoldTier ID: synthetic-target-31");
    expect(text).not.toContain("Confirm and send"); expect(text).not.toContain(">Save draft<");
    expect(text).not.toContain(">Retry<"); expect(text).not.toContain("Edit company details");
    if (state === "FINALIZATION_PENDING") expect(text).not.toContain("Submission failed");
  });

  it("keeps legacy missing submission metadata unknown even with a target ID", () => {
    const summary = fixture(); delete summary.target_submission;
    summary.case.goldtier_result = { party_id: "legacy-id" } as unknown as ZeroTouchCaseSummary["case"]["goldtier_result"];
    const text = markup(summary);
    expect(text).toContain("Submission status unavailable"); expect(text).not.toContain("Submission confirmed");
    expect(text).not.toContain("Sending to GoldTier"); expect(text).not.toContain("Check GoldTier status");
  });

  it("uses checking wording only during the request and leaves customer verification uncertain", () => {
    expect(markup(fixture(), { canCheck: true })).not.toContain("— checking GoldTier status");
    expect(markup(fixture(), { checking: true, canCheck: true })).toContain("Submission outcome uncertain — checking GoldTier status");
    const text = markup(fixture(), { result: result(), canCheck: true });
    expect(text).toContain("Submission outcome uncertain"); expect(text).not.toContain("— checking GoldTier status");
    expect(text).not.toContain("Submission confirmed"); expect(text).toContain("does not establish Policy completion");
    expect(text).toContain("Check GoldTier status");
  });

  it("rejects an unrelated check result and withholds the control without server availability", () => {
    const summary = fixture(); summary.target_submission!.status_check_available = false;
    const text = markup(summary, { result: { ...result("WRONG SUBMISSION OBSERVATION"), submission_id: "other" }, canCheck: true });
    expect(text).not.toContain("WRONG SUBMISSION OBSERVATION"); expect(text).not.toContain("Check GoldTier status");
  });
});

describe("S3 scoped bounded status checking", () => {
  it.each(["EXISTING_REUSED", "NEW_CREATED"] as const)("puts the ID first and presents retained %s handling", (handling) => {
    const summary = fixture("SUBMISSION_CONFIRMED");
    summary.target_submission!.customer_handling = handling;
    summary.target_submission!.verification_available = true;
    const text = markup(summary, { canCheck: true });
    const completed = text.slice(text.indexOf('aria-label="Completed GoldTier submission"'));
    expect(completed.indexOf("<dt>GoldTier ID</dt>")).toBeLessThan(completed.indexOf("<dt>Customer handling</dt>"));
    expect(text).toContain(handling === "EXISTING_REUSED" ? "Existing GoldTier customer reused" : "New GoldTier customer created");
    expect(text).toContain("Verify in GoldTier");
    expect(text).not.toContain("Check GoldTier status");
  });

  it.each(["VERIFIED", "REQUIRES_REVIEW", "UNAVAILABLE"] as const)("presents independent completed verification %s", (verification) => {
    const summary = fixture("SUBMISSION_CONFIRMED");
    const observed: api.CompletedTargetVerificationResult = {
      submission_id: SUBMISSION, goldtier_id: "synthetic-target-31", checked_at: "2026-10-05T09:00:00Z",
      result: verification, legal_name: "SYNTHETIC S3 PTE. LTD.", registration_number: "202600031A", country: "SG",
    };
    const text = markup(summary, { result: observed });
    expect(text).toContain(verification === "VERIFIED" ? "Verified in Sandbox"
      : verification === "REQUIRES_REVIEW" ? "Verification requires review" : "Verification unavailable");
    expect(text).toContain("Submission confirmed");
    expect(text).not.toContain("Submission outcome uncertain");
    expect(markup(summary, { result: { ...observed, goldtier_id: "other" } })).not.toContain("Checked at");
  });

  it("only verifies completed cases on explicit action and retains scoped read-only results", async () => {
    const summary = fixture("SUBMISSION_CONFIRMED");
    summary.target_submission!.verification_available = true;
    const verify = vi.spyOn(api, "verifyCompletedGoldTier").mockResolvedValue({
      submission_id: SUBMISSION, goldtier_id: "synthetic-target-31",
      checked_at: "2026-10-05T09:00:00Z", result: "VERIFIED",
      legal_name: "SYNTHETIC S3 PTE. LTD.", registration_number: "202600031A", country: "SG",
    });
    const uncertain = vi.spyOn(api, "checkZeroTouchTargetStatus");
    const resume = vi.spyOn(api, "resumeZeroTouchCase");
    await mount(summary);
    expect(verify).not.toHaveBeenCalled();
    const button = [...host!.querySelectorAll("button")].find((item) => item.textContent === "Verify in GoldTier");
    expect(button).toBeDefined();
    await act(async () => button!.click());
    expect(verify).toHaveBeenCalledOnce();
    expect(verify.mock.calls[0].slice(0, 2)).toEqual([CASE_A, SUBMISSION]);
    expect(uncertain).not.toHaveBeenCalled();
    expect(resume).not.toHaveBeenCalled();
    expect(host!.textContent).toContain("Verified in Sandbox");
    expect(host!.textContent).toContain("Submission confirmed");
  });

  it("discards a completed verification response after case navigation", async () => {
    const summary = fixture("SUBMISSION_CONFIRMED");
    summary.target_submission!.verification_available = true;
    let finish!: (result: api.CompletedTargetVerificationResult) => void;
    const verify = vi.spyOn(api, "verifyCompletedGoldTier").mockReturnValue(new Promise((resolve) => { finish = resolve; }));
    await mount(summary);
    await act(async () => [...host!.querySelectorAll("button")].find((item) => item.textContent === "Verify in GoldTier")!.click());
    const other = fixture("SUBMISSION_CONFIRMED", CASE_B);
    seed(client!, other);
    await renderCase(CASE_B);
    await act(async () => finish({
      submission_id: SUBMISSION, goldtier_id: "synthetic-target-31", checked_at: "2026-10-05T09:00:00Z",
      result: "VERIFIED", legal_name: "STALE IDENTITY SENTINEL", registration_number: null, country: null,
    }));
    expect(verify.mock.calls[0][2]?.aborted).toBe(true);
    expect(host!.textContent).not.toContain("STALE IDENTITY SENTINEL");
  });

  it("keeps frozen review visible and performs one automatic check across rerenders and remounts", async () => {
    const pending = pendingCheck(); vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Unexpected request")));
    await mount();
    expect(pending.check).toHaveBeenCalledTimes(1);
    expect(host!.querySelector("#submission-state-title")?.textContent).toBe("Submission outcome uncertain — checking GoldTier status");
    expect(host!.querySelector("#case-review-and-send")?.closest(".stage-disclosure")?.querySelector("[hidden]")).toBeNull();
    await renderCase(); expect(pending.check).toHaveBeenCalledTimes(1);
    await act(async () => pending.complete(result()));
    expect(host!.querySelector("#submission-state-title")?.textContent).toBe("Submission outcome uncertain");
    expect(host!.textContent).toContain("Customer identity verified; retained submission outcome remains uncertain.");
    expect(host!.querySelector("#case-review-and-send")?.textContent).not.toContain("Confirm and send");
    expect(vi.mocked(fetch)).not.toHaveBeenCalled();
    await act(async () => root!.unmount()); root = createRoot(host!); await renderCase();
    expect(pending.check).toHaveBeenCalledTimes(1); expect(host!.textContent).toContain("Customer identity verified;");
  });

  it("does not retry a failed check on re-render, but supports an explicit read-only check", async () => {
    const check = vi.spyOn(api, "checkZeroTouchTargetStatus").mockRejectedValueOnce(new TypeError("Synthetic transport unavailable")).mockResolvedValue(result());
    await mount(); await settle(); await renderCase(); await settle();
    expect(check).toHaveBeenCalledTimes(1); expect(host!.textContent).toContain("GoldTier status could not be checked");
    const button = [...host!.querySelectorAll("button")].find((item) => item.textContent === "Check GoldTier status");
    expect(button).toBeDefined(); await act(async () => button!.click());
    expect(check).toHaveBeenCalledTimes(2); expect(host!.querySelector("#submission-state-title")?.textContent).toBe("Submission outcome uncertain");
  });

  it.each(["SUBMISSION_FAILED", "FINALIZATION_PENDING", "SUBMISSION_CONFIRMED", "SENDING"] as const)("does not automatically check or resume %s", async (state) => {
    const check = vi.spyOn(api, "checkZeroTouchTargetStatus"); const resume = vi.spyOn(api, "resumeZeroTouchCase");
    await mount(fixture(state)); expect(check).not.toHaveBeenCalled(); expect(resume).not.toHaveBeenCalled();
    expect(host!.querySelector("#case-review-and-send")).not.toBeNull();
  });

  it("withholds Resume for uncertain recovery and retains local finalization recovery", async () => {
    const check = vi.spyOn(api, "checkZeroTouchTargetStatus").mockResolvedValue(result());
    const resume = vi.spyOn(api, "resumeZeroTouchCase");
    const uncertain = fixture(); uncertain.status = "RECOVERY_PENDING";
    await mount(uncertain); expect(host!.textContent).not.toContain("Complete safe recovery");
    const finalization = fixture("FINALIZATION_PENDING"); finalization.status = "RECOVERY_PENDING"; finalization.version += 1;
    await act(async () => seed(client!, finalization)); await settle();
    expect(host!.textContent).toContain("Complete safe recovery");
    expect(host!.textContent).toContain("Retained target operations are resolved");
    expect(check).toHaveBeenCalledTimes(1); expect(resume).not.toHaveBeenCalled();
  });

  it("aborts a prior submission check and binds the next automatic check to its new submission", async () => {
    const pending = pendingCheck(); await mount(); const signal = pending.check.mock.calls[0][2]!;
    const next = fixture(); next.version += 1;
    next.target_submission!.submission_id = "00000000-0000-4000-8000-00000000033b";
    const nextResult = { ...result("CURRENT SUBMISSION OBSERVATION"), submission_id: next.target_submission!.submission_id };
    pending.check.mockResolvedValueOnce(nextResult);
    await act(async () => seed(client!, next)); await settle();
    expect(signal.aborted).toBe(true); expect(pending.check).toHaveBeenCalledTimes(2);
    expect(pending.check.mock.calls[1][1]).toBe(next.target_submission!.submission_id);
    await act(async () => pending.complete(result("STALE SUBMISSION RESPONSE")));
    expect(host!.textContent).not.toContain("STALE SUBMISSION RESPONSE");
    expect(host!.textContent).toContain("CURRENT SUBMISSION OBSERVATION");
  });

  it("aborts a prior case request and rejects its late result after route change", async () => {
    const pending = pendingCheck(); await mount(); const signal = pending.check.mock.calls[0][2]!;
    seed(client!, fixture("SUBMISSION_FAILED", CASE_B)); await renderCase(CASE_B);
    expect(signal.aborted).toBe(true);
    await act(async () => pending.complete(result("STALE CASE RESPONSE")));
    expect(host!.textContent).not.toContain("STALE CASE RESPONSE");
    expect(host!.querySelector("#submission-state-title")?.textContent).toBe("Submission failed");
  });

  it("aborts a prior actor request and rejects its late result after identity change", async () => {
    const pending = pendingCheck(); await mount(); const signal = pending.check.mock.calls[0][2]!;
    const other = { ...actor, user_id: "synthetic-other-user" }; seed(client!, fixture("FINALIZATION_PENDING"), other);
    await renderCase(CASE_A, other); expect(signal.aborted).toBe(true);
    await act(async () => pending.complete(result("STALE ACTOR RESPONSE")));
    expect(host!.textContent).not.toContain("STALE ACTOR RESPONSE");
    expect(host!.querySelector("#submission-state-title")?.textContent).toBe("Submission finalization pending");
  });

  it("aborts on session unmount and cannot repopulate a cleared session cache", async () => {
    const pending = pendingCheck(); await mount(); const signal = pending.check.mock.calls[0][2]!;
    await act(async () => { clearSessionQueries(client!); root!.unmount(); }); root = null;
    expect(signal.aborted).toBe(true); await act(async () => pending.complete(result("STALE SESSION RESPONSE")));
    expect(client!.getQueryCache().getAll()).toHaveLength(0);
  });

  it("marks the auto attempt before dispatch and never repeats it during StrictMode effects", async () => {
    const pending = pendingCheck(); await mount(fixture(), actor, true);
    expect(pending.check).toHaveBeenCalledTimes(1); await renderCase(CASE_A, actor, true);
    expect(pending.check).toHaveBeenCalledTimes(1); await act(async () => pending.complete(result()));
  });

  it("aborts checking when a fresh authoritative result replaces uncertainty", async () => {
    const pending = pendingCheck(); await mount(); const signal = pending.check.mock.calls[0][2]!;
    const confirmed = fixture("SUBMISSION_CONFIRMED"); confirmed.version += 1;
    await act(async () => seed(client!, confirmed)); await settle();
    expect(signal.aborted).toBe(true); await act(async () => pending.complete(result("STALE UNCERTAIN RESPONSE")));
    expect(host!.querySelector("#submission-state-title")?.textContent).toBe("Submission confirmed");
    expect(host!.textContent).not.toContain("STALE UNCERTAIN RESPONSE");
  });

  it("fails closed when the status check finds an inaccessible case", async () => {
    const check = vi.spyOn(api, "checkZeroTouchTargetStatus").mockRejectedValue(new api.ApiError("Unavailable", 404, null));
    await mount(); await settle(); expect(check).toHaveBeenCalledTimes(1);
    expect(host!.textContent).toContain("The case is unavailable."); expect(host!.textContent).not.toContain("SYNTHETIC S3 PTE. LTD.");
  });
});

describe("Actionable GoldTier recovery", () => {
  const director = { ...actor, role: "DIRECTOR" as const, capabilities: ["CASE_ACCESS", "TARGET_RECOVERY"] as AuthenticatedProfile["capabilities"] };
  function recoverable(operation: "SHELL" | "POLICY", profile: AuthenticatedProfile = director) {
    const summary = fixture();
    Object.assign(summary.target_submission!, {
      recovery_operation: operation, recovery_available: profile.capabilities.includes("TARGET_RECOVERY"),
      attempted_operations: ["SEARCH", "SHELL", ...(operation === "POLICY" ? ["POLICY"] : [])],
      definitively_completed_operations: ["SEARCH", ...(operation === "POLICY" ? ["SHELL"] : [])],
      lifecycle_resolved_operations: ["SEARCH", ...(operation === "POLICY" ? ["SHELL"] : [])],
      provider_policy: operation === "POLICY" ? "Singapore" : null, uncertainty_reason: "TIMEOUT", ledger_state: "IN_PROGRESS",
    });
    return summary;
  }

  it("hands focus to the next retained submission action only on a same-case state transition", async () => {
    vi.spyOn(api, "checkZeroTouchTargetStatus").mockResolvedValue(result());
    const scroll = vi.fn();
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    const originalScroll = HTMLElement.prototype.scrollIntoView;
    HTMLElement.prototype.scrollIntoView = scroll;
    try {
      await mount(fixture("NOT_SUBMITTED"), director);
      expect(document.activeElement?.id).not.toBe("target-recovery-title");
      const uncertain = recoverable("SHELL"); uncertain.version += 1;
      await act(async () => seed(client!, uncertain)); await settle();
      expect(document.activeElement?.id).toBe("target-recovery-title");
      const check = host!.querySelector<HTMLButtonElement>(".target-recovery-panel button")!;
      check.focus();
      await act(async () => seed(client!, { ...uncertain, version: uncertain.version + 1 })); await settle();
      expect(document.activeElement).toBe(check);
      const pending = fixture("FINALIZATION_PENDING"); pending.status = "RECOVERY_PENDING"; pending.version += 3;
      await act(async () => seed(client!, pending)); await settle();
      expect(document.activeElement?.id).toBe("target-continuation-title");
      expect(host!.querySelector('[aria-labelledby="target-continuation-title"]')?.textContent).toContain("Continue the same submission");
      const confirmed = fixture("SUBMISSION_CONFIRMED"); confirmed.status = "COMPLETED"; confirmed.version += 4;
      await act(async () => seed(client!, confirmed)); await settle();
      expect(document.activeElement?.id).toBe("submission-state-title");
      expect(scroll).toHaveBeenCalledTimes(3);
    } finally {
      HTMLElement.prototype.scrollIntoView = originalScroll;
    }
  });

  it.each(["NO_MATCH", "AMBIGUOUS", "CHECK_FAILED", "IDENTITY_UNVERIFIED"] as const)("explains %s without resolving or replaying", (outcome) => {
    const onRecover = vi.fn();
    const text = renderToStaticMarkup(<TargetRecoveryPanel summary={recoverable("SHELL", actor)} actor={actor} busy={false} checking={false} result={{ ...result(), result: outcome }} error={null} onCheck={() => undefined} onRecover={onRecover} />);
    expect(text).toContain("GoldTier submission needs verification");
    expect(text).toContain("Director verification required");
    expect(text).toContain("Check GoldTier status");
    expect(text).not.toContain("Resolve using verified GoldTier record");
    expect(text).toContain("Technical details");
    expect(onRecover).not.toHaveBeenCalled();
  });

  it("requires a checked exact candidate, sources identity from the server and suppresses double recovery", async () => {
    const checked = { ...result(), verified_party_id: "verified-customer" };
    vi.spyOn(api, "checkZeroTouchTargetStatus").mockResolvedValue(checked);
    let complete!: () => void;
    const recovery = vi.spyOn(api, "recoverZeroTouchTarget").mockReturnValue(new Promise<void>((resolve) => { complete = resolve; }));
    const pending = fixture("FINALIZATION_PENDING"); pending.version += 1; pending.status = "RECOVERY_PENDING";
    vi.spyOn(api, "fetchZeroTouchCase").mockResolvedValue(pending);
    vi.spyOn(api, "fetchDocuments").mockResolvedValue([]);
    vi.spyOn(api, "fetchOwnership").mockResolvedValue(null);
    vi.spyOn(api, "fetchIntelligence").mockResolvedValue(null);
    await mount(recoverable("SHELL"), director); await settle();
    const panel = host!.querySelector(".target-recovery-panel")!;
    const checkbox = panel.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    const button = [...panel.querySelectorAll("button")].find((item) => item.textContent === "Resolve using verified GoldTier record")!;
    expect(button.disabled).toBe(true);
    await act(async () => checkbox.click());
    expect(button.disabled).toBe(false);
    await act(async () => { button.click(); button.click(); });
    expect(recovery).toHaveBeenCalledOnce();
    expect(recovery.mock.calls[0]).toEqual([CASE_A, {
      expected_submission_id: SUBMISSION, operation: "SHELL", recovered_party_id: "verified-customer", origin: "UNCERTAIN_DURABLE_LEDGER",
    }]);
    expect(button.disabled).toBe(true);
    await act(async () => complete()); await settle();
    expect(host!.textContent).toContain("Complete safe recovery");
    expect(host!.querySelector(".target-recovery-panel")).toBeNull();
  });

  it("does not enable Shell recovery from stale or ambiguous observations", () => {
    for (const observed of [{ ...result(), result: "AMBIGUOUS" as const, verified_party_id: null }, { ...result(), verified_party_id: "other", submission_id: "old-submission" }]) {
      const text = renderToStaticMarkup(<TargetRecoveryPanel summary={recoverable("SHELL")} actor={director} busy={false} checking={false} result={observed} error={null} onRecover={() => undefined} />);
      expect(text).not.toContain("Verified GoldTier customer ID:");
      expect(text).toMatch(/disabled=""[^>]*>Resolve using verified GoldTier record/);
    }
  });

  it("does not accept customer Search as Policy proof", async () => {
    vi.spyOn(api, "checkZeroTouchTargetStatus").mockResolvedValue({ ...result(), verified_party_id: "synthetic-target-31" });
    const recovery = vi.spyOn(api, "recoverZeroTouchTarget");
    await mount(recoverable("POLICY"), director); await settle();
    const panel = host!.querySelector(".target-recovery-panel")!;
    const button = [...panel.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === "Resolve verified Policy result")!;
    expect(button.disabled).toBe(true); expect(recovery).not.toHaveBeenCalled();
    expect(panel.textContent).toContain("Customer Search cannot prove that a Policy was created");
    expect(panel.querySelector('[role="status"]')?.textContent).toContain("does not verify the Policy result");
    expect(panel.querySelector('[role="status"]')?.textContent).not.toContain("recover a Shell step");
    expect([...panel.querySelectorAll("option")].map((item) => item.value)).toEqual(["", "Requested"]);
    expect(panel.querySelector<HTMLInputElement>('input[readonly]')!.value).toBe("synthetic-target-31");
  });

  it("withholds recovery for a Director when backend eligibility is absent", () => {
    const summary = recoverable("POLICY"); summary.target_submission!.recovery_available = false;
    const text = renderToStaticMarkup(<TargetRecoveryPanel summary={summary} actor={director} busy={false} checking={false} result={null} error={null} onRecover={() => undefined} />);
    expect(text).not.toContain("Resolve verified Policy result");
    expect(text).toContain("cannot currently be resolved");
  });

  it("keeps an unrelated backend failure visible alongside unresolved target evidence", async () => {
    const summary = recoverable("POLICY");
    summary.target_submission!.recovery_available = false;
    summary.technical_failure = { code: "ZERO_TOUCH_UNEXPECTED_FAILURE", message: "A separate controlled failure needs inspection." };
    vi.spyOn(api, "checkZeroTouchTargetStatus").mockResolvedValue(result());
    await mount(summary, director); await settle();
    expect(host!.querySelector(".target-recovery-panel")?.textContent).toContain("GoldTier submission needs verification");
    expect(host!.querySelector(".case-technical-failure")?.textContent).toContain("A separate controlled failure needs inspection.");
    expect(host!.textContent).not.toContain("Resolve verified Policy result");
  });
});

describe("Lost confirmation response", () => {
  function readyToConfirm() {
    const summary = fixture("NOT_SUBMITTED");
    summary.status = "WAITING_FOR_REVIEW"; summary.current_stage = "READINESS";
    summary.technical_failure = null; summary.case.target_dispatch_confirmation = null;
    summary.clm.submission = null;
    summary.clm.submission_plan.request_preview = { dispatch_ready: true, environment: "SANDBOX", policy_version: 1, operations: [] };
    summary.active_exceptions = [{ exception_id: "confirm", exception_type: "TARGET_CONFIRMATION_REQUIRED", status: "OPEN", evidence_version: "current", explanation: "Confirm retained review", allowed_actions: [], blocker_codes: [], stage: "READINESS" }] as unknown as ZeroTouchCaseSummary["active_exceptions"];
    return summary;
  }
  it.each([
    new DOMException("Response lost", "TimeoutError"),
    new SyntaxError("PRIVATE_RESPONSE_BODY_FRAGMENT"),
  ])("posts once and observes retained success after response loss: %s", async (loss) => {
    const confirmation = vi.spyOn(api, "confirmZeroTouchTargetDispatch").mockRejectedValue(loss);
    const completed = fixture("SUBMISSION_CONFIRMED"); completed.version += 1; completed.status = "COMPLETED"; completed.technical_failure = null;
    const read = vi.spyOn(api, "fetchZeroTouchCase").mockResolvedValue(completed);
    const check = vi.spyOn(api, "checkZeroTouchTargetStatus");
    const resume = vi.spyOn(api, "resumeZeroTouchCase");
    await mount(readyToConfirm());
    const button = [...host!.querySelectorAll("button")].find((item) => item.textContent === "Confirm and send to GoldTier sandbox")!;
    await act(async () => { button.click(); button.click(); }); await settle();
    expect(confirmation).toHaveBeenCalledOnce(); expect(read).toHaveBeenCalledOnce();
    expect(check).not.toHaveBeenCalled(); expect(resume).not.toHaveBeenCalled();
    expect(host!.querySelector("#submission-state-title")?.textContent).toBe("Submission confirmed");
    expect(host!.textContent).not.toContain("Response lost");
    expect(host!.textContent).not.toContain("PRIVATE_RESPONSE_BODY_FRAGMENT");
  });
});
