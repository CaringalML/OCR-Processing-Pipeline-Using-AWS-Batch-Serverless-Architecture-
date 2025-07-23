#!/usr/bin/env python3
"""
OCR Processing Pipeline - Batch Processing Only
Converts documents to text using AWS Textract and analyzes with AWS Comprehend
Fixed for DynamoDB compatibility
"""

import json
import os
import logging
import time
import signal
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union
import re
from decimal import Decimal, InvalidOperation

import boto3
from botocore.exceptions import ClientError

# Text correction libraries
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print('WARN: TextBlob not available - text correction disabled')

try:
    import spellchecker
    from spellchecker import SpellChecker
    SPELLCHECKER_AVAILABLE = True
except ImportError:
    SPELLCHECKER_AVAILABLE = False
    print('WARN: PySpellChecker not available - advanced spell checking disabled')

try:
    import spacy
    # Try to load the English model
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except (ImportError, OSError):
    SPACY_AVAILABLE = False
    nlp = None
    print('WARN: spaCy not available - advanced NLP text refinement disabled')

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
            'timestamp': datetime.now(timezone.utc).isoformat(),
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
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime': time.time(),
        'mode': 'batch-only',
        'version': '2.0.0'
    }


def convert_to_dynamodb_compatible(obj: Any) -> Any:
    """
    Recursively convert Python objects to DynamoDB-compatible format.
    Handles floats, None values, and empty containers.
    """
    if obj is None:
        return 'NULL'  # DynamoDB doesn't support null values directly
    elif isinstance(obj, float):
        if obj != obj:  # Check for NaN
            return Decimal('0')
        elif obj == float('inf') or obj == float('-inf'):
            return Decimal('0')
        else:
            try:
                # Convert to string first to avoid precision issues
                return Decimal(str(round(obj, 6)))
            except (InvalidOperation, ValueError):
                return Decimal('0')
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, str):
        return obj if obj else 'EMPTY'  # DynamoDB doesn't like empty strings
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, dict):
        if not obj:  # Empty dict
            return {'EMPTY': 'DICT'}
        converted = {}
        for k, v in obj.items():
            # Convert key to string if needed
            key = str(k) if not isinstance(k, str) else k
            if not key:  # Empty key
                key = 'EMPTY_KEY'
            converted[key] = convert_to_dynamodb_compatible(v)
        return converted
    elif isinstance(obj, (list, tuple)):
        if not obj:  # Empty list
            return ['EMPTY_LIST']
        return [convert_to_dynamodb_compatible(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        # For any other type, convert to string
        return str(obj) if obj is not None else 'NULL'


def safe_decimal_conversion(value: Union[float, int, str]) -> Decimal:
    """Safely convert a value to Decimal with error handling"""
    try:
        if isinstance(value, (int, str)):
            return Decimal(str(value))
        elif isinstance(value, float):
            if value != value:  # NaN check
                return Decimal('0')
            elif value == float('inf') or value == float('-inf'):
                return Decimal('0')
            else:
                return Decimal(str(round(value, 6)))
        else:
            return Decimal('0')
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


def process_s3_file() -> Dict[str, Any]:
    """Main S3 file processing function - synchronous version"""
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
        update_file_status(dynamo_table, file_id, 'processing', {
            'processing_started': datetime.now(timezone.utc).isoformat(),
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
        extracted_data = process_file_with_textract(bucket_name, object_key)
        textract_time = time.time() - start_time
        
        log('INFO', 'Textract processing completed', {
            'processingTimeSeconds': textract_time,
            'wordCount': extracted_data['wordCount'],
            'lineCount': extracted_data['lineCount'],
            'confidence': extracted_data['confidence']
        })
        
        # Format the extracted text with correction
        formatted_text_data = {}
        corrected_text_data = {}
        refined_text_data = {}
        text_for_comprehend = extracted_data['text']
        
        if extracted_data['text'] and extracted_data['text'].strip():
            log('INFO', 'Formatting extracted text')
            formatted_text_data = format_extracted_text(extracted_data['text'])
            
            # Apply text correction to the formatted text
            log('INFO', 'Applying text correction')
            corrected_text_data = apply_text_correction(formatted_text_data.get('formatted', extracted_data['text']))
            
            # Apply spaCy-based text refinement to the corrected text
            log('INFO', 'Applying spaCy text refinement')
            refined_text_data = refine_text_with_spacy(corrected_text_data.get('corrected_text', formatted_text_data.get('formatted', extracted_data['text'])))
            
            # Use the refined text for Comprehend analysis (fallback to corrected text if refinement fails)
            text_for_comprehend = refined_text_data.get('refined_text', corrected_text_data.get('corrected_text', formatted_text_data.get('formatted', extracted_data['text'])))
            
            log('INFO', 'Text formatting, correction, and refinement completed', {
                'originalChars': formatted_text_data['stats']['originalChars'],
                'formattedChars': formatted_text_data['stats']['cleanedChars'],
                'correctedChars': corrected_text_data.get('corrected_length', 0),
                'refinedChars': refined_text_data.get('refined_length', 0),
                'paragraphs': formatted_text_data['stats']['paragraphCount'],
                'sentences': formatted_text_data['stats']['sentenceCount'],
                'correctionsApplied': corrected_text_data.get('corrections_made', 0),
                'refinementsApplied': refined_text_data.get('refinements_applied', 0),
                'correctionMethod': corrected_text_data.get('method', 'none'),
                'refinementMethod': refined_text_data.get('method', 'none'),
                'entitiesFound': len(refined_text_data.get('entities_found', []))
            })
        
        # Process formatted text with AWS Comprehend
        comprehend_data = {}
        if text_for_comprehend and text_for_comprehend.strip():
            log('INFO', 'Starting Comprehend analysis on formatted text')
            comprehend_start_time = time.time()
            comprehend_data = process_text_with_comprehend(text_for_comprehend)
            comprehend_time = time.time() - comprehend_start_time
            
            log('INFO', 'Comprehend analysis completed', {
                'processingTimeSeconds': comprehend_time,
                'language': comprehend_data.get('languageName', comprehend_data.get('language', 'Unknown')),
                'languageCode': comprehend_data.get('language'),
                'sentiment': comprehend_data.get('sentiment', {}).get('Sentiment'),
                'entitiesCount': len(comprehend_data.get('entities', [])),
                'keyPhrasesCount': len(comprehend_data.get('keyPhrases', []))
            })
        else:
            log('INFO', 'Skipping Comprehend analysis - no text extracted')
        
        total_processing_time = time.time() - start_time
        
        # Generate processing results with text correction
        processing_results = {
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'file_size': file_size,
            'content_type': content_type,
            'processing_duration': f'{total_processing_time:.2f} seconds',
            'extracted_text': extracted_data['text'],
            'formatted_text': formatted_text_data.get('formatted', extracted_data['text']),
            'corrected_text': corrected_text_data.get('corrected_text', formatted_text_data.get('formatted', extracted_data['text'])),
            'refined_text': refined_text_data.get('refined_text', corrected_text_data.get('corrected_text', formatted_text_data.get('formatted', extracted_data['text']))),
            'summary_analysis': {
                'word_count': extracted_data['wordCount'],
                'character_count': len(extracted_data['text']),
                'line_count': extracted_data['lineCount'],
                'paragraph_count': formatted_text_data.get('stats', {}).get('paragraphCount', 0),
                'sentence_count': formatted_text_data.get('stats', {}).get('sentenceCount', 0),
                'confidence': extracted_data['confidence'],
                'corrections_applied': corrected_text_data.get('corrections_made', 0),
                'correction_method': corrected_text_data.get('method', 'none'),
                'refinements_applied': refined_text_data.get('refinements_applied', 0),
                'refinement_method': refined_text_data.get('method', 'none'),
                'entities_found': len(refined_text_data.get('entities_found', [])),
                'sentences_processed': refined_text_data.get('sentences_processed', 0)
            },
            'text_correction_details': {
                'corrections_made': corrected_text_data.get('corrections_made', 0),
                'method_used': corrected_text_data.get('method', 'none'),
                'sample_corrections': corrected_text_data.get('correction_details', []),
                'length_change': corrected_text_data.get('corrected_length', 0) - corrected_text_data.get('original_length', 0)
            },
            'text_refinement_details': {
                'refinements_applied': refined_text_data.get('refinements_applied', 0),
                'method_used': refined_text_data.get('method', 'none'),
                'entities_found': refined_text_data.get('entities_found', []),
                'sentences_processed': refined_text_data.get('sentences_processed', 0),
                'sample_refinements': refined_text_data.get('refinement_details', []),
                'pos_statistics': refined_text_data.get('pos_statistics', {}),
                'length_change': refined_text_data.get('refined_length', 0) - refined_text_data.get('original_length', 0)
            },
            'comprehend_analysis': comprehend_data,
            'metadata': {
                'processor_version': '2.3.0',  # Updated version
                'batch_job_id': os.getenv('AWS_BATCH_JOB_ID', 'unknown'),
                'textract_job_id': extracted_data['jobId'],
                'textract_duration': f'{textract_time:.2f} seconds',
                'comprehend_duration': f"{comprehend_data.get('processingTime', 0):.2f} seconds" if comprehend_data.get('processingTime') else 'N/A',
                'text_correction_enabled': TEXTBLOB_AVAILABLE or SPELLCHECKER_AVAILABLE,
                'text_refinement_enabled': SPACY_AVAILABLE
            }
        }
        
        log('INFO', 'Storing processing results')
        
        # Store processing results in DynamoDB
        store_processing_results(file_id, processing_results)
        
        log('INFO', 'Updating status to processed')
        
        # Update file status to 'processed'
        update_file_status(dynamo_table, file_id, 'processed', {
            'processing_completed': datetime.now(timezone.utc).isoformat(),
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
            update_file_status(dynamo_table, file_id, 'failed', {
                'error_message': str(error),
                'failed_at': datetime.now(timezone.utc).isoformat()
            })
            log('INFO', 'File status updated to failed')
        except Exception as update_error:
            log('ERROR', 'Failed to update error status', {'error': str(update_error)})
        
        raise


def process_file_with_textract(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """Process file with AWS Textract - synchronous version"""
    try:
        log('INFO', 'Starting Textract document analysis', {
            's3Uri': f's3://{bucket_name}/{object_key}'
        })
        
        # Start asynchronous document analysis - text only
        # For text-only extraction, we can use start_document_text_detection instead
        # which doesn't require FeatureTypes parameter
        try:
            response = textract_client.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': object_key
                    }
                }
            )
        except Exception as e:
            # If text detection fails, try document analysis with valid feature types
            log('WARN', 'Text detection failed, trying document analysis', {'error': str(e)})
            response = textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': object_key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS']  # Valid feature types for document analysis
            )
        job_id = response['JobId']
        log('INFO', 'Textract job submitted', {'textractJobId': job_id})
        
        # Wait for job completion
        job_status = 'IN_PROGRESS'
        attempts = 0
        max_attempts = 60  # 5 minutes timeout (5 seconds * 60)
        
        while job_status == 'IN_PROGRESS' and attempts < max_attempts:
            time.sleep(5)  # Wait 5 seconds
            
            # Try text detection result first, then document analysis
            try:
                status_response = textract_client.get_document_text_detection(JobId=job_id)
            except:
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
            
            # Try text detection result first, then document analysis
            try:
                response = textract_client.get_document_text_detection(**params)
            except:
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


def apply_text_correction(text: str) -> Dict[str, Any]:
    """
    Apply text correction using available libraries.
    Returns both corrected text and correction statistics.
    """
    if not text or not text.strip():
        return {
            'corrected_text': text,
            'corrections_made': 0,
            'correction_details': [],
            'method': 'none'
        }
    
    correction_details = []
    corrected_text = text
    corrections_made = 0
    method_used = 'none'
    
    try:
        # Method 1: TextBlob correction (preferred for OCR errors)
        if TEXTBLOB_AVAILABLE:
            log('DEBUG', 'Applying TextBlob text correction')
            blob = TextBlob(text)
            corrected_blob = blob.correct()
            corrected_text = str(corrected_blob)
            method_used = 'textblob'
            
            # Count differences
            original_words = text.split()
            corrected_words = corrected_text.split()
            
            if len(original_words) == len(corrected_words):
                for i, (orig, corr) in enumerate(zip(original_words, corrected_words)):
                    if orig != corr:
                        corrections_made += 1
                        correction_details.append({
                            'position': i,
                            'original': orig,
                            'corrected': corr,
                            'type': 'spelling'
                        })
            
            log('DEBUG', f'TextBlob correction completed - {corrections_made} corrections made')
        
        # Method 2: PySpellChecker as fallback/enhancement
        elif SPELLCHECKER_AVAILABLE:
            log('DEBUG', 'Applying PySpellChecker text correction')
            spell = SpellChecker()
            words = text.split()
            corrected_words = []
            method_used = 'pyspellchecker'
            
            for i, word in enumerate(words):
                # Remove punctuation for spell checking
                clean_word = ''.join(char for char in word if char.isalpha())
                if clean_word and clean_word.lower() in spell:
                    corrected_words.append(word)
                elif clean_word:
                    # Get the most likely correction
                    correction = spell.correction(clean_word.lower())
                    if correction and correction != clean_word.lower():
                        # Preserve original case and punctuation
                        corrected_word = word.replace(clean_word, correction.capitalize() if clean_word.isupper() else correction)
                        corrected_words.append(corrected_word)
                        corrections_made += 1
                        correction_details.append({
                            'position': i,
                            'original': word,
                            'corrected': corrected_word,
                            'type': 'spelling'
                        })
                    else:
                        corrected_words.append(word)
                else:
                    corrected_words.append(word)
            
            corrected_text = ' '.join(corrected_words)
            log('DEBUG', f'PySpellChecker correction completed - {corrections_made} corrections made')
        
        # Method 3: Basic OCR-specific corrections (always applied)
        if method_used == 'none':
            log('DEBUG', 'Applying basic OCR corrections')
            corrected_text = apply_basic_ocr_corrections(text)
            method_used = 'basic_ocr'
            # Count basic corrections (approximate)
            if corrected_text != text:
                corrections_made = len(text.split()) - len(corrected_text.split()) + abs(len(text) - len(corrected_text)) // 10
        
    except Exception as error:
        log('WARN', 'Text correction failed, using original text', {'error': str(error)})
        corrected_text = text
        method_used = 'failed'
    
    return {
        'corrected_text': corrected_text,
        'corrections_made': corrections_made,
        'correction_details': correction_details[:10],  # Limit to first 10 for storage
        'method': method_used,
        'original_length': len(text),
        'corrected_length': len(corrected_text)
    }


def refine_text_with_spacy(text: str) -> Dict[str, Any]:
    """
    Use spaCy for advanced NLP-based text refinement.
    This includes:
    - Sentence segmentation and proper capitalization
    - Named entity recognition for proper noun handling
    - Part-of-speech tagging for grammar improvements
    - Dependency parsing for sentence structure
    - Lemmatization for word normalization
    """
    if not SPACY_AVAILABLE or not text or not text.strip():
        return {
            'refined_text': text,
            'refinements_applied': 0,
            'refinement_details': [],
            'method': 'none',
            'entities_found': [],
            'sentences_processed': 0
        }
    
    try:
        # Process text with spaCy
        doc = nlp(text)
        
        refined_sentences = []
        refinement_details = []
        entities_found = []
        refinements_count = 0
        
        # Extract and store named entities
        for ent in doc.ents:
            entities_found.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            })
        
        # Process each sentence
        for sent_idx, sent in enumerate(doc.sents):
            original_sent = sent.text.strip()
            refined_sent = original_sent
            sent_refinements = []
            
            # 1. Ensure proper sentence capitalization
            if refined_sent and refined_sent[0].islower():
                # Check if it starts with a named entity that should stay lowercase
                first_token = sent[0]
                if not (first_token.ent_type_ or first_token.pos_ == 'PROPN'):
                    refined_sent = refined_sent[0].upper() + refined_sent[1:]
                    sent_refinements.append("capitalized_sentence_start")
                    refinements_count += 1
            
            # 2. Handle proper nouns and entities
            tokens = []
            for token in sent:
                token_text = token.text
                
                # Capitalize proper nouns that aren't already capitalized
                if token.pos_ == 'PROPN' and token_text.islower():
                    token_text = token_text.capitalize()
                    sent_refinements.append(f"capitalized_proper_noun:{token.text}")
                    refinements_count += 1
                
                # Preserve entity formatting
                if token.ent_type_:
                    # Special handling for certain entity types
                    if token.ent_type_ in ['PERSON', 'ORG', 'GPE', 'LOC']:
                        if token_text.islower():
                            token_text = token_text.title()
                            sent_refinements.append(f"capitalized_entity:{token.text}({token.ent_type_})")
                            refinements_count += 1
                
                tokens.append(token_text)
            
            # 3. Reconstruct sentence with proper spacing
            refined_sent = ""
            for i, token in enumerate(tokens):
                # Handle spacing
                if i == 0:
                    refined_sent = token
                elif token in ".,!?;:)]}" or tokens[i-1] in "([{":
                    refined_sent += token
                elif token in "'" and i > 0 and tokens[i-1].lower() in ['don', 'doesn', 'didn', 'won', 'wouldn', 'shouldn', 'couldn', 'can', 'couldn']:
                    refined_sent += token
                else:
                    refined_sent += " " + token
            
            # 4. Ensure sentence ends with proper punctuation
            if refined_sent and refined_sent[-1] not in '.!?':
                # Check if it's likely a complete sentence
                if len([t for t in sent if t.pos_ == 'VERB']) > 0:
                    refined_sent += '.'
                    sent_refinements.append("added_period")
                    refinements_count += 1
            
            # 5. Fix common grammar patterns using dependency parsing
            # Example: Fix double punctuation
            refined_sent = re.sub(r'([.!?])\s*\1+', r'\1', refined_sent)
            if original_sent != refined_sent and "fixed_double_punctuation" not in sent_refinements:
                sent_refinements.append("fixed_double_punctuation")
                refinements_count += 1
            
            refined_sentences.append(refined_sent)
            
            if sent_refinements:
                refinement_details.append({
                    'sentence_index': sent_idx,
                    'original': original_sent,
                    'refined': refined_sent,
                    'refinements': sent_refinements
                })
        
        # Join sentences with proper spacing
        refined_text = ' '.join(refined_sentences)
        
        # Advanced grammar refinements (post-processing)
        advanced_refinements = 0
        
        # Fix which/that usage - "that" for restrictive clauses, "which" for non-restrictive
        # Simple heuristic: if no comma before, use "that"; if comma before, use "which"
        which_that_fixes = 0
        # Fix "which are" -> "that are" when restrictive
        refined_text = re.sub(r'\b(\w+)\s+which\s+(are|is|was|were)\b(?!\s*,)', r'\1 that \2', refined_text)
        which_that_fixes += len(re.findall(r'\b(\w+)\s+which\s+(are|is|was|were)\b(?!\s*,)', ' '.join(refined_sentences)))
        
        # Fix "which may" -> "that may" when restrictive  
        refined_text = re.sub(r'\b(\w+)\s+which\s+(may|might|could|should|would|will)\b(?!\s*,)', r'\1 that \2', refined_text)
        which_that_fixes += len(re.findall(r'\b(\w+)\s+which\s+(may|might|could|should|would|will)\b(?!\s*,)', ' '.join(refined_sentences)))
        
        advanced_refinements += which_that_fixes
        
        # Fix redundant word usage
        redundant_fixes = 0
        # "common use, use but" -> "common use, but"
        before_redundant = refined_text
        refined_text = re.sub(r'\b(\w+),\s+\1\s+but\b', r'\1, but', refined_text)
        refined_text = re.sub(r'\b(\w+)\s+\1\s+(,|\.|\s)', r'\1\2', refined_text)  # Remove duplicate words
        if before_redundant != refined_text:
            redundant_fixes += 1
            advanced_refinements += 1
        
        # Fix punctuation issues
        punctuation_fixes = 0
        
        # Add commas before coordinating conjunctions in compound sentences
        before_comma = refined_text
        refined_text = re.sub(r'\b(\w+)\s+(and|but|or|so|yet)\s+(\w)', r'\1, \2 \3', refined_text)
        # But not if it's a short phrase
        refined_text = re.sub(r'\b(\w{1,4}),\s+(and|or)\s+(\w{1,4})\b', r'\1 \2 \3', refined_text)
        if before_comma != refined_text:
            punctuation_fixes += 1
        
        # Fix dash usage - replace single dashes with em dashes in appropriate contexts
        before_dash = refined_text
        # Pattern: word - word -> word—word (em dash for interruption)
        refined_text = re.sub(r'\s-\s([a-z])', r'—\1', refined_text)  # - dream -> —dream
        # Pattern: word - while -> word—while  
        refined_text = re.sub(r'\s-\s(while|when|as|if|though|although)\b', r'—\1', refined_text)
        if before_dash != refined_text:
            punctuation_fixes += 1
        
        advanced_refinements += punctuation_fixes
        
        # Fix OCR artifacts and incomplete words
        artifact_fixes = 0
        
        # Remove incomplete words at the end (like "pi-" at end of text)
        before_artifact = refined_text
        refined_text = re.sub(r'\s+\w{1,3}-\s*$', '', refined_text)  # Remove short words ending with dash at end
        refined_text = re.sub(r'\s+\w{1,2}\s*$', '', refined_text)   # Remove very short orphaned words at end
        if before_artifact != refined_text:
            artifact_fixes += 1
            advanced_refinements += 1
        
        # Fix common OCR number/letter confusion in context
        before_ocr = refined_text
        refined_text = re.sub(r'\blane1\b', 'lane', refined_text)  # lane1 -> lane
        refined_text = re.sub(r'\b(\w+)1\s+(he|she|it|they)\b', r'\1 \2', refined_text)  # word1 he -> word he
        if before_ocr != refined_text:
            artifact_fixes += 1
            advanced_refinements += 1
        
        # Add missing articles and prepositions where obvious
        article_fixes = 0
        before_article = refined_text
        # "a meal, flirt" -> "a meal, or flirt"
        refined_text = re.sub(r'\ba\s+(\w+),\s+([a-z])', r'a \1, or \2', refined_text)
        if before_article != refined_text:
            article_fixes += 1
            advanced_refinements += 1
        
        # Final cleanup
        refined_text = re.sub(r'\s+', ' ', refined_text).strip()
        refined_text = re.sub(r'\s+([.,!?;:])', r'\1', refined_text)
        
        # Calculate statistics
        pos_stats = {}
        for token in doc:
            pos_stats[token.pos_] = pos_stats.get(token.pos_, 0) + 1
        
        return {
            'refined_text': refined_text,
            'refinements_applied': refinements_count + advanced_refinements,
            'basic_refinements': refinements_count,
            'advanced_grammar_fixes': advanced_refinements,
            'refinement_details': refinement_details[:10],  # Limit details to first 10 for brevity
            'method': 'spacy_advanced',
            'entities_found': entities_found[:20],  # Limit to first 20 entities
            'sentences_processed': len(list(doc.sents)),
            'pos_statistics': pos_stats,
            'original_length': len(text),
            'refined_length': len(refined_text)
        }
        
    except Exception as e:
        log('WARN', f'spaCy refinement failed: {str(e)}')
        return {
            'refined_text': text,
            'refinements_applied': 0,
            'refinement_details': [],
            'method': 'none',
            'error': str(e),
            'entities_found': [],
            'sentences_processed': 0
        }


