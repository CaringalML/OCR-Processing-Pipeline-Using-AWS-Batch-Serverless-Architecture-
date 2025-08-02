#!/bin/bash

# Install Dependencies Script for Document Search Lambda Function
# Automatically executed by Terraform during deployment
# This script installs Python dependencies for the document_search Lambda function

set -e

echo "🚀 [Terraform] Installing dependencies for document_search Lambda function..."

# Clean previous build artifacts
echo "🧹 Cleaning previous build artifacts..."
rm -rf __pycache__ *.pyc *.pyo
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Install Python dependencies
echo "📦 Installing Python dependencies from requirements.txt..."
pip3 install -r requirements.txt -t . --upgrade --quiet

# Clean up unnecessary files to reduce package size
echo "🗂️ Optimizing package size..."
# Remove Python cache files
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove dist-info directories (not needed at runtime)
find . -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Remove test files and documentation
find . -name "test*" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*test*.py" -delete 2>/dev/null || true
find . -name "*.md" -delete 2>/dev/null || true
find . -name "*.rst" -delete 2>/dev/null || true

echo "✅ Dependencies installed and optimized successfully!"
echo "📊 Package contents:"
ls -la | grep -E '^d|\.py$' | head -10