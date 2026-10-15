import { expect, type Page } from "@playwright/test";
import type { RegistryEvidenceBinding } from "../src/types";
import { openStageSupport } from "./stage-disclosures";

export async function assertRegistryBindingTimestamps(page: Page, binding: RegistryEvidenceBinding) {
  await openStageSupport(page, "Registry verification", "More");
  await openStageSupport(page, "Registry verification", "Technical");
  const display = page.getByLabel("Registry case-use times", { exact: true });
  const audit = page.locator('[aria-labelledby="registry-provenance-technical-heading"]');
  await expect(display).toBeVisible();
  await expect(audit).toBeVisible();
  for (const [field, label] of [
    ["bound_to_case_at", "Bound to this case at"],
    ["expires_at", "Valid-at-use expiry"],
  ] as const) {
    const value = binding[field];
    expect(value).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/);
    const formatted = new Intl.DateTimeFormat("en-SG", {
      dateStyle: "medium", timeStyle: "medium", timeZone: "Asia/Singapore",
    }).format(new Date(value));
    const row = display.getByText(label, { exact: true }).locator("..");
    await expect(row.locator(".kv-value")).toHaveText(`${formatted} SGT (UTC+08:00)`);
    await expect(audit).toBeVisible();
    const original = audit.getByText(`${label} — original ISO UTC`, { exact: true }).locator("..").locator("dd");
    await expect(original).toBeVisible();
    await expect(original).toHaveText(value);
  }
}
