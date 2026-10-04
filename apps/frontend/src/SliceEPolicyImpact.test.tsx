// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import * as api from "./api";
import { ProposalReview } from "./pages/PolicyRules";
import type { AuthenticatedProfile, PolicyCatalogue, PolicyImpact, PolicyProposal, PolicyRule } from "./types";
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const now = "2026-10-03T00:00:00Z";
const actor: AuthenticatedProfile = { user_id:"hr-proposer",display_name:"Synthetic HR",role:"HR",team_id:null,team_display_name:null,team_type:null,team_description:"Synthetic",client_scope_label:"Synthetic",capabilities:["POLICY_VIEW","POLICY_MUTATE"] };
const rule: PolicyRule = {policy_id:"DOCUMENT_IDP_REVIEW_CONFIDENCE_THRESHOLD",category:"Documents",name:"Synthetic confidence",description:"Synthetic fixture",value:{type:"DECIMAL",value:"0.85"},value_type:"DECIMAL",default_value:{type:"DECIMAL",value:"0.85"},minimum:"0",maximum:"1",allowed_values:[],classifications:["PROJECT_DEFAULT"],authority:null,default_authority:null,enforcement:"RUNTIME_ENFORCED",version:1,created_at:now,updated_at:now,updated_by:"system-bootstrap"};
const proposal: PolicyProposal = {proposal_id:"SAFE_PROPOSAL",version:1,base_active_version:1,proposer_id:actor.user_id,status:"DRAFT",rules:[{...rule,value:{type:"DECIMAL",value:"0.92"}}],reason:"Synthetic proposal",created_at:now,updated_at:now,decided_by:null,decided_at:null,decision_reason:null,activated_version:null};
const catalogue: PolicyCatalogue = {catalogue_id:"GLOBAL_POLICY_CATALOGUE",version:2,active_version:1,active_identity:"a".repeat(64),active_origin:"DEFAULT",active_effective_at:now,proposals:[proposal],superseded_versions:[],created_at:now,updated_at:now,updated_by:"system-bootstrap",rules:[rule]};
const benchmark = {label:"Deterministic",scope:"Synthetic",benchmark_id:"SAFE",benchmark_hash:"b".repeat(64),rule_version:"v2",policy_version:1,support:14,exact_accuracy:1,classes:[],confusion_matrix:{},macro:{precision:1,recall:1,f1:1},micro:{precision:1,recall:1,f1:1}};
const runtime = {registry_freshness_seconds:7776000,not_found_ttl_seconds:600,document_auto_confirm:[false,true,true],ownership_numeric_candidates:[null,null,null]};
export const impactFixture: PolicyImpact = {
 proposal_id:proposal.proposal_id,proposal_version:1,catalogue_version:2,base_active_version:1,current_active_version:1,stale:false,comparison_basis:"ACTIVE_PROPOSAL_BASE",comparison_identity:"c".repeat(64),label:"Read-only synthetic policy impact",
 changes:[{policy_id:rule.policy_id,name:rule.name,current:rule.value,base:rule.value,default:rule.default_value,proposed:proposal.rules[0].value,direction:"INCREASE",stages:["DOCUMENT"],assessment:"ASSESSED",materiality:"HIGH",effect:"AUTOMATIC_REVIEW",scenario_ids:["DOCUMENT_CONFIDENCE_0.90"],coupled_policy_ids:[],reason_codes:["DOCUMENT_FIXTURE_CROSSES_AUTO_CONFIRM_THRESHOLD"],limitations:["Synthetic only"]}],
 before:{policy_version_context:"ACTIVE_BASE",classifier:benchmark,runtime},after:{policy_version_context:"PROSPECTIVE_UNRESERVED",classifier:benchmark,runtime},
 advisor:{fixture_set_id:"SYNTHETIC_POLICY_IMPACT_V1",fixture_set_hash:"d".repeat(64),scope:"Synthetic impact fixtures only — not production volume forecasting.",classifier_scope:"Deterministic classifier benchmark on synthetic fixtures — not trained ML model performance.",materiality:"HIGH",reason_codes:["DOCUMENT_FIXTURE_CROSSES_AUTO_CONFIRM_THRESHOLD"],scenarios:[{fixture_id:"DOCUMENT_CONFIDENCE_0.90",stage:"DOCUMENT",effect:"AUTOMATIC_REVIEW",before:{label:"AUTO_CONFIRMED",value:"0.90",score:null,threshold:"0.85",reason_codes:[],automatic:true,review_required:false,provisional_candidate:null,cache_reuse:null},after:{label:"REVIEW_REQUIRED",value:"0.90",score:null,threshold:"0.92",reason_codes:["DOCUMENT_LOW_CONFIDENCE"],automatic:false,review_required:true,provisional_candidate:null,cache_reuse:null}}],
 automation_delta:{automatic_document_confirmations:{before:7,after:5,delta:-2},provisional_ubo_candidates:{before:7,after:null,delta:null}},automation_direction:"LESS_AUTOMATIC",review_direction:"MORE_REVIEW",registry_reuse_direction:"NO_OBSERVED_CHANGE",negative_reuse_direction:"NO_OBSERVED_CHANGE",classifier_metric_delta:{micro_f1:0},unknown_impacts:[{concept:"GoldTier approval",status:"NOT_ASSESSED",reason_code:"IMPACT_NOT_ASSESSED",limitation:"No approval authority"}],limits:{synthetic_fixtures:64}}
};
function deferred<T>() {let resolve!:(value:T)=>void; const promise=new Promise<T>(done=>{resolve=done;});return {promise,resolve};}
let dispose:(()=>void)|undefined;
afterEach(async()=>{await act(async()=>dispose?.());dispose=undefined;vi.restoreAllMocks();document.body.innerHTML="";});
async function mount() {const host=document.createElement("div");document.body.append(host);const root=createRoot(host);dispose=()=>root.unmount();await act(async()=>root.render(<ProposalReview proposal={proposal} catalogue={catalogue} actor={actor} busy={false} onMutation={async()=>true} onEdit={()=>{}}/>));return {host,root};}
async function simulate(host:HTMLElement) {await act(async()=>Array.from(host.querySelectorAll("button")).find(b=>b.textContent==="Simulate impact")!.click());}
it("renders accessible synthetic explanations, nullable unknowns and no approval authority",async()=>{
 vi.spyOn(api,"fetchPolicyImpact").mockResolvedValue(impactFixture);const {host}=await mount();await simulate(host);
 expect(host.textContent).toContain("Synthetic impact fixtures only");
 for(const label of ["Change summary","Parameter comparison","Workflow impact","Synthetic scenario transitions","Automation/review delta","Registry freshness implications","Ownership threshold implications","Classifier benchmark delta","Unknown / not-assessed impacts","Approval boundary"]) expect(host.textContent).toContain(label);
 expect(host.textContent).toContain("AUTO_CONFIRMED");expect(host.textContent).toContain("NOT_ASSESSED");expect(host.textContent).toContain("GoldTier approval");expect(host.textContent).toContain("not reserved or activated");
 expect(host.querySelectorAll("summary").length).toBeGreaterThan(5);expect(host.textContent).not.toContain("null");
 expect(Array.from(host.querySelectorAll("button")).some(b=>b.textContent==="Approve and activate")).toBe(false);
});
for(const change of ["proposal","catalogue","actor","unmount"] as const) it(`ignores late impact after ${change} replacement`,async()=>{
 const pending=deferred<PolicyImpact>();let signal:AbortSignal|undefined;
 vi.spyOn(api,"fetchPolicyImpact").mockImplementation((_id,s)=>{signal=s;return pending.promise;});
 const {host,root}=await mount();await simulate(host);
 await act(async()=>{
  if(change==="unmount") root.render(null);
  else root.render(<ProposalReview proposal={change==="proposal"?{...proposal,version:2}:proposal} catalogue={change==="catalogue"?{...catalogue,version:3}:catalogue} actor={change==="actor"?{...actor,user_id:"other-user"}:actor} busy={false} onMutation={async()=>true} onEdit={()=>{}}/>);
 });
 expect(signal?.aborted).toBe(true);
 await act(async()=>pending.resolve(impactFixture));
 expect(host.textContent).not.toContain("Change summary");
});
it("rejects a mismatched current proposal/cataloque response",async()=>{
 vi.spyOn(api,"fetchPolicyImpact").mockResolvedValue({...impactFixture,catalogue_version:999});
 const {host}=await mount();await simulate(host);expect(host.textContent).not.toContain("Change summary");expect(host.textContent).toContain("Impact is unavailable");
});
