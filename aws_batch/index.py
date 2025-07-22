#!/usr/bin/env python3
"""
OCR Processing Pipeline - Batch Processing Only
Converts documents to text using AWS Textract and analyzes with AWS Comprehend
"""

import json
import os
import logging
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
textract_client = boto3.client('textract')
comprehend_client = boto3.client('comprehend')

# Production logging (reduced verbosity, structured format)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
IS_DEV = os.getenv('PYTHON_ENV') == 'development'

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def log(level: str, message: str, data: Dict[str, Any] = None) -> None:
    """Structured logging function"""
    if data is None:
        data = {}
    
    levels = {'ERROR': 40, 'WARN': 30, 'INFO': 20, 'DEBUG': 10}
    current_level = levels.get(LOG_LEVEL, 20)
    
    if levels.get(level.upper(), 20) >= current_level:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level.upper(),
            'message': message,
            'batchJobId': os.getenv('AWS_BATCH_JOB_ID'),
            'fileId': os.getenv('FILE_ID'),
            **data
        }
        print(json.dumps(log_entry))


# Startup logging (minimal in production)
if IS_DEV or LOG_LEVEL == 'DEBUG':
    log('DEBUG', 'Container startup debug info', {
        'pythonVersion': sys.version,
        'environment': {
            'AWS_BATCH_JOB_ID': os.getenv('AWS_BATCH_JOB_ID'),
            'S3_BUCKET': os.getenv('S3_BUCKET'),
            'S3_KEY': os.getenv('S3_KEY'),
            'FILE_ID': os.getenv('FILE_ID'),
            'DYNAMODB_TABLE': os.getenv('DYNAMODB_TABLE'),
            'AWS_REGION': os.getenv('AWS_REGION')
        }
    })
else:
    log('INFO', 'OCR Processor starting - batch mode only', {
        'hasRequiredEnvVars': bool(
            os.getenv('S3_BUCKET') and 
            os.getenv('S3_KEY') and 
            os.getenv('FILE_ID') and 
            os.getenv('DYNAMODB_TABLE')
        )
    })


def health_check() -> Dict[str, Any]:
    """Simple health check for container health monitoring"""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'uptime': time.time(),
        'mode': 'batch-only',
        'version': '2.0.0'
    }


