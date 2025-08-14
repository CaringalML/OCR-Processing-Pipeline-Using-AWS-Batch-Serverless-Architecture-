import json
import boto3
import os
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import time

def calculate_real_time_duration(processing_result):
    """Calculate real-time processing duration based on current time and start time"""
    try:
        # Check if processing is completed (has processing_duration in the DB)
        stored_duration = processing_result.get('processing_duration')
        if stored_duration and processing_result.get('processing_status') == 'completed':
            return stored_duration
        
        # For ongoing processing, calculate real-time duration
        processing_started = processing_result.get('processing_started')
        if processing_started:
            try:
                # Parse ISO format timestamp
                start_time = datetime.fromisoformat(processing_started.replace('Z', '+00:00'))
                current_time = datetime.now(start_time.tzinfo)
                elapsed_seconds = (current_time - start_time).total_seconds()
                return elapsed_seconds
            except (ValueError, AttributeError):
                pass
        
        # Fallback to upload timestamp if processing_started is not available
        upload_timestamp = processing_result.get('upload_timestamp')
        if upload_timestamp:
            try:
                upload_time = datetime.fromisoformat(upload_timestamp.replace('Z', '+00:00'))
                current_time = datetime.now(upload_time.tzinfo)
                elapsed_seconds = (current_time - upload_time).total_seconds()
                return elapsed_seconds
            except (ValueError, AttributeError):
                pass
                
        return 0
    except Exception as e:
        print(f"Error calculating real-time duration: {str(e)}")
        return 0

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    try:
        if isinstance(size_bytes, str):
            size_bytes = float(size_bytes)
        size_bytes = float(size_bytes)
        
        if size_bytes == 0:
            return "0B"
        
        # Define size units
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = size_bytes
        
        # Convert to appropriate unit
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        # Format with appropriate decimal places
        if unit_index == 0:  # Bytes
            return f"{int(size)}B"
        elif size >= 100:  # No decimal for 100+ units
            return f"{int(size)}{units[unit_index]}"
        elif size >= 10:   # 1 decimal for 10-99 units
            return f"{size:.1f}{units[unit_index]}"
        else:              # 2 decimals for less than 10 units
            return f"{size:.2f}{units[unit_index]}"
            
    except (ValueError, TypeError):
        return "Unknown"

def get_detailed_processing_status(processing_result):
    """Get detailed processing status with progress for running batch jobs"""
    base_status = processing_result.get('processing_status', '')
    batch_job_id = processing_result.get('batch_job_id')
    processing_type = processing_result.get('processing_type', '')
    
    # Debug logging can be enabled when needed
    # print(f"DEBUG: Processing status check - base_status: {base_status}, batch_job_id: {batch_job_id}, processing_type: {processing_type}")
    
    # For short-batch jobs that are still processing, just show "processing"
    if processing_type == 'short-batch':
        if base_status in ['completed', 'failed', 'processed']:
            return base_status
        else:
            return 'processing'
    
    # For long-batch jobs, always check the batch job status if we have a job ID
    if processing_type == 'long-batch' and batch_job_id:
        # Even if status is "uploaded" or other states, check the actual batch job
        try:
            batch_client = boto3.client('batch')
            
            # Get job details
            response = batch_client.describe_jobs(jobs=[batch_job_id])
            
            print(f"DEBUG: Batch response for job {batch_job_id}: {response}")
            
            if response.get('jobs'):
                job = response['jobs'][0]
                job_status = job.get('status', 'UNKNOWN')
                print(f"DEBUG: Job status: {job_status}")
                
                # Check for container status for more detailed info
                container = job.get('container', {})
                task_arn = container.get('taskArn', '')
                log_stream_name = container.get('logStreamName', '')
                
                # Map AWS Batch statuses to user-friendly progress
                if job_status == 'SUBMITTED':
                    return 'Queued for processing'
                elif job_status == 'PENDING':
                    return 'Pending - Waiting for resources'
                elif job_status == 'RUNNABLE':
                    return 'Starting - Provisioning container'
                elif job_status == 'STARTING':
                    # ECS task is being provisioned
                    return 'Starting - ECS task provisioning'
                elif job_status == 'RUNNING':
                    # Job is actually running, show progress
                    return get_running_progress(job)
                elif job_status == 'SUCCEEDED':
                    return 'completed'
                elif job_status == 'FAILED':
                    # Check if there's a reason for failure
                    status_reason = job.get('statusReason', '')
                    if 'Task failed' in status_reason:
                        return 'failed - Task error'
                    elif 'ResourcesNotAvailable' in status_reason:
                        return 'failed - Resources unavailable'
                    else:
                        return 'failed'
                else:
                    return f'Processing ({job_status.lower()})'
            else:
                print(f"DEBUG: No jobs found for {batch_job_id}")
                # Job not found, possibly completed and cleaned up
                if base_status == 'completed':
                    return 'completed'
                else:
                    return 'Queued for processing'
                    
        except Exception as e:
            print(f"Error getting batch job status for {batch_job_id}: {str(e)}")
            # If we can't get batch status, use base status with enhancement
            if base_status == 'uploaded':
                return 'Queued for processing'
            elif base_status == 'processing':
                # Fallback to time-based estimation
                return get_time_based_progress(processing_result)
            else:
                return base_status
    
    # For long-batch without job ID (shouldn't happen) or completed/failed status
    if processing_type == 'long-batch':
        if base_status == 'uploaded':
            return 'Queued for processing'
        elif base_status in ['completed', 'processed']:
            return 'completed'
        elif base_status == 'failed':
            return 'failed'
        elif base_status == 'processing':
            # Check if batch job was submitted recently but not yet stored in DB
            recent_job_status = check_recent_batch_job_status(processing_result)
            if recent_job_status:
                return recent_job_status
            else:
                return 'Processing - Batch job pending'
        else:
            # Handle any unexpected status
            return f'Status: {base_status}'
    
    return base_status

