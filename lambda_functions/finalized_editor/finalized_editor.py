import json
import boto3
import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import time

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
    Lambda function to edit finalized OCR results
    Allows users to modify finalized documents while maintaining complete audit trail
    
    Triggered by API Gateway PUT requests to /finalized/edit/{fileId} endpoint
    
    Request body should contain:
    {
        "finalizedText": "New finalized text content",  # Required: updated text
        "editReason": "Corrected OCR errors",           # Required: reason for edit
        "preserveHistory": true                         # Optional: keep edit history (default: true)
    }
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    finalized_table_name = os.environ.get('FINALIZED_TABLE', 'ocr-processor-batch-finalized-results')
    edit_history_table_name = os.environ.get('EDIT_HISTORY_TABLE', 'ocr-processor-edit-history')
    
    if not finalized_table_name or not edit_history_table_name:
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
        # Parse path parameters and request body
        path_params = event.get('pathParameters', {}) or {}
        query_params = event.get('queryStringParameters', {}) or {}
        file_id = path_params.get('fileId') or query_params.get('fileId')
        
        print(f"Edit finalized document request for fileId: {file_id}")
        print(f"Event path parameters: {path_params}")
        
        if not file_id:
            print("ERROR: Missing fileId in request")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Missing fileId in path parameters'
                })
            }
        
        # Parse request body
        body_raw = event.get('body', '{}')
        print(f"Request body: {body_raw}")
        body = json.loads(body_raw)
        finalized_text = body.get('finalizedText')
        edit_reason = body.get('editReason')
        preserve_history = body.get('preserveHistory', True)
        
        print(f"Parsed body - hasFinalizedText: {bool(finalized_text)}, editReason: {edit_reason}")
        
        # Validate required fields
        if not finalized_text:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'finalizedText is required'
                })
            }
        
        if not edit_reason:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'editReason is required to maintain audit trail'
                })
            }
        
        # Initialize tables
        finalized_table = dynamodb.Table(finalized_table_name)
        edit_history_table = dynamodb.Table(edit_history_table_name)
        
        # Get current finalized document
        # Note: We need to scan since we only have file_id but table uses composite key
        scan_response = finalized_table.scan(
            FilterExpression='file_id = :file_id',
            ExpressionAttributeValues={
                ':file_id': file_id
            }
        )
        
        if not scan_response.get('Items'):
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': f'Finalized document {file_id} not found'
                })
            }
        
        # Get the most recent finalized version (should only be one)
        current_finalized = scan_response['Items'][0]
        
        # Create edit timestamp
        edit_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Prepare edit history entry for separate table
        edit_entry = {
            'file_id': file_id,
            'edit_timestamp': edit_timestamp,
            'timestamp': edit_timestamp,  # For backward compatibility
            'edit_reason': edit_reason,
            'previous_text': current_finalized.get('finalized_text', ''),
            'new_text': finalized_text,
            'text_length_change': len(finalized_text) - len(current_finalized.get('finalized_text', '')),
            'ttl': int(time.time()) + (30 * 24 * 60 * 60)  # 30 days TTL
        }
        
        # Store edit history in separate table if preserving history
        if preserve_history:
            try:
                edit_history_table.put_item(Item=edit_entry)
                print(f"Stored edit history entry for {file_id} with TTL: {edit_entry['ttl']}")
            except Exception as e:
                print(f"Warning: Failed to store edit history: {str(e)}")
                # Continue with the update even if edit history fails
        
        # Update the finalized document (entity_analysis and other metadata are automatically preserved)
        # Note: Since we're only updating specific fields, existing fields like entity_analysis remain unchanged
        update_expression = 'SET finalized_text = :new_text, last_edited_timestamp = :edit_time, edit_count = if_not_exists(edit_count, :zero) + :one'
        expression_values = {
            ':new_text': finalized_text,
            ':edit_time': edit_timestamp,
            ':zero': 0,
            ':one': 1
        }
        
        # Perform the update
        finalized_table.update_item(
            Key={
                'file_id': file_id,
                'finalized_timestamp': current_finalized['finalized_timestamp']
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        print(f"Successfully updated finalized document {file_id}")
        
        # Retrieve edit history from separate table for response
        edit_history = []
        if preserve_history:
            try:
                history_response = edit_history_table.query(
                    KeyConditionExpression='file_id = :file_id',
                    ExpressionAttributeValues={':file_id': file_id},
                    ScanIndexForward=False,  # Most recent first
                    Limit=10  # Limit to recent entries for response
                )
                edit_history = [decimal_to_json(item) for item in history_response.get('Items', [])]
            except Exception as e:
                print(f"Warning: Failed to retrieve edit history for response: {str(e)}")
        
        # Build response (convert Decimal objects to avoid JSON serialization issues)
        response_data = {
            'fileId': file_id,
            'editTimestamp': edit_timestamp,
            'editReason': edit_reason,
            'editCount': int(current_finalized.get('edit_count', 0)) + 1,  # Convert Decimal to int
            'textLengthChange': edit_entry['text_length_change'],
            'preservedHistory': preserve_history,
            'message': f'Finalized document updated successfully. Edit #{int(current_finalized.get("edit_count", 0)) + 1}',
            'editedTextPreview': finalized_text[:500] if len(finalized_text) > 500 else finalized_text,
            'editHistory': edit_history,  # Include edit history from separate table
            'latestEdit': {
                'timestamp': edit_timestamp,
                'editReason': edit_reason,
                'textLengthChange': edit_entry['text_length_change']
            }
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(decimal_to_json(response_data))
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
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