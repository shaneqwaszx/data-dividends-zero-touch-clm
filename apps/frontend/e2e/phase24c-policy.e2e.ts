import { expect, test, type Page, type Locator } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import { expectDisclosureContrast } from "./stage-disclosures";
let violations: string[];
let pageErrors: string[];
test.beforeEach(async ({ page }) => {
  violations=[]; pageErrors=[];
  page.on("pageerror",error=>pageErrors.push(`${error.name}: ${error.message}`));
  const policy=createBrowserNetworkPolicy({frontendOrigin:process.env.PLAYWRIGHT_BASE_URL!, backendOrigin:process.env.CLM_E2E_BACKEND_ORIGIN!,allowDirectBackend:false});
  await page.route("**/*",route=>handleBrowserRoute(route,policy,violations));
});
test.afterEach(()=>{ expect(violations).toEqual([]); expect(pageErrors).toEqual([]); });
async function login(page:Page,user:string) {
  await page.goto("/"); await page.getByLabel("User ID").fill(user); await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
  await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await page.getByRole("link",{name:"Policy",exact:true}).click();
  await expect(page.getByRole("heading",{name:/Active policy/})).toBeVisible();
}
async function logout(page:Page) {
  await page.locator(".operator-account__button").click(); await page.getByRole("button",{name:"Sign out",exact:true}).click();
  await expect(page.getByRole("heading",{name:"Sign in",exact:true})).toBeVisible();
}
async function contained(page:Page) {
  const layout=await page.evaluate(()=>({body:document.body.scrollWidth,root:document.documentElement.scrollWidth,width:document.documentElement.clientWidth}));
  expect(Math.max(layout.body,layout.root),JSON.stringify(layout)).toBeLessThanOrEqual(layout.width+1);
}
async function keyboardToggle(summary:Locator,page:Page) {
  await summary.focus(); await expect(summary).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(summary.locator("..")).toHaveAttribute("open","");
  await expectDisclosureContrast(summary);
}
for (const width of [320,360,768,1280,1440,1920]) {
  test(`Phase24C policy approval and accessible layout ${width}`,async({page})=>{
    test.setTimeout(60000); await page.setViewportSize({width,height:1000});
    await login(page,"hr-admin"); await contained(page);
    if (width===320 || width===1280) await page.screenshot({path:`${process.env.TEMP}/clm-phase24c-policy-${width}.png`});
    const active=await page.getByRole("heading",{name:/Active policy/}).textContent();
    const card=page.locator(".policy-parameter").filter({has:page.getByRole("heading",{name:"IDP review confidence threshold",exact:true})});
    await card.getByRole("button",{name:"Propose change",exact:true}).click();
    await card.getByLabel("Proposed value for IDP review confidence threshold").fill("0.90");
    await card.getByRole("button",{name:"Use proposed value",exact:true}).click();
    await page.getByLabel("Change reason",{exact:true}).fill("Synthetic policy review with a deliberately long reason for responsive layout and independent Director approval; existing in-flight and completed cases retain their frozen values.");
    await page.getByRole("button",{name:"Save draft",exact:true}).click();
    const proposal=page.locator(".policy-proposal").first(); await expect(proposal.getByRole("heading",{level:3})).toHaveText("Proposal · DRAFT");
    await expect(page.getByRole("heading",{name:/Active policy/})).toHaveText(active!);
    await proposal.getByRole("button",{name:"Edit draft",exact:true}).click();
    await expect(page.getByRole("heading",{name:"Edit policy draft",exact:true})).toBeVisible();
    await page.getByLabel("Change reason",{exact:true}).fill("Synthetic edited proposal: Director review required and reset remains a proposal operation.");
    await page.getByRole("button",{name:"Save draft",exact:true}).click();
    await proposal.getByRole("button",{name:"Submit for approval",exact:true}).click();
    await expect(proposal.getByRole("heading",{level:3})).toHaveText("Proposal · PENDING APPROVAL");
    await expect(page.getByRole("button",{name:"Approve and activate",exact:true})).toHaveCount(0);
    await contained(page); await logout(page);
    await login(page,"olivia-koh"); await expect(page.getByRole("heading",{name:"Prepare policy proposal",exact:true})).toHaveCount(0);
    const review=page.locator(".policy-proposal").first();
    await expect(review).toContainText("Proposer: hr-admin");
    await review.getByRole("button",{name:"Evaluate synthetic impact",exact:true}).click();
    await expect(review.getByRole("region",{name:"Policy impact comparison"})).toBeVisible();
    await expect(review).toContainText("Before: active policy"); await expect(review).toContainText("After: proposed policy");
    const metrics=review.locator(".policy-metrics").first(); await keyboardToggle(metrics.locator("summary").first(),page);
    await expect(metrics).toContainText("Support 14"); await expect(metrics).toContainText("Macro precision");
    await review.getByLabel("Decision reason").fill("Independent synthetic benchmark impact reviewed by Director.");
    await review.getByRole("button",{name:"Approve and activate",exact:true}).click();
    await expect(review.getByRole("heading",{level:3})).toHaveText("Proposal · APPROVED");
    await expect(review).toContainText("Decision by olivia-koh"); await contained(page);
    await logout(page); await login(page,"hr-admin");
    const reset=page.getByRole("button",{name:"Reset business parameters to defaults",exact:true}); await reset.click();
    const dialog=page.getByRole("alertdialog"); await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("aria-modal","true"); await expect(dialog.getByRole("button",{name:"Cancel",exact:true})).toBeFocused();
    await page.keyboard.press("Shift+Tab"); await expect(dialog.getByRole("button",{name:"Use default in proposal",exact:true})).toBeFocused();
    await page.keyboard.press("Escape"); await expect(dialog).toHaveCount(0); await expect(reset).toBeFocused();
    await reset.click(); await dialog.getByRole("button",{name:"Use default in proposal",exact:true}).click();
    await expect(page.getByText("proposed 0.85",{exact:false}).first()).toBeVisible(); await expect(page.getByRole("heading",{name:/Active policy/})).toContainText("version");
    if (width===1280) { await page.evaluate(()=>{document.documentElement.style.zoom="2";}); await contained(page); await expect(page.getByLabel("Change reason",{exact:true})).toBeVisible(); await page.evaluate(()=>{document.documentElement.style.zoom="";}); }
    await contained(page);
  });
}
test("Phase24C RM views policy without draft or decision controls",async({page})=>{
  await page.setViewportSize({width:320,height:1000}); await login(page,"ethan-tan");
  await expect(page.getByRole("heading",{name:"Prepare policy proposal",exact:true})).toHaveCount(0);
  await expect(page.getByRole("button",{name:"Propose change",exact:true})).toHaveCount(0);
  await expect(page.getByRole("button",{name:"Approve and activate",exact:true})).toHaveCount(0);
  await expect(page.locator(".policy-parameter").first()).toContainText("Current"); await expect(page.locator(".policy-parameter").first()).toContainText("Default"); await contained(page);
});