def get_running_progress(job):
    """Calculate progress for a running batch job by checking CloudWatch logs"""
    try:
        # First try to get actual progress from CloudWatch logs
        container = job.get('container', {})
        log_stream_name = container.get('logStreamName')
        
        if log_stream_name:
            # Parse progress from CloudWatch logs
            actual_progress = get_progress_from_logs(log_stream_name)
            if actual_progress:
                return actual_progress
        
        # Fallback to time-based estimation if we can't get logs
        started_at = job.get('startedAt')
        if not started_at:
            return 'In progress - Starting'
            
        # Convert milliseconds to seconds
        start_time = started_at / 1000
        current_time = time.time()
        elapsed_minutes = (current_time - start_time) / 60
        
        # Estimate progress based on typical processing time
        if elapsed_minutes < 2:
            progress = min(15, int(elapsed_minutes * 7.5))  # 0-15% in first 2 minutes
        elif elapsed_minutes < 10:
            progress = min(50, 15 + int((elapsed_minutes - 2) * 4.375))  # 15-50% in next 8 minutes
        elif elapsed_minutes < 20:
            progress = min(80, 50 + int((elapsed_minutes - 10) * 3))  # 50-80% in next 10 minutes
        else:
            progress = min(95, 80 + int((elapsed_minutes - 20) * 0.75))  # 80-95% after 20 minutes
            
        return f'In progress {progress}%'
        
    except Exception as e:
        print(f"Error calculating progress: {str(e)}")
        return 'In progress'

