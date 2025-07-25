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
    Lambda handler for OpenSearch operations
    Handles search queries, document indexing, and management operations
    """
    try:
        # Parse request
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        query_params = event.get('queryStringParameters') or {}
        
        # Parse request body
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event.get('body', '{}'))
            except json.JSONDecodeError:
                return create_response(400, {"error": "Invalid JSON in request body"})
        
        logger.info(f"Processing {http_method} request to {path}")
        logger.info(f"Query params: {query_params}")
        logger.info(f"Request body keys: {list(body.keys())}")
        
        # Initialize OpenSearch client
        opensearch_client = get_opensearch_client()
        
        # Route request based on operation
        operation = body.get('operation', 'search')
        
        if operation == 'search':
            return handle_search(opensearch_client, body, query_params)
        elif operation == 'index':
            return handle_index(opensearch_client, body)
        elif operation == 'delete':
            return handle_delete(opensearch_client, body)
        elif operation == 'status':
            return handle_status(opensearch_client)
        else:
            return create_response(400, {"error": f"Unknown operation: {operation}"})
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return create_response(500, {
            "error": "Internal server error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })

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

def handle_search(client: OpenSearch, body: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
    """Handle search operations"""
    try:
        index_name = os.environ.get('INDEX_NAME', 'ocr-documents')
        
        # Build search query
        search_body = build_search_query(body, query_params)
        
        logger.info(f"Executing search on index '{index_name}' with query: {json.dumps(search_body, indent=2)}")
        
        # Execute search
        response = client.search(
            index=index_name,
            body=search_body
        )
        
        # Process and format results
        results = process_search_results(response)
        
        return create_response(200, {
            "results": results,
            "total": response['hits']['total']['value'],
            "took": response['took'],
            "max_score": response['hits']['max_score'],
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return create_response(500, {"error": f"Search failed: {str(e)}"})

def build_search_query(body: Dict[str, Any], query_params: Dict[str, str]) -> Dict[str, Any]:
    """Build OpenSearch query from request parameters"""
    
    # Default query structure
    query = {
        "query": {
            "match_all": {}
        },
        "size": min(int(query_params.get('size', '10')), 100),  # Limit to 100 results
        "from": int(query_params.get('from', '0')),
        "sort": [
            {"timestamp": {"order": "desc"}}
        ],
        "highlight": {
            "fields": {
                "extracted_text": {
                    "fragment_size": 150,
                    "number_of_fragments": 3
                },
                "corrected_text": {
                    "fragment_size": 150,
                    "number_of_fragments": 3
                }
            }
        }
    }
    
    # Build search query based on input
    search_text = body.get('query', '').strip()
    search_type = body.get('search_type', 'multi_match')
    
    if search_text:
        if search_type == 'multi_match':
            query["query"] = {
                "multi_match": {
                    "query": search_text,
                    "fields": [
                        "extracted_text^2",  # Higher relevance for extracted text
                        "corrected_text^2",
                        "filename^1.5",
                        "file_metadata.original_name^1.5",
                        "nlp_analysis.key_phrases",
                        "nlp_analysis.entities.text"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        elif search_type == 'phrase':
            query["query"] = {
                "multi_match": {
                    "query": search_text,
                    "fields": ["extracted_text", "corrected_text"],
                    "type": "phrase"
                }
            }
        elif search_type == 'wildcard':
            query["query"] = {
                "bool": {
                    "should": [
                        {"wildcard": {"extracted_text": f"*{search_text.lower()}*"}},
                        {"wildcard": {"corrected_text": f"*{search_text.lower()}*"}},
                        {"wildcard": {"filename": f"*{search_text.lower()}*"}}
                    ]
                }
            }
    
    # Add filters
    filters = []
    
    # File type filter
    if body.get('file_type'):
        filters.append({"term": {"file_metadata.file_type": body['file_type']}})
    
    # Date range filter
    if body.get('date_from') or body.get('date_to'):
        date_range = {}
        if body.get('date_from'):
            date_range['gte'] = body['date_from']
        if body.get('date_to'):
            date_range['lte'] = body['date_to']
        filters.append({"range": {"timestamp": date_range}})
    
    # Status filter
    if body.get('status'):
        filters.append({"term": {"status": body['status']}})
    
    # Apply filters if any
    if filters:
        if query["query"] == {"match_all": {}}:
            query["query"] = {"bool": {"filter": filters}}
        else:
            original_query = query["query"]
            query["query"] = {
                "bool": {
                    "must": original_query,
                    "filter": filters
                }
            }
    
    # Add aggregations for faceted search
    query["aggs"] = {
        "file_types": {
            "terms": {"field": "file_metadata.file_type", "size": 10}
        },
        "processing_status": {
            "terms": {"field": "status", "size": 10}
        },
        "date_histogram": {
            "date_histogram": {
                "field": "timestamp",
                "calendar_interval": "day",
                "min_doc_count": 1
            }
        }
    }
    
    return query

def process_search_results(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process and format search results"""
    results = []
    
    for hit in response['hits']['hits']:
        source = hit['_source']
        result = {
            "id": hit['_id'],
            "score": hit['_score'],
            "filename": source.get('filename', 'Unknown'),
            "file_type": source.get('file_metadata', {}).get('file_type', 'Unknown'),
            "timestamp": source.get('timestamp'),
            "status": source.get('status', 'Unknown'),
            "preview": get_text_preview(source),
            "file_size": source.get('file_metadata', {}).get('file_size'),
            "processing_time": source.get('processing_time_seconds')
        }
        
        # Add highlights if available
        if 'highlight' in hit:
            result['highlights'] = hit['highlight']
        
        # Add NLP insights if available
        if 'nlp_analysis' in source:
            nlp = source['nlp_analysis']
            result['nlp_insights'] = {
                "key_phrases": nlp.get('key_phrases', [])[:5],  # Top 5 phrases
                "entities": [
                    {"text": e.get('text'), "type": e.get('type')} 
                    for e in nlp.get('entities', [])[:5]  # Top 5 entities
                ],
                "sentiment": nlp.get('sentiment', {}).get('sentiment')
            }
        
        results.append(result)
    
    return results

