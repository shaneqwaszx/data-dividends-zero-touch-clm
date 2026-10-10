"""Task-owned offline validation; no implementation mutation or protected resources."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.venv/Scripts/python.exe'
RECEIPT = ROOT / 'tmp/sdq01-r3-validation.json'
ENV = os.environ.copy()
ENV['PYTHONDONTWRITEBYTECODE'] = '1'
ENV['PYTHONUNBUFFERED'] = '1'
ENV['PYTHONPATH'] = os.pathsep.join(str(ROOT / p) for p in ('', 'apps/backend', 'tests/contract'))
ENV['CLM_E2E_SYNTHETIC_MONGO_PORT'] = '27419'
ENV['PATH'] = r'C:\Program Files\Tesseract-OCR' + os.pathsep + ENV['PATH']
previous = json.loads((ROOT / 'tmp/sdq01-r3-validation-missing-ocr.json').read_text(encoding='utf-8'))
previous['checks'][-1]['log'] = 'tmp/sdq01-r3-shard1-missing-ocr.log'
(ROOT / 'tmp/sdq01-r3-validation-missing-ocr.json').write_text(json.dumps(previous, indent=2) + '\n', encoding='utf-8')
observations: list[dict[str, object]] = [previous['checks'][0]]


def run(name: str, argv: list[str], *, cwd: Path = ROOT, env: dict[str, str] = ENV) -> None:
    log = ROOT / f'tmp/sdq01-r3-{name}.log'
    started = time.monotonic()
    stamp = datetime.now(timezone.utc).isoformat()
    print(f'START {name}', flush=True)
    with log.open('wb') as stream:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False)
    observation = {'name': name, 'argv': argv, 'cwd': str(cwd), 'started_utc': stamp,
                   'exit_code': result.returncode, 'elapsed_seconds': round(time.monotonic() - started, 3),
                   'log': log.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(log.read_bytes()).hexdigest()}
    observations.append(observation)
    RECEIPT.write_text(json.dumps({'checks': observations}, indent=2) + '\n', encoding='utf-8')
    print(f'END {name}: exit={result.returncode}; seconds={observation["elapsed_seconds"]}', flush=True)
    if result.returncode:
        sys.exit(result.returncode)


# The preceding isolated historical-environment PASS is retained; only the full shard
# missing an installed prerequisite is repeated, with unchanged source/assertions/deadline.
run('original-shard1', [str(PYTHON), '-B', 'scripts/run_e2e.py', '--backend-port', '18900',
    '--frontend-port', '19400', '--timeout-seconds', '60', '--shard', '1/2'])
run('harness', [str(PYTHON), '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_run_e2e.py', '-v'])
run('focused-backend', [str(PYTHON), '-B', '-m', 'pytest', 'apps/backend/tests/test_batch_review_decisions.py',
    'apps/backend/tests/test_final_review_editing.py', 'apps/backend/tests/test_sponsor_demo_fixtures.py',
    'apps/backend/tests/test_idp_classification_line_endings.py',
    'apps/backend/tests/test_target_reliability_recovery_ux.py',
    'apps/backend/tests/test_target_classification_continuation.py',
    '-o', 'addopts=', '-p', 'no:cacheprovider', '-q'])
run('frontend', ['npm.cmd', 'test', '--', '--reporter=dot'], cwd=ROOT / 'apps/frontend')
run('typecheck', ['npm.cmd', 'run', 'typecheck'], cwd=ROOT / 'apps/frontend')
for checker in ('project_state', 'architecture', 'tooling_config', 'policy_authority', 'external_provider_readiness', 'secrets'):
    run(checker, [str(PYTHON), '-B', f'scripts/check_{checker}.py'])
