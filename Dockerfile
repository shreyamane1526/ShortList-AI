# syntax=docker/dockerfile:1

FROM python:3.11-slim

# --- System deps (minimal) ---
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Improve layer caching: only copy requirements first
COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source code
COPY . /app

# Ensure project root is on PYTHONPATH
ENV PYTHONPATH=/app

EXPOSE 8000

# Dev reload is enabled by setting RELOAD=true
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 ${RELOAD:+--reload}"]

