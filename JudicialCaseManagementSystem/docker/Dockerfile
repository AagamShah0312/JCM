# Dockerfile for Django Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application
COPY backend/ .

# Create necessary directories
RUN mkdir -p staticfiles logs media

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Create superuser (optional, for initial setup)
# RUN python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

EXPOSE 8000

CMD ["gunicorn", "judicial_backend.wsgi:application", "--bind", "0.0.0.0:8000"]
