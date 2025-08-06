# Invoice Filename Fix

## Problem
When uploading invoices, the filename appears as "Unknown" in the response instead of the actual uploaded filename.

## Root Cause Analysis
The issue could be caused by:
1. **Multipart Form Data Parsing**: Problems with extracting filename from Content-Disposition header
2. **Empty Filename**: Client not providing filename in the multipart data
3. **Content-Disposition Format**: Different formats of the filename parameter

## Fixes Applied

### 1. Enhanced Filename Extraction in `invoice_uploader.py`

**Improved multipart parsing** to handle multiple filename formats:
- `filename="value"` (standard format)
- `filename=value` (non-quoted format)
- Empty or missing filename handling

**Added fallback filename generation** when no filename is provided:
```python
if not filename:
    # Generate default name based on content type
    if 'pdf' in file_content_type.lower():
        filename = f'invoice_{int(time.time())}.pdf'
    elif 'png' in file_content_type.lower():
        filename = f'invoice_{int(time.time())}.png'
    # ... etc
```

**Added error handling** with graceful fallback to default filename.

### 2. Enhanced Debug Logging

Added comprehensive logging to track:
- Content-Disposition header parsing
- Filename extraction process  
- Final filename resolution in reader

### 3. Filename Storage Verification

Verified that both `original_filename` and `file_name` fields are properly stored in DynamoDB by the uploader and preserved during processing.

## Testing the Fix

### Test Case 1: Normal Upload with Filename
```bash
curl -X POST "https://your-api-gateway-url/short-batch/invoices/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@invoice-sample.pdf"
```

**Expected Result**: filename should show as "invoice-sample.pdf"

### Test Case 2: Upload without Filename
```bash
# Upload with empty filename
curl -X POST "https://your-api-gateway-url/short-batch/invoices/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@invoice.pdf;filename=''"
```

**Expected Result**: filename should show as "invoice_[timestamp].pdf"

### Test Case 3: JSON Upload (Fallback)
```bash
curl -X POST "https://your-api-gateway-url/short-batch/invoices/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "file": "base64_encoded_content",
    "fileName": "my-invoice.pdf",
    "contentType": "application/pdf"
  }'
```

**Expected Result**: filename should show as "my-invoice.pdf"

## Debugging

If filename still shows as "Unknown":

1. **Check CloudWatch logs** for the invoice-uploader Lambda:
   ```bash
   aws logs tail /aws/lambda/[project]-[env]-invoice-uploader --follow
   ```

2. **Look for debug messages**:
   - "DEBUG: Processing Content-Disposition: ..."
   - "DEBUG: Successfully extracted filename: ..."
   - "DEBUG: Parsed file info - filename: ..."

3. **Check DynamoDB record** to verify filename is stored:
   ```bash
   aws dynamodb get-item \
     --table-name [project]-[env]-invoice-metadata \
     --key '{"invoice_id":{"S":"your-file-id"},"upload_timestamp":{"S":"timestamp"}}'
   ```

4. **Check invoice reader logs** for filename resolution:
   ```bash
   aws logs tail /aws/lambda/[project]-[env]-invoice-reader --follow
   ```

## Files Modified

- `lambda_functions/invoice_uploader/invoice_uploader.py` - Enhanced filename parsing
- `lambda_functions/invoice_reader/invoice_reader.py` - Added debug logging

## Deployment

After making these changes, redeploy:
```bash
terraform apply
```

The filename should now be properly extracted and displayed in API responses.