import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { targetedIntakeFailurePresentation } from "../App";
import { FILE_REJECTION_CODES, uploadRejectionPresentation, type IntakeUploadFailure } from "../uploadRejection";
import { PendingDocumentsBanner, type PendingDocuments } from "./CaseDetail";

const CASE_ID = "00000000-0000-4000-8000-000000000014";

// The backend's fixed wording for each reason (apps/backend/app/services/document_errors.py).
const REASONS: Array<[string, string]> = [
  ["DOCUMENT_TOO_MANY_PAGES", "This file has more than 10 pages. Upload only the pages needed (up to 10)."],
  ["DOCUMENT_ENCRYPTED", "This PDF is password-protected. Remove the password and upload it again."],
  ["DOCUMENT_ACTIVE_CONTENT", "This PDF contains links or interactive content, which isn't allowed. Print it to PDF ('Save as PDF') and upload that copy."],
  ["DOCUMENT_PAGE_TOO_LARGE", "A page in this file is too large. Export it at a standard page size (A4 or Letter) and upload it again."],
  ["DOCUMENT_CONTENT_TOO_LARGE", "This file is too large to process. Upload fewer or smaller pages."],
  ["DOCUMENT_STRUCTURE_INVALID", "This file isn't a readable PDF or image. Re-export it and upload it again."],
];

function failure(overrides: Partial<IntakeUploadFailure>): IntakeUploadFailure {
  return { fileName: "Forecast in Tableau.pdf", message: REASONS[2][1], code: "DOCUMENT_ACTIVE_CONTENT", rejectedBeforeStorage: true, ...overrides };
}

function bannerFor(failures: IntakeUploadFailure[], withChooser = true): string {
  const retained = targetedIntakeFailurePresentation(CASE_ID, failures.map(item => `${item.fileName}: ${item.message}`));
  const pending: PendingDocuments = {
    fileNames: failures.map(item => item.fileName),
    busy: false,
    progress: retained.progress,
    error: retained.message,
    rejection: uploadRejectionPresentation(retained.message, failures),
    onUpload: () => undefined,
    onDiscard: () => undefined,
  };
  return renderToStaticMarkup(<PendingDocumentsBanner pending={pending} onChooseDifferentFile={withChooser ? () => undefined : undefined} />);
}

function visibleText(markup: string): string {
  // Everything outside the collapsed Technical details disclosure.
  return markup.replace(/<details[\s\S]*?<\/details>/g, "");
}

describe("upload rejection banner", () => {
  it.each(REASONS)("%s shows the plain reason and offers a different file", (code, message) => {
    expect(FILE_REJECTION_CODES.has(code)).toBe(true);
    const markup = bannerFor([failure({ code, message })]);
    const html = message.replaceAll("'", "&#x27;");
    expect(visibleText(markup)).toContain(`Forecast in Tableau.pdf: ${html}`);
    expect(markup).toContain(">Choose a different file</button>");
    expect(markup).not.toContain("Try upload again");
    expect(markup).toContain(">Discard</button>");
  });

  it("keeps the case ID and retry wording in collapsed Technical details", () => {
    const markup = bannerFor([failure({})]);
    expect(markup).toMatch(/<details class="[^"]*pending-documents__technical[^"]*"><summary>Technical details<\/summary>/);
    expect(markup).not.toMatch(/<details[^>]*\sopen/);
    const visible = visibleText(markup);
    expect(visible).not.toContain(CASE_ID);
    expect(visible).not.toContain("Retry the same selection");
    expect(visible).not.toContain("bounded local");
    const technical = markup.slice(markup.indexOf("<details"));
    expect(technical).toContain(`Case ${CASE_ID} was retained.`);
    expect(technical).toContain("Retry the same selection");
    expect(technical).toContain("DOCUMENT_ACTIVE_CONTENT");
  });

  it.each([
    ["DOCUMENT_PROCESSING_TIMEOUT", "Processing this file took too long. Try uploading it again; if it keeps happening, upload a smaller or simpler copy."],
    ["DOCUMENT_RUNTIME_UNAVAILABLE", "Document processing isn't available right now. Try again in a moment."],
  ])("keeps Try upload again for %s with its plain message", (code, message) => {
    const markup = bannerFor([failure({ code, message })]);
    expect(visibleText(markup)).toContain(`Forecast in Tableau.pdf: ${message.replaceAll("'", "&#x27;")}`);
    expect(markup).toContain(">Try upload again</button>");
    expect(markup).not.toContain("Choose a different file");
    expect(markup).toContain("<summary>Technical details</summary>");
  });

  it("keeps Try upload again for a network failure with no code", () => {
    const markup = bannerFor([failure({ code: null, message: "upload failed", rejectedBeforeStorage: false })]);
    expect(markup).toContain(">Try upload again</button>");
  });

  it("leaves a stored failed document on the existing retry flow", () => {
    // The text limit is found at extraction, after the document is stored as FAILED.
    const markup = bannerFor([failure({ code: "DOCUMENT_CONTENT_TOO_LARGE", message: REASONS[4][1], rejectedBeforeStorage: false })]);
    expect(visibleText(markup)).toContain(REASONS[4][1]);
    expect(markup).toContain(">Try upload again</button>");
    expect(markup).not.toContain("Choose a different file");
  });

  it("offers a different file only when every failed file was rejected for its content", () => {
    const markup = bannerFor([
      failure({}),
      failure({ fileName: "profile.pdf", code: "DOCUMENT_PROCESSING_TIMEOUT", message: "Processing this file took too long. Try uploading it again; if it keeps happening, upload a smaller or simpler copy." }),
    ]);
    expect(markup).toContain(">Try upload again</button>");
    expect(markup).toContain("2 documents couldn&#x27;t be uploaded");
  });

  it("falls back to the existing behaviour when no chooser is wired", () => {
    expect(bannerFor([failure({})], false)).toContain(">Try upload again</button>");
  });
});
