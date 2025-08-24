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
    Lambda function to restore files from recycle bin
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    finalized_table_name = os.environ.get('FINALIZED_TABLE', 'ocr-processor-batch-finalized-results')
    recycle_bin_table_name = os.environ.get('RECYCLE_BIN_TABLE')
    
    if not all([finalized_table_name, recycle_bin_table_name]):
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
        # Parse path parameters
        path_params = event.get('pathParameters', {}) or {}
        file_id = path_params.get('fileId')
        
        if not file_id:
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
        
        # Initialize tables (only finalized and recycle bin needed)
        finalized_table = dynamodb.Table(finalized_table_name)
        recycle_bin_table = dynamodb.Table(recycle_bin_table_name)
        
        # Get item from recycle bin
        recycle_response = recycle_bin_table.query(
            KeyConditionExpression=Key('file_id').eq(file_id),
            Limit=1
        )
        
        if not recycle_response['Items']:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Not Found',
                    'message': f'File {file_id} not found in recycle bin'
                })
            }
        
        recycled_item = recycle_response['Items'][0]
        
        # Get the original document metadata
        original_metadata = recycled_item['original_metadata']
        
        # Only finalized documents should be in the recycle bin
        # Non-finalized documents from Upload page are permanently deleted
        if 'finalized_timestamp' not in original_metadata:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid Operation',
                    'message': f'Non-finalized documents should not be in recycle bin'
                })
            }
        
        # Check if file already exists in finalized table
        existing_finalized = finalized_table.scan(
            FilterExpression='file_id = :file_id',
            ExpressionAttributeValues={':file_id': file_id}
        )
        if existing_finalized.get('Items'):
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Conflict',
                    'message': f'File {file_id} already exists in finalized documents'
                })
            }
        
        # Restore finalized document to finalized table
        restored_timestamp = datetime.now(timezone.utc)
        original_metadata['restored_at'] = restored_timestamp.isoformat()
        original_metadata['restored_from_recycle_bin'] = True
        
        # Restore to finalized table (only finalized documents should be in recycle bin)
        finalized_table.put_item(Item=original_metadata)
        
        # No need to restore results separately for finalized documents
        # All data is already in the finalized document metadata
        
        # Delete from recycle bin
        recycle_bin_table.delete_item(
            Key={
                'file_id': file_id,
                'deleted_timestamp': recycled_item['deleted_timestamp']
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'File {file_id} restored successfully',
                'fileId': file_id,
                'fileName': original_metadata.get('file_name', 'Unknown'),
                'restoredAt': restored_timestamp.isoformat(),  # ISO 8601 format
                'wasDeletedAt': recycled_item['deleted_timestamp'],  # ISO 8601 format
                'processingStatus': original_metadata.get('processing_status', 'unknown')
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