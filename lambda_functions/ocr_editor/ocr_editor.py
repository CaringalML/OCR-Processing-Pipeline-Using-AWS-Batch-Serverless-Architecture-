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
    Lambda function to update OCR results (refinedText, formattedText, and metadata)
    Triggered by API Gateway PATCH requests to /processed/{fileId} endpoint
    
    IMPORTANT: This endpoint uses HTTP PATCH method instead of PUT for the following reasons:
    
    1. SEMANTIC CORRECTNESS:
       - PATCH is designed for partial updates/modifications of existing resources
       - PUT is designed for complete replacement of resources
       - We're only updating specific fields (refinedText/formattedText/metadata) not replacing entire record
    
    2. PARTIAL UPDATE CAPABILITY:
       - Users can update refinedText, formattedText, metadata, or any combination
       - PATCH allows optional fields in request body
       - PUT would require all fields to be sent (complete resource replacement)
    
    3. IDEMPOTENCY CONSIDERATIONS:
       - PATCH can be non-idempotent (each call may produce different results due to edit history)
       - PUT is idempotent (same request produces same result)
       - Our edit tracking makes each PATCH unique (timestamps, history)
    
    4. HTTP STANDARD COMPLIANCE:
       - RFC 5789 defines PATCH for partial modifications
       - RFC 7231 defines PUT for complete replacement
       - Using PATCH follows REST API best practices
    
    5. CLIENT EXPECTATIONS:
       - Frontend developers expect PATCH for partial updates
       - PATCH clearly indicates "modify existing" vs PUT's "replace entire"
       - Better API documentation and understanding
    
    6. FIELD PRESERVATION:
       - PATCH preserves fields not mentioned in request
       - PUT would require all existing fields to be resent to preserve them
       - Prevents accidental data loss from incomplete requests
    
    Examples:
    - PATCH: { "refinedText": "new text" } - only updates refinedText
    - PATCH: { "metadata": { "title": "New Title", "author": "New Author" } } - only updates specific metadata
    - PATCH: { "refinedText": "new", "formattedText": "new", "metadata": {...} } - updates multiple fields
    - PUT: Would need entire resource: { "refinedText": "new", "formattedText": "existing", "metadata": {...}, "all_other_fields": "..." }
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
        # Parse path parameters and query parameters for fileId
        path_params = event.get('pathParameters', {}) or {}
        query_params = event.get('queryStringParameters', {}) or {}
        file_id = path_params.get('fileId') or query_params.get('fileId')
        
        if not file_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'Missing fileId in path parameters or query parameters'
                })
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate that at least one field is being updated
        # This validation is PATCH-specific - with PUT we'd require ALL fields
        refined_text = body.get('refinedText')
        formatted_text = body.get('formattedText')
        metadata = body.get('metadata', {})
        
        # PATCH allows partial updates - at least one field must be provided
        # If this were PUT, we'd need to validate ALL resource fields are present
        if refined_text is None and formatted_text is None and not metadata:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': 'At least one of refinedText, formattedText, or metadata must be provided'
                })
            }
        
        # Initialize metadata table (use throughout function)
        try:
            metadata_table = dynamodb.Table(metadata_table_name)
            print(f"Initialized metadata table: {metadata_table_name}")
        except Exception as e:
            print(f"ERROR initializing metadata table: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Configuration Error',
                    'message': f'Failed to access metadata table: {str(e)}'
                })
            }
        
        # Get metadata to verify file exists
        try:
            metadata_response = metadata_table.query(
                KeyConditionExpression=Key('file_id').eq(file_id),
                Limit=1
            )
        except Exception as e:
            print(f"ERROR querying metadata table: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Database Error',
                    'message': f'Failed to query metadata: {str(e)}'
                })
            }
        
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
        
        # Check if file has been processed (both long-batch 'processed' and short-batch 'completed' statuses)
        processing_status = file_metadata.get('processing_status')
        if processing_status not in ['processed', 'completed']:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Bad Request',
                    'message': f'File {file_id} has not been processed yet. Status: {processing_status}. Expected: processed or completed'
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
        
        # Prepare update expression for PATCH operation
        # PATCH semantics: Only update fields that are explicitly provided
        # PUT semantics would require: Replace entire resource with provided data
        update_expression = []
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        # Track edit history (this is why PATCH is perfect - each edit is tracked)
        # With PUT, this edit tracking would be semantically confusing since PUT implies "replace all"
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
        
        # Prepare metadata updates if provided
        metadata_updates = {}
        if metadata:
            print(f"Processing metadata updates: {metadata}")
            print(f"Metadata table name: {metadata_table_name}")
            
            # Validate metadata fields
            allowed_metadata_fields = ['publication', 'year', 'title', 'author', 'description', 'tags']
            
            for field, value in metadata.items():
                if field in allowed_metadata_fields:
                    metadata_updates[field] = value
                    edit_entry['edited_fields'].append(f'metadata.{field}')
                    edit_entry[f'previous_metadata_{field}'] = file_metadata.get(field, '')
                else:
                    print(f"Ignoring invalid metadata field: {field}")
            
            print(f"Valid metadata updates: {metadata_updates}")
            
            # If metadata updates exist, we need to update the metadata table
            if metadata_updates:
                # Store original metadata if this is the first metadata edit
                for field in metadata_updates.keys():
                    original_field = f'original_metadata_{field}'
                    if original_field not in current_results:
                        update_expression.append(f'{original_field} = :{original_field.replace(".", "_")}')
                        expression_attribute_values[f':{original_field.replace(".", "_")}'] = file_metadata.get(field, '')
        
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
        
        # Perform the update on results table
        update_params = {
            'Key': {'file_id': file_id},
            'UpdateExpression': 'SET ' + ', '.join(update_expression),
            'ExpressionAttributeValues': expression_attribute_values
        }
        
        # Only add ExpressionAttributeNames if it's not empty
        if expression_attribute_names:
            update_params['ExpressionAttributeNames'] = expression_attribute_names
        
        results_table.update_item(**update_params)
        
        # Update metadata table if metadata changes were provided
        if metadata_updates:
            try:
                print(f"Attempting to update metadata table: {metadata_table_name}")
                print(f"File metadata keys: {list(file_metadata.keys())}")
                print(f"Upload timestamp: {file_metadata.get('upload_timestamp')}")
                
                metadata_update_expression = []
                metadata_expression_values = {}
                
                for field, value in metadata_updates.items():
                    metadata_update_expression.append(f'{field} = :{field}')
                    metadata_expression_values[f':{field}'] = value
                
                # Add last_updated timestamp
                metadata_update_expression.append('last_updated = :lu')
                metadata_expression_values[':lu'] = datetime.now(timezone.utc).isoformat()
                
                upload_timestamp = file_metadata.get('upload_timestamp')
                
                if not upload_timestamp:
                    print(f"ERROR: Missing upload_timestamp in file_metadata: {file_metadata}")
                    raise ValueError(f'Missing upload_timestamp for file {file_id}')
                
                print(f"About to update metadata table with keys: file_id={file_id}, upload_timestamp={upload_timestamp}")
                
                # metadata_table is already initialized at the top of the function
                
                # Update metadata table
                update_result = metadata_table.update_item(
                    Key={
                        'file_id': file_id,
                        'upload_timestamp': upload_timestamp
                    },
                    UpdateExpression='SET ' + ', '.join(metadata_update_expression),
                    ExpressionAttributeValues=metadata_expression_values,
                    ReturnValues='UPDATED_NEW'
                )
                
                print(f"Successfully updated metadata for file {file_id}: {update_result}")
                
            except Exception as metadata_error:
                print(f"ERROR updating metadata: {str(metadata_error)}")
                print(f"Error type: {type(metadata_error)}")
                # Return the error instead of silently failing
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Metadata Update Error',
                        'message': f'Failed to update metadata: {str(metadata_error)}'
                    })
                }
        
        # Get updated results
        updated_response = results_table.get_item(
            Key={'file_id': file_id}
        )
        
        updated_item = decimal_to_json(updated_response['Item'])
        
        # Get updated metadata if metadata was changed
        updated_metadata = {}
        if metadata_updates:
            try:
                # Use the already initialized metadata_table
                updated_metadata_response = metadata_table.query(
                    KeyConditionExpression=Key('file_id').eq(file_id),
                    Limit=1
                )
                if updated_metadata_response['Items']:
                    updated_file_metadata = decimal_to_json(updated_metadata_response['Items'][0])
                    updated_metadata = {
                        'publication': updated_file_metadata.get('publication', ''),
                        'year': updated_file_metadata.get('year', ''),
                        'title': updated_file_metadata.get('title', ''),
                        'author': updated_file_metadata.get('author', ''),
                        'description': updated_file_metadata.get('description', ''),
                        'tags': updated_file_metadata.get('tags', [])
                    }
                    print(f"Retrieved updated metadata: {updated_metadata}")
                else:
                    print(f"Warning: Could not retrieve updated metadata for file {file_id}")
                    # Return the metadata that was sent in the request as fallback
                    updated_metadata = metadata_updates
            except Exception as query_error:
                print(f"ERROR querying updated metadata: {str(query_error)}")
                # Return the metadata that was sent in the request as fallback
                updated_metadata = metadata_updates
        
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
        
        # Include updated metadata in response if it was changed
        if metadata_updates:
            response_data['metadata'] = updated_metadata
        
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