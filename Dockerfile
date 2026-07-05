# Luqi AI v13 — Docker Deployment
# Build:  docker build -t luqi-ai .
# Run:    docker run -p 8000:8000 --env-file .env luqi-ai
# Or:     docker-compose up -d

FROM python:3.11-slim

LABEL maintainer="Luqi AI"
LABEL version="13.0.0"
LABEL description="Luqi AI — Africa's AI Platform with 85 languages and virtual labs"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data uploads memory

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "start_server.py"]
