# Short Batch Processor - Lambda Function

## Overview
This Lambda function processes images using Claude API for OCR text extraction. It's designed for AWS Lambda Python 3.10 runtime.

## ⚠️ Python Runtime Update
**Required: Python 3.10**  
AWS Lambda Python 3.9 is being deprecated. This function has been updated and optimized for Python 3.10.

## Key Features
- **Claude API OCR**: Uses Claude 3.5 Sonnet for high-quality text extraction
- **Budget Management**: Tracks API usage with configurable limits
- **Dead Letter Queue**: Routes messages to DLQ when budget exceeded
- **SNS Notifications**: Sends alerts for budget thresholds
- **DynamoDB Integration**: Tracks processing status and results
- **SQS-Triggered**: Processes batches from SQS queue

## Files Structure
```
short_batch_processor/
├── short_batch_processor.py     # Main Lambda function (Python 3.10)
├── requirements.txt             # Python dependencies
├── build_lambda_310.sh         # Build script for Python 3.10
├── package/                    # Dependencies directory (generated)
└── README.md                   # This file
```

## Dependencies
```
boto3>=1.35.0,<2.0.0
anthropic>=0.45.0,<1.0.0  
httpx>=0.25.0,<1.0.0
```

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key | - |
| `DOCUMENTS_TABLE` | Yes | DynamoDB table name | - |
| `PROCESSED_BUCKET` | Yes | S3 bucket for results | - |
| `DEAD_LETTER_QUEUE_URL` | No | SQS DLQ URL | - |
| `SNS_TOPIC_ARN` | No | SNS topic for alerts | - |
| `BUDGET_LIMIT` | No | Monthly budget limit (USD) | 10.0 |

## Building for Deployment

### Option 1: Using the build script (Recommended)
```bash
chmod +x build_lambda_310.sh
./build_lambda_310.sh
```

### Option 2: Manual build
```bash
# Create package directory
mkdir package

# Install dependencies
pip install --target package -r requirements.txt

# Copy function
cp short_batch_processor.py package/

# Create zip
cd package
zip -r ../lambda-deployment.zip .
```

### Option 3: Using Docker (Best for consistency)
```bash
docker run --rm \
  -v "$PWD":/var/task \
  -w /var/task \
  public.ecr.aws/lambda/python:3.10 \
  bash -c "pip install --target package -r requirements.txt && cp short_batch_processor.py package/ && cd package && zip -r ../lambda-deployment.zip ."
```

## Deployment Steps

1. **Update Lambda Runtime to Python 3.10**
   - Go to AWS Lambda console
   - Select `ocr-processor-batch-short-batch-processor`
   - Runtime settings → Edit → Python 3.10 → Save

2. **Upload Code**
   - Upload `lambda-deployment-310.zip`
   - Or use AWS CLI: `aws lambda update-function-code --function-name ocr-processor-batch-short-batch-processor --zip-file fileb://lambda-deployment-310.zip`

3. **Verify Environment Variables**
   - Ensure all required variables are set

4. **Test**
   ```json
   {
     "Records": [{
       "body": "{\"bucket\": \"your-bucket\", \"key\": \"test-image.jpg\", \"document_id\": \"test-123\"}"
     }]
   }
   ```

## Known Issues & Solutions

### pydantic_core Import Error
**Error**: `No module named 'pydantic_core._pydantic_core'`  
**Cause**: Binary incompatibility between local build and Lambda runtime  
**Solutions**:
1. Use Docker build method (recommended)
2. Build on Amazon Linux 2 or AWS Cloud9
3. Use Lambda Layers for dependencies

### Budget Tracking
The function tracks Claude API usage:
- **Input tokens**: $3 per million
- **Output tokens**: $15 per million  
- **Alert threshold**: 90% of budget
- **Hard stop**: 100% of budget (messages go to DLQ)

## Processing Pipeline
1. **Receive SQS Message** - Get document details
2. **Budget Check** - Verify usage against limit
3. **Download Image** - Retrieve from S3
4. **Claude OCR** - Extract text using Claude API
5. **Cost Tracking** - Update budget usage
6. **Store Results** - Save to S3 and DynamoDB
7. **Send Alerts** - Notify if approaching limit

## Error Handling
- **Budget Exceeded**: Message sent to DLQ, SNS alert sent
- **Import Errors**: Clear error messages with suggested fixes
- **API Failures**: Logged to CloudWatch, status updated in DynamoDB
- **Invalid Files**: Marked as failed with error details

## Performance
- **Processing Time**: ~2-5 seconds per document
- **Memory**: 1024MB allocated
- **Timeout**: 900 seconds (15 minutes)
- **File Size Limit**: 10MB
- **Supported Formats**: JPEG, PNG, WebP

## Version History
- **v5.0.0** (2025-08-04): Python 3.10 update, improved error handling, lazy loading
- **v4.0.0**: Initial Claude API integration
- **v3.0.0**: Previous AWS Textract version (deprecated)