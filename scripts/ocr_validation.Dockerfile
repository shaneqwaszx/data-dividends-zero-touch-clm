# Build only for the authorized synthetic local OCR acceptance pack.
FROM python:3.12.10-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr=5.3.0-2 tesseract-ocr-eng=1:4.1.0-2 fonts-dejavu-core=2.37-6 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY apps/backend/pyproject.toml /workspace/apps/backend/pyproject.toml
COPY apps/backend/app /workspace/apps/backend/app
RUN python -m pip install --no-cache-dir '/workspace/apps/backend[dev]'
COPY apps/backend/tests /workspace/apps/backend/tests
ENV PYTHONDONTWRITEBYTECODE=1 CLM_REAL_OCR_REQUIRED=1
CMD ["python", "-B", "-m", "pytest", "apps/backend/tests/test_s2_local_ocr.py", "-q"]
