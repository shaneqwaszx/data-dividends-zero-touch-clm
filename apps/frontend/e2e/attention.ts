import type { Page } from "@playwright/test";

/** Sidebar attention items are folded under their pipeline step; open them all. */
export async function showAllIssues(page: Page) {
  const toggle = page.getByRole("button", { name: "Show all issues", exact: true });
  if (await toggle.count()) await toggle.click();
}
