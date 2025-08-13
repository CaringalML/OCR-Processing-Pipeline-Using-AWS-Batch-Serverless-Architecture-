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

def format_duration(duration_seconds):
    """Format duration in seconds to human-readable format"""
    if not duration_seconds:
        return "0s"
    
    # Handle case where duration is already a formatted string (e.g., "139.58 seconds")
    if isinstance(duration_seconds, str):
        # If it's already formatted, return as-is
        if 'seconds' in duration_seconds or 'minutes' in duration_seconds or 'hours' in duration_seconds:
            # Extract numeric part and reformat consistently
            import re
            match = re.search(r'(\d+\.?\d*)', duration_seconds)
            if match:
                numeric_value = float(match.group(1))
                if 'seconds' in duration_seconds:
                    return f"{numeric_value:.1f}s"
                elif 'minutes' in duration_seconds:
                    return f"{numeric_value:.1f}m"
                elif 'hours' in duration_seconds:
                    return f"{numeric_value:.1f}h"
            # Fallback: return original string if parsing fails
            return duration_seconds
        else:
            # Try to convert string to float
            try:
                duration = float(duration_seconds)
            except (ValueError, TypeError):
                return str(duration_seconds)
    else:
        duration = float(duration_seconds)
    
    if duration < 60:
        # Less than 1 minute - show in seconds with 1 decimal place
        return f"{duration:.1f}s"
    elif duration < 3600:
        # Less than 1 hour - show in minutes with 1 decimal place
        minutes = duration / 60
        return f"{minutes:.1f}m"
    else:
        # 1 hour or more - show in hours with 1 decimal place
        hours = duration / 3600
        return f"{hours:.1f}h"

