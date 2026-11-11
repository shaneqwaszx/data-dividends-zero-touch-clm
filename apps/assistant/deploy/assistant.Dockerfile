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
# Hashed into the qualification basis, so the hosted basis equals a development checkout's.
COPY apps/assistant/tests/fixtures/eval tests/fixtures/eval
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
EXPOSE 8100
CMD ["python", "-m", "assistant_hosting.run"]
