import { expect, test, type Page, type Locator } from "@playwright/test";
import { createBrowserNetworkPolicy, handleBrowserRoute } from "../playwright.config";
import path from "node:path";

let violations: string[];
let errors: string[];
test.beforeEach(async ({page}) => {
 violations=[];errors=[];
 page.on("pageerror",error=>errors.push(error.name));
 const policy=createBrowserNetworkPolicy({frontendOrigin:process.env.PLAYWRIGHT_BASE_URL!,backendOrigin:process.env.CLM_E2E_BACKEND_ORIGIN!,allowDirectBackend:false});
 await page.route("**/*",route=>handleBrowserRoute(route,policy,violations));
});
test.afterEach(()=>{expect(violations).toEqual([]);expect(errors).toEqual([]);});
async function login(page:Page,user:string,policy=true) {
 await page.goto("/");await page.getByLabel("User ID").fill(user);await page.getByLabel("Password").fill(process.env.CLM_E2E_PASSWORD!);
 await page.getByRole("button",{name:"Sign in",exact:true}).click();
 await expect(page.getByRole("link",{name:"Policy",exact:true})).toBeVisible();
 if(policy){await page.getByRole("link",{name:"Policy",exact:true}).click();await expect(page.getByRole("heading",{name:/Active policy/})).toBeVisible();}
}
async function logout(page:Page) {
 await page.locator(".operator-account__button").click();await page.getByRole("button",{name:"Sign out",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Sign in",exact:true})).toBeVisible();
}
async function change(page:Page,name:string,value:string) {
 const card=page.locator(".policy-parameter").filter({has:page.getByRole("heading",{name,exact:true,includeHidden:true})});
 const category=card.locator("xpath=ancestor::details[1]");
 if(await category.getAttribute("open")===null) await category.locator("summary").first().click();
 await card.getByRole("button",{name:"Propose change",exact:true}).click();
 await card.getByLabel("Proposed value for "+name).fill(value);
 await card.getByRole("button",{name:"Use proposed value",exact:true}).click();
}
async function draft(page:Page,reason:string) {
 await page.getByLabel("Change reason",{exact:true}).fill(reason);
 await page.getByRole("button",{name:"Save draft",exact:true}).click();
 await expect(page.locator(".policy-proposal").first().getByRole("heading",{level:3})).toHaveText("Proposal · DRAFT");
 return page.locator(".policy-proposal").first();
}
async function simulate(proposal:Locator,page:Page) {
 const response=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith("/impact")&&r.request().method()==="GET");
 await proposal.getByRole("button",{name:"Simulate impact",exact:true}).click();
 const result=await response;expect(result.status()).toBe(200);
 await expect(proposal.getByRole("region",{name:"Policy impact comparison",exact:true})).toBeVisible();
 return result.json();
}
async function contained(page:Page) {
 const widths=await page.evaluate(()=>[document.body.scrollWidth,document.documentElement.scrollWidth,document.documentElement.clientWidth]);
 expect(Math.max(widths[0],widths[1])).toBeLessThanOrEqual(widths[2]+1);
}
async function createFrozenCase(page:Page) {
 await login(page,"maya-lim",false);
 await page.getByRole("link",{name:"New onboarding",exact:true}).click();
 await page.getByLabel("Jurisdiction",{exact:true}).selectOption("SG");
 await page.getByLabel("Company Legal Name",{exact:true}).fill("MERLION CIRCULAR LABS PTE. LTD.");
 await page.getByLabel("Registration ID / UEN").fill("202400001A");
 await page.locator("#home-document").setInputFiles(path.resolve("../backend/tests/fixtures/uat/clean-company-profile.pdf"));
 await page.getByRole("button",{name:"Create onboarding",exact:true}).click();
 await expect(page).toHaveURL(/\/cases\/([0-9a-f-]{36})$/i);
 const id=page.url().split("/").at(-1)!;
 const response=await page.request.get(`/api/clm/zero-touch/cases/${id}`);
 expect(response.status()).toBe(200);
 const result=await response.json();
 return {id,snapshot:result.case.policy_snapshot};
}
test("Slice E HR and Director same impact, stale approval, reject and frozen cases",async({page})=>{
 test.setTimeout(120000);await page.setViewportSize({width:1280,height:1000});
 const frozen=await createFrozenCase(page);await logout(page);await login(page,"hr-admin");
 await change(page,"IDP extraction evidence score threshold","0.92");
 await change(page,"Registry evidence freshness","30");
 await change(page,"Definitive not-found cache TTL","60");
 await change(page,"UBO threshold percent","30");
 await change(page,"Semantic classification threshold","0.95");
 let proposal=await draft(page,"Synthetic multi-parameter explainable impact proposal");
 await proposal.getByRole("button",{name:"Edit draft",exact:true}).click();
 await page.getByLabel("Change reason",{exact:true}).fill("Edited synthetic multi-parameter impact with independent approval");
 await page.getByRole("button",{name:"Save draft",exact:true}).click();
 await proposal.getByRole("button",{name:"Submit for approval",exact:true}).click();
 await expect(proposal.getByRole("heading",{level:3})).toHaveText("Proposal · PENDING APPROVAL");
 let hr=await simulate(proposal,page);
 for(const label of ["Change summary","Parameter comparison","Automation/review delta","Registry freshness implications","Ownership threshold implications","Classifier benchmark delta","Unknown / not-assessed impacts","Approval boundary"]) await expect(proposal.getByText(label,{exact:true})).toBeVisible();
 await expect(proposal).toContainText("Current");await expect(proposal).toContainText("Default");await expect(proposal).toContainText("Proposed");
 await expect(proposal).toContainText("GoldTier approval: NOT_ASSESSED");
 const scenarios=proposal.getByText("Synthetic scenario transitions",{exact:true});
 await scenarios.focus();await page.keyboard.press("Enter");
 await expect(proposal).toContainText("DOCUMENT_CONFIDENCE_0.90");await expect(proposal).toContainText("AUTO_CONFIRMED");await expect(proposal).toContainText("REVIEW_REQUIRED");
 await expect(proposal.getByRole("button",{name:"Approve and activate",exact:true})).toHaveCount(0);
 // A separate draft deliberately becomes stale after the first activation.
 await change(page,"IDP extraction evidence score threshold","0.90");
 await draft(page,"Synthetic proposal retained against the old active base");
 hr=await simulate(page.locator(".policy-proposal").filter({has:page.getByRole("heading",{name:"Proposal · PENDING APPROVAL",exact:true})}).first(),page);
 await contained(page);await logout(page);await login(page,"olivia-koh");
 proposal=page.locator(".policy-proposal").filter({has:page.getByRole("heading",{name:"Proposal · PENDING APPROVAL",exact:true})}).first();
 const director=await simulate(proposal,page);expect(director).toEqual(hr);
 await proposal.getByLabel("Decision reason").fill("Independent Director reviewed the same synthetic policy impact");
 await proposal.getByRole("button",{name:"Approve and activate",exact:true}).click();
 await expect(page.locator(".policy-proposal").filter({hasText:"Edited synthetic multi-parameter impact with independent approval"}).getByRole("heading",{level:3})).toHaveText("Proposal · APPROVED");
 const stale=page.locator(".policy-proposal").filter({has:page.getByRole("heading",{name:"Proposal · DRAFT",exact:true})}).first();
 const staleEvidence=await simulate(stale,page);expect(staleEvidence.stale).toBe(true);expect(staleEvidence.comparison_basis).toBe("RETAINED_PROPOSAL_BASE");
 await expect(stale).toContainText("STALE_PROPOSAL_BASE");await expect(stale.getByRole("button",{name:"Approve and activate",exact:true})).toHaveCount(0);
 const oldResponse=await page.request.get(`/api/clm/zero-touch/cases/${frozen.id}`);expect(oldResponse.status()).toBe(200);expect((await oldResponse.json()).case.policy_snapshot).toEqual(frozen.snapshot);
 await logout(page);const newCase=await createFrozenCase(page);
 expect(newCase.snapshot.catalogue_version).toBeGreaterThan(frozen.snapshot.catalogue_version);
 expect(newCase.snapshot.idp_review_confidence_threshold).toBe("0.92");
 await logout(page);await login(page,"hr-admin");
 await change(page,"IDP extraction evidence score threshold","0.91");
 const rejected=await draft(page,"Synthetic new proposal for independent Director rejection");
 await rejected.getByRole("button",{name:"Submit for approval",exact:true}).click();
 await logout(page);await login(page,"olivia-koh");
 const decision=page.locator(".policy-proposal").first();await simulate(decision,page);
 await decision.getByLabel("Decision reason").fill("Independent rejection preserves the existing active policy");
 await decision.getByRole("button",{name:"Reject proposal",exact:true}).click();
 await expect(decision.getByRole("heading",{level:3})).toHaveText("Proposal · REJECTED");
 await contained(page);
});
test("Slice E late impact after edit and accessible narrow layout",async({page})=>{
 test.setTimeout(60000);await page.setViewportSize({width:320,height:1000});await login(page,"hr-admin");
 await change(page,"IDP extraction evidence score threshold","0.93");
 const proposal=await draft(page,"Synthetic delayed impact response before an edit");
 let release!:()=>void;const gate=new Promise<void>(done=>{release=done;});
 let finished!:()=>void;const completed=new Promise<void>(done=>{finished=done;});
 let observed!:()=>void;const arrived=new Promise<void>(done=>{observed=done;});
 await page.route("**/api/policies/proposals/*/impact",async route=>{
  const response=await route.fetch();const body=await response.json();observed();await gate;
  try {await route.fulfill({response,json:{...body,label:"STALE IMPACT MUST NOT PUBLISH"}});} catch { /* request was aborted on edit */ } finally {finished();}
 });
 await proposal.getByRole("button",{name:"Simulate impact",exact:true}).click();await arrived;
 await proposal.getByRole("button",{name:"Edit draft",exact:true}).click();
 await page.getByLabel("Change reason",{exact:true}).fill("Synthetic edited draft invalidates earlier comparison");
 await page.getByRole("button",{name:"Save draft",exact:true}).click();
 release();await completed;await page.unroute("**/api/policies/proposals/*/impact");
 await expect(proposal).not.toContainText("STALE IMPACT MUST NOT PUBLISH");
 await simulate(proposal,page);
 await expect(proposal).toContainText("Current");await expect(proposal).toContainText("Default");await expect(proposal).toContainText("Proposed");
 await expect(proposal).toContainText("Synthetic impact fixtures only");
 await contained(page);
 const disclosure=proposal.getByText("Synthetic scenario transitions",{exact:true});await disclosure.focus();await page.keyboard.press("Enter");await contained(page);
});
