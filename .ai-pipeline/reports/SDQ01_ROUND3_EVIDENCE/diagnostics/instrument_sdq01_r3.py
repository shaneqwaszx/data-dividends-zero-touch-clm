from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "apps/frontend/e2e/authenticated-zero-touch.e2e.ts"
body = path.read_bytes().decode("utf-8")
(root / "tmp/sdq01-r3-authenticated-original.ts").write_bytes(path.read_bytes())
start = body.index('test("onboarding progress is visible while backend-authored stages advance"')
end = body.index('\ntest("Director explicitly selects', start)
block = body[start:end]
opening = block.index("\n") + 1
block = block[:opening] + '''  const diagnosticStart = Date.now();
  const trace = (label: string, detail: Record<string, unknown> = {}) => {
    console.log("SDQ01_R3", JSON.stringify({ utc: new Date().toISOString(),
      elapsed_ms: Date.now() - diagnosticStart, label, ...detail }));
  };
  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith("/api/")) trace("request", { method: request.method(), path: pathname });
  });
  page.on("response", (response) => {
    const pathname = new URL(response.url()).pathname;
    if (pathname.startsWith("/api/")) trace("response", { method: response.request().method(),
      path: pathname, status: response.status() });
  });
  page.on("requestfailed", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.startsWith("/api/")) trace("request-failed", { method: request.method(), path: pathname });
  });
  trace("test-enter");
''' + block[opening:]
steps = [
    ('await page.goto("/");', "goto-home"),
    ('await login(page);', "login"),
    ('await openFreshOnboarding(page);', "open-onboarding"),
    ('await page.getByLabel("Jurisdiction").selectOption("SG");', "select-jurisdiction"),
    ('await page.getByLabel("Company Legal Name").fill(legalNameForUen("202400001A"));', "fill-company"),
    ('await page.getByLabel("Registration ID / UEN").fill("202400001A");', "fill-uen"),
    ('await page.locator("#home-document").setInputFiles(cleanFixture);', "set-document"),
    ('await page.getByRole("button", { name: "Create onboarding" }).click();', "create-click"),
    ('await expect(page).toHaveURL(/\\/new-onboarding\\/[0-9a-f-]{36}$/i);', "retained-route"),
    ('await expect(progress).toBeVisible();', "progress-visible"),
    ('await expect(progress.getByRole("progressbar")).toHaveAttribute("aria-valuenow");', "progress-aria"),
    ('await expect(progress.getByText("Document verification", { exact: true })).toBeVisible();', "document-label"),
    ('await expect(progress.getByText("Current:").locator("..")).toContainText("Document verification — In progress");', "document-current"),
    ('await expect.poll(() => caseReadCount).toBeGreaterThanOrEqual(1);', "document-read-count"),
    ('await expect(progress.getByText("Current:").locator("..")).toContainText("Ownership & UBO — In progress");', "ownership-current"),
    ('await expect.poll(() => caseReadCount).toBeGreaterThanOrEqual(2);', "ownership-read-count"),
    ('await confirmMockTarget(page);', "confirm-helper"),
    ('await openStage(page, "GoldTier submission package");', "open-submission-stage"),
    ('await expect(page.getByText("Completed POC workflow")).toBeVisible({ timeout: 120_000 });', "completed-visible"),
]
for operation, label in steps:
    assert block.count(operation) == 1, label
    actual = operation.replace("confirmMockTarget(page)", "confirmMockTarget(page, trace)")
    block = block.replace(operation, f'trace("before-{label}"); {actual} trace("after-{label}");')
block = block.replace('body: await page.screenshot(),', 'body: await (async () => { trace("before-screenshot"); const result = await page.screenshot(); trace("after-screenshot"); return result; })(),')
block = block.replace('await new Promise((resolve) => setTimeout(resolve, 3_500));', 'trace("intake-delay-enter"); await new Promise((resolve) => setTimeout(resolve, 3_500)); trace("intake-delay-exit");')
block = block.replace('const response = await route.fetch();', 'trace("before-case-route-fetch"); const response = await route.fetch(); trace("after-case-route-fetch", { status: response.status() });')
block = block.replace('    if (!showObservedProgress) {', '    trace("authoritative-case", { version: payload.version, status: payload.status, stage: payload.current_stage, caseReadCount });\n    if (!showObservedProgress) {')
block = block.replace('    await route.fulfill({ response, json: payload });', '    trace("before-case-fulfill", { version: payload.version, status: payload.status, stage: payload.current_stage }); await route.fulfill({ response, json: payload }); trace("after-case-fulfill");')
body = body[:start] + block + body[end:]
# Keep helper line count intact so the failing test still starts at line670.
body = body.replace('async function confirmMockTarget(page: Page) {', 'async function confirmMockTarget(page: Page, diagnostic?: (label: string) => void) {')
helper_start = body.index('async function confirmMockTarget(')
helper_end = body.index('\nasync function expectDocumentContained', helper_start)
helper = body[helper_start:helper_end]
for operation, label in [
    ('await page.getByRole("button", { name: "Open full case" }).click();', 'full-case-click'),
    ('await expect(page).toHaveURL(/\\/cases\\/[0-9a-f-]{36}$/i);', 'full-case-url'),
    ('await expect(confirmation).toBeEnabled({ timeout: 120_000 });', 'confirmation-enabled'),
    ('await confirmation.click();', 'confirmation-click'),
    ('expect((await response).status()).toBe(200);', 'confirmation-response'),
]:
    assert helper.count(operation) == 1, label
    helper = helper.replace(operation, f'diagnostic?.("before-{label}"); {operation} diagnostic?.("after-{label}");')
body = body[:helper_start] + helper + body[helper_end:]
assert body[:body.index('test("onboarding progress is visible')].count('\n') == 669
path.write_bytes(body.encode("utf-8"))
print("Temporary timestamped stage/request tracing installed; behavior, assertions and deadlines unchanged.")
