import json
import boto3
import os
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

# Environment variables
METADATA_TABLE = os.environ['METADATA_TABLE']
SHORT_BATCH_QUEUE_URL = os.environ['SHORT_BATCH_QUEUE_URL']
LONG_BATCH_QUEUE_URL = os.environ['LONG_BATCH_QUEUE_URL']
FILE_SIZE_THRESHOLD_MB = int(os.environ.get('FILE_SIZE_THRESHOLD_MB', '10'))  # Default 10MB

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Smart router that decides between short-batch (Lambda) and long-batch (AWS Batch) processing
    based on file size and other criteria.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract file information from the event
        body = json.loads(event.get('body', '{}'))
        file_id = body.get('file_id')
        file_size_bytes = body.get('file_size', 0)
        file_type = body.get('file_type', '')
        processing_priority = body.get('priority', 'normal')  # normal, high, urgent
        
        if not file_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'file_id is required'
                })
            }
        
        # Convert bytes to MB
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Routing decision logic
        routing_decision = make_routing_decision(
            file_size_mb=file_size_mb,
            file_type=file_type,
            priority=processing_priority
        )
        
        logger.info(f"Routing decision for file {file_id}: {routing_decision}")
        
        # Route to appropriate processing queue
        if routing_decision['route'] == 'short-batch':
            result = route_to_short_batch(file_id, body)
        else:
            result = route_to_long_batch(file_id, body)
        
        # Update metadata with routing information
        update_metadata(file_id, routing_decision)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'File routed successfully',
                'file_id': file_id,
                'routing': routing_decision,
                'queue_message_id': result.get('MessageId')
            })
        }
        
    except Exception as e:
        logger.error(f"Error in smart router: {str(e)}")
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

def make_routing_decision(file_size_mb: float, file_type: str, priority: str) -> Dict[str, Any]:
    """
    Intelligent routing decision based on multiple factors.
    """
    decision = {
        'route': 'short-batch',  # default
        'reason': [],
        'estimated_processing_time': '1-5 minutes',
        'processor_type': 'lambda'
    }
    
    # Size-based routing (primary factor)
    if file_size_mb > FILE_SIZE_THRESHOLD_MB:
        decision['route'] = 'long-batch'
        decision['reason'].append(f'File size ({file_size_mb:.1f}MB) exceeds threshold ({FILE_SIZE_THRESHOLD_MB}MB)')
        decision['estimated_processing_time'] = '5-30 minutes'
        decision['processor_type'] = 'aws_batch'
    else:
        decision['reason'].append(f'File size ({file_size_mb:.1f}MB) within short-batch threshold')
    
    # File type considerations
    complex_types = ['pdf', 'tiff', 'tif']
    simple_types = ['jpg', 'jpeg', 'png']
    
    file_ext = file_type.lower().split('/')[-1] if '/' in file_type else file_type.lower()
    
    if file_ext in complex_types:
        # Complex file types might need more processing power
        if file_size_mb > 5:  # Lower threshold for complex types
            decision['route'] = 'long-batch'
            decision['reason'].append(f'Complex file type ({file_ext}) requires batch processing')
            decision['processor_type'] = 'aws_batch'
    elif file_ext in simple_types:
        # Simple images can usually be processed quickly
        decision['reason'].append(f'Simple file type ({file_ext}) suitable for quick processing')
    
    # Priority override
    if priority == 'urgent':
        # Urgent files go to short-batch for faster startup (even if larger)
        if file_size_mb <= FILE_SIZE_THRESHOLD_MB * 1.5:  # Allow 50% size increase for urgent
            decision['route'] = 'short-batch'
            decision['reason'].append('Urgent priority overrides size threshold')
            decision['processor_type'] = 'lambda_urgent'
            decision['estimated_processing_time'] = '30 seconds - 2 minutes'
    elif priority == 'low':
        # Low priority files can use batch processing for cost efficiency
        if file_size_mb > FILE_SIZE_THRESHOLD_MB * 0.5:  # Lower threshold for low priority
            decision['route'] = 'long-batch'
            decision['reason'].append('Low priority routed to cost-efficient batch processing')
    
    return decision

