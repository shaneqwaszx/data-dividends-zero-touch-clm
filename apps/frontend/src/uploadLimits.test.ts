import { afterEach, describe, expect, it, vi } from "vitest";

import configSource from "../../backend/app/config.py?raw";
import mediaSource from "../../backend/app/services/document_media.py?raw";
import { ApiError, intakeZeroTouchDocument } from "./api";
import {
  MAX_CASE_UPLOAD_BYTES,
  MAX_UPLOAD_FILE_BYTES,
  UPLOAD_ACCEPT,
  UPLOAD_DOCUMENT_TYPES,
  UPLOAD_ERROR_BY_CODE,
  UPLOAD_ERRORS,
  UPLOAD_HELP_TEXT,
} from "./uploadLimits";

function backendDefaultBytes(setting: string): number {
  const match = new RegExp(`${setting}: int = Field\\(default=(\\d+) \\* 1024 \\* 1024`).exec(configSource);
  expect(match, `${setting} default not found in config.py`).not.toBeNull();
  return Number(match![1]) * 1024 * 1024;
}

function backendSupportedExtensions(): Record<string, string> {
  const constants = Object.fromEntries([...mediaSource.matchAll(/^(\w+_MEDIA_TYPE) = "([^"]+)"$/gm)].map((item) => [item[1], item[2]]));
  const block = /^SUPPORTED_EXTENSIONS = \{([\s\S]*?)^\}/m.exec(mediaSource);
  expect(block, "SUPPORTED_EXTENSIONS not found in document_media.py").not.toBeNull();
  return Object.fromEntries([...block![1].matchAll(/"(\.[a-z]+)": (?:"([^"]+)"|(\w+))/g)]
    .map((item) => [item[1], item[2] ?? constants[item[3]]]));
}

describe("shared upload limits", () => {
  it("match the backend's configured per-file and per-case defaults", () => {
    expect(MAX_UPLOAD_FILE_BYTES).toBe(backendDefaultBytes("idp_max_upload_bytes"));
    expect(MAX_CASE_UPLOAD_BYTES).toBe(backendDefaultBytes("idp_max_total_intake_bytes"));
  });

  it("match the backend's accepted extensions and media types exactly", () => {
    expect(UPLOAD_DOCUMENT_TYPES).toEqual(backendSupportedExtensions());
    for (const [extension, mediaType] of Object.entries(UPLOAD_DOCUMENT_TYPES)) {
      expect(UPLOAD_ACCEPT.split(",")).toEqual(expect.arrayContaining([extension, mediaType]));
    }
  });

  it("uses the agreed wording for the help line and every limit error", () => {
    expect(UPLOAD_HELP_TEXT).toBe("PDF, Word (.docx), text, PNG, JPEG or TIFF · up to 5 MB per file, 25 MB per case");
    expect(UPLOAD_ERRORS).toEqual({
      fileTooLarge: "This file is larger than 5 MB",
      caseTotalTooLarge: "These files add up to more than 25 MB for this case",
      unsupportedType: "This file type isn't supported. Use PDF, Word (.docx), text, PNG, JPEG or TIFF",
    });
    expect(UPLOAD_ERROR_BY_CODE).toEqual({
      DOCUMENT_TOO_LARGE: UPLOAD_ERRORS.fileTooLarge,
      DOCUMENT_TOTAL_SIZE_LIMIT_EXCEEDED: UPLOAD_ERRORS.caseTotalTooLarge,
      DOCUMENT_MEDIA_TYPE_UNSUPPORTED: UPLOAD_ERRORS.unsupportedType,
    });
  });
});

describe("backend upload errors", () => {
  afterEach(() => vi.unstubAllGlobals());

  it.each(Object.entries(UPLOAD_ERROR_BY_CODE))("shows %s with the shared wording and keeps the code", async (code, message) => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ detail: { code, message: "Backend wording." } }), { status: 413, headers: { "Content-Type": "application/json" } },
    )));
    const failure = await intakeZeroTouchDocument("case-1", new File(["x"], "a.pdf", { type: "application/pdf" }), false).catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).message).toBe(message);
    expect((failure as ApiError).code).toBe(code);
  });

  it("leaves other backend messages unchanged", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ detail: { code: "DOCUMENT_NAME_INVALID", message: "Backend wording." } }), { status: 422, headers: { "Content-Type": "application/json" } },
    )));
    const failure = await intakeZeroTouchDocument("case-1", new File(["x"], "a.pdf", { type: "application/pdf" }), false).catch((error: unknown) => error);
    expect((failure as ApiError).message).toBe("Backend wording.");
  });
});
