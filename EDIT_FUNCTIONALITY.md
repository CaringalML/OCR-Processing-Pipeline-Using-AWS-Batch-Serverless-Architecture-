# OCR Edit Functionality

This document describes the new edit functionality that allows users to modify OCR results (refinedText and formattedText) after processing.

## Overview

The edit functionality enables users to update the `refinedText` and `formattedText` fields of processed OCR documents through a REST API endpoint. All edits are tracked with history and the original text is preserved.

## API Endpoint

### Edit OCR Results

**Endpoint:** `PATCH /processed/{fileId}`

**Description:** Updates the refinedText and/or formattedText for a specific file.

**Request Headers:**
```
Content-Type: application/json
```

**Path Parameters:**
- `fileId` (required): The unique identifier of the file to edit

**Request Body:**
```json
{
  "refinedText": "Updated refined text content (optional)",
  "formattedText": "Updated formatted text content (optional)"
}
```

**Response (200 OK):**
```json
{
  "fileId": "123e4567-e89b-12d3-a456-426614174000",
  "refinedText": "Updated refined text content",
  "formattedText": "Updated formatted text content",
  "userEdited": true,
  "lastEdited": "2025-01-27T10:30:00Z",
  "editHistory": [
    {
      "edited_at": "2025-01-27T10:30:00Z",
      "edited_fields": ["refined_text", "formatted_text"],
      "previous_refined_text": "Original refined text",
      "previous_formatted_text": "Original formatted text"
    }
  ],
  "message": "OCR results updated successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Missing required fields or file not yet processed
- `404 Not Found`: File ID not found
- `500 Internal Server Error`: Server error

## Features

### 1. Edit Tracking
- All edits are tracked with timestamps
- Edit history maintains the last 10 edits
- Each edit records which fields were changed and their previous values

### 2. Original Text Preservation
- The first time a file is edited, the original `refinedText` and `formattedText` are saved
- Original text is stored in `original_refined_text` and `original_formatted_text` fields

### 3. User Edit Flag
- Files that have been edited are marked with `user_edited: true`
- This helps distinguish between system-processed and user-modified content

### 4. Partial Updates
- Users can update just `refinedText`, just `formattedText`, or both
- At least one field must be provided in the request

## Implementation Details

### Lambda Function
- **Name:** `ocr-editor`
- **Runtime:** Python 3.9
- **Memory:** 256 MB
- **Timeout:** 60 seconds

### DynamoDB Updates
The function updates the processing results table with:
- Updated text fields
- Edit history
- Original text preservation (first edit only)
- Last edited timestamp
- User edited flag

### IAM Permissions
The editor Lambda function has permissions to:
- Query and update DynamoDB tables (file metadata and processing results)
- Write to CloudWatch logs

## Usage Example

### Using cURL
```bash
# Edit both refinedText and formattedText
curl -X PATCH https://your-api-gateway-url/dev/processed/123e4567-e89b-12d3-a456-426614174000 \
  -H "Content-Type: application/json" \
  -d '{
    "refinedText": "This is the corrected refined text",
    "formattedText": "This is the corrected formatted text"
  }'

# Edit only refinedText
curl -X PATCH https://your-api-gateway-url/dev/processed/123e4567-e89b-12d3-a456-426614174000 \
  -H "Content-Type: application/json" \
  -d '{
    "refinedText": "This is the corrected refined text"
  }'
```

### Using JavaScript
```javascript
async function editOCRResults(fileId, refinedText, formattedText) {
  const response = await fetch(`${API_BASE_URL}/processed/${fileId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      refinedText: refinedText,
      formattedText: formattedText
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}
```

## Frontend Integration

To integrate this functionality into a frontend application:

1. **Display Current Text**: First fetch the current OCR results using the existing GET endpoint
2. **Edit Interface**: Provide text areas or rich text editors for users to modify refinedText and formattedText
3. **Save Changes**: Call the PATCH endpoint with the modified text
4. **Show History**: Optionally display the edit history to users

### Example React Component

```jsx
import React, { useState, useEffect } from 'react';

function OCREditor({ fileId }) {
  const [refinedText, setRefinedText] = useState('');
  const [formattedText, setFormattedText] = useState('');
  const [saving, setSaving] = useState(false);
  const [editHistory, setEditHistory] = useState([]);

  // Fetch current OCR results
  useEffect(() => {
    fetch(`${API_BASE_URL}/processed?fileId=${fileId}`)
      .then(res => res.json())
      .then(data => {
        setRefinedText(data.refinedText);
        setFormattedText(data.formattedText);
        setEditHistory(data.editHistory || []);
      });
  }, [fileId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE_URL}/processed/${fileId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refinedText, formattedText })
      });
      
      const result = await response.json();
      if (response.ok) {
        alert('OCR results updated successfully!');
        setEditHistory(result.editHistory);
      } else {
        alert(`Error: ${result.message}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h2>Edit OCR Results</h2>
      
      <div>
        <h3>Refined Text</h3>
        <textarea
          value={refinedText}
          onChange={(e) => setRefinedText(e.target.value)}
          rows={10}
          cols={80}
        />
      </div>
      
      <div>
        <h3>Formatted Text</h3>
        <textarea
          value={formattedText}
          onChange={(e) => setFormattedText(e.target.value)}
          rows={10}
          cols={80}
        />
      </div>
      
      <button onClick={handleSave} disabled={saving}>
        {saving ? 'Saving...' : 'Save Changes'}
      </button>
      
      {editHistory.length > 0 && (
        <div>
          <h3>Edit History</h3>
          <ul>
            {editHistory.map((edit, index) => (
              <li key={index}>
                Edited on {new Date(edit.edited_at).toLocaleString()}
                - Modified: {edit.edited_fields.join(', ')}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

## Deployment

To deploy the edit functionality:

1. Run Terraform to create the new resources:
   ```bash
   terraform plan
   terraform apply
   ```

2. The deployment will create:
   - New Lambda function (`editor`)
   - New API Gateway endpoint (`PATCH /processed/{fileId}`)
   - IAM roles and policies
   - CloudWatch log group

3. After deployment, the edit endpoint URL will be available in Terraform outputs:
   ```bash
   terraform output api_endpoints
   ```

## Security Considerations

1. **Authentication**: Currently, the endpoint has no authentication. Consider adding:
   - API Keys for basic protection
   - AWS Cognito for user authentication
   - IAM authentication for service-to-service calls

2. **Input Validation**: The Lambda function validates that:
   - At least one field is provided
   - The file exists and has been processed
   - Request body is valid JSON

3. **Rate Limiting**: Consider implementing rate limiting to prevent abuse

## Future Enhancements

1. **Revision Control**: Implement full revision history with ability to revert to previous versions
2. **Diff View**: Show visual differences between original and edited text
3. **Collaborative Editing**: Support for multiple users editing with conflict resolution
4. **Validation Rules**: Add custom validation for specific document types
5. **Webhooks**: Notify external systems when edits are made
6. **Bulk Editing**: Support editing multiple files at once
7. **Export Options**: Export edit history and changes report