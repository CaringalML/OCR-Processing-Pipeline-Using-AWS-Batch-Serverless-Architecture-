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
    Handle S3 file upload from API Gateway
    Now supports folder structure: short-batch-files/ and long-batch-files/
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
            
            # Calculate file size for initial routing decision
            file_size = len(file_content)
            file_size_mb = file_size / (1024 * 1024)
            
            # Determine initial folder based on size (can be overridden by smart router later)
            # This is just for initial storage organization
            initial_folder = "short-batch-files" if file_size_mb <= 10 else "long-batch-files"
            
            # Create S3 key with folder structure
            file_extension = os.path.splitext(original_filename)[1]
            s3_key = f"{initial_folder}/{file_id}{file_extension}"
            
            # Upload to S3 with folder structure
            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original-filename': original_filename,
                    'file-id': file_id,
                    'upload-timestamp': timestamp,
                    'initial-routing': initial_folder
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
                's3_folder': initial_folder,
                'processing_status': 'uploaded',
                'upload_source': 'api',
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
            
            uploaded_files.append({
                'file_id': file_id,
                'filename': original_filename,
                'size': file_size,
                'size_mb': round(file_size_mb, 2),
                's3_key': s3_key,
                's3_folder': initial_folder,
                'timestamp': timestamp,
                'content_type': content_type
            })
        
        # Return success response with all uploaded files
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': f'Successfully uploaded {len(uploaded_files)} file(s)',
                'files': uploaded_files,
                'note': 'Files are initially organized by size. Smart router will make final processing decision.'
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