async def process_s3_file() -> Dict[str, Any]:
    """Main S3 file processing function"""
    bucket_name = os.getenv('S3_BUCKET')
    object_key = os.getenv('S3_KEY')
    file_id = os.getenv('FILE_ID')
    dynamo_table = os.getenv('DYNAMODB_TABLE')
    
    log('INFO', 'Starting file processing', {
        'bucket': bucket_name,
        'key': object_key,
        'fileId': file_id,
        'table': dynamo_table
    })
    
    # Validate required environment variables
    missing_vars = []
    if not bucket_name:
        missing_vars.append('S3_BUCKET')
    if not object_key:
        missing_vars.append('S3_KEY')
    if not file_id:
        missing_vars.append('FILE_ID')
    if not dynamo_table:
        missing_vars.append('DYNAMODB_TABLE')
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        log('ERROR', error_msg)
        raise ValueError(error_msg)
    
    try:
        log('INFO', 'Updating status to processing')
        
        # Update processing status to 'processing'
        await update_file_status(dynamo_table, file_id, 'processing', {
            'processing_started': datetime.utcnow().isoformat() + 'Z',
            'batch_job_id': os.getenv('AWS_BATCH_JOB_ID', 'unknown')
        })
        
        log('INFO', 'Retrieving file metadata from S3')
        
        # Get file metadata from S3
        try:
            s3_object_metadata = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        except ClientError as e:
            log('ERROR', f'Failed to get S3 object metadata: {e}')
            raise
        
        file_size = s3_object_metadata.get('ContentLength', 0)
        content_type = s3_object_metadata.get('ContentType', 'unknown')
        
        log('INFO', 'File metadata retrieved', {
            'size': file_size,
            'contentType': content_type,
            'lastModified': s3_object_metadata.get('LastModified', '').isoformat() if s3_object_metadata.get('LastModified') else None
        })
        
        log('INFO', 'Starting Textract OCR processing')
        
        # Process file with AWS Textract
        start_time = time.time()
        extracted_data = await process_file_with_textract(bucket_name, object_key)
        textract_time = time.time() - start_time
        
        log('INFO', 'Textract processing completed', {
            'processingTimeSeconds': textract_time,
            'wordCount': extracted_data['wordCount'],
            'lineCount': extracted_data['lineCount'],
            'confidence': extracted_data['confidence']
        })
        
        # Format the extracted text
        formatted_text_data = {}
        text_for_comprehend = extracted_data['text']
        
        if extracted_data['text'] and extracted_data['text'].strip():
            log('INFO', 'Formatting extracted text')
            formatted_text_data = format_extracted_text(extracted_data['text'])
            
            # Use the formatted text for Comprehend analysis
            text_for_comprehend = formatted_text_data.get('formatted', extracted_data['text'])
            
            log('INFO', 'Text formatting completed', {
                'originalChars': formatted_text_data['stats']['originalChars'],
                'cleanedChars': formatted_text_data['stats']['cleanedChars'],
                'paragraphs': formatted_text_data['stats']['paragraphCount'],
                'sentences': formatted_text_data['stats']['sentenceCount'],
                'reduction': f"{formatted_text_data['stats']['reductionPercent']}%"
            })
        
        # Process formatted text with AWS Comprehend
        comprehend_data = {}
        if text_for_comprehend and text_for_comprehend.strip():
            log('INFO', 'Starting Comprehend analysis on formatted text')
            comprehend_start_time = time.time()
            comprehend_data = await process_text_with_comprehend(text_for_comprehend)
            comprehend_time = time.time() - comprehend_start_time
            
            log('INFO', 'Comprehend analysis completed', {
                'processingTimeSeconds': comprehend_time,
                'language': comprehend_data.get('language'),
                'sentiment': comprehend_data.get('sentiment', {}).get('Sentiment'),
                'entitiesCount': len(comprehend_data.get('entities', [])),
                'keyPhrasesCount': len(comprehend_data.get('keyPhrases', []))
            })
        else:
            log('INFO', 'Skipping Comprehend analysis - no text extracted')
        
        total_processing_time = time.time() - start_time
        
        # Generate processing results
        processing_results = {
            'processed_at': datetime.utcnow().isoformat() + 'Z',
            'file_size': file_size,
            'content_type': content_type,
            'processing_duration': f'{total_processing_time:.2f} seconds',
            'extracted_text': extracted_data['text'],
            'formatted_text': formatted_text_data.get('formatted', extracted_data['text']),
            'text_formatting': {
                'paragraphs': formatted_text_data.get('paragraphs', []),
                'stats': formatted_text_data.get('stats', {}),
                'hasFormatting': bool(formatted_text_data.get('formatted'))
            },
            'analysis': {
                'word_count': extracted_data['wordCount'],
                'character_count': len(extracted_data['text']),
                'line_count': extracted_data['lineCount'],
                'confidence': extracted_data['confidence']
            },
            'comprehend_analysis': comprehend_data,
            'metadata': {
                'processor_version': '2.2.0',
                'batch_job_id': os.getenv('AWS_BATCH_JOB_ID', 'unknown'),
                'textract_job_id': extracted_data['jobId'],
                'textract_duration': f'{textract_time:.2f} seconds',
                'comprehend_duration': f"{comprehend_data.get('processingTime', 0):.2f} seconds" if comprehend_data.get('processingTime') else 'N/A'
            }
        }
        
        log('INFO', 'Storing processing results')
        
        # Store processing results in DynamoDB
        await store_processing_results(file_id, processing_results)
        
        log('INFO', 'Updating status to processed')
        
        # Update file status to 'processed'
        await update_file_status(dynamo_table, file_id, 'processed', {
            'processing_completed': datetime.utcnow().isoformat() + 'Z',
            'processing_duration': processing_results['processing_duration']
        })
        
        log('INFO', 'File processing completed successfully', {
            'processingTimeSeconds': total_processing_time,
            'extractedWords': extracted_data['wordCount'],
            'extractedLines': extracted_data['lineCount'],
            'confidence': extracted_data['confidence'],
            'comprehendLanguage': comprehend_data.get('language'),
            'comprehendSentiment': comprehend_data.get('sentiment', {}).get('Sentiment')
        })
        
        return processing_results
        
    except Exception as error:
        log('ERROR', 'File processing failed', {
            'error': str(error),
            'type': type(error).__name__
        })
        
        # Update status to 'failed'
        try:
            await update_file_status(dynamo_table, file_id, 'failed', {
                'error_message': str(error),
                'failed_at': datetime.utcnow().isoformat() + 'Z'
            })
            log('INFO', 'File status updated to failed')
        except Exception as update_error:
            log('ERROR', 'Failed to update error status', {'error': str(update_error)})
        
        raise


