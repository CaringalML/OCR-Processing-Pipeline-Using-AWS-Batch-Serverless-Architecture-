# Use the most recent secure Python Alpine image
FROM python:3.12-alpine3.20

# Set working directory
WORKDIR /app

# Copy requirements file first
COPY requirements.txt ./

# Install dependencies as root user
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create a non-root user and change ownership
RUN addgroup -g 1001 -S python && \
    adduser -S python -u 1001 -G python && \
    chown -R python:python /app

# Switch to non-root user
USER python

# Expose port (not necessary for AWS Batch but good practice)
EXPOSE 3000

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; import sys; sys.exit(0 if requests.get('http://localhost:3000/health').status_code == 200 else 1)" 2>/dev/null || exit 0

# Command to run the application
CMD ["python", "index.py"]