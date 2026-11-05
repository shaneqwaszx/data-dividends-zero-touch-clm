import { CasePipelineAttention, type AttentionDestination } from "./CaseAttentionSummary";
import BlockerDecisionReview, { reviewableSourceDiscrepancies, type ReviewDraftHandle } from "./BlockerDecisionReview";
import type { ReviewDecisionBatch } from "../types";
import { confirmReviewDecisions } from "../api";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  checkZeroTouchTargetStatus,
  verifyCompletedGoldTier,
  recoverZeroTouchTarget,
  type TargetRecoveryInput,
  type TargetSearchObservation,
  confirmZeroTouchTargetDispatch,
  completeZeroTouchIntake,
  correctRegistryIdentity,
  deleteZeroTouchCase,
  fetchIntelligence,
  fetchOwnership,
  fetchZeroTouchCase,
  intakeZeroTouchDocument,
  replaceZeroTouchDocument,
  recheckZeroTouchIdentitySearch,
  confirmExistingGoldTierCustomer,
  rebindZeroTouchPolicy,
  submitManualOwnershipEvidence,
  confirmGovernmentStatus,
  reviewDocument,
  resolveZeroTouchException,
  resumeZeroTouchCase,
  retryZeroTouchIntakeDocument,
  updateCasePriority,
  updateGoldTierTargetClassification,
} from "../api";
import { startAutomationPolling } from "../automationPolling";
import { confirmationResponseMayBeLost, observeSubmissionOutcome } from "../submissionObservation";
import {
  caseDeletedEffect,
  publishCaseDetail,
  retainNewestVersionedEvidence,
  caseDetailQueryOptions,
  caseSummaryMutationEffect,
  caseSupportingMutationEffect,
  documentQueryOptions,
  intelligenceQueryOptions,
  identitySearchRecheckMutationEffect,
  manualOwnershipMutationEffect,
  ownershipQueryOptions,
  policyRebindMutationEffect,
  priorityMutationEffect,
  targetConfirmationMutationEffect,
} from "../caseQueries";
import { displayTimestamp, formatTimestamp, shouldPollAutomation, targetOutcomeLabel } from "../shared";
import type {
  DocumentProcessingRecord,
  AuthenticatedProfile,
  HumanInterventionProjection,
  OwnershipAnalysisRecord,
  ProcessingNode,
  ReadinessStageStatus,
  SimulationProfile,
  ZeroTouchCaseSummary,
} from "../types";
import {
  businessStageMembers,
  CompletedOverview,
  ConfirmDetailsPanel,
  stageStatusFor,
  GOLDTIER_DETAILS_STAGE_LABEL,
  GOLDTIER_DETAILS_STEP_ID,
  DetailedProcessingInspector,
  findBusinessStage,
  findProcessingNode,
  OnboardingProgressPanel,
  OperationalTiming,
  processingNodeFocusTarget,
  ProcessingBlockerPanels,
  RegistryStatePanel,
} from "./CaseStatePanels";
import { type EvidenceFocusTarget } from "./CaseStateExplanationPanel";
import PriorityControl from "./PriorityControl";
import DeleteCaseDialog from "./DeleteCaseDialog";
import DocumentEvidencePanel, {
  canContinueRecoveredIntake, isCurrentDocument, isDocumentReuploadRequired, type DocumentReviewRequest,
} from "./DocumentEvidencePanel";
import OwnershipPathExplorer, { OwnershipSupportingDetails } from "./OwnershipPathExplorer";
import IntelligencePanel from "./IntelligencePanel";
import GoldTierRequestPreview from "./GoldTierRequestPreview";
import RegistryProvenancePanel from "./RegistryProvenancePanel";
import TargetClassificationPanel, { TargetClassificationDetails } from "./TargetClassificationPanel";
import HumanInterventionPanel from "./HumanInterventionPanel";
import AdvisoryContinuation from "./AdvisoryContinuation";
import ReviewAndSend from "./ReviewAndSend";
import TargetRecoveryPanel, { TargetRecoveryDetails } from "./TargetRecoveryPanel";
import StageDisclosure, { revealStage } from "./StageDisclosure";
import OnboardingWorkspace, { onboardingExecutionMessage, onboardingIsExecuting } from "./OnboardingWorkspace";
import IdentityCorrectionForm from "./IdentityCorrectionForm";
import UenRouteNote from "./UenRouteNote";
import ManualOwnershipEvidenceForm from "./ManualOwnershipEvidenceForm";
import GovernmentStatusPanel from "./GovernmentStatusPanel";
import { UPLOAD_ACCEPT, UPLOAD_HELP_TEXT } from "../uploadLimits";
import PolicyRebindPanel, { PolicyRebindDetails } from "./PolicyRebindPanel";

const EVIDENCE_TARGET_IDS: Record<EvidenceFocusTarget, string> = {
  identity: "case-identity-correction",
  registry: "case-evidence-registry",
  documents: "case-evidence-documents",
  reconciliation: "case-evidence-reconciliation",
  ownership: "case-evidence-ownership",
  classification: "case-target-classification",
  policy: "case-policy-rebind",
  recovery: "case-evidence-recovery",
};
const SEARCH_TARGET_ID = "case-existing-customer-search";
const MANUAL_OWNERSHIP_TARGET_ID = "case-manual-ownership-evidence";

interface CaseActionIdentity {
  readonly generation: number;
  readonly caseId: string;
  readonly actorUserId: string;
}

interface RetainedTargetStatusCheck {
  attempted: true;
  result: TargetSearchObservation | null;
  error: string | null;
}

interface TargetStatusCheckView extends RetainedTargetStatusCheck {
  identity: string;
  checking: boolean;
}

interface EvidenceFocusNotice {
  readonly identity: string;
  readonly message: string;
}

