import { renderToStaticMarkup } from "react-dom/server";
import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { confirmZeroTouchTargetDispatch } from "../api";
import { caseQueryKeys, caseSummaryMutationEffect, targetConfirmationMutationEffect } from "../caseQueries";
import type { AuthenticatedProfile, BlockerDecisionRecord, ZeroTouchCaseSummary, OwnershipAnalysisRecord } from "../types";
import { gardenAssumedBasisFixture } from "./ownershipAssumedBasisFixture";
import { ownershipStructureFixture } from "./ownershipStructureFixture";
import ReviewAndSend from "./ReviewAndSend";

function summaryFixture(environment: "MOCK" | "SANDBOX" = "SANDBOX"): ZeroTouchCaseSummary {
  return {
    version: 7,
    evidence_decision_authorized: true,
    document_replacement_authorized: true,
    ownership_edit_authorized: false,
    case: {
      case_id: "case-1",
      team_id: "TEAM_A",
      requested_uen: "201900001A",
      initial_identity: { legal_name: "Example Pte Ltd", registration_number: "201900001A", country_of_incorporation: "SG" },
      identity_corrections: [],
      target_dispatch_confirmation: null,
      entity: {
        legal_name: "Example Pte Ltd",
        registration_number: "201900001A",
        country_of_incorporation: "SG",
        party_type: "Organisation",
        source: { source_system: "ACRA", environment: "SANDBOX", retrieved_at: "2026-09-29T00:00:00Z" },
      },
      events: [{ sequence: 1 }, { sequence: 2 }, { sequence: 3 }],
    },
    clm: {
      version: 4,
      submission_plan: {
        environment,
        provider_classification: environment === "SANDBOX" ? "SANDBOX_PARTIAL" : "MOCK",
        request_preview: {
          dispatch_ready: true,
          environment,
          policy_version: 2,
          operations: [{
            operation: "SHELL",
            validation: "VALID",
            missing_fields: [],
            fields: [{ target_field: "legal_name", value: "Example Pte Ltd", provenance: "REGISTRY", authority: "CANONICAL_EVIDENCE", required: true, missing: false, validation: "VALID" }],
          }],
        },
      },
      target_search_checkpoint: { status: "COMPLETED", disposition: "NO_MATCH", selected_party_id: null },
      readiness: { warnings: ["SANDBOX_PARTIAL"], blockers: [] },
      submission: null,
    },
    target_classification: {
      vocabulary_version: "v1",
      editable: true,
      kyc_customer_type: { selected_value: "CORPORATE" },
      client_segment: { selected_value: "SME" },
    },
    classification_consistency: {
      status: "COMPATIBLE",
      title: "Legal form and KYC selection are consistent",
      explanation: "The source legal form and selected KYC customer type use the same company category.",
      blocking: false,
      authority: "PROJECT_ADVISORY_ONLY",
    },
    active_exceptions: [{ exception_type: "TARGET_CONFIRMATION_REQUIRED" }],
  } as unknown as ZeroTouchCaseSummary;
}

const actor: AuthenticatedProfile = {
  user_id: "case-user",
  display_name: "Case User",
  role: "CLIENT_ONBOARDER",
  team_id: "team-1",
  team_display_name: "Team 1",
  team_type: "CLIENT",
  team_description: "",
  client_scope_label: "Clients",
  capabilities: ["CASE_ACCESS"],
};

function render(summary = summaryFixture(), profile = actor, ownership: OwnershipAnalysisRecord | null = null): string {
  return renderToStaticMarkup(
    <ReviewAndSend
      summary={summary}
      documents={[]}
      ownership={ownership}
      actor={profile}
      busy={false}
      onConfirm={() => undefined}
      onSaveDraft={() => undefined}
      onReviewOutstanding={() => undefined}
      onEditIdentity={() => undefined}
      onEditClassification={() => undefined}
      onEditDocuments={() => undefined}
      onEditOwnership={() => undefined}
    />,
  );
}

