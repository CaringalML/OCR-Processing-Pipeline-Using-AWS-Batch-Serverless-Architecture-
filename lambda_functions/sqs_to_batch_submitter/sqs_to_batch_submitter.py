import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    Process SQS messages from event source mapping and submit Batch jobs for S3 file processing
    Direct SQS trigger replaces EventBridge polling for better performance
    """
    
    # Initialize AWS clients
    batch_client = boto3.client('batch')
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    job_queue = os.environ.get('BATCH_JOB_QUEUE')
    job_definition = os.environ.get('BATCH_JOB_DEFINITION')
    dynamodb_table_name = os.environ.get('DYNAMODB_TABLE')
    results_table_name = os.environ.get('RESULTS_TABLE')
    
    if not all([job_queue, job_definition, dynamodb_table_name]):
        print("ERROR: Missing required environment variables")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Configuration error'})
        }
    
    table = dynamodb.Table(dynamodb_table_name)
    processed_count = 0
    error_count = 0
    batch_item_failures = []
    
    try:
        # Process messages from SQS event source mapping
        records = event.get('Records', [])
        print(f"Processing {len(records)} SQS records from event source mapping")
        
        for record in records:
            message_id = record.get('messageId')
            receipt_handle = record.get('receiptHandle')
            
            try:
                # Parse the SQS message body from event source mapping
                body = json.loads(record['body'])
                
                # Handle both message formats: direct long-batch uploader and smart router
                if 'fileId' in body and 'processingRoute' in body:
                    # Direct long-batch uploader message format (new)
                    file_id = body['fileId']
                    bucket_name = body['bucket']
                    object_key = body['key']
                    file_name = body.get('fileName', '')
                    file_size = body.get('fileSize', 0)
                    content_type = body.get('contentType', '')
                    
                    print(f"Processing direct long-batch uploader message for file_id: {file_id}")
                    print(f"S3 location: s3://{bucket_name}/{object_key}")
                    
                elif 'file_id' in body and 'processing_type' in body and body['processing_type'] == 'long-batch':
                    # Smart router message format (existing)
                    file_id = body['file_id']
                    metadata = body.get('metadata', {})
                    bucket_name = metadata.get('s3_bucket') or metadata.get('bucket_name')
                    object_key = metadata.get('s3_key')
                    file_name = metadata.get('file_name', '')
                    file_size = metadata.get('file_size', 0)
                    content_type = metadata.get('content_type', '')
                    
                    print(f"Processing smart router long-batch message for file_id: {file_id}")
                    print(f"S3 location: s3://{bucket_name}/{object_key}")
                    
                    if not bucket_name or not object_key:
                        print(f"Missing S3 details in smart router message: {body}")
                        batch_item_failures.append({"itemIdentifier": message_id})
                        error_count += 1
                        continue
                    
                else:
                    print(f"Invalid message format - missing required fields. Expected either (fileId+processingRoute) or (file_id+processing_type=long-batch): {body}")
                    batch_item_failures.append({"itemIdentifier": message_id})
                    error_count += 1
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
                            {'name': 'DYNAMODB_TABLE', 'value': dynamodb_table_name},
                            {'name': 'RESULTS_TABLE', 'value': results_table_name or 'ocr-processor-batch-processing-results'}
                        ]
                    }
                )
                
                job_id = batch_response['jobId']
                print(f"Submitted Batch job {job_id} for file {file_id}")
                
                # Update DynamoDB with job information (unified table uses only file_id as key)
                try:
                    table.update_item(
                        Key={'file_id': file_id},
                        UpdateExpression='SET processing_status = :status, batch_job_id = :job_id, batch_job_name = :job_name, last_updated = :updated, processing_started = :started',
                        ExpressionAttributeValues={
                            ':status': 'processing',
                            ':job_id': job_id,
                            ':job_name': job_name,
                            ':updated': datetime.utcnow().isoformat(),
                            ':started': datetime.utcnow().isoformat()  # Store as ISO string for consistency
                        }
                    )
                    print(f"Updated file {file_id} with batch job ID {job_id}")
                except Exception as update_error:
                    print(f"ERROR: Failed to update DynamoDB for file_id {file_id}: {str(update_error)}")
                    batch_item_failures.append({"itemIdentifier": message_id})
                    error_count += 1
                    continue
                
                # Success - message will be automatically deleted by SQS
                processed_count += 1
                print(f"Successfully submitted batch job {job_id} for file {file_id}")
                    
            except Exception as e:
                print(f"Error processing message {message_id}: {str(e)}")
                batch_item_failures.append({"itemIdentifier": message_id})
                error_count += 1
        
        print(f"Processed {processed_count} messages, {error_count} errors")
        
        # Return batch item failures for SQS event source mapping
        response = {
            'batchItemFailures': batch_item_failures
        }
        
        if batch_item_failures:
            print(f"Returning {len(batch_item_failures)} failed items for retry")
        
        return response
        
    except Exception as e:
        print(f"CRITICAL ERROR in Lambda execution: {str(e)}")
        # Return all messages as failures for retry
        return {
            'batchItemFailures': [{"itemIdentifier": record.get('messageId')} for record in event.get('Records', [])]
        }