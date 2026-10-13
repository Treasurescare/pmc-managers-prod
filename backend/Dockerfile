# PMC Managers v2 · Backend · Elastic Beanstalk Docker platform
# Built from the contents of pmc-backend-v52cq.zip. All env vars come from
# EB configuration — never from a .env baked into the image.

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Backend binds 8001 by convention; EB Docker maps the container's
    # exposed port to the instance's load balancer target automatically.
    PORT=8001

WORKDIR /app

# System libs needed by pymongo / bcrypt / weasyprint / lxml / cryptography.
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc g++ make curl \
      libffi-dev libssl-dev libpq-dev \
      libcairo2 libpango-1.0-0 libpangoft2-1.0-0 \
      libharfbuzz0b libharfbuzz-subset0 \
      libjpeg-dev libopenjp2-7-dev libtiff-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching.
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy the rest of the backend (includes scripts/ + data/ so startup
# bootstrap can seed the UNSPSC / geography / country-license masters).
COPY . /app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
  CMD curl -f http://localhost:8001/api/v1/health || exit 1

# Two workers behind gunicorn + uvicorn worker class. Scale workers via the
# WEB_CONCURRENCY env var on EB if the instance is beefier.
CMD ["sh", "-c", "gunicorn server:app --workers ${WEB_CONCURRENCY:-2} --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001 --timeout 120 --keep-alive 5 --access-logfile - --error-logfile -"]
