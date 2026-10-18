# Production Dockerfile for BharatLink Nexus AI — Google Cloud Run Edition
FROM python:3.10-slim

# Set working directory & environment variables
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    ENVIRONMENT=production

# Install curl for healthcheck probe
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code, assets, and templates
COPY . .

# Expose default Cloud Run port
EXPOSE 8080

# Run with uvicorn bound to 0.0.0.0 and dynamic $PORT
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 2 --timeout-keep-alive 30
