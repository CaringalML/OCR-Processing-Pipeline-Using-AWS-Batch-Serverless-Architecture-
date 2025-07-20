# AWS Batch OCR Processor (Go Implementation)

This is a Go implementation of the OCR processing pipeline for AWS Batch, optimized for performance and minimal Docker image size.

## Features

- **Textract Integration**: Extracts text from documents using AWS Textract
- **Comprehend Analysis**: Performs sentiment analysis, entity detection, key phrase extraction, and syntax analysis
- **Text Formatting**: Smart text formatting with URL/email fixing and paragraph detection
- **DynamoDB Integration**: Stores processing results and updates file status
- **Optimized Docker Image**: Uses multi-stage build with scratch base image (~15MB)
- **Structured Logging**: JSON-formatted logs with configurable log levels

## Building

### Local Build
```bash
cd aws_batch/src
go mod tidy
go build -o ocr-processor index.go
```

### Docker Build
```bash
docker build -t ocr-processor:latest .
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| S3_BUCKET | S3 bucket containing the file to process | Yes |
| S3_KEY | S3 object key of the file to process | Yes |
| FILE_ID | Unique identifier for the file | Yes |
| DYNAMODB_TABLE | DynamoDB table for file metadata | Yes |
| AWS_REGION | AWS region | Yes |
| LOG_LEVEL | Logging level (ERROR, WARN, INFO, DEBUG) | No (default: INFO) |
| AWS_BATCH_JOB_ID | AWS Batch job ID (set automatically by Batch) | No |

## Docker Image Optimization

The Docker image uses a multi-stage build process:

1. **Builder Stage**: Uses `golang:1.21-alpine` to compile the Go binary
2. **Runtime Stage**: Uses `scratch` (empty base image) for minimal size
3. **Final Image Size**: ~15MB (compared to ~400MB+ for Node.js Alpine)

### Benefits:
- **Faster Pull Times**: Significantly reduced image size means faster container startup in AWS Batch
- **Security**: Minimal attack surface with no OS utilities or shells
- **Performance**: Native compiled Go binary with optimized build flags

## Performance Improvements

- **Native Compilation**: Go compiles to native machine code
- **Concurrent Processing**: Utilizes Go's goroutines for parallel operations where applicable
- **Memory Efficiency**: Lower memory footprint compared to Node.js
- **Startup Time**: Faster cold start times in AWS Batch

## Usage

The processor runs as a batch job and expects environment variables to be set by AWS Batch:

```bash
docker run \
  -e S3_BUCKET=my-bucket \
  -e S3_KEY=documents/sample.pdf \
  -e FILE_ID=123e4567-e89b-12d3-a456-426614174000 \
  -e DYNAMODB_TABLE=ocr-file-metadata \
  -e AWS_REGION=us-east-1 \
  ocr-processor:latest
```

## Logging

The application uses structured JSON logging with the following format:
```json
{
  "timestamp": "2024-01-20T10:30:45Z",
  "level": "INFO",
  "message": "Processing file",
  "batchJobId": "abc123",
  "fileId": "xyz789",
  "data": {
    "bucket": "my-bucket",
    "key": "document.pdf"
  }
}
```