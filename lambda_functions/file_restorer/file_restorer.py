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
    results_table_name = os.environ.get('RESULTS_TABLE')
    recycle_bin_table_name = os.environ.get('RECYCLE_BIN_TABLE')
    
    if not all([results_table_name, recycle_bin_table_name]):
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
        
        # Initialize tables (using single results table)
        results_table = dynamodb.Table(results_table_name)
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
        
        # Check if file already exists (shouldn't happen, but check anyway)
        existing_metadata = results_table.get_item(
            Key={'file_id': file_id}
        )
        
        if 'Item' in existing_metadata:
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Conflict',
                    'message': f'File {file_id} already exists in active files'
                })
            }
        
        # Restore metadata
        original_metadata = recycled_item['original_metadata']
        original_metadata['restored_at'] = datetime.now(timezone.utc).isoformat()
        original_metadata['restored_from_recycle_bin'] = True
        
        results_table.put_item(Item=original_metadata)
        
        # Restore results if they existed
        if recycled_item.get('original_results'):
            original_results = recycled_item['original_results']
            original_results['restored_at'] = datetime.now(timezone.utc).isoformat()
            
            results_table.put_item(Item=original_results)
        
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
                'restoredAt': original_metadata['restored_at'],
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