describe("ReviewAndSend", () => {
  it("lists only backend-qualified natural persons with rounded effective, direct, indirect and source evidence", () => {
    const markup = render(summaryFixture(), actor, ownershipStructureFixture());
    expect(markup).toContain("Identified UBO candidates");
    expect(markup).toContain("Synthetic qualifying person");
    expect(markup).toContain("25% via this route");
    expect(markup).toContain("Meets the 25% threshold (25% or more)");
    expect(markup).not.toContain("GREATER_THAN_OR_EQUAL_TO");
    expect(markup).toContain("<dt>Indirect</dt><dd>25%</dd>");
    expect(markup).toContain("OFFICIAL_MOCK_PLUS_LOCAL_SUPPLEMENT");
    expect(markup).not.toContain("Synthetic below-threshold person");
  });
  it("explains assumed-basis matches apart from formal UBOs without enabling submission", () => {
    const summary = summaryFixture("MOCK");
    summary.clm.readiness!.blockers = ["OWNERSHIP_REVIEW_REQUIRED"];
    const markup = render(summary, actor, gardenAssumedBasisFixture());
    expect(markup).toContain("Identified UBO candidates");
    expect(markup).toContain("No natural person is formally classified as a provisional UBO; 2 meet the threshold only on an assumed basis (below).");
    expect(markup).toContain("Meets the threshold on an assumed basis — review required");
    expect(markup).toContain("They are not verified or provisionally classified UBOs and do not clear ownership readiness.");
    expect(markup).toContain("ABCD123");
    expect(markup).toContain("POC equal-unit assumption");
    expect(markup).toContain("LIM CHOON HUAT");
    expect(markup).toContain("Local synthetic overlay basis");
    expect(markup).not.toContain("Confirm and send to Mock GoldTier");
    expect(markup).toContain("Review outstanding items");
    // F5: assessed people, formal provisional UBOs and assumed-basis matches stay distinct.
    expect(markup).toContain("Ownership: 4 natural person(s) assessed, 0 provisional UBO candidate(s), 2 assumed-basis threshold match(es),");
    expect(markup).not.toContain("4 provisional candidate(s)");
  });

  it("D-082: an accepted POC basis keeps the disclosure without outdated review wording", () => {
    const summary = summaryFixture("MOCK");
    const markup = render(summary, actor, { ...gardenAssumedBasisFixture(), poc_basis_accepted: true });
    expect(markup).toContain("Meets the threshold on an assumed basis");
    expect(markup).not.toContain("Meets the threshold on an assumed basis — review required");
    expect(markup).toContain("These percentages meet the configured threshold under declared POC assumptions. They are not verified legal UBO determinations or provisionally classified UBOs.");
    expect(markup).not.toContain("do not clear ownership readiness");
    expect(markup).toContain("Ownership: 4 natural person(s) assessed, 0 provisional UBO candidate(s), 2 assumed-basis threshold match(es),");
  });
  it("D-124: separates operational readiness from the open, provisional ownership review", () => {
    const open = render(summaryFixture(), actor, { ...gardenAssumedBasisFixture(), state: "REVIEW_REQUIRED", poc_basis_accepted: false });
    expect(open).toContain("Ownership review:");
    expect(open).toContain("still unresolved");
    expect(open).toContain("provisional, not verified");
    const accepted = render(summaryFixture(), actor, { ...gardenAssumedBasisFixture(), state: "REVIEW_REQUIRED", poc_basis_accepted: true });
    expect(accepted).not.toContain("ownership-review-open");
  });

  it("renders the current mapping, truthful sandbox boundary, and print control", () => {
    const markup = render();
    expect(markup).toContain("Review and send");
    expect(markup).toContain("GoldTier Sandbox");
    expect(markup).toContain("Classification");
    expect(markup).toContain("Sandbox Partial");
    expect(markup).not.toContain("Verified existing customer");
    expect(markup).toContain("New customer");
    expect(markup).toContain("Shell - Valid");
    expect(markup).toContain("Example Pte Ltd");
    expect(markup).toContain("Legal form");
    expect(markup).toContain("Organisation");
    expect(markup).toContain("Owning team");
    expect(markup).toContain("TEAM_A");
    expect(markup).toContain("Edit company details");
    expect(markup).toContain("Edit classification");
    expect(markup).toContain("Edit documents");
    expect(markup).not.toContain("Edit ownership");
    expect(markup).toContain("Ownership source is review-only; no correction action is currently authorized.");
    expect(markup).toContain("Print / save PDF");
    expect(markup).toContain("review-and-send");
    expect(markup).toContain("Confirm and send to GoldTier sandbox");
    expect(markup).toContain("Current server review projection");
    expect(markup).not.toContain("Frozen server review projection");
    expect(markup).toContain("What will be sent");
    expect(markup).toContain("GoldTier approval status is outside this POC");
    expect(markup).not.toContain("Ready-for-Approval");
  });

  it("uses truthful Mock wording and withholds confirmation without CASE_ACCESS", () => {
    const mockMarkup = render(summaryFixture("MOCK"));
    expect(mockMarkup).toContain("Destination");
    expect(mockMarkup).toContain("Mock GoldTier (local POC)");
    expect(mockMarkup).toContain("Confirm and send to Mock GoldTier");
    const markup = render(summaryFixture(), { ...actor, capabilities: [] });
    expect(markup).not.toContain("Confirm and send to GoldTier sandbox");
    expect(markup).toContain("do not have the case capability");
  });

  it("labels same-case identity corrections as local user input rather than verified provider identity", () => {
    const summary = summaryFixture();
    summary.case.identity_corrections = [{
      correction_id: "33333333-3333-4333-8333-333333333333",
      actor_id: "case-user",
      evidence_type: "USER_SUPPLIED_CORRECTION_POC",
      previous_identity: null,
      corrected_identity: {
        legal_name: "Example Pte Ltd",
        registration_number: "201900001A",
        country_of_incorporation: "SG",
      },
      previous_search_request_id: null,
      corrected_at: "2026-09-29T04:00:00Z",
    }];

    const markup = render(summary);
    expect(markup).toContain("user-supplied same-case correction");
    expect(markup).toContain("not provider verified");
    expect(markup).not.toContain("operator-verified source");
  });

  it("shows draft and outstanding-item actions before eligibility and exposes stale/error state", () => {
    const summary = summaryFixture();
    summary.active_exceptions = [];
    summary.clm.target_search_checkpoint!.status = "STALE";
    const markup = renderToStaticMarkup(
      <ReviewAndSend
        summary={summary}
        documents={[]}
        ownership={null}
        actor={actor}
        busy={false}
        error="The reviewed version is stale."
        onConfirm={() => undefined}
        onSaveDraft={() => undefined}
        onReviewOutstanding={() => undefined}
        onEditIdentity={() => undefined}
        onEditClassification={() => undefined}
        onEditDocuments={() => undefined}
        onEditOwnership={() => undefined}
      />,
    );
    expect(markup).toContain("Save draft");
    expect(markup).toContain("Review outstanding items");
    expect(markup).toContain("Target search evidence is Stale");
    expect(markup).toContain("The reviewed version is stale.");
  });

  it("labels a retained manual declaration as local and unverified while preserving independent blockers", () => {
    const summary = summaryFixture();
    summary.ownership_recovery = {
      analysis_id: "22222222-2222-4222-8222-222222222222",
      version: 5,
      state: "ANALYZED",
      manual_evidence_action: null,
      review_receipt: {
        case_id: "case-1",
        actor_id: "case-user",
        reviewed_at: "2026-09-29T03:00:00Z",
        rationale: "Reviewed against the signed declaration.",
        evidence_document_id: "11111111-1111-4111-8111-111111111111",
        evidence_document_version: 3,
        evidence_reference: "MANUAL_DOC_11111111_V3",
        source_type: "USER_SUPPLIED_DECLARATION",
        provider_name: "MANUAL_DECLARATION_POC",
        provider_environment: "LOCAL",
        as_of_date: "2026-09-28",
      },
    };
    summary.clm.readiness!.warnings = ["TARGET_CONFIRMATION_REQUIRED"];
    const markup = render(summary);
    expect(markup).toContain("user-supplied declaration retained locally");
    expect(markup).toContain("not ACRA or verified ownership evidence");
    expect(markup).toContain("Manual ownership reviewed by case-user");
    expect(markup).toContain("MANUAL_DOC_11111111_V3");
    expect(markup).toContain("TARGET_CONFIRMATION_REQUIRED");
    expect(markup).toContain("Confirm and send to GoldTier sandbox");
  });

  it("offers ownership editing only when the backend authorizes manual evidence", () => {
    const summary = summaryFixture();
    summary.ownership_edit_authorized = true;
    summary.ownership_recovery = {
      analysis_id: "22222222-2222-4222-8222-222222222222",
      version: 5,
      state: "REVIEW_REQUIRED",
      manual_evidence_action: "MANUAL_OWNERSHIP_EVIDENCE",
      review_receipt: null,
    };

    const markup = render(summary);
    expect(markup).toContain("Edit ownership");
    expect(markup).not.toContain("Ownership source is review-only; no correction action is currently authorized.");
  });

  it("offers calculated ownership editing only with current backend authority", () => {
    const summary = summaryFixture();
    summary.ownership_edit_authorized = true;
    expect(render(summary)).toContain("Edit ownership");
    summary.ownership_edit_authorized = false;
    summary.evidence_decision_authorized = false;
    const markup = render(summary);
    expect(markup).not.toContain("Edit ownership");
    expect(markup).not.toContain("Edit documents");
    expect(markup).not.toContain("Edit company details");
  });

  it("calls the projection frozen only after confirmation and displays the retaining actor", () => {
    const summary = summaryFixture();
    summary.case.target_dispatch_confirmation = {
      confirmation_id: "confirmation-1",
      actor_id: "case-user",
      confirmed_at: "2026-09-29T04:00:00Z",
      case_event_count: 3,
      clm_version: 4,
      destination: "GOLDTIER_XPI_SANDBOX",
      warnings: [],
      review_digest: "a".repeat(64),
      classification: "USER_AUTHORIZED_POC",
    };
    const markup = render(summary);
    expect(markup).toContain("Frozen server review projection");
    expect(markup).toContain("Confirmed by case-user");
    expect(markup).not.toContain("Current server review projection");
    expect(markup).not.toContain("Edit company details");
    expect(markup).not.toContain("Edit classification");
    expect(markup).not.toContain("Edit documents");
    expect(markup).not.toContain("Edit ownership");
  });

  it("retains accepted configuration revision, unavailable fields, and rebind actor provenance", () => {
    const summary = summaryFixture();
    summary.case.policy_rebind = {
      revision: 2,
      configuration_status: "CURRENT_ACCEPTED_POC",
      accepted_poc_fields: ["customerExternalSystem", "registrationType", "policy", "bookingEntity"],
      editable_fields: ["kycCustomerType", "clientSegment"],
      upstream_fields: ["registrationNumber"],
      unavailable_fields: ["accountEntityType", "productType"],
      last_rebound_by: "case-user",
      last_rebound_at: "2026-09-29T02:00:00Z",
      last_rationale: "Replace superseded SG POC target constants.",
      last_changed_fields: ["customerExternalSystem", "registrationType", "policy", "bookingEntity"],
    };
    const markup = render(summary);
    expect(markup).toContain("Account entity type: Saved in this case; not transmitted to GoldTier");
    expect(markup).toContain("Product type: Saved in this case; not transmitted to GoldTier");
    expect(markup).toContain("POC configuration revision 2 - CURRENT_ACCEPTED_POC");
    expect(markup).toContain("Configuration rebound by case-user");
  });

  it("renders retained CONTINUE_WITH_WARNING history without inventing AUTO_RESOLVED", () => {
    const summary = summaryFixture();
    const retainedWarning: BlockerDecisionRecord = {
      decision_id: "decision-warning-1",
      case_id: "case-1",
      exception_id: null,
      evidence_version: "readiness:4",
      automation_version: 7,
      recorded_at: "2026-09-29T02:00:00Z",
      metadata: {
        blocker_code: "RELATED_PARTY_WRITE_NOT_EXECUTED",
        exception_type: null,
        classification: "CONTINUE_WITH_WARNING",
        policy_version: "BLOCKER_DECISION_POC_V1",
        rule_version: "RELATED_PARTY_WARNING_V1",
        owner: "POLICY_OWNER",
        minimum_inputs: ["CURRENT_READINESS_WARNING"],
        permitted_actions: ["RETAIN_READINESS_WARNING"],
        currently_available_actions: ["RETAIN_READINESS_WARNING"],
        resume_stage: null,
        resume_transition: "RETAIN_NOTE_WITHOUT_WORKFLOW_CHANGE",
        resume_ready: false,
        invalidated_dependencies: ["TARGET_PLAN", "TARGET_PLAN"],
        explanation: "Related-party writes remain unsupported and the warning is retained.",
        unknowns: [],
      },
      actor_id: null,
      reviewer_id: null,
    };
    summary.non_blocking_decisions = [retainedWarning, retainedWarning];
    const markup = render(summary);
    expect(markup).toContain("Important notes before sending");
    expect(markup).toContain("Related-party submission is not included");
    expect(markup).toContain("Non-blocking");
    expect(markup).toContain("Technical details and audit appendix");
    expect(markup).toContain("Continue with warning decision decision-warning-1 - BLOCKER_DECISION_POC_V1 - rule RELATED_PARTY_WARNING_V1");
    expect(markup.match(/RELATED_PARTY_WRITE_NOT_EXECUTED/g)).toHaveLength(1);
    expect(markup.match(/Target plan/g)).toHaveLength(1);
    expect(markup).not.toContain("Auto resolved");
  });

  it.each([
    ["OPERATOR_REVIEW", "Review legal form and KYC customer type", true],
    ["UNKNOWN_LEGAL_FORM", "Legal form needs operator review", true],
    ["COMPATIBLE", "Legal form and KYC selection are consistent", false],
  ] as const)("renders %s classification advice with a direct KYC edit control", (status, title, visible) => {
    const summary = summaryFixture();
    summary.classification_consistency = {
      status,
      title,
      explanation: visible ? "Review the classification before sending." : "The categories are consistent.",
      blocking: false,
      authority: "PROJECT_ADVISORY_ONLY",
    };
    const markup = render(summary);
    expect(markup.includes(title)).toBe(visible);
    expect(markup.includes("Review KYC classification")).toBe(visible);
    if (visible) expect(markup).toContain("no sponsor or regulatory incompatibility rule is claimed");
  });

  it("translates retained codes once and keeps raw evidence in the technical appendix", () => {
    const summary = summaryFixture();
    summary.clm.readiness!.warnings = [
      "IDP_PROFILE_PROVISIONAL",
      "UBO_POLICY_NOT_SPONSOR_CONFIRMED",
      "RELATED_PARTY_MAPPING_PENDING",
    ];
    const markup = render(summary);
    expect(markup.match(/Document extraction uses the current POC parser/g)).toHaveLength(1);
    expect(markup.match(/Check the configured ownership threshold/g)).toHaveLength(1);
    expect(markup).toContain("aggregated ownership at or above 25%");
    expect(markup).toContain("an older assessment or a different configured threshold");
    expect(markup).not.toContain("still requires human approval");
    expect(markup.match(/Related-party submission is not included/g)).toHaveLength(1);
    expect(markup).not.toContain("Continue with warning</strong>");
    expect(markup).toContain("IDP_PROFILE_PROVISIONAL, UBO_POLICY_NOT_SPONSOR_CONFIRMED, RELATED_PARTY_MAPPING_PENDING");
  });
});

