import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  ApiError,
  checkZeroTouchTargetStatus,
  type TargetStatusCheckResult,
  confirmZeroTouchTargetDispatch,
  correctRegistryIdentity,
  deleteZeroTouchCase,
  fetchDocuments,
  fetchIntelligence,
  fetchOwnership,
  fetchZeroTouchCase,
  intakeZeroTouchDocument,
  replaceZeroTouchDocument,
  recheckZeroTouchIdentitySearch,
  rebindZeroTouchPolicy,
  submitManualOwnershipEvidence,
  reviewDocument,
  resolveZeroTouchException,
  resumeZeroTouchCase,
  retryZeroTouchIntakeDocument,
  updateCasePriority,
  updateGoldTierTargetClassification,
} from "../api";
import { startAutomationPolling } from "../automationPolling";
import {
  caseDeletedEffect,
  publishCaseDetail,
  retainNewestDocuments,
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
import { formatTimestamp, shouldPollAutomation, targetOutcomeLabel } from "../shared";
import type {
  DocumentProcessingRecord,
  AuthenticatedProfile,
  OwnershipAnalysisRecord,
  ProcessingNode,
  SimulationProfile,
  ZeroTouchCaseSummary,
} from "../types";
import {
  CompletedOverview,
  ConfirmDetailsPanel,
  DetailedProcessingInspector,
  findProcessingNode,
  OnboardingProgressPanel,
  OperationalTiming,
  PipelineRail,
  processingNodeFocusTarget,
  ProcessingBlockerPanels,
  RegistryStatePanel,
} from "./CaseStatePanels";
import CaseStateExplanationPanel, { type EvidenceFocusTarget } from "./CaseStateExplanationPanel";
import PriorityControl, { PriorityBadge } from "./PriorityControl";
import DeleteCaseDialog from "./DeleteCaseDialog";
import DocumentEvidencePanel, { type DocumentReviewRequest } from "./DocumentEvidencePanel";
import OwnershipPathExplorer from "./OwnershipPathExplorer";
import IntelligencePanel from "./IntelligencePanel";
import GoldTierRequestPreview from "./GoldTierRequestPreview";
import RegistryProvenancePanel from "./RegistryProvenancePanel";
import TargetClassificationPanel from "./TargetClassificationPanel";
import HumanInterventionPanel from "./HumanInterventionPanel";
import ReviewAndSend from "./ReviewAndSend";
import StageDisclosure, { revealStage } from "./StageDisclosure";
import OnboardingWorkspace, { onboardingExecutionMessage, onboardingIsExecuting } from "./OnboardingWorkspace";
import IdentityCorrectionForm from "./IdentityCorrectionForm";
import ManualOwnershipEvidenceForm from "./ManualOwnershipEvidenceForm";
import PolicyRebindPanel from "./PolicyRebindPanel";

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
const MANUAL_OWNERSHIP_TARGET_ID = "case-manual-ownership-evidence";

interface CaseActionIdentity {
  readonly generation: number;
  readonly caseId: string;
  readonly actorUserId: string;
}

interface RetainedTargetStatusCheck {
  attempted: true;
  result: TargetStatusCheckResult | null;
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

export function shouldRefreshAfterMutationError(error: unknown): boolean {
  return error instanceof TypeError || (error instanceof ApiError && [409, 503].includes(error.status));
}

export default function CaseDetail({
  caseId,
  actor,
  onBack,
  onViewOnboarded,
  onViewAudit,
  registryProviderMode,
  initialFocusNodeId,
}: {
  caseId: string;
  actor: AuthenticatedProfile;
  onBack: () => void;
  onViewOnboarded: (caseId: string) => void;
  onViewAudit: (caseId: string) => void;
  registryProviderMode?: SimulationProfile["registry_provider_mode"];
  initialFocusNodeId?: string;
}) {
  const queryClient = useQueryClient();
  const evidenceIdentity = `${actor.user_id}:${caseId}`;
  const detailQuery = useQuery(caseDetailQueryOptions(actor.user_id, caseId));
  const documentQuery = useQuery(documentQueryOptions(actor.user_id, caseId));
  const ownershipQuery = useQuery(ownershipQueryOptions(actor.user_id, caseId));
  const intelligenceQuery = useQuery(intelligenceQueryOptions(actor.user_id, caseId));
  const summary = detailQuery.data ?? null;
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
  const targetSubmission = summary?.target_submission;
  const targetSubmissionId = targetSubmission?.submission_id ?? null;
  const targetStatusIdentity = `${evidenceIdentity}:${targetSubmissionId ?? "none"}`;
  const canCheckTargetStatus = targetSubmission?.state === "SUBMISSION_OUTCOME_UNCERTAIN"
    && targetSubmission.status_check_available
    && targetSubmissionId !== null
    && actor.capabilities.includes("CASE_ACCESS")
    && !caseUnavailable && !mutationBlocked && !detailQuery.isError;
  const generation = useRef(0);
  const mounted = useRef(false);
  const mutationPending = useRef<CaseActionIdentity | null>(null);
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
    const latestDocuments = fetchDocuments(action.caseId).then((documents) => {
      if (isCurrentCaseAction(action)) {
        queryClient.setQueryData(
          documentQueryOptions(action.actorUserId, action.caseId).queryKey,
          (current: DocumentProcessingRecord[] | undefined) => retainNewestDocuments(current, documents),
        );
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
      generation.current += 1;
      targetStatusController.current?.abort();
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
    mutationPending.current = null;
    return () => {
      generation.current = current + 1;
      targetStatusController.current?.abort();
    };
  }, [actor.user_id, caseId]);

  const runTargetStatusCheck = useCallback(async (automatic: boolean) => {
    if (!canCheckTargetStatus || !targetSubmissionId || isBusy || mutationPending.current
      || targetStatusController.current) return;
    const action = captureCaseAction();
    const key = [
      ...caseDetailQueryOptions(action.actorUserId, action.caseId).queryKey,
      "target-status-check", targetSubmissionId,
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
      const result = await checkZeroTouchTargetStatus(action.caseId, targetSubmissionId, controller.signal);
      if (controller.signal.aborted || !isCurrentCaseAction(action)) return;
      const next: RetainedTargetStatusCheck = result.submission_id === targetSubmissionId
        ? { attempted: true, result, error: null }
        : { attempted: true, result: null, error: "The status check did not match this submission. The retained outcome remains uncertain." };
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
        error: "GoldTier status could not be checked. The retained submission outcome remains uncertain.",
      };
      if (!(checkError instanceof ApiError && [401, 403, 404].includes(checkError.status))) {
        queryClient.setQueryData(key, next);
      }
      setTargetStatusCheck({ ...next, identity: targetStatusIdentity, checking: false });
    } finally {
      if (targetStatusController.current === controller) targetStatusController.current = null;
    }
  }, [actor.user_id, caseId, queryClient, canCheckTargetStatus, targetSubmissionId, targetStatusIdentity, isBusy]);

  useEffect(() => {
    const key = [
      ...caseDetailQueryOptions(actor.user_id, caseId).queryKey,
      "target-status-check", targetSubmissionId,
    ];
    const retained = targetSubmissionId
      ? queryClient.getQueryData<RetainedTargetStatusCheck>(key) : undefined;
    setTargetStatusCheck(retained ? { ...retained, identity: targetStatusIdentity, checking: false } : null);
    return () => {
      targetStatusController.current?.abort();
      targetStatusController.current = null;
    };
  }, [actor.user_id, caseId, queryClient, targetSubmissionId, targetStatusIdentity, targetSubmission?.state, canCheckTargetStatus]);

  useEffect(() => {
    if (canCheckTargetStatus) void runTargetStatusCheck(true);
  }, [canCheckTargetStatus, runTargetStatusCheck]);

  useEffect(() => {
    if (!summary || !shouldPollAutomation(summary.status)) return;
    const activeGeneration = generation.current;
    return startAutomationPolling({
      caseId,
      generation: activeGeneration,
      currentGeneration: () => generation.current,
      fetchCase: fetchZeroTouchCase,
      onUpdate: (latest) => {
        caseSummaryMutationEffect(queryClient, actor.user_id, latest);
        void Promise.all([fetchDocuments(caseId), fetchOwnership(caseId)]).then(([docs, owner]) => {
          if (activeGeneration === generation.current) {
            queryClient.setQueryData(documentQueryOptions(actor.user_id, caseId).queryKey,
              (current: DocumentProcessingRecord[] | undefined) => retainNewestDocuments(current, docs));
            queryClient.setQueryData(ownershipQueryOptions(actor.user_id, caseId).queryKey,
              (current: unknown) => retainNewestVersionedEvidence(current, owner));
          }
        });
      },
      onWarning: (warning) => setError(warning),
      shouldContinue: shouldPollAutomation,
    });
  }, [actor.user_id, caseId, queryClient, summary?.status, summary?.version]);

  useEffect(() => {
    if (!summary) return;
    const requestedNodeId = initialFocusNodeId;
    if (!requestedNodeId) return;
    const focusIdentity = `${evidenceIdentity}:${requestedNodeId}`;
    if (lastNavigationFocus.current === focusIdentity) return;
    const node = findProcessingNode(summary.processing_pipeline ?? [], requestedNodeId);
    if (!node || !processingNodeFocusTarget(node)) return;
    lastNavigationFocus.current = focusIdentity;
    focusProcessingNode(node);
  }, [evidenceIdentity, initialFocusNodeId, summary?.version]);

  async function runMutation(
    operation: () => Promise<ZeroTouchCaseSummary>,
    label = "Saving case action…",
    effect: "supporting" | "target-confirmation" | "identity-recheck" | "registry-identity" | "manual-ownership" | "policy-rebind" = "supporting",
  ) {
    let action = captureCaseAction();
    if (mutationPending.current || mutationBlocked) return;
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
    } catch (mutationError) {
      if (!isCurrentCaseAction(action)) return;
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
        await refreshEvidence(action);
        if (!isCurrentCaseAction(action)) return;
        setMutationBlocked(false);
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
      () => replaceZeroTouchDocument(caseId, document.document_id, document.events.length, file),
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

  function focusEvidence(target: EvidenceFocusTarget): void {
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

  function focusManualOwnership(): void {
    const section = document.getElementById(MANUAL_OWNERSHIP_TARGET_ID);
    if (!section) {
      setEvidenceFocusNotice({
        identity: evidenceIdentity,
        message: "Manual ownership evidence is not authorized for the current case state.",
      });
      return;
    }
    setEvidenceFocusNotice(null);
    revealStage(section);
    section.focus({ preventScroll: true });
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    section.scrollIntoView?.({ block: "start", behavior: reducedMotion ? "auto" : "smooth" });
  }

  function focusProcessingNode(node: ProcessingNode): void {
    const targetId = processingNodeFocusTarget(node);
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
    window.setTimeout(() => {
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
    }, 50);
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

  const loadError = detailQuery.error ?? documentQuery.error ?? ownershipQuery.error;
  if (caseUnavailable) return <div className="ds-root ds-page"><button type="button" className="btn btn-ghost" onClick={onBack}>← Back to Cases</button><div className="ds-banner ds-banner-warn">The case is unavailable.</div></div>;
  if ((error || loadError) && !summary) return <div className="ds-root ds-page"><button type="button" className="btn btn-ghost" onClick={onBack}>← Back to Cases</button><div className="ds-banner ds-banner-warn">{error ?? (loadError instanceof Error ? loadError.message : "The case is unavailable.")}</div></div>;
  if (!summary) return <div className="ds-root ds-page"><p className="text-muted">Loading case…</p></div>;

  const entity = summary.case.entity;
  const acquisition = summary.case.registry_acquisition;
  const ownershipRecovery = summary.ownership_recovery;
  const identityIncomplete = summary.active_exceptions.some(
    (exception) => exception.blocker_code === "INITIAL_IDENTITY_INCOMPLETE",
  );
  const identityEditable = summary.evidence_decision_authorized === true
    && summary.status !== "COMPLETED"
    && !summary.case.goldtier_result
    && !summary.case.target_dispatch_confirmation
    && !summary.clm.submission;
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

  const renderInterventions = (stages?: readonly string[], historyOnly = false) => (
        <HumanInterventionPanel
          summary={summary}
          stages={stages}
          historyOnly={historyOnly}
          isBusy={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true}
          onEvidenceAction={(target) => {
            const targetIds = {
              DOCUMENTS: EVIDENCE_TARGET_IDS.documents,
              OWNERSHIP_DETAILS: MANUAL_OWNERSHIP_TARGET_ID,
              OWNERSHIP_UPLOAD: "case-ownership-evidence-upload",
              CLASSIFICATION: EVIDENCE_TARGET_IDS.classification,
              IDENTITY: EVIDENCE_TARGET_IDS.identity,
              REVIEW_SEND: "case-review-and-send",
            };
            const element = document.getElementById(targetIds[target]);
            if (element) revealStage(element);
            element?.scrollIntoView({ behavior: "smooth", block: "start" });
            requestAnimationFrame(() => element?.focus({ preventScroll: true }));
          }}
          onResolve={(exception, action) => void runMutation(
            () => resolveZeroTouchException(
              summary,
              exception.exception_id,
              action,
              exception.evidence_version,
            ),
          )}
        />

  );
  const stageIsActive = (stages: readonly string[]) => summary.status !== "COMPLETED"
    && stages.includes(summary.interventions?.find((item) => item.blocker_code !== "TARGET_CONFIRMATION_REQUIRED")?.owning_stage ?? summary.current_stage ?? "REGISTRY");
  const reviewReady = summary.active_exceptions.some((item) => item.exception_type === "TARGET_CONFIRMATION_REQUIRED");
  const frozenReview = Boolean(summary.case.target_dispatch_confirmation || summary.clm.submission
    || (targetSubmission && targetSubmission.state !== "NOT_SUBMITTED"));
  const showFinalReview = reviewReady || frozenReview || summary.status === "COMPLETED";
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
    return unresolved && uen && uen !== summary.case.requested_uen && field?.review_status !== "REJECTED"
      ? [{ uen, documentId: item.document_id, eventCount: item.events.length }] : [];
  });
  const identityConflict = identityEditable && documentUenCandidates.length > 0;

  return (
    <div className="ds-root detail-layout">
      <div className="side-panel case-pipeline-panel">
        <button type="button" className="btn btn-ghost" onClick={onBack} style={{ paddingLeft: 0 }}>← Back to Cases</button>
        <h4 style={{ marginTop: 16 }}>Pipeline</h4>
        <PipelineRail summary={summary} />
        <hr className="hr" />
        <div className="text-muted" style={{ fontSize: 11.5 }}>
          Loop —
        </div>
      </div>

      <OnboardingWorkspace active={onboardingIsExecuting(summary, isBusy, error ?? (loadError ? "Evidence load failed" : null))} message={onboardingExecutionMessage(summary, busyLabel)}>
      <div className="ds-page" style={{ flex: 1 }}>
        <div className="ds-page-header"><div><p className="card-kicker">{summary.case.requested_uen} · {summary.case.jurisdiction_resolution?.resolved_jurisdiction ?? "—"} · {summary.case.client_scope_label ?? "Legacy unassigned"}</p><h1>{entity?.legal_name ?? summary.case.requested_uen}</h1></div><div className="case-header-actions"><PriorityBadge priority={summary.case.priority} /><PriorityControl priority={summary.case.priority} disabled={isBusy || mutationBlocked} onSave={runPriorityMutation} />{(actor.role === "DIRECTOR" || actor.role === "RELATIONSHIP_MANAGER") && <button type="button" className="btn btn-danger" disabled={isBusy || mutationBlocked} onClick={() => { if (!mutationPending.current && !mutationBlocked) setDeleteDialogOpen(captureCaseAction()); }}>Delete case</button>}<span className="tag tag-accent-2">{summary.status.replaceAll("_", " ")}</span></div></div>
        {error && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}>{error}</div>}

        <OnboardingProgressPanel
          summary={summary}
          onStageActivate={focusProcessingNode}
          availableFocusTargets={availableFocusTargets}
          initialFocusNodeId={initialFocusNodeId}
        />


        {isBusy && busyLabel && (
          <div className="ds-banner case-action-progress" role="status" aria-live="polite"
            style={{ position: "fixed", bottom: 16, left: 16, right: 16, margin: "0 auto", maxWidth: 420, zIndex: 30 }}>
            {busyLabel}
          </div>
        )}

        <StageDisclosure title="Registry verification" active={identityConflict || stageIsActive(["REGISTRY", "GOLDTIER_SEARCH"])}>
          {renderInterventions(["REGISTRY", "GOLDTIER_SEARCH"])}
        {(identityIncomplete || identityEditable) && (
          <div
            key={`${evidenceIdentity}:identity:${summary.version}`}
            id={EVIDENCE_TARGET_IDS.identity}
            className="evidence-focus-target"
            tabIndex={-1}
          >
            <IdentityCorrectionForm
              onboardingCase={summary.case}
              registryRecovery={!identityIncomplete}
              documentCandidates={documentUenCandidates}
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
                  return identityIncomplete
                    ? recheckZeroTouchIdentitySearch(caseId, identityInput)
                    : correctRegistryIdentity(caseId, {
                        ...identityInput, choice: values.choice ?? "OTHER",
                        document_id: values.document_id,
                        expected_document_event_count: values.expected_document_event_count,
                      });
                },
                "Verifying company identity and resuming…",
                identityIncomplete ? "identity-recheck" : "registry-identity",
              )}
            />
          </div>
        )}

        <RegistryStatePanel summary={summary} registryProviderMode={registryProviderMode} />
        <ProcessingBlockerPanels summary={summary} stage="REGISTRY" />
        <div key={`${evidenceIdentity}:registry`} id={EVIDENCE_TARGET_IDS.registry} className="evidence-focus-target" tabIndex={-1}>
          <RegistryProvenancePanel acquisition={acquisition} binding={summary.case.registry_evidence_binding} entityType={entity?.party_type} providerMode={registryProviderMode} />
        </div>
        <div className="ds-two-col case-corporate-evidence"><div><h4>Corporate particulars</h4><div>
          <div className="kv-row"><span className="kv-label">Company name</span><span className="kv-value">{entity?.legal_name ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registration ID</span><span className="kv-value">{entity?.registration_number ?? summary.case.requested_uen}</span></div><div className="kv-row"><span className="kv-label">Entity type</span><span className="kv-value">{entity?.party_type ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registry status</span><span className="kv-value">{entity?.entity_status ?? "—"}</span></div><div className="kv-row"><span className="kv-label">Registration date</span><span className="kv-value">{entity?.registration_date ?? "—"}</span></div>
        </div></div><div><h4>Registry officers and roles</h4>{acquisition && acquisition.officers.length > 0 ? <div className="table-card"><table className="table"><tbody>{acquisition.officers.map((officer) => <tr key={officer.officer_id}><td>{officer.name}</td><td>{officer.role}</td></tr>)}</tbody></table></div> : <p className="text-muted" style={{ fontSize: 12 }}>Not available.</p>}</div></div>

        {acquisition && (
          <details className="evidence-details registry-evidence-details">
            <summary>Registry operation results, issues, and safe provenance</summary>
            {acquisition.operation_results.map((operation) => (
              <p key={operation.operation}><strong>{operation.operation.replaceAll("_", " ")}</strong> · {operation.status} · {operation.record_count} record(s) · {operation.provenance ? `${operation.provenance.provider} ${operation.provenance.environment} · ${operation.provenance.evidence_reference}` : "provenance —"}{operation.error ? ` · ${operation.error.code}: ${operation.error.message}` : ""}</p>
            ))}
            {acquisition.issues.map((issue) => <p key={issue.code}><strong>{issue.code}</strong> · {issue.message}</p>)}
          </details>
        )}

        </StageDisclosure>
        <StageDisclosure title="Document verification" active={!identityConflict && stageIsActive(["DOCUMENT"])}>
          {renderInterventions(["DOCUMENT"])}
        {summary.reconciliation && summary.current_stage === "DOCUMENT" && (
          <div key={`${evidenceIdentity}:reconciliation`} id={EVIDENCE_TARGET_IDS.reconciliation} className="evidence-focus-target" tabIndex={-1}>
            <ConfirmDetailsPanel summary={summary} isBusy={isBusy || mutationBlocked || summary.evidence_decision_authorized !== true} />
          </div>
        )}
        <div key={`${evidenceIdentity}:documents`} id={EVIDENCE_TARGET_IDS.documents} className="evidence-focus-target" tabIndex={-1}>
          <DocumentEvidencePanel key={evidenceIdentity} summary={summary} documents={documents} busy={isBusy} busyLabel={busyLabel} mutationBlocked={mutationBlocked} loading={documentQuery.isPending} loadFailed={documentQuery.isError} onReview={handleDocumentReview} onReplace={handleReplacement} onRetry={handleRetry} onContinue={handleContinueRecoveredIntake} onRefresh={() => void handleReadOnlyRefresh()} />
        </div>

        </StageDisclosure>
        <StageDisclosure title="Ownership & UBO" active={stageIsActive(["OWNERSHIP"])}>
          {renderInterventions(["OWNERSHIP"])}
        {ownershipRecovery && summary.ownership_edit_authorized === true
          && ownership?.analysis_id === ownershipRecovery.analysis_id
          && (ownership.version === undefined || ownership.version === ownershipRecovery.version) && (
          <div id={MANUAL_OWNERSHIP_TARGET_ID} className="evidence-focus-target" tabIndex={-1}>
            <ManualOwnershipEvidenceForm
              key={`${evidenceIdentity}:${ownershipRecovery.analysis_id}:${ownershipRecovery.version}:${ownership.analysis_id}:${ownership.version ?? "unknown"}:${documents.map((document) => `${document.document_id}:${document.events.length}`).join("|")}`}
              canonicalRootUen={summary.case.entity?.registration_number ?? summary.case.initial_identity?.registration_number ?? summary.case.requested_uen}
              initialRootLegalName={summary.case.entity?.legal_name ?? summary.case.initial_identity?.legal_name ?? ""}
              documents={documents}
              ownership={ownership}
              disabled={isBusy || mutationBlocked || summary.ownership_edit_authorized !== true}
              onUploadEvidence={(file) => void settleEvidenceMutation(
                () => intakeZeroTouchDocument(caseId, file, false),
                "Validating client-supplied ownership evidence…",
                "Ownership evidence could not be added.",
              )}
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
            <OwnershipPathExplorer key={`${evidenceIdentity}:${ownership?.analysis_id ?? "none"}`} record={ownership} acquisition={acquisition} primaryBlockerVisible={summary.active_exceptions.some((item) => item.stage === "OWNERSHIP")} />
          </div>
        </StageDisclosure>
        <StageDisclosure title="Readiness check" active={stageIsActive(["READINESS"])}>
          {renderInterventions(["READINESS"])}
        {summary.case.policy_rebind && (
          <PolicyRebindPanel
            metadata={summary.case.policy_rebind}
            registrationNumber={summary.case.entity?.registration_number ?? summary.case.initial_identity?.registration_number ?? summary.case.requested_uen}
            disabled={isBusy || mutationBlocked}
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
          <TargetClassificationPanel
            key={`${summary.case.case_id}:${summary.target_classification.vocabulary_version}:${summary.target_classification.kyc_customer_type.selected_value ?? "unresolved"}:${summary.target_classification.client_segment.selected_value ?? "unresolved"}`}
            classification={summary.target_classification}
            disabled={isBusy || mutationBlocked}
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
        </StageDisclosure>
        <StageDisclosure title="Preparing GoldTier Submission" active={stageIsActive(["MOCK_GOLDTIER"])}>
          {renderInterventions(["MOCK_GOLDTIER"])}
        <ProcessingBlockerPanels summary={summary} stage="TARGET" />
        {summary.status === "RECOVERY_PENDING"
          && (!targetSubmission || targetSubmission.state === "FINALIZATION_PENDING") && <div className="ds-banner" style={{ marginBottom: 16 }}><p style={{ margin: 0, fontSize: 12.5 }}>Backend recovery is pending; target operations will not be replayed by the browser.</p><button type="button" className="btn btn-primary" style={{ marginTop: 10 }} disabled={isBusy || mutationBlocked} onClick={() => void runMutation(() => resumeZeroTouchCase(caseId))}>Complete safe recovery</button></div>}
        {summary.status === "TECHNICAL_FAILURE" && summary.technical_failure && <div className="ds-banner ds-banner-warn" style={{ marginBottom: 16 }}><h3 style={{ marginTop: 0 }}>Automation stopped safely</h3><strong>{summary.technical_failure.code}</strong><p style={{ marginBottom: 0 }}>{summary.technical_failure.message}</p></div>}
        <CompletedOverview summary={summary} onViewOnboarded={onViewOnboarded} onViewAudit={onViewAudit} />
        <OperationalTiming summary={summary} />

          <details className="evidence-details"><summary>Backend execution details</summary>
          <div key={`${evidenceIdentity}:recovery`} id={EVIDENCE_TARGET_IDS.recovery} className="evidence-focus-target evidence-workbench-column" tabIndex={-1}>
            <CaseStateExplanationPanel summary={summary} onNavigate={focusEvidence} />
            {evidenceFocusNotice?.identity === evidenceIdentity && <p className="ds-banner ds-banner-warn" role="status">{evidenceFocusNotice.message}</p>}
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
          </div>          </details>
        </StageDisclosure>
        <StageDisclosure title="Historical / resolved issues">
          {renderInterventions(undefined, true)}
          <DetailedProcessingInspector key={`${summary.case.case_id}:${summary.automation_id}`} summary={summary} />
        <h4 style={{ marginTop: 24 }}>Automation timeline</h4><div className="table-card"><table className="table"><thead><tr><th>Timestamp</th><th>Stage</th><th>Event</th><th>Outcome</th></tr></thead><tbody>{summary.timeline.map((event) => <tr key={event.sequence}><td>{formatTimestamp(event.timestamp)}</td><td>{event.stage}</td><td>{event.message}</td><td>{event.outcome}</td></tr>)}</tbody></table></div>          {intelligence && <details className="evidence-details"><summary>Advisory intelligence</summary><IntelligencePanel record={intelligence} /></details>}
        </StageDisclosure>
        <StageDisclosure title="Final review & send" final active={showFinalReview}
          summary={!showFinalReview ? (
            remainingIssueCount > 0
              ? `Not yet available — resolve ${remainingIssueCount} remaining issues.`
              : "Not yet available — complete the current stage."
          ) : undefined}>
        {showFinalReview && <ReviewAndSend
          summary={summary}
          documents={documents}
          ownership={ownership}
          actor={actor}
          busy={isBusy || mutationBlocked}
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
          onCheckStatus={canCheckTargetStatus ? () => void runTargetStatusCheck(false) : undefined}
          onSaveDraft={onBack}
          onReviewOutstanding={() => focusEvidence("recovery")}
          onEditIdentity={() => focusEvidence("identity")}
          onEditClassification={() => focusEvidence("classification")}
          onEditDocuments={() => focusEvidence("documents")}
          onEditOwnership={focusManualOwnership}
        />}
        </StageDisclosure>
      </div>
      </OnboardingWorkspace>

      {deleteDialogOpen && isCurrentCaseAction(deleteDialogOpen) && <DeleteCaseDialog caseId={deleteDialogOpen.caseId} companyName={entity?.legal_name ?? summary.case.requested_uen} requestedUen={summary.case.requested_uen} mutationDisabled={isBusy || mutationBlocked} onCancel={() => setDeleteDialogOpen(null)} onConfirm={() => deleteCase(deleteDialogOpen)} />}
    </div>
  );
}
