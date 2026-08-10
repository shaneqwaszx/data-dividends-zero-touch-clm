import type { MockScenarioDiscovery, OnboardingCase } from "./types";

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
