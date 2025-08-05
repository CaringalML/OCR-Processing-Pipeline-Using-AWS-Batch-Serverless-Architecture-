#!/usr/bin/env python3
"""
Invoice OCR Uploader Lambda Function
====================================

Specialized Lambda function for uploading invoices to be processed with 
enhanced invoice-specific OCR using Claude AI.

Features:
- Invoice-specific S3 folder structure
- Enhanced metadata for invoice processing
- Direct SQS messaging to invoice processor
- Invoice validation and preprocessing
- Support for common invoice formats (PDF, PNG, JPG, JPEG)

Version: 1.0.0
Author: OCR Processing System
Updated: 2025-08-04
"""

import json
import os
import logging
import boto3
import uuid
from datetime import datetime, timezone
from decimal import Decimal
import base64
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
UPLOAD_BUCKET = os.environ.get('UPLOAD_BUCKET')
METADATA_TABLE = os.environ.get('METADATA_TABLE')
INVOICE_QUEUE_URL = os.environ.get('INVOICE_QUEUE_URL')

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sqs_client = boto3.client('sqs')

# Supported invoice file types
SUPPORTED_INVOICE_TYPES = {
    'application/pdf': 'pdf',
    'image/png': 'png', 
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg'
}

def validate_invoice_file(content_type: str, file_size: int) -> dict:
    """Validate invoice file type and size"""
    result = {'valid': True, 'issues': []}
    
    # Check file type
    if content_type not in SUPPORTED_INVOICE_TYPES:
        result['valid'] = False
        result['issues'].append(f'Unsupported file type: {content_type}. Supported types: PDF, PNG, JPG, JPEG')
    
    # Check file size (max 10MB for invoices)
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        result['valid'] = False
        result['issues'].append(f'File too large: {file_size} bytes. Maximum: {max_size} bytes (10MB)')
    
    # Check minimum size
    min_size = 1024  # 1KB
    if file_size < min_size:
        result['valid'] = False
        result['issues'].append(f'File too small: {file_size} bytes. Minimum: {min_size} bytes')
    
    return result

def extract_invoice_metadata(body: dict) -> dict:
    """Extract optional user-provided metadata (OCR will extract the actual invoice data)"""
    metadata = {}
    
    # Optional user-provided metadata (not required since OCR will extract everything)
    metadata['description'] = body.get('description', 'Invoice OCR processing')
    metadata['tags'] = body.get('tags', ['invoice', 'financial'])
    metadata['processing_priority'] = body.get('priority', 'normal')  # urgent, normal, low
    metadata['business_category'] = body.get('businessCategory', '')  # optional classification
    
    # These will be populated by OCR processing
    metadata['vendor_name'] = ''
    metadata['invoice_number'] = ''
    metadata['invoice_date'] = ''
    metadata['due_date'] = ''
    metadata['total_amount'] = ''
    metadata['currency'] = 'USD'  # default, will be detected by OCR
    metadata['purchase_order'] = ''
    metadata['tax_amount'] = ''
    metadata['payment_terms'] = ''
    metadata['invoice_type'] = 'standard'
    
    return metadata