async def process_file_with_textract(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """Process file with AWS Textract"""
    try:
        log('INFO', 'Starting Textract document analysis', {
            's3Uri': f's3://{bucket_name}/{object_key}'
        })
        
        # Start asynchronous document analysis
        start_params = {
            'DocumentLocation': {
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': object_key
                }
            },
            'FeatureTypes': ['TABLES', 'FORMS']  # Extract tables and forms in addition to text
        }
        
        response = textract_client.start_document_analysis(**start_params)
        job_id = response['JobId']
        log('INFO', 'Textract job submitted', {'textractJobId': job_id})
        
        # Wait for job completion
        job_status = 'IN_PROGRESS'
        attempts = 0
        max_attempts = 60  # 5 minutes timeout (5 seconds * 60)
        
        while job_status == 'IN_PROGRESS' and attempts < max_attempts:
            time.sleep(5)  # Wait 5 seconds
            
            status_response = textract_client.get_document_analysis(JobId=job_id)
            job_status = status_response['JobStatus']
            attempts += 1
            
            if attempts % 6 == 0:  # Log every 30 seconds
                log('INFO', 'Waiting for Textract completion', {
                    'status': job_status,
                    'attempt': attempts,
                    'maxAttempts': max_attempts
                })
            
            if job_status == 'FAILED':
                status_reason = status_response.get('StatusMessage', 'Unknown error')
                raise Exception(f'Textract job failed: {status_reason}')
        
        if job_status != 'SUCCEEDED':
            raise Exception(f'Textract job failed with status: {job_status} after {attempts} attempts')
        
        log('INFO', 'Textract job completed, retrieving results')
        
        # Get all results (handle pagination)
        next_token = None
        all_blocks = []
        page_count = 0
        
        while True:
            params = {'JobId': job_id}
            if next_token:
                params['NextToken'] = next_token
            
            response = textract_client.get_document_analysis(**params)
            all_blocks.extend(response.get('Blocks', []))
            next_token = response.get('NextToken')
            page_count += 1
            
            if not next_token:
                break
        
        log('DEBUG', 'Textract results retrieved', {
            'totalBlocks': len(all_blocks),
            'pages': page_count
        })
        
        # Extract text from blocks
        extracted_text = []
        total_confidence = 0
        confidence_count = 0
        
        for block in all_blocks:
            if block.get('BlockType') == 'LINE' and block.get('Text'):
                extracted_text.append(block['Text'])
                if block.get('Confidence'):
                    total_confidence += block['Confidence']
                    confidence_count += 1
        
        full_text = '\n'.join(extracted_text)
        words = [word for word in full_text.split() if word.strip()]
        
        result = {
            'text': full_text,
            'wordCount': len(words),
            'lineCount': len(extracted_text),
            'confidence': f'{total_confidence / confidence_count:.2f}' if confidence_count > 0 else '0',
            'jobId': job_id
        }
        
        return result
        
    except Exception as error:
        log('ERROR', 'Textract processing error', {'error': str(error)})
        
        # Fallback for non-supported file types or errors
        if 'UnsupportedDocumentException' in str(error) or 'InvalidParameterException' in str(error):
            log('WARN', 'File type not supported by Textract', {'errorType': type(error).__name__})
            return {
                'text': 'File type not supported for text extraction',
                'wordCount': 0,
                'lineCount': 0,
                'confidence': '0',
                'jobId': 'N/A'
            }
        
        raise


