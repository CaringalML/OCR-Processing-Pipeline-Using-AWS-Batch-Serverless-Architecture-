import json
import boto3
import logging
import os
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
batch_client = boto3.client('batch')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to reconcile AWS Batch job status with DynamoDB records.
    Triggered by EventBridge when Batch jobs complete (SUCCEEDED/FAILED).
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract job details from EventBridge event
        detail = event.get('detail', {})
        job_id = detail.get('jobId')
        job_name = detail.get('jobName')
        job_status = detail.get('jobStatus')
        
        if not job_id or not job_name or not job_status:
            logger.error(f"Missing required job details in event: {detail}")
            return {
                'statusCode': 400,
                'body': json.dumps('Missing required job details')
            }
        
        logger.info(f"Processing job status change: {job_name} -> {job_status}")
        
        # Extract file_id from job name (format: process-file-{file_id}-{timestamp})
        file_id = extract_file_id_from_job_name(job_name)
        if not file_id:
            logger.error(f"Could not extract file_id from job name: {job_name}")
            return {
                'statusCode': 400,
                'body': json.dumps('Could not extract file_id from job name')
            }
        
        # Get DynamoDB table from environment variable
        table_name = os.environ.get('DYNAMODB_TABLE')
        if not table_name:
            logger.error("DYNAMODB_TABLE environment variable not set")
            return {
                'statusCode': 500,
                'body': json.dumps('DynamoDB table name not configured')
            }
        
        table = dynamodb.Table(table_name)
        
        # Update DynamoDB record based on job status
        if job_status == 'SUCCEEDED':
            update_status_to_processed(table, file_id, job_id)
        elif job_status == 'FAILED':
            update_status_to_failed(table, file_id, job_id, detail)
        else:
            logger.warning(f"Unexpected job status: {job_status}")
            return {
                'statusCode': 200,
                'body': json.dumps(f'No action taken for status: {job_status}')
            }
        
        logger.info(f"Successfully updated status for file_id: {file_id}")
        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully processed job {job_id}')
        }
        
    except Exception as e:
        logger.error(f"Error processing batch job status change: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def extract_file_id_from_job_name(job_name: str) -> str:
    """
    Extract file_id from job name.
    Job name format: process-file-{file_id}-{timestamp}
    """
    try:
        parts = job_name.split('-')
        if len(parts) >= 4 and parts[0] == 'process' and parts[1] == 'file':
            # Join all parts except the first two (process-file) and the last one (timestamp)
            file_id = '-'.join(parts[2:-1])
            return file_id
    except Exception as e:
        logger.error(f"Error extracting file_id from job name {job_name}: {str(e)}")
    
    return None

def update_status_to_processed(table: Any, file_id: str, job_id: str) -> None:
    """
    Update DynamoDB record to 'processed' status when Batch job succeeds.
    """
    import time
    
    try:
        # First, query to get the correct upload_timestamp
        query_response = table.query(
            KeyConditionExpression='file_id = :file_id',
            ExpressionAttributeValues={':file_id': file_id},
            Limit=1
        )
        
        if not query_response['Items']:
            logger.warning(f"File {file_id} not found in DynamoDB")
            return
            
        upload_timestamp = query_response['Items'][0]['upload_timestamp']
        
        response = table.update_item(
            Key={
                'file_id': file_id,
                'upload_timestamp': upload_timestamp
            },
            UpdateExpression='SET processing_status = :status, processing_completed = :completed, last_updated = :updated, batch_job_final_status = :batch_status',
            ExpressionAttributeValues={
                ':status': 'processed',
                ':completed': int(time.time()),
                ':updated': int(time.time()),
                ':batch_status': 'SUCCEEDED',
                ':processing_status': 'processing'
            },
            ConditionExpression='attribute_exists(file_id) AND processing_status = :processing_status',
            ReturnValues='UPDATED_NEW'
        )
        logger.info(f"Updated file_id {file_id} to processed status")
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.warning(f"File {file_id} not in processing status or doesn't exist - skipping update")
    except Exception as e:
        logger.error(f"Error updating file {file_id} to processed: {str(e)}")
        raise

def update_status_to_failed(table: Any, file_id: str, job_id: str, job_detail: Dict[str, Any]) -> None:
    """
    Update DynamoDB record to 'failed' status when Batch job fails.
    """
    import time
    
    try:
        # Extract failure reason from job detail
        status_reason = job_detail.get('statusReason', 'Batch job failed')
        
        # First, query to get the correct upload_timestamp
        query_response = table.query(
            KeyConditionExpression='file_id = :file_id',
            ExpressionAttributeValues={':file_id': file_id},
            Limit=1
        )
        
        if not query_response['Items']:
            logger.warning(f"File {file_id} not found in DynamoDB")
            return
            
        upload_timestamp = query_response['Items'][0]['upload_timestamp']
        
        response = table.update_item(
            Key={
                'file_id': file_id,
                'upload_timestamp': upload_timestamp
            },
            UpdateExpression='SET processing_status = :status, failed_at = :failed_at, last_updated = :updated, error_message = :error, batch_job_final_status = :batch_status',
            ExpressionAttributeValues={
                ':status': 'failed',
                ':failed_at': int(time.time()),
                ':updated': int(time.time()),
                ':error': f"Batch job failed: {status_reason}",
                ':batch_status': 'FAILED',
                ':processing_status': 'processing'
            },
            ConditionExpression='attribute_exists(file_id) AND processing_status = :processing_status',
            ReturnValues='UPDATED_NEW'
        )
        logger.info(f"Updated file_id {file_id} to failed status")
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        logger.warning(f"File {file_id} not in processing status or doesn't exist - skipping update")
    except Exception as e:
        logger.error(f"Error updating file {file_id} to failed: {str(e)}")
        raise