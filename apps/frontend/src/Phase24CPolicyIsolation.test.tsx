// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import * as api from "./api";
import PolicyRules from "./pages/PolicyRules";
import type { AuthenticatedProfile, PolicyCatalogue, ClassifierBenchmark } from "./types";
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const now = "2026-10-02T00:00:00Z";
const hr: AuthenticatedProfile = { user_id:"hr-proposer",display_name:"Synthetic HR",role:"HR",team_id:null,team_display_name:null,team_type:null,team_description:"Synthetic",client_scope_label:"Synthetic",capabilities:["POLICY_VIEW","POLICY_MUTATE"] };
const rm: AuthenticatedProfile = {...hr,user_id:"rm-reader",role:"RELATIONSHIP_MANAGER",capabilities:["POLICY_VIEW"]};
const catalogue: PolicyCatalogue = {catalogue_id:"GLOBAL_POLICY_CATALOGUE",version:1,active_version:1,active_identity:"a".repeat(64),active_origin:"DEFAULT",active_effective_at:now,proposals:[],superseded_versions:[],created_at:now,updated_at:now,updated_by:"system-bootstrap",rules:[{policy_id:"DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD",category:"Documents",name:"Synthetic confidence",description:"Synthetic fixture",value:{type:"DECIMAL",value:"0.85"},value_type:"DECIMAL",default_value:{type:"DECIMAL",value:"0.85"},minimum:"0",maximum:"1",allowed_values:[],classifications:["PROJECT_DEFAULT"],authority:null,default_authority:null,enforcement:"RUNTIME_ENFORCED",version:1,created_at:now,updated_at:now,updated_by:"system-bootstrap"}]};
const metrics: ClassifierBenchmark = {label:"Parameterized deterministic evidence classifier",scope:"Synthetic only",benchmark_id:"safe-fixtures",benchmark_hash:"b".repeat(64),rule_version:"v2",policy_version:1,support:14,exact_accuracy:1,classes:[],confusion_matrix:{},macro:{precision:1,recall:1,f1:1},micro:{precision:1,recall:1,f1:1}};
function deferred<T>() { let resolve!:(value:T)=>void; const promise=new Promise<T>(done=>{resolve=done;}); return {promise,resolve}; }
let dispose:(()=>void)|undefined;
afterEach(async()=>{await act(async()=>dispose?.());dispose=undefined;vi.restoreAllMocks();document.body.innerHTML="";});
it("aborts and ignores an old actor's late policy GET",async()=>{
  const old=deferred<PolicyCatalogue>(); const signals:AbortSignal[]=[];
  vi.spyOn(api,"fetchPolicies").mockImplementationOnce(signal=>{signals.push(signal!);return old.promise;}).mockResolvedValue(catalogue);
  vi.spyOn(api,"fetchClassifierBenchmark").mockResolvedValue(metrics);
  const host=document.createElement("div");document.body.append(host);const root=createRoot(host);dispose=()=>root.unmount();
  await act(async()=>root.render(<PolicyRules actor={hr}/>));
  await act(async()=>root.render(<PolicyRules actor={rm}/>));
  expect(signals[0].aborted).toBe(true);
  await act(async()=>old.resolve({...catalogue,active_version:999,active_identity:"c".repeat(64)}));
  expect(host.textContent).toContain("Active policy · version 1");expect(host.textContent).not.toContain("999");expect(host.textContent).not.toContain("Prepare policy proposal");
});
it("does not publish a completed old-actor proposal mutation after identity change",async()=>{
  vi.spyOn(api,"fetchPolicies").mockResolvedValue(catalogue);vi.spyOn(api,"fetchClassifierBenchmark").mockResolvedValue(metrics);
  const pending=deferred<PolicyCatalogue>();const save=vi.spyOn(api,"savePolicyProposal").mockReturnValue(pending.promise);
  const host=document.createElement("div");document.body.append(host);const root=createRoot(host);dispose=()=>root.unmount();
  await act(async()=>root.render(<PolicyRules actor={hr}/>));
  await act(async()=>Array.from(host.querySelectorAll("button")).find(button=>button.textContent==="Reset business parameters to defaults")!.click());
  await act(async()=>Array.from(host.querySelectorAll("button")).find(button=>button.textContent==="Use default in proposal")!.click());
  const input=host.querySelector("#policy-proposal-reason") as HTMLTextAreaElement;
  await act(async()=>{Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value")!.set!.call(input,"Synthetic deferred policy proposal");input.dispatchEvent(new Event("input",{bubbles:true}));});
  await act(async()=>host.querySelector("form")!.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true})));
  expect(save).toHaveBeenCalledOnce();
  await act(async()=>root.render(<PolicyRules actor={rm}/>));
  await act(async()=>pending.resolve({...catalogue,active_version:999,version:999}));
  expect(host.textContent).not.toContain("999");expect(host.textContent).not.toContain("Prepare policy proposal");
});
