import type { WorkflowField, WorkflowFieldKind } from "./workflowApi";

function field(label: string, kind: WorkflowFieldKind = "TEXT", extra: Partial<WorkflowField> = {}): WorkflowField {
  return {
    field_id: label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""),
    label,
    kind,
    required: true,
    options: [],
    autofill: false,
    document_label: null,
    ...extra,
  };
}

/** Labels the document reader already recognises, so these fields can autofill. */
function fromDocument(label: string, documentLabel: string, caseDataKey: string): WorkflowField {
  return field(label, "TEXT", { autofill: true, document_label: documentLabel, case_data_key: caseDataKey });
}

/**
 * Mock data-collection versions of the existing onboarding stages. They are forms for a
 * person to fill in: reusing one never runs the automated stage it is named after.
 */
export const ONBOARDING_STAGE_TEMPLATES: Record<string, WorkflowField[]> = {
  CASE_START: [
    field("Case reference", "TEXT", { case_data_key: "CASE_REFERENCE" }),
    field("Priority", "NUMBER", { required: false, case_data_key: "PRIORITY" }),
  ],
  INITIAL_IDENTITY: [
    fromDocument("Legal name", "Legal Name", "LEGAL_NAME"),
    fromDocument("Registration ID", "UEN", "REGISTRATION_ID"),
    fromDocument("Country of incorporation", "Country", "COUNTRY"),
  ],
  JURISDICTION: [field("Jurisdiction", "CHOICE", { options: ["SG", "AU", "MY", "HK"], case_data_key: "JURISDICTION" })],
  GOLDTIER_SEARCH: [
    field("Existing customer?", "YES_NO", { case_data_key: "EXISTING_CUSTOMER" }),
    field("GoldTier ID", "TEXT", { required: false, case_data_key: "GOLDTIER_ID" }),
  ],
  ACRA_REGISTRY: [
    fromDocument("UEN", "UEN", "REGISTRATION_ID"),
    fromDocument("Legal name", "Legal Name", "LEGAL_NAME"),
    fromDocument("Registered address", "Registered Address", "REGISTERED_ADDRESS"),
    fromDocument("Country of incorporation", "Country", "COUNTRY"),
  ],
  DOCUMENT_IDP: [
    field("Document name", "TEXT", { case_data_key: "DOCUMENT_NAME" }),
    field("Document reviewed?", "YES_NO", { case_data_key: "DOCUMENT_REVIEWED" }),
  ],
  RECONCILIATION: [
    field("Discrepancies found?", "YES_NO", { case_data_key: "DISCREPANCIES_FOUND" }),
    field("Discrepancy notes", "TEXT", { required: false }),
  ],
  OWNERSHIP_UBO: [
    field("Owner name", "TEXT", { case_data_key: "OWNER_NAME" }),
    field("Owner type", "CHOICE", { options: ["Natural person", "Legal entity"], case_data_key: "OWNER_TYPE" }),
    field("Ownership percentage", "NUMBER", { case_data_key: "OWNERSHIP_PERCENT" }),
  ],
  ADVISORY: [field("Risk level", "CHOICE", { options: ["Low", "Medium", "High"], case_data_key: "RISK_LEVEL" })],
  GOLDTIER_DETAILS: [
    field("KYC customer type", "TEXT", { case_data_key: "KYC_CUSTOMER_TYPE" }),
    field("Client segment", "TEXT", { case_data_key: "CLIENT_SEGMENT" }),
    field("Booking entity", "TEXT", { case_data_key: "BOOKING_ENTITY" }),
  ],
  FINAL_REVIEW_SEND: [
    field("Reviewed by", "TEXT", { case_data_key: "REVIEWED_BY" }),
    field("Review date", "DATE", { case_data_key: "REVIEW_DATE" }),
    field("Ready to send?", "YES_NO", { case_data_key: "READY_TO_SEND" }),
  ],
};
