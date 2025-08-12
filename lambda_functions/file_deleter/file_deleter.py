import json
import boto3
import os
from datetime import datetime, timezone, timedelta
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
    Lambda function to delete files by moving them to recycle bin
    Supports both soft delete (to recycle bin) and permanent delete
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    s3 = boto3.client('s3')
    
    # Get configuration
    results_table_name = os.environ.get('RESULTS_TABLE', 'ocr-processor-batch-processing-results')
    recycle_bin_table_name = os.environ.get('RECYCLE_BIN_TABLE')
    s3_bucket = os.environ.get('S3_BUCKET')
    
    if not all([results_table_name, recycle_bin_table_name, s3_bucket]):
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
        
        # Check for permanent delete flag in query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        permanent = query_params.get('permanent', 'false').lower() == 'true'
        
        # Initialize tables
        results_table = dynamodb.Table(results_table_name)
        recycle_bin_table = dynamodb.Table(recycle_bin_table_name)
        
        # Get file data from results table to verify file exists
        results_response = results_table.get_item(
            Key={'file_id': file_id}
        )
        
        if 'Item' not in results_response:
            # Check if file is in recycle bin
            if permanent:
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
                            'message': f'File {file_id} not found'
                        })
                    }
                
                # Permanent delete from recycle bin
                recycled_item = recycle_response['Items'][0]
                
                # Delete from recycle bin table
                recycle_bin_table.delete_item(
                    Key={
                        'file_id': file_id,
                        'deleted_timestamp': recycled_item['deleted_timestamp']
                    }
                )
                
                # Delete from S3 if file still exists
                if 'key' in recycled_item['original_metadata']:
                    try:
                        s3.delete_object(
                            Bucket=s3_bucket,
                            Key=recycled_item['original_metadata']['key']
                        )
                    except Exception as e:
                        print(f"Error deleting S3 object: {str(e)}")
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'message': f'File {file_id} permanently deleted',
                        'fileId': file_id,
                        'fileName': recycled_item['original_metadata'].get('file_name', 'Unknown')
                    })
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Not Found',
                        'message': f'File {file_id} not found'
                    })
                }
        
        file_metadata = results_response['Item']
        
        # The file data is already combined in the results table
        processing_results = file_metadata
        
        # Prepare recycle bin entry
        current_timestamp = datetime.now(timezone.utc)
        deleted_timestamp = current_timestamp.isoformat()
        deletion_date = current_timestamp.strftime('%Y-%m-%d')
        
        # Calculate TTL (30 days from now)
        ttl_timestamp = int((current_timestamp + timedelta(days=30)).timestamp())
        
        recycle_bin_item = {
            'file_id': file_id,
            'deleted_timestamp': deleted_timestamp,
            'deletion_date': deletion_date,
            'ttl': ttl_timestamp,
            'original_metadata': file_metadata,
            'original_results': processing_results,
            'deleted_by': event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
        }
        
        # Move to recycle bin
        recycle_bin_table.put_item(Item=recycle_bin_item)
        
        # Delete from results table (now the unified table)
        results_table.delete_item(
            Key={'file_id': file_id}
        )
        
        # Note: We keep the S3 file for now, it will be deleted after 30 days
        # or when permanently deleted from recycle bin
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'File {file_id} moved to recycle bin',
                'fileId': file_id,
                'fileName': file_metadata.get('file_name', 'Unknown'),
                'deletedAt': deleted_timestamp,
                'willBeDeletedAt': (current_timestamp + timedelta(days=30)).isoformat()
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