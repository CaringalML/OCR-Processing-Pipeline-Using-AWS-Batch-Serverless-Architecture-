import json
import boto3
import os
import uuid
from datetime import datetime, timezone

# Initialize AWS clients
sqs_client = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

# Environment variables
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
METADATA_TABLE = os.environ.get('METADATA_TABLE', 'ocr-processor-metadata')

def lambda_handler(event, context):
    """
    Lambda handler that receives API Gateway requests and submits them to SQS for processing
    """
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        file_id = body.get('fileId')
        
        if not file_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'fileId is required'})
            }
        
        # Validate file exists in metadata table
        metadata_table = dynamodb.Table(METADATA_TABLE)
        metadata_response = metadata_table.get_item(Key={'file_id': file_id})
        
        if 'Item' not in metadata_response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'File not found'})
            }
        
        file_metadata = metadata_response['Item']
        
        # Check if already processing or completed
        if file_metadata.get('processing_status') in ['processing', 'completed']:
            return {
                'statusCode': 202,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': f"File is already {file_metadata.get('processing_status')}",
                    'fileId': file_id,
                    'status': file_metadata.get('processing_status')
                })
            }
        
        # Check file size (10MB limit for short batch)
        file_size_mb = file_metadata.get('file_size', 0) / (1024 * 1024)
        if file_size_mb > 10:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'File too large for short batch processing',
                    'maxSizeMB': 10,
                    'fileSizeMB': round(file_size_mb, 2),
                    'suggestion': 'Please use the regular batch processing endpoint for large files'
                })
            }
        
        # Create message for SQS
        message = {
            'messageId': str(uuid.uuid4()),
            'fileId': file_id,
            'bucketName': file_metadata.get('bucket_name'),
            's3Key': file_metadata.get('s3_key'),
            'fileName': file_metadata.get('file_name', 'unknown'),
            'fileSize': file_metadata.get('file_size', 0),
            'submittedAt': datetime.now(timezone.utc).isoformat(),
            'requestId': context.request_id,
            'processingType': 'short_batch'
        }
        
        # Send message to SQS with deduplication
        sqs_response = sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageAttributes={
                'fileId': {
                    'StringValue': file_id,
                    'DataType': 'String'
                },
                'processingType': {
                    'StringValue': 'short_batch',
                    'DataType': 'String'
                }
            }
        )
        
        # Update status to queued
        metadata_table.update_item(
            Key={'file_id': file_id},
            UpdateExpression='SET processing_status = :status, sqs_message_id = :msg_id, queue_timestamp = :timestamp',
            ExpressionAttributeValues={
                ':status': 'queued',
                ':msg_id': sqs_response['MessageId'],
                ':timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Return success response
        return {
            'statusCode': 202,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'File queued for short batch processing',
                'fileId': file_id,
                'messageId': sqs_response['MessageId'],
                'status': 'queued',
                'estimatedProcessingTime': '10-30 seconds',
                'checkStatusUrl': f"/processed?fileId={file_id}"
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }