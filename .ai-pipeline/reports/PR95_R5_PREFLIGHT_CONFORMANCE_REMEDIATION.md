# PR95-R5 preflight conformance remediation

## Authority and correction

R5-QG-01 is within the explicitly authorized P2-06 opaque scoped-read correction.
The independent preflight requires unexpected foreign query results to fail as an
internal integrity error. The first R5 Quality Gate correctly returned FAIL; that report
and the preceding adversarial CLEAR report remain immutable historical evidence.

The sole product change adds a canonical string-ID membership check against the
captured authorized set in CapturedCaseBatch.read_selected, before the selected-cohort
skip. Foreign, missing, null and non-string routing IDs now raise the existing
PersistenceDataInvalidError. Authorized excluded-date rows continue to skip without
full schema/nested decoding. Existing finally cleanup consumes and clears the batch on
success or error. No additional query, clock read, authorization owner, codec, shared
validator, schema, migration or provider behavior is introduced.

## Failing-first and focused evidence

The new regression parametrizes foreign/missing/null/integer keys with empty and
nonempty selections. All eight cases failed before correction (8 failed,19 deselected;
.runtime/pr95-r5-scoped-integrity-red.log). They verify no full decoder call, cleared
raw/callback/authority references and rejection of reuse. The corrected focused owner,
dashboard compatibility, activity and portfolio suite passes95 tests in5.51s
(.runtime/pr95-r5-scoped-integrity-focused2.log). A later formatting-only wrap addresses
a101-character new test signature; no assertion changes.

The initial edit script rejected its assumed LF bytes without changing product content;
its accompanying test invocation used two nonexistent filenames. Both invocation
errors are retained in the session; the successful edit preserves every existing line
ending and uses the actual phase17/phase18 regression suites. No acceptance claim uses
the invalid invocation. The first configured Ruff run found the new signature E501;
that failure remains in integrity-ruff.log and must receive a passing rerun.

## Exact evidence boundary

Before this correction the complete ordinary backend suite passed2818 with171 skips
and3 warnings in1073.47s; backend-full.log/exit0. This is the frozen V2 pre-correction
baseline, not proof for the corrected product bytes. Its physical tests were executed
separately by the independent reviewer (165PASS,0skip). Required final-source full
backend, physical regression, new comprehensive adversarial review and a separate
independent re-gate remain pending. Earlier frontend/type/build/browser/contract/
governance evidence remains attributed to unchanged owned paths, with affected checks
rerun or explicitly assessed by the final gate. No local implementation commit is
permitted before exact final independent PASS.

The original R4 FAIL, R5 FAIL and all prior R2/R3 corrections remain preserved. This
implementer report supplies no independent verdict. No GitHub write, push, hosted
review request, PR96 modification, protected database operation, dotenv read or provider
request is authorized or performed. CASE_TIMING_PROFILE.md remains unchanged.