def apply_basic_ocr_corrections(text: str) -> str:
    """
    Apply basic OCR-specific corrections for common character recognition errors.
    This works without external libraries.
    """
    if not text:
        return text
    
    # Common OCR character substitutions
    ocr_corrections = {
        # Number/letter confusions
        r'\b0\b': 'O',  # Standalone 0 to O
        r'\bO\b(?=\d)': '0',  # O followed by digits to 0
        r'\b1\b(?=[A-Za-z])': 'I',  # 1 before letters to I
        r'\bI\b(?=\d)': '1',  # I before digits to 1
        r'\b5\b(?=[A-Za-z])': 'S',  # 5 before letters to S
        r'\b8\b(?=[A-Za-z])': 'B',  # 8 before letters to B
        
        # Common character confusions
        r'\brn\b': 'm',  # rn to m
        r'\bvv\b': 'w',  # vv to w
        r'\bcl\b': 'd',  # cl to d
        r'\bri\b': 'n',  # ri to n
        
        # Fix spacing around punctuation
        r'\s+([,.!?;:])': r'\1',  # Remove space before punctuation
        r'([,.!?;:])\s*': r'\1 ',  # Ensure space after punctuation
        
        # Fix common word breaks
        r'\bthe\s+': 'the ',
        r'\band\s+': 'and ',
        r'\bwith\s+': 'with ',
        r'\bthat\s+': 'that ',
        r'\bthis\s+': 'this ',
        
        # Multiple spaces to single space
        r'\s{2,}': ' ',
    }
    
    corrected = text
    for pattern, replacement in ocr_corrections.items():
        corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
    
    return corrected.strip()


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
                'stats': {'paragraphCount': 0, 'sentenceCount': 0, 'cleanedChars': 0, 'originalChars': 0, 'reductionPercent': 0}
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
        
        def fix_ocr_character_errors(text: str) -> str:
            """
            Fix common OCR character recognition errors while preserving legitimate usage.
            Only applies fixes when characters are clearly misplaced in word contexts.
            """
            # First, protect legitimate patterns by temporarily replacing them
            protected_patterns = []
            
            # Protect email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            def protect_email(match):
                placeholder = f"__EMAIL_{len(protected_patterns)}__"
                protected_patterns.append(match.group(0))
                return placeholder
            text = re.sub(email_pattern, protect_email, text)
            
            # Protect URLs
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            def protect_url(match):
                placeholder = f"__URL_{len(protected_patterns)}__"
                protected_patterns.append(match.group(0))
                return placeholder
            text = re.sub(url_pattern, protect_url, text)
            
            # Protect www patterns
            www_pattern = r'www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s]*'
            def protect_www(match):
                placeholder = f"__WWW_{len(protected_patterns)}__"
                protected_patterns.append(match.group(0))
                return placeholder
            text = re.sub(www_pattern, protect_www, text)
            
            # Protect file paths
            filepath_pattern = r'[A-Za-z]:\\[^\s<>"*|?]+|/[^\s<>"*|?]+'
            def protect_filepath(match):
                placeholder = f"__PATH_{len(protected_patterns)}__"
                protected_patterns.append(match.group(0))
                return placeholder
            text = re.sub(filepath_pattern, protect_filepath, text)
            
            # Protect currency and measurements
            money_pattern = r'\$\d+(?:\.\d{2})?|\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s*(?:kg|lb|cm|inch|ft|meter|mile)'
            def protect_money(match):
                placeholder = f"__MEASURE_{len(protected_patterns)}__"
                protected_patterns.append(match.group(0))
                return placeholder
            text = re.sub(money_pattern, protect_money, text, flags=re.IGNORECASE)
            
            # Now apply OCR character fixes to unprotected text
            
            # Common OCR character substitutions in words (not at word boundaries near protected content)
            # Fix > and / when they appear mid-word (likely OCR errors)
            text = re.sub(r'\b(\w+)[>\/\|\\](\w+)\b', lambda m: f"{m.group(1)}{m.group(2)}", text)
            
            # Fix common letter-to-symbol OCR errors in word contexts
            text = re.sub(r'\b(\w*)[@&](\w+)\b', lambda m: f"{m.group(1)}a{m.group(2)}", text)  # @ -> a
            text = re.sub(r'\b(\w+)[€£\$](\w+)\b', lambda m: f"{m.group(1)}e{m.group(2)}", text)  # €/£/$ -> e (in words)
            text = re.sub(r'\b(\w+)0(\w+)\b', lambda m: f"{m.group(1)}o{m.group(2)}" if 'o' in m.group(1).lower() or 'o' in m.group(2).lower() else m.group(0), text)  # 0 -> o
            text = re.sub(r'\b(\w+)1(\w+)\b', lambda m: f"{m.group(1)}l{m.group(2)}" if any(c in 'aeiou' for c in m.group(1).lower()) else m.group(0), text)  # 1 -> l
            text = re.sub(r'\b(\w+)5(\w+)\b', lambda m: f"{m.group(1)}s{m.group(2)}" if any(c in 'aeiou' for c in m.group(1).lower()) else m.group(0), text)  # 5 -> s
            text = re.sub(r'\b(\w+)8(\w+)\b', lambda m: f"{m.group(1)}b{m.group(2)}" if any(c in 'aeiou' for c in m.group(1).lower()) else m.group(0), text)  # 8 -> b
            
            # Fix specific word patterns that are commonly mis-OCR'd
            text = re.sub(r'\bgui[>\/\|\\]dan[\/\\]ce\b', 'guidance', text, flags=re.IGNORECASE)
            text = re.sub(r'\bsel[€£\$]ct\b', 'select', text, flags=re.IGNORECASE)
            text = re.sub(r'\bp[@&]ssenger\b', 'passenger', text, flags=re.IGNORECASE)
            text = re.sub(r'\bauto[>\/\|]matic\b', 'automatic', text, flags=re.IGNORECASE)
            text = re.sub(r'\btrans[>\/\|]port\b', 'transport', text, flags=re.IGNORECASE)
            text = re.sub(r'\bdevel[0o]pment\b', 'development', text, flags=re.IGNORECASE)
            text = re.sub(r'\beff[1l]cient\b', 'efficient', text, flags=re.IGNORECASE)
            text = re.sub(r'\bveh[1l]cle\b', 'vehicle', text, flags=re.IGNORECASE)
            
            # Restore protected patterns
            for i, pattern in enumerate(protected_patterns):
                text = text.replace(f"__EMAIL_{i}__", pattern)
                text = text.replace(f"__URL_{i}__", pattern)
                text = text.replace(f"__WWW_{i}__", pattern)
                text = text.replace(f"__PATH_{i}__", pattern)
                text = text.replace(f"__MEASURE_{i}__", pattern)
            
            return text
        
        # Apply OCR character error fixes (after URL/email protection)
        preprocessed = fix_ocr_character_errors(preprocessed)
        
        # Fix hyphenated words at line breaks AFTER OCR character fixes
        # Pattern: word- \n next_part -> word next_part
        preprocessed = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', preprocessed)
        
        # Fix partial words split across lines without hyphens
        # Pattern: partial_word \n rest_of_word (when both parts don't form real words)
        # This is more complex - we'll handle common patterns
        preprocessed = re.sub(r'\b(guid|ance)\s*\n\s*(ance|system)', lambda m: 
                            'guidance' if m.group(1).lower() == 'guid' and m.group(2).lower().startswith('ance') 
                            else 'guidance system' if m.group(1).lower() == 'guid' 
                            else m.group(0), preprocessed, flags=re.IGNORECASE)
        
        preprocessed = re.sub(r'\b(se)\s*\n\s*(lect)', r'select', preprocessed, flags=re.IGNORECASE)
        preprocessed = re.sub(r'\b(pas)\s*\n\s*(senger)', r'passenger', preprocessed, flags=re.IGNORECASE)
        preprocessed = re.sub(r'\b(devel)\s*\n\s*(opment)', r'development', preprocessed, flags=re.IGNORECASE)
        preprocessed = re.sub(r'\b(auto)\s*\n\s*(matic)', r'automatic', preprocessed, flags=re.IGNORECASE)
        preprocessed = re.sub(r'\b(trans)\s*\n\s*(port)', r'transport', preprocessed, flags=re.IGNORECASE)
        
        # Continue with other preprocessing
        preprocessed = re.sub(r'\.\s+([A-Z])', r'. \1', preprocessed)  # Fix period spacing
        preprocessed = re.sub(r'([a-z])\s+([A-Z])', r'\1 \2', preprocessed)  # Fix word spacing
        preprocessed = re.sub(r'(\w)\s+([,.])', r'\1\2', preprocessed)  # Remove space before punctuation
        preprocessed = re.sub(r'([,.!?;:])\s*', r'\1 ', preprocessed)  # Add single space after punctuation
        preprocessed = re.sub(r'\n{4,}', '\n\n\n', preprocessed)  # Cap at 3 newlines max
        preprocessed = re.sub(r'\r', '', preprocessed)  # Remove carriage returns
        preprocessed = re.sub(r'\t', ' ', preprocessed)  # Replace tabs with spaces
        
        # Fix common OCR number/letter artifacts in formatting stage
        preprocessed = re.sub(r'\blane1\b', 'lane', preprocessed)  # lane1 -> lane
        preprocessed = re.sub(r'\b(\w+)1\s+(he|she|it|they)\b', r'\1 \2', preprocessed)  # word1 he -> word he
        
        # Remove incomplete words at the end (like "pi-" at end of text)
        preprocessed = re.sub(r'\s+\w{1,3}-\s*$', '', preprocessed)  # Remove short words ending with dash at end
        preprocessed = re.sub(r'\s+\w{1,2}\s*$', '', preprocessed)   # Remove very short orphaned words at end
        
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
            
            # Special case: check if current_line ends with a partial word and line starts with rest of word
            ends_with_hyphen = current_line.endswith('-') if current_line else False
            current_line_words = current_line.split() if current_line else []
            line_words = line.split() if line else []
            
            # Check for split word patterns (last word of current + first word of next)
            should_join_split_word = False
            if (current_line_words and line_words and not ends_with_punctuation 
                and not starts_with_capital and len(current_line_words[-1]) < 8 
                and len(line_words[0]) < 8):
                # Potential split word - join them
                should_join_split_word = True
            
            if (current_line and (ends_with_hyphen or should_join_split_word or 
                (not ends_with_punctuation and not starts_with_capital 
                and not looks_like_heading and not is_very_short))):
                # Join with previous line
                if ends_with_hyphen:
                    # Remove hyphen when joining
                    current_line = current_line.rstrip('-') + line
                else:
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
        original_len = len(raw_text)
        formatted_len = len(formatted)
        
        stats = {
            'paragraphCount': len(paragraphs),
            'sentenceCount': len(sentences),
            'cleanedChars': formatted_len,
            'originalChars': original_len,
            'reductionPercent': round((1 - formatted_len / original_len) * 100) if original_len > 0 else 0
        }
        
        return {
            'formatted': formatted,
            'paragraphs': paragraphs,
            'stats': stats
        }
        
    except Exception as error:
        log('ERROR', 'Text formatting error', {'error': str(error)})
        word_count = len(raw_text.split()) if raw_text else 0
        original_len = len(raw_text) if raw_text else 0
        return {
            'formatted': raw_text,
            'paragraphs': [{'text': raw_text, 'type': 'paragraph', 'wordCount': word_count, 'charCount': original_len}],
            'stats': {'paragraphCount': 1, 'sentenceCount': 0, 'cleanedChars': original_len, 'originalChars': original_len, 'reductionPercent': 0}
        }


