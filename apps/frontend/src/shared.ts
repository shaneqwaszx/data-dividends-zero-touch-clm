import type { AutomationStage, ZeroTouchCaseSummary } from "./types";

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

/** The wireframe pipeline grouped around backend-authored stages. */
export const STAGE_BANDS: Array<{ label: string; stages: AutomationStage[] }> = [
  { label: "Registry verification", stages: ["REGISTRY"] },
  { label: "Document and data check", stages: ["DOCUMENT"] },
  { label: "Ownership analysis", stages: ["OWNERSHIP"] },
  { label: "Readiness and Mock target", stages: ["READINESS", "MOCK_GOLDTIER", "COMPLETE"] },
];

/** Progress label for a case queue row, based on its current backend stage. */
export function stageProgressLabel(currentStage: AutomationStage): string {
  if (currentStage === "COMPLETE") return `${STAGE_BANDS.length} of ${STAGE_BANDS.length}`;
  const index = STAGE_BANDS.findIndex((band) => band.stages.includes(currentStage));
  return `${index === -1 ? 1 : index + 1} of ${STAGE_BANDS.length}`;
}
