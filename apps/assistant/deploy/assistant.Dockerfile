# Build from the repository root. BuildKit reads assistant.Dockerfile.dockerignore beside this
# file instead of the root .dockerignore, so the shared ignore file stays unchanged.
FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/assistant HOME=/tmp
WORKDIR /opt/assistant
COPY apps/assistant/deploy/requirements.lock deploy/requirements.lock
RUN pip install --no-cache-dir --disable-pip-version-check -r deploy/requirements.lock && pip check
COPY apps/assistant/deploy/model_profiles.hosted.json deploy/
COPY apps/assistant/ai_assistant ai_assistant
COPY apps/assistant/assistant_hosting assistant_hosting
COPY apps/assistant/scripts/storage/backup_stores.py scripts/storage/backup_stores.py
# D-138 R4: the operator's ledger commands (LEDGER_RECOVERY.md): reconcile, resume-after-review,
# owner-close, and the non-destructive archive of a format-1 store.
COPY apps/assistant/scripts/budget_ledger.py scripts/budget_ledger.py
COPY apps/assistant/scripts/storage/archive_accounting_stores.py scripts/storage/archive_accounting_stores.py
# R2.2: the qualification harness the service starts for a paid Claude qualification (D-093).
COPY apps/assistant/assistant_eval assistant_eval
COPY apps/assistant/scripts/qualify_model.py scripts/qualify_model.py
# The synthetic Garden fixtures its Phase B questions run against (assistant_eval/variants.py).
COPY apps/assistant/tests/fixtures/garden_address_conflict_summary.json apps/assistant/tests/fixtures/garden_documents.json apps/assistant/tests/fixtures/garden_waiting_for_documents_summary.json apps/assistant/tests/fixtures/me_client_onboarder.json tests/fixtures/
COPY apps/backend/tests/fixtures/uat/garden-business-clean-onboarding-profile.pdf /opt/backend/tests/fixtures/uat/
# Hashed into the qualification basis, so the hosted basis equals a development checkout's.
COPY apps/assistant/tests/fixtures/eval tests/fixtures/eval
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
EXPOSE 8100
CMD ["python", "-m", "assistant_hosting.run"]
