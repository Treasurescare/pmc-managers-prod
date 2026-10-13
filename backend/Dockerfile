# PMC Managers v2 · Backend · Elastic Beanstalk Docker platform (AL2023)
#
# IMPORTANT (v52cq rev 3):
#   AL2023 Docker single-container platform does NOT run a host-side nginx
#   reverse proxy. The container must bind directly to the port that the
#   Elastic Load Balancer forwards traffic to — which is port 80 by default.
#   So gunicorn here binds to 0.0.0.0:80 and we EXPOSE 80. No
#   Dockerrun.aws.json is needed with this setup.

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

EXPOSE 80

# Hits the plain /health probe registered at the top of server.py.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS http://localhost:80/health || exit 1

# Bind directly to port 80 — see note at top of file. Two workers fit on a
# t3.small; override via WEB_CONCURRENCY env var on the EB console if
# instance size changes.
CMD ["sh", "-c", "gunicorn server:app --workers ${WEB_CONCURRENCY:-2} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:80 --timeout 120 --keep-alive 5 --access-logfile - --error-logfile -"]