def get_entity_category(entity_type: str) -> str:
    """Categorize AWS Comprehend entity types for better organization"""
    categories = {
        'PERSON': 'People',
        'LOCATION': 'Places',
        'ORGANIZATION': 'Organizations',
        'COMMERCIAL_ITEM': 'Products & Services',
        'EVENT': 'Events',
        'DATE': 'Dates & Times',
        'QUANTITY': 'Numbers & Quantities',
        'TITLE': 'Titles & Positions',
        'OTHER': 'Other'
    }
    
    return categories.get(entity_type, 'Other')


def format_extracted_text(raw_text: str) -> Dict[str, Any]:
    """Format extracted text for better readability"""
    try:
        if not raw_text or not isinstance(raw_text, str):
            return {
                'formatted': '',
                'paragraphs': [],
                'stats': {'paragraphCount': 0, 'sentenceCount': 0, 'cleanedChars': 0}
            }
        
        def fix_urls_and_emails(text: str) -> str:
            """Fix URLs and emails that got broken during OCR"""
            # Fix email patterns
            text = re.sub(r'(\w+)\s*@\s*([^\s\n\r\t]+)', lambda m: f"{m.group(1)}@{m.group(2).replace(' ', '')}", text)
            
            # Fix www. patterns
            text = re.sub(r'www\.\s+([^\s\n\r\t]+?)(\s+(?:I|,|\||$))', 
                         lambda m: f"www.{m.group(1).replace(' ', '')}{m.group(2)}", text, flags=re.IGNORECASE)
            
            # Fix domain patterns with spaces around dots
            text = re.sub(r'(\w+)\.\s+(\w+)\.\s+(\w+)(?=\s|$|[^\w])', r'\1.\2.\3', text)
            text = re.sub(r'(\w+)\.\s+(\w+)(?=\s|$|[^\w])', r'\1.\2', text)
            
            # Fix http/https patterns
            text = re.sub(r'https?\s*:\s*/\s*/\s*', lambda m: m.group(0).replace(' ', ''), text, flags=re.IGNORECASE)
            
            return text
        
        # Apply URL/email fixes first
        preprocessed = fix_urls_and_emails(raw_text)
        
        # Continue with other preprocessing
        preprocessed = re.sub(r'\.\s+([A-Z])', r'. \1', preprocessed)  # Fix period spacing
        preprocessed = re.sub(r'([a-z])\s+([A-Z])', r'\1 \2', preprocessed)  # Fix word spacing
        preprocessed = re.sub(r'(\w)\s+([,.])', r'\1\2', preprocessed)  # Remove space before punctuation
        preprocessed = re.sub(r'([,.!?;:])\s*', r'\1 ', preprocessed)  # Add single space after punctuation
        preprocessed = re.sub(r'\n{4,}', '\n\n\n', preprocessed)  # Cap at 3 newlines max
        preprocessed = re.sub(r'\r', '', preprocessed)  # Remove carriage returns
        preprocessed = re.sub(r'\t', ' ', preprocessed)  # Replace tabs with spaces
        
        # Smart line joining
        lines = preprocessed.split('\n')
        processed_lines = []
        current_line = ''
        
        for line in lines:
            line = line.strip()
            
            if not line:
                # Empty line - preserve paragraph break
                if current_line:
                    processed_lines.append(current_line)
                    current_line = ''
                processed_lines.append('')
                continue
            
            # Check if this line should be joined with previous
            is_very_short = len(line) < 20
            ends_with_punctuation = bool(re.search(r'[.!?]$', current_line))
            starts_with_capital = bool(re.match(r'^[A-Z]', line))
            looks_like_heading = len(line) < 40 and line == line.upper()
            
            if (current_line and not ends_with_punctuation and not starts_with_capital 
                and not looks_like_heading and not is_very_short):
                # Join with previous line
                current_line += ' ' + line
            else:
                # Start new line
                if current_line:
                    processed_lines.append(current_line)
                current_line = line
        
        if current_line:
            processed_lines.append(current_line)
        
        # Create clean paragraphs
        paragraphs = []
        current_paragraph = []
        
        for line in processed_lines:
            if line == '':
                # Empty line marks paragraph break
                if current_paragraph:
                    text = ' '.join(current_paragraph).strip()
                    if text:
                        paragraphs.append({
                            'text': text,
                            'type': 'paragraph',
                            'wordCount': len(text.split()),
                            'charCount': len(text)
                        })
                    current_paragraph = []
            else:
                current_paragraph.append(line)
        
        # Don't forget the last paragraph
        if current_paragraph:
            text = ' '.join(current_paragraph).strip()
            if text:
                paragraphs.append({
                    'text': text,
                    'type': 'paragraph',
                    'wordCount': len(text.split()),
                    'charCount': len(text)
                })
        
        # Create final formatted output
        formatted = '\n\n'.join(p['text'] for p in paragraphs)
        
        # Apply URL/email fixes one more time
        formatted = fix_urls_and_emails(formatted)
        
        # Final cleanup
        formatted = re.sub(r'\s+([,.!?;:])', r'\1', formatted)  # Remove space before punctuation
        formatted = re.sub(r'([,.!?;:])(?!\s|$)', r'\1 ', formatted)  # Ensure space after punctuation
        formatted = re.sub(r' {2,}', ' ', formatted)  # Remove multiple spaces
        formatted = formatted.strip()
        
        # Calculate statistics
        sentences = re.findall(r'[.!?]+', formatted)
        stats = {
            'paragraphCount': len(paragraphs),
            'sentenceCount': len(sentences),
            'cleanedChars': len(formatted),
            'originalChars': len(raw_text),
            'reductionPercent': round((1 - len(formatted) / len(raw_text)) * 100) if len(raw_text) > 0 else 0
        }
        
        return {
            'formatted': formatted,
            'paragraphs': paragraphs,
            'stats': stats
        }
        
    except Exception as error:
        log('ERROR', 'Text formatting error', {'error': str(error)})
        word_count = len(raw_text.split()) if raw_text else 0
        return {
            'formatted': raw_text,
            'paragraphs': [{'text': raw_text, 'type': 'paragraph', 'wordCount': word_count, 'charCount': len(raw_text)}],
            'stats': {'paragraphCount': 1, 'sentenceCount': 0, 'cleanedChars': len(raw_text)}
        }


