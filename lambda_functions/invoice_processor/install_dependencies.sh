#!/bin/bash

# Install Dependencies and Package Lambda Function for Invoice OCR Processing
# This script is automatically called by Terraform during deployment

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "===================================================================================="
echo "Installing dependencies for Invoice Processor (Claude API)"
echo "===================================================================================="

# Clean up any existing artifacts
echo "🧹 Cleaning up existing artifacts..."
rm -rf package/
rm -f invoice_processor.zip
rm -rf __pycache__/
rm -rf *.pyc

# Create package directory
echo "📁 Creating package directory..."
mkdir -p package

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [ -f requirements.txt ]; then
    echo "Installing from requirements.txt..."
    # Install with dependencies for Lambda Python 3.12 runtime
    pip install --target package --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all: --upgrade -r requirements.txt || {
        echo "⚠️  Binary-only install failed, trying with compilation..."
        pip install --target package --upgrade -r requirements.txt
    }
    
    # Verify critical dependencies were installed
    if [ ! -d "package/anthropic" ]; then
        echo "❌ Error: anthropic library not found in package"
        exit 1
    fi
    
    if [ ! -d "package/boto3" ]; then
        echo "❌ Error: boto3 library not found in package"
        exit 1
    fi
    
    if [ ! -d "package/botocore" ]; then
        echo "❌ Error: botocore library not found in package"
        exit 1
    fi
    
    if [ ! -d "package/pydantic" ]; then
        echo "❌ Error: pydantic library not found in package"
        exit 1
    fi
    
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Error: requirements.txt not found"
    exit 1
fi

# Copy main function file
echo "📄 Copying main function file..."
cp invoice_processor.py package/

# Remove unnecessary files to reduce package size (but keep essential modules)
echo "🗑️ Optimizing package size..."
cd package

# Remove cache and compiled files
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove metadata directories (but not actual code)
find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove documentation files only (not directories that might contain code)
find . -name "*.md" -delete 2>/dev/null || true
find . -name "*.rst" -delete 2>/dev/null || true
find . -name "README*" -delete 2>/dev/null || true
find . -name "CHANGELOG*" -delete 2>/dev/null || true
find . -name "LICENSE*" -delete 2>/dev/null || true

# Remove specific test directories but be more careful
find . -type d -path "*/tests/*" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "test_*" -exec rm -rf {} + 2>/dev/null || true

# Verify critical botocore modules are still present
echo "🔍 Verifying critical modules..."
if [ ! -d "botocore/docs" ]; then
    echo "❌ Error: botocore.docs module missing after cleanup"
    exit 1
fi

if [ ! -f "anthropic/__init__.py" ]; then
    echo "❌ Error: anthropic module missing after cleanup"
    exit 1
fi

if [ ! -f "pydantic/__init__.py" ]; then
    echo "❌ Error: pydantic module missing after cleanup"
    exit 1
fi

# Check if pydantic_core exists (it's a dependency of pydantic)
if [ -d "pydantic_core" ]; then
    echo "✅ pydantic_core found in package"
else
    echo "⚠️  pydantic_core not found as separate package (may be bundled with pydantic)"
fi

echo "✅ All critical modules verified"

# Create deployment package
echo "📦 Creating deployment package..."
zip -r ../invoice_processor.zip . -q

cd ..

# Verify package was created
if [ ! -f invoice_processor.zip ]; then
    echo "❌ Error: Failed to create deployment package"
    exit 1
fi

# Show package information
PACKAGE_SIZE=$(ls -lh invoice_processor.zip | awk '{print $5}')
echo "✅ Deployment package created: invoice_processor.zip (${PACKAGE_SIZE})"

# List package contents for verification
echo "📋 Package contents:"
unzip -l invoice_processor.zip | head -20

# Clean up temporary package directory
echo "🧹 Cleaning up temporary files..."
rm -rf package/

echo "===================================================================================="
echo "✅ Invoice Processor package ready for deployment!"
echo "Package: invoice_processor.zip (${PACKAGE_SIZE})"
echo "===================================================================================="