# syntax=docker/dockerfile:1

# ---- base -------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ---- dependencies ---------------------------------------------------------
# Install into a separate layer so code changes don't re-run pip.
FROM base AS deps
COPY requirement.txt .
RUN pip install --prefix=/install -r requirement.txt

# ---- runtime ------------------------------------------------------------
FROM base AS runtime

# Run as an unprivileged user, not root.
RUN useradd --create-home --uid 1000 appuser

COPY --from=deps /install /usr/local
COPY . .

USER appuser

EXPOSE 8000

# $PORT is set by most PaaS hosts (Render, Railway, Fly). Falls back to 8000.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
