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
                            'field_name': name,
                            'filename': filename,
                            'content': content,
                            'content_type': file_content_type
                        })
                else:
                    # This is a form field
                    form_data[name] = content.decode()
    
    return form_data, files

def process_single_file_upload(s3_client, dynamodb, bucket_name, dynamodb_table, file_name, file_bytes, file_content_type):
    """Process upload of a single file"""
    try:
        # Generate unique file ID and S3 key
        file_id = uuid.uuid4().hex
        timestamp = datetime.utcnow()
        s3_key = f"uploads/{timestamp.strftime('%Y/%m/%d')}/{file_id}/{file_name}"
        
        # Upload file to S3
        s3_response = s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_bytes,
            ContentType=file_content_type,
            Metadata={
                'file_id': file_id,
                'original_name': file_name,
                'upload_timestamp': timestamp.isoformat()
            }
        )
        
        # Store metadata in DynamoDB
        table = dynamodb.Table(dynamodb_table)
        table.put_item(
            Item={
                'file_id': file_id,
                'upload_timestamp': timestamp.isoformat(),
                'bucket_name': bucket_name,
                's3_key': s3_key,
                'file_name': file_name,
                'file_size': len(file_bytes),
                'content_type': file_content_type,
                'processing_status': 'uploaded',
                'etag': s3_response['ETag'].strip('"'),
                'upload_date': timestamp.strftime('%Y-%m-%d'),
                'expiration_time': int((timestamp.timestamp() + 365 * 24 * 60 * 60))  # 1 year TTL
            }
        )
        
        print(f"Successfully uploaded file: {file_id} to S3: {s3_key}")
        
        return {
            'success': True,
            'data': {
                'fileId': file_id,
                'fileName': file_name,
                's3Key': s3_key,
                'bucket': bucket_name,
                'size': len(file_bytes),
                'timestamp': timestamp.isoformat(),
                'status': 'File uploaded and queued for processing'
            }
        }
        
    except Exception as e:
        print(f"Error uploading file {file_name}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def lambda_handler(event, context):
    """
    AWS Lambda handler for S3 file uploads
    Handles multipart/form-data uploads from API Gateway
    """
    
    # Initialize AWS clients
    s3_client = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration from environment variables
    bucket_name = os.environ.get('UPLOAD_BUCKET_NAME')
    dynamodb_table = os.environ.get('DYNAMODB_TABLE')
    
    # Validate environment variables
    if not bucket_name or not dynamodb_table:
        error_msg = "Missing required environment variables"
        print(f"ERROR: {error_msg}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Configuration Error',
                'message': error_msg,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    try:
        # Get content type from headers
        content_type = event.get('headers', {}).get('content-type', '') or event.get('headers', {}).get('Content-Type', '')
        
        if 'multipart/form-data' in content_type:
            # Handle multipart form data (supports multiple files)
            body = base64.b64decode(event['body']) if event.get('isBase64Encoded') else event['body'].encode()
            form_data, files = parse_multipart_form_data(body, content_type)
            
            # Check if any files were uploaded
            if not files:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Bad Request',
                        'message': 'No files found in upload',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }
            
            # Process multiple files
            upload_results = []
            upload_errors = []
            
            for file_info in files:
                try:
                    file_name = file_info['filename']
                    file_bytes = file_info['content']
                    file_content_type = file_info['content_type']
                    
                    # Validate file
                    if not file_name:
                        file_name = f"file-{uuid.uuid4().hex[:8]}"
                        
                    if len(file_bytes) == 0:
                        upload_errors.append({
                            'filename': file_name,
                            'error': 'File is empty'
                        })
                        continue
                    
                    # Process single file upload
                    result = process_single_file_upload(
                        s3_client, dynamodb, bucket_name, dynamodb_table,
                        file_name, file_bytes, file_content_type
                    )
                    
                    if result['success']:
                        upload_results.append(result['data'])
                    else:
                        upload_errors.append({
                            'filename': file_name,
                            'error': result['error']
                        })
                        
                except Exception as e:
                    upload_errors.append({
                        'filename': file_info.get('filename', 'unknown'),
                        'error': str(e)
                    })
            
            # Return results for multiple files
            return {
                'statusCode': 200 if upload_results else 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': len(upload_results) > 0,
                    'message': f'Processed {len(files)} files: {len(upload_results)} successful, {len(upload_errors)} failed',
                    'uploadedFiles': upload_results,
                    'errors': upload_errors,
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
            
        else:
            # Fallback to JSON format for backward compatibility (single file)
            body = json.loads(event['body'])
            
            file_name = body.get('fileName', f"file-{uuid.uuid4().hex[:8]}")
            file_content = body.get('fileContent')  # Base64 encoded
            file_content_type = body.get('contentType', 'application/octet-stream')
            
            if not file_content:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Bad Request',
                        'message': 'Missing file content',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }
            
            file_bytes = base64.b64decode(file_content)
            
            # Validate file
            if not file_name:
                file_name = f"file-{uuid.uuid4().hex[:8]}"
                
            if len(file_bytes) == 0:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Bad Request',
                        'message': 'File is empty',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }
            
            # Process single file upload
            result = process_single_file_upload(
                s3_client, dynamodb, bucket_name, dynamodb_table,
                file_name, file_bytes, file_content_type
            )
            
            if result['success']:
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': True,
                        'message': 'File uploaded successfully',
                        **result['data']
                    })
                }
            else:
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': False,
                        'error': 'File upload failed',
                        'details': result['error'],
                        'timestamp': datetime.utcnow().isoformat()
                    })
                }
        
    except Exception as e:
        error_msg = f"Error uploading file: {str(e)}"
        print(f"ERROR: {error_msg}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'File upload failed',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }
