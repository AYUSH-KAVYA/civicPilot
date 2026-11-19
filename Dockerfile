FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies needed for geos, cffi, and health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgeos-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy source code
COPY . /app

EXPOSE 8000

# Run database setup & seed, then start Uvicorn
CMD ["sh", "-c", "python -m backend.app.db.init_db && uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