def get_progress_from_logs(log_stream_name):
    """Parse actual progress from CloudWatch logs"""
    try:
        logs_client = boto3.client('logs')
        log_group_name = '/aws/batch/ocr-processor-batch-long-batch-processor'
        
        # Get the latest log events
        response = logs_client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            startFromHead=False,  # Get latest logs
            limit=50  # Get last 50 log entries
        )
        
        # Parse logs to determine current stage
        events = response.get('events', [])
        
        # Define progress stages based on log messages
        progress_stages = {
            'OCR Processor starting': 5,
            'Starting file processing': 10,
            'Retrieving file metadata': 15,
            'File metadata retrieved': 20,
            'Starting Textract OCR processing': 25,
            'Starting Textract document analysis': 30,
            'Textract job submitted': 35,
            'Waiting for Textract completion': 40,
            'Textract job completed, retrieving results': 50,
            'Textract job completed': 50,
            'Textract processing completed': 55,
            'Extracting text from Textract results': 58,
            'Formatting extracted text': 62,
            'Applying comprehensive text refinement': 67,
            'Text processing completed': 72,
            'Starting Comprehend analysis on refined text': 76,
            'Starting Comprehend analysis': 76,
            'Comprehend analysis completed': 82,
            'Storing processing results': 88,
            'Long-batch processing completed and stored in results table': 94,
            'Long-batch processing completed': 94,
            'File processing completed successfully': 98,
            'Batch job completed successfully': 100
        }
        
        # Find the latest stage from logs
        current_stage = 'In progress'
        current_progress = 0
        
        for event in reversed(events):  # Check from newest to oldest
            message = event.get('message', '')
            
            # Try to parse JSON log
            try:
                if message.startswith('{'):
                    log_data = json.loads(message)
                    log_message = log_data.get('message', '')
                    
                    # Check for specific stages
                    for stage, progress in progress_stages.items():
                        if stage in log_message:
                            if progress > current_progress:
                                current_progress = progress
                                current_stage = stage
                                
                    # Check for Textract waiting status with percentage
                    if 'Waiting for Textract completion' in log_message:
                        # Textract processing can take time, show intermediate progress
                        elapsed = log_data.get('context', {}).get('elapsedMinutes', 0)
                        if elapsed > 0:
                            # Textract typically takes 5-15 minutes
                            textract_progress = min(45, 35 + int(elapsed * 2))
                            if textract_progress > current_progress:
                                current_progress = textract_progress
                                current_stage = f'Processing document (Textract)'
            except:
                # If not JSON, check plain text
                for stage, progress in progress_stages.items():
                    if stage in message:
                        if progress > current_progress:
                            current_progress = progress
                            current_stage = stage
        
        if current_progress > 0:
            # Add time-based interpolation for smoother progress
            # If we detect a stage but it's been running for a while, add some interpolation
            from datetime import datetime, timezone
            import time
            
            current_time = time.time()
            stage_duration_bonus = 0
            
            # Add small bonus based on how long the current stage has been running
            # This helps fill gaps between detected stages
            if current_progress < 100:
                # Add up to 2% bonus based on elapsed time (max 5 minutes)
                elapsed_minutes = 2  # Assume some elapsed time if we can't determine it
                stage_duration_bonus = min(2, elapsed_minutes * 0.4)
                current_progress = min(99, current_progress + stage_duration_bonus)
            
            # Return user-friendly status based on stage
            if current_progress < 30:
                return f'In progress {current_progress}% - Initializing'
            elif current_progress < 55:
                return f'In progress {current_progress}% - Extracting text'
            elif current_progress < 75:
                return f'In progress {current_progress}% - Refining text'
            elif current_progress < 90:
                return f'In progress {current_progress}% - Analyzing content'
            elif current_progress < 100:
                return f'In progress {current_progress}% - Finalizing'
            else:
                return f'Completed'
        
        return None  # No specific progress found, use fallback
        
    except Exception as e:
        print(f"Error reading CloudWatch logs: {str(e)}")
        return None

def check_recent_batch_job_status(processing_result):
    """Check for recent batch job submissions and their status via logs and batch API"""
    try:
        file_id = processing_result.get('file_id', '')
        upload_timestamp = processing_result.get('upload_timestamp', '')
        
        if not file_id:
            return None
            
        # Check CloudWatch logs for recent batch job submissions for this file
        logs_client = boto3.client('logs')
        batch_client = boto3.client('batch')
        
        # Look for recent SQS processor logs mentioning this file
        try:
            # Get logs from the last 10 minutes
            start_time = int((datetime.now() - timedelta(minutes=10)).timestamp() * 1000)
            
            sqs_log_response = logs_client.filter_log_events(
                logGroupName='/aws/lambda/ocr-processor-batch-sqs-batch-processor',
                startTime=start_time,
                filterPattern=f'"{file_id}"',
                limit=20
            )
            
            # Look for batch job submission in logs
            batch_job_id = None
            job_submitted = False
            
            for event in sqs_log_response.get('events', []):
                message = event.get('message', '')
                if 'Submitted Batch job' in message and file_id in message:
                    # Extract job ID from log message
                    # Format: "Submitted Batch job JOB_ID for file FILE_ID"
                    parts = message.split()
                    if len(parts) >= 4:
                        batch_job_id = parts[3]  # The job ID
                        job_submitted = True
                        break
                elif 'ERROR' in message and file_id in message:
                    return 'Processing failed - Check logs'
                elif 'Updated file' in message and file_id in message:
                    # Job was submitted and DB updated successfully
                    if 'batch job ID' in message:
                        parts = message.split()
                        for i, part in enumerate(parts):
                            if part == 'ID' and i + 1 < len(parts):
                                batch_job_id = parts[i + 1]
                                break
            
            if batch_job_id:
                # Found a batch job ID, check its current status
                try:
                    batch_response = batch_client.describe_jobs(jobs=[batch_job_id])
                    if batch_response.get('jobs'):
                        job = batch_response['jobs'][0]
                        job_status = job.get('status', 'UNKNOWN')
                        
                        # Map status to user-friendly messages
                        if job_status == 'RUNNING':
                            # Get actual progress from batch processor logs
                            container = job.get('container', {})
                            log_stream_name = container.get('logStreamName', '')
                            if log_stream_name:
                                actual_progress = get_progress_from_batch_logs(batch_job_id)
                                if actual_progress:
                                    return actual_progress
                            return get_running_progress(job)
                        else:
                            status_mapping = {
                                'SUBMITTED': 'Queued for processing',
                                'PENDING': 'Pending - Waiting for resources',
                                'RUNNABLE': 'Starting - Provisioning container',
                                'STARTING': 'Starting - ECS task provisioning',
                                'SUCCEEDED': 'Processing completed',
                                'FAILED': 'Processing failed'
                            }
                            return status_mapping.get(job_status, f'Processing ({job_status.lower()})')
                        
                except Exception as batch_error:
                    print(f"Error checking batch job {batch_job_id}: {str(batch_error)}")
            
            elif job_submitted:
                return 'Batch job submitted - Starting soon'
            
            # Check if file is in SQS queue waiting to be processed
            sqs_client = boto3.client('sqs')
            queue_url = 'https://sqs.ap-southeast-2.amazonaws.com/939737198590/ocr-processor-batch-batch-queue'
            
            # Check if there are messages in flight
            queue_attrs = sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
            )
            
            visible_messages = int(queue_attrs['Attributes'].get('ApproximateNumberOfMessages', 0))
            invisible_messages = int(queue_attrs['Attributes'].get('ApproximateNumberOfMessagesNotVisible', 0))
            
            if visible_messages > 0:
                return f'Queued for processing ({visible_messages} files ahead)'
            elif invisible_messages > 0:
                return 'Processing queue - Job starting soon'
            else:
                # No messages in queue, check if it's a recent upload
                if upload_timestamp:
                    upload_time = datetime.fromisoformat(upload_timestamp.replace('Z', '+00:00'))
                    time_since_upload = (datetime.now(upload_time.tzinfo) - upload_time).total_seconds()
                    
                    if time_since_upload < 300:  # Less than 5 minutes
                        return 'Processing initiated - Starting batch job'
                    else:
                        return 'Processing delayed - Check system status'
            
        except Exception as log_error:
            print(f"Error checking logs for file {file_id}: {str(log_error)}")
            return None
            
    except Exception as e:
        print(f"Error in check_recent_batch_job_status: {str(e)}")
        return None

