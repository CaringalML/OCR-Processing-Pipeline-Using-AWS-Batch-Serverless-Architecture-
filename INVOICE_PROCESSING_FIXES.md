# Invoice Processing Pipeline Fixes

## Issues Identified and Fixed

### 1. **Budget Tracking Table Reference Issue** ✅ FIXED
**Problem**: The invoice processor was using a hardcoded table name `ocr_budget_tracking` instead of using an environment variable.

**Fix**: Updated the `get_current_budget_usage()` and `update_budget_usage()` functions to use:
```python
budget_table = os.environ.get('BUDGET_TRACKING_TABLE', 'ocr_budget_tracking')
```

**Terraform Fix**: Added `BUDGET_TRACKING_TABLE` environment variable to the invoice processor Lambda configuration:
```hcl
BUDGET_TRACKING_TABLE = aws_dynamodb_table.ocr_budget_tracking.name
```

### 2. **Dependencies and Build Process** ✅ VERIFIED
**Problem**: Checked for missing dependencies or build issues.

**Status**: 
- ✅ `requirements.txt` exists with correct dependencies (anthropic, boto3, etc.)
- ✅ `install_dependencies.sh` exists and is properly configured
- ✅ Terraform build process properly configured

### 3. **Environment Variables Configuration** ✅ VERIFIED
**Problem**: Verified all required environment variables are configured.

**Status**:
- ✅ `ANTHROPIC_API_KEY` - Configured via terraform variable
- ✅ `DOCUMENTS_TABLE` - Points to invoice metadata table
- ✅ `PROCESSED_BUCKET` - Configured
- ✅ `SNS_TOPIC_ARN` - Configured for alerts
- ✅ `BUDGET_LIMIT` - Set to 10.0
- ✅ `BUDGET_TRACKING_TABLE` - Now properly configured

### 4. **Infrastructure Components** ✅ VERIFIED
**Components Verified**:
- ✅ SQS queues (invoice_queue, invoice_dlq) - Properly configured
- ✅ DynamoDB tables (invoice_metadata, invoice_processing_results) - Exist
- ✅ Lambda functions (invoice_uploader, invoice_processor, invoice_reader) - Configured
- ✅ API Gateway endpoints - Properly mapped
- ✅ Event source mapping - SQS to Lambda connection exists
- ✅ IAM roles and policies - Properly configured

## Configuration Requirements

### Required Terraform Variables
Ensure your `terraform.tfvars` file includes:

```hcl
# Anthropic API Key for Claude OCR
# Get your API key from: https://console.anthropic.com/
anthropic_api_key = "sk-ant-api03-YOUR_ACTUAL_API_KEY_HERE"
```

### API Endpoints
After deployment, the invoice processing endpoints will be available at:

- **Upload**: `POST /short-batch/invoices/upload`
- **Read**: `GET /short-batch/invoices/processed`

## Pipeline Flow

1. **Upload**: Client uploads invoice via API Gateway → `invoice_uploader` Lambda
2. **Queue**: Uploader stores file in S3 and sends message to `invoice_queue` SQS
3. **Process**: `invoice_processor` Lambda triggered by SQS → processes with Claude AI
4. **Store**: Results stored in DynamoDB and S3
5. **Read**: `invoice_reader` Lambda serves processed invoice data via API

## Testing Steps

To verify the fixes:

1. **Deploy Infrastructure**:
   ```bash
   terraform plan
   terraform apply
   ```

2. **Test Upload**:
   ```bash
   curl -X POST "$(terraform output -json api_endpoints | jq -r '.invoice_upload')" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@sample-invoice.pdf"
   ```

3. **Check Processing**:
   ```bash
   # Get the fileId from upload response, then:
   curl "$(terraform output -json api_endpoints | jq -r '.invoice_processed')?fileId=YOUR_FILE_ID"
   ```

4. **Monitor Logs**:
   ```bash
   aws logs tail /aws/lambda/[project]-[env]-invoice-processor --follow
   ```

## Monitoring

The following CloudWatch alarms are configured:
- Invoice DLQ message alerts
- High message count alerts  
- Budget limit notifications

## Next Steps

1. Set the `anthropic_api_key` in your `terraform.tfvars`
2. Run `terraform apply` to deploy the fixes
3. Test the invoice processing pipeline
4. Monitor CloudWatch logs for any remaining issues

All infrastructure components are properly configured and the invoice processing pipeline should now work correctly with Claude AI OCR.