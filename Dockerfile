# PMC Managers v2 — production Docker image for AWS Elastic Beanstalk (Docker platform)
# Builds a single FastAPI backend container. React frontend is served separately from S3+CloudFront.
FROM python:3.11-slim

# System deps for WeasyPrint (PDF generation) + wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache dependency install
COPY backend/requirements.txt /app/backend/requirements.txt
# ⚠️ Emergent's private PyPI hosts `emergentintegrations` — must add as extra-index-url
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
      --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
      -r backend/requirements.txt

# App source (rest of backend)
COPY backend /app/backend

# Elastic Beanstalk sends traffic to port 8080 by default for Docker
ENV PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# Health check hits our FastAPI /api/v1/meta/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request,sys; \
    sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/v1/meta/health',timeout=3).status==200 else 1)"

WORKDIR /app/backend
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
