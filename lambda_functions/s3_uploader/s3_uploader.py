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
from typing import Dict, Any, Tuple, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

def get_processing_route_from_path(path: str, query_params: Dict[str, str] = None) -> Tuple[str, str, bool]:
    """
    Determine processing route based on API path and query parameters.
    Returns: (route, endpoint_type, force_routing)
    """
    if query_params is None:
        query_params = {}
    
    # Check for explicit route override in query params
    route_override = query_params.get('route', '').lower()
    if route_override in ['short-batch', 'long-batch']:
        return route_override, 'query-override', True
    
    # Route based on API path - consolidated routing
    if '/batch/short-batch/upload' in path or '/short-batch/upload' in path:
        return 'short-batch', 'endpoint-specific', True
    elif '/batch/long-batch/upload' in path or '/long-batch/upload' in path:
        return 'long-batch', 'endpoint-specific', True
    elif '/batch/upload' in path:
        return 'auto', 'smart-router', False
    else:
        # Default smart routing for legacy /upload endpoint
        return 'auto', 'legacy', False

def validate_file_size_for_route(file_size_bytes: int, route: str, max_lambda_size_mb: int = 50) -> Dict[str, Any]:
    """
    Validate if file size is appropriate for the chosen route.
    """
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    if route == 'short-batch' and file_size_mb > max_lambda_size_mb:
        return {
            'valid': False,
            'error': f'File too large for short-batch processing',
            'details': f'File size {file_size_mb:.2f}MB exceeds Lambda limit of {max_lambda_size_mb}MB',
            'suggestion': 'Use /long-batch/upload endpoint or /batch/upload for automatic routing'
        }
    
    return {'valid': True}

def lambda_handler(event, context):
    """
    Unified S3 file upload handler supporting multiple routing strategies:
    
    Routes:
    - /batch/upload (or /upload) - Smart routing based on file size (≤300KB -> short-batch, >300KB -> long-batch)
    - /batch/short-batch/upload or /short-batch/upload - Force short-batch processing (Lambda), rejects files >50MB
    - /batch/long-batch/upload or /long-batch/upload - Force long-batch processing (AWS Batch), no size limit
    
    Query Parameters:
    - route=short-batch|long-batch - Override routing decision
    """
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    
    bucket_name = os.environ['UPLOAD_BUCKET_NAME']
    table_name = os.environ['DYNAMODB_TABLE']
    table = dynamodb.Table(table_name)
    
    # Get processing route from path and query parameters
    path = event.get('path', '/upload')
    query_params = event.get('queryStringParameters') or {}
    route_decision, endpoint_type, force_routing = get_processing_route_from_path(path, query_params)
    
    logger.info(f"Upload request - Path: {path}, Route: {route_decision}, Type: {endpoint_type}, Force: {force_routing}")
    
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
            
            # Determine final routing based on endpoint and file characteristics
            if route_decision == 'auto':
                # Use smart routing for auto routes
                routing_decision = make_routing_decision(file_size, file_type, priority)
                final_route = routing_decision['route']
                routing_reasons = routing_decision['reason']
            else:
                # Validate forced routing
                validation = validate_file_size_for_route(file_size, route_decision)
                if not validation['valid']:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps(validation)
                    }
                
                final_route = route_decision
                routing_reasons = [f'Forced via {endpoint_type}: {path}']
                
                # Create routing decision structure for forced routes
                routing_decision = {
                    'route': final_route,
                    'reason': routing_reasons,
                    'estimated_processing_time': '30 seconds - 5 minutes' if final_route == 'short-batch' else '5-30 minutes',
                    'processor_type': 'lambda' if final_route == 'short-batch' else 'aws_batch',
                    's3_folder': f'{final_route}-files',
                    'queue_url': os.environ.get('SHORT_BATCH_QUEUE_URL') if final_route == 'short-batch' else os.environ.get('LONG_BATCH_QUEUE_URL')
                }
            
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
                'bucket': bucket_name,  # Add bucket for unified table compatibility
                's3_key': s3_key,
                'key': s3_key,  # Add key for unified table compatibility
                's3_folder': routing_decision['s3_folder'],
                'processing_status': 'uploaded',
                'upload_source': 'api',
                'bucket_name': bucket_name,  # For GSI query
                # Enhanced routing metadata
                'processing_route': routing_decision['route'],
                'processing_type': routing_decision['route'],  # Add processing_type for lambda_reader compatibility
                'processor_type': routing_decision['processor_type'],
                'routing_reason': routing_decision['reason'],
                'estimated_processing_time': routing_decision['estimated_processing_time'],
                'routing_decision': routing_decision,  # Store full decision for debugging
                'priority': priority,
                # Enhanced routing metadata
                'endpoint_type': endpoint_type,
                'api_path': path,
                'force_routing': force_routing,
                'route_override': query_params.get('route', ''),
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
                'fileSize': format_file_size(file_size),  # Human readable size
                's3_key': s3_key,
                's3_folder': routing_decision['s3_folder'],
                'timestamp': timestamp,
                'content_type': content_type,
                'routing': {
                    'decision': final_route,
                    'processor': routing_decision['processor_type'],
                    'reason': routing_reasons[0] if routing_reasons else 'No specific reason',
                    'estimated_time': routing_decision['estimated_processing_time'],
                    'endpoint_type': endpoint_type,
                    'forced': force_routing
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
                'endpoint_info': {
                    'path': path,
                    'type': endpoint_type,
                    'routing_method': route_decision,
                    'force_routing': force_routing
                },
                'routing_info': {
                    'threshold_kb': FILE_SIZE_THRESHOLD_KB,
                    'short_batch': f'Files ≤ {FILE_SIZE_THRESHOLD_KB}KB → Fast Lambda processing (30s-5min)',
                    'long_batch': f'Files > {FILE_SIZE_THRESHOLD_KB}KB → AWS Batch processing (5-30min)'
                },
                'available_endpoints': {
                    '/batch/upload': 'Smart routing based on file size and priority',
                    '/batch/short-batch/upload': 'Force Lambda processing (files ≤50MB)',
                    '/batch/long-batch/upload': 'Force AWS Batch processing (any size)',
                    '/short-batch/upload': 'Legacy - Force Lambda processing (files ≤50MB)',
                    '/long-batch/upload': 'Legacy - Force AWS Batch processing (any size)'
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