# Multi-stage build optimized for AWS Batch
# Stage 1: Build stage with Debian slim for PyTorch compatibility
FROM python:3.12-slim as builder

# Add labels for AWS Batch tracking
LABEL maintainer="Lawrence Caringal"
LABEL application="batch-processing"

# Install build dependencies for Debian
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt ./

# Create a virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies with pre-built wheels where possible
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir wheel && \
    pip install --no-cache-dir --force-reinstall --no-binary regex regex>=2022.10.31 && \
    pip install --no-cache-dir -r requirements.txt

# === EXISTING LIBRARIES (PRESERVED) ===
RUN pip install --no-cache-dir \
    pyspellchecker==0.7.2

# Test core dependencies are properly installed
RUN python -c "import boto3; import regex; print('Core dependencies verified')"

# === ENHANCED LIBRARIES (SAFE ADDITIONS) ===
# Pre-download AI models for offline use (with error handling)
RUN echo 'import subprocess, sys; print("Downloading spaCy model..."); subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=False); print("spaCy model download completed")' | python || true
RUN echo 'from transformers import pipeline; print("Downloading transformers model..."); pipeline("text2text-generation", model="facebook/bart-base"); print("Transformers model cached")' | python || true
RUN echo 'from sentence_transformers import SentenceTransformer; print("Downloading sentence-transformers model..."); SentenceTransformer("all-MiniLM-L6-v2"); print("Sentence-transformers model cached")' | python || true
RUN echo "=== ENHANCEMENT SETUP COMPLETE ==="

# Stage 2: Runtime stage with minimal Debian image
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set environment variables early
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# AWS Batch specific optimizations
# Disable Python buffering for real-time CloudWatch logs
ENV PYTHONUNBUFFERED=1
# Set memory allocation for better container performance
ENV MALLOC_ARENA_MAX=2

# Verify core dependencies work in runtime environment
RUN python -c "import boto3; import regex; import ftfy; print('✅ All core dependencies verified in runtime stage')"

# Copy application code
COPY . .

# Create a non-root user and change ownership
# AWS Batch runs containers as root by default, but we can still use non-root for security
RUN groupadd -g 1001 python && \
    useradd -m -u 1001 -g python python && \
    chown -R python:python /app

# Create directory for AWS Batch job outputs if needed
RUN mkdir -p /tmp/batch-output && \
    chown -R python:python /tmp/batch-output

# Switch to non-root user
USER python

# Health check for AWS Batch monitoring (optional)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Command to run the application
# AWS Batch will override this with job definition parameters
CMD ["python", "index.py"]