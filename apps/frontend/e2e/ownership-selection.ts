import { expect, type Page } from "@playwright/test";
import { classificationText, thresholdResultText } from "../src/ownershipLabels";

export const selectedHolderName = (page: Page) =>
  page.locator('[aria-label="Ownership hierarchy"] .ownership-node__body > button[aria-pressed="true"]').first();

/** The Selected holder panel names the holder and its backend classification (in plain language); the tree row is highlighted. */
export async function expectSelectedHolder(page: Page, candidate: {
  party: { display_name: string }; classification: string; threshold_result: string;
  threshold_percent: string; threshold_comparator: string;
}) {
  const selectedHolder = page.getByRole("complementary", { name: "Selected holder", exact: true });
  await expect(selectedHolder.getByRole("heading", { name: candidate.party.display_name, exact: true })).toBeVisible();
  // The panel words the backend values; it never shows or recomputes them itself.
  await expect(selectedHolder).toContainText(classificationText(candidate.classification));
  await expect(selectedHolder).toContainText(thresholdResultText(candidate.threshold_result, candidate.threshold_percent, candidate.threshold_comparator));
  await expect(selectedHolderName(page)).toHaveText(candidate.party.display_name);
  const row = page.locator('[aria-label="Ownership hierarchy"] [role="row"].is-selected').first();
  if (candidate.classification === "PROVISIONAL_UBO_CANDIDATE" && candidate.threshold_result === "MET") {
    await expect(row).toContainText("Provisional UBO");
    await expect(page.locator(".ubo-summary").first()).toContainText(candidate.party.display_name);
  } else {
    await expect(row).not.toContainText("Provisional UBO");
  }
}
