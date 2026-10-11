import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { retainedEvidencePath } from "../playwright.config";

export async function expectDisclosureContrast(button: Locator): Promise<void> {
  const ratio = await button.evaluate((element) => {
    const channels = (value: string) => value.match(/[0-9.]+/g)!.map(Number);
    const ancestors: Element[] = [];
    for (let current: Element | null = element; current; current = current.parentElement) {
      ancestors.unshift(current);
    }
    let background = [255, 255, 255];
    for (const ancestor of ancestors) {
      const color = channels(getComputedStyle(ancestor).backgroundColor);
      const alpha = color[3] ?? 1;
      background = background.map((value, index) => color[index] * alpha + value * (1 - alpha));
    }
    const foreground = channels(getComputedStyle(element).color);
    const luminance = (color: number[]) => color.slice(0, 3).map((value) => {
      const normalized = value / 255;
      return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
    }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
    const levels = [luminance(foreground), luminance(background)].sort((a, b) => a - b);
    return (levels[1] + 0.05) / (levels[0] + 0.05);
  });
  expect(ratio).toBeGreaterThanOrEqual(4.5);
}

export async function openStage(page: Page, name: string): Promise<void> {
  const button = page.locator(".stage-disclosure > h2 > button").filter({ hasText: name });
  await expect(button).toBeVisible();
  await expect(async () => {
    if (await button.getAttribute("aria-expanded") === "false") await button.click();
    await expect(button).toHaveAttribute("aria-expanded", "true", { timeout: 1000 });
  }).toPass({ timeout: 15000 });
}

export async function focusPipelineAction(page: Page, nodeId: string, control: Locator) {
  const mutations: string[] = [];
  const listener = (request: import("@playwright/test").Request) => {
    if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method())) mutations.push(request.url());
  };
  page.on("request", listener);
  const node = page.locator(`.ds-stage[data-node-id="${nodeId}"]`);
  await expect(node).toHaveCount(1);
  const details = node.locator("details");
  if (await details.getAttribute("open") === null) await node.locator("summary").click();
  await node.getByRole("button", { name: "Open case stage details", exact: true }).click();
  await expect(control).toBeVisible(); await expect(control).toBeEnabled(); await expect(control).toBeFocused();
  await expect.poll(() => control.evaluate(element => { const r = element.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; })).toBe(true);
  await expect.poll(() => control.evaluate(element => {
    const r = element.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return hit === element || (hit !== null && element.contains(hit));
  })).toBe(true);
  page.off("request", listener);
  expect(mutations).toEqual([]);
  const evidence = retainedEvidencePath("blocker-regression");
  await mkdir(evidence, { recursive: true });
  const name = `${test.info().title}-${nodeId}`.replace(/[^a-z0-9-]/gi, "-");
  const actual = await control.evaluate(element => ({ tag: element.tagName, id: element.id,
    type: element.getAttribute("type"), label: element.getAttribute("aria-label"),
    field: element.getAttribute("data-review-field") ?? element.getAttribute("data-reconciliation-field") }));
  await writeFile(path.join(evidence, `focus-${name}.json`), JSON.stringify({ scenario: test.info().title,
    node: nodeId, actual_control: actual, visible: true, enabled: true, focused: true,
    in_viewport: true, unobscured: true, calls_before_confirmation: 0, verdict: "PASS" }, null, 2)+"\n");
}
