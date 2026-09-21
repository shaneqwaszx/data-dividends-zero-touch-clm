import type { QueryClient } from "@tanstack/react-query";

import {
  fetchDashboard,
  fetchCaseActivity,
  fetchDocuments,
  fetchExecutionProfile,
  fetchOwnership,
  fetchZeroTouchCase,
  fetchZeroTouchCases,
  type PriorityFilter,
  type PrioritySort,
  type CaseActivityFilters,
} from "./api";
import type {
  AuthenticatedProfile,
  AutomationStatus,
  BusinessExceptionType,
  DashboardSnapshot,
  ZeroTouchCaseListItem,
  ZeroTouchCaseSummary,
} from "./types";

const absent = "all";

function dashboardTeamScope(teamFilter?: string): string {
  return teamFilter ?? absent;
}

export const caseQueryKeys = {
  auth: (userId: string) => ["auth", userId] as const,
  dashboards: (userId: string) => ["auth", userId, "dashboard"] as const,
  dashboard: (userId: string, teamFilter?: string) => [
    ...caseQueryKeys.dashboards(userId),
    { teamFilter: dashboardTeamScope(teamFilter) },
  ] as const,
  caseLists: (userId: string) => ["auth", userId, "cases", "list"] as const,
  caseList: (
    userId: string,
    status: AutomationStatus | undefined,
    priority: PriorityFilter,
    prioritySort: PrioritySort,
    teamFilter?: string,
    attentionType?: BusinessExceptionType,
  ) => ["auth", userId, "cases", "list", {
    status: status ?? absent,
    priorityFilter: priority,
    prioritySort,
    teamFilter: teamFilter ?? absent,
    attentionType: attentionType ?? absent,
  }] as const,
  caseResources: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "resources", caseId] as const,
  detail: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "detail", caseId] as const,
  documents: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "documents", caseId] as const,
  ownership: (userId: string, caseId: string) =>
    ["auth", userId, "cases", "ownership", caseId] as const,
  activities: (userId: string) => ["auth", userId, "activity"] as const,
  activity: (userId: string, filters: CaseActivityFilters) => [
    ...caseQueryKeys.activities(userId),
    {
      caseId: filters.caseId ?? absent,
      teamFilter: filters.teamFilter ?? absent,
      action: filters.action ?? absent,
      stage: filters.stage ?? absent,
      outcome: filters.outcome ?? absent,
      from: filters.from ?? absent,
      to: filters.to ?? absent,
      offset: filters.offset ?? 0,
      limit: filters.limit ?? 50,
    },
  ] as const,
  executionProfile: (userId: string) =>
    ["auth", userId, "system", "execution-profile"] as const,
};

export function dashboardQueryOptions(userId: string, teamFilter?: string) {
  const scope = dashboardTeamScope(teamFilter);
  return {
    queryKey: caseQueryKeys.dashboard(userId, scope),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchDashboard(scope, signal),
  };
}

export function caseListQueryOptions(
  userId: string,
  status: AutomationStatus | undefined,
  priority: PriorityFilter,
  prioritySort: PrioritySort,
  teamFilter?: string,
  attentionType?: BusinessExceptionType,
) {
  return {
    queryKey: caseQueryKeys.caseList(
      userId,
      status,
      priority,
      prioritySort,
      teamFilter,
      attentionType,
    ),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      fetchZeroTouchCases(status, priority, prioritySort, teamFilter, signal, attentionType),
  };
}

export function caseDetailQueryOptions(userId: string, caseId: string) {
  return {
    queryKey: caseQueryKeys.detail(userId, caseId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchZeroTouchCase(caseId, signal),
  };
}

export function documentQueryOptions(userId: string, caseId: string) {
  return {
    queryKey: caseQueryKeys.documents(userId, caseId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchDocuments(caseId, signal),
  };
}

export function ownershipQueryOptions(userId: string, caseId: string) {
  return {
    queryKey: caseQueryKeys.ownership(userId, caseId),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchOwnership(caseId, signal),
  };
}

export function activityQueryOptions(userId: string, filters: CaseActivityFilters) {
  return {
    queryKey: caseQueryKeys.activity(userId, filters),
    queryFn: ({ signal }: { signal: AbortSignal }) => fetchCaseActivity(filters, signal),
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
  void queryClient.prefetchQuery(dashboardQueryOptions(profile.user_id, absent));
  void queryClient.prefetchQuery(
    caseListQueryOptions(profile.user_id, undefined, "all", "highest_first"),
  );
}

export function publishCaseDetail(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): void {
  queryClient.setQueryData(
    caseQueryKeys.detail(userId, summary.case.case_id),
    summary,
  );
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
  publishCaseDetail(queryClient, userId, summary);
  void queryClient.invalidateQueries({ queryKey: caseQueryKeys.caseLists(userId) });
  queryClient.removeQueries({ queryKey: caseQueryKeys.dashboards(userId) });
  void queryClient.invalidateQueries({ queryKey: caseQueryKeys.activities(userId) });
}

export async function caseSupportingMutationEffect(
  queryClient: QueryClient,
  userId: string,
  summary: ZeroTouchCaseSummary,
): Promise<void> {
  caseSummaryMutationEffect(queryClient, userId, summary);
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
    queryClient.cancelQueries({ queryKey: caseQueryKeys.activities(userId) }),
  ]);
  queryClient.setQueriesData<ZeroTouchCaseListItem[]>(
    { queryKey: caseQueryKeys.caseLists(userId) },
    (current) => current?.filter((item) => item.case_id !== caseId),
  );
  queryClient.removeQueries({ queryKey: caseQueryKeys.detail(userId, caseId), exact: true });
  queryClient.removeQueries({ queryKey: caseQueryKeys.documents(userId, caseId), exact: true });
  queryClient.removeQueries({ queryKey: caseQueryKeys.ownership(userId, caseId), exact: true });
  queryClient.removeQueries({ queryKey: caseQueryKeys.dashboards(userId) });
  queryClient.removeQueries({ queryKey: caseQueryKeys.activities(userId) });
}

export function cachedDashboard(
  queryClient: QueryClient,
  userId: string,
  teamFilter?: string,
): DashboardSnapshot | undefined {
  return queryClient.getQueryData(caseQueryKeys.dashboard(userId, teamFilter));
}
