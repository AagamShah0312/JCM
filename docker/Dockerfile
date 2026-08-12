# Django backend — Python 3.12
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
        libpq-dev \
        build-essential \
        tesseract-ocr \
        libtesseract-dev \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ .
RUN mkdir -p staticfiles logs media

EXPOSE 8000
CMD ["gunicorn", "judicial_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
