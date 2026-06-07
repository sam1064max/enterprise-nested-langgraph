# syntax=docker/dockerfile:1.7

# ---- Stage 1: build dependencies in a uv-enabled image ----
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install uv (https://github.com/astral-sh/uv)
RUN pip install --no-cache-dir uv==0.4.18

# Copy only the project files needed to resolve dependencies first
COPY pyproject.toml uv.lock* requirements.txt requirements-dev.txt ./
COPY config ./config
COPY app.py ./
COPY config ./config
COPY graphs ./graphs
COPY guardrails ./guardrails
COPY models ./models
COPY observability ./observability
COPY tools ./tools
COPY storage ./storage

RUN uv export --format requirements-txt --no-hashes --no-dev --no-install-project -o requirements-prod.txt \
    && uv export --format requirements-txt --no-hashes --no-install-project -o requirements-all.txt

# ---- Stage 2: lean runtime image ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    PORT=8080

# Create a non-root user
RUN groupadd --system --gid 1001 appgroup \
    && useradd --system --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR ${APP_HOME}

# Install runtime dependencies into the system Python
COPY --from=builder /build/requirements-prod.txt /tmp/requirements-prod.txt
RUN pip install --no-cache-dir -r /tmp/requirements-prod.txt \
    && rm -f /tmp/requirements-prod.txt

# Copy the application
COPY --chown=appuser:appgroup app.py ./
COPY --chown=appuser:appgroup config ./config
COPY --chown=appuser:appgroup graphs ./graphs
COPY --chown=appuser:appgroup guardrails ./guardrails
COPY --chown=appuser:appgroup models ./models
COPY --chown=appuser:appgroup observability ./observability
COPY --chown=appuser:appgroup tools ./tools
COPY --chown=appuser:appgroup storage ./storage
COPY --chown=appuser:appgroup pyproject.toml ./

USER appuser

EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys; from app import run; sys.exit(0 if run('healthcheck') is not None else 1)" || exit 1

CMD ["python", "app.py"]