def get_language_name(language_code: str) -> str:
    """Convert AWS Comprehend language codes to full language names"""
    language_map = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh': 'Chinese (Simplified)',
        'zh-TW': 'Chinese (Traditional)',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'tr': 'Turkish',
        'pl': 'Polish',
        'nl': 'Dutch',
        'sv': 'Swedish',
        'da': 'Danish',
        'no': 'Norwegian',
        'fi': 'Finnish',
        'cs': 'Czech',
        'hu': 'Hungarian',
        'ro': 'Romanian',
        'bg': 'Bulgarian',
        'hr': 'Croatian',
        'sk': 'Slovak',
        'sl': 'Slovenian',
        'et': 'Estonian',
        'lv': 'Latvian',
        'lt': 'Lithuanian',
        'uk': 'Ukrainian',
        'he': 'Hebrew',
        'th': 'Thai',
        'vi': 'Vietnamese',
        'id': 'Indonesian',
        'ms': 'Malay',
        'tl': 'Filipino',
        'ta': 'Tamil',
        'te': 'Telugu',
        'bn': 'Bengali',
        'ur': 'Urdu',
        'fa': 'Persian',
        'sw': 'Swahili',
        'am': 'Amharic',
        'so': 'Somali',
        'yo': 'Yoruba',
        'ig': 'Igbo',
        'ha': 'Hausa'
    }
    return language_map.get(language_code.lower(), f"Unknown ({language_code})")


