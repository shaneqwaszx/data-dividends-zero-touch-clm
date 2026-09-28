import type { ZeroTouchCaseSummary } from "./types";

export function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-SG", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "Asia/Singapore",
  }).format(new Date(value));
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