def route_to_short_batch(file_id: str, file_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route file to short-batch Lambda processing via SQS.
    """
    message_body = {
        'file_id': file_id,
        'processing_type': 'short-batch',
        'timestamp': file_data.get('timestamp'),
        'metadata': file_data
    }
    
    response = sqs.send_message(
        QueueUrl=SHORT_BATCH_QUEUE_URL,
        MessageBody=json.dumps(message_body),
        MessageAttributes={
            'processing_type': {
                'StringValue': 'short-batch',
                'DataType': 'String'
            },
            'file_id': {
                'StringValue': file_id,
                'DataType': 'String'
            }
        }
    )
    
    logger.info(f"Routed file {file_id} to short-batch queue: {response['MessageId']}")
    return response

def route_to_long_batch(file_id: str, file_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route file to long-batch AWS Batch processing via SQS.
    """
    message_body = {
        'file_id': file_id,
        'processing_type': 'long-batch',
        'timestamp': file_data.get('timestamp'),
        'metadata': file_data
    }
    
    response = sqs.send_message(
        QueueUrl=LONG_BATCH_QUEUE_URL,
        MessageBody=json.dumps(message_body),
        MessageAttributes={
            'processing_type': {
                'StringValue': 'long-batch',
                'DataType': 'String'
            },
            'file_id': {
                'StringValue': file_id,
                'DataType': 'String'
            }
        }
    )
    
    logger.info(f"Routed file {file_id} to long-batch queue: {response['MessageId']}")
    return response

def update_metadata(file_id: str, routing_decision: Dict[str, Any]) -> None:
    """
    Update file metadata with routing information.
    Respects forced routing from dedicated endpoints.
    """
    try:
        table = dynamodb.Table(METADATA_TABLE)
        
        # Get current timestamp for routing decision
        from datetime import datetime
        routing_timestamp = datetime.utcnow().isoformat()
        
        # Check if this file was uploaded via forced routing (e.g., /long-batch/upload or /short-batch/upload)
        try:
            response = table.get_item(Key={'file_id': file_id})
            item = response.get('Item', {})
            forced_routing = item.get('forced_routing', False)
            existing_s3_folder = item.get('s3_folder')
            
            if forced_routing and existing_s3_folder:
                # Respect forced routing - don't override S3 folder
                logger.info(f"File {file_id} has forced routing, preserving S3 folder: {existing_s3_folder}")
                
                table.update_item(
                    Key={'file_id': file_id},
                    UpdateExpression='SET processing_route = :route, routing_reason = :reason, routing_timestamp = :timestamp, estimated_processing_time = :time, processor_type = :processor',
                    ExpressionAttributeValues={
                        ':route': routing_decision['route'],
                        ':reason': routing_decision['reason'],
                        ':timestamp': routing_timestamp,
                        ':time': routing_decision['estimated_processing_time'],
                        ':processor': routing_decision['processor_type']
                    }
                )
                
                logger.info(f"Updated metadata for file {file_id} with routing decision, preserved S3 folder: {existing_s3_folder}")
                
            else:
                # Normal routing - determine S3 folder based on routing decision
                s3_folder = "short-batch-files" if routing_decision['route'] == 'short-batch' else "long-batch-files"
                
                table.update_item(
                    Key={'file_id': file_id},
                    UpdateExpression='SET processing_route = :route, routing_reason = :reason, routing_timestamp = :timestamp, estimated_processing_time = :time, processor_type = :processor, s3_folder = :folder',
                    ExpressionAttributeValues={
                        ':route': routing_decision['route'],
                        ':reason': routing_decision['reason'],
                        ':timestamp': routing_timestamp,
                        ':time': routing_decision['estimated_processing_time'],
                        ':processor': routing_decision['processor_type'],
                        ':folder': s3_folder
                    }
                )
                
                logger.info(f"Updated metadata for file {file_id} with routing decision, S3 folder: {s3_folder}")
                
        except Exception as get_error:
            logger.warning(f"Could not check existing metadata for file {file_id}: {str(get_error)}, proceeding with normal routing")
            
            # Fallback to normal routing if we can't check existing metadata
            s3_folder = "short-batch-files" if routing_decision['route'] == 'short-batch' else "long-batch-files"
            
            table.update_item(
                Key={'file_id': file_id},
                UpdateExpression='SET processing_route = :route, routing_reason = :reason, routing_timestamp = :timestamp, estimated_processing_time = :time, processor_type = :processor, s3_folder = :folder',
                ExpressionAttributeValues={
                    ':route': routing_decision['route'],
                    ':reason': routing_decision['reason'],
                    ':timestamp': routing_timestamp,
                    ':time': routing_decision['estimated_processing_time'],
                    ':processor': routing_decision['processor_type'],
                    ':folder': s3_folder
                }
            )
            
            logger.info(f"Updated metadata for file {file_id} with routing decision (fallback), S3 folder: {s3_folder}")
        
    except Exception as e:
        logger.error(f"Failed to update metadata for file {file_id}: {str(e)}")
        # Don't fail the whole operation if metadata update fails