import json
import boto3
import uuid
import os
import base64
from datetime import datetime
from urllib.parse import unquote_plus
import email
from io import StringIO
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File size threshold for routing (300KB)
FILE_SIZE_THRESHOLD_KB = int(os.environ.get('FILE_SIZE_THRESHOLD_KB', '300'))

def make_routing_decision(file_size_bytes: int, file_type: str, priority: str) -> Dict[str, Any]:
    """
    Simple, bulletproof routing decision based on 300KB threshold.
    Files <= 300KB go to short-batch, everything else goes to long-batch.
    """
    file_size_kb = file_size_bytes / 1024
    
    decision = {
        'route': 'short-batch',
        'reason': [],
        'estimated_processing_time': '1-5 minutes',
        'processor_type': 'lambda',
        's3_folder': 'short-batch-files',
        'queue_url': os.environ.get('SHORT_BATCH_QUEUE_URL')
    }
    
    # Simple size-based routing - the only reliable factor
    if file_size_kb <= FILE_SIZE_THRESHOLD_KB:
        decision['route'] = 'short-batch'
        decision['reason'].append(f'File size ({file_size_kb:.0f}KB) ≤ {FILE_SIZE_THRESHOLD_KB}KB threshold')
        decision['estimated_processing_time'] = '30 seconds - 5 minutes'
        decision['processor_type'] = 'lambda'
        decision['s3_folder'] = 'short-batch-files'
        decision['queue_url'] = os.environ.get('SHORT_BATCH_QUEUE_URL')
    else:
        decision['route'] = 'long-batch'
        decision['reason'].append(f'File size ({file_size_kb:.0f}KB) > {FILE_SIZE_THRESHOLD_KB}KB threshold')
        decision['estimated_processing_time'] = '5-30 minutes'
        decision['processor_type'] = 'aws_batch'
        decision['s3_folder'] = 'long-batch-files'
        decision['queue_url'] = os.environ.get('LONG_BATCH_QUEUE_URL')
    
    # Priority override for urgent processing
    if priority == 'urgent' and file_size_kb <= FILE_SIZE_THRESHOLD_KB * 2:  # Allow up to 600KB for urgent
        decision['route'] = 'short-batch'
        decision['reason'].append('Urgent priority - using fast Lambda processing')
        decision['processor_type'] = 'lambda_urgent'
        decision['estimated_processing_time'] = '30 seconds - 2 minutes'
        decision['s3_folder'] = 'short-batch-files'
        decision['queue_url'] = os.environ.get('SHORT_BATCH_QUEUE_URL')
    elif priority == 'low' and file_size_kb > FILE_SIZE_THRESHOLD_KB * 0.5:  # Lower threshold for low priority (150KB)
        decision['route'] = 'long-batch'
        decision['reason'].append('Low priority - using cost-efficient batch processing')
        decision['s3_folder'] = 'long-batch-files'
        decision['queue_url'] = os.environ.get('LONG_BATCH_QUEUE_URL')
    
    return decision

