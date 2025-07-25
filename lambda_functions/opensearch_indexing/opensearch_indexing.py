import json
import boto3
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for automatic OpenSearch indexing
    Triggered by EventBridge when OCR processing completes
    """
    try:
        logger.info(f"Processing indexing event: {json.dumps(event, default=str)}")
        
        # Parse EventBridge event
        detail = event.get('detail', {})
        job_name = detail.get('jobName', '')
        job_status = detail.get('jobStatus', '')
        job_id = detail.get('jobId', '')
        
        if job_status != 'SUCCEEDED':
            logger.info(f"Job {job_id} status is {job_status}, skipping indexing")
            return {"statusCode": 200, "message": "Job not succeeded, skipping"}
        
        if not job_name.startswith('ocr-processor-job-'):
            logger.info(f"Job {job_name} is not an OCR processor job, skipping")
            return {"statusCode": 200, "message": "Not an OCR job, skipping"}
        
        # Extract file ID from job name
        file_id = extract_file_id_from_job_name(job_name)
        if not file_id:
            logger.error(f"Could not extract file ID from job name: {job_name}")
            return {"statusCode": 400, "error": "Invalid job name format"}
        
        logger.info(f"Processing successful OCR job {job_id} for file {file_id}")
        
        # Initialize clients
        opensearch_client = get_opensearch_client()
        dynamodb = boto3.resource('dynamodb')
        
        # Get OCR results from DynamoDB
        ocr_data = get_ocr_results(dynamodb, file_id)
        if not ocr_data:
            logger.error(f"No OCR results found for file {file_id}")
            return {"statusCode": 404, "error": "OCR results not found"}
        
        # Get file metadata
        file_metadata = get_file_metadata(dynamodb, file_id)
        
        # Index document in OpenSearch
        index_result = index_document(opensearch_client, file_id, ocr_data, file_metadata)
        
        logger.info(f"Successfully indexed document {file_id}: {index_result}")
        
        return {
            "statusCode": 200,
            "message": "Document indexed successfully",
            "file_id": file_id,
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in indexing handler: {str(e)}")
        return {
            "statusCode": 500,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

def get_opensearch_client() -> OpenSearch:
    """Initialize and return OpenSearch client with AWS authentication"""
    endpoint = os.environ.get('OPENSEARCH_ENDPOINT')
    region = os.environ.get('OPENSEARCH_REGION', 'ap-southeast-2')
    use_serverless = os.environ.get('USE_SERVERLESS', 'false').lower() == 'true'
    
    if not endpoint:
        raise ValueError("OPENSEARCH_ENDPOINT environment variable is required")
    
    # Create AWS authentication
    credentials = boto3.Session().get_credentials()
    
    # Use different service name for serverless
    service_name = 'aoss' if use_serverless else 'es'
    auth = AWSRequestsAuth(credentials, region, service_name)
    
    # Clean endpoint URL
    clean_endpoint = endpoint.replace('https://', '').replace('http://', '')
    
    # Initialize OpenSearch client
    client = OpenSearch(
        hosts=[{'host': clean_endpoint, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True
    )
    
    return client

def extract_file_id_from_job_name(job_name: str) -> Optional[str]:
    """Extract file ID from OCR job name"""
    # Expected format: ocr-processor-job-{file_id}-{timestamp}
    if not job_name.startswith('ocr-processor-job-'):
        return None
    
    parts = job_name.replace('ocr-processor-job-', '').split('-')
    if len(parts) >= 1:
        return parts[0]
    
    return None

def get_ocr_results(dynamodb, file_id: str) -> Optional[Dict[str, Any]]:
    """Get OCR results from DynamoDB"""
    try:
        table_name = os.environ.get('DYNAMODB_TABLE')
        if not table_name:
            raise ValueError("DYNAMODB_TABLE environment variable is required")
        
        table = dynamodb.Table(table_name)
        
        response = table.get_item(Key={'file_id': file_id})
        
        if 'Item' not in response:
            logger.warning(f"No OCR results found for file {file_id}")
            return None
        
        return response['Item']
        
    except Exception as e:
        logger.error(f"Error getting OCR results for {file_id}: {str(e)}")
        return None

def get_file_metadata(dynamodb, file_id: str) -> Optional[Dict[str, Any]]:
    """Get file metadata from DynamoDB"""
    try:
        table_name = os.environ.get('FILE_METADATA_TABLE')
        if not table_name:
            logger.warning("FILE_METADATA_TABLE not configured, skipping metadata lookup")
            return None
        
        table = dynamodb.Table(table_name)
        
        response = table.get_item(Key={'file_id': file_id})
        
        if 'Item' not in response:
            logger.warning(f"No metadata found for file {file_id}")
            return None
        
        return response['Item']
        
    except Exception as e:
        logger.error(f"Error getting file metadata for {file_id}: {str(e)}")
        return None

def index_document(client: OpenSearch, file_id: str, ocr_data: Dict[str, Any], 
                  file_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Index document in OpenSearch"""
    try:
        index_name = os.environ.get('INDEX_NAME', 'ocr-documents')
        
        # Ensure index exists
        ensure_index_exists(client, index_name)
        
        # Build document for indexing
        document = build_search_document(file_id, ocr_data, file_metadata)
        
        # Index the document
        response = client.index(
            index=index_name,
            id=file_id,
            body=document,
            refresh=True  # Make document immediately searchable
        )
        
        logger.info(f"Document indexed: {response['_id']} with result: {response['result']}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error indexing document {file_id}: {str(e)}")
        raise

