import json
import boto3
import os
from datetime import datetime, timezone
from decimal import Decimal

def decimal_to_json(obj):
    """Convert Decimal objects to JSON-serializable types"""
    if isinstance(obj, Decimal):
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

def lambda_handler(event, context):
    """
    Lambda function to finalize OCR results by saving user-selected text to ocr_finalized table
    Users can choose between formattedText or refinedText, and optionally edit before finalizing
    
    Triggered by API Gateway POST requests to /finalize/{fileId} endpoint
    
    Request body should contain:
    {
        "textSource": "formatted" | "refined",  # Required: which text version to finalize
        "editedText": "Optional edited version", # Optional: if provided, this overrides the selected text
        "finalizedBy": "user@example.com",      # Optional: who finalized the document
        "notes": "Additional notes"              # Optional: any notes about finalization
    }
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    results_table_name = os.environ.get('RESULTS_TABLE', 'ocr-processor-batch-processing-results')
    finalized_table_name = os.environ.get('FINALIZED_TABLE', 'ocr-processor-batch-finalized-results')
    
    if not results_table_name or not finalized_table_name:
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
        # Parse path parameters and request body
        path_params = event.get('pathParameters', {}) or {}
        query_params = event.get('queryStringParameters', {}) or {}
        file_id = path_params.get('fileId') or query_params.get('fileId')
        
        print(f"Finalization request received for fileId: {file_id}")
        print(f"Event path parameters: {path_params}")
        print(f"Event query parameters: {query_params}")
        
        if not file_id:
            print("ERROR: Missing fileId in request")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Missing fileId in path parameters'
                })
            }
        
        # Parse request body
        body_raw = event.get('body', '{}')
        print(f"Request body: {body_raw}")
        body = json.loads(body_raw)
        text_source = body.get('textSource')
        edited_text = body.get('editedText')  # Optional edited version
        finalized_by = body.get('finalizedBy', 'system')
        notes = body.get('notes', '')
        
        print(f"Parsed body - textSource: {text_source}, hasEditedText: {bool(edited_text)}, finalizedBy: {finalized_by}")
        
        # Validate text source selection
        if text_source not in ['formatted', 'refined']:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'textSource must be either "formatted" or "refined"'
                })
            }
        
        # Initialize tables
        results_table = dynamodb.Table(results_table_name)
        finalized_table = dynamodb.Table(finalized_table_name)
        
        # Get current OCR results
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
        
        current_results = results_response['Item']
        
        # Check if file has been processed
        processing_status = current_results.get('processing_status')
        if processing_status not in ['processed', 'completed']:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': f'File {file_id} has not been processed yet. Status: {processing_status}'
                })
            }
        
        # Get the selected text based on user choice
        if text_source == 'formatted':
            base_text = current_results.get('formatted_text', '')
            if not base_text:
                # Try alternative field names for backward compatibility
                base_text = current_results.get('formattedText', '') or current_results.get('extracted_text', '')
                if not base_text:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': 'Bad Request',
                            'message': f'File {file_id} does not have formatted text available'
                        })
                    }
        else:  # refined
            base_text = current_results.get('refined_text', '')
            if not base_text:
                # Try alternative field names for backward compatibility
                base_text = current_results.get('refinedText', '') or current_results.get('extracted_text', '')
                if not base_text:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': 'Bad Request',
                            'message': f'File {file_id} does not have refined text available'
                        })
                    }
        
        # Use edited text if provided, otherwise use the selected base text
        finalized_text = edited_text if edited_text else base_text
        
        # Track if user made edits before finalizing
        was_edited = bool(edited_text)
        
        # Prepare finalized record
        finalized_timestamp = datetime.now(timezone.utc).isoformat()
        finalized_record = {
            'file_id': file_id,
            'finalized_timestamp': finalized_timestamp,
            'finalized_text': finalized_text,
            'text_source': text_source,
            'was_edited_before_finalization': was_edited,
            'original_formatted_text': current_results.get('formatted_text', ''),
            'original_refined_text': current_results.get('refined_text', ''),
            'finalized_by': finalized_by,
            'notes': notes,
            
            # File and S3 metadata
            'file_name': current_results.get('file_name', ''),
            'bucket': current_results.get('bucket', ''),
            'key': current_results.get('key', ''),
            's3_uri': current_results.get('s3_uri', ''),
            'content_type': current_results.get('content_type', ''),
            'file_size': current_results.get('file_size', 0),
            
            # Timestamps
            'upload_timestamp': current_results.get('upload_timestamp', ''),
            'processing_timestamp': current_results.get('processing_timestamp', ''),
            'processed_at': current_results.get('processed_at', ''),
            
            # Processing metadata
            'processing_type': current_results.get('processing_type', ''),
            'processing_status': current_results.get('processing_status', ''),
            'processing_cost': current_results.get('processing_cost', 0),
            'total_cost': current_results.get('total_cost', 0),
            'processing_time_seconds': current_results.get('processing_time_seconds', 0),
            'processing_duration': current_results.get('processing_duration', ''),
            'model_used': current_results.get('model_used', ''),
            'confidence_score': current_results.get('confidence_score', 0),
            
            # OCR and analysis data
            'user_edited': current_results.get('user_edited', False),
            'edit_history': current_results.get('edit_history', []),
            'token_usage': current_results.get('token_usage', {}),
            'language_detection': current_results.get('language_detection', {}),
            'entity_analysis': current_results.get('entity_analysis', {}),
            'textAnalysis': current_results.get('textAnalysis', {}),
            
            # Publication metadata fields
            'publication': current_results.get('publication', ''),
            'publication_year': current_results.get('publication_year', ''),
            'publication_title': current_results.get('publication_title', ''),
            'publication_author': current_results.get('publication_author', ''),
            'publication_description': current_results.get('publication_description', ''),
            'publication_page': current_results.get('publication_page', ''),
            'publication_tags': current_results.get('publication_tags', []),
            'publication_collection': current_results.get('publication_collection', ''),
            'publication_document_type': current_results.get('publication_document_type', ''),
            
            # Additional processing metadata
            'total_pages': current_results.get('total_pages', 0)
        }
        
        # Save to finalized table
        finalized_table.put_item(Item=finalized_record)
        
        # ARCHITECTURAL IMPROVEMENT: Remove document from processing_results table 
        # to avoid duplication and clean up the processing queue
        # This ensures /batch/processed only shows documents still being processed
        # while finalized documents are exclusively in the finalized table
        try:
            results_table.delete_item(
                Key={'file_id': file_id}
            )
            print(f"Successfully removed file {file_id} from processing_results table after finalization")
        except Exception as delete_error:
            print(f"WARNING: Failed to remove file {file_id} from processing_results: {str(delete_error)}")
            # Continue execution - finalization was successful even if cleanup failed
        
        # Build response
        message = f'OCR results finalized successfully using {text_source} text and moved to finalized inventory'
        if was_edited:
            message = f'OCR results finalized successfully using edited {text_source} text and moved to finalized inventory'
            
        response_data = {
            'fileId': file_id,
            'finalizedTimestamp': finalized_timestamp,
            'textSource': text_source,
            'wasEdited': was_edited,
            'finalizedBy': finalized_by,
            'message': message,
            'finalizedTextPreview': finalized_text[:500] if len(finalized_text) > 500 else finalized_text
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
        }
        
    except json.JSONDecodeError:
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