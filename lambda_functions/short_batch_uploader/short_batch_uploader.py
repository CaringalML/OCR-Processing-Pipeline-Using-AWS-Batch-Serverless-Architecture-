import json
import boto3
import uuid
import os
import base64
from datetime import datetime
from urllib.parse import unquote_plus
import email
from io import StringIO

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
    Handle S3 file upload specifically for SHORT-BATCH processing
    All files uploaded through this endpoint will be forced to short-batch processing
    """
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    sqs = boto3.client('sqs')
    
    bucket_name = os.environ['UPLOAD_BUCKET_NAME']
    table_name = os.environ['DYNAMODB_TABLE']
    short_batch_queue_url = os.environ['SHORT_BATCH_QUEUE_URL']
    table = dynamodb.Table(table_name)
    
    # Lambda processing limits
    MAX_LAMBDA_FILE_SIZE_MB = int(os.environ.get('MAX_LAMBDA_FILE_SIZE_MB', '50'))
    
    print(f"SHORT-BATCH UPLOADER: Processing upload request")
    
    try:
        # Parse the multipart form data
        content_type = event.get('headers', {}).get('content-type', '') or event.get('headers', {}).get('Content-Type', '')
        
        # Handle None body case
        raw_body = event.get('body', '')
        if raw_body is None:
            raw_body = ''
        
        # Check if we have a valid multipart request
        if not content_type or 'multipart/form-data' not in content_type:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid content type',
                    'details': 'Request must be multipart/form-data with files',
                    'received_content_type': content_type or 'none'
                })
            }
        
        if not raw_body:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Empty request body',
                    'details': 'No files provided in multipart request'
                })
            }
            
        body = base64.b64decode(raw_body) if event.get('isBase64Encoded', False) else raw_body.encode()
        
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
            
            # Check if file exceeds Lambda limits
            if file_size_mb > MAX_LAMBDA_FILE_SIZE_MB:
                print(f"SHORT-BATCH UPLOADER WARNING: File {original_filename} ({file_size_mb:.2f}MB) exceeds Lambda limit ({MAX_LAMBDA_FILE_SIZE_MB}MB)")
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': f'File too large for short-batch processing',
                        'details': f'File size {file_size_mb:.2f}MB exceeds Lambda limit of {MAX_LAMBDA_FILE_SIZE_MB}MB',
                        'suggestion': 'Use /long-batch/upload endpoint for large files'
                    })
                }
            
            # FORCE to short-batch folder
            s3_folder = "short-batch-files"
            
            # Create S3 key with short-batch folder
            file_extension = os.path.splitext(original_filename)[1]
            s3_key = f"{s3_folder}/{file_id}{file_extension}"
            
            print(f"SHORT-BATCH UPLOADER: Uploading {original_filename} ({file_size_mb:.2f}MB) to {s3_key}")
            
            # Upload to S3 in short-batch folder
            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original-filename': original_filename,
                    'file-id': file_id,
                    'upload-timestamp': timestamp,
                    'forced-routing': 'short-batch',
                    'upload-endpoint': '/short-batch/upload'
                }
            )
            
            # Store metadata in DynamoDB
            item = {
                'file_id': file_id,
                'upload_timestamp': timestamp,
                'original_filename': original_filename,  # Keep for backwards compatibility
                'file_name': original_filename,           # Add the expected field name
                'content_type': content_type,
                'file_size': file_size,
                'file_size_mb': str(file_size_mb),
                's3_bucket': bucket_name,
                's3_key': s3_key,
                's3_folder': s3_folder,
                'processing_status': 'uploaded',
                'processing_route': 'short-batch',
                'routing_reason': ['Forced via /short-batch/upload endpoint'],
                'upload_source': 'short-batch-api',
                'upload_endpoint': '/short-batch/upload',
                'forced_routing': True,
                'bucket_name': bucket_name,  # For GSI query
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
            
            # Send directly to short-batch queue (no EventBridge for short batch)
            queue_message = {
                'fileId': file_id,
                'processing_type': 'short-batch',
                'timestamp': timestamp,
                'forced_routing': True,
                'metadata': item
            }
            
            sqs_response = sqs.send_message(
                QueueUrl=short_batch_queue_url,
                MessageBody=json.dumps(queue_message),
                MessageAttributes={
                    'processing_type': {
                        'StringValue': 'short-batch',
                        'DataType': 'String'
                    },
                    'file_id': {
                        'StringValue': file_id,
                        'DataType': 'String'
                    },
                    'forced_routing': {
                        'StringValue': 'true',
                        'DataType': 'String'
                    }
                }
            )
            
            print(f"SHORT-BATCH UPLOADER: Sent {file_id} to short-batch queue: {sqs_response['MessageId']}")
            
            uploaded_files.append({
                'file_id': file_id,
                'filename': original_filename,
                'size': file_size,
                'size_mb': round(file_size_mb, 2),
                's3_key': s3_key,
                's3_folder': s3_folder,
                'timestamp': timestamp,
                'content_type': content_type,
                'processing_route': 'short-batch',
                'forced_routing': True,
                'queue_message_id': sqs_response['MessageId']
            })
        
        # Return success response with all uploaded files
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'Successfully uploaded {len(uploaded_files)} file(s) for SHORT-BATCH processing',
                'processing_type': 'short-batch',
                'files': uploaded_files,
                'note': 'All files forced to short-batch processing via Lambda regardless of size'
            })
        }
        
    except Exception as e:
        print(f"SHORT-BATCH UPLOADER ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Short-batch upload failed',
                'details': str(e)
            })
        }