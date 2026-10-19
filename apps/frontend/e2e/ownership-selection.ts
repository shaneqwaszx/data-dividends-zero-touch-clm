import { expect, type Page } from "@playwright/test";

export const selectedHolderName = (page: Page) =>
  page.locator('[aria-label="Ownership hierarchy"] .ownership-node__body > button[aria-pressed="true"]').first();

/** The selected holder is the highlighted tree row; UBO status shows on the row and in the UBO summary. */
export async function expectSelectedHolder(page: Page, candidate: {
  party: { display_name: string }; classification: string; threshold_result: string;
}) {
  await expect(selectedHolderName(page)).toHaveText(candidate.party.display_name);
  const row = page.locator('[aria-label="Ownership hierarchy"] [role="row"].is-selected').first();
  if (candidate.classification === "PROVISIONAL_UBO_CANDIDATE" && candidate.threshold_result === "MET") {
    await expect(row).toContainText("Provisional UBO");
    await expect(page.locator(".ubo-summary").first()).toContainText(candidate.party.display_name);
  } else {
    await expect(row).not.toContainText("Provisional UBO");
  }
}
