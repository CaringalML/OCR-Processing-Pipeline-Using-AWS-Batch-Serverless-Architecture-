# Use the most recent secure Python Alpine image
FROM python:3.12-alpine3.20

# Set working directory
WORKDIR /app

# Install system dependencies required for text processing libraries
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    build-base \
    && rm -rf /var/cache/apk/*

# Copy requirements file first
COPY requirements.txt ./

# Install Python dependencies as root user
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install text correction libraries
RUN pip install --no-cache-dir \
    textblob==0.17.1 \
    pyspellchecker==0.7.2

# Download TextBlob corpora for better text correction
RUN python -m textblob.download_corpora lite

# Download spaCy language model
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application code
COPY . .

# Create a non-root user and change ownership
RUN addgroup -g 1001 -S python && \
    adduser -S python -u 1001 -G python && \
    chown -R python:python /app

# Remove build dependencies to reduce image size (keep runtime dependencies)
RUN apk del gcc musl-dev build-base

# Switch to non-root user
USER python

# Set environment variables for better Python performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Command to run the application
CMD ["python", "index.py"]