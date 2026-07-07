# Arvelos — single-container web service (FastAPI backend + static frontend).
# Works on any container host: Render, Railway, Fly.io, a VPS, etc.
FROM python:3.12-slim

# System libraries WeasyPrint needs to render PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi8 shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
RUN mkdir -p /data

# The FastAPI app serves the static frontend too when ARVELOS_FRONTEND is set,
# so one container = whole website (landing, quiz, checkout, PDF delivery).
ENV ARVELOS_DB=/data/arvelos.db \
    ARVELOS_FRONTEND=/app/frontend \
    PAYMENT_PROVIDER=mock \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend
EXPOSE 8000
# $PORT is provided by most PaaS hosts; falls back to 8000 locally.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