describe("confirmZeroTouchTargetDispatch", () => {
  it("posts the three expected versions once to confirmation and never a submit endpoint", async () => {
    const response = summaryFixture();
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);

    await confirmZeroTouchTargetDispatch("case-1", {
      expected_automation_version: 7,
      expected_clm_version: 4,
      expected_case_event_count: 3,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/clm/zero-touch/cases/case-1/target-confirmation");
    expect(url).not.toContain("submit");
    expect(JSON.parse(String(init.body))).toEqual({ expected_automation_version: 7, expected_clm_version: 4, expected_case_event_count: 3 });
  });
});

describe("targetConfirmationMutationEffect", () => {
  it("prevents an in-flight older detail GET from overwriting confirmed completion", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const older = summaryFixture();
    const completed = { ...older, status: "COMPLETED" as const, version: older.version + 1 };
    let resolve!: (value: typeof older) => void;
    let signal!: AbortSignal;
    const pending = new Promise<typeof older>((done) => { resolve = done; });
    const inflight = client.fetchQuery({
      queryKey: caseQueryKeys.detail("case-user", "case-1"),
      queryFn: (context) => { signal = context.signal; return pending; },
    }).catch(() => undefined);
    await targetConfirmationMutationEffect(client, "case-user", completed);
    resolve(older);
    await inflight;
    expect(client.getQueryData(caseQueryKeys.detail("case-user", "case-1"))).toEqual(completed);
    expect(signal.aborted).toBe(true);
    client.clear();
  });

  it("rejects an older independently polled summary after confirmed completion", () => {
    const client = new QueryClient();
    const older = summaryFixture();
    const completed = { ...older, status: "COMPLETED" as const, version: older.version + 1 };
    client.setQueryData(caseQueryKeys.detail("case-user", "case-1"), completed);
    caseSummaryMutationEffect(client, "case-user", older);
    expect(client.getQueryData(caseQueryKeys.detail("case-user", "case-1"))).toEqual(completed);
    client.clear();
  });

  it("publishes the case and invalidates only the confirming user's scopes", async () => {
    const client = new QueryClient();
    const summary = summaryFixture();
    client.setQueryData(caseQueryKeys.detail("other-user", "case-1"), { marker: "untouched" });
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const remove = vi.spyOn(client, "removeQueries");

    await targetConfirmationMutationEffect(client, "case-user", summary);

    expect(client.getQueryData(caseQueryKeys.detail("case-user", "case-1"))).toBe(summary);
    expect(client.getQueryData(caseQueryKeys.detail("other-user", "case-1"))).toEqual({ marker: "untouched" });
    expect(invalidate.mock.calls.every(([filters]) => JSON.stringify(filters?.queryKey).includes("case-user"))).toBe(true);
    expect(remove.mock.calls.every(([filters]) => JSON.stringify(filters?.queryKey).includes("case-user"))).toBe(true);
  });
});


it("provides an accessible focus destination for the existing Review and Send control", () => {
  expect(render()).toMatch(/id="case-review-and-send"[^>]*tabindex="-1"/);
});