def build_search_document(file_id: str, ocr_data: Dict[str, Any], 
                         file_metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build search document from OCR results and metadata"""
    
    # Base document structure
    document = {
        "file_id": file_id,
        "timestamp": datetime.utcnow().isoformat(),
        "status": ocr_data.get('status', 'completed'),
        "extracted_text": ocr_data.get('extracted_text', ''),
        "corrected_text": ocr_data.get('corrected_text', ''),
        "processing_time_seconds": float(ocr_data.get('processing_time_seconds', 0))
    }
    
    # Add filename (from metadata or OCR data)
    if file_metadata:
        document["filename"] = file_metadata.get('filename', file_metadata.get('original_name', 'unknown'))
        document["file_metadata"] = {
            "file_type": file_metadata.get('content_type', '').split('/')[-1] if file_metadata.get('content_type') else 'unknown',
            "file_size": int(file_metadata.get('file_size', 0)),
            "original_name": file_metadata.get('filename', 'unknown'),
            "upload_timestamp": file_metadata.get('created_at', file_metadata.get('timestamp'))
        }
    else:
        document["filename"] = ocr_data.get('filename', 'unknown')
        document["file_metadata"] = {
            "file_type": "unknown",
            "file_size": 0,
            "original_name": ocr_data.get('filename', 'unknown'),
            "upload_timestamp": ocr_data.get('created_at')
        }
    
    # Add NLP analysis if available
    if 'nlp_analysis' in ocr_data:
        nlp = ocr_data['nlp_analysis']
        document["nlp_analysis"] = {
            "key_phrases": nlp.get('key_phrases', []),
            "entities": nlp.get('entities', []),
            "sentiment": nlp.get('sentiment', {}),
            "language": nlp.get('language', 'en')
        }
    
    # Add textract analysis results if available
    if 'textract_analysis' in ocr_data:
        textract = ocr_data['textract_analysis']
        document["textract_analysis"] = {
            "form_fields": textract.get('form_fields', []),
            "tables": textract.get('tables', []),
            "confidence_scores": textract.get('confidence_scores', {})
        }
    
    # Add processing metadata
    document["processing_metadata"] = {
        "batch_job_id": ocr_data.get('batch_job_id'),
        "processing_start_time": ocr_data.get('processing_start_time'),
        "processing_end_time": ocr_data.get('processing_end_time'),
        "ocr_engine": ocr_data.get('ocr_engine', 'textract'),
        "version": ocr_data.get('processor_version', '1.0')
    }
    
    # Calculate content statistics
    extracted_text = document["extracted_text"]
    if extracted_text:
        document["content_stats"] = {
            "character_count": len(extracted_text),
            "word_count": len(extracted_text.split()),
            "line_count": len(extracted_text.split('\n')),
            "paragraph_count": len([p for p in extracted_text.split('\n\n') if p.strip()])
        }
    
    return document

def ensure_index_exists(client: OpenSearch, index_name: str):
    """Ensure the index exists with proper mapping"""
    if not client.indices.exists(index=index_name):
        logger.info(f"Creating index: {index_name}")
        
        # Define index mapping optimized for OCR documents
        mapping = {
            "mappings": {
                "properties": {
                    "timestamp": {"type": "date"},
                    "filename": {"type": "keyword"},
                    "file_id": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "extracted_text": {
                        "type": "text",
                        "analyzer": "standard",
                        "search_analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256}
                        }
                    },
                    "corrected_text": {
                        "type": "text",
                        "analyzer": "standard",
                        "search_analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword", "ignore_above": 256}
                        }
                    },
                    "file_metadata": {
                        "properties": {
                            "file_type": {"type": "keyword"},
                            "file_size": {"type": "long"},
                            "original_name": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                }
                            },
                            "upload_timestamp": {"type": "date"}
                        }
                    },
                    "processing_time_seconds": {"type": "float"},
                    "nlp_analysis": {
                        "properties": {
                            "key_phrases": {"type": "keyword"},
                            "entities": {
                                "properties": {
                                    "text": {"type": "keyword"},
                                    "type": {"type": "keyword"},
                                    "confidence": {"type": "float"}
                                }
                            },
                            "sentiment": {
                                "properties": {
                                    "sentiment": {"type": "keyword"},
                                    "confidence": {"type": "float"}
                                }
                            },
                            "language": {"type": "keyword"}
                        }
                    },
                    "textract_analysis": {
                        "properties": {
                            "form_fields": {"type": "nested"},
                            "tables": {"type": "nested"},
                            "confidence_scores": {
                                "properties": {
                                    "average": {"type": "float"},
                                    "minimum": {"type": "float"},
                                    "maximum": {"type": "float"}
                                }
                            }
                        }
                    },
                    "processing_metadata": {
                        "properties": {
                            "batch_job_id": {"type": "keyword"},
                            "processing_start_time": {"type": "date"},
                            "processing_end_time": {"type": "date"},
                            "ocr_engine": {"type": "keyword"},
                            "version": {"type": "keyword"}
                        }
                    },
                    "content_stats": {
                        "properties": {
                            "character_count": {"type": "integer"},
                            "word_count": {"type": "integer"},
                            "line_count": {"type": "integer"},
                            "paragraph_count": {"type": "integer"}
                        }
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "ocr_analyzer": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop", "stemmer"]
                        }
                    }
                }
            }
        }
        
        client.indices.create(index=index_name, body=mapping)
        logger.info(f"Index created successfully: {index_name}")
    else:
        logger.info(f"Index already exists: {index_name}")

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized response"""
    return {
        'statusCode': status_code,
        'body': json.dumps(body, ensure_ascii=False, default=str)
    }