def lambda_handler(event, context):
    """
    Lambda function to read processed files from DynamoDB and generate CloudFront URLs
    Triggered by API Gateway GET requests to /processed endpoint
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration - only results table needed now
    results_table_name = os.environ.get('RESULTS_TABLE', 'ocr-processor-batch-processing-results')
    cloudfront_domain = os.environ.get('CLOUDFRONT_DOMAIN')
    
    if not all([results_table_name, cloudfront_domain]):
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
        
        # Determine which endpoint was called to filter by batch type
        resource_path = event.get('requestContext', {}).get('resourcePath', '')
        batch_type_filter = None
        if '/short-batch/' in resource_path:
            batch_type_filter = 'short-batch'
        elif '/long-batch/' in resource_path:
            batch_type_filter = 'long-batch'
        # If '/processed' (root endpoint), show all batch types (batch_type_filter = None)
        
        results_table = dynamodb.Table(results_table_name)
        
        # If specific file_id is requested
        if file_id:
            # Get file data from results table
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
            
            processing_result = decimal_to_json(results_response['Item'])
            
            # Generate CloudFront URL from results table data
            s3_key = processing_result.get('key', '')
            cloudfront_url = f"https://{cloudfront_domain}/{s3_key}" if s3_key else ''
            
            # Build response data from results table
            response_data = {
                'fileId': file_id,
                'fileName': processing_result.get('file_name', ''),
                'uploadTimestamp': processing_result.get('upload_timestamp', ''),
                'processingStatus': processing_result.get('processing_status', ''),
                'processingType': processing_result.get('processing_type', ''),
                'fileSize': processing_result.get('file_size', 0),
                'contentType': processing_result.get('content_type', ''),
                'cloudFrontUrl': cloudfront_url,
                'bucket': processing_result.get('bucket', ''),
                'key': processing_result.get('key', ''),
                'processingModel': processing_result.get('processing_model', '')
            }
            
            # Add OCR results from unified table structure
            if processing_result:
                response_data['ocrResults'] = {
                    'extractedText': processing_result.get('extracted_text', ''),
                    'formattedText': processing_result.get('formatted_text', ''),
                    'refinedText': processing_result.get('refined_text', ''),
                    'processingModel': processing_result.get('processing_model', ''),
                    'processingType': processing_result.get('processing_type', ''),
                    'processingCost': processing_result.get('processing_cost', 0),
                    'processedAt': processing_result.get('processed_at', ''),
                    'processingDuration': processing_result.get('processing_duration', ''),
                    'tokenUsage': processing_result.get('token_usage', {}),
                    'languageDetection': processing_result.get('language_detection', {}),
                    'qualityAssessment': processing_result.get('quality_assessment', {}),
                    'entityAnalysis': processing_result.get('entity_analysis', {}),
                    'userEdited': processing_result.get('user_edited', False),
                    'editHistory': processing_result.get('edit_history', [])
                }
            else:
                # No OCR results available
                response_data['ocrResults'] = None
            
            # Add analysis data based on processing type
            if processing_result and processing_result.get('processing_type') == 'short-batch':
                # For Claude processing from shared table, add text statistics
                formatted_text = processing_result.get('formatted_text', '')
                refined_text = processing_result.get('refined_text', '')
                
                if formatted_text or refined_text:
                    # Use refined text for analysis (better for word/sentence counting)
                    analysis_text = refined_text if refined_text else formatted_text
                    words = analysis_text.split()
                    paragraphs = analysis_text.split('\n\n')
                    sentences = analysis_text.split('. ')
                    
                    response_data['textAnalysis'] = {
                        'total_words': len(words),
                        'total_paragraphs': len([p for p in paragraphs if p.strip()]),
                        'total_sentences': len([s for s in sentences if s.strip()]),
                        'raw_character_count': len(formatted_text),
                        'refined_character_count': len(refined_text),
                        'processing_model': processing_result.get('processing_model', 'claude-sonnet-4-20250514'),
                        'processing_notes': 'Dual-pass Claude processing: OCR extraction + grammar refinement',
                        'improvement_ratio': round(len(refined_text) / len(formatted_text), 2) if formatted_text else 1.0
                    }
                    
                    # Add entity analysis if available in results
                    entity_analysis = processing_result.get('entity_analysis', {})
                    if entity_analysis and entity_analysis.get('entity_summary'):
                        response_data['entityAnalysis'] = {
                            'entity_summary': entity_analysis.get('entity_summary', {}),
                            'total_entities': entity_analysis.get('total_entities', 0),
                            'entity_types': list(entity_analysis.get('entity_summary', {}).keys()),
                            'detection_source': 'Claude AI OCR Analysis'
                        }
            # Legacy code removed - now using unified table structure
            
            if processing_result:
                # For Textract processing, use existing analysis
                enhanced_textract_analysis = processing_result.get('textract_analysis', {})                
                if enhanced_textract_analysis:
                    response_data['textAnalysis'] = enhanced_textract_analysis
                else:
                    # Fallback to legacy construction for backward compatibility
                    summary_analysis = processing_result.get('summary_analysis', {})
                    text_refinement_details = processing_result.get('text_refinement_details', {})
                    
                    response_data['textAnalysis'] = {
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
                
                # Add enhanced Comprehend entity analysis for long-batch
                comprehend_analysis = processing_result.get('comprehend_analysis', {})
                if comprehend_analysis:
                    response_data['comprehendAnalysis'] = comprehend_analysis
                    
                
                # Add dedicated Invoice Analysis section
                invoice_analysis = processing_result.get('invoice_analysis', {})
                if invoice_analysis:
                    response_data['invoiceAnalysis'] = invoice_analysis
            
        else:
            # Query files from results table
            if status_filter == 'all':
                # Scan all files from results table
                response = results_table.scan(
                    Limit=limit
                )
            elif status_filter == 'processed':
                # Handle batch type filtering based on endpoint
                if batch_type_filter == 'short-batch':
                    # Only get short-batch files (status = 'completed')
                    response = metadata_table.query(
                        IndexName='StatusIndex',
                        KeyConditionExpression=Key('processing_status').eq('completed'),
                        Limit=limit,
                        ScanIndexForward=False  # Most recent first
                    )
                elif batch_type_filter == 'long-batch':
                    # Only get long-batch files (status = 'processed')
                    response = metadata_table.query(
                        IndexName='StatusIndex',
                        KeyConditionExpression=Key('processing_status').eq('processed'),
                        Limit=limit,
                        ScanIndexForward=False  # Most recent first
                    )
                else:
                    # For processed files, we need to get both 'processed' (long-batch) and 'completed' (short-batch)
                    # First get 'processed' files
                    response1 = metadata_table.query(
                        IndexName='StatusIndex',
                        KeyConditionExpression=Key('processing_status').eq('processed'),
                        Limit=limit//2,  # Split the limit
                        ScanIndexForward=False  # Most recent first
                    )
                    # Then get 'completed' files
                    response2 = metadata_table.query(
                        IndexName='StatusIndex', 
                        KeyConditionExpression=Key('processing_status').eq('completed'),
                        Limit=limit//2,  # Split the limit
                        ScanIndexForward=False  # Most recent first
                    )
                    # Combine results
                    all_items = response1.get('Items', []) + response2.get('Items', [])
                    # Sort by upload_timestamp descending (most recent first)
                    all_items.sort(key=lambda x: x.get('upload_timestamp', ''), reverse=True)
                    # Limit to requested number
                    response = {
                        'Items': all_items[:limit],
                        'LastEvaluatedKey': None  # Simplified pagination
                    }
            else:
                # Query by specific status using GSI
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
                # Get processing results from shared table for both short and long batch
                if item.get('processing_status') in ['processed', 'completed']:
                    # Query shared results table for both processing types
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
                    'cloudFrontUrl': cloudfront_url,
                    'metadata': {
                        'publication': item.get('publication', ''),
                        'year': item.get('year', ''),
                        'title': item.get('title', ''),
                        'author': item.get('author', ''),
                        'description': item.get('description', ''),
                        'tags': item.get('tags', [])
                    }
                }
                
                # Add processing results if available
                if item.get('processing_status') in ['processed', 'completed']:
                    # Determine processing type and add appropriate results
                    processing_route = item.get('processing_route', 'long-batch')
                    
                    if processing_result:
                        # Results found in shared table
                        processing_type = processing_result.get('processing_type', processing_route)
                        
                        if processing_type == 'short-batch':
                            # Short-batch results from shared table
                            item_data['ocrResults'] = {
                                'formattedText': processing_result.get('formatted_text', ''),
                                'refinedText': processing_result.get('refined_text', ''),
                                'extractedText': processing_result.get('extracted_text', ''),
                                'processingModel': processing_result.get('processing_model', 'claude-sonnet-4-20250514'),
                                'processingType': 'short-batch',
                                'processingCost': processing_result.get('processing_cost', 0),
                                'processedAt': processing_result.get('processed_at', ''),
                                'processingDuration': format_duration(processing_result.get('processing_duration', 0)),
                                'tokenUsage': processing_result.get('token_usage', {}),
                                'languageDetection': processing_result.get('language_detection', {})
                            }
                        else:
                            # Long-batch results from shared table
                            item_data['ocrResults'] = {
                                'extractedText': processing_result.get('extracted_text', ''),
                                'formattedText': processing_result.get('formatted_text', ''),
                                'refinedText': processing_result.get('refined_text', ''),
                                'processingModel': processing_result.get('processing_model', 'aws-textract'),
                                'processingType': 'long-batch',
                                'processingDuration': format_duration(processing_result.get('processing_duration', 0))
                            }
                    # Legacy short-batch handling removed - now using unified results table
                    elif processing_result:
                        # Long-batch (Textract) results - stored in results table
                        item_data['ocrResults'] = {
                            'extractedText': processing_result.get('extracted_text', ''),     # Raw Textract
                            'formattedText': processing_result.get('formatted_text', ''),    # Processed
                            'refinedText': processing_result.get('refined_text', ''),        # Final refined
                            'processingModel': 'aws-textract',
                            'processingType': 'long-batch',
                            'processingDuration': format_duration(processing_result.get('processing_duration', 0))
                        }
                        
                        # For Textract processing, use existing analysis
                        enhanced_textract_analysis = processing_result.get('textract_analysis', {})                
                        if enhanced_textract_analysis:
                            item_data['textAnalysis'] = enhanced_textract_analysis
                        else:
                            # Fallback to legacy construction for backward compatibility
                            summary_analysis = processing_result.get('summary_analysis', {})
                            text_refinement_details = processing_result.get('text_refinement_details', {})
                            
                            item_data['textAnalysis'] = {
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
                        
                        # Add enhanced Comprehend entity analysis for long-batch
                        comprehend_analysis = processing_result.get('comprehend_analysis', {})
                        if comprehend_analysis:
                            item_data['comprehendAnalysis'] = comprehend_analysis
                            
                        # Add dedicated Invoice Analysis section
                        invoice_analysis = processing_result.get('invoice_analysis', {})
                        if invoice_analysis:
                            item_data['invoiceAnalysis'] = invoice_analysis
                    else:
                        # No OCR results available
                        item_data['ocrResults'] = None
                
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