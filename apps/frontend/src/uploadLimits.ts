/**
 * The one frontend copy of the backend's document upload limits and accepted types.
 *
 * Kept in sync with apps/backend/app/config.py (idp_max_upload_bytes, idp_max_total_intake_bytes)
 * and apps/backend/app/services/document_media.py (SUPPORTED_EXTENSIONS); uploadLimits.test.ts
 * checks both. The backend stays authoritative: these values only shape the wording and the
 * early client-side checks.
 */

export const MAX_UPLOAD_FILE_BYTES = 5 * 1024 * 1024;
export const MAX_CASE_UPLOAD_BYTES = 25 * 1024 * 1024;

/** Accepted extension -> the media type the browser must report for it. */
export const UPLOAD_DOCUMENT_TYPES: Readonly<Record<string, string>> = {
  ".pdf": "application/pdf",
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".txt": "text/plain",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".tif": "image/tiff",
  ".tiff": "image/tiff",
};

/** The `accept` attribute for every document upload control. */
export const UPLOAD_ACCEPT = [
  ...new Set(Object.values(UPLOAD_DOCUMENT_TYPES)),
  ...Object.keys(UPLOAD_DOCUMENT_TYPES),
].join(",");

const TYPE_NAMES = "PDF, Word (.docx), text, PNG, JPEG or TIFF";

/** Shown next to every upload control. */
export const UPLOAD_HELP_TEXT = `${TYPE_NAMES} · up to 5 MB per file, 25 MB per case`;

export const UPLOAD_ERRORS = {
  fileTooLarge: "This file is larger than 5 MB",
  caseTotalTooLarge: "These files add up to more than 25 MB for this case",
  unsupportedType: `This file type isn't supported. Use ${TYPE_NAMES}`,
} as const;

/** Backend error codes that carry the same meaning as the messages above. */
export const UPLOAD_ERROR_BY_CODE: Readonly<Record<string, string>> = {
  DOCUMENT_TOO_LARGE: UPLOAD_ERRORS.fileTooLarge,
  DOCUMENT_TOTAL_SIZE_LIMIT_EXCEEDED: UPLOAD_ERRORS.caseTotalTooLarge,
  DOCUMENT_MEDIA_TYPE_UNSUPPORTED: UPLOAD_ERRORS.unsupportedType,
};
