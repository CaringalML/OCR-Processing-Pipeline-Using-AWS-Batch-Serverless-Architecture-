#!/bin/bash
# Install Dependencies Script for Short Batch Processor Lambda Function
# Automatically executed by Terraform during deployment
# Smart packaging with change detection - only rebuilds when source files or dependencies change

set -e

FUNCTION_NAME="ocr-processor-batch-short-batch-processor"
PACKAGE_NAME="short_batch_processor.zip"
PACKAGE_DIR="package"
SOURCE_FILE="short_batch_processor.py"

# Always use requirements.txt (standalone mode with all dependencies bundled)
echo "🚀 [Terraform] Installing dependencies for short_batch_processor Lambda function..."
echo "📦 Using standalone mode - bundling all dependencies in package"
REQUIREMENTS_FILE="requirements.txt"

# Checksum files for intelligent change detection
CHECKSUMS_FILE=".package_checksums"
CURRENT_CHECKSUMS_FILE=".current_checksums"

echo "🔍 Checking for changes to optimize build time..."

# Calculate current checksums
calculate_checksums() {
    {
        # Source code checksum
        if [ -f "$SOURCE_FILE" ]; then
            echo "source: $(md5sum "$SOURCE_FILE" | cut -d' ' -f1)"
        fi
        
        # Requirements checksum
        if [ -f "$REQUIREMENTS_FILE" ]; then
            echo "requirements: $(md5sum "$REQUIREMENTS_FILE" | cut -d' ' -f1)"
        fi
        
    } | sort
}

# Check if package needs rebuilding
needs_rebuild() {
    # If no previous checksums or package doesn't exist, rebuild
    if [ ! -f "$CHECKSUMS_FILE" ] || [ ! -f "$PACKAGE_NAME" ]; then
        return 0  # needs rebuild
    fi
    
    # Calculate current checksums
    calculate_checksums > "$CURRENT_CHECKSUMS_FILE"
    
    # Compare with previous checksums
    if ! diff -q "$CHECKSUMS_FILE" "$CURRENT_CHECKSUMS_FILE" > /dev/null 2>&1; then
        return 0  # needs rebuild
    else
        return 1  # no rebuild needed
    fi
}

# Build package with optimization
build_package() {
    echo "📦 Building optimized Lambda deployment package..."
    
    # Clean up previous builds
    echo "🧹 Cleaning previous build artifacts..."
    rm -rf "$PACKAGE_DIR"
    rm -f "$PACKAGE_NAME"
    
    # Create package directory
    mkdir -p "$PACKAGE_DIR"
    
    # Install Python dependencies
    echo "📥 Installing Python dependencies from requirements.txt..."
    pip3 install -r "$REQUIREMENTS_FILE" -t "$PACKAGE_DIR/" --upgrade --quiet
    
    # Copy source code
    echo "📋 Copying Lambda function source code..."
    cp "$SOURCE_FILE" "$PACKAGE_DIR/"
    
    # Optimize package size
    echo "🗂️ Optimizing package size for AWS Lambda..."
    cd "$PACKAGE_DIR"
    
    # Remove Python cache and compiled files
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    find . -name "*.pyd" -delete 2>/dev/null || true
    
    # Remove package metadata
    find . -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    
    # Remove test files and documentation
    find . -name "test*" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*test*" -name "*.py" -delete 2>/dev/null || true
    find . -name "*.md" -delete 2>/dev/null || true
    find . -name "*.rst" -delete 2>/dev/null || true
    find . -name "*.txt" -not -name "requirements.txt" -delete 2>/dev/null || true
    
    # Remove unnecessary spaCy model files (keep only core)
    find . -path "*/spacy/lang/*" -not -path "*/spacy/lang/en*" -exec rm -rf {} + 2>/dev/null || true
    find . -path "*/spacy/tests*" -exec rm -rf {} + 2>/dev/null || true
    
    # Remove NLTK test data
    find . -path "*/nltk/test*" -exec rm -rf {} + 2>/dev/null || true
    find . -path "*/nltk/*/test*" -exec rm -rf {} + 2>/dev/null || true
    
    # Remove numpy tests
    find . -path "*/numpy/*/test*" -exec rm -rf {} + 2>/dev/null || true
    find . -path "*/numpy/tests*" -exec rm -rf {} + 2>/dev/null || true
    
    # Remove source files for compiled extensions
    find . -name "*.c" -delete 2>/dev/null || true
    find . -name "*.cpp" -delete 2>/dev/null || true
    find . -name "*.pyx" -delete 2>/dev/null || true
    find . -name "*.pxd" -delete 2>/dev/null || true
    
    # Create ZIP
    echo "📦 Creating ZIP package..."
    zip -r "../$PACKAGE_NAME" . -q
    cd ..
    
    # Save checksums for next time
    calculate_checksums > "$CHECKSUMS_FILE"
    
    # Clean up temp files
    rm -f "$CURRENT_CHECKSUMS_FILE"
    
    package_size=$(du -h "$PACKAGE_NAME" | cut -f1)
    echo "✅ Deployment package created: $PACKAGE_NAME ($package_size)"
}

# Main execution logic with intelligent rebuilding
if needs_rebuild; then
    if [ -f "$CHECKSUMS_FILE" ]; then
        echo "🔄 Changes detected in source files or dependencies - rebuilding package..."
    else
        echo "📦 No previous package found - building new deployment package..."
    fi
    build_package
    echo "📝 Package optimized and ready for Lambda deployment"
else
    echo "✅ No changes detected - reusing existing optimized package: $PACKAGE_NAME"
    package_size=$(du -h "$PACKAGE_NAME" | cut -f1)
    echo "📊 Current package size: $package_size"
fi

# Clean up temporary files
rm -f "$CURRENT_CHECKSUMS_FILE"

echo "🎉 [Terraform] Dependencies installation completed successfully!"
echo "🚀 Lambda function package is ready for deployment"