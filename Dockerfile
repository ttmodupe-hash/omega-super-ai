# syntax=docker/dockerfile:1
# ==============================================================================
# OMEGA-LUQI ENGINE - production Dockerfile (replaces the Nixpacks auto-build)
#
# SECURITY LAW: runtime-only secrets (JWT_SECRET_SIGNING_KEY, KIMI_API_KEY,
# LUQI_ADMIN_SECRET, DATABASE_URL, MONTHLY_TOKEN_BUDGET_USD) are NEVER declared
# here - no ARG, no ENV. Railway injects service variables into the runtime
# container; nothing sensitive enters a build layer or the image history.
# (Nixpacks generated ARG/ENV for every variable, which is what tripped
# BuildKit's SecretsUsedInArgOrEnv warning - even with blanked values.)
#
# Python 3.12 pinned: matches nixpacks.toml - psycopg2-binary 2.9.9 ships no
# Python 3.13 wheel, and the sklearn trio was sandbox-verified on 3.12.
# ==============================================================================

# ---------- Build stage: compile wheels ----------
FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
# gcc lives only in this stage: source-build insurance, never ships in the image
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/wheels -r requirements.txt

# If a BUILD step ever genuinely needs a secret (e.g. a private pip index),
# use a BuildKit secret mount - it exists for that one RUN only and is never
# written to any layer:
#
#   RUN --mount=type=secret,id=PIP_INDEX_TOKEN \
#       pip wheel --index-url "https://user:$(cat /run/secrets/PIP_INDEX_TOKEN)@pypi.example.com/simple" ...

# ---------- Runtime stage: lean, non-root ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# libgomp1: OpenMP runtime for scikit-learn (hybrid_ai front-door classifier)
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 luqi
WORKDIR /app
COPY requirements.txt .
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels
COPY --chown=luqi:luqi . .
# Runtime writes (ops journal restore, SQLite WAL fallback) need a writable app dir
RUN chown luqi:luqi /app
USER luqi
EXPOSE 8000
# Docker-level healthcheck mirrors Railway's healthcheckPath (other container hosts)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/v1/health',timeout=4)" || exit 1
# Single boot path (unchanged): Postgres-gated alembic, then uvicorn core.main:app on $PORT
CMD ["bash", "start.sh"]
