# Session 3 R2 current OCR and browser receipt

Date: 2026-10-04. Authorized verification only. This task changed no application,
test, production configuration, dependency, schema, provider, mapping, business rule
or Git state. Historical OCR receipts, PRE manifests and gates were not modified.
This receipt is focused evidence, not an independent Quality Gate or Live claim.

## Results and exact content

| Current verification | Result | Execution time | Lifecycle |
| --- | --- | --- | --- |
| `test_s2_local_ocr.py` | 36 passed, 0 skipped, exit 0; 1 dependency warning | 13.78 s | 16.500 s |
| Authenticated actual-scan Chromium journey | 1 journey, 87 assertions passed, 0 skipped, exit 0 | 4.026 s | 11.469 s |

The pack includes six actual Tesseract cases: PNG, JPEG, TIFF, scanned PDF, mixed
native/scanned PDF and poor PNG. `CLM_REAL_OCR_REQUIRED=1` prevented silently skipping
required real OCR. Other pack cases cover extraction/provenance and adverse bounds.
The warning was Starlette's `httpx` test-client deprecation; no test failed.

The fresh pack helper initially classified the passing footer as a wrapper failure
because its regex omitted the optional `, 1 warning` clause. Actual pytest exit 0 and
`36 passed, 1 warning in 13.78s` were preserved. Result bookkeeping was reconciled
against that completed sanitized log, retaining the original helper-failure JSON.
The passing tests were not rerun and no production remediation was made.

Worktree: `C:\Users\shane\.codex-clean2\worktrees\onboarding-intelligence-goldtier-sandbox\data-dividends-zero-touch-clm`.
Preparation, pack-before, pack-after, browser-before and browser-after all identified
the same **218-file application manifest**:

`fd18199cf4bbb90892dab8b5d58327733d19c068d12e2feb97f7afb455bace8c`.

The manifest includes backend `app/**/*.py`, frontend `src` `.ts/.tsx/.css` files,
backend `pyproject.toml`, frontend `package.json`, `package-lock.json` and
`index.html`. The Windows Python 3.12 helpers sort `Path` objects with
`sorted(files)`, using Windows case-insensitive path-component ordering. For each
file, the aggregate SHA-256 receives the original-case repository-relative POSIX
path as UTF-8, one NUL byte and the binary SHA-256 of its content. There is no extra
separator or newline. Both full browser manifests have identical artifact hashes.
Git was outside this task's authorization and was not accessed.

## Fresh image, commands and isolation

The current `scripts/ocr_validation.Dockerfile` was copied into the fresh ignored
`.runtime/s3-r2-ocr-b8c2d4` directory. Its Dockerfile-specific ignore file excluded
everything except backend `pyproject.toml`, `app` and `tests`, with explicit final
exclusions for `.env*`, Git, virtual environments, Node dependencies, bytecode and
pytest caches. The transferred context was 2.08 MB. No private configuration entered
the build. Build preparation completed before coordinator release; the pack and
browser ran only after release, sequentially.

```text
docker build --tag clm-s3-r2-ocr:20261004-b8c2d4
  --file .runtime/s3-r2-ocr-b8c2d4/ocr_validation.Dockerfile .
docker image inspect clm-s3-r2-ocr:20261004-b8c2d4 --format {{.Id}}
.venv/Scripts/python.exe -B .runtime/s3-r2-ocr-b8c2d4/run_pack.py
.venv/Scripts/python.exe -B .runtime/s3-r2-ocr-b8c2d4/run.py
```

All commands ran from the named worktree. The verified fresh image tag is
`clm-s3-r2-ocr:20261004-b8c2d4`; its raw image ID is:

`sha256:a03571861f327c7258d3fcef5c279ef3537f7c07182b85e66e9ab3439e265b73`.

The image ID was checked before each run and again after cleanup. The current
backend directory was mounted read-only over the image's backend for execution.
Only the fresh task helper directory was additionally mounted for the browser.

| Runtime | Observed value |
| --- | --- |
| Linux Python / Tesseract | `3.12.10` / `5.3.0` |
| Pillow / pypdfium2 | `12.3.0` / `5.13.0` |
| Windows Node / Playwright | `22.23.3` / `1.56.1` |
| Chromium | `141.0.7390.37`, headless |
| ACRA / GoldTier / ownership | Explicit `mock` |
| IDP / persistence | Explicit `local_pdf_text` / `memory` |
| Ordinary OCR route | `/usr/bin/tesseract`, `stdout -l eng --psm 6 tsv` |

The original **60-second lifecycle bound and 12-second ordinary OCR deadline** were
unchanged. Browser assertion/read deadlines remained 15 seconds. Pack Docker run
used `--network none`; browser Docker run used an inspected dedicated internal
network and had no default route or published ports. Both used read-only root
filesystems, user `65534:65534`, `--cap-drop ALL`, `no-new-privileges`, 1 GiB memory,
128 PIDs, 2 CPUs and `/tmp:rw,noexec,nosuid,size=268435456`.

