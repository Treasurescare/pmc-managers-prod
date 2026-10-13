# PMC Managers v2 · Backend · Elastic Beanstalk Docker platform
# For: AL2023 Docker platform (single-container). EB will build this image
# from source on every "Upload and deploy". All env vars come from the EB
# configuration — never from a baked-in .env.
#
# IMPORTANT:
#   - We rely on EB's built-in nginx reverse proxy (port 80 → container's
#     EXPOSEd port). Do NOT ship a Dockerrun.aws.json alongside this file.
#   - The master-data seeding (UNSPSC + geography) is kicked off in the
#     background by server.py at startup — the HTTP app is ready in <2s
#     so EB healthchecks pass immediately. Seeding then finishes within
#     ~2–3 min and only runs when its collections are empty (idempotent).

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System libs needed by pymongo / bcrypt / weasyprint / lxml / cryptography.
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ make curl \
      libffi-dev libssl-dev libpq-dev \
      libcairo2 libpango-1.0-0 libpangoft2-1.0-0 \
      libharfbuzz0b libharfbuzz-subset0 \
      libjpeg-dev libopenjp2-7-dev libtiff-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps (cached layer).
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir gunicorn

# App code + seed data (needed by background bootstrap).
COPY . /app

EXPOSE 8001

# Lightweight self-check: hit the plain /health root-level probe that is
# always registered first in server.py.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS http://localhost:8001/health || exit 1

# One worker is enough for a t3.small — scale via WEB_CONCURRENCY on the EB
# console. The uvicorn worker class is mandatory for ASGI (FastAPI).
CMD ["sh", "-c", "gunicorn server:app --workers ${WEB_CONCURRENCY:-2} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001 --timeout 120 --keep-alive 5 --access-logfile - --error-logfile -"]
