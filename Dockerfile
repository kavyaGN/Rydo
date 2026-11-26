# Stage 1: build the React app. It calls the API on the same origin (/api/v1).
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Stage 2: the API, which also serves the built web app (see app/core/frontend.py).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FRONTEND_DIST_DIR=/app/frontend_dist \
    PORT=8000 \
    WEB_CONCURRENCY=2

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .
COPY --from=web /web/dist /app/frontend_dist

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=3)"

# Apply migrations and seed demo data, then serve. PORT and WEB_CONCURRENCY are set by the host.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed && exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --timeout 60"]
