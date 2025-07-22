import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    Process SQS messages and submit Batch jobs for S3 file processing
    """
    
    # Initialize AWS clients
    sqs_client = boto3.client('sqs')
    batch_client = boto3.client('batch')
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    queue_url = os.environ.get('SQS_QUEUE_URL')
    job_queue = os.environ.get('BATCH_JOB_QUEUE')
    job_definition = os.environ.get('BATCH_JOB_DEFINITION')
    dynamodb_table_name = os.environ.get('DYNAMODB_TABLE')
    
    if not all([queue_url, job_queue, job_definition, dynamodb_table_name]):
        print("ERROR: Missing required environment variables")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Configuration error'})
        }
    
    table = dynamodb.Table(dynamodb_table_name)
    processed_count = 0
    error_count = 0
    
    try:
        # Receive messages from SQS
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=5,
            MessageAttributeNames=['All']
        )
        
        messages = response.get('Messages', [])
        
        for message in messages:
            try:
                # Parse the message
                body = json.loads(message['Body'])
                
                # Extract S3 event details
                if 'detail' in body:
                    detail = body['detail']
                    bucket_name = detail['bucket']['name']
                    object_key = detail['object']['key']
                    
                    # Skip if not in uploads folder
                    if not object_key.startswith('uploads/'):
                        print(f"Skipping non-upload file: {object_key}")
                        delete_message(sqs_client, queue_url, message['ReceiptHandle'])
                        continue
                    
                    # Extract file_id from the key structure
                    # Format: uploads/YYYY/MM/DD/{file_id}/{filename}
                    key_parts = object_key.split('/')
                    if len(key_parts) >= 6:
                        file_id = key_parts[4]
                    else:
                        print(f"Invalid key structure: {object_key}")
                        delete_message(sqs_client, queue_url, message['ReceiptHandle'])
                        continue
                    
                    # Submit Batch job
                    job_name = f"process-file-{file_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                    
                    batch_response = batch_client.submit_job(
                        jobName=job_name,
                        jobQueue=job_queue,
                        jobDefinition=job_definition,
                        parameters={
                            'bucket': bucket_name,
                            'key': object_key,
                            'fileId': file_id
                        },
                        containerOverrides={
                            'environment': [
                                {'name': 'S3_BUCKET', 'value': bucket_name},
                                {'name': 'S3_KEY', 'value': object_key},
                                {'name': 'FILE_ID', 'value': file_id},
                                {'name': 'DYNAMODB_TABLE', 'value': dynamodb_table_name}
                            ]
                        }
                    )
                    
                    job_id = batch_response['jobId']
                    print(f"Submitted Batch job {job_id} for file {file_id}")
                    
                    # First, query to get the correct upload_timestamp
                    metadata_response = table.query(
                        KeyConditionExpression='file_id = :file_id',
                        ExpressionAttributeValues={':file_id': file_id},
                        Limit=1
                    )
                    
                    if metadata_response['Items']:
                        upload_timestamp = metadata_response['Items'][0]['upload_timestamp']
                        
                        # Update DynamoDB with job information
                        table.update_item(
                            Key={
                                'file_id': file_id,
                                'upload_timestamp': upload_timestamp
                            },
                            UpdateExpression='SET processing_status = :status, batch_job_id = :job_id, batch_job_name = :job_name, last_updated = :updated',
                            ExpressionAttributeValues={
                                ':status': 'processing',
                                ':job_id': job_id,
                                ':job_name': job_name,
                                ':updated': datetime.utcnow().isoformat()
                            }
                        )
                    else:
                        print(f"ERROR: File metadata not found for file_id: {file_id}")
                        error_count += 1
                        continue
                    
                    # Delete message from queue after successful processing
                    delete_message(sqs_client, queue_url, message['ReceiptHandle'])
                    processed_count += 1
                    
                else:
                    print(f"Invalid message format: {message}")
                    error_count += 1
                    
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                error_count += 1
                # Message will return to queue after visibility timeout
        
        print(f"Processed {processed_count} messages, {error_count} errors")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed': processed_count,
                'errors': error_count,
                'total_messages': len(messages)
            })
        }
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def delete_message(sqs_client, queue_url, receipt_handle):
    """Helper function to delete a message from SQS"""
    try:
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
    except Exception as e:
        print(f"Error deleting message: {str(e)}")