def parse_multipart_form_data(body, content_type):
    """Parse multipart/form-data from Lambda event"""
    if 'boundary=' not in content_type:
        raise ValueError("No boundary found in content-type")
    
    boundary = content_type.split('boundary=')[1]
    
    # Parse the multipart data
    parts = body.split(f'--{boundary}'.encode())
    form_data = {}
    files = []
    
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
                    if filename:
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
    """Main Lambda handler for invoice upload processing"""
    logger.info("Invoice OCR Uploader Lambda Handler Started")
    logger.info(f"Request ID: {context.aws_request_id if context else 'N/A'}")
    
    try:
        # Parse the multipart form data
        content_type = event.get('headers', {}).get('content-type', '') or event.get('headers', {}).get('Content-Type', '')
        
        if 'multipart/form-data' in content_type:
            # Handle multipart form data
            body = base64.b64decode(event['body']) if event.get('isBase64Encoded', False) else event['body'].encode()
            form_data, files = parse_multipart_form_data(body, content_type)
            
            if not files:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'No files provided',
                        'message': 'Please upload an invoice file'
                    })
                }
            
            # Get the first file (invoices are processed one at a time)
            file_info = files[0]
            file_bytes = file_info['content']
            file_name = file_info['filename']
            file_content_type = file_info['content_type']
            file_size = len(file_bytes)
            
            # Use form data for metadata
            request_data = form_data
            
        else:
            # Handle JSON format (fallback for API testing)
            if event.get('isBase64Encoded', False):
                body_str = base64.b64decode(event['body']).decode('utf-8')
            else:
                body_str = event['body']
            
            request_data = json.loads(body_str)
            
            # Extract file data from JSON request
            if 'file' not in request_data:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'No file provided',
                        'message': 'Please provide file as multipart/form-data or base64 in JSON'
                    })
                }
            
            # Decode the base64 file content
            try:
                file_bytes = base64.b64decode(request_data['file'])
            except Exception as e:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Invalid file data',
                        'message': 'File must be base64 encoded'
                    })
                }
            
            file_name = request_data.get('fileName', 'invoice.pdf')
            file_content_type = request_data.get('contentType', 'application/pdf')
            file_size = len(file_bytes)
        
        # Validate invoice file
        validation = validate_invoice_file(file_content_type, file_size)
        if not validation['valid']:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid Invoice File',
                    'message': '; '.join(validation['issues'])
                })
            }
        
        # Generate file ID and timestamps
        file_id = str(uuid.uuid4())
        upload_timestamp = datetime.now(timezone.utc).isoformat()
        
        # Get file extension
        file_extension = SUPPORTED_INVOICE_TYPES.get(file_content_type, 'unknown')
        
        # Create S3 key for invoice-specific folder
        s3_key = f"invoice-files/{file_id}.{file_extension}"
        
        logger.info(f"Processing invoice upload: {file_name} -> {s3_key}")
        
        # Extract invoice metadata
        invoice_metadata = extract_invoice_metadata(request_data)
        
        # Upload to S3
        try:
            s3_client.put_object(
                Bucket=UPLOAD_BUCKET,
                Key=s3_key,
                Body=file_bytes,
                ContentType=file_content_type,
                Metadata={
                    'original-filename': file_name,
                    'upload-timestamp': upload_timestamp,
                    'file-id': file_id,
                    'processing-type': 'invoice-ocr',
                    'content-type': file_content_type
                }
            )
            logger.info(f"Invoice uploaded to S3: s3://{UPLOAD_BUCKET}/{s3_key}")
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Upload Failed',
                    'message': 'Failed to upload invoice to storage'
                })
            }
        
        # Store metadata in DynamoDB
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        metadata_item = {
            'invoice_id': file_id,
            'upload_timestamp': upload_timestamp,
            'original_filename': file_name,
            'file_name': file_name,
            'content_type': file_content_type,
            'file_size': file_size,
            'file_size_mb': str(file_size_mb),
            's3_bucket': UPLOAD_BUCKET,
            's3_key': s3_key,
            's3_folder': 'invoice-files',
            'processing_status': 'uploaded',
            'processing_route': 'invoice-ocr',
            'routing_reason': ['Invoice-specific OCR processing endpoint'],
            'upload_source': 'invoice-api',
            'upload_endpoint': '/batch/short-batch/invoices/upload',
            'file_extension': file_extension,
            
            # Placeholder fields for DynamoDB indexing (will be populated by OCR)
            'vendor_name': 'PENDING_OCR',
            'invoice_number': 'PENDING_OCR',
            'invoice_date': 'PENDING_OCR',
            'due_date': '',
            'total_amount': '',
            'currency': 'USD',
            'purchase_order': '',
            'tax_amount': '',
            'payment_terms': '',
            'invoice_type': 'standard',
            'business_category': invoice_metadata.get('business_category', ''),
            'processing_priority': invoice_metadata.get('processing_priority', 'normal'),
            
            # User-provided metadata
            'description': invoice_metadata.get('description', 'Invoice OCR processing'),
            'tags': invoice_metadata.get('tags', ['invoice', 'financial'])
        }
        
        try:
            if METADATA_TABLE:
                table = dynamodb.Table(METADATA_TABLE)
                table.put_item(Item=metadata_item)
                logger.info(f"Invoice metadata stored in DynamoDB: {file_id}")
        except ClientError as e:
            logger.error(f"Failed to store metadata in DynamoDB: {e}")
            # Continue processing even if metadata storage fails
        
        # Send message to invoice processing queue
        invoice_message = {
            'fileId': file_id,
            'processing_type': 'invoice-ocr',
            'timestamp': upload_timestamp,
            'invoice_processing': True,
            'metadata': metadata_item
        }
        
        try:
            if INVOICE_QUEUE_URL:
                sqs_client.send_message(
                    QueueUrl=INVOICE_QUEUE_URL,
                    MessageBody=json.dumps(invoice_message),
                    MessageAttributes={
                        'processing_type': {
                            'StringValue': 'invoice-ocr',
                            'DataType': 'String'
                        },
                        'file_id': {
                            'StringValue': file_id,
                            'DataType': 'String'
                        },
                        'invoice_processing': {
                            'StringValue': 'true',
                            'DataType': 'String'
                        }
                    }
                )
                logger.info(f"Invoice processing message sent to SQS: {file_id}")
        except ClientError as e:
            logger.error(f"Failed to send message to SQS: {e}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Processing Queue Error',
                    'message': 'Failed to queue invoice for processing'
                })
            }
        
        # Return success response
        response_data = {
            'fileId': file_id,
            'fileName': file_name,
            'uploadTimestamp': upload_timestamp,
            'processingStatus': 'uploaded',
            'processingRoute': 'invoice-ocr',
            'fileSize': file_size,
            'fileSizeMB': file_size_mb,
            'contentType': file_content_type,
            's3Key': s3_key,
            'message': 'Invoice uploaded successfully and queued for OCR processing - all data will be extracted automatically'
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            })
        }