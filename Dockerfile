# Dockerfile
FROM python:3.11-slim

# Force rebuild - change this to invalidate cache
ARG CACHE_BUST=2026-01-24-12-52-00

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port (if needed for health checks)
EXPOSE 8080

# Health check - comprehensive check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

# Default command
CMD ["python", "main.py"]
