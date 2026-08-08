FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi8 shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY astro-engine/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY astro-engine /app
RUN mkdir -p /data

ENV ARVELOS_DB=/data/arvelos.db \
    ARVELOS_FRONTEND=/app/frontend \
    PAYMENT_PROVIDER=mock \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