def get_progress_from_batch_logs(batch_job_id):
    """Get progress directly from batch processor logs using job ID"""
    try:
        logs_client = boto3.client('logs')
        log_group_name = '/aws/batch/ocr-processor-batch-long-batch-processor'
        
        # Get recent log events from the last 30 minutes
        start_time = int((datetime.now() - timedelta(minutes=30)).timestamp() * 1000)
        
        # Filter logs by batch job ID to get logs for this specific job
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time,
            filterPattern=f'"{batch_job_id}"',  # Filter by job ID
            limit=50
        )
        
        events = response.get('events', [])
        
        # If no logs found for this job ID, try getting recent logs for any job
        if not events:
            response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=start_time,
                limit=20
            )
            events = response.get('events', [])
        
        # Parse the same progress stages as before
        progress_stages = {
            'OCR Processor starting': 5,
            'Starting file processing': 10,
            'Retrieving file metadata': 15,
            'File metadata retrieved': 20,
            'Starting Textract OCR processing': 25,
            'Starting Textract document analysis': 30,
            'Textract job submitted': 35,
            'Waiting for Textract completion': 40,
            'Textract job completed, retrieving results': 50,
            'Textract job completed': 50,
            'Textract processing completed': 55,
            'Extracting text from Textract results': 58,
            'Formatting extracted text': 62,
            'Applying comprehensive text refinement': 67,
            'Text processing completed': 72,
            'Starting Comprehend analysis on refined text': 76,
            'Starting Comprehend analysis': 76,
            'Comprehend analysis completed': 82,
            'Storing processing results': 88,
            'Long-batch processing completed and stored in results table': 94,
            'Long-batch processing completed': 94,
            'File processing completed successfully': 98,
            'Batch job completed successfully': 100
        }
        
        # Find the latest stage from logs
        current_progress = 0
        
        for event in reversed(events):  # Check from newest to oldest
            message = event.get('message', '')
            
            # Try to parse JSON log
            try:
                if message.startswith('{'):
                    log_data = json.loads(message)
                    log_message = log_data.get('message', '')
                    
                    # Check for specific stages
                    for stage, progress in progress_stages.items():
                        if stage in log_message:
                            if progress > current_progress:
                                current_progress = progress
                                
                    # Check for Textract waiting status
                    if 'Waiting for Textract completion' in log_message:
                        context = log_data.get('context', {})
                        if 'elapsedMinutes' in context:
                            elapsed = context['elapsedMinutes']
                            # Textract typically takes 5-15 minutes
                            textract_progress = min(45, 35 + int(elapsed * 2))
                            if textract_progress > current_progress:
                                current_progress = textract_progress
            except:
                # If not JSON, check plain text
                for stage, progress in progress_stages.items():
                    if stage in message:
                        if progress > current_progress:
                            current_progress = progress
        
        if current_progress > 0:
            # Add time-based interpolation for smoother progress
            if current_progress < 100:
                # Add small bonus for elapsed time to show progression
                stage_duration_bonus = min(3, 1.5)  # Add up to 3% bonus
                current_progress = min(99, current_progress + stage_duration_bonus)
            
            # Return user-friendly status based on stage
            if current_progress < 30:
                return f'In progress {current_progress}% - Initializing'
            elif current_progress < 55:
                return f'In progress {current_progress}% - Extracting text (Textract)'
            elif current_progress < 75:
                return f'In progress {current_progress}% - Refining text'
            elif current_progress < 90:
                return f'In progress {current_progress}% - Analyzing content (Comprehend)'
            elif current_progress < 100:
                return f'In progress {current_progress}% - Finalizing'
            else:
                return f'Completed'
        
        return None  # No specific progress found
        
    except Exception as e:
        print(f"Error reading batch processor logs: {str(e)}")
        return None