The browser reached the real container loopback backend through the approved raw
`docker exec -i` TCP relay bound only to `127.0.0.1:38765`; Vite bound only to
`127.0.0.1:34173` and proxied API requests to that relay. The relay copied bytes
without substituting HTTP/API responses. Settings dotenv loading was disabled;
the temporary Vite config used `envDir:false`. Synthetic credentials were generated
only for the run, not printed or written to task/repository files. Their processes
and container were removed. No `.env`, Mongo or external provider was accessed.

Browser requests were restricted to the owned frontend origin; service workers
and downloads were disabled. External requests forwarded: 0; unexpected external
requests: 0; one exact known font stylesheet was neutralized with empty local CSS.
API response substitutions: 0. Dependency downloads occurred only during the
authorized build, before the network-isolated verification runs.

## Actual scan journey assertions

The existing synthetic creator signed in, opened New onboarding, created a Mock
Singapore case and selected the fresh generated 2400 by 1000 PNG through the normal
file control. The raster used 44-pixel Arial and a fictional ownership table; no
extraction response or provider result was substituted.

- The real response retained one Local, reviewed PNG document, four distinct strict
  identity fields, all `MATCH` and auto-confirmed `ACCEPTED`, and real page 1 /
  `PAGE_1` with immutable document version 1.
- Page and field extraction method was `LOCAL_TESSERACT_OCR`, quality `HIGH`, raw
  OCR mean `95.16945748648648` and word count 37. The UI separately displayed source
  agreement, verification, deterministic evidence score, score formula and the
  warning that evidence scores and OCR word confidence are not probabilities.
- The explicit fictional natural-person observation retained 70 percent and
  `2026-10-04`, without inferred share counts or denominators. Server-authored
  observation ID, document ID, page and version bindings were visible and retained.
- Ownership stayed `REVIEW_REQUIRED`; the observation stayed `PROPOSED` and the
  discrepancy still required review. No manual creator receipt existed. Backend
  creator binding and evidence/ownership-edit capabilities were checked.
- The creator could view the proposed document source choice, but its observation
  checkbox remained unchecked. Viewing did not alter the retained analysis or
  submit an ownership decision.
- The case stayed `WAITING_FOR_REVIEW`, without target confirmation or submission.
  Every non-Search target ledger operation was `NOT_ATTEMPTED`. Ownership-decision
  requests, confirmation requests and target writes attempted were all 0.

## Evidence hashes and cleanup

All paths below are under `.runtime/s3-r2-ocr-b8c2d4`. Sanitized logs, helpers and
manifests are retained as ignored task evidence for the coordinator. No historical
helper/result file was overwritten.

| Artifact | SHA-256 |
| --- | --- |
| `pack-output.log` | `18349974fbf8c3b2cb6cf42dd8d2c58ca54db2db9b3f402f2c2f5912f4380671` |
| `pack-result.json` | `9b32d0e996c6214d1224184548152abd4c87024ce9799f55e363aad9b59e75e2` |
| Original `pack-result-summary-parser-failure.json` | `3b20dfc0ca27f4d02ed6ed0113cc05063615e40757ef8350d0c3641129aace27` |
| Browser `result.json` | `0e26051d67105a040779046ae55d45917caf88e284ca6b4bc8bc3baedf2bf525` |
| `browser-result.json` | `4aed12ffa2479400f71f108b3c3b1f3a1391eabba25ecd971818d22eb75832cc` |
| `source-manifest-before.json` and `source-manifest-after.json` | `896614faf2ee344a30ab53cd628333ec4c5c0209c60c27aad483d6fa053f7d34` |
| Executed `run_pack.py` | `ca02b97428b45f465f304600ad3ad1ffbe3e9dd4549757fefb8443c012a4475d` |
| Executed `run.py` | `379c13e0b9931424d39a988000633ac416076cd0595318b3716ac2a1d35c8bbc` |
| Executed `journey.mjs` | `4ab2685ad5ebc7d256c1affbfb70e7374287d5b4da124c0fac29fa39358dfe24` |
| Copied `ocr_validation.Dockerfile` | `d2301392c8e2a8b27bec5c4bf84eacc52a4b2ec97916e16ae68a7cb289ee021a` |
| Task Dockerfile-specific ignore | `a175c5a362335b8e50912cd027c835f268e8107183e1e6660ee25ff86eeb1db1` |
| `final-cleanup-proof.json` | `e270032747d72671db5305486597959b80e8dead7a2a4932c57e3532b5f923b5` |

The exact pack container `clm-s3-r2-ocr-pack-b8c2d4`, browser container and internal
network `clm-s3-r2-ocr-browser-b8c2d4` are absent. The owned Chromium, Vite and relay
processes stopped. Both assigned ports were checked for absent listeners and bound
successfully after cleanup. Only the freshly generated scan and resolved owned Vite
cache were deleted; unrelated resources and previous helper history were preserved.

The verified image tag and ID remain available for **coordinator final cleanup**.
Only this new report is a durable task change. No API/type, schema, connector,
configuration, business-rule, mapping, auth/security, architecture, provider-status
or application-runtime behavior was changed by this verification task. No gate or
publication action was taken.
