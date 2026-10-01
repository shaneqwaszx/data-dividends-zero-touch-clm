import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";
import {
  caseDetailQueryOptions, caseQueryKeys, caseSupportingMutationEffect, publishCaseDetail,
  retainNewestDocuments, retainNewestVersionedEvidence, documentQueryOptions, ownershipQueryOptions,
} from "./caseQueries";
import type { ZeroTouchCaseSummary, DocumentProcessingRecord } from "./types";

const user = "test-operator";
const caseId = "00000000-0000-4000-8000-000000000001";
function snapshot(version: number, caseVersion = version, clmVersion = version): ZeroTouchCaseSummary {
  return {
    version, case: { case_id: caseId, events: Array.from({ length: caseVersion }, () => ({})) },
    clm: { version: clmVersion }, active_exceptions: version === 1 ? [{ blocker_code: "OWNERSHIP_REQUIRED" }] : [],
  } as unknown as ZeroTouchCaseSummary;
}
afterEach(() => vi.restoreAllMocks());

describe("authoritative zero-touch publication", () => {
  it("rejects an older mutation on the supporting-evidence path", async () => {
    const client = new QueryClient();
    publishCaseDetail(client, user, snapshot(3));
    await caseSupportingMutationEffect(client, user, snapshot(2));
    expect(client.getQueryData<ZeroTouchCaseSummary>(caseQueryKeys.detail(user, caseId))?.version).toBe(3);
    client.clear();
  });
  it("cannot restore a blocker when an older GET finishes after intervention success", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    let release!: (value: ZeroTouchCaseSummary) => void;
    const oldRead = new Promise<ZeroTouchCaseSummary>((resolve) => { release = resolve; });
    vi.spyOn(api, "fetchZeroTouchCase").mockReturnValue(oldRead);
    const read = client.fetchQuery(caseDetailQueryOptions(user, caseId)).catch(() => undefined);
    await caseSupportingMutationEffect(client, user, snapshot(2));
    release(snapshot(1));
    await read;
    expect(client.getQueryData<ZeroTouchCaseSummary>(caseQueryKeys.detail(user, caseId))?.active_exceptions).toEqual([]);
    client.clear();
  });
  it("preserves newer case and CLM revisions when automation version is unchanged", () => {
    const client = new QueryClient();
    publishCaseDetail(client, user, snapshot(2, 4, 5));
    publishCaseDetail(client, user, snapshot(2, 3, 4));
    const retained = client.getQueryData<ZeroTouchCaseSummary>(caseQueryKeys.detail(user, caseId));
    expect(retained?.case.events).toHaveLength(4);
    expect(retained?.clm.version).toBe(5);
    client.clear();
  });
  it("retains newer document versions, replacements and ownership/intelligence revisions", () => {
    const document = (id: string, count: number) => ({ document_id: id,
      events: Array.from({ length: count }, () => ({})),
    }) as unknown as DocumentProcessingRecord;
    const newest = [document("original", 6), document("replacement", 4)];
    expect(retainNewestDocuments(newest, [document("original", 5)])).toBe(newest);
    expect(retainNewestDocuments(newest, [document("original", 6), document("replacement", 3)])).toBe(newest);
    const resolved = [{ ...document("original", 6), reconciliation_version: 7, semantic_completion: "RECONCILIATION_RESOLVED" as const }];
    expect(retainNewestDocuments(resolved, [{ ...document("original", 6), reconciliation_version: 6 }])).toBe(resolved);
    const refreshed = [{ ...document("original", 6), reconciliation_version: 8, semantic_completion: null }];
    expect(retainNewestDocuments(resolved, refreshed)).toBe(refreshed);
    expect(retainNewestVersionedEvidence({ version: 4 }, { version: 3 })).toEqual({ version: 4 });
    expect(retainNewestVersionedEvidence({ version: 4 }, null)).toEqual({ version: 4 });
  });
  it("publishes bound replacement history despite cleared reconciliation, rejecting stale reversal", () => {
    const original = { document_id: "original", events: Array.from({ length: 9 }, () => ({})),
      reconciliation_version: 2, superseded_by_document_id: null,
    } as unknown as DocumentProcessingRecord;
    const historical = { ...original, events: [...original.events, {}], reconciliation_version: null,
      superseded_by_document_id: "replacement" } as DocumentProcessingRecord;
    const replacement = { document_id: "replacement", events: Array.from({ length: 9 }, () => ({})),
      reconciliation_version: 3, supersedes_document_id: "original", superseded_by_document_id: null,
    } as unknown as DocumentProcessingRecord;
    const before = [original];
    const after = [historical, replacement];
    expect(retainNewestDocuments(before, after)).toBe(after);
    expect(retainNewestDocuments(after, before)).toBe(after);
    expect(retainNewestDocuments(before, [historical])).toBe(before);
    expect(retainNewestDocuments(before, [{ ...historical, events: original.events }, replacement])).toBe(before);
    expect(retainNewestDocuments(before, [historical, { ...replacement, supersedes_document_id: "unrelated" }])).toBe(before);
  });
  it("held supporting GETs cannot replace evidence published after intervention", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const doc = (count: number) => ({ document_id: "current", events: Array.from({ length: count }, () => ({})) }) as unknown as DocumentProcessingRecord;
    let finishDocs!: (value: DocumentProcessingRecord[]) => void;
    let finishOwner!: (value: any) => void;
    vi.spyOn(api, "fetchDocuments").mockReturnValue(new Promise((resolve) => { finishDocs = resolve; }));
    vi.spyOn(api, "fetchOwnership").mockReturnValue(new Promise((resolve) => { finishOwner = resolve; }));
    const docs = client.fetchQuery(documentQueryOptions(user, caseId));
    const owner = client.fetchQuery(ownershipQueryOptions(user, caseId));
    client.setQueryData(caseQueryKeys.documents(user, caseId), [doc(4)]);
    client.setQueryData(caseQueryKeys.ownership(user, caseId), { version: 4, state: "ANALYZED" });
    finishDocs([doc(2)]); finishOwner({ version: 2, state: "REVIEW_REQUIRED" });
    await Promise.all([docs, owner]);
    expect(client.getQueryData<DocumentProcessingRecord[]>(caseQueryKeys.documents(user, caseId))?.[0].events).toHaveLength(4);
    expect(client.getQueryData(caseQueryKeys.ownership(user, caseId))).toEqual({ version: 4, state: "ANALYZED" });
    client.clear();
  });

});
