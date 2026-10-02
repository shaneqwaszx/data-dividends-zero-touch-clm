import { expect, type Locator, type Page } from "@playwright/test";

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