def get_time_based_progress(processing_result):
    """Fallback progress estimation based on processing start time"""
    try:
        processing_started = processing_result.get('processing_started')
        if not processing_started:
            return 'In progress'
            
        # Parse the ISO timestamp
        start_time = datetime.fromisoformat(processing_started.replace('Z', '+00:00'))
        current_time = datetime.now(start_time.tzinfo)
        elapsed_minutes = (current_time - start_time).total_seconds() / 60
        
        # Simple time-based progress estimation
        if elapsed_minutes < 5:
            progress = min(20, int(elapsed_minutes * 4))
        elif elapsed_minutes < 15:
            progress = min(60, 20 + int((elapsed_minutes - 5) * 4))
        elif elapsed_minutes < 25:
            progress = min(85, 60 + int((elapsed_minutes - 15) * 2.5))
        else:
            progress = min(95, 85 + int((elapsed_minutes - 25) * 0.5))
            
        return f'In progress {progress}%'
        
    except Exception as e:
        print(f"Error calculating time-based progress: {str(e)}")
        return 'In progress'

def decimal_to_json(obj):
    """Convert Decimal objects to JSON-serializable types"""
    if isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise to float
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

def format_duration(duration_seconds):
    """Format duration in seconds to human-readable format"""
    if not duration_seconds:
        return "0s"
    
    # Handle case where duration is already a formatted string (e.g., "139.58 seconds")
    if isinstance(duration_seconds, str):
        # If it's already formatted, return as-is
        if 'seconds' in duration_seconds or 'minutes' in duration_seconds or 'hours' in duration_seconds:
            # Extract numeric part and reformat consistently
            import re
            match = re.search(r'(\d+\.?\d*)', duration_seconds)
            if match:
                numeric_value = float(match.group(1))
                if 'seconds' in duration_seconds:
                    return f"{numeric_value:.1f}s"
                elif 'minutes' in duration_seconds:
                    return f"{numeric_value:.1f}m"
                elif 'hours' in duration_seconds:
                    return f"{numeric_value:.1f}h"
            # Fallback: return original string if parsing fails
            return duration_seconds
        else:
            # Try to convert string to float
            try:
                duration = float(duration_seconds)
            except (ValueError, TypeError):
                return str(duration_seconds)
    else:
        duration = float(duration_seconds)
    
    if duration < 60:
        # Less than 1 minute - show in seconds with 1 decimal place
        return f"{duration:.1f}s"
    elif duration < 3600:
        # Less than 1 hour - show in minutes with 1 decimal place
        minutes = duration / 60
        return f"{minutes:.1f}m"
    else:
        # 1 hour or more - show in hours with 1 decimal place
        hours = duration / 3600
        return f"{hours:.1f}h"

