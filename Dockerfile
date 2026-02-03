# Dockerfile
FROM python:3.11-slim

# Force rebuild - change this to invalidate cache
ARG CACHE_BUST=2026-02-03-CREATOR-DASHBOARD-SIMPLIFIED-FINAL

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    postgresql-client \
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

# Default command - run Discord bot with proper error handling
CMD ["python", "run_bot.py"]
