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
                'cloudFrontUrl': cloudfront_url,
                'metadata': {
                    'publication': file_metadata.get('publication', ''),
                    'year': file_metadata.get('year', ''),
                    'title': file_metadata.get('title', ''),
                    'author': file_metadata.get('author', ''),
                    'description': file_metadata.get('description', ''),
                    'tags': file_metadata.get('tags', [])
                }
            }
            
            # Determine processing type and add appropriate results
            processing_route = file_metadata.get('processing_route', 'long-batch')
            
            if processing_route == 'short-batch' and (file_metadata.get('raw_ocr_text') or file_metadata.get('refined_ocr_text')):
                # Short-batch (Claude API) results - stored in metadata table
                raw_text = file_metadata.get('raw_ocr_text', '')
                refined_text = file_metadata.get('refined_ocr_text', '')
                
                response_data['ocrResults'] = {
                    'formattedText': raw_text,      # Exact replica of scanned document
                    'refinedText': refined_text,    # Grammar and punctuation improved by Claude
                    'processingModel': file_metadata.get('model', 'claude-sonnet-4-20250514'),
                    'processingType': 'short-batch',
                    'processingCost': file_metadata.get('processing_cost', 0),
                    'processedAt': file_metadata.get('processed_at', ''),
                    'rawTextLength': len(raw_text),
                    'refinedTextLength': len(refined_text),
                    'tokenUsage': {
                        'ocrTokens': file_metadata.get('ocr_tokens', {}),
                        'refinementTokens': file_metadata.get('refinement_tokens', {})
                    },
                    'detectedLanguage': file_metadata.get('detected_language', 'unknown'),
                    'languageConfidence': file_metadata.get('language_confidence', 0.0)
                }
            elif processing_result:
                # Long-batch (Textract) results - stored in results table
                response_data['ocrResults'] = {
                    'extractedText': processing_result.get('extracted_text', ''),     # Raw Textract
                    'formattedText': processing_result.get('formatted_text', ''),    # Processed
                    'refinedText': processing_result.get('refined_text', ''),        # Final refined
                    'processingModel': 'aws-textract',
                    'processingType': 'long-batch',
                    'processingDuration': processing_result.get('processing_duration', '')
                }
            else:
                # No OCR results available
                response_data['ocrResults'] = None
            
            # Add analysis data based on processing type
            if processing_route == 'short-batch':
                # For Claude processing, add text statistics for both versions
                raw_text = file_metadata.get('raw_ocr_text', '')
                refined_text = file_metadata.get('refined_ocr_text', '')
                
                if raw_text or refined_text:
                    # Use refined text for analysis (better for word/sentence counting)
                    analysis_text = refined_text if refined_text else raw_text
                    words = analysis_text.split()
                    paragraphs = analysis_text.split('\n\n')
                    sentences = analysis_text.split('. ')
                    
                    response_data['textAnalysis'] = {
                        'total_words': len(words),
                        'total_paragraphs': len([p for p in paragraphs if p.strip()]),
                        'total_sentences': len([s for s in sentences if s.strip()]),
                        'raw_character_count': len(raw_text),
                        'refined_character_count': len(refined_text),
                        'processing_model': file_metadata.get('model', 'claude-sonnet-4-20250514'),
                        'processing_notes': 'Dual-pass Claude processing: OCR extraction + grammar refinement',
                        'improvement_ratio': round(len(refined_text) / len(raw_text), 2) if raw_text else 1.0
                    }
                    
                    # Add entity analysis for short-batch - from Claude detection
                    entity_summary = file_metadata.get('entity_summary', {})
                    if entity_summary:
                        response_data['entityAnalysis'] = {
                            'entity_summary': entity_summary,
                            'total_entities': file_metadata.get('total_entities', 0),
                            'entity_types': list(entity_summary.keys()) if entity_summary else [],
                            'detection_method': 'claude_ai'
                        }
            elif processing_result:
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
                if item.get('processing_status') == 'processed':
                    # Debug: check what fields are available
                    has_extracted_text = bool(item.get('extractedText'))
                    has_textract_analysis = bool(item.get('textract_analysis'))
                    print(f"DEBUG: File {item['file_id']} - has_extracted_text: {has_extracted_text}, has_textract_analysis: {has_textract_analysis}")
                    
                    # Check if data exists in metadata table first (short-batch files)
                    if item.get('extractedText') or item.get('textract_analysis'):
                        # Data is in metadata table (short-batch)
                        item_data['extractedText'] = item.get('extractedText', '')
                        item_data['formattedText'] = item.get('formattedText', '')
                        item_data['refinedText'] = item.get('refinedText', '')
                        item_data['processingDuration'] = item.get('processingDuration', '')
                        
                        # Use enhanced textract_analysis directly from metadata table
                        textract_analysis = item.get('textract_analysis', {})
                        if textract_analysis:
                            item_data['textract_analysis'] = decimal_to_json(textract_analysis)
                        else:
                            item_data['textract_analysis'] = {
                                'total_words': 0,
                                'total_paragraphs': 0,
                                'total_sentences': 0,
                                'total_improvements': 0,
                                'spell_corrections': 0,
                                'grammar_refinements': 0,
                                'methods_used': [],
                                'entities_found': 0,
                                'processing_notes': '',
                                'confidence_score': 0,
                                'character_count': 0,
                                'line_count': 0
                            }
                        
                        # Add enhanced entity analysis if available
                        entity_analysis = item.get('entity_analysis', {})
                        if entity_analysis:
                            item_data['entityAnalysis'] = decimal_to_json(entity_analysis)
                            
                        # Add comprehensive comprehend analysis if available  
                        comprehend_analysis = item.get('comprehend_analysis', {})
                        if comprehend_analysis:
                            item_data['comprehendAnalysis'] = decimal_to_json(comprehend_analysis)
                        
                        # Use comprehend analysis from metadata table
                        comprehend_analysis = item.get('comprehendAnalysis', {})
                        if comprehend_analysis:
                            item_data['comprehendAnalysis'] = decimal_to_json(comprehend_analysis)
                        
                        # Add dedicated Invoice Analysis section from metadata table
                        invoice_analysis = item.get('invoice_analysis', {})
                        if invoice_analysis:
                            item_data['invoiceAnalysis'] = decimal_to_json(invoice_analysis)
                    
                    elif processing_result:
                        # Data is in results table (long-batch)
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