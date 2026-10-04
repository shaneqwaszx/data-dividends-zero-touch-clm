# Session 2 actual OCR browser receipt

Date: 2026-10-04. Assigned verification only; no application, test, durable harness,
configuration, dependency, persistence, provider, business-rule or Git changes.

## Result and tested content

The final authenticated Chromium journey passed: **1 journey, 50 counted assertions,
0 skipped, 4.400 seconds browser time, 10.218 seconds complete lifecycle**. This is
focused browser evidence, not an independent Quality Gate or a Live-provider claim.
The separately reported 31-case actual OCR pack was not rerun by this task.

Worktree: `C:\Users\shane\.codex-clean2\worktrees\onboarding-intelligence-goldtier-sandbox\data-dividends-zero-touch-clm`.
Branch: `feat/onboarding-intelligence-goldtier-sandbox`.
BASE, HEAD and locally recorded `origin/main`:
`1d426e0ceddc32d80b0aaec293c62fb761f2fecf`.
The tested application includes the current uncommitted Session 2 content; HEAD alone
does not identify that content. No fetch or Git mutation was performed.

The before and after source-manifest SHA-256 values were identical:

`f08d4fd94b393ebc0c5e0bcb97e3c634d803e4af147bee81dafe3ba51fab4c67`.

The manifest contains 217 files: every `apps/backend/app/**/*.py`, every frontend
`src` file with suffix `.ts`, `.tsx` or `.css`, backend `pyproject.toml`, frontend
`package.json`, `package-lock.json` and `index.html`. The Windows Python 3.12
orchestrator uses `sorted(files)` on `pathlib.WindowsPath` objects, applying Windows
case-insensitive path-component ordering before converting each path to text. The
digest receives each original-case repository-relative POSIX path encoded as UTF-8,
one NUL byte, then the binary SHA-256 digest of that file, with no additional
separator or newline. Sorting relative POSIX strings instead gives a different
order. Other workers' E2E-only changes are outside this manifest.

## Runtime and isolation

| Component | Observed version / mode |
| --- | --- |
| Image | `clm-s2-ocr:20261004` |
| Image ID | `sha256:39fe52fc0d8c58bf1b5cbafe6a9b99decb1600ac20ece259293c5dfd99e0caec` |
| Linux Python | `3.12.10` |
| Tesseract | `5.3.0` |
| Pillow | `12.3.0` |
| pypdfium2 | `5.13.0` |
| Windows Node | `22.23.3` |
| Playwright | Existing installed `1.56.1` |
| Chromium | `141.0.7390.37`, headless |
| ACRA / GoldTier / ownership | Explicit `mock` |
| IDP | Explicit `local_pdf_text`, `/usr/bin/tesseract`, 12-second OCR timeout |
| Persistence | Explicit `memory` |

The image's older application copy was replaced at runtime by the current backend
directory mounted read-only. A dedicated Docker internal network was inspected as
`Internal=true`; the container's `/proc/net/route` contained no default route. The
container ran as `65534:65534`, root filesystem read-only, all capabilities dropped,
`no-new-privileges`, 1 GiB memory, 128 PIDs, 2 CPUs and a 256 MiB
`/tmp` tmpfs with `noexec,nosuid`. It had zero published ports.

Docker Desktop did not expose the internal network's first attempted published
loopback port even though container-local health returned 200. That attempt failed
readiness and was cleaned up. The final run retained network isolation and used a
task-owned raw TCP tunnel listening only on `127.0.0.1:38765`. For each connection,
`docker exec -i` connected to actual container loopback port 8000 and copied bounded
chunks of stdin/socket/stdout bytes. The tunnel never parsed or rewrote HTTP or API
responses. Frontend Vite listened only on `127.0.0.1:34173` and proxied `/api` to that
tunnel.

The temporary backend launcher disabled Settings dotenv loading before importing
`app.main`, passed `Settings(_env_file=None, ...)`, generated synthetic credential
hashes only in memory and selected the explicit modes above. A temporary Vite config
used `envDir:false`, current frontend source, the existing React plugin and an owned
temporary cache directory. No `.env` was read. The credential was generated afresh
in the orchestrator and passed through process environment without printing or
writing it to repository/task files; the container and all credential-bearing
processes were removed.

Browser HTTP requests were admitted only to the assigned frontend loopback port;
service workers and downloads were disabled. The known Google Fonts stylesheet was
fulfilled with empty CSS without forwarding it. Unexpected external requests: 0;
external requests forwarded: 0; neutralized stylesheet requests: 1. API response
interceptions: 0. No remote OCR or external provider was called.

## Executed commands and temporary profile

Commands ran from the worktree above. The Python orchestrator owned every process,
container and network and cleaned each in `finally`.

```powershell
.venv/Scripts/python.exe -B .runtime/s2-ocr-browser-a724be/run.py
```

The final orchestrator dispatched these Docker and frontend/browser commands
(`CLM_E2E_PASSWORD` refers to an ephemeral process-environment value, never a literal
credential argument):

