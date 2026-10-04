"""Generate the final sponsor guide from the existing blocker-decision catalogue."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/backend"))

from app.services.blocker_decision_policy import (
    BLOCKER_DECISION_POLICY_VERSION,
    BlockerCatalogueEntry,
    blocker_catalogue,
)

GUIDE = ROOT / "docs/demo/BLOCKER_RECTIFICATION_GUIDE.md"


@dataclass(frozen=True)
class Scenario:
    trigger: str
    user_sees: str
    corrective_action: str
    next_stage: str
    retained_evidence: str
    calls: str
    limitations: str


_SYNTHETIC_CALLS = (
    "All external providers: 0. Synthetic Mock acquisition on a miss: "
    "ENTITY_PROFILE, OFFICERS, OWNERSHIP_PARTIES, RELATIONSHIPS once each; fresh COMPLETE "
    "cache hit: 0. Read-only Search runs once per authorized identity attempt; "
    "Shell/Policy/Amend: 0 before explicit confirmation."
)
_RETAINED = (
    "Current evidence remains bound to its case/version/generation. Superseded documents, "
    "identity corrections, prior registry/ownership evidence, decisions, and timeline stay "
    "historical. Resolved/cancelled exceptions leave active issues; stale requests cannot "
    "make them current again."
)
_LOCAL_LIMIT = (
    "Use isolated local Mock/LOCAL fixtures only. Confirmation is local POC dispatch, "
    "not sponsor approval or legal UBO. A stated control is conditional on backend "
    "current actions and state; no manual refresh is part of the supported happy recovery."
)
_UNIT_SCENARIO = Scenario(
    trigger="Use the owning backend test's synthetic fault/state seam for the listed code; "
    "there is no supplied user-uploadable fixture that guarantees this code.",
    user_sees="The sanitized current blocker/stage and absence reason, without raw failure details.",
    corrective_action="Inspect the declared-action paths below. If no current browser control "
    "is listed, retain the issue for the named owner; do not retry, waive, or change provider.",
    next_stage="The retained stage stays paused until the existing owner accepts valid evidence.",
    retained_evidence=_RETAINED,
    calls="All external providers: 0. No recovery target mutation is authorized by this guide.",
    limitations="Unit-only coverage reference. No end-to-end browser demonstration or current "
    "case resolution is claimed for a declared action lacking a browser control.",
)

SCENARIOS = {
    "wrong_uen": Scenario(
        trigger="In the synthetic local app create a case with eligible but absent 99999999Z "
        "and a legal name/country SG, or use the initial incomplete identity fixture. "
        "Correct to 202400001A; Phase24 covers A -> B -> A and repeated same-UEN correction.",
        user_sees="Registry identity attention with the safe not-found/ineligible explanation "
        "and the current identity correction control.",
        corrective_action="Open Registry identity, choose Edit UEN, enter 202400001A, and "
        "choose Verify UEN and resume. For missing initial identity supply name/UEN/SG via "
        "the authorized identity Search recheck. Do not create a replacement case.",
        next_stage="Registry verification -> bounded read-only Search -> Documents & reconciliation "
        "or the exact remaining current evidence stage. Target mutation stays stopped.",
        retained_evidence=_RETAINED,
        calls=_SYNTHETIC_CALLS,
        limitations=_LOCAL_LIMIT
        + " Unknown UEN verification rejects without canonical mutation "
        "or Search; an unsupported country is never silently converted to SG.",
    ),
    "registry_incomplete": Scenario(
        trigger="Current incomplete registry seams emit ACRA_ENTITY_NOT_FOUND or "
        "CANONICAL_DATA_INCOMPLETE. REGISTRY_RECHECK_INCOMPLETE remains supported "
        "for valid retained synthetic records; the catalogue regression binds that "
        "historical rule. Do not edit owner records to manufacture it.",
        user_sees="Incomplete registry evidence and conditional same-case identity verification.",
        corrective_action="If identity is wrong, use Registry identity > Edit UEN > Verify UEN "
        "and resume. Supply a currently verifiable eligible SG identity. If the correct identity "
        "still returns incomplete provider/canonical data, keep the blocker for registry review.",
        next_stage="Registry -> Search only after verification succeeds; otherwise Registry remains paused.",
        retained_evidence=_RETAINED,
        calls=_SYNTHETIC_CALLS,
        limitations="No direct canonical/registry override or missing-field fabrication. These "
        "producer gaps have unit coverage; no dedicated browser fixture is claimed.",
    ),
    "jurisdiction": Scenario(
        trigger="Use the synthetic unresolved/conflicting country input from "
        "test_phase09_jurisdiction_gateway.py; SG is the only implemented registry.",
        user_sees="Jurisdiction evidence unresolved/conflicting; supported identity correction "
        "appears only under the current backend guards.",
        corrective_action="Explicitly provide a verifiable SG name/UEN/country through Registry "
        "identity. If evidence supports another jurisdiction, stop for the owner.",
        next_stage="Registry only after eligible explicit SG verification.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. Unsupported route: 0 registry/target calls. "
        "Valid local correction uses its normal synthetic registry/Search budget.",
        limitations="No arbitrary country resolver, non-SG registry, or source-precedence decision.",
    ),
    "document_required": Scenario(
        trigger="Create local 202400001A and leave supporting evidence absent. Use "
        "apps/backend/tests/fixtures/uat/clean-company-profile.pdf when intake is open.",
        user_sees="The Documents & reconciliation intake/required-document state.",
        corrective_action="Upload the matching synthetic PDF; complete its allowed field "
        "review. For PENDING_INPUTS choose the exact Continue/Start action when enabled.",
        next_stage="Documents/reconciliation -> Ownership & UBO after valid current evidence.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. Local PDF extraction/reconciliation only; no "
        "additional ACRA call for unchanged identity and no target writes before confirmation.",
        limitations=_LOCAL_LIMIT + " Initial upload alone does not start automation.",
    ),
    "document_replacement": Scenario(
        trigger="Use the existing document processing/unreadable/failed replacement synthetic "
        "seams and low-confidence fixture. Replace with clean-company-profile.pdf.",
        user_sees="Current evidence requires replacement; a historical document is read-only. "
        "Interrupted intake exposes its targeted reupload action.",
        corrective_action="Documents & reconciliation > current document > Replace document. "
        "For interrupted intake use the specific failed-record reupload, then Continue "
        "when the backend authorizes it.",
        next_stage="Re-evaluated Documents/reconciliation -> Ownership or the exact remaining blocker.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. Local extraction/reconciliation; no additional "
        "registry calls for unchanged identity; no target write until confirmation.",
        limitations=_LOCAL_LIMIT
        + " No value-selection waiver for unavailable document text.",
    ),
    "document_review": Scenario(
        trigger="Use the current low-confidence Mock IDP seam/low-confidence.pdf or the "
        "required-field-missing seam. These are synthetic fault fixtures, not real OCR.",
        user_sees="The required field, confidence/missing-value reason, current review control, "
        "or replacement requirement.",
        corrective_action="Documents & reconciliation > current document > confirm/correct the "
        "required field using the owning review decision. A missing/unverifiable field that "
        "cannot be corrected safely needs a replacement document.",
        next_stage="Document checkpoint refresh automatically re-evaluates reconciliation; "
        "then Ownership or the exact remaining evidence/confirmation action.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. Local review/extraction/reconciliation only; "
        "zero target writes while unresolved.",
        limitations=_LOCAL_LIMIT
        + " Low confidence does not authorize KEEP_REGISTRY_VALUE "
        "or USE_DOCUMENT_VALUE before current evidence becomes valid.",
    ),
    "document_discrepancy": Scenario(
        trigger="Use the existing synthetic DOCUMENT_DISCREPANCY/LOW_CONFIDENCE seams. "
        "phase24-identity.e2e.ts constructs a PDF with document UEN 202400009I against "
        "entered 202400001A. Existing authenticated tests cover legal-name/address and "
        "supported country discrepancies.",
        user_sees="Entered/registry and document observations disagree, with current "
        "field-bound authorized actions and no silent source winner.",
        corrective_action="For a UEN conflict go to Registry identity and explicitly choose "
        "the supported document-detected UEN or type another UEN; Verify UEN and resume "
        "reverifies it. For legal name/address/country use Documents & reconciliation and "
        "only the displayed allowed field decision. If no decision is authorized, replace "
        "the document or request additional information.",
        next_stage="Registry/Search on identity correction; otherwise Document reconciliation "
        "-> Ownership -> readiness, stopping at any remaining current blocker.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. UEN correction on synthetic cache miss reacquires "
        "four registry operations and one read-only Search. Unchanged KEEP_REGISTRY_VALUE "
        "adds 0 calls. USE_DOCUMENT_VALUE that changes canonical identity, such as legal name, "
        "invalidates the Search checkpoint: after the last discrepancy clears, readiness "
        "may run the existing bounded read-only Search recheck (initial Search + recheck = 2). "
        "Registry acquisition and Shell/Policy/Amend mutations add 0; restart and repeated "
        "resume add 0 calls.",
        limitations=_LOCAL_LIMIT
        + " Country selection is bounded by current allowed_actions; "
        "non-SG routing is unsupported. No automatic document-UEN selection. A canonical "
        "identity-changing field decision cannot reuse stale Search, even when UEN is unchanged.",
    ),
    "ownership": Scenario(
        trigger="Use accepted Slice B Garden partnership synthetic offline decoder fixture "
        "11111999A and garden-partnership-reviewed-client.pdf, or OWNERSHIP_CYCLE/"
        "OWNERSHIP_INCOMPLETE/indeterminate synthetic Mock evidence. Contradictory ownership "
        "uses the actual ownership-evidence unit seam.",
        user_sees="Incomplete/review-required ownership with LOCAL structured declaration "
        "action only for a current pre-confirmation ownership review.",
        corrective_action="Open Ownership & UBO. Upload/review current supporting evidence "
        "if required. Enter the explicitly reviewed structured parties, percentages and "
        "relationships in ManualOwnershipEvidenceForm with the receipt; submit the "
        "declaration. Garden's accepted synthetic declaration is 60/40.",
        next_stage="The single Decimal owner recalculates -> readiness -> classification or "
        "Review & Send. Remaining indeterminate evidence stays blocked.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. Garden offline acquisition dispatches only supported "
        "ENTITY_PROFILE/OFFICERS transport; unsupported company ownership operations stay "
        "unsupported. LOCAL manual declaration adds 0 registry and 0 target calls until confirmation.",
        limitations=_LOCAL_LIMIT
        + " Garden percentages are USER_SUPPLIED_DECLARATION / "
        "LOCAL / MANUAL_DECLARATION_POC, not registry ownership authority. No stand-alone "
        "browser RERUN_OWNERSHIP_ANALYSIS or legal UBO determination.",
    ),
    "search_review": Scenario(
        trigger="Use scripts/run_e2e.py --registry-demo synthetic-target-ambiguity with focused "
        "--grep 'Slice F ambiguous target match'. The isolated fixture creates two "
        "actual process-local Mock candidates through accepted Shell/Policy operations.",
        user_sees="Read-only Search identity review and bounded correction/recheck; no "
        "candidate binding or duplicate customer creation action.",
        corrective_action="Registry identity > correct the explicit name/UEN/SG > authorized "
        "read-only recheck; examine current resolver result.",
        next_stage="Registry/current evidence or the exact unresolved Search review; target "
        "writes require resolver prerequisites and final confirmation.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. One local read-only Search per authorized attempt; "
        "zero Shell/Policy/Amend while identity remains ambiguous. Fixture setup uses four "
        "local Mock mutations separately; no browser-journey target writes.",
        limitations=_LOCAL_LIMIT
        + " Recheck is not identity confirmation/approval by itself.",
    ),
    "search_failure": Scenario(
        trigger="Use scripts/run_e2e.py --recovery-demo search-recheck with focused --grep "
        "'Slice C failed Search'. Create local 202400001A with clean-company-profile.pdf, "
        "then save Company - Private / Corporate classification. The inert XPI transport "
        "fails its first read-only Search with a synthetic timeout.",
        user_sees="Safe provider failure or missing/stale Search; it never implies NO_MATCH. "
        "A bounded read-only recheck appears only when the current identity path permits it.",
        corrective_action="Registry identity > Edit UEN > retain 202400001A > Verify UEN "
        "and resume. The existing registry-identity owner verifies it and performs the bounded "
        "read-only Search. If the backend does not expose this control, retain the failure.",
        next_stage="Current successful Search permits existing resolver flow; failure keeps "
        "target mutations blocked while permitted independent evidence intake remains usable.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. Before correction the offline target operation "
        "list is [SEARCH]; after correction it is [SEARCH, SEARCH], with 0 target writes. "
        "Only later explicit confirmation permits the ordinary inert target sequence.",
        limitations="EXTERNAL_DEPENDENCY describes the unavailable Search prerequisite. "
        "The dedicated browser fixture exercises an offline recovery path, not real provider "
        "availability. Timeout/malformed/unavailable variants also retain backend unit coverage.",
    ),
    "classification": Scenario(
        trigger="Use a current synthetic pre-confirmation case whose frozen vocabulary requires "
        "customer type/client segment; leave those choices unresolved.",
        user_sees="GOLDTIER_CLASSIFICATION_REQUIRED and the backend's current vocabulary options.",
        corrective_action="Classification & readiness > choose the valid customer type and "
        "client segment > save classification.",
        next_stage="Readiness re-evaluation -> Review & Send only after all prerequisites pass.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. Classification save: 0 provider calls/target writes; "
        "later confirmation may perform the existing bounded read-only Search.",
        limitations=_LOCAL_LIMIT
        + " Vocabulary choices are case-bound POC configuration.",
    ),
    "confirmation": Scenario(
        trigger="Use accepted local second-company 202400008H with "
        "multiple-owner-demo-client.pdf, or clean 202400001A with current reviewed evidence.",
        user_sees="All prerequisites satisfied; Review & Send is last and requests explicit "
        "confirmation. Before that action Shell/Policy/Amend remain uncalled.",
        corrective_action="Review & Send > inspect current identity/documents/ownership/"
        "classification/target destination > confirm reviewed target dispatch.",
        next_stage="Target sequence -> COMPLETED / MOCK_GOLDTIER_SUBMITTED. A changed "
        "confirmation-time Search/plan returns another explicit review.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. Existing confirmation-time read-only Search guard; "
        "new D2 Mock customer requires Shell, Policy, Amend and same-ID readback. "
        "Six connector calls [search, search, shell, policy, amend, search] correspond "
        "to five ledger markers. Optional omission belongs only to the explicit "
        "SYNTHETIC_OFFLINE XPI-shaped fixture below.",
        limitations=_LOCAL_LIMIT
        + " No autonomous/final approval or sponsor Ready-for-Approval.",
    ),
    "target_finalization": Scenario(
        trigger="Use scripts/run_e2e.py --recovery-demo retained-recovery with focused --grep "
        "'Slice C retained finalization recovery'. Create 202400001A with "
        "clean-company-profile.pdf, save Company - Private / Corporate classification, and "
        "explicitly confirm the offline sandbox-shaped dispatch. The fixture interrupts "
        "receipt construction twice through the existing bounded owner seam.",
        user_sees="Retained outcome with bounded automatic finalization; if still "
        "RECOVERY_PENDING, Complete safe recovery is the exact next control.",
        corrective_action="Allow the owning bounded finalization; if RECOVERY_PENDING remains, "
        "Target preparation / submission state > Complete safe recovery.",
        next_stage="The dedicated offline fixture finalizes RECOVERY_PENDING to COMPLETED "
        "without redispatching target operations. Other retained outcomes keep their "
        "already-decided review/failure semantics.",
        retained_evidence=_RETAINED,
        calls="All external providers: 0. The retained offline operation list is "
        "[SEARCH, SEARCH, SHELL, POLICY, READBACK] before and after Complete safe recovery; "
        "recovery adds exactly 0 target calls and Amend remains uncalled.",
        limitations="Dedicated browser coverage: Slice C retained finalization recovery makes "
        "no target replay in apps/frontend/e2e/slice-c-recovery.e2e.ts. This isolated "
        "SYNTHETIC_OFFLINE memory/LOCAL fixture constructs no external HTTP transport. "
        "An uncertain target outcome still requires separate provider verification, not retry.",
    ),
}


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _values(values: tuple[object, ...]) -> str:
    return ", ".join(map(str, values)) if values else "None"


def render_guide() -> str:
    entries = blocker_catalogue()
    counts = Counter(entry.classification for entry in entries)
    lines = [
        "# Blocker Rectification Guide",
        "",
        "Generated by scripts/generate_blocker_rectification_guide.py from",
        "apps/backend/app/services/blocker_decision_policy.py. Regenerate after changing",
        "the owner; --check and test_slice_c_blocker_catalogue.py reject drift.",
        "",
        f"Policy: {BLOCKER_DECISION_POLICY_VERSION}. Catalogue: {len(entries)} supported",
        "OPEN/target-recovery codes. The five guide categories are descriptive strings,",
        "not new durable enums or authorization. Six retained warnings and the one",
        "equivalent-document auto-confirm note are nonblocking records outside this count.",
        "",
        "Coverage references are not an execution claim. Slice C browser references identify",
        "the current isolated fixture tests; execution results belong to the implementation",
        "and independent gate reports. Existing test names do not prove every sibling code",
        "was browser-demonstrated. This guide contains no sponsor content or credentials.",
        "",
        "All external provider budgets are zero: ACRA, GoldTier Sandbox, GoldTier",
        "Production and other external providers. Fixtures are synthetic offline",
        "Mock/LOCAL. Directory paths below are repository-relative coverage/source links.",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    for category in (
        "USER_ACTION_REQUIRED",
        "OPERATOR_REVIEW_REQUIRED",
        "AUTOMATIC_RECOVERY",
        "EXTERNAL_DEPENDENCY",
        "HARD_STOP",
    ):
        lines.append(f"| {category} | {counts[category]} |")
    lines.extend(
        [
            "",
            "## Canonical inventory",
            "",
            "Each row binds to a rule detail and scenario below; core decision fields are",
            "derived from the existing rule specs, including all current exception bindings.",
            "",
            "| Code | Domain/stage | Guide classification | Rule | Scenario |",
            "|---|---|---|---|---|",
        ]
    )
    for entry in entries:
        lines.append(
            f"| {entry.code} | {entry.domain_stage} | {entry.classification} | "
            f"{entry.rule_version} | {entry.local_demo_scenario} |"
        )
    groups: dict[str, list[BlockerCatalogueEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.rule_version, []).append(entry)
    for version, group in groups.items():
        entry = group[0]
        scenario = SCENARIOS.get(entry.local_demo_scenario, _UNIT_SCENARIO)
        lines.extend(
            [
                "",
                f"## {version}",
                "",
                f"Codes: {_values(tuple(item.code for item in group))}.",
                "",
                "| Catalogue field | Current owner evidence |",
                "|---|---|",
            ]
        )
        facts = {
            "Domain/stage": entry.domain_stage,
            "Classification": entry.classification,
            "Durable policy classification": entry.policy_classification,
            "Exception bindings": _values(entry.exception_types),
            "Human explanation / why paused": entry.explanation,
            "Required input/evidence": _values(entry.required_inputs),
            "Declared available actions": _values(entry.declared_actions),
            "Current action predicate": entry.current_action_predicate,
            "No current valid action reason": entry.no_action_reason,
            "Permitted owner": entry.owner,
            "Resume stage / transition": f"{entry.resume_stage} / {entry.resume_transition}",
            "Invalidated dependencies": _values(entry.invalidated_dependencies),
            "Auto-resumes?": entry.auto_resume,
            "External dependency?": entry.external_dependency,
            "Local demo scenario": entry.local_demo_scenario,
            "Test coverage references": _values(entry.test_coverage),
        }
        for name, value in facts.items():
            lines.append(f"| {name} | {_cell(value)} |")
        lines.extend(
            [
                "",
                (
                    "| Declared action | Current browser control | Role/capability | "
                    "Owning write/transition | Predicate / absence reason |"
                ),
                "|---|---|---|---|---|",
            ]
        )
        for path in entry.action_paths:
            role = (
                f"{path.capability} / {_values(path.roles)}"
                if path.capability
                else ("No browser capability grant; owner diagnosis only")
            )
            lines.append(
                f"| {path.action} | {_cell(path.browser_control or 'No current browser action')} | "
                f"{_cell(role)} | {_cell(path.backend_owner or 'No local mutation')} | "
                f"{_cell(path.current_action_predicate)} Absence: {_cell(path.no_action_reason)} |"
            )
        lines.extend(["", "| Demo field | Synthetic/offline recipe |", "|---|---|"])
        for name, value in {
            "Scenario": entry.local_demo_scenario,
            "How to trigger / synthetic fixture": scenario.trigger,
            "What the user sees": scenario.user_sees,
            "Why paused": entry.explanation,
            "Exact corrective action": scenario.corrective_action,
            "Expected automatic resume": entry.auto_resume,
            "Expected next stage": scenario.next_stage,
            "Retained evidence/history": scenario.retained_evidence,
            "Provider calls expected": scenario.calls,
            "Limitations": scenario.limitations,
        }.items():
            lines.append(f"| {name} | {_cell(value)} |")
    lines.extend(
        [
            "",
            "## Unknown technical/provider codes",
            "",
            "Safe codes outside the supported set match the existing BPD-UNKNOWN-1 fail-closed",
            "decision. The catalogue's unknown_blocker_guidance accepts only the existing",
            "constrained SafeBlockerCode, never free-text exception/provider details.",
            "Classification: HARD_STOP; current browser actions: none; automatic resume: no.",
            "Timeout, malformed/unavailable provider response, persistence failure and unexpected",
            "target failure retain sanitized code/history/correlation evidence for diagnosis.",
            "A provider-declared code cannot become user-correctable by naming it differently.",
            "A mapped Search/document failure has only its explicitly guarded read-only recheck",
            "or replacement path; it does not authorize broad retries or write replay.",
            "",
            "## Adjacent current controls and neutral outcomes",
            "",
            "Case policy rebind is an adjacent current control, not an invented blocker code.",
            "Classification & readiness > PolicyRebindPanel is shown from case.policy_rebind.",
            "ZeroTouchOrchestrator.rebind_case_policy_snapshot requires current expected",
            "automation/CLM/case revisions, backend CASE_ACCESS/team scope, accepted SG POC",
            "catalogue and a pre-confirmation case. Supply the required rationale and use only",
            "the offered rebind. If the backend says unchanged, it is an idempotent no-op;",
            "classification choices and prior snapshot/audit remain retained. Re-evaluation",
            "may stop at classification/final confirmation; no provider write is implied.",
            "References: test_policy_rebind_preserves_case_choices_and_audits_previous_snapshot",
            "and test_current_policy_rebind_is_noop_and_reauthorization_precedes_mutation in",
            "apps/backend/tests/test_zero_touch_orchestration.py. Dedicated browser reference:",
            "Slice C stale policy rebind preserves selection and resumes in",
            "apps/frontend/e2e/slice-c-recovery.e2e.ts. Use scripts/run_e2e.py",
            "--recovery-demo stale-policy with focused --grep 'Slice C stale policy rebind'.",
            "The isolated fixture binds a supported synthetic legacy configuration on creation.",
            "After classification, open Classification & readiness, enter Rebind rationale, and",
            "choose Rebind accepted Singapore POC configuration. The owner retains snapshot",
            "revision 2, Company - Private / Corporate choices and the rebind receipt; the offline",
            "target operations remain [SEARCH] until explicit Review & Send confirmation.",
            "",
            (
                "GoldTier Search NO_MATCH is successful: "
                "“No existing customer found. Continuing as a new customer.”"
            ),
            "It is absent from this blocker inventory. Exact verified",
            "existing target reuse skips only the operations the ledger declares unnecessary.",
            "Fresh COMPLETE ACRA cache reuse is neutral and adds zero registry provider calls.",
            "Retained AMEND_NOT_REQUIRED means SKIPPED/NOT_REQUIRED and adds zero Amend calls.",
            "Use scripts/run_e2e.py --recovery-demo optional-amend with focused --grep",
            "'Slice C optional Amend and NO_MATCH'. Create 202400001A using",
            "clean-company-profile.pdf, save Company - Private / Corporate classification,",
            "and explicitly confirm the offline sandbox-shaped dispatch. The retained Amend",
            "outcome is AMEND_NOT_REQUIRED; its child stage is SKIPPED. The inert operation",
            "list is [SEARCH, SEARCH, SHELL, POLICY, READBACK], with no Amend request.",
            "",
            "The four --recovery-demo modes require a focused --grep and separate isolated",
            "composition; never combine them with Garden protocol or Slice B registry fixtures.",
            "scripts/slice_c_recovery_fixture.py supplies inert XPI protocol transport, memory",
            "state and LOCAL document extraction. Sandbox-shaped DTO wording is not an external",
            "Sandbox/Live call or interoperability claim. tests/test_slice_c_e2e_fixture_routing.py",
            "checks dispatch isolation and the zero-external-call owner seams.",
            "",
            "Required unsupported functionality stays review/blocked/external; it never becomes",
            "skipped to inflate progress. The existing projection counts COMPLETE, EMPTY",
            "(Complete — no records), and legitimate SKIPPED/NOT_REQUIRED stages in its numerator.",
            "FAILED, BLOCKED, REVIEW_REQUIRED and NOT_REACHED do not contribute. The accepted",
            "terminal automation status COMPLETED projects 100% POC completion, consistently",
            "with docs/ARCHITECTURE.md; final human approval remains outside this workflow.",
            "",
            "Browser coverage references: apps/frontend/e2e/slice-c-recovery.e2e.ts (current",
            "offline recovery tests), apps/frontend/e2e/phase24-identity.e2e.ts (UEN choices/currentness),",
            "apps/frontend/e2e/authenticated-zero-touch.e2e.ts (document review/replacement,",
            "ownership, navigation and final review), apps/frontend/e2e/zero-touch-exception.e2e.ts",
            "(field discrepancy/auto-resume/history), apps/frontend/e2e/slice-b-registry-demo.e2e.ts",
            "(Garden LOCAL evidence, second company and cache/no-call floor). Stale response",
            "and resolved-history verification uses the existing caseQueries publication owner",
            "and the current browser tests; no frontend workflow authority is created.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Reject generated guide drift."
    )
    args = parser.parse_args()
    expected = render_guide()
    if args.check:
        if not GUIDE.is_file() or GUIDE.read_text(encoding="utf-8") != expected:
            print(
                "Blocker rectification guide is stale; regenerate from the policy catalogue."
            )
            return 1
        print(
            f"Blocker rectification guide matches {len(blocker_catalogue())} catalogue codes."
        )
        return 0
    GUIDE.parent.mkdir(parents=True, exist_ok=True)
    GUIDE.write_text(expected, encoding="utf-8", newline="\n")
    print(
        f"Generated blocker rectification guide for {len(blocker_catalogue())} catalogue codes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
