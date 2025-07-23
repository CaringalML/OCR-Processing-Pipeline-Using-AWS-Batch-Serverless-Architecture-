import json
import boto3
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

def decimal_to_json(obj):
    """Convert Decimal objects to JSON-serializable types"""
    if isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise to float
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
    Lambda function to read processed files from DynamoDB and generate CloudFront URLs
    Triggered by API Gateway GET requests to /processed endpoint
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    metadata_table_name = os.environ.get('METADATA_TABLE')
    results_table_name = os.environ.get('RESULTS_TABLE')
    cloudfront_domain = os.environ.get('CLOUDFRONT_DOMAIN')
    
    if not all([metadata_table_name, results_table_name, cloudfront_domain]):
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
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        status_filter = query_params.get('status', 'processed')
        limit = int(query_params.get('limit', '50'))
        file_id = query_params.get('fileId')
        
        metadata_table = dynamodb.Table(metadata_table_name)
        results_table = dynamodb.Table(results_table_name)
        
        # If specific file_id is requested
        if file_id:
            # Get file metadata
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
            
            file_metadata = decimal_to_json(metadata_response['Items'][0])
            
            # Get processing results
            results_response = results_table.get_item(
                Key={'file_id': file_id}
            )
            
            processing_result = decimal_to_json(results_response.get('Item', {}))
            
            # Generate CloudFront URL
            cloudfront_url = f"https://{cloudfront_domain}/{file_metadata['s3_key']}"
            
            # Build response data
            response_data = {
                'fileId': file_id,
                'fileName': file_metadata.get('file_name', ''),
                'uploadTimestamp': file_metadata.get('upload_timestamp', ''),
                'processingStatus': file_metadata.get('processing_status', ''),
                'fileSize': file_metadata.get('file_size', 0),
                'contentType': file_metadata.get('content_type', ''),
                'cloudFrontUrl': cloudfront_url
            }
            
            # Add processing results if available
            if processing_result:
                response_data['extractedText'] = processing_result.get('extracted_text', '')
                response_data['formattedText'] = processing_result.get('formatted_text', '')
                response_data['refinedText'] = processing_result.get('refined_text', '')
                response_data['processingDuration'] = processing_result.get('processing_duration', '')
                
                # Add Textract analysis with text refinement details
                summary_analysis = processing_result.get('summary_analysis', {})
                text_refinement_details = processing_result.get('text_refinement_details', {})
                
                response_data['textract_analysis'] = {
                    'total_words': summary_analysis.get('word_count', 0),
                    'total_paragraphs': summary_analysis.get('paragraph_count', 0),
                    'total_sentences': summary_analysis.get('sentence_count', 0),
                    'total_improvements': text_refinement_details.get('total_improvements', 0),
                    'spell_corrections': text_refinement_details.get('spell_corrections', 0),
                    'grammar_refinements': text_refinement_details.get('grammar_refinements', 0),
                    'methods_used': text_refinement_details.get('methods_used', []),
                    'entities_found': len(text_refinement_details.get('entities_found', [])),
                    'processing_notes': text_refinement_details.get('processing_notes', ''),
                    'confidence_score': summary_analysis.get('confidence', '0'),
                    'character_count': summary_analysis.get('character_count', 0),
                    'line_count': summary_analysis.get('line_count', 0)
                }
                
                # Add Comprehend analysis if available
                comprehend_analysis = processing_result.get('comprehend_analysis', {})
                if comprehend_analysis:
                    response_data['comprehendAnalysis'] = comprehend_analysis
            
        else:
            # Query files by status
            if status_filter == 'all':
                # Scan all files (less efficient but necessary for 'all')
                response = metadata_table.scan(
                    Limit=limit
                )
            else:
                # Query by status using GSI
                response = metadata_table.query(
                    IndexName='StatusIndex',
                    KeyConditionExpression=Key('processing_status').eq(status_filter),
                    Limit=limit,
                    ScanIndexForward=False  # Most recent first
                )
            
            items = decimal_to_json(response.get('Items', []))
            
            # Enrich items with CloudFront URLs and results
            processed_items = []
            for item in items:
                # Get processing results if available
                if item.get('processing_status') == 'processed':
                    results_response = results_table.get_item(
                        Key={'file_id': item['file_id']}
                    )
                    processing_result = decimal_to_json(results_response.get('Item', {}))
                else:
                    processing_result = {}
                
                # Generate CloudFront URL
                cloudfront_url = f"https://{cloudfront_domain}/{item['s3_key']}"
                
                # Build item data
                item_data = {
                    'fileId': item['file_id'],
                    'fileName': item.get('file_name', ''),
                    'uploadTimestamp': item.get('upload_timestamp', ''),
                    'processingStatus': item.get('processing_status', ''),
                    'fileSize': item.get('file_size', 0),
                    'contentType': item.get('content_type', ''),
                    'cloudFrontUrl': cloudfront_url
                }
                
                # Add processing results if available
                if processing_result and item.get('processing_status') == 'processed':
                    item_data['extractedText'] = processing_result.get('extracted_text', '')
                    item_data['formattedText'] = processing_result.get('formatted_text', '')
                    item_data['refinedText'] = processing_result.get('refined_text', '')
                    
                    # Add Textract analysis with text refinement details
                    summary_analysis = processing_result.get('summary_analysis', {})
                    text_refinement_details = processing_result.get('text_refinement_details', {})
                    
                    item_data['textract_analysis'] = {
                        'total_words': summary_analysis.get('word_count', 0),
                        'total_paragraphs': summary_analysis.get('paragraph_count', 0),
                        'total_sentences': summary_analysis.get('sentence_count', 0),
                        'total_improvements': text_refinement_details.get('total_improvements', 0),
                        'spell_corrections': text_refinement_details.get('spell_corrections', 0),
                        'grammar_refinements': text_refinement_details.get('grammar_refinements', 0),
                        'methods_used': text_refinement_details.get('methods_used', []),
                        'entities_found': len(text_refinement_details.get('entities_found', [])),
                        'processing_notes': text_refinement_details.get('processing_notes', ''),
                        'confidence_score': summary_analysis.get('confidence', '0'),
                        'character_count': summary_analysis.get('character_count', 0),
                        'line_count': summary_analysis.get('line_count', 0)
                    }
                    
                    # Add Comprehend analysis if available
                    comprehend_analysis = processing_result.get('comprehend_analysis', {})
                    if comprehend_analysis:
                        item_data['comprehendAnalysis'] = comprehend_analysis
                
                processed_items.append(item_data)
            
            response_data = {
                'files': processed_items,
                'count': len(processed_items),
                'hasMore': response.get('LastEvaluatedKey') is not None
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data)
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