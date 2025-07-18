import json
import boto3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
batch_client = boto3.client('batch')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to detect and handle jobs stuck in 'processing' status.
    Runs periodically to find jobs that have been processing for too long.
    """
    logger.info("Starting dead job detection")
    
    try:
        # Get configuration from environment variables
        table_name = os.environ.get('DYNAMODB_TABLE')
        max_processing_minutes = int(os.environ.get('MAX_PROCESSING_MINUTES', '120'))  # Default 2 hours
        
        if not table_name:
            logger.error("DYNAMODB_TABLE environment variable not set")
            return {
                'statusCode': 500,
                'body': json.dumps('DynamoDB table name not configured')
            }
        
        table = dynamodb.Table(table_name)
        
        # Find jobs stuck in processing status
        stuck_jobs = find_stuck_processing_jobs(table, max_processing_minutes)
        
        if not stuck_jobs:
            logger.info("No stuck jobs found")
            return {
                'statusCode': 200,
                'body': json.dumps('No stuck jobs found')
            }
        
        logger.info(f"Found {len(stuck_jobs)} stuck jobs")
        
        # Process each stuck job
        results = []
        for job in stuck_jobs:
            result = process_stuck_job(table, job)
            results.append(result)
        
        success_count = sum(1 for r in results if r['success'])
        
        logger.info(f"Processed {len(stuck_jobs)} stuck jobs, {success_count} successful")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(stuck_jobs)} stuck jobs',
                'successful': success_count,
                'failed': len(stuck_jobs) - success_count,
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in dead job detection: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def find_stuck_processing_jobs(table: Any, max_processing_minutes: int) -> List[Dict[str, Any]]:
    """
    Find jobs that have been in 'processing' status for too long.
    """
    import time
    
    # Calculate cutoff time
    cutoff_time = int(time.time()) - (max_processing_minutes * 60)
    
    try:
        # Scan for jobs in processing status that started before cutoff time
        response = table.scan(
            FilterExpression='processing_status = :status AND processing_started < :cutoff',
            ExpressionAttributeValues={
                ':status': 'processing',
                ':cutoff': cutoff_time
            }
        )
        
        stuck_jobs = response.get('Items', [])
        
        logger.info(f"Found {len(stuck_jobs)} jobs stuck in processing status")
        
        return stuck_jobs
        
    except Exception as e:
        logger.error(f"Error scanning for stuck jobs: {str(e)}")
        raise

def process_stuck_job(table: Any, job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single stuck job by checking its actual Batch status and updating accordingly.
    """
    file_id = job.get('file_id')
    batch_job_id = job.get('batch_job_id')
    
    logger.info(f"Processing stuck job: file_id={file_id}, batch_job_id={batch_job_id}")
    
    try:
        # If no batch job ID, mark as failed
        if not batch_job_id:
            logger.warning(f"No batch_job_id for file_id {file_id}, marking as failed")
            update_status_to_failed(table, file_id, "No batch job ID found")
            return {
                'file_id': file_id,
                'action': 'marked_failed',
                'reason': 'no_batch_job_id',
                'success': True
            }
        
        # Check actual Batch job status
        try:
            batch_response = batch_client.describe_jobs(jobs=[batch_job_id])
            jobs = batch_response.get('jobs', [])
            
            if not jobs:
                logger.warning(f"Batch job {batch_job_id} not found, marking as failed")
                update_status_to_failed(table, file_id, f"Batch job {batch_job_id} not found")
                return {
                    'file_id': file_id,
                    'action': 'marked_failed',
                    'reason': 'batch_job_not_found',
                    'success': True
                }
            
            batch_job = jobs[0]
            batch_status = batch_job.get('jobStatus')
            
            logger.info(f"Batch job {batch_job_id} status: {batch_status}")
            
            # Handle based on actual Batch status
            if batch_status == 'SUCCEEDED':
                update_status_to_processed(table, file_id, batch_job_id)
                return {
                    'file_id': file_id,
                    'action': 'marked_processed',
                    'reason': 'batch_job_succeeded',
                    'success': True
                }
            elif batch_status in ['FAILED', 'CANCELLED']:
                status_reason = batch_job.get('statusReason', f'Batch job {batch_status.lower()}')
                update_status_to_failed(table, file_id, f"Batch job {batch_status.lower()}: {status_reason}")
                return {
                    'file_id': file_id,
                    'action': 'marked_failed',
                    'reason': f'batch_job_{batch_status.lower()}',
                    'success': True
                }
            elif batch_status in ['SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING', 'RUNNING']:
                # Job is still active in Batch, leave it alone for now
                logger.info(f"Batch job {batch_job_id} is still active ({batch_status}), leaving unchanged")
                return {
                    'file_id': file_id,
                    'action': 'no_change',
                    'reason': f'batch_job_still_{batch_status.lower()}',
                    'success': True
                }
            else:
                logger.warning(f"Unknown batch status {batch_status} for job {batch_job_id}")
                return {
                    'file_id': file_id,
                    'action': 'no_change',
                    'reason': f'unknown_batch_status_{batch_status}',
                    'success': True
                }
                
        except Exception as e:
            logger.error(f"Error checking batch job {batch_job_id}: {str(e)}")
            # If we can't check the batch job, mark as failed
            update_status_to_failed(table, file_id, f"Error checking batch job: {str(e)}")
            return {
                'file_id': file_id,
                'action': 'marked_failed',
                'reason': 'batch_check_error',
                'success': True
            }
            
    except Exception as e:
        logger.error(f"Error processing stuck job {file_id}: {str(e)}")
        return {
            'file_id': file_id,
            'action': 'error',
            'reason': str(e),
            'success': False
        }

def update_status_to_processed(table: Any, file_id: str, batch_job_id: str) -> None:
    """
    Update DynamoDB record to 'processed' status.
    """
    import time
    
    try:
        table.update_item(
            Key={'file_id': file_id},
            UpdateExpression='SET processing_status = :status, processing_completed = :completed, last_updated = :updated, batch_job_final_status = :batch_status',
            ExpressionAttributeValues={
                ':status': 'processed',
                ':completed': int(time.time()),
                ':updated': int(time.time()),
                ':batch_status': 'SUCCEEDED'
            },
            ConditionExpression='attribute_exists(file_id)'
        )
        logger.info(f"Updated file_id {file_id} to processed status")
    except Exception as e:
        logger.error(f"Error updating file {file_id} to processed: {str(e)}")
        raise

def update_status_to_failed(table: Any, file_id: str, error_message: str) -> None:
    """
    Update DynamoDB record to 'failed' status.
    """
    import time
    
    try:
        table.update_item(
            Key={'file_id': file_id},
            UpdateExpression='SET processing_status = :status, failed_at = :failed_at, last_updated = :updated, error_message = :error, batch_job_final_status = :batch_status',
            ExpressionAttributeValues={
                ':status': 'failed',
                ':failed_at': int(time.time()),
                ':updated': int(time.time()),
                ':error': f"Dead job detection: {error_message}",
                ':batch_status': 'FAILED'
            },
            ConditionExpression='attribute_exists(file_id)'
        )
        logger.info(f"Updated file_id {file_id} to failed status: {error_message}")
    except Exception as e:
        logger.error(f"Error updating file {file_id} to failed: {str(e)}")
        raise