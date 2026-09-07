FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY pdf_templates/ /app/pdf_templates/

RUN mkdir -p /data

ENV ARVELOS_DB=/data/arvelos.db
ENV ARVELOS_DATA_DIR=/data
ENV ARVELOS_FRONTEND=/app/frontend
ENV PYTHONUNBUFFERED=1

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