async def process_text_with_comprehend(text: str) -> Dict[str, Any]:
    """Process text with AWS Comprehend"""
    try:
        # Comprehend has a 5000 character limit for most operations
        max_length = 5000
        text_to_analyze = text[:max_length] if len(text) > max_length else text
        
        log('INFO', 'Starting Comprehend analysis', {
            'originalLength': len(text),
            'analyzedLength': len(text_to_analyze),
            'truncated': len(text) > max_length
        })
        
        start_time = time.time()
        results = {}
        
        # Language detection
        try:
            language_result = comprehend_client.detect_dominant_language(Text=text_to_analyze)
            
            results['language'] = language_result['Languages'][0]['LanguageCode'] if language_result['Languages'] else 'unknown'
            results['languageScore'] = language_result['Languages'][0]['Score'] if language_result['Languages'] else 0
            
            log('DEBUG', 'Language detection completed', {
                'language': results['language'],
                'score': results['languageScore']
            })
        except Exception as error:
            log('WARN', 'Language detection failed', {'error': str(error)})
            results['language'] = 'unknown'
            results['languageScore'] = 0
        
        # Sentiment analysis
        try:
            sentiment_result = comprehend_client.detect_sentiment(
                Text=text_to_analyze,
                LanguageCode=results['language'] if results['language'] != 'unknown' else 'en'
            )
            
            results['sentiment'] = {
                'Sentiment': sentiment_result['Sentiment'],
                'SentimentScore': sentiment_result['SentimentScore']
            }
            
            log('DEBUG', 'Sentiment analysis completed', {
                'sentiment': results['sentiment']['Sentiment'],
                'positive': results['sentiment']['SentimentScore']['Positive'],
                'negative': results['sentiment']['SentimentScore']['Negative'],
                'neutral': results['sentiment']['SentimentScore']['Neutral'],
                'mixed': results['sentiment']['SentimentScore']['Mixed']
            })
        except Exception as error:
            log('WARN', 'Sentiment analysis failed', {'error': str(error)})
            results['sentiment'] = None
        
        # Entity detection
        try:
            entity_result = comprehend_client.detect_entities(
                Text=text_to_analyze,
                LanguageCode=results['language'] if results['language'] != 'unknown' else 'en'
            )
            
            # Enhanced entity mapping with detailed information
            results['entities'] = []
            for entity in entity_result['Entities']:
                results['entities'].append({
                    'Text': entity['Text'],
                    'Type': entity['Type'],
                    'Score': entity['Score'],
                    'BeginOffset': entity['BeginOffset'],
                    'EndOffset': entity['EndOffset'],
                    'Length': entity['EndOffset'] - entity['BeginOffset'],
                    'Category': get_entity_category(entity['Type']),
                    'Confidence': 'High' if entity['Score'] >= 0.8 else 'Medium' if entity['Score'] >= 0.5 else 'Low'
                })
            
            # Group entities by type for better organization
            entity_summary = {}
            for entity in results['entities']:
                if entity['Type'] not in entity_summary:
                    entity_summary[entity['Type']] = []
                entity_summary[entity['Type']].append({
                    'text': entity['Text'],
                    'score': entity['Score'],
                    'confidence': entity['Confidence']
                })
            
            results['entitySummary'] = entity_summary
            results['entityStats'] = {
                'totalEntities': len(results['entities']),
                'uniqueTypes': list(set(e['Type'] for e in results['entities'])),
                'highConfidenceEntities': len([e for e in results['entities'] if e['Score'] >= 0.8]),
                'categories': list(set(e['Category'] for e in results['entities']))
            }
            
            log('DEBUG', 'Entity detection completed', {
                'entitiesCount': len(results['entities']),
                'types': results['entityStats']['uniqueTypes'],
                'categories': results['entityStats']['categories'],
                'highConfidence': results['entityStats']['highConfidenceEntities']
            })
        except Exception as error:
            log('WARN', 'Entity detection failed', {'error': str(error)})
            results['entities'] = []
            results['entitySummary'] = {}
            results['entityStats'] = {
                'totalEntities': 0,
                'uniqueTypes': [],
                'highConfidenceEntities': 0,
                'categories': []
            }
        
        # Key phrases extraction
        try:
            key_phrases_result = comprehend_client.detect_key_phrases(
                Text=text_to_analyze,
                LanguageCode=results['language'] if results['language'] != 'unknown' else 'en'
            )
            
            results['keyPhrases'] = []
            for phrase in key_phrases_result['KeyPhrases']:
                results['keyPhrases'].append({
                    'Text': phrase['Text'],
                    'Score': phrase['Score'],
                    'BeginOffset': phrase['BeginOffset'],
                    'EndOffset': phrase['EndOffset']
                })
            
            log('DEBUG', 'Key phrases extraction completed', {
                'keyPhrasesCount': len(results['keyPhrases'])
            })
        except Exception as error:
            log('WARN', 'Key phrases extraction failed', {'error': str(error)})
            results['keyPhrases'] = []
        
        # Syntax analysis
        try:
            syntax_result = comprehend_client.detect_syntax(
                Text=text_to_analyze,
                LanguageCode=results['language'] if results['language'] != 'unknown' else 'en'
            )
            
            results['syntax'] = []
            for token in syntax_result['SyntaxTokens']:
                results['syntax'].append({
                    'Text': token['Text'],
                    'PartOfSpeech': token['PartOfSpeech']['Tag'],
                    'Score': token['PartOfSpeech']['Score'],
                    'BeginOffset': token['BeginOffset'],
                    'EndOffset': token['EndOffset']
                })
            
            log('DEBUG', 'Syntax analysis completed', {
                'tokensCount': len(results['syntax'])
            })
        except Exception as error:
            log('WARN', 'Syntax analysis failed', {'error': str(error)})
            results['syntax'] = []
        
        processing_time = time.time() - start_time
        results['processingTime'] = processing_time
        results['analyzedTextLength'] = len(text_to_analyze)
        results['originalTextLength'] = len(text)
        results['truncated'] = len(text) > max_length
        
        return results
        
    except Exception as error:
        log('ERROR', 'Comprehend processing error', {'error': str(error)})
        
        # Return empty results on error
        return {
            'language': 'unknown',
            'languageScore': 0,
            'sentiment': None,
            'entities': [],
            'entitySummary': {},
            'entityStats': {
                'totalEntities': 0,
                'uniqueTypes': [],
                'highConfidenceEntities': 0,
                'categories': []
            },
            'keyPhrases': [],
            'syntax': [],
            'processingTime': 0,
            'analyzedTextLength': 0,
            'originalTextLength': len(text),
            'truncated': False,
            'error': str(error)
        }


