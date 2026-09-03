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
