# PMC Managers v2 · Backend · Elastic Beanstalk Docker platform (AL2023)
#
# v52cq rev 8 — final fixes confirmed from production logs:
#   1. REMOVED docker-compose.yml from this bundle. EB's AL2023 Docker
#      platform actually RUNS docker-compose when the file is present, and
#      the old file mapped host 8080 → container 80, leaving host port 80
#      with no listener — which is exactly why the ELB kept failing even
#      though gunicorn was up. Without a compose file EB generates its own
#      single-container definition from this Dockerfile (EXPOSE 80).
#   2. curl is verified present in the image (the previous running image
#      logged healthcheck exitCode=127 — curl not found — because that
#      image predates this Dockerfile).
#   3. gunicorn binds directly to 0.0.0.0:80 (AL2023 has no host nginx).
#   4. App boots in <2s; master-data seeding runs in a background task.
#   5. config.py loads secrets from SSM Parameter Store when
#      PMC_SSM_PREFIX is set; individual EB env vars take priority.
#   6. Only ADMIN_PASSWORD and OWNER_PASSWORD are hard-required in prod;
#      the five STAFF_PW_* keys fall back to demo values with a log line
#      (seed is skip-if-exists so existing accounts are never touched).

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ make curl \
      libffi-dev libssl-dev libpq-dev \
      libcairo2 libpango-1.0-0 libpangoft2-1.0-0 \
      libharfbuzz0b libharfbuzz-subset0 \
      libjpeg-dev libopenjp2-7-dev libtiff-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir gunicorn

COPY . /app

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s --start-period=45s --retries=3 \
  CMD curl -fsS http://localhost:80/health || exit 1

CMD ["gunicorn", "server:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:80", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--capture-output"]