def get_text_preview(source: Dict[str, Any], max_length: int = 200) -> str:
    """Extract a preview of the document text"""
    text = source.get('corrected_text') or source.get('extracted_text', '')
    
    if len(text) <= max_length:
        return text
    
    # Find a good break point near the max length
    preview = text[:max_length]
    last_sentence = preview.rfind('.')
    last_space = preview.rfind(' ')
    
    if last_sentence > max_length - 50:
        return preview[:last_sentence + 1]
    elif last_space > max_length - 20:
        return preview[:last_space] + "..."
    else:
        return preview + "..."

def handle_index(client: OpenSearch, body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle document indexing operations"""
    try:
        index_name = os.environ.get('INDEX_NAME', 'ocr-documents')
        
        # Ensure index exists
        ensure_index_exists(client, index_name)
        
        document = body.get('document')
        doc_id = body.get('document_id')
        
        if not document:
            return create_response(400, {"error": "Document data is required"})
        
        # Index the document
        response = client.index(
            index=index_name,
            id=doc_id,
            body=document,
            refresh=True
        )
        
        logger.info(f"Document indexed successfully: {response['_id']}")
        
        return create_response(200, {
            "message": "Document indexed successfully",
            "document_id": response['_id'],
            "result": response['result'],
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Indexing error: {str(e)}")
        return create_response(500, {"error": f"Indexing failed: {str(e)}"})

def handle_delete(client: OpenSearch, body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle document deletion operations"""
    try:
        index_name = os.environ.get('INDEX_NAME', 'ocr-documents')
        doc_id = body.get('document_id')
        
        if not doc_id:
            return create_response(400, {"error": "Document ID is required"})
        
        # Delete the document
        response = client.delete(
            index=index_name,
            id=doc_id,
            refresh=True
        )
        
        logger.info(f"Document deleted successfully: {doc_id}")
        
        return create_response(200, {
            "message": "Document deleted successfully",
            "document_id": doc_id,
            "result": response['result'],
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Deletion error: {str(e)}")
        return create_response(500, {"error": f"Deletion failed: {str(e)}"})

def handle_status(client: OpenSearch) -> Dict[str, Any]:
    """Handle cluster status operations"""
    try:
        # Get cluster health
        health = client.cluster.health()
        
        # Get index stats
        index_name = os.environ.get('INDEX_NAME', 'ocr-documents')
        try:
            stats = client.indices.stats(index=index_name)
            index_stats = stats['indices'].get(index_name, {})
        except:
            index_stats = {}
        
        return create_response(200, {
            "cluster_status": health['status'],
            "cluster_name": health['cluster_name'],
            "number_of_nodes": health['number_of_nodes'],
            "active_shards": health['active_shards'],
            "index_name": index_name,
            "document_count": index_stats.get('total', {}).get('docs', {}).get('count', 0),
            "index_size": index_stats.get('total', {}).get('store', {}).get('size_in_bytes', 0),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return create_response(500, {"error": f"Status check failed: {str(e)}"})

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
                        "search_analyzer": "standard"
                    },
                    "corrected_text": {
                        "type": "text",
                        "analyzer": "standard",
                        "search_analyzer": "standard"
                    },
                    "file_metadata": {
                        "properties": {
                            "file_type": {"type": "keyword"},
                            "file_size": {"type": "long"},
                            "original_name": {"type": "text"},
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
                            }
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

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
        },
        'body': json.dumps(body, ensure_ascii=False, default=str)
    }