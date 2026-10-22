import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PendingDocumentsBanner, type PendingDocuments } from "./CaseDetail";

function pending(overrides: Partial<PendingDocuments>): PendingDocuments {
  return {
    fileNames: ["synthetic-profile.pdf"],
    busy: false,
    progress: null,
    error: null,
    onUpload: () => undefined,
    onDiscard: () => undefined,
    ...overrides,
  };
}

describe("pending documents banner", () => {
  it("shows only upload progress while an upload is in flight", () => {
    const markup = renderToStaticMarkup(<PendingDocumentsBanner pending={pending({ busy: true, progress: "Uploading document 1 of 1…" })} />);
    expect(markup).toContain("1 document is being uploaded");
    expect(markup).toContain("Uploading document 1 of 1…");
    expect(markup).not.toContain("stopped before document intake");
    expect(markup).not.toContain("waiting to upload");
    expect(markup).not.toContain("couldn&#x27;t be uploaded");
    expect(markup).not.toContain("<button");
  });

  it("keeps the stopped explanation and actions once intake is not running", () => {
    const markup = renderToStaticMarkup(<PendingDocumentsBanner pending={pending({})} />);
    expect(markup).toContain("1 document is waiting to upload");
    expect(markup).toContain("stopped before document intake");
    expect(markup).toContain(">Upload now</button>");
    expect(markup).toContain(">Discard</button>");
  });

  it("keeps the rejection explanation and retry after a refused upload", () => {
    const markup = renderToStaticMarkup(<PendingDocumentsBanner pending={pending({ error: "Synthetic intake unavailable." })} />);
    expect(markup).toContain("Your document couldn&#x27;t be uploaded");
    expect(markup).toContain("Synthetic intake unavailable.");
    expect(markup).not.toContain("stopped before document intake");
    expect(markup).toContain(">Try upload again</button>");
  });
});
