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
    
    # Extract boundary - handle multiple boundary parameters by taking the last one
    boundary_parts = content_type.split('boundary=')
    if len(boundary_parts) < 2:
        raise ValueError("No boundary found in content-type")
    
    # Take the last boundary parameter and clean it
    boundary = boundary_parts[-1].split(';')[0].strip()
    
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
    Handle S3 file upload specifically for LONG-BATCH processing
    All files uploaded through this endpoint will be forced to long-batch processing
    """
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    
    bucket_name = os.environ['UPLOAD_BUCKET_NAME']
    table_name = os.environ['DYNAMODB_TABLE']
    table = dynamodb.Table(table_name)
    
    print(f"LONG-BATCH UPLOADER: Processing upload request")
    print(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # Parse the multipart form data
        content_type = event.get('headers', {}).get('content-type', '') or event.get('headers', {}).get('Content-Type', '')
        
        # Handle body encoding - API Gateway may send as base64 for binary data
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(event['body'])
        else:
            # Try to handle as string first, then as bytes
            event_body = event.get('body', '')
            if isinstance(event_body, str):
                body = event_body.encode('latin1')  # Use latin1 to preserve binary data
            else:
                body = event_body
        
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
            
            # FORCE to long-batch folder (override size-based logic)
            s3_folder = "long-batch-files"
            
            # Create S3 key with long-batch folder
            file_extension = os.path.splitext(original_filename)[1]
            s3_key = f"{s3_folder}/{file_id}{file_extension}"
            
            print(f"LONG-BATCH UPLOADER: Uploading {original_filename} ({file_size_mb:.2f}MB) to {s3_key}")
            
            # Upload to S3 in long-batch folder
            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original-filename': original_filename,
                    'file-id': file_id,
                    'upload-timestamp': timestamp,
                    'forced-routing': 'long-batch',
                    'upload-endpoint': '/long-batch/upload'
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
                'processing_route': 'long-batch',
                'routing_reason': ['Forced via /long-batch/upload endpoint'],
                'upload_source': 'long-batch-api',
                'upload_endpoint': '/long-batch/upload',
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
            
            # Send direct SQS message for immediate processing (replaces EventBridge)
            sqs_message = {
                'fileId': file_id,
                'bucket': bucket_name,
                'key': s3_key,
                'fileName': original_filename,
                'fileSize': file_size,
                'contentType': content_type,
                'uploadTimestamp': timestamp,
                'processingRoute': 'long-batch',
                'forcedRouting': True
            }
            
            try:
                sqs_client = boto3.client('sqs')
                queue_url = os.environ.get('LONG_BATCH_QUEUE_URL')
                
                if queue_url:
                    response = sqs_client.send_message(
                        QueueUrl=queue_url,
                        MessageBody=json.dumps(sqs_message),
                        MessageAttributes={
                            'ProcessingRoute': {
                                'StringValue': 'long-batch',
                                'DataType': 'String'
                            },
                            'FileSize': {
                                'StringValue': str(file_size),
                                'DataType': 'Number'
                            }
                        }
                    )
                    print(f"LONG-BATCH UPLOADER: File {file_id} uploaded and SQS message sent. MessageId: {response['MessageId']}")
                else:
                    print(f"WARNING: LONG_BATCH_QUEUE_URL not configured - file uploaded but no processing message sent")
                    
            except Exception as sqs_error:
                print(f"ERROR sending SQS message for {file_id}: {sqs_error}")
                # Continue processing - file is uploaded, but processing may need manual trigger
            
            uploaded_files.append({
                'file_id': file_id,
                'filename': original_filename,
                'size': file_size,
                'size_mb': round(file_size_mb, 2),
                's3_key': s3_key,
                's3_folder': s3_folder,
                'timestamp': timestamp,
                'content_type': content_type,
                'processing_route': 'long-batch',
                'forced_routing': True
            })
        
        # Return success response with all uploaded files
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'Successfully uploaded {len(uploaded_files)} file(s) for LONG-BATCH processing',
                'processing_type': 'long-batch',
                'files': uploaded_files,
                'note': 'All files forced to long-batch processing via AWS Batch regardless of size'
            })
        }
        
    except Exception as e:
        print(f"LONG-BATCH UPLOADER ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Long-batch upload failed',
                'details': str(e)
            })
        }