import type {
  DocumentProcessingRecord,
  DocumentFieldKey,
  MockIdpScenario,
  MockScenarioDiscovery,
  OnboardingCase,
  ReviewDecision,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Application API request failed (${response.status}).`);
  }
  return (await response.json()) as T;
}

export async function fetchMockScenarios(): Promise<MockScenarioDiscovery> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/mock-scenarios`);
  return parseResponse<MockScenarioDiscovery>(response);
}

export async function createOnboardingCase(uen: string): Promise<OnboardingCase> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/cases`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uen }),
  });
  return parseResponse<OnboardingCase>(response);
}

export async function fetchOnboardingCase(caseId: string): Promise<OnboardingCase> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/cases/${caseId}`);
  return parseResponse<OnboardingCase>(response);
}

export async function fetchDocuments(caseId: string): Promise<DocumentProcessingRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/onboarding/cases/${caseId}/documents`);
  return parseResponse<DocumentProcessingRecord[]>(response);
}

export async function uploadDocument(
  caseId: string,
  file: File,
  scenario: MockIdpScenario,
): Promise<DocumentProcessingRecord> {
  const response = await fetch(`${API_BASE_URL}/api/demo/onboarding/cases/${caseId}/documents`, {
    method: "POST",
    headers: {
      "Content-Type": file.type || "application/pdf",
      "X-Document-Name": file.name,
      "X-Mock-IDP-Scenario": scenario,
    },
    body: file,
  });
  return parseResponse<DocumentProcessingRecord>(response);
}

export async function reviewDocument(
  caseId: string,
  documentId: string,
  fieldKey: DocumentFieldKey,
  decision: ReviewDecision,
  correctedValue?: string,
  note?: string,
): Promise<DocumentProcessingRecord> {
  const response = await fetch(
    `${API_BASE_URL}/api/onboarding/cases/${caseId}/documents/${documentId}/reviews`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        field_key: fieldKey,
        decision,
        ...(correctedValue ? { corrected_value: correctedValue } : {}),
        ...(note ? { note } : {}),
      }),
    },
  );
  return parseResponse<DocumentProcessingRecord>(response);
}