def send_to_processing_queue(queue_url: str, file_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send file metadata to the appropriate processing queue
    """
    if not queue_url:
        logger.error("Queue URL not provided")
        return {'success': False, 'error': 'Queue URL not configured'}
    
    sqs = boto3.client('sqs')
    
    message_body = {
        'file_id': file_data['file_id'],
        'processing_type': file_data['routing_decision']['route'],
        'timestamp': file_data['upload_timestamp'],
        'metadata': file_data
    }
    
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            MessageAttributes={
                'processing_type': {
                    'StringValue': file_data['routing_decision']['route'],
                    'DataType': 'String'
                },
                'file_id': {
                    'StringValue': file_data['file_id'],
                    'DataType': 'String'
                }
            }
        )
        
        logger.info(f"Sent file {file_data['file_id']} to {file_data['routing_decision']['route']} queue: {response['MessageId']}")
        return {'success': True, 'message_id': response['MessageId']}
        
    except Exception as e:
        logger.error(f"Failed to send message to queue {queue_url}: {str(e)}")
        return {'success': False, 'error': str(e)}

def parse_multipart_form_data(body, content_type):
    """Parse multipart/form-data from Lambda event - supports multiple files"""
    if 'boundary=' not in content_type:
        raise ValueError("No boundary found in content-type")
    
    boundary = content_type.split('boundary=')[1]
    
    # Parse the multipart data
    parts = body.split(f'--{boundary}'.encode())
    form_data = {}
    files = []  # Changed to list to support multiple files
    
    for part in parts:
        if not part.strip() or part.strip() == b'--':
            continue
            
        # Split headers and content
        if b'\r\n\r\n' in part:
            headers_section, content = part.split(b'\r\n\r\n', 1)
            content = content.rstrip(b'\r\n')
        else:
            continue
            
        headers = {}
        for line in headers_section.decode().split('\r\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        if 'content-disposition' in headers:
            disp = headers['content-disposition']
            if 'name=' in disp:
                name = disp.split('name="')[1].split('"')[0]
                
                if 'filename=' in disp:
                    # This is a file
                    filename = disp.split('filename="')[1].split('"')[0]
                    if filename:  # Only add if filename is not empty
                        file_content_type = headers.get('content-type', 'application/octet-stream')
                        files.append({
                            'filename': filename,
                            'content': content,
                            'content_type': file_content_type
                        })
                else:
                    # This is a regular form field
                    form_data[name] = content.decode()
    
    return form_data, files

def lambda_handler(event, context):
    """
    Enhanced S3 file upload with integrated smart routing.
    Files are routed to short-batch (≤300KB) or long-batch (>300KB) immediately upon upload.
    """
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    
    bucket_name = os.environ['UPLOAD_BUCKET_NAME']
    table_name = os.environ['DYNAMODB_TABLE']
    table = dynamodb.Table(table_name)
    
    try:
        # Parse the multipart form data
        content_type = event.get('headers', {}).get('content-type', '') or event.get('headers', {}).get('Content-Type', '')
        body = base64.b64decode(event['body']) if event.get('isBase64Encoded', False) else event['body'].encode()
        
        form_data, files = parse_multipart_form_data(body, content_type)
        
        if not files:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'No files provided'})
            }
        
        uploaded_files = []
        
        for file_info in files:
            file_content = file_info['content']
            original_filename = file_info['filename']
            content_type = file_info['content_type']
            
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            # Calculate file size
            file_size = len(file_content)
            file_size_mb = file_size / (1024 * 1024)
            
            # Get file type from filename extension
            file_extension = os.path.splitext(original_filename)[1]
            file_type = file_extension.lstrip('.').lower()
            
            # Get priority from form data
            priority = form_data.get('priority', 'normal')
            
            # Make intelligent routing decision
            routing_decision = make_routing_decision(file_size, file_type, priority)
            
            # Create S3 key with appropriate folder structure
            s3_key = f"{routing_decision['s3_folder']}/{file_id}{file_extension}"
            
            # Upload to S3 with enhanced metadata
            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original-filename': original_filename,
                    'file-id': file_id,
                    'upload-timestamp': timestamp,
                    'routing-decision': routing_decision['route'],
                    'processor-type': routing_decision['processor_type'],
                    'file-size-kb': str(file_size / 1024)
                }
            )
            
            # Store enhanced metadata in DynamoDB
            item = {
                'file_id': file_id,
                'upload_timestamp': timestamp,
                'original_filename': original_filename,  # Keep for backwards compatibility
                'file_name': original_filename,           # Add the expected field name
                'content_type': content_type,
                'file_size': file_size,
                'file_size_mb': str(file_size_mb),
                'file_size_kb': str(file_size / 1024),
                's3_bucket': bucket_name,
                's3_key': s3_key,
                's3_folder': routing_decision['s3_folder'],
                'processing_status': 'uploaded',
                'upload_source': 'api',
                'bucket_name': bucket_name,  # For GSI query
                # Enhanced routing metadata
                'processing_route': routing_decision['route'],
                'processor_type': routing_decision['processor_type'],
                'routing_reason': routing_decision['reason'],
                'estimated_processing_time': routing_decision['estimated_processing_time'],
                'routing_decision': routing_decision,  # Store full decision for debugging
                'priority': priority,
                # Add default metadata fields that the reader expects
                'publication': form_data.get('publication', ''),
                'year': form_data.get('year', ''),
                'title': form_data.get('title', ''),
                'author': form_data.get('author', '')
            }
            
            # Add optional form data
            if 'priority' in form_data:
                item['priority'] = form_data['priority']
            if 'description' in form_data:
                item['description'] = form_data['description']
            if 'tags' in form_data:
                item['tags'] = form_data['tags']
            
            table.put_item(Item=item)
            
            # Send to appropriate processing queue
            queue_result = send_to_processing_queue(routing_decision['queue_url'], item)
            
            file_result = {
                'file_id': file_id,
                'filename': original_filename,
                'size': file_size,
                'size_mb': round(file_size_mb, 2),
                'size_kb': round(file_size / 1024, 2),
                's3_key': s3_key,
                's3_folder': routing_decision['s3_folder'],
                'timestamp': timestamp,
                'content_type': content_type,
                'routing': {
                    'decision': routing_decision['route'],
                    'processor': routing_decision['processor_type'],
                    'reason': routing_decision['reason'][0] if routing_decision['reason'] else 'No specific reason',
                    'estimated_time': routing_decision['estimated_processing_time']
                },
                'queue_status': 'sent' if queue_result.get('success') else 'failed',
                'queue_message_id': queue_result.get('message_id')
            }
            
            if not queue_result.get('success'):
                logger.warning(f"Failed to send file {file_id} to processing queue: {queue_result.get('error')}")
                file_result['queue_error'] = queue_result.get('error')
            
            uploaded_files.append(file_result)
        
        # Return success response with all uploaded files
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'Successfully uploaded and routed {len(uploaded_files)} file(s)',
                'files': uploaded_files,
                'routing_info': {
                    'threshold_kb': FILE_SIZE_THRESHOLD_KB,
                    'short_batch': f'Files ≤ {FILE_SIZE_THRESHOLD_KB}KB → Fast Lambda processing (30s-5min)',
                    'long_batch': f'Files > {FILE_SIZE_THRESHOLD_KB}KB → AWS Batch processing (5-30min)'
                }
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