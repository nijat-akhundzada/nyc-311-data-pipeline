# Multi-stage Dockerfile for nyc311-pipeline foundation
# Non-root runtime execution with locked dependencies

# ------------------------------------------------------------------------------
# Stage 1: Build environment
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.lock /build/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.lock

COPY pyproject.toml README.md /build/
COPY src/ /build/src/
RUN pip install --no-cache-dir --no-deps .

# ------------------------------------------------------------------------------
# Stage 2: Final non-root runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Create dedicated non-root user and group
RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv
COPY --chown=appuser:appgroup src/ /app/src/
COPY --chown=appuser:appgroup pyproject.toml README.md /app/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

# Default command verifies package import and non-root execution
CMD ["python", "-c", "import nyc311_pipeline, os; print(f'nyc311_pipeline v{nyc311_pipeline.__version__} (uid={os.getuid()})')"]
