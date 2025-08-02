# OCR Pipeline Fixes Summary

## Issues Resolved

### 1. Files Stuck at "uploaded" Status 
**Problem**: Long batch files remained at "uploaded" status and never progressed to "processing"

**Root Cause**: SQS processor Lambda function couldn't handle:
- Direct upload messages from long_batch_uploader (different format than S3 events)
- New S3 file structure (`long-batch-files/` vs expected `uploads/`)

**Fix Applied**: Updated `lambda_functions/sqs_to_batch_submitter/sqs_to_batch_submitter.py` to:
- Handle both S3 event messages and direct Lambda upload messages
- Recognize `long-batch-files/` file structure
- Extract file_id correctly from new S3 key format

### 2. Missing/Empty Metadata Fields
**Problem**: API responses showed empty `fileName` and metadata fields (`publication`, `year`, `title`, `author`)

**Root Cause**: Uploader functions stored `original_filename` but system expected `file_name`, plus missing standard metadata fields

**Fix Applied**: Updated all uploader Lambda functions:
- `lambda_functions/long_batch_uploader/long_batch_uploader.py`
- `lambda_functions/short_batch_uploader/short_batch_uploader.py`  
- `lambda_functions/s3_uploader/s3_uploader.py`

Added consistent metadata structure:
```python
item = {
    'original_filename': original_filename,  # Keep for backwards compatibility
    'file_name': original_filename,           # Add the expected field name
    # Add default metadata fields that the reader expects
    'publication': form_data.get('publication', ''),
    'year': form_data.get('year', ''),
    'title': form_data.get('title', ''),
    'author': form_data.get('author', '')
}
```

### 3. Duplicate Job Submission Issue
**Problem**: Each upload created two jobs - first job did nothing, second job processed the file

**Root Cause**: Both Lambda uploaders AND S3 EventBridge were sending messages to SQS queues:
- `long_batch_uploader` sent direct SQS message
- S3 EventBridge also sent message for the same file upload
- Result: 2 messages = 2 jobs

**Fix Applied**: 
- Removed direct SQS message sending from both uploaders
- Updated Lambda functions to rely only on S3 EventBridge notifications
- Removed SQS queue URL environment variables from uploaders
- Removed SQS permissions from uploader IAM policies

### 4. Terraform Configuration Issues
**Problem**: Lambda functions couldn't be updated via terraform due to `ignore_changes` lifecycle rules

**Fix Applied**: Removed all `ignore_changes` blocks from `lambda.tf`:
```hcl
# Old (prevented updates):
lifecycle {
  ignore_changes = [
    source_code_hash,
    filename
  ]
}

# New (allows updates):
# Removed ignore_changes to allow code updates
```

## Current Working Pipeline

```
Upload → Long Batch Uploader → S3 → EventBridge → SQS Queue → SQS Processor → AWS Batch → Processing → Results
  ✅           ✅              ✅       ✅          ✅           ✅           ✅          ✅            ✅
```

### Status Progression
- ✅ `uploaded` → `processing` → `completed`
- ✅ Single job per upload (no duplicates)
- ✅ Batch jobs are successfully submitted and processed
- ✅ Complete metadata is stored and returned

### Fixed Message Handling
The SQS processor now handles both:

1. **S3 Event Messages** (from EventBridge):
```json
{
  "detail": {
    "bucket": {"name": "bucket-name"},
    "object": {"key": "long-batch-files/file-id.ext"}
  }
}
```

2. **Direct Upload Messages** (from Lambda uploaders):
```json
{
  "file_id": "file-id",
  "processing_type": "long-batch",
  "metadata": {
    "s3_bucket": "bucket-name",
    "s3_key": "long-batch-files/file-id.ext"
  }
}
```

## Files Updated

### Core Processing Logic
- `lambda_functions/sqs_to_batch_submitter/sqs_to_batch_submitter.py` - Fixed message handling and S3 path recognition

### Uploader Functions (Metadata Fixes)
- `lambda_functions/long_batch_uploader/long_batch_uploader.py` - Added complete metadata structure
- `lambda_functions/short_batch_uploader/short_batch_uploader.py` - Added complete metadata structure  
- `lambda_functions/s3_uploader/s3_uploader.py` - Added complete metadata structure

### Infrastructure Configuration (Terraform)
- `lambda.tf` - Removed `ignore_changes` blocks to allow Lambda code updates
- `lambda.tf` - Removed `LONG_BATCH_QUEUE_URL` and `SHORT_BATCH_QUEUE_URL` environment variables from uploaders
- `iam.tf` - Removed SQS permissions from long_batch_uploader and short_batch_uploader IAM policies

### Files NOT Changed (Already Compatible)
- `aws_batch/index.py` - Already designed to work with any S3 structure via environment variables
- All other Lambda functions - No changes needed

## Test Results

### Before Fixes
```json
{
  "fileName": "",
  "processingStatus": "uploaded", 
  "metadata": {
    "publication": "",
    "year": "",
    "title": "",
    "author": ""
  }
}
```

### After Fixes  
```json
{
  "fileName": "test-9.jpeg",
  "processingStatus": "completed",
  "metadata": {
    "publication": "Future Transportation Quarterly",
    "year": "2025", 
    "title": "Electric Car Vision Report",
    "author": "Tesla Research Team"
  }
}
```

## Deployment Commands Used

### Manual Lambda Updates (for immediate fix)
```bash
# Update SQS Processor
aws lambda update-function-code --function-name "ocr-processor-batch-sqs-batch-processor" --zip-file "fileb://lambda_functions/sqs_to_batch_submitter/sqs_to_batch_submitter.zip"

# Update Long Batch Uploader  
aws lambda update-function-code --function-name "ocr-processor-batch-long-batch-uploader" --zip-file "fileb://lambda_functions/long_batch_uploader/long_batch_uploader.zip"

# Update Short Batch Uploader
aws lambda update-function-code --function-name "ocr-processor-batch-short-batch-uploader" --zip-file "fileb://lambda_functions/short_batch_uploader/short_batch_uploader.zip"

# Update Main Uploader
aws lambda update-function-code --function-name "ocr-processor-batch-uploader" --zip-file "fileb://lambda_functions/s3_uploader/s3_uploader.zip"
```

### Terraform Deployment (for consistent infrastructure)
```bash
# Full deployment (will now work correctly)
terraform apply

# Targeted deployment (for specific functions)
terraform apply -target=aws_lambda_function.sqs_batch_processor -target=aws_lambda_function.long_batch_uploader -target=aws_lambda_function.short_batch_uploader -target=aws_lambda_function.uploader
```

## Usage Examples

### Upload with Complete Metadata
```bash
curl -X POST "https://api-gateway-url/batch/long-batch/upload" \
  -F "file=@document.pdf" \
  -F "title=Document Title" \
  -F "author=Author Name" \
  -F "publication=Publication Name" \
  -F "year=2025" \
  -F "description=Document description"
```

### Check Processing Status
```bash
curl "https://api-gateway-url/batch/long-batch/processed?fileId=your-file-id"
```

## System Status: ✅ FULLY OPERATIONAL

- Pipeline flow working end-to-end
- Status progression working correctly  
- Complete metadata capture and retrieval
- AWS Batch processing functioning
- Terraform configuration consistent with deployed state