def lambda_handler(event, context):
    """
    Lambda function to read processed files from DynamoDB and generate CloudFront URLs
    Triggered by API Gateway GET requests to /processed endpoint
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration - only results table needed now
    results_table_name = os.environ.get('RESULTS_TABLE', 'ocr-processor-batch-processing-results')
    cloudfront_domain = os.environ.get('CLOUDFRONT_DOMAIN')
    
    if not all([results_table_name, cloudfront_domain]):
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
        status_filter = query_params.get('status', 'processed')
        limit = int(query_params.get('limit', '50'))
        file_id = query_params.get('fileId')
        
        # Determine which endpoint was called to filter by batch type
        resource_path = event.get('requestContext', {}).get('resourcePath', '')
        batch_type_filter = None
        if '/short-batch/' in resource_path:
            batch_type_filter = 'short-batch'
        elif '/long-batch/' in resource_path:
            batch_type_filter = 'long-batch'
        # If '/processed' (root endpoint), show all batch types (batch_type_filter = None)
        
        results_table = dynamodb.Table(results_table_name)
        
        # If specific file_id is requested
        if file_id:
            # Get file data from results table
            results_response = results_table.get_item(
                Key={'file_id': file_id}
            )
            
            if not results_response.get('Item'):
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
            
            processing_result = decimal_to_json(results_response['Item'])
            
            # Generate CloudFront URL from results table data
            s3_key = processing_result.get('key', '')
            cloudfront_url = f"https://{cloudfront_domain}/{s3_key}" if s3_key else ''
            
            # Get detailed processing status (with progress for running jobs)
            detailed_status = get_detailed_processing_status(processing_result)
            
            # Build response data from results table
            response_data = {
                'fileId': file_id,
                'fileName': processing_result.get('file_name', ''),
                'uploadTimestamp': processing_result.get('upload_timestamp', ''),
                'processingStatus': detailed_status,
                'processingType': processing_result.get('processing_type', ''),
                'fileSize': format_file_size(processing_result.get('file_size', 0)),
                'contentType': processing_result.get('content_type', ''),
                'cloudFrontUrl': cloudfront_url,
                'bucket': processing_result.get('bucket', ''),
                'key': processing_result.get('key', ''),
                'metadata': {
                    'publication': processing_result.get('publication', ''),
                    'publication_year': processing_result.get('publication_year', ''),
                    'publication_title': processing_result.get('publication_title', ''),
                    'publication_author': processing_result.get('publication_author', ''),
                    'publication_description': processing_result.get('publication_description', ''),
                    'publication_page': processing_result.get('publication_page', ''),
                    'publication_tags': processing_result.get('publication_tags', [])
                }
            }
            
            # Add OCR results from unified table structure
            if processing_result:
                response_data['ocrResults'] = {
                    'extractedText': processing_result.get('extracted_text', ''),
                    'formattedText': processing_result.get('formatted_text', ''),
                    'refinedText': processing_result.get('refined_text', ''),
                    'processingType': processing_result.get('processing_type', ''),
                    'processingCost': processing_result.get('processing_cost', 0),
                    'processedAt': processing_result.get('processed_at', ''),
                    'processingDuration': format_duration(calculate_real_time_duration(processing_result)),
                    'tokenUsage': processing_result.get('token_usage', {}),
                    'languageDetection': processing_result.get('language_detection', {}),
                    'entityAnalysis': processing_result.get('entityAnalysis', processing_result.get('entity_analysis', {})),
                    'userEdited': processing_result.get('user_edited', False),
                    'editHistory': processing_result.get('edit_history', [])
                }
            else:
                # No OCR results available
                response_data['ocrResults'] = None
            
            # Add analysis data based on processing type
            if processing_result and processing_result.get('processing_type') == 'short-batch':
                # For Claude processing from shared table, use stored textAnalysis if available
                stored_text_analysis = processing_result.get('textAnalysis')
                
                if stored_text_analysis:
                    # Use the stored textAnalysis from the database
                    response_data['textAnalysis'] = stored_text_analysis
                else:
                    # Fallback: Generate text analysis on-the-fly for backward compatibility
                    formatted_text = processing_result.get('formatted_text', '')
                    refined_text = processing_result.get('refined_text', '')
                    
                    if formatted_text or refined_text:
                        # Use refined text for analysis (better for word/sentence counting)
                        analysis_text = refined_text if refined_text else formatted_text
                        words = analysis_text.split()
                        paragraphs = analysis_text.split('\n\n')
                        sentences = analysis_text.split('. ')
                        
                        # Safe improvement ratio calculation
                        improvement_ratio = 1.0
                        if formatted_text and len(formatted_text) > 0:
                            improvement_ratio = round(len(refined_text) / len(formatted_text), 2)
                        
                        response_data['textAnalysis'] = {
                            'improvement_ratio': improvement_ratio,
                            'refined_total_character_count': len(refined_text),
                            'refined_total_word_count': len(words),
                            'refined_total_sentences': len([s for s in sentences if s.strip()]),
                            'refined_total_paragraphs': len([p for p in paragraphs if p.strip()]),
                            'refined_total_spell_corrections': 0,
                            'refined_total_grammar_count': 0,
                            'refined_flow_improvements': 0,
                            'refined_total_improvements': 0,
                            'raw_total_character_count': len(formatted_text),
                            'raw_total_word_count': len(words),  # Approximation for old records
                            'raw_total_sentences': len([s for s in sentences if s.strip()]),
                            'raw_total_paragraphs': len([p for p in paragraphs if p.strip()]),
                            'processing_model': processing_result.get('processing_model', 'claude-sonnet-4-20250514'),
                            'processing_notes': 'Dual-pass Claude processing: OCR extraction + grammar refinement (legacy fallback)',
                            'methods_used': ['claude_ocr', 'grammar_refinement'],
                            'qualityAssessment': {
                                'confidence_score': '95',
                                'issues': [],
                                'assessment': 'legacy_fallback'
                            }
                        }
                    
                    # Add entity analysis if available in results (check both field names for compatibility)
                    entity_analysis = processing_result.get('entityAnalysis', processing_result.get('entity_analysis', {}))
                    if entity_analysis and entity_analysis.get('entity_summary'):
                        response_data['entityAnalysis'] = {
                            'entity_summary': entity_analysis.get('entity_summary', {}),
                            'total_entities': entity_analysis.get('total_entities', 0),
                            'entity_types': list(entity_analysis.get('entity_summary', {}).keys()),
                            'detection_source': 'Claude AI OCR Analysis'
                        }
            # Legacy code removed - now using unified table structure
            
            if processing_result:
                # For long-batch/Textract processing, use stored textAnalysis if available
                stored_text_analysis = processing_result.get('textAnalysis')
                
                if stored_text_analysis:
                    # Use the stored textAnalysis from the database
                    response_data['textAnalysis'] = stored_text_analysis
                else:
                    # Check for legacy textract_analysis field
                    enhanced_textract_analysis = processing_result.get('textract_analysis', {})                
                    if enhanced_textract_analysis:
                        response_data['textAnalysis'] = enhanced_textract_analysis
                    else:
                        # Fallback to legacy construction for backward compatibility
                        summary_analysis = processing_result.get('summary_analysis', {})
                        text_refinement_details = processing_result.get('text_refinement_details', {})
                        
                        response_data['textAnalysis'] = {
                            'improvement_ratio': 1.0,
                            'refined_total_character_count': summary_analysis.get('character_count', 0),
                            'refined_total_word_count': summary_analysis.get('word_count', 0),
                            'refined_total_sentences': summary_analysis.get('sentence_count', 0),
                            'refined_total_paragraphs': summary_analysis.get('paragraph_count', 0),
                            'refined_total_spell_corrections': text_refinement_details.get('spell_corrections', 0),
                            'refined_total_grammar_count': text_refinement_details.get('grammar_refinements', 0),
                            'refined_flow_improvements': 0,
                            'refined_total_improvements': text_refinement_details.get('total_improvements', 0),
                            'raw_total_character_count': summary_analysis.get('character_count', 0),
                            'raw_total_word_count': summary_analysis.get('word_count', 0),
                            'raw_total_sentences': summary_analysis.get('sentence_count', 0),
                            'raw_total_paragraphs': summary_analysis.get('paragraph_count', 0),
                            'processing_model': 'aws-textract-comprehend',
                            'processing_notes': text_refinement_details.get('processing_notes', 'Legacy Textract processing'),
                            'methods_used': text_refinement_details.get('methods_used', ['textract', 'comprehend']),
                            'qualityAssessment': {
                                'confidence_score': summary_analysis.get('confidence', '0'),
                                'issues': [],
                                'assessment': 'legacy_textract'
                            }
                        }
                
                # Add enhanced Comprehend entity analysis for long-batch
                comprehend_analysis = processing_result.get('comprehend_analysis', {})
                if comprehend_analysis:
                    response_data['comprehendAnalysis'] = comprehend_analysis
                    
                
                # Add dedicated Invoice Analysis section
                invoice_analysis = processing_result.get('invoice_analysis', {})
                if invoice_analysis:
                    response_data['invoiceAnalysis'] = invoice_analysis
            
        else:
            # Query files from results table
            if status_filter == 'all':
                # Scan all files from results table
                response = results_table.scan(
                    Limit=limit
                )
            elif status_filter == 'processed':
                # Handle batch type filtering based on endpoint
                if batch_type_filter == 'short-batch':
                    # Only get short-batch files (status = 'completed')
                    response = results_table.scan(
                        FilterExpression=Attr('processing_status').eq('completed') & Attr('processing_type').eq('short-batch'),
                        Limit=limit
                    )
                elif batch_type_filter == 'long-batch':
                    # Only get long-batch files (status = 'completed')
                    response = results_table.scan(
                        FilterExpression=Attr('processing_status').eq('completed') & Attr('processing_type').eq('long-batch'),
                        Limit=limit
                    )
                else:
                    # For processed files, get both short-batch and long-batch completed files
                    response = results_table.scan(
                        FilterExpression=Attr('processing_status').eq('completed'),
                        Limit=limit
                    )
            else:
                # Query by specific status
                response = results_table.scan(
                    FilterExpression=Attr('processing_status').eq(status_filter),
                    Limit=limit
                )
            
            items = decimal_to_json(response.get('Items', []))
            
            # Enrich items with CloudFront URLs and results
            processed_items = []
            for item in items:
                # Since we're using a single table, all data is already in 'item'
                # No need for additional queries
                processing_result = item  # All data is already here
                
                # Generate CloudFront URL
                s3_key = item.get('key', '')  # 'key' is the field name in results table
                cloudfront_url = f"https://{cloudfront_domain}/{s3_key}" if s3_key else None
                
                # Build item data
                item_data = {
                    'fileId': item['file_id'],
                    'fileName': item.get('file_name', ''),
                    'uploadTimestamp': item.get('upload_timestamp', ''),
                    'processingStatus': item.get('processing_status', ''),
                    'fileSize': format_file_size(item.get('file_size', 0)),
                    'contentType': item.get('content_type', ''),
                    'cloudFrontUrl': cloudfront_url,
                    'metadata': {
                        'publication': item.get('publication', ''),
                        'publication_year': item.get('publication_year', ''),
                        'publication_title': item.get('publication_title', ''),
                        'publication_author': item.get('publication_author', ''),
                        'publication_description': item.get('publication_description', ''),
                        'publication_page': item.get('publication_page', ''),
                        'publication_tags': item.get('publication_tags', [])
                    }
                }
                
                # Add processing results if available
                if item.get('processing_status') in ['processed', 'completed']:
                    # Determine processing type and add appropriate results
                    processing_type = item.get('processing_type', 'long-batch')
                    
                    if processing_type == 'short-batch':
                        # Short-batch results from shared table
                        item_data['ocrResults'] = {
                            'formattedText': item.get('formatted_text', ''),
                            'refinedText': item.get('refined_text', ''),
                            'extractedText': item.get('extracted_text', ''),
                            'processingModel': item.get('processing_model', 'claude-sonnet-4-20250514'),
                            'processingType': 'short-batch',
                            'processingCost': item.get('processing_cost', 0),
                            'processedAt': item.get('processed_at', ''),
                            'processingDuration': format_duration(calculate_real_time_duration(item)),
                            'tokenUsage': item.get('token_usage', {}),
                            'languageDetection': item.get('language_detection', {})
                        }
                        
                        # Add text analysis for short-batch
                        text_analysis = item.get('textAnalysis', {})
                        if text_analysis:
                            item_data['textAnalysis'] = text_analysis
                    else:
                        # Long-batch results from shared table
                        item_data['ocrResults'] = {
                            'extractedText': item.get('extracted_text', ''),
                            'formattedText': item.get('formatted_text', ''),
                            'refinedText': item.get('refined_text', ''),
                            'processingModel': item.get('processing_model', 'aws-textract'),
                            'processingType': 'long-batch',
                            'processingDuration': format_duration(calculate_real_time_duration(item))
                        }
                        
                        # Add additional analysis data for long-batch
                        enhanced_textract_analysis = item.get('textract_analysis', {})                
                        if enhanced_textract_analysis:
                            item_data['textAnalysis'] = enhanced_textract_analysis
                        
                        # Add enhanced Comprehend entity analysis for long-batch
                        comprehend_analysis = item.get('comprehend_analysis', {})
                        if comprehend_analysis:
                            item_data['comprehendAnalysis'] = comprehend_analysis
                            
                        # Add dedicated Invoice Analysis section
                        invoice_analysis = item.get('invoice_analysis', {})
                        if invoice_analysis:
                            item_data['invoiceAnalysis'] = invoice_analysis
                
                processed_items.append(item_data)
            
            response_data = {
                'files': processed_items,
                'count': len(processed_items),
                'hasMore': response.get('LastEvaluatedKey') is not None
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
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