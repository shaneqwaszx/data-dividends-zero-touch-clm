import { revealStage } from "./StageDisclosure";

/** The case page stage with this title (StageDisclosure), if the case page is showing it. */
export function findCaseSection(title: string): HTMLElement | null {
  if (typeof document === "undefined") return null;
  for (const section of document.querySelectorAll<HTMLElement>("section.stage-disclosure")) {
    const label = section.querySelector(":scope > h2 > button > span");
    if (label?.textContent?.trim() === title) return section;
  }
  return null;
}

/**
 * Opens that stage and scrolls it into view. Only the view changes: no navigation and no
 * request, so it is as safe as the RM clicking the stage heading themselves.
 */
export function goToCaseSection(title: string): boolean {
  const section = findCaseSection(title);
  if (!section) return false;
  const heading = section.querySelector<HTMLButtonElement>(":scope > h2 > button");
  if (heading) revealStage(heading);
  const still = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  section.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
  heading?.focus({ preventScroll: true });
  return true;
}