async def update_file_status(table_name: str, file_id: str, status: str, additional_data: Dict[str, Any] = None) -> None:
    """Update file status in DynamoDB"""
    if additional_data is None:
        additional_data = {}
    
    try:
        # Get the table
        table = dynamodb.Table(table_name)
        
        # First, get the current item to find the upload_timestamp
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('file_id').eq(file_id),
            Limit=1
        )
        
        if not response['Items']:
            raise ValueError(f'File with ID {file_id} not found in database')
        
        upload_timestamp = response['Items'][0]['upload_timestamp']
        
        # Update the item
        update_expression = 'SET processing_status = :status, last_updated = :updated'
        expression_attribute_values = {
            ':status': status,
            ':updated': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Add additional data to the update
        for i, (key, value) in enumerate(additional_data.items()):
            attr_name = f':val{i}'
            update_expression += f', {key} = {attr_name}'
            expression_attribute_values[attr_name] = value
        
        table.update_item(
            Key={
                'file_id': file_id,
                'upload_timestamp': upload_timestamp
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        log('DEBUG', 'DynamoDB status updated', {'fileId': file_id, 'status': status})
        
    except Exception as error:
        log('ERROR', 'Failed to update file status', {
            'fileId': file_id,
            'status': status,
            'error': str(error)
        })
        raise


async def store_processing_results(file_id: str, results: Dict[str, Any]) -> None:
    """Store processing results in DynamoDB"""
    results_table_name = os.getenv('DYNAMODB_TABLE', '').replace('-file-metadata', '-processing-results')
    
    try:
        table = dynamodb.Table(results_table_name)
        
        item = {
            'file_id': file_id,
            **results
        }
        
        table.put_item(Item=item)
        log('DEBUG', 'Processing results stored', {'fileId': file_id, 'table': results_table_name})
        
    except Exception as error:
        log('ERROR', 'Failed to store processing results', {
            'fileId': file_id,
            'error': str(error)
        })
        raise


def run_batch_job() -> None:
    """Batch-only execution logic"""
    # Validate required environment variables
    required_vars = ['S3_BUCKET', 'S3_KEY', 'FILE_ID', 'DYNAMODB_TABLE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        log('ERROR', 'Missing required environment variables', {'missingVars': missing_vars})
        sys.exit(1)
    
    log('INFO', 'Starting batch processing', {
        'batchJobId': os.getenv('AWS_BATCH_JOB_ID'),
        'jobQueue': os.getenv('AWS_BATCH_JQ_NAME')
    })
    
    try:
        import asyncio
        
        # For Python < 3.7 compatibility
        if hasattr(asyncio, 'run'):
            result = asyncio.run(process_s3_file())
        else:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(process_s3_file())
        
        log('INFO', 'Batch job completed successfully', {
            'processingDuration': result['processing_duration'],
            'textExtracted': result['analysis']['word_count'] > 0
        })
        sys.exit(0)
    except Exception as error:
        log('ERROR', 'Batch job failed', {
            'error': str(error),
            'type': type(error).__name__
        })
        sys.exit(1)


# Enhanced error handling
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    log('INFO', f'Received signal {signum}, shutting down gracefully')
    sys.exit(0)


def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    log('ERROR', 'Uncaught exception', {
        'error': str(exc_value),
        'type': exc_type.__name__
    })
    sys.exit(1)


# Set up signal handlers and exception handling
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
sys.excepthook = handle_exception


def main():
    """Main entry point"""
    # Graceful startup with error handling
    time.sleep(0.1)  # Minimal delay for logging setup
    run_batch_job()


if __name__ == '__main__':
    main()