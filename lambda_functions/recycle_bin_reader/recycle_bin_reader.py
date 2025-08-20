import json
import boto3
import os
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key
from decimal import Decimal

def decimal_to_json(obj):
    """Convert Decimal objects to JSON-serializable types"""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_json(item) for item in obj]
    else:
        return obj

def lambda_handler(event, context):
    """
    Lambda function to list files in recycle bin
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    recycle_bin_table_name = os.environ.get('RECYCLE_BIN_TABLE')
    
    if not recycle_bin_table_name:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Configuration Error',
                'message': 'Missing required environment variables'
            })
        }
    
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        limit = min(int(query_params.get('limit', 50)), 100)  # Max 100 items
        last_evaluated_key = query_params.get('lastKey')
        file_id = query_params.get('fileId')
        
        # Initialize table
        recycle_bin_table = dynamodb.Table(recycle_bin_table_name)
        
        # Build query parameters
        scan_params = {
            'Limit': limit
        }
        
        if last_evaluated_key:
            try:
                # Decode the last evaluated key
                import base64
                decoded_key = json.loads(base64.b64decode(last_evaluated_key))
                scan_params['ExclusiveStartKey'] = decoded_key
            except:
                pass
        
        # Query for specific file or scan all
        if file_id:
            response = recycle_bin_table.query(
                KeyConditionExpression=Key('file_id').eq(file_id),
                **scan_params
            )
        else:
            response = recycle_bin_table.scan(**scan_params)
        
        # Process items
        items = []
        for item in response.get('Items', []):
            # Calculate days until permanent deletion
            ttl_timestamp = int(item.get('ttl', 0))  # Convert Decimal to int
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            days_remaining = max(0, int((ttl_timestamp - current_timestamp) / 86400))
            
            # The original_metadata contains the entire record from the consolidated table
            original_data = item.get('original_metadata', {})
            
            # Calculate expiry date
            expiry_date = datetime.fromtimestamp(ttl_timestamp, tz=timezone.utc)
            
            processed_item = {
                'fileId': item['file_id'],
                'deletedAt': item['deleted_timestamp'],  # ISO 8601 format
                'expiresAt': expiry_date.isoformat(),     # ISO 8601 format
                'daysRemaining': days_remaining,
                'deletedBy': item.get('deleted_by', 'unknown'),
                'metadata': {
                    'filename': original_data.get('file_name', ''),
                    'filesize': original_data.get('file_size', 0),
                    'mimeType': original_data.get('content_type', ''),
                    'processingStatus': original_data.get('processing_status', 'unknown'),
                    'uploadedAt': original_data.get('upload_timestamp', ''),  # Keep ISO format
                    # Publication metadata from consolidated table structure
                    'title': original_data.get('publication_title', ''),
                    'author': original_data.get('publication_author', ''),
                    'publication': original_data.get('publication', ''),
                    'date': original_data.get('publication_year', ''),
                    'description': original_data.get('publication_description', ''),
                    'page': original_data.get('publication_page', ''),
                    'tags': original_data.get('publication_tags', []),
                    'collection': original_data.get('publication_collection', ''),
                    'documentType': original_data.get('publication_document_type', '')
                }
            }
            
            # Include OCR results summary if available
            if item.get('original_results'):
                processed_item['hasOcrResults'] = True
                processed_item['ocrSummary'] = {
                    'textLength': len(item['original_results'].get('refined_text', '')),
                    'hasFormattedText': bool(item['original_results'].get('formatted_text')),
                    'userEdited': item['original_results'].get('user_edited', False)
                }
            else:
                processed_item['hasOcrResults'] = False
            
            items.append(processed_item)
        
        # Prepare response
        result = {
            'items': decimal_to_json(items),
            'count': len(items)
        }
        
        # Add pagination info if there are more items
        if response.get('LastEvaluatedKey'):
            import base64
            encoded_key = base64.b64encode(
                json.dumps(decimal_to_json(response['LastEvaluatedKey'])).encode()
            ).decode()
            result['lastKey'] = encoded_key
            result['hasMore'] = True
        else:
            result['hasMore'] = False
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e)
            })
        }