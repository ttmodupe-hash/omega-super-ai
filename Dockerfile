# Luqi AI v18 — Docker Container
# Build: docker build -t luqi-ai .
# Run:   docker run -p 8000:8000 --env-file .env luqi-ai
#
FROM python:3.11-slim

LABEL maintainer="Luqi AI"
LABEL version="18.0.0"
LABEL description="Luqi AI v18 — World-class AI for Africa & Beyond"

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p uploads generated_images chroma_db

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Start server (without reload for production)
CMD ["python", "-m", "uvicorn", "backend.router:app", "--host", "0.0.0.0", "--port", "8000"]
