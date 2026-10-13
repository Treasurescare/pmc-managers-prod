# PMC Managers v2 · Backend · Elastic Beanstalk Docker platform (AL2023)
#
# v52cq rev 4 — crash-fast + direct exec so container startup errors
# surface in EB container logs instead of being masked behind sh.

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

# Exec form (no sh wrapper) so signals and crash exit codes propagate
# straight to Docker/EB. --preload forces the FastAPI import to happen
# BEFORE workers fork, so any import error crashes the master cleanly
# with a visible stack trace in /var/log/eb-docker/containers/.
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
