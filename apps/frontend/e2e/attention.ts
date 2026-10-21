import { expect, type Page } from "@playwright/test";

/** Sidebar attention items are folded under their pipeline step; open them all. */
export async function showAllIssues(page: Page) {
  // The region renders with the case summary; only then is the toggle present or absent for certain.
  await expect(page.getByRole("region", { name: "Attention required", exact: true })).toBeVisible();
  const toggle = page.getByRole("button", { name: "Show all issues", exact: true });
  if (await toggle.count()) await toggle.click();
}
