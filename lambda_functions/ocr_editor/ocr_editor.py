import json
import boto3
import os
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key
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
    Lambda function to update OCR results (refinedText and formattedText)
    Triggered by API Gateway PATCH requests to /processed/{fileId} endpoint
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    metadata_table_name = os.environ.get('METADATA_TABLE')
    results_table_name = os.environ.get('RESULTS_TABLE')
    
    if not all([metadata_table_name, results_table_name]):
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
        # Parse path parameters
        path_params = event.get('pathParameters', {}) or {}
        file_id = path_params.get('fileId')
        
        if not file_id:
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
        body = json.loads(event.get('body', '{}'))
        
        # Validate that at least one field is being updated
        refined_text = body.get('refinedText')
        formatted_text = body.get('formattedText')
        
        if refined_text is None and formatted_text is None:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'At least one of refinedText or formattedText must be provided'
                })
            }
        
        # Get metadata to verify file exists
        metadata_table = dynamodb.Table(metadata_table_name)
        metadata_response = metadata_table.query(
            KeyConditionExpression=Key('file_id').eq(file_id),
            Limit=1
        )
        
        if not metadata_response['Items']:
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
        
        file_metadata = metadata_response['Items'][0]
        
        # Check if file has been processed
        if file_metadata.get('processing_status') != 'processed':
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': f'File {file_id} has not been processed yet. Status: {file_metadata.get("processing_status")}'
                })
            }
        
        # Get current results
        results_table = dynamodb.Table(results_table_name)
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
                    'message': f'Processing results for file {file_id} not found'
                })
            }
        
        current_results = results_response['Item']
        
        # Prepare update expression
        update_expression = []
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        # Track edit history
        edit_history = current_results.get('edit_history', [])
        edit_entry = {
            'edited_at': datetime.now(timezone.utc).isoformat(),
            'edited_fields': []
        }
        
        # Update refined text if provided
        if refined_text is not None:
            update_expression.append('#rt = :rt')
            expression_attribute_names['#rt'] = 'refined_text'
            expression_attribute_values[':rt'] = refined_text
            
            # Save original if this is the first edit
            if 'original_refined_text' not in current_results:
                update_expression.append('original_refined_text = :ort')
                expression_attribute_values[':ort'] = current_results.get('refined_text', '')
            
            edit_entry['edited_fields'].append('refined_text')
            edit_entry['previous_refined_text'] = current_results.get('refined_text', '')
        
        # Update formatted text if provided
        if formatted_text is not None:
            update_expression.append('#ft = :ft')
            expression_attribute_names['#ft'] = 'formatted_text'
            expression_attribute_values[':ft'] = formatted_text
            
            # Save original if this is the first edit
            if 'original_formatted_text' not in current_results:
                update_expression.append('original_formatted_text = :oft')
                expression_attribute_values[':oft'] = current_results.get('formatted_text', '')
            
            edit_entry['edited_fields'].append('formatted_text')
            edit_entry['previous_formatted_text'] = current_results.get('formatted_text', '')
        
        # Add edit history entry
        edit_history.append(edit_entry)
        update_expression.append('edit_history = :eh')
        expression_attribute_values[':eh'] = edit_history[-10:]  # Keep last 10 edits
        
        # Update last modified timestamp
        update_expression.append('last_edited = :le')
        expression_attribute_values[':le'] = datetime.now(timezone.utc).isoformat()
        
        # Update user edit flag
        update_expression.append('user_edited = :ue')
        expression_attribute_values[':ue'] = True
        
        # Perform the update
        results_table.update_item(
            Key={'file_id': file_id},
            UpdateExpression='SET ' + ', '.join(update_expression),
            ExpressionAttributeNames=expression_attribute_names if expression_attribute_names else None,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        # Get updated results
        updated_response = results_table.get_item(
            Key={'file_id': file_id}
        )
        
        updated_item = decimal_to_json(updated_response['Item'])
        
        # Build response
        response_data = {
            'fileId': file_id,
            'refinedText': updated_item.get('refined_text', ''),
            'formattedText': updated_item.get('formatted_text', ''),
            'userEdited': updated_item.get('user_edited', False),
            'lastEdited': updated_item.get('last_edited', ''),
            'editHistory': updated_item.get('edit_history', [])[-5:],  # Return last 5 edits
            'message': 'OCR results updated successfully'
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