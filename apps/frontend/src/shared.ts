import type { RegistryAcquisition, RegistryEvidenceBinding, ZeroTouchCaseSummary } from "./types";

export function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-SG", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "Asia/Singapore",
  }).format(new Date(value));
}

/** Registry wire times are UTC; validity is independent of presentation text. */
export function registryTimestampIsUsable(value: string | null | undefined): value is string {
  if (!value || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/.test(value)) return false;
  const date = new Date(value);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 19) === value.slice(0, 19);
}

/** Invalid or missing provenance is never a freshness claim. */
export function formatRegistryTimestamp(value: string | null | undefined): string {
  if (!value) return "Not recorded";
  if (!registryTimestampIsUsable(value)) return "Unavailable (invalid timestamp)";
  return `${formatTimestamp(value)} SGT (UTC+08:00)`;
}

/** One presentation rule for retained registry reuse; does not assess current freshness. */
export function registryReuseDescription(
  acquisition: RegistryAcquisition | null | undefined,
  binding: RegistryEvidenceBinding,
): string {
  const timestampsRecorded = [binding.bound_to_case_at, binding.expires_at, acquisition?.retrieved_at,
    ...(acquisition?.operation_results.filter(result => result.provenance).map(result => result.provenance!.retrieved_at) ?? [])]
    .every(registryTimestampIsUsable);
  return timestampsRecorded
    ? "Reused fresh registry evidence — no ACRA request required."
    : "Retained registry reuse; valid-at-use timestamps unavailable.";
}

/** A calendar date, independent of the browser's timezone and UTC date rollover. */
export function singaporeCalendarDate(now = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-SG", {
    timeZone: "Asia/Singapore", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now);
  const part = (kind: Intl.DateTimeFormatPartTypes) => parts.find(item => item.type === kind)!.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

export function formatDateNoSeconds(value: string): string {
  return new Intl.DateTimeFormat("en-SG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

/** Format a backend-authored bounded duration without consulting browser wall time. */
export function formatDuration(milliseconds: number): string {
  if (!Number.isSafeInteger(milliseconds) || milliseconds < 0) return "—";
  if (milliseconds < 1_000) return "< 1s";
  const seconds = Math.floor(milliseconds / 1_000);
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  const remainingSeconds = seconds % 60;
  if (days > 0) return `${days}d${hours > 0 ? ` ${hours}h` : ""}`;
  if (hours > 0) return `${hours}h${minutes > 0 ? ` ${minutes}m` : ""}`;
  if (minutes > 0) return `${minutes}m${remainingSeconds > 0 ? ` ${remainingSeconds}s` : ""}`;
  return `${remainingSeconds}s`;
}

export function shouldPollAutomation(status: ZeroTouchCaseSummary["status"]): boolean {
  return status === "RUNNING" || status === "RESUMING";
}

export function shouldMaintainLiveProgress(
  status: ZeroTouchCaseSummary["status"],
  intakeMutationActive: boolean,
): boolean {
  return intakeMutationActive || shouldPollAutomation(status);
}

export function goldTierJourneyLabel(environment: "MOCK" | "SANDBOX"): string {
  return environment === "MOCK" ? "Mock GoldTier" : "GoldTier Sandbox";
}

/** Present the legacy durable outcome without treating its identifier as provider truth. */
export function targetOutcomeLabel(
  outcome: string,
  environment?: "MOCK" | "SANDBOX",
): string {
  if (outcome === "MOCK_GOLDTIER_SUBMITTED") {
    return environment
      ? `${goldTierJourneyLabel(environment)} submitted`
      : "GoldTier target submitted";
  }
  return outcome.replaceAll("_", " ");
}
