import type { QueryClient } from "@tanstack/react-query";

import {
  fetchDashboard,
  fetchCasePortfolio,
  fetchCaseActivity,
  fetchDocuments,
  fetchExecutionProfile,
  fetchOwnership,
  fetchPolicies,
  fetchIntelligence,
  fetchZeroTouchCase,
  fetchZeroTouchCases,
  type DashboardDateRange,
  type PriorityFilter,
  type PrioritySort,
  type CaseActivityFilters,
  type CasePortfolioFilters,
} from "./api";
import { fetchDashboardInsights, type DashboardInsightsRequest } from "./aiAssistant";
import type {
  AuthenticatedProfile,
  AutomationStatus,
  BusinessExceptionType,
  DashboardSnapshot,
  CasePortfolioPage,
  ZeroTouchCaseListItem,
  ZeroTouchCaseSummary,
  DocumentProcessingRecord,
} from "./types";

const absent = "all";

function dashboardTeamScope(teamFilter?: string): string {
  return teamFilter ?? absent;
}

type ActivityActorScope = Pick<AuthenticatedProfile, "role" | "team_id">;

/** Rows per Cases tab page; the session prefetch requests the same first page. */
export const CASES_PAGE_SIZE = 10;

export const caseQueryKeys = {
  auth: (userId: string) => ["auth", userId] as const,
  policyCatalogue: (userId: string) => ["auth", userId, "policies"] as const,
  dashboardInsights: (userId: string, request: DashboardInsightsRequest) => ["auth", userId, "dashboard-insights", request] as const,
  dashboards: (userId: string) => ["auth", userId, "dashboard"] as const,
  dashboard: (userId: string, teamFilter?: string, scope?: "team" | "mine", dateRange?: DashboardDateRange) => [
    ...caseQueryKeys.dashboards(userId),
    { teamFilter: dashboardTeamScope(teamFilter), scope: scope ?? "team", dateRange: dateRange ?? "30d" },
  ] as const,
  caseLists: (userId: string) => ["auth", userId, "cases", "list"] as const,
  casePortfolio: (userId: string, filters: CasePortfolioFilters) => [
    ...caseQueryKeys.caseLists(userId),
    "page",
    {
      status: filters.status ?? absent,
      progress: filters.progress ?? absent,
      priorityFilter: filters.priority,
      prioritySort: filters.prioritySort,
      teamFilter: filters.teamFilter ?? absent,
      attentionType: filters.attentionType ?? absent,
      jurisdiction: filters.jurisdiction ?? absent,
      search: filters.search?.trim() || absent,
      createdFrom: filters.createdFrom || absent,
      createdTo: filters.createdTo || absent,
      offset: filters.offset ?? 0,
      limit: filters.limit ?? 50,
    },
  ] as const,
  caseList: (
    userId: string,
    status: AutomationStatus | undefined,
    priority: PriorityFilter,
    prioritySort: PrioritySort,
    teamFilter?: string,
    attentionType?: BusinessExceptionType,
    createdFrom?: string,
    createdTo?: string,
  ) => ["auth", userId, "cases", "list", {
    status: status ?? absent,
    priorityFilter: priority,
    prioritySort,
    teamFilter: teamFilter ?? absent,
    attentionType: attentionType ?? absent,
    createdFrom: createdFrom || absent,
    createdTo: createdTo || absent,
  }] as const,
  caseResources: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "resources", caseId] as const,
  detail: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "detail", caseId] as const,
  documents: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "documents", caseId] as const,
  ownership: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "ownership", caseId] as const,
  intelligence: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "intelligence", caseId] as const,
  activities: (userId: string) => ["auth", userId, "activity"] as const,
  activity: (userId: string, filters: CaseActivityFilters, actorScope?: ActivityActorScope) => [
    ...caseQueryKeys.activities(userId),
    {
      caseId: filters.caseId ?? absent,
      teamFilter: filters.teamFilter ?? absent,
      action: filters.action ?? absent,
      stage: filters.stage ?? absent,
      outcome: filters.outcome ?? absent,
      from: filters.from ?? absent,
      to: filters.to ?? absent,
      createdBy: filters.createdBy ?? absent,
      actorRole: actorScope?.role ?? absent,
      actorTeam: actorScope?.team_id ?? absent,
      offset: filters.offset ?? 0,
      limit: filters.limit ?? 50,
    },
  ] as const,
  executionProfile: (userId: string) =>
    ["auth", userId, "system", "execution-profile"] as const,
};

