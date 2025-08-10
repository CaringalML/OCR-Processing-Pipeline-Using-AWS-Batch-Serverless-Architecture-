# ================================================================================================
# OCR PROCESSING PIPELINE DOCKERFILE
# ================================================================================================
# Optimized container for high-quality document processing at scale
# Size: ~400-500MB (includes language-tool-python JVM)
# Cold start: ~8-12 seconds (includes language tool initialization)

FROM python:3.12-slim

# Install Java and wget (required for language-tool-python)
RUN apt-get update && \
    apt-get install -y --no-install-recommends openjdk-17-jre-headless wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add labels for AWS Batch tracking
LABEL maintainer="Lawrence Caringal"
LABEL application="ocr-batch-processing"
LABEL version="4.1.0"
LABEL description="High-quality OCR pipeline with advanced grammar correction"

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python build tools and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-distutils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables for optimal performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Language Tool configuration
ENV JAVA_OPTS="-Xmx512m"
ENV LT_DISABLE_REMOTE_RULES=true

# AWS Batch specific optimizations
ENV MALLOC_ARENA_MAX=2

# Verify core dependencies (skip language_tool_python to avoid download during build)
RUN python -c "from spellchecker import SpellChecker; import boto3, json, re, regex, ftfy, rapidfuzz, email_validator, furl; print('✅ Core OCR dependencies verified')"

# Copy application code (single file)
COPY index.py ./

# Create non-root user for security
RUN groupadd -g 1001 python && \
    useradd -m -u 1001 -g python python && \
    chown -R python:python /app

# Create directory for AWS Batch job outputs
RUN mkdir -p /tmp/batch-output && \
    chown -R python:python /tmp/batch-output

# Switch to non-root user
USER python

# Lightweight health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Command to run the application
CMD ["python", "index.py"]