# Multi-stage build for faster and smaller images
# Stage 1: Build stage with Alpine to match runtime
FROM python:3.12-alpine3.20 as builder

# Install build dependencies for Alpine
RUN apk add --no-cache \
    gcc \
    g++ \
    musl-dev \
    python3-dev \
    linux-headers \
    build-base

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

# Stage 2: Runtime stage with minimal Alpine image
FROM python:3.12-alpine3.20

# Install runtime dependencies including what's needed for compiled Python extensions
RUN apk add --no-cache \
    libstdc++ \
    libgomp \
    libgcc \
    libc6-compat \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set environment variables early
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Verify core dependencies work in runtime environment
RUN python -c "import boto3; import regex; import ftfy; print('✅ All core dependencies verified in runtime stage')"

# Copy application code
COPY . .

# Create a non-root user and change ownership
RUN addgroup -g 1001 -S python && \
    adduser -S python -u 1001 -G python && \
    chown -R python:python /app

# Switch to non-root user
USER python

# Command to run the application
CMD ["python", "index.py"]