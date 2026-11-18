// Upload failures on a retained case: the backend's plain message is shown to the RM,
// and the case ID / retry wording moves into Technical details. Wording stays backend-owned.

/** Codes for a rejection caused by the file itself; uploading the same file again cannot succeed. */
export const FILE_REJECTION_CODES: ReadonlySet<string> = new Set([
  "DOCUMENT_TOO_MANY_PAGES",
  "DOCUMENT_ENCRYPTED",
  "DOCUMENT_ACTIVE_CONTENT",
  "DOCUMENT_PAGE_TOO_LARGE",
  "DOCUMENT_CONTENT_TOO_LARGE",
  "DOCUMENT_STRUCTURE_INVALID",
]);

export interface IntakeUploadFailure {
  fileName: string;
  message: string;
  code: string | null;
  /** True when the backend refused the upload before storing it (no failed document to retry). */
  rejectedBeforeStorage: boolean;
}

export interface UploadRejection {
  /** The exact request-error text this rejection belongs to; a newer error supersedes it. */
  forMessage: string;
  lines: string[];
  technical: string;
  fileProblem: boolean;
}

/** `retainedMessage` is targetedIntakeFailurePresentation(...).message for the same failures. */
export function uploadRejectionPresentation(retainedMessage: string, failures: IntakeUploadFailure[]): UploadRejection {
  const codes = failures.map(failure => failure.code).filter((code): code is string => Boolean(code));
  return {
    forMessage: retainedMessage,
    lines: failures.map(failure => `${failure.fileName}: ${failure.message}`),
    technical: codes.length > 0 ? `${retainedMessage} Codes: ${codes.join(", ")}.` : retainedMessage,
    fileProblem: failures.length > 0 && failures.every(failure =>
      failure.rejectedBeforeStorage && failure.code !== null && FILE_REJECTION_CODES.has(failure.code)),
  };
}
