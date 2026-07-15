# Build stage
ARG PYTHON_IMAGE_DIGEST="sha256:c3d81d25b3154142b0b42eb1e61300024426268edeb5b5a26dd7ddf64d9daf28"
# IA-164: digest listy manifestów oficjalnego python:3.12-slim.
# Rotacja: docker buildx imagetools inspect python:3.12-slim (pole "Digest:").
FROM python:3.12-slim@${PYTHON_IMAGE_DIGEST} AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Runtime stage
FROM python:3.12-slim@${PYTHON_IMAGE_DIGEST}

WORKDIR /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY --from=builder /install /usr/local

COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/
COPY entrypoint.sh .

RUN mkdir -p /app/data /app/.numba_cache \
    && chown -R appuser:appgroup /app/data /app/.numba_cache \
    && sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

ENV NUMBA_CACHE_DIR=/app/.numba_cache

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