```text
docker network create --internal clm-s2-ocr-browser-a724be
docker network inspect clm-s2-ocr-browser-a724be --format {{.Internal}}
docker run -d --name clm-s2-ocr-browser-a724be
  --network clm-s2-ocr-browser-a724be --read-only --user 65534:65534
  --cap-drop ALL --security-opt no-new-privileges:true
  --memory 1g --pids-limit 128 --cpus 2
  --tmpfs /tmp:rw,noexec,nosuid,size=268435456
  --mount type=bind,source=<worktree>/apps/backend,target=/workspace/apps/backend,readonly
  --mount type=bind,source=<worktree>/.runtime/s2-ocr-browser-a724be,target=/task,readonly
  --workdir /tmp --env CLM_E2E_PASSWORD
  --env PYTHONPATH=/workspace/apps/backend --env PYTHONDONTWRITEBYTECODE=1
  clm-s2-ocr:20261004 python -B /task/serve.py
<worktree>/.venv/Scripts/python.exe -B <worktree>/.runtime/s2-ocr-browser-a724be/relay.py
node <worktree>/apps/frontend/node_modules/vite/bin/vite.js
  --config <worktree>/.runtime/s2-ocr-browser-a724be/vite.config.mjs --configLoader native
node <worktree>/.runtime/s2-ocr-browser-a724be/journey.mjs
docker rm -f clm-s2-ocr-browser-a724be
docker network rm clm-s2-ocr-browser-a724be
```

`<worktree>` expands to the absolute worktree specified above. The final temporary
scripts were removed after recording their SHA-256 identifiers:

| Temporary file | SHA-256 |
| --- | --- |
| `run.py` | `a97b7650f594b635a24c796b3dd86bdee4354220442d5437153926311ea41706` |
| `serve.py` | `b4f5243d4665c66530ecb5960b1d9eda0104e820769b4a0a30536ad52c7f60f1` |
| `relay.py` | `7e2cf91704e39fc6b164aa4c32626401b292cf831a4bbe9c8c3220232bc21391` |
| `journey.mjs` | `02164489baa367390ced0b073fd1fc9c8bb59ff533768026a3e83ed8b11bf5f3` |
| `vite.config.mjs` | `9133c54e4e6200e4fdcfd61d4c55451d8187bb2d92affec31304f964f1e98c50` |

Temporary launcher/assertion corrections preceded the final passing run: native
Vite config loading resolved its closed module-runner transform error; a bounded
ownership poll allowed the asynchronous document checkpoint to finish; the source
selector assertion was aligned with the current explicit
`USER_SUPPLIED_DECLARATION` initial value. No application fix was made by this task.

## Safe browser assertions

The journey used the existing synthetic creator, navigated through New onboarding,
created a Singapore Mock case and uploaded a generated 2400 by 1000 PNG through
`#home-document`. Pillow drew fictional evidence in 44-pixel Arial; its actual raster
bytes entered the normal upload/media/render/Tesseract/provider/service path.
There was no substituted extraction payload.

The actual response and the visible full-case panels established:

- One successful Local document, four strict identity fields, one real page reference
  `PAGE_1` and immutable `document_version=1`.
- Page and field method `LOCAL_TESSERACT_OCR`, quality `HIGH`, raw OCR mean
  `95.02234173809524` and 42 OCR words. Field scores identified
  `DETERMINISTIC_EVIDENCE_SCORE` and `LABEL_SCORE_TIMES_OCR_MEAN_OVER_100`; the UI
  stated that the score is not a probability. All four synthetic identity comparisons
  were `MATCH`.
- One explicitly observed fictional `NATURAL_PERSON`, explicit 70 percent and
  as-of date `2026-10-04`. The server retained the document ID, version 1, page 1 and
  observation ID; extraction did not author an ownership decision.
- Document page provenance and the proposed ownership disclosure were visible.
  Source agreement, extraction quality/method/score and verification were separate
  UI concepts.
- Ownership analysis remained `REVIEW_REQUIRED`, its observation remained
  `PROPOSED`, its discrepancy required review and no manual creator receipt existed.
  The creator review form was visible and backend authorization permitted ownership
  editing.
- Deliberately viewing the document-observation source option left its observation
  checkbox unchecked and did not submit a decision or change the server analysis.
- The summary remained `WAITING_FOR_REVIEW`. Every target ledger operation other
  than Search was `NOT_ATTEMPTED`. No target-confirmation or ownership-decision
  request was issued by the journey. Target writes attempted: 0.

The browser evidence covers this synthetic one-page PNG journey. Multi-page PDF,
JPEG, TIFF, poor-image and adverse-media coverage remains the separately executed
offline OCR pack; this receipt does not imply an additional browser run for them.

## Cleanup and handoff

The final orchestrator stopped its exact Chromium, Vite and raw-tunnel process trees,
removed the exact container and network, and successfully bound both assigned ports
after cleanup. A final task-scoped check reconfirmed their absence and removed only
the resolved `.runtime/s2-ocr-browser-a724be` directory, including the synthetic scan,
temporary scripts, Vite cache and safe intermediate result. The shared OCR image
remains available. Other workers' ports, containers and runtime artifacts were not
touched.

Only this receipt is retained from the task. No API/type, schema, connector,
configuration, business-rule, mapping, auth/security, architecture, provider-status
or application-runtime behavior was changed. Parent integration and independent
review remain the next authorized owners; no publication action was taken.
