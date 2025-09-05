# syntax=docker/dockerfile:1.4
# Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Proxy build args (optional)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

# Set proxy env for pip if provided
ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    PIP_DEFAULT_TIMEOUT=100

# System packages: none required for runtime; keep image minimal

# Copy requirements and install Python dependencies
# This layer is cached as long as requirements.txt doesn't change
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check without curl
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys,urllib.request; \
import socket; socket.setdefaulttimeout(5); \
urllib.request.urlopen('http://localhost:8000/', timeout=5)"

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