export function dashboardQueryOptions(userId: string, teamFilter?: string, scope: "team" | "mine" = "team", dateRange: DashboardDateRange = "30d") {
  const team = dashboardTeamScope(teamFilter);
  return {
    queryKey: caseQueryKeys.dashboard(userId, team, scope, dateRange),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchDashboard(team, scope, dateRange, signal),
  };
}

export function caseListQueryOptions(
  userId: string,
  status: AutomationStatus | undefined,
  priority: PriorityFilter,
  prioritySort: PrioritySort,
  teamFilter?: string,
  attentionType?: BusinessExceptionType,
  createdFrom?: string,
  createdTo?: string,
) {
  return {
    queryKey: caseQueryKeys.caseList(
      userId,
      status,
      priority,
      prioritySort,
      teamFilter,
      attentionType,
      createdFrom,
      createdTo,
    ),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      fetchZeroTouchCases(status, priority, prioritySort, teamFilter, signal, attentionType, createdFrom, createdTo),
  };
}

export function casePortfolioQueryOptions(
  userId: string,
  filters: CasePortfolioFilters,
) {
  return {
    queryKey: caseQueryKeys.casePortfolio(userId, filters),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchCasePortfolio(filters, signal),
  };
}

export function caseDetailQueryOptions(userId: string, caseId: string) {
  return {
    queryKey: caseQueryKeys.detail(userId, caseId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchZeroTouchCase(caseId, signal),
    structuralSharing: (current: unknown, incoming: unknown) => retainNewestCaseSummary(
      current as ZeroTouchCaseSummary | undefined, incoming as ZeroTouchCaseSummary,
    ),
  };
}

export function documentQueryOptions(userId: string, caseId: string) {
  return {
    queryKey: caseQueryKeys.documents(userId, caseId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchDocuments(caseId, signal),
    structuralSharing: (current: unknown, incoming: unknown) => retainNewestDocuments(
      current as DocumentProcessingRecord[] | undefined, incoming as DocumentProcessingRecord[],
    ),
  };
}

export function ownershipQueryOptions(userId: string, caseId: string) {
  return {
    queryKey: caseQueryKeys.ownership(userId, caseId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchOwnership(caseId, signal),
    structuralSharing: retainNewestVersionedEvidence,
  };
}

export function intelligenceQueryOptions(userId: string, caseId: string) {
  return {
    queryKey: caseQueryKeys.intelligence(userId, caseId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchIntelligence(caseId, signal),
    structuralSharing: retainNewestVersionedEvidence,
  };
}

export function activityQueryOptions(userId: string, filters: CaseActivityFilters, actorScope?: ActivityActorScope) {
  return {
    queryKey: caseQueryKeys.activity(userId, filters, actorScope),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchCaseActivity(filters, signal),
  };
}

/**
 * ADR-015 AI insights for exactly these findings. Identical findings reuse the cached reply,
 * failures are not retried (the panel stays hidden), and it never refetches on its own.
 */
export function dashboardInsightsQueryOptions(userId: string, request: DashboardInsightsRequest) {
  return {
    queryKey: caseQueryKeys.dashboardInsights(userId, request),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchDashboardInsights(request, signal),
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: 30 * 60_000,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  };
}

/** Read-only policy catalogue for the Director's pending-approval count on the Dashboard. */
export function policyCatalogueQueryOptions(userId: string) {
  return {
    queryKey: caseQueryKeys.policyCatalogue(userId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchPolicies(signal),
  };
}

export function executionProfileQueryOptions(userId: string) {
  return {
    queryKey: caseQueryKeys.executionProfile(userId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchExecutionProfile(signal),
  };
}

export function prefetchSessionQueries(
  queryClient: QueryClient,
  profile: AuthenticatedProfile,
): void {
  if (!profile.capabilities.includes("CASE_ACCESS")) return;
  void queryClient.prefetchQuery(dashboardQueryOptions(profile.user_id, absent));
  void queryClient.prefetchQuery(
    casePortfolioQueryOptions(profile.user_id, {
      priority: "all",
      prioritySort: "highest_first",
      teamFilter: "all",
      offset: 0,
      limit: CASES_PAGE_SIZE,
    }),
  );
}

export function publishCaseDetail(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): void {
  queryClient.setQueryData(
    caseQueryKeys.detail(userId, summary.case.case_id),
    (current: ZeroTouchCaseSummary | undefined) => retainNewestCaseSummary(current, summary),
  );
}

export function retainNewestDocuments(
  current: DocumentProcessingRecord[] | undefined,
  incoming: DocumentProcessingRecord[],
): DocumentProcessingRecord[] {
  if (!current) return incoming;
  const next = new Map(incoming.map((document) => [document.document_id, document]));
  return current.some((document) => {
    const updated = next.get(document.document_id);
    if (!updated || updated.events.length < document.events.length) return true;
    // Supersession adds a durable event; historical projections clear current reconciliation.
    const replacement = updated.superseded_by_document_id
      ? next.get(updated.superseded_by_document_id) : undefined;
    const boundSupersession = updated.events.length > document.events.length
      && updated.reconciliation_version === null
      && replacement?.supersedes_document_id === document.document_id;
    return !boundSupersession
      && (updated.reconciliation_version ?? 0) < (document.reconciliation_version ?? 0);
  }) ? current : incoming;
}

export function retainNewestVersionedEvidence(current: unknown, incoming: unknown): unknown {
  const previous = current as { version?: number } | null | undefined;
  const next = incoming as { version?: number } | null | undefined;
  return previous && (!next || (next.version ?? 0) < (previous.version ?? 0)) ? current : incoming;
}

function retainNewestCaseSummary(
  current: ZeroTouchCaseSummary | undefined, incoming: ZeroTouchCaseSummary,
): ZeroTouchCaseSummary {
  if (current && (
    (current.version ?? 0) > (incoming.version ?? 0)
    || (current.case.events?.length ?? 0) > (incoming.case.events?.length ?? 0)
    || (current.clm?.version ?? 0) > (incoming.clm?.version ?? 0)
  )) return current;
  return incoming;
}

export function caseCreatedEffect(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): void {
  publishCaseDetail(queryClient, userId, summary);
  void queryClient.invalidateQueries({ queryKey: caseQueryKeys.caseLists(userId) });
  queryClient.removeQueries({ queryKey: caseQueryKeys.dashboards(userId) });
  void queryClient.invalidateQueries({ queryKey: caseQueryKeys.activities(userId) });
}

export function caseSummaryMutationEffect(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): void {
  const current = queryClient.getQueryData<ZeroTouchCaseSummary>(
    caseQueryKeys.detail(userId, summary.case.case_id),
  );
  if (current && current.version > summary.version) return;
  publishCaseMutationScopes(queryClient, userId, summary);
  void queryClient.invalidateQueries({
    queryKey: caseQueryKeys.intelligence(userId, summary.case.case_id),
    exact: true,
  });
}

function publishCaseMutationScopes(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): void {
  publishCaseDetail(queryClient, userId, summary);
  void queryClient.invalidateQueries({ queryKey: caseQueryKeys.caseLists(userId) });
  queryClient.removeQueries({ queryKey: caseQueryKeys.dashboards(userId) });
  void queryClient.invalidateQueries({ queryKey: caseQueryKeys.activities(userId) });
}

export function targetConfirmationMutationEffect(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): void {
  void queryClient.cancelQueries({
    queryKey: caseQueryKeys.detail(userId, summary.case.case_id),
    exact: true,
  });
  caseSummaryMutationEffect(queryClient, userId, summary);
}

export function identitySearchRecheckMutationEffect(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): void {
  caseSummaryMutationEffect(queryClient, userId, summary);
}

export async function manualOwnershipMutationEffect(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): Promise<void> {
  await caseSupportingMutationEffect(queryClient, userId, summary);
}

export function policyRebindMutationEffect(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): void {
  caseSummaryMutationEffect(queryClient, userId, summary);
}

export async function caseSupportingMutationEffect(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
  retireIdentityEvidence = false,
): Promise<void> {
  const supportingKeys = [
    caseQueryKeys.documents(userId, summary.case.case_id),
    caseQueryKeys.ownership(userId, summary.case.case_id),
    caseQueryKeys.intelligence(userId, summary.case.case_id),
  ];
  await Promise.all([
    caseQueryKeys.detail(userId, summary.case.case_id),
    ...supportingKeys,
  ].map((queryKey) => queryClient.cancelQueries({ queryKey, exact: true })));
  if (retireIdentityEvidence) {
    // Reset before publishing the rebound identity: null/lower-version responses
    // must not share the previous identity's monotonic evidence baseline.
    const refreshed = Promise.all(supportingKeys.map((queryKey) =>
      queryClient.resetQueries({ queryKey, exact: true }),
    ));
    publishCaseMutationScopes(queryClient, userId, summary);
    await refreshed;
    return;
  }
  publishCaseMutationScopes(queryClient, userId, summary);
  const caseId = summary.case.case_id;
  await Promise.all([
    queryClient.invalidateQueries({
      queryKey: caseQueryKeys.documents(userId, caseId),
      exact: true,
    }),
    queryClient.invalidateQueries({
      queryKey: caseQueryKeys.ownership(userId, caseId),
      exact: true,
    }),
    queryClient.invalidateQueries({
      queryKey: caseQueryKeys.intelligence(userId, caseId),
      exact: true,
    }),
  ]);
}

export async function priorityMutationEffect(
  queryClient: QueryClient,
  userId: string,
): Promise<void> {
  queryClient.removeQueries({
    queryKey: caseQueryKeys.caseLists(userId),
    type: "inactive",
  });
  await queryClient.invalidateQueries({
    queryKey: caseQueryKeys.caseLists(userId),
    type: "active",
  });
  queryClient.removeQueries({ queryKey: caseQueryKeys.dashboards(userId) });
  await queryClient.invalidateQueries({ queryKey: caseQueryKeys.activities(userId) });
}

export async function caseDeletedEffect(
  queryClient: QueryClient,
  userId: string,
  caseId: string,
): Promise<void> {
  await Promise.all([
    queryClient.cancelQueries({ queryKey: caseQueryKeys.caseLists(userId) }),
    queryClient.cancelQueries({
      queryKey: caseQueryKeys.dashboards(userId),
    }),
    queryClient.cancelQueries({
      queryKey: caseQueryKeys.detail(userId, caseId),
      exact: true,
    }),
    queryClient.cancelQueries({
      queryKey: caseQueryKeys.documents(userId, caseId),
      exact: true,
    }),
    queryClient.cancelQueries({
      queryKey: caseQueryKeys.ownership(userId, caseId),
      exact: true,
    }),
    queryClient.cancelQueries({
      queryKey: caseQueryKeys.intelligence(userId, caseId),
      exact: true,
    }),
    queryClient.cancelQueries({ queryKey: caseQueryKeys.activities(userId) }),
  ]);
  queryClient.setQueriesData<ZeroTouchCaseListItem[] | CasePortfolioPage>(
    { queryKey: caseQueryKeys.caseLists(userId) },
    (current) => {
      if (current === undefined) return current;
      if (Array.isArray(current)) {
        return current.filter((item) => item.case_id !== caseId);
      }
      return {
        ...current,
        items: current.items.filter((item) => item.case_id !== caseId),
      };
    },
  );
  queryClient.removeQueries({ queryKey: caseQueryKeys.detail(userId, caseId), exact: true });
  queryClient.removeQueries({ queryKey: caseQueryKeys.documents(userId, caseId), exact: true });
  queryClient.removeQueries({ queryKey: caseQueryKeys.ownership(userId, caseId), exact: true });
  queryClient.removeQueries({
    queryKey: caseQueryKeys.intelligence(userId, caseId),
    exact: true,
  });
  queryClient.removeQueries({ queryKey: caseQueryKeys.dashboards(userId) });
  queryClient.removeQueries({ queryKey: caseQueryKeys.activities(userId) });
  await queryClient.invalidateQueries({
    queryKey: caseQueryKeys.caseLists(userId),
    type: "active",
  });
}

export function cachedDashboard(
  queryClient: QueryClient,
  userId: string,
  teamFilter?: string,
): DashboardSnapshot | undefined {
  return queryClient.getQueryData(caseQueryKeys.dashboard(userId, teamFilter));
}
