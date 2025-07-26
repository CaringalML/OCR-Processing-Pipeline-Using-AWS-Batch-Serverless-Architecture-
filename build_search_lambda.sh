#!/bin/bash

# Build script for document_search Lambda function
# Run this before terraform apply

echo "Building document_search Lambda function..."

cd lambda_functions/document_search

# Clean previous build
rm -rf __pycache__ *.pyc

# Install dependencies locally (they'll be packaged by Terraform)
echo "Installing dependencies..."
pip install -r requirements.txt -t .

echo "Dependencies installed successfully!"
echo "Now run: terraform apply"