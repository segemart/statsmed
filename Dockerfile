# Statsmed API (FastAPI + PostgreSQL). Built from repo root.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY statsmed/ statsmed/
COPY web/ web/
COPY backend/ backend/

RUN pip install --no-cache-dir -e ".[web]" && \
    pip install --no-cache-dir -r backend/requirements.txt

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