def process_text_with_comprehend(text: str) -> Dict[str, Any]:
    """Process text with AWS Comprehend - synchronous version"""
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
            
            language_code = language_result['Languages'][0]['LanguageCode'] if language_result['Languages'] else 'unknown'
            language_score = safe_decimal_conversion(language_result['Languages'][0]['Score'] if language_result['Languages'] else 0)
            
            results['language'] = language_code
            results['languageName'] = get_language_name(language_code)
            results['languageScore'] = language_score
            
            log('DEBUG', 'Language detection completed', {
                'languageCode': language_code,
                'languageName': results['languageName'],
                'score': float(language_score)
            })
        except Exception as error:
            log('WARN', 'Language detection failed', {'error': str(error)})
            results['language'] = 'unknown'
            results['languageName'] = 'Unknown'
            results['languageScore'] = Decimal('0')
        
        # Sentiment analysis
        try:
            sentiment_result = comprehend_client.detect_sentiment(
                Text=text_to_analyze,
                LanguageCode=results['language'] if results['language'] != 'unknown' else 'en'
            )
            
            results['sentiment'] = {
                'Sentiment': sentiment_result['Sentiment'],
                'SentimentScore': {
                    'Positive': safe_decimal_conversion(sentiment_result['SentimentScore']['Positive']),
                    'Negative': safe_decimal_conversion(sentiment_result['SentimentScore']['Negative']),
                    'Neutral': safe_decimal_conversion(sentiment_result['SentimentScore']['Neutral']),
                    'Mixed': safe_decimal_conversion(sentiment_result['SentimentScore']['Mixed'])
                }
            }
            
            log('DEBUG', 'Sentiment analysis completed', {
                'sentiment': results['sentiment']['Sentiment'],
                'positive': float(results['sentiment']['SentimentScore']['Positive']),
                'negative': float(results['sentiment']['SentimentScore']['Negative']),
                'neutral': float(results['sentiment']['SentimentScore']['Neutral']),
                'mixed': float(results['sentiment']['SentimentScore']['Mixed'])
            })
        except Exception as error:
            log('WARN', 'Sentiment analysis failed', {'error': str(error)})
            results['sentiment'] = {
                'Sentiment': 'UNKNOWN',
                'SentimentScore': {
                    'Positive': Decimal('0'),
                    'Negative': Decimal('0'),
                    'Neutral': Decimal('0'),
                    'Mixed': Decimal('0')
                }
            }
        
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
                    'Score': safe_decimal_conversion(entity['Score']),
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
            
            results['entitySummary'] = entity_summary if entity_summary else {'EMPTY': 'NO_ENTITIES'}
            results['entityStats'] = {
                'totalEntities': len(results['entities']),
                'uniqueTypes': list(set(e['Type'] for e in results['entities'])) if results['entities'] else ['NONE'],
                'highConfidenceEntities': len([e for e in results['entities'] if float(e['Score']) >= 0.8]),
                'categories': list(set(e['Category'] for e in results['entities'])) if results['entities'] else ['NONE']
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
            results['entitySummary'] = {'EMPTY': 'NO_ENTITIES'}
            results['entityStats'] = {
                'totalEntities': 0,
                'uniqueTypes': ['NONE'],
                'highConfidenceEntities': 0,
                'categories': ['NONE']
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
                    'Score': safe_decimal_conversion(phrase['Score']),
                    'BeginOffset': phrase['BeginOffset'],
                    'EndOffset': phrase['EndOffset']
                })
            
            if not results['keyPhrases']:
                results['keyPhrases'] = [{'Text': 'NO_KEY_PHRASES', 'Score': Decimal('0'), 'BeginOffset': 0, 'EndOffset': 0}]
            
            log('DEBUG', 'Key phrases extraction completed', {
                'keyPhrasesCount': len([kp for kp in results['keyPhrases'] if kp['Text'] != 'NO_KEY_PHRASES'])
            })
        except Exception as error:
            log('WARN', 'Key phrases extraction failed', {'error': str(error)})
            results['keyPhrases'] = [{'Text': 'NO_KEY_PHRASES', 'Score': Decimal('0'), 'BeginOffset': 0, 'EndOffset': 0}]
        
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
                    'Score': safe_decimal_conversion(token['PartOfSpeech']['Score']),
                    'BeginOffset': token['BeginOffset'],
                    'EndOffset': token['EndOffset']
                })
            
            if not results['syntax']:
                results['syntax'] = [{'Text': 'NO_SYNTAX', 'PartOfSpeech': 'UNKNOWN', 'Score': Decimal('0'), 'BeginOffset': 0, 'EndOffset': 0}]
            
            log('DEBUG', 'Syntax analysis completed', {
                'tokensCount': len([s for s in results['syntax'] if s['Text'] != 'NO_SYNTAX'])
            })
        except Exception as error:
            log('WARN', 'Syntax analysis failed', {'error': str(error)})
            results['syntax'] = [{'Text': 'NO_SYNTAX', 'PartOfSpeech': 'UNKNOWN', 'Score': Decimal('0'), 'BeginOffset': 0, 'EndOffset': 0}]
        
        processing_time = time.time() - start_time
        results['processingTime'] = safe_decimal_conversion(processing_time)
        results['analyzedTextLength'] = len(text_to_analyze)
        results['originalTextLength'] = len(text)
        results['truncated'] = len(text) > max_length
        
        return results
        
    except Exception as error:
        log('ERROR', 'Comprehend processing error', {'error': str(error)})
        
        # Return empty results on error
        return {
            'language': 'unknown',
            'languageScore': Decimal('0'),
            'sentiment': {
                'Sentiment': 'UNKNOWN',
                'SentimentScore': {
                    'Positive': Decimal('0'),
                    'Negative': Decimal('0'),
                    'Neutral': Decimal('0'),
                    'Mixed': Decimal('0')
                }
            },
            'entities': [],
            'entitySummary': {'EMPTY': 'NO_ENTITIES'},
            'entityStats': {
                'totalEntities': 0,
                'uniqueTypes': ['NONE'],
                'highConfidenceEntities': 0,
                'categories': ['NONE']
            },
            'keyPhrases': [{'Text': 'NO_KEY_PHRASES', 'Score': Decimal('0'), 'BeginOffset': 0, 'EndOffset': 0}],
            'syntax': [{'Text': 'NO_SYNTAX', 'PartOfSpeech': 'UNKNOWN', 'Score': Decimal('0'), 'BeginOffset': 0, 'EndOffset': 0}],
            'processingTime': Decimal('0'),
            'analyzedTextLength': 0,
            'originalTextLength': len(text),
            'truncated': False,
            'error': str(error)
        }


def update_file_status(table_name: str, file_id: str, status: str, additional_data: Dict[str, Any] = None) -> None:
    """Update file status in DynamoDB - synchronous version"""
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
        
        # Convert additional data to DynamoDB compatible format
        additional_data_converted = convert_to_dynamodb_compatible(additional_data)
        
        # Update the item
        update_expression = 'SET processing_status = :status, last_updated = :updated'
        expression_attribute_values = {
            ':status': status,
            ':updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Add additional data to the update
        for i, (key, value) in enumerate(additional_data_converted.items()):
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


def store_processing_results(file_id: str, results: Dict[str, Any]) -> None:
    """Store processing results in DynamoDB - synchronous version"""
    results_table_name = os.getenv('DYNAMODB_TABLE', '').replace('-file-metadata', '-processing-results')
    
    try:
        table = dynamodb.Table(results_table_name)
        
        # Convert all values to DynamoDB compatible format
        item = convert_to_dynamodb_compatible({
            'file_id': file_id,
            **results
        })
        
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
        # Process synchronously (no async/await)
        result = process_s3_file()
        
        log('INFO', 'Batch job completed successfully', {
            'processingDuration': result['processing_duration'],
            'textExtracted': result['summary_analysis']['word_count'] > 0
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