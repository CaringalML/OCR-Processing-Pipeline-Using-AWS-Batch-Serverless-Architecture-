# Multi-stage build for faster and smaller images
# Stage 1: Build stage with full Python image for compiling dependencies
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
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
    pip install --no-cache-dir -r requirements.txt

# === EXISTING LIBRARIES (PRESERVED) ===
RUN pip install --no-cache-dir \
    pyspellchecker==0.7.2

# === ENHANCED LIBRARIES (SAFE ADDITIONS) ===
# Pre-download AI models for offline use (with error handling)
RUN python -c "\
try:\
    print('Downloading spaCy model...');\
    import subprocess;\
    subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'], check=False);\
    print('spaCy model download completed or skipped');\
except Exception as e:\
    print(f'spaCy model download failed (non-critical): {e}');\
try:\
    print('Downloading transformers model...');\
    from transformers import pipeline;\
    pipeline('text2text-generation', model='facebook/bart-base');\
    print('Transformers model cached successfully');\
except Exception as e:\
    print(f'Transformers model download failed (non-critical): {e}');\
try:\
    print('Downloading sentence-transformers model...');\
    from sentence_transformers import SentenceTransformer;\
    SentenceTransformer('all-MiniLM-L6-v2');\
    print('Sentence-transformers model cached successfully');\
except Exception as e:\
    print(f'Sentence-transformers model download failed (non-critical): {e}');\
print('=== ENHANCEMENT SETUP COMPLETE ===');\
"

# Stage 2: Runtime stage with minimal Alpine image
FROM python:3.12-alpine3.20

# Install only runtime dependencies
RUN apk add --no-cache \
    libstdc++ \
    libgomp \
    && rm -rf /var/cache/apk/*

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Create a non-root user and change ownership
RUN addgroup -g 1001 -S python && \
    adduser -S python -u 1001 -G python && \
    chown -R python:python /app

# Switch to non-root user
USER python

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Command to run the application
CMD ["python", "index.py"]