/** "NOT_SUBMITTED" -> "Not submitted" for display. */
function titleCaseWords(value: string): string {
  const words = value.replaceAll("_", " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

function readinessTone(status: ReadinessStageStatus): "done" | "attention" | "pending" {
  if (status === "READY" || status === "SUBMITTED") return "done";
  if (status === "MISSING" || status === "BLOCKED" || status === "FAILED" || status === "REVIEW_REQUIRED") return "attention";
  return "pending";
}

export interface PendingDocuments {
  fileNames: string[];
  busy: boolean;
  progress: string | null;
  error: string | null;
  onUpload: () => void;
  onDiscard: () => void;
}

export function PendingDocumentsBanner({ pending }: { pending: PendingDocuments }) {
  const count = pending.fileNames.length;
  return (
    <section className="ds-banner pending-documents" aria-labelledby="pending-documents-title" role="status">
      {/* An upload in progress has not stopped or failed; show only its progress. */}
      {pending.busy ? <>
        <h3 id="pending-documents-title">{count === 1 ? "1 document is being uploaded" : `${count} documents are being uploaded`}</h3>
        {pending.progress && <p className="control-help">{pending.progress}</p>}
      </> : pending.error ? <>
        {/* The upload reached the backend and was refused; say so instead of implying it never ran. */}
        <h3 id="pending-documents-title">{count === 1 ? "Your document couldn't be uploaded" : `${count} documents couldn't be uploaded`}</h3>
        <p>{pending.fileNames.join(", ")} — the upload was rejected. Fix the cause below, then try again.</p>
        <p className="control-help pending-documents__error">{pending.error}</p>
      </> : <>
        <h3 id="pending-documents-title">{count === 1 ? "1 document is waiting to upload" : `${count} documents are waiting to upload`}</h3>
        <p>{pending.fileNames.join(", ")} — not uploaded yet because the case stopped before document intake. Fix the issue above (for example, complete the company details), then upload.</p>
        {pending.progress && <p className="control-help">{pending.progress}</p>}
      </>}
      {!pending.busy && <div className="pending-documents__actions">
        <button type="button" className="btn btn-primary" onClick={pending.onUpload}>{pending.error ? "Try upload again" : "Upload now"}</button>
        <button type="button" className="btn btn-ghost" onClick={pending.onDiscard}>Discard</button>
      </div>}
    </section>
  );
}

export function shouldRefreshAfterMutationError(error: unknown): boolean {
  return error instanceof TypeError || (error instanceof ApiError && [409, 503].includes(error.status));
}

export default function CaseDetail({
  caseId,
  actor,
  onBack,
  onViewAudit,
  registryProviderMode,
  initialFocusNodeId,
  pendingDocuments,
  onDeleted,
}: {
  caseId: string;
  actor: AuthenticatedProfile;
  onBack: () => void;
  onViewAudit: (caseId: string) => void;
  registryProviderMode?: SimulationProfile["registry_provider_mode"];
  initialFocusNodeId?: string;
  /** Documents chosen at Create onboarding that are not uploaded yet (e.g. the registry step stopped first). */
  pendingDocuments?: PendingDocuments;
  /** Called after the backend confirms this case was deleted, before returning to Cases. */
  onDeleted?: (caseId: string) => void;
}) {
  const queryClient = useQueryClient();
  const batchReviewRef = useRef<ReviewDraftHandle>(null);
  const [pendingProcessingFocus, setPendingProcessingFocus] = useState<(CaseActionIdentity & {
    nodeId: string; automationVersion: number;
  }) | null>(null);
  const evidenceIdentity = `${actor.user_id}:${caseId}`;
  // AuthProvider remounts this subtree for each authenticated session generation.
  const disclosureIdentity = `${evidenceIdentity}:${actor.role}:${actor.team_id}`;
  const detailQuery = useQuery(caseDetailQueryOptions(actor.user_id, caseId));
  const documentQuery = useQuery(documentQueryOptions(actor.user_id, caseId));
  const ownershipQuery = useQuery(ownershipQueryOptions(actor.user_id, caseId));
  const intelligenceQuery = useQuery(intelligenceQueryOptions(actor.user_id, caseId));
  const summary = detailQuery.data ?? null;
  const focusVersion = useRef(summary?.version);
  focusVersion.current = summary?.version;
  const [pendingAttention, setPendingAttention] = useState<(CaseActionIdentity & {
    version: number; destination: AttentionDestination;
  }) | null>(null);
  const documents = documentQuery.data ?? [];
  const ownership = ownershipQuery.data ?? null;
  const intelligence = intelligenceQuery.data ?? null;
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState<string | null>(null);
  const [mutationBlocked, setMutationBlocked] = useState(false);
  const [caseUnavailable, setCaseUnavailable] = useState(false);
  const [evidenceFocusNotice, setEvidenceFocusNotice] = useState<EvidenceFocusNotice | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState<CaseActionIdentity | null>(null);
  const [targetStatusCheck, setTargetStatusCheck] = useState<TargetStatusCheckView | null>(null);
  const targetStatusController = useRef<AbortController | null>(null);
  const submissionObservationController = useRef<AbortController | null>(null);
  const [confirmationUnknownIdentity, setConfirmationUnknownIdentity] = useState<string | null>(null);
  const confirmationUnknown = confirmationUnknownIdentity === evidenceIdentity;
  const targetSubmission = summary?.target_submission;
  const safeContinuation = summary?.status === "RECOVERY_PENDING"
    && targetSubmission?.state === "FINALIZATION_PENDING";
  const priorSubmissionView = useRef<{
    identity: string; state: NonNullable<ZeroTouchCaseSummary["target_submission"]>["state"] | undefined;
    unknown: boolean; continuation: boolean;
  } | null>(null);
  const targetSubmissionId = targetSubmission?.submission_id ?? null;
  const targetStatusIdentity = `${evidenceIdentity}:${targetSubmissionId ?? "none"}`;
  const completedVerification = targetSubmission?.state === "SUBMISSION_CONFIRMED";
  const targetCheckKind = completedVerification ? "completed-target-verification" : "target-status-check";
  const canCheckTargetStatus = (
    (targetSubmission?.state === "SUBMISSION_OUTCOME_UNCERTAIN" && targetSubmission.status_check_available)
    || (completedVerification && targetSubmission?.verification_available === true)
  )
    && targetSubmissionId !== null
    && actor.capabilities.includes("CASE_ACCESS")
    && !caseUnavailable && !mutationBlocked && !detailQuery.isError;
  const generation = useRef(0);
  const mounted = useRef(false);
  const mutationPending = useRef<CaseActionIdentity | null>(null);
  const reviewEdit = useRef<(CaseActionIdentity & { target: EvidenceFocusTarget }) | null>(null);
  const [classificationReviewRequest, setClassificationReviewRequest] = useState<CaseActionIdentity | null>(null);
  const focusIntent = useRef(0);
  const focusFrames = useRef(new Set<number>());
  const [pendingReviewReturn, setPendingReviewReturn] = useState<(CaseActionIdentity & { version: number; focusIntent: number }) | null>(null);

  function cancelPendingFocus(): void {
    focusIntent.current += 1;
    focusFrames.current.forEach((frame) => cancelAnimationFrame(frame));
    focusFrames.current.clear();
  }

  function scheduleFocusFrame(callback: FrameRequestCallback): void {
    const frame = requestAnimationFrame((timestamp) => {
      focusFrames.current.delete(frame);
      callback(timestamp);
    });
    focusFrames.current.add(frame);
  }

  function recordOwnershipInteraction(event: { target: EventTarget | null }): void {
    const stage = document.getElementById(EVIDENCE_TARGET_IDS.ownership)?.closest(".stage-disclosure");
    if (event.target instanceof Node && stage?.contains(event.target)) cancelPendingFocus();
  }
  const lastNavigationFocus = useRef<string | null>(null);
  const activeIdentity = useRef({ caseId, actorUserId: actor.user_id });
  activeIdentity.current = { caseId, actorUserId: actor.user_id };

  function captureCaseAction(): CaseActionIdentity {
    return { generation: generation.current, caseId, actorUserId: actor.user_id };
  }

  function isCurrentCaseAction(action: CaseActionIdentity): boolean {
    return mounted.current
      && generation.current === action.generation
      && activeIdentity.current.caseId === action.caseId
      && activeIdentity.current.actorUserId === action.actorUserId;
  }

  const refreshEvidence = useCallback(async (action: CaseActionIdentity) => {
    await Promise.all([
      queryClient.cancelQueries({
        queryKey: caseDetailQueryOptions(action.actorUserId, action.caseId).queryKey,
        exact: true,
      }),
      queryClient.cancelQueries({
        queryKey: documentQueryOptions(action.actorUserId, action.caseId).queryKey,
        exact: true,
      }),
      queryClient.cancelQueries({
        queryKey: ownershipQueryOptions(action.actorUserId, action.caseId).queryKey,
        exact: true,
      }),
      queryClient.cancelQueries({
        queryKey: intelligenceQueryOptions(action.actorUserId, action.caseId).queryKey,
        exact: true,
      }),
    ]);
    if (!isCurrentCaseAction(action)) {
      throw new Error("Case evidence refresh is no longer current.");
    }
    const latestCase = fetchZeroTouchCase(action.caseId).then((latest) => {
      if (isCurrentCaseAction(action)) {
        publishCaseDetail(queryClient, action.actorUserId, latest);
      }
      return latest;
    });
    const latestDocuments = queryClient.fetchQuery({
      ...documentQueryOptions(action.actorUserId, action.caseId),
      staleTime: 0,
      retry: false,
    }).then((documents) => {
      if (isCurrentCaseAction(action)) {
        if (import.meta.env.VITE_E2E_DIAGNOSTICS === "1") {
          const reviewedFieldCount = documents
            .find((document) => document.superseded_by_document_id === null)
            ?.fields.filter((field) => field.review_status !== "PENDING").length ?? 0;
          console.info("E2E_DIAG", JSON.stringify({
            milestone: "REVIEW_QUERY_DATA_PUBLISHED",
            case_id: action.caseId,
            reviewed_field_count: reviewedFieldCount,
            monotonic_ms: Math.round(performance.now()),
          }));
        }
      }
      return documents;
    });
    const latestOwnership = fetchOwnership(action.caseId).then((ownership) => {
      if (isCurrentCaseAction(action)) {
        queryClient.setQueryData(
          ownershipQueryOptions(action.actorUserId, action.caseId).queryKey,
          (current: unknown) => retainNewestVersionedEvidence(current, ownership),
        );
      }
      return ownership;
    });
    const latestIntelligence = fetchIntelligence(action.caseId).then((record) => {
      if (isCurrentCaseAction(action)) {
        queryClient.setQueryData(
          intelligenceQueryOptions(action.actorUserId, action.caseId).queryKey,
          (current: unknown) => retainNewestVersionedEvidence(current, record),
        );
      }
      return record;
    });
    const [latest] = await Promise.all([
      latestCase,
      latestDocuments,
      latestOwnership,
      latestIntelligence,
    ]);
    return latest;
  }, [queryClient]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      cancelPendingFocus();
      generation.current += 1;
      targetStatusController.current?.abort();
      submissionObservationController.current?.abort();
    };
  }, []);

  useEffect(() => {
    generation.current += 1;
    const current = generation.current;
    setError(null);
    setIsBusy(false);
    setBusyLabel(null);
    setMutationBlocked(false);
    setCaseUnavailable(false);
    setDeleteDialogOpen(null);
    setConfirmationUnknownIdentity(queryClient.getQueryData<boolean>([
      ...caseDetailQueryOptions(actor.user_id, caseId).queryKey, "confirmation-response-lost",
    ]) ? evidenceIdentity : null);
    mutationPending.current = null;
    return () => {
      generation.current = current + 1;
      cancelPendingFocus();
      targetStatusController.current?.abort();
      submissionObservationController.current?.abort();
    };
  }, [actor.user_id, caseId]);

  useEffect(() => {
    const current = {
      identity: evidenceIdentity, state: targetSubmission?.state,
      unknown: confirmationUnknown, continuation: safeContinuation,
    };
    const previous = priorSubmissionView.current;
    priorSubmissionView.current = current;
    // Initial load, navigation and ordinary evidence refresh keep the user's focus.
    if (!previous?.state || previous.identity !== current.identity) return;
    const stateChanged = previous.state !== current.state;
    const observed = previous.unknown && !current.unknown;
    const targetId = current.unknown && !previous.unknown ? "submission-observation-title"
      : current.state === "SUBMISSION_OUTCOME_UNCERTAIN" && (stateChanged || observed) ? "target-recovery-title"
      : current.continuation && (!previous.continuation || observed) ? "target-continuation-title"
      : (current.state === "SUBMISSION_CONFIRMED" || current.state === "SUBMISSION_FAILED")
        && (stateChanged || observed) ? "submission-state-title" : null;
    if (!targetId) return;
    const action = captureCaseAction();
    // Wait for disclosure layout effects before scrolling to the next action.
    const handoffFrame = requestAnimationFrame(() => {
      if (!isCurrentCaseAction(action)) return;
      const target = document.getElementById(targetId);
      if (!target) return;
      revealStage(target);
      target.focus({ preventScroll: true });
      target.scrollIntoView({ block: "center", behavior: "auto" });
    });
    return () => cancelAnimationFrame(handoffFrame);
  }, [evidenceIdentity, targetSubmission?.state, confirmationUnknown, safeContinuation]);

  const runTargetStatusCheck = useCallback(async (automatic: boolean) => {
    if (!canCheckTargetStatus || !targetSubmissionId || isBusy || mutationPending.current
      || targetStatusController.current) return;
    const action = captureCaseAction();
    const key = [
      ...caseDetailQueryOptions(action.actorUserId, action.caseId).queryKey,
      targetCheckKind, targetSubmissionId,
    ];
    if (automatic && queryClient.getQueryData<RetainedTargetStatusCheck>(key)?.attempted) return;
    const previous = queryClient.getQueryData<RetainedTargetStatusCheck>(key);
    const retained: RetainedTargetStatusCheck = {
      attempted: true, result: previous?.result ?? null, error: null,
    };
    // One automatic attempt per frozen submission in this session; logout clears the cache.
    queryClient.setQueryDefaults(key, { gcTime: Infinity, retry: false });
    queryClient.setQueryData(key, retained);
    const controller = new AbortController();
    targetStatusController.current = controller;
    setTargetStatusCheck({ ...retained, identity: targetStatusIdentity, checking: true });
    try {
      const result = completedVerification
        ? await verifyCompletedGoldTier(action.caseId, targetSubmissionId, controller.signal)
        : await checkZeroTouchTargetStatus(action.caseId, targetSubmissionId, controller.signal);
      if (controller.signal.aborted || !isCurrentCaseAction(action)) return;
      const next: RetainedTargetStatusCheck = result.submission_id === targetSubmissionId
        ? { attempted: true, result, error: null }
        : { attempted: true, result: null, error: "The check did not match this retained submission." };
      queryClient.setQueryData(key, next);
      setTargetStatusCheck({ ...next, identity: targetStatusIdentity, checking: false });
    } catch (checkError) {
      if (controller.signal.aborted || !isCurrentCaseAction(action)) return;
      if (checkError instanceof ApiError && [401, 403, 404].includes(checkError.status)) {
        queryClient.removeQueries({ queryKey: key, exact: true });
        setMutationBlocked(true);
        if (checkError.status === 404) setCaseUnavailable(true);
      }
      const next: RetainedTargetStatusCheck = {
        attempted: true, result: previous?.result ?? null,
        error: completedVerification
          ? "GoldTier verification is unavailable. The confirmed submission remains retained."
          : "GoldTier status could not be checked. The retained submission outcome remains uncertain.",
      };
      if (!(checkError instanceof ApiError && [401, 403, 404].includes(checkError.status))) {
        queryClient.setQueryData(key, next);
      }
      setTargetStatusCheck({ ...next, identity: targetStatusIdentity, checking: false });
    } finally {
      if (targetStatusController.current === controller) targetStatusController.current = null;
    }
  }, [actor.user_id, caseId, queryClient, canCheckTargetStatus, targetSubmissionId, targetStatusIdentity, targetCheckKind, completedVerification, isBusy]);

  useEffect(() => {
    const key = [
      ...caseDetailQueryOptions(actor.user_id, caseId).queryKey,
      targetCheckKind, targetSubmissionId,
    ];
    const retained = targetSubmissionId
      ? queryClient.getQueryData<RetainedTargetStatusCheck>(key) : undefined;
    setTargetStatusCheck(retained ? { ...retained, identity: targetStatusIdentity, checking: false } : null);
    return () => {
      targetStatusController.current?.abort();
      targetStatusController.current = null;
    };
  }, [actor.user_id, caseId, queryClient, targetSubmissionId, targetStatusIdentity, targetCheckKind, targetSubmission?.state, canCheckTargetStatus]);

  useEffect(() => {
    if (canCheckTargetStatus && !completedVerification) void runTargetStatusCheck(true);
  }, [canCheckTargetStatus, completedVerification, runTargetStatusCheck]);

  useEffect(() => {
    if (!summary || summary.document_refresh_recovery || !shouldPollAutomation(summary.status)) return;
    const activeGeneration = generation.current;
    return startAutomationPolling({
      caseId,
      generation: activeGeneration,
      currentGeneration: () => generation.current,
      fetchCase: fetchZeroTouchCase,
      onUpdate: (latest) => {
        caseSummaryMutationEffect(queryClient, actor.user_id, latest);
        // Each existing query owns cancellation, newest-evidence retention and visible
        // failure/recovery. A failed read cannot suppress its successful sibling.
        void Promise.allSettled([
          queryClient.fetchQuery({
            ...documentQueryOptions(actor.user_id, caseId), staleTime: 0, retry: false,
          }),
          queryClient.fetchQuery({
            ...ownershipQueryOptions(actor.user_id, caseId), staleTime: 0, retry: false,
          }),
        ]);
      },
      onWarning: (warning) => setError(warning),
      shouldContinue: shouldPollAutomation,
    });
  }, [actor.user_id, caseId, queryClient, summary?.status, summary?.version, summary?.document_refresh_recovery]);

  useEffect(() => {
    if (!summary) return;
    const requestedNodeId = initialFocusNodeId;
    if (!requestedNodeId) return;
    const focusIdentity = `${evidenceIdentity}:${requestedNodeId}`;
    if (lastNavigationFocus.current === focusIdentity) return;
    const node = findBusinessStage(summary.processing_pipeline ?? [], requestedNodeId);
    if (!node || (!processingNodeFocusTarget(node)
      && !(summary.status === "PENDING_INPUTS" && node.node_id === "DOCUMENT_IDP"))) return;
    if (["DOCUMENT_IDP", "RECONCILIATION"].includes(node.node_id) && documentQuery.isPending) return;
    if (node.node_id === "OWNERSHIP_UBO" && ownershipQuery.isPending) return;
    lastNavigationFocus.current = focusIdentity;
    focusProcessingNode(node);
  }, [evidenceIdentity, initialFocusNodeId, summary?.version, documentQuery.isPending, ownershipQuery.isPending]);

  useEffect(() => {
    if (!pendingProcessingFocus) return;
    if (!isCurrentCaseAction(pendingProcessingFocus) || summary?.version !== pendingProcessingFocus.automationVersion) {
      setPendingProcessingFocus(null);
      return;
    }
    if ((["DOCUMENT_IDP", "RECONCILIATION"].includes(pendingProcessingFocus.nodeId) && documentQuery.isPending)
      || (pendingProcessingFocus.nodeId === "OWNERSHIP_UBO" && ownershipQuery.isPending)) return;
    const node = findProcessingNode(summary.processing_pipeline ?? [], pendingProcessingFocus.nodeId);
    setPendingProcessingFocus(null);
    if (node) focusProcessingNode(node);
  }, [pendingProcessingFocus, evidenceIdentity, summary?.version, documentQuery.isPending, ownershipQuery.isPending]);

  async function runMutation(
    operation: () => Promise<ZeroTouchCaseSummary>,
    label = "Saving case action…",
    effect: "supporting" | "target-confirmation" | "identity-recheck" | "registry-identity" | "manual-ownership" | "policy-rebind" = "supporting",
  ) {
    let action = captureCaseAction();
    const returnToReview = reviewEdit.current !== null && isCurrentCaseAction(reviewEdit.current);
    const returnFocusIntent = focusIntent.current;
    if (mutationPending.current || mutationBlocked || confirmationUnknown) return;
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel(label);
    setError(null);
    try {
      const updated = await operation();
      if (!isCurrentCaseAction(action)) return;
      if (effect === "target-confirmation") {
        targetConfirmationMutationEffect(queryClient, action.actorUserId, updated);
      } else if (effect === "registry-identity") {
        // Retire direct refresh/poll continuations captured under the prior identity.
        action = { ...action, generation: ++generation.current };
        mutationPending.current = action;
        await caseSupportingMutationEffect(queryClient, action.actorUserId, updated, true);
      } else if (effect === "identity-recheck") {
        identitySearchRecheckMutationEffect(queryClient, action.actorUserId, updated);
      } else if (effect === "manual-ownership") {
        await manualOwnershipMutationEffect(queryClient, action.actorUserId, updated);
      } else if (effect === "policy-rebind") {
        policyRebindMutationEffect(queryClient, action.actorUserId, updated);
      } else {
        await caseSupportingMutationEffect(queryClient, action.actorUserId, updated);
      }
      if (returnToReview && isCurrentCaseAction(action)) {
        reviewEdit.current = null;
        setClassificationReviewRequest(null);
        setPendingReviewReturn({ ...action, version: updated.version, focusIntent: returnFocusIntent });
      }
    } catch (mutationError) {
      if (!isCurrentCaseAction(action)) return;
      if (effect === "target-confirmation" && confirmationResponseMayBeLost(mutationError)) {
        await verifySubmissionResponse(action);
        return;
      }
      if (shouldRefreshAfterMutationError(mutationError)) {
        await refreshEvidence(action).catch(() => undefined);
      }
      if (!isCurrentCaseAction(action)) return;
      setError(mutationError instanceof Error ? mutationError.message : "The case action failed.");
    } finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) {
        setIsBusy(false);
        setBusyLabel(null);
      }
    }
  }

  async function verifySubmissionResponse(action: CaseActionIdentity): Promise<void> {
    const key = [...caseDetailQueryOptions(action.actorUserId, action.caseId).queryKey, "confirmation-response-lost"];
    queryClient.setQueryData(key, true);
    setConfirmationUnknownIdentity(`${action.actorUserId}:${action.caseId}`);
    setBusyLabel("Verifying submission outcome…");
    const controller = new AbortController();
    submissionObservationController.current?.abort();
    submissionObservationController.current = controller;
    try {
      const observed = await observeSubmissionOutcome({
        caseId: action.caseId, signal: controller.signal,
        isCurrent: () => isCurrentCaseAction(action),
        onUpdate: (latest) => caseSummaryMutationEffect(queryClient, action.actorUserId, latest),
      });
      if (controller.signal.aborted || !isCurrentCaseAction(action)) return;
      if (observed) {
        queryClient.removeQueries({ queryKey: key, exact: true });
        setConfirmationUnknownIdentity(null);
        setError(null);
      } else {
        setError("The submission response was lost. Its outcome is still being verified. Do not send another confirmation; use Verify submission outcome to read the retained state again.");
      }
    } catch (observationError) {
      if (controller.signal.aborted || !isCurrentCaseAction(action)) return;
      if (observationError instanceof ApiError && [401, 403, 404].includes(observationError.status)) {
        setMutationBlocked(true);
        if (observationError.status === 404) setCaseUnavailable(true);
      }
      setError("The submission outcome could not be observed safely. Refresh your authorized session and check this case; no confirmation was repeated.");
    } finally {
      if (submissionObservationController.current === controller) submissionObservationController.current = null;
    }
  }

  async function verifySubmissionAgain() {
    if (isBusy || mutationPending.current || mutationBlocked) return;
    const action = captureCaseAction();
    mutationPending.current = action;
    setIsBusy(true);
    try { await verifySubmissionResponse(action); }
    finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) { setIsBusy(false); setBusyLabel(null); }
    }
  }

  function recoverTarget(input: TargetRecoveryInput) {
    if (input.expected_submission_id !== targetSubmissionId) return;
    const action = captureCaseAction();
    void runMutation(async () => {
      await recoverZeroTouchTarget(caseId, input);
      if (!isCurrentCaseAction(action)) throw new DOMException("Action superseded", "AbortError");
      return fetchZeroTouchCase(caseId);
    }, "Recording verified GoldTier recovery…");
  }

  async function runPriorityMutation(priority: number | null): Promise<void> {
    const action = captureCaseAction();
    if (mutationPending.current || mutationBlocked) return;
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel("Saving case priority…");
    setError(null);
    try {
      await updateCasePriority(action.caseId, priority);
      if (!isCurrentCaseAction(action)) return;
      await refreshEvidence(action);
      if (!isCurrentCaseAction(action)) return;
      await priorityMutationEffect(queryClient, action.actorUserId);
    } catch (priorityError) {
      if (!isCurrentCaseAction(action)) return;
      setError(priorityError instanceof Error ? priorityError.message : "Priority could not be updated.");
      throw priorityError;
    } finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) {
        setIsBusy(false);
        setBusyLabel(null);
      }
    }
  }

  async function settleEvidenceMutation(
    operation: () => Promise<unknown>,
    label: string,
    failureText: string,
  ): Promise<void> {
    const action = captureCaseAction();
    const returnToReview = reviewEdit.current !== null && isCurrentCaseAction(reviewEdit.current);
    const returnFocusIntent = focusIntent.current;
    if (mutationPending.current || mutationBlocked) return;
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel(label);
    setError(null);
    let mutationError: unknown = null;
    try {
      await operation();
    } catch (caught) {
      mutationError = caught;
    }
    if (!isCurrentCaseAction(action)) {
      if (mutationPending.current === action) mutationPending.current = null;
      return;
    }
    const mustRefresh = mutationError === null || shouldRefreshAfterMutationError(mutationError);
    if (mustRefresh) {
      try {
        const latest = await refreshEvidence(action);
        if (!isCurrentCaseAction(action)) return;
        setMutationBlocked(false);
        if (mutationError === null && returnToReview) {
          reviewEdit.current = null;
          setClassificationReviewRequest(null);
          setPendingReviewReturn({ ...action, version: latest.version, focusIntent: returnFocusIntent });
        }
        if (mutationError !== null) {
          setError(
            mutationError instanceof ApiError && mutationError.status === 409
              ? "The evidence changed before this action. Current case evidence was reloaded."
              : "The outcome could not be confirmed. Current case evidence was reloaded; check the field status before trying another action.",
          );
        }
      } catch (refreshError) {
        if (!isCurrentCaseAction(action)) return;
        if (refreshError instanceof ApiError && refreshError.status === 404) {
          setCaseUnavailable(true);
          setError(null);
        } else {
          setMutationBlocked(true);
          setError("The outcome and evidence reload could not be confirmed. Last-confirmed information is shown; refresh case evidence before another mutation.");
        }
      }
    } else if (mutationError !== null) {
      if (mutationError instanceof ApiError && mutationError.status === 404) {
        setCaseUnavailable(true);
        setError(null);
      } else {
        setError(mutationError instanceof Error ? mutationError.message : failureText);
      }
    }
    if (mutationPending.current === action) mutationPending.current = null;
    if (isCurrentCaseAction(action)) {
      setIsBusy(false);
      setBusyLabel(null);
    }
  }

  function handleDocumentReview(
    document: DocumentProcessingRecord,
    request: DocumentReviewRequest,
    repair: boolean,
  ) {
    const label = request.fieldKey.replaceAll("_", " ");
    void settleEvidenceMutation(
      () => reviewDocument(
        caseId,
        document.document_id,
        request.fieldKey,
        request.decision,
        request.correctedValue,
        request.note,
      ),
      repair ? `Retrying saved ${label} checkpoint…` : `Saving ${label} decision…`,
      "The document review could not be saved.",
    );
  }

  function handleReplacement(document: DocumentProcessingRecord, file: File) {
    void settleEvidenceMutation(
      () => replaceZeroTouchDocument(caseId, document.document_id, document.events.length, file, summary ?? undefined),
      "Replacing current document…",
      "The replacement could not be saved.",
    );
  }

  function handleRetry(document: DocumentProcessingRecord, file: File) {
    void settleEvidenceMutation(
      () => retryZeroTouchIntakeDocument(caseId, document.document_id, file, false),
      "Retrying affected document…",
      "The document retry failed.",
    );
  }

  function handleContinueRecoveredIntake() {
    void settleEvidenceMutation(
      () => resumeZeroTouchCase(caseId),
      "Continuing recovered intake…",
      "Recovered intake could not continue.",
    );
  }

  function handleCompleteInitialIntake(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const expectedCount = Number(new FormData(event.currentTarget).get("expectedDocumentCount"));
    if (!Number.isInteger(expectedCount) || expectedCount < 1 || expectedCount > 20) return;
    void settleEvidenceMutation(
      () => completeZeroTouchIntake(caseId, expectedCount, false),
      "Completing document intake…",
      "Document intake could not complete. Check the intended count and uploaded documents.",
    );
  }

  function handleRecoverDocumentRefresh() {
    if (!summary?.document_refresh_recovery?.can_resume) return;
    void settleEvidenceMutation(
      () => resumeZeroTouchCase(caseId, summary),
      "Refreshing retained replacement evidence…",
      "The replacement is retained. Reload current evidence before retrying recovery.",
    );
  }

  async function handleReadOnlyRefresh() {
    const action = captureCaseAction();
    if (mutationPending.current) return;
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel("Refreshing case evidence…");
    try {
      await refreshEvidence(action);
      if (!isCurrentCaseAction(action)) return;
      setMutationBlocked(false);
      setError(null);
    } catch (refreshError) {
      if (!isCurrentCaseAction(action)) return;
      if (refreshError instanceof ApiError && refreshError.status === 404) {
        setCaseUnavailable(true);
        setError(null);
      } else {
        setError("Case evidence could not be refreshed. Last-confirmed information is still shown.");
      }
    } finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) {
        setIsBusy(false);
        setBusyLabel(null);
      }
    }
  }

  function focusActionControl(targetId: string, selector?: string): void {
    cancelPendingFocus();
    const intent = focusIntent.current;
    const action = captureCaseAction();
    const version = summary?.version;
    const currentFocus = () => isCurrentCaseAction(action) && focusVersion.current === version
      && focusIntent.current === intent;
    const section = document.getElementById(targetId);
    if (!section) {
      setEvidenceFocusNotice({ identity: evidenceIdentity, message: "The required action is not available for the current case evidence." });
      return;
    }
    revealStage(section);
    if (targetId === EVIDENCE_TARGET_IDS.identity && !section.querySelector("#identity-registration-number")) {
      const edit = Array.from(section.querySelectorAll<HTMLButtonElement>("button:not([disabled])"))
        .find(button => ["Edit UEN", "Enter another UEN"].includes(button.textContent ?? ""));
      edit?.click();
    }
    scheduleFocusFrame(() => {
      if (!currentFocus()) return;
      const current = document.getElementById(targetId);
      if (!current) return;
      // Entry navigation may run before the disclosure's effect has subscribed.
      // Reveal again at the mounted frame, then focus after its committed layout.
      revealStage(current);
      const controls = selector ?? "input:not([disabled]):not([readonly]):not([type=hidden]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]):not([data-stage-toggle]):not(.review-and-send__print)";
      const target = (current.matches(controls) ? [current] : Array.from(current.querySelectorAll<HTMLElement>(controls)))
        .find(element => !element.matches(":disabled"));
      if (!target) {
        setEvidenceFocusNotice({ identity: evidenceIdentity, message: "No corrective input is currently authorized here. Review the retained reason and required evidence." });
        current.tabIndex = -1;
        current.focus({ preventScroll: true });
        current.scrollIntoView?.({ block: "center", behavior: "auto" });
        return;
      }
      revealStage(target);
      scheduleFocusFrame(() => {
        if (!currentFocus() || !target.isConnected || target.matches(":disabled")) return;
        if (target.closest("[hidden]")) {
          setEvidenceFocusNotice({ identity: evidenceIdentity, message: "The corrective input could not be opened for the current case evidence." });
          return;
        }
        setEvidenceFocusNotice(null);
        target.focus({ preventScroll: true });
        const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
        target.scrollIntoView?.({ block: "center", behavior: reducedMotion ? "auto" : "smooth" });
      });
    });
  }

  function focusEvidence(target: EvidenceFocusTarget): void {
    // Explicit evidence navigation also supersedes an older automatic return.
    cancelPendingFocus();
    if (target === "identity") { focusActionControl(EVIDENCE_TARGET_IDS.identity, "#identity-registration-number:not([disabled])"); return; }
    if (target === "classification") {
      const onlySegmentMissing = summary?.target_classification?.kyc_customer_type.selected_value
        && !summary?.target_classification?.client_segment.selected_value;
      focusActionControl(EVIDENCE_TARGET_IDS.classification, onlySegmentMissing
        ? 'select[aria-label="Client segment"]:not([disabled])' : "select:not([disabled])");
      return;
    }
    if (target === "policy") { focusActionControl(EVIDENCE_TARGET_IDS.policy, "#policy-rebind-rationale:not([disabled])"); return; }
    if (target === "documents" || target === "reconciliation") {
      const failed = documents.find(doc => isDocumentReuploadRequired(doc, summary ?? undefined));
      if (failed) { focusActionControl(EVIDENCE_TARGET_IDS.documents, `.document-card[data-document-id="${failed.document_id}"] input[type=file]:not([disabled])`); return; }
      if (document.getElementById("case-document-intake-continue")) { focusActionControl("case-document-intake-continue", "button:not([disabled])"); return; }
      if (document.getElementById("case-document-intake-start")) { focusActionControl("case-document-intake-start", "button:not([disabled])"); return; }
      if (document.getElementById("case-blocker-review")) { focusActionControl("case-blocker-review", "input[data-review-field]:not([disabled]), input[data-reconciliation-field]:not([disabled])"); return; }
      if (document.getElementById("case-document-checkpoint-repair")) { focusActionControl("case-document-checkpoint-repair", "button:not([disabled])"); return; }
      focusActionControl(document.getElementById("case-document-upload") ? "case-document-upload" : EVIDENCE_TARGET_IDS.documents, "input[type=file]:not([disabled])"); return;
    }
    if (target === "ownership" && document.getElementById(MANUAL_OWNERSHIP_TARGET_ID)) { focusManualOwnership(); return; }
    if (target === "recovery" && document.getElementById("case-target-recovery")) { focusActionControl("case-target-recovery"); return; }
    const section = document.getElementById(EVIDENCE_TARGET_IDS[target]);
    if (!section) {
      setEvidenceFocusNotice({
        identity: evidenceIdentity,
        message: `${target.replaceAll("_", " ")} evidence is not available for this case.`,
      });
      return;
    }
    setEvidenceFocusNotice(null);
    revealStage(section);
    section.focus({ preventScroll: true });
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    section.scrollIntoView?.({ block: "start", behavior: reducedMotion ? "auto" : "smooth" });
  }

  useEffect(() => {
    if (!pendingAttention) return;
    if (!isCurrentCaseAction(pendingAttention) || summary?.version !== pendingAttention.version) {
      setPendingAttention(null); return;
    }
    if (documentQuery.isPending || ownershipQuery.isPending) return;
    setPendingAttention(null);
    requestAnimationFrame(() => {
      if (isCurrentCaseAction(pendingAttention) && focusVersion.current === pendingAttention.version) {
        focusAttention(pendingAttention.destination);
      }
    });
  }, [pendingAttention, evidenceIdentity, summary?.version, documentQuery.isPending, ownershipQuery.isPending]);

  function focusSearch(interventionId?: string, fromPipeline = false): void {
    const searchPanel = document.getElementById(SEARCH_TARGET_ID)?.querySelector(".stage-disclosure > div");
    if (searchPanel) revealStage(searchPanel);
    if (document.getElementById("existing-customer-confirmation-form")) {
      focusActionControl("existing-customer-confirmation-form", "input:not([disabled])"); return;
    }
    const intervention = summary?.interventions?.find(item => item.owning_stage === "GOLDTIER_SEARCH"
      && (!interventionId || item.intervention_id === interventionId));
    if (intervention?.evidence_actions?.some(action => action.target === "IDENTITY")
      || identitySearchRecheck) { focusEvidence("identity"); return; }
    if (intervention && document.getElementById(`case-intervention-${intervention.intervention_id}`)) {
      focusActionControl(`case-intervention-${intervention.intervention_id}`); return;
    }
    if (fromPipeline && document.getElementById(EVIDENCE_TARGET_IDS.identity)) {
      focusEvidence("identity"); return;
    }
    focusActionControl(document.getElementById("case-search-diagnostic") ? "case-search-diagnostic" : SEARCH_TARGET_ID);
  }

  function focusAttention(destination: AttentionDestination): void {
    if (summary && (documentQuery.isPending || ownershipQuery.isPending)) {
      setPendingAttention({ ...captureCaseAction(), version: summary.version, destination }); return;
    }
    if (destination.kind === "final") { focusActionControl("case-review-and-send", ".btn-primary:not([disabled])"); return; }
    if (destination.kind === "intervention") { focusActionControl(`case-intervention-${destination.interventionId}`); return; }
    if (destination.kind === "technical") {
      if (document.getElementById("case-target-recovery")) { focusActionControl("case-target-recovery"); return; }
      const diagnostic = document.getElementById("case-search-diagnostic") ? "case-search-diagnostic"
        : document.getElementById("case-target-blocker") ? "case-target-blocker" : EVIDENCE_TARGET_IDS.recovery;
      focusActionControl(diagnostic); return;
    }
    if (destination.kind === "evidence") {
      const targets = { DOCUMENTS: "documents", CLASSIFICATION: "classification", IDENTITY: "identity" } as const;
      if (destination.target in targets) { focusEvidence(targets[destination.target as keyof typeof targets]); return; }
      if (destination.target === "REVIEW_SEND") { focusActionControl("case-review-and-send", ".btn-primary:not([disabled])"); return; }
      focusActionControl(destination.target === "OWNERSHIP_UPLOAD" ? "case-ownership-evidence-upload" : MANUAL_OWNERSHIP_TARGET_ID,
        destination.target === "OWNERSHIP_UPLOAD" ? "input[type=file]:not([disabled])" : undefined); return;
    }
    const exception = destination.exception;
    if (exception.stage === "DOCUMENT") {
      if (identityConflict && exception.evidence.some(item => item.field_key === "registration_identifier" || item.field_key === "registration_number")) { focusEvidence("identity"); return; }
      // Change the visible decision group only. No draft choice or business mutation.
      const discrepancy = summary?.reconciliation?.discrepancies.find(item => item.discrepancy_id === exception.exception_id);
      const field = exception.evidence.find(item => item.reference_id && item.field_key);
      const documentId = exception.evidence.find(item => documents.some(doc => doc.document_id === item.reference_id && !doc.superseded_by_document_id))?.reference_id
        ?? discrepancy?.observations.find(item => item.document_id && documents.some(doc => doc.document_id === item.document_id && !doc.superseded_by_document_id))?.document_id;
      const escaped = (value: string) => value.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      if (discrepancy?.allowed_actions.length) {
        batchReviewRef.current?.openDecision({ discrepancyId: discrepancy.discrepancy_id });
        focusActionControl("case-blocker-review", `input[data-discrepancy-id="${escaped(discrepancy.discrepancy_id)}"]:not([disabled])`); return;
      }
      if (field && batchReviewRef.current?.openDecision({ documentId: field.reference_id!, fieldKey: field.field_key! })) {
        focusActionControl("case-blocker-review", `input[data-document-id="${escaped(field.reference_id!)}"][data-review-field="${escaped(field.field_key!)}"]:not([disabled])`); return;
      }
      if (documentId) {
        focusActionControl(EVIDENCE_TARGET_IDS.documents, `.document-card[data-document-id="${escaped(documentId)}"] input[type=file]:not([disabled])`); return;
      }
      focusEvidence("documents"); return;
    }
    if (exception.stage === "REGISTRY") { focusEvidence("identity"); return; }
    if (exception.stage === "OWNERSHIP") {
      if (document.getElementById(MANUAL_OWNERSHIP_TARGET_ID)) { focusEvidence("ownership"); return; }
      focusActionControl(`case-intervention-${exception.exception_id}`); return;
    }
    if (exception.blocker_code === "GOLDTIER_CLASSIFICATION_REQUIRED") { focusEvidence("classification"); return; }
    if (exception.stage === "GOLDTIER_SEARCH") {
      focusSearch(exception.exception_id); return;
    }
    if (exception.stage === "READINESS" && summary?.case.policy_rebind?.configuration_status === "REQUIRES_REBIND") { focusEvidence("policy"); return; }
    if (document.getElementById(`case-intervention-${exception.exception_id}`)) { focusActionControl(`case-intervention-${exception.exception_id}`); return; }
    focusEvidence("recovery");
    setEvidenceFocusNotice({ identity: evidenceIdentity, message: "No corrective input is currently authorized here. Review the retained reason and required evidence." });
  }

  function editFromFinalReview(target: EvidenceFocusTarget): void {
    reviewEdit.current = { ...captureCaseAction(), target };
    if (target === "classification") setClassificationReviewRequest(captureCaseAction());
    focusEvidence(target);
  }

  useEffect(() => {
    if (!pendingReviewReturn) return;
    if (!isCurrentCaseAction(pendingReviewReturn) || focusIntent.current !== pendingReviewReturn.focusIntent) {
      setPendingReviewReturn(null); return;
    }
    if (isBusy || documentQuery.isPending || ownershipQuery.isPending || !summary
      || summary.version < pendingReviewReturn.version) return;
    setPendingReviewReturn(null);
    const latest = summary;
    scheduleFocusFrame(() => {
      if (!isCurrentCaseAction(pendingReviewReturn) || focusIntent.current !== pendingReviewReturn.focusIntent) return;
      if (latest.active_exceptions.some(item => item.exception_type === "TARGET_CONFIRMATION_REQUIRED")) {
        focusActionControl("case-review-and-send", ".btn-primary:not([disabled])");
      } else {
        const node = latest.processing_pipeline?.find(item => item.status === "BLOCKED");
        if (node) focusProcessingNode(node);
      }
    });
  }, [pendingReviewReturn, summary?.version, isBusy, documentQuery.isPending, ownershipQuery.isPending, evidenceIdentity]);

  function focusManualOwnership(): void {
    focusActionControl(MANUAL_OWNERSHIP_TARGET_ID);
  }

  /** The specific authorized readiness control to focus, if one is currently available. */
  function readinessAction(): (() => void) | null {
    if (document.querySelector("#policy-rebind-rationale:not([disabled])")) return () => focusEvidence("policy");
    if (summary?.active_exceptions.some(item => item.blocker_code === "GOLDTIER_CLASSIFICATION_REQUIRED")) return () => focusEvidence("classification");
    if (document.querySelector("#case-review-and-send .btn-primary:not([disabled])")) return () => focusActionControl("case-review-and-send", ".btn-primary:not([disabled])");
    return null;
  }

  function focusProcessingNode(node: ProcessingNode): void {
    if (node.node_id === GOLDTIER_DETAILS_STEP_ID && summary) {
      // One readiness or package stage needing the user routes to its own content; when both do, the one
      // with a specific authorized control wins, else the section opens at its status overview.
      const members = businessStageMembers(summary.processing_pipeline ?? [], node);
      const attention = members.filter(item => ["REVIEW_REQUIRED", "BLOCKED", "FAILED"].includes(item.status));
      const member = attention.length === 1 ? attention[0]
        : attention.length > 1 ? attention.find(item => (item.node_id === "READINESS"
          ? readinessAction() !== null : document.getElementById("case-target-recovery") !== null))
        : members.find(item => item.status === "IN_PROGRESS");
      if (member) { focusProcessingNode(member); return; }
    }
    if (["DOCUMENT_IDP", "RECONCILIATION"].includes(node.node_id) && identityConflict) { focusEvidence("identity"); return; }
    if (summary && ((["DOCUMENT_IDP", "RECONCILIATION"].includes(node.node_id) && documentQuery.isPending)
      || (node.node_id === "OWNERSHIP_UBO" && ownershipQuery.isPending))) {
      setPendingProcessingFocus({ ...captureCaseAction(), nodeId: node.node_id, automationVersion: summary.version });
      return;
    }
    const readinessControl = node.node_id === "READINESS" ? readinessAction() : null;
    if (readinessControl) { readinessControl(); return; }
    if (node.node_id === "INITIAL_IDENTITY") { focusEvidence("identity"); return; }
    if (node.node_id.startsWith("ACRA_")) { focusEvidence(identityInSearch ? "registry" : "identity"); return; }
    if (["DOCUMENT_IDP", "RECONCILIATION"].includes(node.node_id)) { focusEvidence(node.node_id === "RECONCILIATION" ? "reconciliation" : "documents"); return; }
    if (node.node_id === "OWNERSHIP_UBO") { focusEvidence("ownership"); return; }
    if (node.node_id === "FINAL_REVIEW_SEND") { focusActionControl("case-review-and-send", ".btn-primary:not([disabled])"); return; }
    if (node.node_id.startsWith("TARGET_CLASSIFICATION")) { focusEvidence(processingNodeFocusTarget(node) === EVIDENCE_TARGET_IDS.policy ? "policy" : "classification"); return; }
    if (node.node_id.startsWith("GOLDTIER_SEARCH")) {
      focusSearch(undefined, true); return;
    }
    if (node.node_id.startsWith("GOLDTIER_") && document.getElementById("case-target-recovery")) { focusActionControl("case-target-recovery"); return; }
    // A settled readiness or GoldTier stage has no single action; open its own area of the section.
    const targetId = processingNodeFocusTarget(node)
      ?? (["READINESS", "GOLDTIER_TARGET"].includes(node.node_id) ? "case-target-blocker" : null);
    const section = targetId ? document.getElementById(targetId) : null;
    if (!section) {
      setEvidenceFocusNotice({
        identity: evidenceIdentity,
        message: `${node.label} details are not available for this case.`,
      });
      return;
    }
    setEvidenceFocusNotice(null);
    const action = captureCaseAction();
    requestAnimationFrame(() => {
      if (!isCurrentCaseAction(action)) return;
      const currentSection = document.getElementById(targetId!);
      if (!currentSection) return;
      revealStage(currentSection);
      requestAnimationFrame(() => {
        if (isCurrentCaseAction(action)) currentSection.focus({ preventScroll: true });
      });
      const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      currentSection.scrollIntoView?.({
        block: "start",
        behavior: reducedMotion ? "auto" : "smooth",
      });
    });
  }

  async function deleteCase(action: CaseActionIdentity): Promise<void> {
    if (!isCurrentCaseAction(action) || mutationPending.current || mutationBlocked) {
      throw new Error("Another case action is still pending.");
    }
    mutationPending.current = action;
    setIsBusy(true);
    setBusyLabel("Deleting case…");
    try {
      await deleteZeroTouchCase(action.caseId);
      if (!isCurrentCaseAction(action)) return;
      await caseDeletedEffect(queryClient, action.actorUserId, action.caseId);
      queryClient.removeQueries({
        queryKey: [...caseDetailQueryOptions(action.actorUserId, action.caseId).queryKey, "target-status-check"],
      });
      if (!isCurrentCaseAction(action)) return;
      setDeleteDialogOpen(null);
      onDeleted?.(action.caseId);
      onBack();
    } catch (deleteError) {
      if (isCurrentCaseAction(action)) throw deleteError;
    } finally {
      if (mutationPending.current === action) mutationPending.current = null;
      if (isCurrentCaseAction(action)) {
        setIsBusy(false);
        setBusyLabel(null);
      }
    }
  }

  // Read notices project the existing query owners; no local data retention or polling.
  function readNotice(label: "Ownership" | "Readiness" | "Target" | "Final review", pending: boolean, fetching: boolean, failed: boolean, retained: boolean) {
    const lower = label.toLowerCase();
    if (failed) return <p className="ds-banner ds-banner-warn" role="alert">{label} information could not be loaded. {retained ? `Last-confirmed ${lower} information remains visible and may be stale.` : "Current evidence is unavailable; absence has not been confirmed."}</p>;
    if (pending || fetching) return <p className="control-help" role="status">Loading {lower} information… {retained ? `Last-confirmed ${lower} information remains visible while it is refreshed.` : "Current evidence is not yet confirmed."}</p>;
    return null;
  }
  const ownershipReadUnconfirmed = ownershipQuery.isPending || ownershipQuery.isFetching || ownershipQuery.isError || detailQuery.isFetching || detailQuery.isError;
  const readinessReadUnconfirmed = detailQuery.isPending || detailQuery.isFetching || detailQuery.isError;
  const ownershipReadNotice = readNotice("Ownership", ownershipQuery.isPending, ownershipQuery.isFetching || detailQuery.isFetching, ownershipQuery.isError || detailQuery.isError, ownershipQuery.data !== undefined);
  const readinessReadNotice = readNotice("Readiness", detailQuery.isPending, detailQuery.isFetching, detailQuery.isError, detailQuery.data !== undefined);
  const finalReadNotice = readNotice("Final review", detailQuery.isPending, detailQuery.isFetching, detailQuery.isError, detailQuery.data !== undefined);
  const confirmedOwnershipEmpty = !ownershipReadUnconfirmed && ownership === null;
  const loadError = detailQuery.error ?? documentQuery.error ?? ownershipQuery.error;
  if (caseUnavailable) return <div className="ds-root ds-page"><button type="button" className="btn btn-ghost" onClick={onBack}>← Back to Cases</button><div className="ds-banner ds-banner-warn">The case is unavailable.</div></div>;
  if ((error || loadError) && !summary) return <div className="ds-root ds-page"><button type="button" className="btn btn-ghost" onClick={onBack}>← Back to Cases</button><div className="ds-banner ds-banner-warn">{error ?? (loadError instanceof Error ? loadError.message : "The case is unavailable.")}</div></div>;
  if (!summary) return <div className="ds-root ds-page"><p className="text-muted">Loading case…</p></div>;

  const entity = summary.case.entity;
  const acquisition = summary.case.registry_acquisition;
  const ownershipRecovery = summary.ownership_recovery;
  const registryCorrectionRequired = summary.active_exceptions.some(item => item.status === "OPEN"
    && item.stage === "REGISTRY" && item.blocker_code !== "INITIAL_IDENTITY_INCOMPLETE");
  const initialIdentityException = summary.active_exceptions.some(item => item.blocker_code === "INITIAL_IDENTITY_INCOMPLETE");
  const identityIncomplete = initialIdentityException
    || summary.interventions?.some(item => item.blocker_code === "INITIAL_IDENTITY_INCOMPLETE") === true;
  // An additional identity projection describes missing input, not Search-recheck eligibility.
  const identitySearchRecheck = !registryCorrectionRequired && (initialIdentityException || (identityIncomplete
    && (summary.case.error?.code === "INITIAL_IDENTITY_INCOMPLETE"
      || ["COMPLETED", "FAILED", "REVIEW_REQUIRED"].includes(summary.clm.target_search_checkpoint?.status ?? ""))));
  const identityEditable = summary.evidence_decision_authorized === true
    && summary.status !== "COMPLETED"
    && !summary.case.goldtier_result
    && !summary.case.target_dispatch_confirmation
    && !summary.clm.submission
    && !(targetSubmission && targetSubmission.state !== "NOT_SUBMITTED");
  const availableFocusTargets = new Set([
    EVIDENCE_TARGET_IDS.registry,
    EVIDENCE_TARGET_IDS.documents,
    EVIDENCE_TARGET_IDS.ownership,
    "case-search-diagnostic",
    "case-target-blocker",
    "case-review-and-send",
    ...(identityIncomplete || identityEditable ? [EVIDENCE_TARGET_IDS.identity] : []),
    ...(summary.reconciliation && summary.current_stage === "DOCUMENT"
      ? [EVIDENCE_TARGET_IDS.reconciliation]
      : []),
    ...(summary.target_classification ? ["case-target-classification"] : []),
    ...(summary.case.policy_rebind ? [EVIDENCE_TARGET_IDS.policy] : []),
  ]);

  const renderInterventions = (stages?: readonly string[], historyOnly = false, omit?: (item: HumanInterventionProjection) => boolean) => (
        <HumanInterventionPanel
          summary={summary}
          stages={stages}
          historyOnly={historyOnly}
          omit={omit}
          isBusy={isBusy || mutationBlocked || documentQuery.isPending || summary.evidence_decision_authorized !== true}
          onConfirmExisting={(rationale) => void runMutation(
            () => confirmExistingGoldTierCustomer(summary, rationale),
            "Confirming retained existing customer…",
          )}
          onEvidenceAction={(target) => {
            const targetIds = {
              DOCUMENTS: EVIDENCE_TARGET_IDS.documents,
              OWNERSHIP_DETAILS: MANUAL_OWNERSHIP_TARGET_ID,
              OWNERSHIP_UPLOAD: "case-ownership-evidence-upload",
              CLASSIFICATION: EVIDENCE_TARGET_IDS.classification,
              IDENTITY: EVIDENCE_TARGET_IDS.identity,
              REVIEW_SEND: "case-review-and-send",
            };
            if (target === "DOCUMENTS") focusEvidence("documents");
            else if (target === "CLASSIFICATION") focusEvidence("classification");
            else if (target === "IDENTITY") focusEvidence("identity");
            else if (target === "REVIEW_SEND") focusActionControl("case-review-and-send", ".btn-primary:not([disabled])");
            else focusActionControl(targetIds[target], target === "OWNERSHIP_UPLOAD" ? "input[type=file]:not([disabled])" : undefined);
          }}
          onResolve={(exception, action) => {
            if (exception.stage === "DOCUMENT" && (action === "KEEP_REGISTRY_VALUE" || action === "USE_DOCUMENT_VALUE") && batchReviewRef.current?.selectSourceDecision(exception.exception_id, action)) {
              focusActionControl("case-blocker-review", `input[data-discrepancy-id="${exception.exception_id}"][value="${action}"]`);
              return;
            }
            if (exception.stage === "DOCUMENT") {
              focusActionControl("case-blocker-review");
              return;
            }
            void runMutation(() => resolveZeroTouchException(summary, exception.exception_id, action, exception.evidence_version));
          }}
        />

  );
  const stageNeedsAttention = (stages: readonly string[]) => summary.active_exceptions.some(item => stages.includes(item.stage))
    || Boolean(summary.interventions?.some(item => stages.includes(item.owning_stage)));
  const reviewReady = summary.active_exceptions.some((item) => item.exception_type === "TARGET_CONFIRMATION_REQUIRED");
  const frozenReview = Boolean(summary.case.target_dispatch_confirmation || summary.clm.submission
    || (targetSubmission && targetSubmission.state !== "NOT_SUBMITTED"));
  const showFinalReview = reviewReady || frozenReview || summary.status === "COMPLETED";
  const preflightUnavailable = summary.clm.target_search_checkpoint?.status === "FAILED"
    && targetSubmission?.state === "NOT_SUBMITTED" && !frozenReview;
  // Summarize existing target projections; action eligibility stays with Main's owners.
  const targetAttention = summary.interventions?.some(item => item.owning_stage === "MOCK_GOLDTIER")
    || summary.active_exceptions.some(item => item.stage === "MOCK_GOLDTIER"
      && item.exception_type !== "TARGET_CONFIRMATION_REQUIRED");
  const targetHeaderStatus = (() => {
    if (confirmationUnknown) return "Submission confirmation is being verified — do not send again.";
    if (targetSubmission?.state === "SUBMISSION_OUTCOME_UNCERTAIN") return "Submission outcome uncertain — verification required.";
    if (targetSubmission?.state === "SENDING") return "Submission in progress — do not send again.";
    if (preflightUnavailable) return "Attention required — GoldTier availability check needed.";
    if (targetAttention) return "Target intervention requires review.";
    if (safeContinuation) return "Verified work retained — safe continuation requires review.";
    if (summary.status === "RECOVERY_PENDING" && !targetSubmission) return "Backend recovery pending — review required.";
    switch (targetSubmission?.state) {
      case "SUBMISSION_FAILED": return "Submission failed — review required.";
      case "SUBMISSION_CONFIRMED": return "Submission confirmed.";
      case "FINALIZATION_PENDING": return "Submission finalization pending — review required.";
      case "NOT_SUBMITTED": return "Submission not started.";
      default: return "Submission state not available in retained evidence.";
    }
  })();
  // Freshness belongs to the existing query owners, including supporting package reads.
  function headerReadSummary(label: string, queries: Array<{
    isPending: boolean; isFetching: boolean; isError: boolean; data: unknown;
  }>) {
    const retained = queries.every(query => query.data !== undefined);
    if (queries.some(query => query.isError)) return retained
      ? "Last-confirmed " + label + " information (refresh failed; may be stale). "
      : "Current evidence unavailable; absence not confirmed. ";
    if (queries.some(query => query.isPending || query.isFetching)) return retained
      ? "Last-confirmed " + label + " information (refresh in progress). "
      : "Loading " + label + " information — current evidence not yet confirmed. ";
    return "";
  }
  const detailHeaderQueries = [detailQuery];
  const ownershipHeaderFreshness = headerReadSummary("ownership", [detailQuery, ownershipQuery]);
  const documentHeaderFreshness = headerReadSummary("document", [detailQuery, documentQuery]);
  const targetHeaderFreshness = headerReadSummary("target", detailHeaderQueries);
  const finalHeaderContext = headerReadSummary("final review", [detailQuery, documentQuery, ownershipQuery])
    + targetHeaderStatus + " " + (frozenReview || summary.status === "COMPLETED" ? "Reviewed package frozen. " : "");
  // D-082 N2: never claim acceptance while the workflow still holds the ownership stage.
  // D-101: for a Government entity the Ownership & UBO stage holds the Government status step
  // instead of an ownership analysis; the stage keeps its title so AI Assistant section links match.
  const governmentBasis = summary.entity_type_basis?.entity_type === "GOVERNMENT" ? summary.entity_type_basis : null;
  const partnershipPendingLabel = summary.entity_type_basis?.partnership_state === "AWAITING_RM_CONFIRMATION" ? summary.entity_type_basis.label : null;
  const ownershipHeaderStatus = ownership?.poc_basis_accepted && !stageNeedsAttention(["OWNERSHIP"])
    ? "Ownership calculated — POC basis accepted."
    : ownership
    ? "Ownership: " + ownership.state.replaceAll("_", " ") + ". " + (stageNeedsAttention(["OWNERSHIP"]) || ["REVIEW_REQUIRED", "FAILED"].includes(ownership.state) || ownership.issues.length > 0 ? "Attention required — review ownership evidence." : "Provisional ownership and UBO analysis.")
    : confirmedOwnershipEmpty ? "No ownership analysis retained in the confirmed response."
      : "Ownership analysis not confirmed.";
  const currentTargetStatusCheck = targetStatusCheck?.identity === targetStatusIdentity
    ? targetStatusCheck : null;
  const remainingIssueCount = summary.active_exceptions.filter(
    (item) => item.exception_type !== "TARGET_CONFIRMATION_REQUIRED",
  ).length + (summary.technical_failure ? 1 : 0);
  const documentUenCandidates = documents.filter((item) => !item.superseded_by_document_id).flatMap((item) => {
    const field = item.fields.find((value) => value.field_key === "registration_number");
    const uen = field?.reviewed_value ?? field?.normalized_value;
    const unresolved = summary.reconciliation?.discrepancies.some((discrepancy) =>
      discrepancy.status === "OPEN" && discrepancy.field_name === "registration_identifier" &&
      discrepancy.observations.some((observation) => observation.source_kind === "DOCUMENT_IDP" &&
        observation.validity === "VALID" && observation.normalized_value === uen &&
        (!observation.document_id || observation.document_id === item.document_id)));
    return (unresolved || !summary.case.registry_acquisition) && uen && uen !== summary.case.requested_uen && field?.review_status !== "REJECTED"
      ? [{ uen, documentId: item.document_id, eventCount: item.events.length }] : [];
  });
  const identityConflict = identityEditable && documentUenCandidates.length > 0;
  // Open discrepancies with no permitted value choice can only be cleared by replacement evidence.
  // Company name and UEN are explained on the affected document's own warning card instead.
  const replacementFieldNames = summary.current_stage === "DOCUMENT"
    ? [...new Set((summary.reconciliation?.discrepancies ?? []).filter(item => item.status === "OPEN" && item.allowed_actions.length === 0
      && item.field_name !== "legal_name" && item.field_name !== "registration_identifier")
      .map(item => item.field_name.replaceAll("_", " ")))]
    : [];
  // The comparison table shows whenever reconciliation evidence exists, so the chosen values stay visible later.
  const showComparison = Boolean(summary.reconciliation);
  // Document-stage "Documents / reconciliation" cards repeat what this section already shows
  // (comparison table, review decisions, replace-document control), so they are hidden.
  // A card stays only if it carries an action that nothing else on the page offers.
  const reviewPanelSourceIds = new Set(reviewableSourceDiscrepancies(summary, documents).map(item => item.discrepancy_id));
  const coveredByReviewPanel = (item: HumanInterventionProjection) => item.owning_stage === "DOCUMENT"
    && (item.evidence_actions ?? []).every(action => action.target === "DOCUMENTS")
    && item.authorized_actions.length > 0
    && item.authorized_actions.every(action => (action.action === "KEEP_REGISTRY_VALUE" || action.action === "USE_DOCUMENT_VALUE")
      && reviewPanelSourceIds.has(item.intervention_id));

  // The backend projection owns placement; endpoint eligibility stays with the
  // existing predicate above. A genuine Registry correction keeps the one editor.
  const identityInSearch = !registryCorrectionRequired && !identityConflict
    && !summary.interventions?.some(item => item.owning_stage === "REGISTRY"
      && item.evidence_actions?.some(action => action.target === "IDENTITY"))
    && (summary.interventions?.some(item => item.owning_stage === "GOLDTIER_SEARCH"
      && item.evidence_actions?.some(action => action.target === "IDENTITY"))
      || summary.active_exceptions.some(item => item.status === "OPEN"
        && item.stage === "GOLDTIER_SEARCH" && item.blocker_code === "INITIAL_IDENTITY_INCOMPLETE"));
  const identityEditor = (identityIncomplete || identityEditable) && (
    <div
      key={`${evidenceIdentity}:identity:${summary.version}`}
      id={EVIDENCE_TARGET_IDS.identity}
      className="evidence-focus-target"
      tabIndex={-1}
    >
      <IdentityCorrectionForm
        onboardingCase={summary.case}
        registryRecovery={!identitySearchRecheck}
        documentCandidates={documentUenCandidates}
        error={reviewEdit.current?.target === "identity" && isCurrentCaseAction(reviewEdit.current) ? error : null}
        disabled={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true}
        onSubmit={(values) => void runMutation(
          () => {
            const identityInput = {
            legal_name: values.legal_name,
            registration_number: values.registration_number,
            country_of_incorporation: values.country_of_incorporation,
            expected_automation_version: summary.version,
            expected_clm_version: summary.clm.version,
            expected_case_event_count: summary.case.events.length,
            };
            return identitySearchRecheck
              ? recheckZeroTouchIdentitySearch(caseId, identityInput)
              : correctRegistryIdentity(caseId, {
                  ...identityInput, choice: values.choice ?? "OTHER",
                  document_id: values.document_id,
                  expected_document_event_count: values.expected_document_event_count,
                });
          },
          "Verifying company identity and resuming…",
          identitySearchRecheck ? "identity-recheck" : "registry-identity",
        )}
      />
    </div>
  );

  return (
    <div className="ds-root detail-layout" onKeyDownCapture={recordOwnershipInteraction}
      onPointerDownCapture={recordOwnershipInteraction} onMouseDownCapture={recordOwnershipInteraction}
      onClickCapture={recordOwnershipInteraction}>
      <div className="side-panel case-pipeline-panel">
        <button type="button" className="btn btn-ghost" onClick={onBack} style={{ paddingLeft: 0 }}>← Back to Cases</button>
        {evidenceFocusNotice?.identity === evidenceIdentity && <p className="ds-banner ds-banner-warn" role="status">{evidenceFocusNotice.message}</p>}
        <CasePipelineAttention summary={summary} onNavigate={focusAttention} onStageActivate={focusProcessingNode} />
        <AdvisoryContinuation
          summary={summary}
          disabled={isBusy || mutationBlocked}
          onContinue={() => void runMutation(() => resumeZeroTouchCase(caseId, summary), "Continuing onboarding")}
        />
        {(targetSubmission?.state !== "SUBMISSION_OUTCOME_UNCERTAIN" || summary.current_stage !== "MOCK_GOLDTIER" || summary.technical_failure?.code !== "CLM_TARGET_OUTCOME_UNCERTAIN") && !preflightUnavailable && summary.status === "TECHNICAL_FAILURE" && summary.technical_failure && <div className="ds-banner ds-banner-warn case-technical-failure" style={{ marginBottom: 16 }}><h3 style={{ marginTop: 0 }}>Automation stopped safely</h3><strong>{summary.technical_failure.code}</strong><p style={{ marginBottom: 0 }}>{summary.technical_failure.message}</p></div>}
        <hr className="hr" />
        <div className="text-muted" style={{ fontSize: 11.5 }}>
          Loop —
        </div>
      </div>

      <OnboardingWorkspace active={onboardingIsExecuting(summary, isBusy, error ?? (loadError ? "Evidence load failed" : null))} message={onboardingExecutionMessage(summary, busyLabel)}>
      <div className="ds-page" style={{ flex: 1 }}>
        <div className="ds-page-header"><div><p className="card-kicker case-header-meta"><span>{summary.case.requested_uen} · {summary.case.jurisdiction_resolution?.resolved_jurisdiction ?? "—"} · {summary.case.client_scope_label ?? "Legacy unassigned"}</span></p><h1>{entity?.legal_name ?? summary.case.requested_uen}</h1></div><div className="case-header-actions"><div className="case-priority" role="group" aria-label="Case priority"><span className="case-priority__label">Priority</span><PriorityControl priority={summary.case.priority} disabled={isBusy || mutationBlocked} onSave={runPriorityMutation} /></div>{(actor.role === "DIRECTOR" || actor.role === "RELATIONSHIP_MANAGER") && <button type="button" className="btn btn-danger" disabled={isBusy || mutationBlocked} onClick={() => { if (!mutationPending.current && !mutationBlocked) setDeleteDialogOpen(captureCaseAction()); }}>Delete case</button>}<span className="tag tag-accent-2 case-header-status">{summary.status.replaceAll("_", " ")}</span></div></div>
        {error && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{error}</div>}

        <OnboardingProgressPanel
          summary={summary}
          onStageActivate={focusProcessingNode}
          availableFocusTargets={availableFocusTargets}
          initialFocusNodeId={initialFocusNodeId}
        />
        {/* The stage rail keeps the backend's registry status; a UEN mismatch is flagged separately. */}
        {identityConflict && <p className="ds-banner ds-banner-warn uen-conflict-indicator" role="status">
          <strong>UEN conflict — review required.</strong> Entered UEN and document UEN differ — confirm which to use in Registry verification.
        </p>}
        {pendingDocuments && <PendingDocumentsBanner pending={pendingDocuments} />}


        {isBusy && busyLabel && (
          <div className="ds-banner case-action-progress" role="status" aria-live="polite"
            style={{ position: "fixed", bottom: 16, left: 16, right: 16, margin: "0 auto", maxWidth: 420, zIndex: 30 }}>
            {busyLabel}
          </div>
        )}

        <div id={SEARCH_TARGET_ID} role="group" aria-label="Existing-customer search" className="evidence-focus-target" tabIndex={-1}>
        <StageDisclosure title="Existing-customer search" status={stageStatusFor(summary, ["GOLDTIER_SEARCH"])} summary={`${headerReadSummary("Search", detailHeaderQueries)}Search: ${summary.clm.target_search_checkpoint?.status.replaceAll("_", " ") ?? "No result retained"}. ${identityInSearch || stageNeedsAttention(["GOLDTIER_SEARCH"]) ? "Attention required — review Search identity or decision." : "GoldTier Search evidence."}`} scopeKey={`${disclosureIdentity}:${summary.clm.target_search_checkpoint?.request_id ?? "no-request"}`}
          main={<>
            <p className="control-help">{summary.clm.target_search_checkpoint
              ? `Retained Search status: ${summary.clm.target_search_checkpoint.status.replaceAll("_", " ")}.`
              : "No Search result is retained for this case."}</p>
            {summary.clm.target_search_checkpoint && <p>Search provider: GoldTier · {summary.clm.target_search_checkpoint.provider_mode} · {summary.clm.target_search_checkpoint.provider_classification}</p>}
            {summary.clm.target_search_checkpoint && <p>Retained Search outcome: {summary.clm.target_search_checkpoint.disposition ?? "Not recorded"}.</p>}
            <ProcessingBlockerPanels summary={summary} stage="REGISTRY" searchPart="main" />
          {renderInterventions(["GOLDTIER_SEARCH"])}
          {identityInSearch && identityEditor}
          {!identityInSearch && identityEditor
            && (identitySearchRecheck || summary.clm.target_search_checkpoint?.status === "FAILED") && <button type="button"
            className="btn btn-secondary" disabled={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true}
            onClick={() => focusEvidence("identity")}>{identitySearchRecheck
              ? "Review identity for Search recheck" : "Review Registry identity for Search"}</button>}

          </>}
          moreDetails={<>{summary.clm.target_search_checkpoint ? <dl aria-label="Retained Search evidence">
            <div><dt>Retained disposition</dt><dd>{summary.clm.target_search_checkpoint.disposition}</dd></div>
            <div><dt>Provider outcome</dt><dd>{summary.clm.target_search_checkpoint.provider_outcome}</dd></div>
            <div><dt>Candidate count</dt><dd>{summary.clm.target_search_checkpoint.candidate_count ?? "Not recorded"}</dd></div>
            <div><dt>Match explanation</dt><dd>{summary.clm.target_search_checkpoint.message}</dd></div>
            {summary.clm.target_search_checkpoint.resolution_outcome && <div><dt>Retained choice</dt><dd>{summary.clm.target_search_checkpoint.resolution_outcome}</dd></div>}
          </dl> : <p>No supporting Search result is retained.</p>}<ProcessingBlockerPanels summary={summary} stage="REGISTRY" searchPart="more" /></>}
          technicalDetails={<>
            <ProcessingBlockerPanels summary={summary} stage="REGISTRY" searchPart="technical" />
            {summary.clm.target_search_checkpoint && <dl aria-label="Search checkpoint diagnostics">
              <div><dt>Retained request</dt><dd>{summary.clm.target_search_checkpoint.request_id}</dd></div>
              <div><dt>Safe code</dt><dd>{summary.clm.target_search_checkpoint.code ?? "None recorded"}</dd></div>
              <div><dt>Status code</dt><dd>{summary.clm.target_search_checkpoint.status_code ?? "Not recorded"}</dd></div>
              <div><dt>Searched at</dt><dd>{displayTimestamp(summary.clm.target_search_checkpoint.searched_at)}</dd></div>
            </dl>}
          </>}
        />
        </div>
        <StageDisclosure title="Registry verification" status={stageStatusFor(summary, ["ACRA_REGISTRY"])} active={identityConflict || undefined} summary={`${headerReadSummary("registry", detailHeaderQueries)}Registry: ${summary.clm.readiness.registry.status}. ${stageNeedsAttention(["REGISTRY"]) ? "Attention required — review registry identity and evidence." : "Retained registry evidence and source."}`} scopeKey={`${disclosureIdentity}:${summary.case.registry_evidence_binding?.bound_to_case_at ?? "unbound"}:${acquisition?.retrieved_at ?? "no-acquisition"}`}
          main={<>
            {renderInterventions(["REGISTRY"])}
            <UenRouteNote route={summary.case.uen_route} />
            {!identityInSearch && identityEditor}
            <RegistryStatePanel summary={summary} registryProviderMode={registryProviderMode} compact />
            <div key={`${evidenceIdentity}:registry`} id={EVIDENCE_TARGET_IDS.registry} className="evidence-focus-target" tabIndex={-1}>
              <RegistryProvenancePanel acquisition={acquisition} binding={summary.case.registry_evidence_binding} entityType={entity?.party_type} providerMode={registryProviderMode} part="main" />
            </div>
          </>}
          moreDetails={<>
        <div className="ds-two-col case-corporate-evidence"><div><h4>Corporate particulars</h4><div>
          <div className="kv-row"><span className="kv-label">Company name</span><span className="kv-value">{entity?.legal_name ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registration ID</span><span className="kv-value">{entity?.registration_number ?? summary.case.requested_uen}</span></div><div className="kv-row"><span className="kv-label">Entity type</span><span className="kv-value">{entity?.party_type ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registry status</span><span className="kv-value">{entity?.entity_status ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registration date</span><span className="kv-value">{entity?.registration_date ?? "—"}</span></div>
        </div></div><div><h4>Registry officers and roles</h4>{acquisition && acquisition.officers.length > 0 ? <div className="table-card"><table className="table"><tbody>{acquisition.officers.map((officer) => <tr key={officer.officer_id}><td>{officer.name}</td><td>{officer.role}</td></tr>)}</tbody></table></div> : <p className="text-muted" style={{ fontSize: 12 }}>Not available.</p>}</div></div>
            <RegistryProvenancePanel acquisition={acquisition} binding={summary.case.registry_evidence_binding} entityType={entity?.party_type} providerMode={registryProviderMode} part="more" />
          </>}
          technicalDetails={<RegistryProvenancePanel acquisition={acquisition} binding={summary.case.registry_evidence_binding} entityType={entity?.party_type} providerMode={registryProviderMode} part="technical" />}
        />
        <StageDisclosure title="Document verification" status={stageStatusFor(summary, ["DOCUMENT_IDP", "RECONCILIATION"])} summary={`${documentHeaderFreshness}Documents: ${summary.clm.readiness.document.status}. ${stageNeedsAttention(["DOCUMENT"]) ? "Attention required — review document evidence and required actions." : summary.current_stage === "DOCUMENT" ? "Current stage — review document evidence and required actions." : "Document evidence and reconciliation."}`} scopeKey={disclosureIdentity}
          main={<>
          {renderInterventions(["DOCUMENT"], false, coveredByReviewPanel)}
          {summary.status === "PENDING_INPUTS" && !documents.some(doc => isDocumentReuploadRequired(doc, summary)) && <label id="case-document-upload" className="btn btn-secondary document-upload-control">
            Upload required document
            <input type="file" className="sr-only document-upload-input"
              accept={UPLOAD_ACCEPT}
              disabled={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true}
              onChange={event => {
                const file = event.target.files?.[0]; event.target.value = "";
                if (file) void settleEvidenceMutation(() => intakeZeroTouchDocument(caseId, file, false), "Processing uploaded evidence…", "Document upload could not complete.");
              }} />
          </label>}
          {summary.status === "PENDING_INPUTS" && !documents.some(doc => isDocumentReuploadRequired(doc, summary))
            && <p className="control-help">{UPLOAD_HELP_TEXT}</p>}
          {summary.status === "PENDING_INPUTS" && documents.some(isCurrentDocument)
            && !documents.some(doc => isCurrentDocument(doc) && doc.state === "FAILED")
            && !canContinueRecoveredIntake(summary, documents)
            && summary.timing.automation_elapsed_ms !== null
            && <button id="case-document-intake-start" type="button" className="btn btn-primary"
              disabled={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true}
              onClick={handleContinueRecoveredIntake}>Continue evidence review</button>}
          {summary.status === "PENDING_INPUTS" && summary.timing.automation_elapsed_ms === null
            && documents.some(isCurrentDocument)
            && !documents.some(doc => isCurrentDocument(doc) && doc.state === "FAILED")
            && <form key={`${evidenceIdentity}:initial-intake`} id="case-document-intake-start" onSubmit={handleCompleteInitialIntake}>
              <p>Upload the full document set, then enter its intended count to complete intake.</p>
              <label>Intended document count
                <input name="expectedDocumentCount" type="number" min="1" max="20" step="1" required
                  disabled={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true} />
              </label>
              <button type="submit" className="btn btn-primary"
                disabled={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true}>Complete document intake</button>
            </form>}
          {summary.status === "WAITING_FOR_REVIEW" && summary.current_stage === "DOCUMENT"
            && ["MATCHED", "RESOLVED"].includes(summary.reconciliation?.status ?? "")
            && summary.active_exceptions.some(item => item.stage === "DOCUMENT")
            && documents.filter(isCurrentDocument).length > 0
            && documents.filter(isCurrentDocument).every(doc => doc.semantic_completion === "RECONCILIATION_RESOLVED"
              || doc.fields.every(field => field.review_status !== "PENDING"))
            && <section id="case-document-checkpoint-repair" className="ds-banner">
              <p>Review decisions are retained. Continue once to recheck the remaining onboarding checkpoint.</p>
              <button type="button" className="btn btn-secondary"
                disabled={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true}
                onClick={handleContinueRecoveredIntake}>Continue retained review checkpoint</button>
            </section>}
        <BlockerDecisionReview
          key={`${evidenceIdentity}:${actor.role}:${actor.team_id}:${summary.evidence_decision_authorized}:${summary.version}:${summary.case.events.length}:${documents.map(doc => `${doc.document_id}:${doc.events.length}:${doc.review_source_fingerprint}`).join("|")}`}
          ref={batchReviewRef} summary={summary} documents={documents} busy={isBusy || mutationBlocked}
          onReplaceDocument={() => document.querySelector<HTMLInputElement>(`#${EVIDENCE_TARGET_IDS.documents} .document-upload-input:not([disabled])`)?.click()}
          // Each Confirm submits only the selected decision family; the registry-vs-document step
          // is then pre-filled from the reviewer's choices and needs its own explicit Confirm.
          onConfirm={(batch: ReviewDecisionBatch) => void settleEvidenceMutation(
            () => confirmReviewDecisions(caseId, batch), "Applying confirmed review decisions…", "Review confirmation could not be completed.")}
        />
        {/* One card: the registry-vs-document comparison, then the uploaded file's status. */}
        <section className="card document-combined" aria-labelledby="document-combined-heading">
          <div className="document-combined__header">
            <p className="card-kicker">Local/Mock evidence · not approval</p>
            <h3 id="document-combined-heading">Document evidence</h3>
            <p className="text-muted">Registry and document values side by side. No source wins automatically.</p>
          </div>
          {replacementFieldNames.length > 0 && <div className="ds-banner ds-banner-warn document-combined__action" role="status">
            <strong>Action needed: upload a replacement document</strong>
            <span>The current document has no usable value for {replacementFieldNames.join(", ")}. Upload a corrected document to continue — the case re-checks it automatically.</span>
            <button type="button" className="btn btn-primary" disabled={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true}
              onClick={() => document.querySelector<HTMLInputElement>(`#${EVIDENCE_TARGET_IDS.documents} .document-upload-input:not([disabled])`)?.click()}>
              Upload replacement document
            </button>
          </div>}
        {showComparison && (
          <div key={`${evidenceIdentity}:reconciliation`} id={EVIDENCE_TARGET_IDS.reconciliation} className="evidence-focus-target" tabIndex={-1}>
            <ConfirmDetailsPanel presentation="main" embedded summary={summary} documents={documents} isBusy={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true} />
          </div>
        )}
        <div key={`${evidenceIdentity}:documents`} id={EVIDENCE_TARGET_IDS.documents} className="evidence-focus-target" tabIndex={-1}>
          {error && reviewEdit.current?.target === "documents" && isCurrentCaseAction(reviewEdit.current)
            && <p role="alert" className="ds-banner ds-banner-warn">{error}</p>}
          <DocumentEvidencePanel presentation="main" embedded hideFieldRows={showComparison} reviewInWorkspace key={evidenceIdentity} summary={summary} documents={documents} busy={isBusy} busyLabel={busyLabel} mutationBlocked={mutationBlocked} loading={documentQuery.isPending || documentQuery.isFetching} loadFailed={documentQuery.isError} onReview={handleDocumentReview} onReplace={handleReplacement} onRetry={handleRetry} onContinue={handleContinueRecoveredIntake} onRecoverRefresh={handleRecoverDocumentRefresh} onRefresh={() => void handleReadOnlyRefresh()}
            onReviewDifference={summary.reconciliation && summary.current_stage === "DOCUMENT" ? () => focusEvidence("reconciliation") : undefined}
            onCorrectIdentity={identityIncomplete || identityEditable ? () => focusEvidence("identity") : undefined} />
        </div>
        </section>

          </>}
          moreDetails={<DocumentEvidencePanel presentation="more" summary={summary} documents={documents} busy={isBusy} busyLabel={null} mutationBlocked={mutationBlocked} loading={documentQuery.isPending || documentQuery.isFetching} loadFailed={documentQuery.isError} onReview={handleDocumentReview} onReplace={handleReplacement} onRetry={handleRetry} onContinue={handleContinueRecoveredIntake} onRefresh={() => void handleReadOnlyRefresh()} />}
          technicalDetails={<>
            <DocumentEvidencePanel presentation="technical" summary={summary} documents={documents} busy={isBusy} busyLabel={null} mutationBlocked={mutationBlocked} loading={documentQuery.isPending || documentQuery.isFetching} loadFailed={documentQuery.isError} onReview={handleDocumentReview} onReplace={handleReplacement} onRetry={handleRetry} onContinue={handleContinueRecoveredIntake} onRefresh={() => void handleReadOnlyRefresh()} />
            <ConfirmDetailsPanel presentation="technical" summary={summary} />
          </>}
        />
        <StageDisclosure title="Ownership & UBO" status={stageStatusFor(summary, ["OWNERSHIP_UBO"])} summary={governmentBasis ? governmentBasis.label : `${ownershipHeaderFreshness}${ownershipHeaderStatus}`} scopeKey={disclosureIdentity} main={governmentBasis ? <>
          {renderInterventions(["OWNERSHIP"])}
          <div key={`${evidenceIdentity}:government`} id={EVIDENCE_TARGET_IDS.ownership} className="evidence-focus-target" tabIndex={-1}>
            <GovernmentStatusPanel
              basis={governmentBasis}
              canConfirm={summary.ownership_edit_authorized === true}
              disabled={isBusy || mutationBlocked}
              onConfirm={() => {
                const status = governmentBasis.government_status;
                if (!status?.document_id || status.document_event_count === null) return;
                void runMutation(
                  () => confirmGovernmentStatus(caseId, {
                    document_id: status.document_id!,
                    document_event_count: status.document_event_count!,
                    expected_automation_version: summary.version,
                    expected_case_event_count: summary.case.events.length,
                  }),
                  "Confirming Government status…",
                  "manual-ownership",
                );
              }}
            />
          </div>
        </> : <>
          {ownershipReadNotice}
          {confirmedOwnershipEmpty && <p>No ownership analysis is retained in the confirmed response.</p>}
          {summary.entity_type_basis?.entity_type === "PARTNERSHIP" && <p className="ds-banner" role="note" data-testid="partnership-basis">{summary.entity_type_basis.label}</p>}
          {renderInterventions(["OWNERSHIP"])}
        {ownershipRecovery && summary.ownership_edit_authorized === true
          && ownership?.analysis_id === ownershipRecovery.analysis_id
          && (ownership.version === undefined || ownership.version === ownershipRecovery.version) && (
          <div id={MANUAL_OWNERSHIP_TARGET_ID} className="evidence-focus-target" tabIndex={-1}>
            <ManualOwnershipEvidenceForm
              key={`${evidenceIdentity}:${ownershipRecovery.analysis_id}:${ownershipRecovery.version}:${ownership.analysis_id}:${ownership.version ?? "unknown"}:${documents.map((document) => `${document.document_id}:${document.events.length}`).join("|")}`}
              canonicalRootUen={summary.case.entity?.registration_number ?? summary.case.initial_identity?.registration_number ?? summary.case.requested_uen}
              initialRootLegalName={summary.case.entity?.legal_name ?? summary.case.initial_identity?.legal_name ?? ""}
              legalFormLabel={summary.entity_type_basis?.entity_type === "PARTNERSHIP" ? "Partnership" : undefined}
              partnershipState={summary.entity_type_basis?.partnership_state}
              documents={documents}
              ownership={ownership}
              disabled={isBusy || mutationBlocked || ownershipReadUnconfirmed || summary.ownership_edit_authorized !== true}
              onUploadEvidence={summary.interventions?.some((intervention) =>
                intervention.evidence_actions?.some((action) => action.target === "OWNERSHIP_UPLOAD"),
              ) ? (file) => void settleEvidenceMutation(
                () => intakeZeroTouchDocument(caseId, file, false),
                "Validating client-supplied ownership evidence…",
                "Ownership evidence could not be added.",
              ) : undefined}
              onSubmit={(values) => void runMutation(
                () => submitManualOwnershipEvidence(caseId, {
                  root_registration_number: summary.case.entity?.registration_number ?? summary.case.initial_identity?.registration_number ?? summary.case.requested_uen,
                  evidence_document_id: values.evidence_document_id,
                  evidence_document_version: values.evidence_document_version,
                  as_of_date: values.as_of_date,
                  rationale: values.rationale,
                  root_party_id: values.root_party_id,
                  source_selection: values.source_selection,
                  observed_document_versions: values.observed_document_versions,
                  selected_observation_ids: values.selected_observation_ids,
                  parties: values.parties,
                  relationships: values.owners.map((owner) => ({
                    relationship_id: owner.relationship_id,
                    parent_party_id: owner.parent_party_id,
                    child_party_id: owner.party_id,
                    ownership_percent: owner.ownership_percent,
                    relationship_type: "DIRECT_ECONOMIC_INTEREST",
                  })),
                  expected_automation_version: summary.version,
                  expected_ownership_version: ownershipRecovery.version,
                  expected_case_event_count: summary.case.events.length,
                }),
                "Submitting reviewed ownership declaration…",
                "manual-ownership",
              )}
            />
          </div>
        )}
          <div key={`${evidenceIdentity}:ownership`} id={EVIDENCE_TARGET_IDS.ownership} className="evidence-focus-target" tabIndex={-1}>
            {ownership && <OwnershipPathExplorer presentation="main" partnershipPendingLabel={partnershipPendingLabel} key={`${evidenceIdentity}:${ownership?.analysis_id ?? "none"}`} record={ownership} acquisition={acquisition} primaryBlockerVisible={summary.active_exceptions.some((item) => item.stage === "OWNERSHIP")} />}
          </div>
        </>}
          moreDetails={<>{ownershipReadNotice}{confirmedOwnershipEmpty && <p>No ownership analysis is retained in the confirmed response.</p>}<OwnershipSupportingDetails record={ownership} presentation="more" partnershipPendingLabel={partnershipPendingLabel} /></>}
          technicalDetails={<>{ownershipReadNotice}{confirmedOwnershipEmpty && <p>No ownership analysis is retained in the confirmed response.</p>}<OwnershipSupportingDetails key={ownership?.analysis_id ?? "none"} record={ownership} presentation="technical" partnershipPendingLabel={partnershipPendingLabel} /></>}
        />
        {/* An uncertain outcome or pending safe recovery needs the reviewer: the section opens on load and shows the blocked final step. */}
        <StageDisclosure title={GOLDTIER_DETAILS_STAGE_LABEL} active={targetSubmission?.state === "SUBMISSION_OUTCOME_UNCERTAIN" || safeContinuation || summary.status === "RECOVERY_PENDING" ? true : undefined}
          status={stageStatusFor(summary, targetSubmission?.state === "SUBMISSION_OUTCOME_UNCERTAIN" ? ["READINESS", "GOLDTIER_TARGET", "FINAL_REVIEW_SEND"] : ["READINESS", "GOLDTIER_TARGET"])}
          summary={`${targetHeaderFreshness}${stageNeedsAttention(["READINESS"]) ? "Attention required — review required inputs and configuration. " : ""}${targetHeaderStatus} · ${titleCaseWords(summary.clm.submission_plan.environment)}`} scopeKey={disclosureIdentity} main={<>
          {readinessReadNotice}
          {/* Focus anchors for "Resolve issue" / "Review outstanding" navigation into this section. */}
          <div key={`${evidenceIdentity}:recovery`} id={EVIDENCE_TARGET_IDS.recovery} className="evidence-focus-target" tabIndex={-1}>
          <section id="case-target-blocker" className="goldtier-status evidence-focus-target" tabIndex={-1} aria-label="GoldTier readiness and submission status">
            <ul className="goldtier-status__grid" aria-label="Readiness by area">
              {([
                ["Registry", summary.clm.readiness.registry.status],
                ["Documents", summary.clm.readiness.document.status],
                ["Ownership", summary.clm.readiness.ownership.status],
                ["GoldTier", summary.clm.readiness.goldtier.status],
              ] as const).map(([label, status]) => (
                <li key={label} className="goldtier-status__tile" data-tone={readinessTone(status)}>
                  <span className="goldtier-status__label">{label}</span>
                  <span className="goldtier-status__value">{titleCaseWords(status)}</span>
                </li>
              ))}
            </ul>
            <p className="control-help goldtier-status__note">Shows whether the case is ready to send to GoldTier. GoldTier KYC and four-eye approval happen separately.</p>
          </section>
          </div>
          {renderInterventions(["READINESS"])}
        {summary.case.policy_rebind && (
          <PolicyRebindPanel
            presentation="main"
            key={`${disclosureIdentity}:${summary.case.policy_rebind.revision}:${summary.case.policy_rebind.configuration_status}`}
            classification={summary.target_classification}
            metadata={summary.case.policy_rebind}
            registrationNumber={summary.case.entity?.registration_number ?? summary.case.initial_identity?.registration_number ?? summary.case.requested_uen}
            disabled={isBusy || mutationBlocked || readinessReadUnconfirmed}
            onFocusClassification={() => focusEvidence("classification")}
            onSubmit={(rationale) => void runMutation(
              () => rebindZeroTouchPolicy(caseId, {
                rationale,
                expected_automation_version: summary.version,
                expected_clm_version: summary.clm.version,
                expected_case_event_count: summary.case.events.length,
              }),
              "Rebinding accepted Singapore POC configuration…",
              "policy-rebind",
            )}
          />
        )}
        {summary.target_classification && (
          <div id="case-target-classification" className="evidence-focus-target" tabIndex={-1}>
          {error && reviewEdit.current?.target === "classification" && isCurrentCaseAction(reviewEdit.current)
            && <p role="alert" className="ds-banner ds-banner-warn">{error}</p>}
          <TargetClassificationPanel
            presentation="main"
            reviewRequested={classificationReviewRequest !== null && isCurrentCaseAction(classificationReviewRequest)}
            key={`${summary.case.case_id}:${summary.target_classification.vocabulary_version}:${summary.target_classification.evidence_fingerprint ?? "unknown"}:${summary.target_classification.current ?? "unknown"}:${summary.target_classification.kyc_customer_type.selected_value ?? "unresolved"}:${summary.target_classification.client_segment.selected_value ?? "unresolved"}`}
            classification={summary.target_classification}
            disabled={isBusy || mutationBlocked || readinessReadUnconfirmed || summary.evidence_decision_authorized !== true || frozenReview}
            onSubmit={(input) => runMutation(
              () => updateGoldTierTargetClassification(caseId, {
                ...input,
                expected_automation_version: summary.version,
                expected_case_event_count: summary.case.events.length,
              }),
              "Saving GoldTier target classification…",
            )}
          />
          </div>
        )}

        {preflightUnavailable && <section className="ds-banner ds-banner-warn" aria-labelledby="target-preflight-title">
          <h3 id="target-preflight-title">GoldTier availability check needed</h3>
          <p>GoldTier could not be checked safely before sending. No target write was attempted. Your case data is preserved; check again when GoldTier is available.</p>
          {summary.case.initial_identity && actor.capabilities.includes("CASE_ACCESS") && <button type="button" className="btn btn-secondary" disabled={isBusy || mutationBlocked || confirmationUnknown} onClick={() => void runMutation(() => recheckZeroTouchIdentitySearch(caseId, {
            ...summary.case.initial_identity!, country_of_incorporation: "SG",
            expected_automation_version: summary.version, expected_clm_version: summary.clm.version,
            expected_case_event_count: summary.case.events.length,
          }), "Checking GoldTier availability…", "identity-recheck")}>Check GoldTier availability</button>}
          <p className="control-help">This performs a read-only identity check. Sending still requires the current final review.</p>
        </section>}
        {confirmationUnknown && <div className="ds-banner" role="status">
          <h3 id="submission-observation-title" tabIndex={-1}>Verifying submission outcome…</h3><p>The confirmation was sent once. Only retained case state is being read; no submission is repeated.</p>
          <button type="button" className="btn btn-secondary" disabled={isBusy || mutationBlocked} onClick={() => void verifySubmissionAgain()}>Verify submission outcome</button>
        </div>}
        {targetSubmission?.state === "SUBMISSION_OUTCOME_UNCERTAIN" && <TargetRecoveryPanel
          key={targetStatusIdentity} summary={summary} actor={actor} presentation="main"
          busy={isBusy || mutationBlocked || confirmationUnknown}
          checking={currentTargetStatusCheck?.checking ?? false}
          result={currentTargetStatusCheck?.result ?? null} error={currentTargetStatusCheck?.error ?? null}
          onCheck={canCheckTargetStatus ? () => void runTargetStatusCheck(false) : undefined}
          onRecover={recoverTarget}
        />}
          {renderInterventions(["MOCK_GOLDTIER"])}
        {safeContinuation && <section className="ds-banner" aria-labelledby="target-continuation-title" aria-live="polite" style={{ marginBottom: 16 }}>
          <h3 id="target-continuation-title" tabIndex={-1}>Verified work is saved</h3>
          <p>Continue the same submission to complete the remaining steps. Previously completed or verified steps will not be sent again.</p>
          <button type="button" className="btn btn-primary" disabled={isBusy || mutationBlocked} onClick={() => void runMutation(() => resumeZeroTouchCase(caseId))}>Complete safe recovery</button>
        </section>}
        {summary.status === "RECOVERY_PENDING"
          && !targetSubmission && <div className="ds-banner" style={{ marginBottom: 16 }}><p style={{ margin: 0, fontSize: 12.5 }}>Backend recovery is pending; target operations will not be replayed by the browser.</p><button type="button" className="btn btn-primary" style={{ marginTop: 10 }} disabled={isBusy || mutationBlocked} onClick={() => void runMutation(() => resumeZeroTouchCase(caseId))}>Complete safe recovery</button></div>}

        <CompletedOverview summary={summary} onViewAudit={onViewAudit} />
        </>}
          moreDetails={<>
            {readinessReadNotice}
            <p>Readiness prepares the current case for submission. It does not establish GoldTier KYC verification or four-eye approval.</p>
            {summary.target_classification && <TargetClassificationDetails classification={summary.target_classification} presentation="more" />}
            {summary.case.policy_rebind && <PolicyRebindDetails metadata={summary.case.policy_rebind} registrationNumber={summary.case.entity?.registration_number ?? summary.case.initial_identity?.registration_number ?? summary.case.requested_uen} presentation="more" />}
            <h3>Retained operation summaries</h3>
            <ul>{summary.target_operations.map(item => <li key={item.operation}>{item.operation}: {item.status}</li>)}</ul>
            <OperationalTiming summary={summary} />
          </>}
          technicalDetails={<>
            {readinessReadNotice}
            <p>Readiness policy version: {summary.clm.readiness.policy_version ?? "Not recorded"} · evaluated at: {displayTimestamp(summary.clm.readiness.evaluated_at)} · CLM version: {summary.clm.version ?? "Not recorded"}</p>
            <p>Backend submission state: {targetSubmission?.state ?? "Not available in retained evidence"}</p>
            {summary.clm.readiness.blockers.length > 0 && <><h4>Readiness blocker codes</h4><ul>{summary.clm.readiness.blockers.map((blocker, index) => <li key={`blocker-${index}`}>{blocker}</li>)}</ul></>}
            {summary.clm.readiness.warnings.length > 0 && <><h4>Readiness warning codes</h4><ul>{summary.clm.readiness.warnings.map((warning, index) => <li key={`warning-${index}`}>{warning}</li>)}</ul></>}
            {summary.target_classification && <TargetClassificationDetails classification={summary.target_classification} presentation="technical" />}
            {summary.case.policy_rebind && <PolicyRebindDetails metadata={summary.case.policy_rebind} registrationNumber={summary.case.entity?.registration_number ?? summary.case.initial_identity?.registration_number ?? summary.case.requested_uen} presentation="technical" />}
            <TargetRecoveryDetails summary={summary} result={currentTargetStatusCheck?.result ?? null} />
            {targetSubmission?.state !== "SUBMISSION_OUTCOME_UNCERTAIN" && <dl>
              <div><dt>Submission ID</dt><dd>{targetSubmission?.submission_id ?? "Not retained"}</dd></div>
              <div><dt>Ledger state</dt><dd>{targetSubmission?.ledger_state ?? "Not retained"}</dd></div>
            </dl>}
            <h3>Target operation state and sequence</h3>
            <ol>{summary.target_operations.map(item => <li key={item.operation}>{item.operation}: {item.status}</li>)}</ol>
            <aside className="readiness-panel evidence-run-record" aria-label="Retained execution record">
            <h4>Submission plan</h4>
            <p className="control-help">{summary.clm.submission_plan.environment} · {summary.clm.submission_plan.base_operations.join(" → ")}</p>
            <p className="control-help">Ready-for-Approval: {summary.clm.submission_plan.real_ready_for_approval.replaceAll("_", " ")}</p>
            {summary.clm.submission_plan.request_preview && (
              <GoldTierRequestPreview preview={summary.clm.submission_plan.request_preview} />
            )}
            <div className="kv-row"><span className="kv-label">{summary.clm.submission_plan.environment === "MOCK" ? "Mock GoldTier" : "GoldTier Sandbox"} party ID</span><span className="kv-value">{summary.case.goldtier_result?.party_id ?? "—"}</span></div>
            <h4>Run metrics</h4>
            <div className="kv-row"><span className="kv-label">Automated stages</span><span className="kv-value">{summary.metrics.automated_stages_completed}</span></div>
            <div className="kv-row"><span className="kv-label">Human interventions</span><span className="kv-value">{summary.metrics.human_interventions}</span></div>
            <div className="kv-row"><span className="kv-label">Exceptions</span><span className="kv-value">{summary.metrics.exceptions_resolved}/{summary.metrics.exceptions_raised} resolved</span></div>
            <div className="kv-row"><span className="kv-label">Final outcome</span><span className="kv-value">{summary.metrics.final_outcome ? targetOutcomeLabel(summary.metrics.final_outcome, summary.clm.submission_plan.environment) : "—"}</span></div>
            </aside>
          </>}
        />
        {showFinalReview ? <ReviewAndSend
          disclosureScopeKey={disclosureIdentity}
          readNotice={finalReadNotice}
          headerContext={finalHeaderContext}
          confirmationUnknown={confirmationUnknown}
          headerReadUnconfirmed={[detailQuery, documentQuery, ownershipQuery].some(query => query.isPending || query.isFetching || query.isError)}
          summary={summary}
          documents={documents}
          ownership={ownership}
          actor={actor}
          busy={isBusy || mutationBlocked || confirmationUnknown}
          error={error}
          onConfirm={() => void runMutation(
            () => confirmZeroTouchTargetDispatch(caseId, {
              expected_automation_version: summary.version,
              expected_clm_version: summary.clm.version,
              expected_case_event_count: summary.case.events.length,
            }),
            "Confirming reviewed target dispatch…",
            "target-confirmation",
          )}
          statusChecking={currentTargetStatusCheck?.checking}
          statusCheckResult={currentTargetStatusCheck?.result}
          statusCheckError={currentTargetStatusCheck?.error}
          onCheckStatus={canCheckTargetStatus && completedVerification ? () => void runTargetStatusCheck(false) : undefined}
          onSaveDraft={onBack}
          onReviewOutstanding={() => focusEvidence("recovery")}
          onEditIdentity={() => editFromFinalReview("identity")}
          onEditClassification={() => editFromFinalReview("classification")}
          onEditDocuments={() => editFromFinalReview("documents")}
          onEditOwnership={() => editFromFinalReview("ownership")}
        /> : <StageDisclosure title="Final review & send" status={stageStatusFor(summary, ["FINAL_REVIEW_SEND"])} summary={finalHeaderContext + (remainingIssueCount > 0 ? `Not yet available — ${remainingIssueCount} remaining issues.` : "Not yet available — complete the current stage.")} scopeKey={disclosureIdentity} final
          main={<>{finalReadNotice}<p>{remainingIssueCount > 0
            ? `Not yet available — resolve ${remainingIssueCount} remaining issues.`
            : "Not yet available — complete the current stage."}</p></>}
        /> }
        <StageDisclosure title="Historical / resolved issues">
          {renderInterventions(undefined, true)}
          <DetailedProcessingInspector key={`${summary.case.case_id}:${summary.automation_id}`} summary={summary} />
        <h4 style={{ marginTop: 24 }}>Automation timeline</h4><div className="table-card"><table className="table"><thead><tr><th>Timestamp</th><th>Stage</th><th>Event</th><th>Outcome</th></tr></thead><tbody>{summary.timeline.map((event) => <tr key={event.sequence}><td>{formatTimestamp(event.timestamp)}</td><td>{event.stage}</td><td>{event.message}</td><td>{event.outcome}</td></tr>)}</tbody></table></div>          {intelligence && <details className="evidence-details"><summary>Advisory intelligence</summary><IntelligencePanel record={intelligence} /></details>}
        </StageDisclosure>
      </div>
      </OnboardingWorkspace>

      {deleteDialogOpen && isCurrentCaseAction(deleteDialogOpen) && <DeleteCaseDialog caseId={deleteDialogOpen.caseId} companyName={entity?.legal_name ?? summary.case.requested_uen} requestedUen={summary.case.requested_uen} mutationDisabled={isBusy || mutationBlocked} onCancel={() => setDeleteDialogOpen(null)} onConfirm={() => deleteCase(deleteDialogOpen)} />}
    </div>
  );
}
