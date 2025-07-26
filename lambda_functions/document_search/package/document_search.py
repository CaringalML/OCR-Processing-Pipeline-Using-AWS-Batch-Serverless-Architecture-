import json
import boto3
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
try:
    from rapidfuzz import fuzz, process
    FUZZY_SEARCH_AVAILABLE = True
except ImportError:
    FUZZY_SEARCH_AVAILABLE = False

def decimal_default(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def fuzzy_match(query, text, threshold=80):
    """
    Perform fuzzy matching between query and text
    Returns True if similarity is above threshold, along with the score
    """
    if not FUZZY_SEARCH_AVAILABLE or not query or not text:
        return False, 0
    
    # Use token_sort_ratio for better matching of words in different order
    score = fuzz.token_sort_ratio(query.lower(), text.lower())
    return score >= threshold, score

def fuzzy_search_in_text(query, text, threshold=80):
    """
    Search for fuzzy matches of query within a larger text
    Returns the best matching snippet and its score
    """
    if not FUZZY_SEARCH_AVAILABLE or not query or not text:
        return None, 0
    
    # Split text into sentences or chunks for better matching
    words = query.split()
    text_lower = text.lower()
    query_lower = query.lower()
    
    # Try to find the best matching section
    best_score = 0
    best_match_start = 0
    
    # Sliding window approach
    window_size = len(query) * 3  # Look for text roughly 3x the query length
    
    for i in range(0, len(text) - window_size + 1, 20):  # Step by 20 chars
        window = text[i:i + window_size]
        score = fuzz.partial_ratio(query_lower, window.lower())
        if score > best_score:
            best_score = score
            best_match_start = i
    
    if best_score >= threshold:
        # Extract context around the match
        start = max(0, best_match_start - 50)
        end = min(len(text), best_match_start + window_size + 50)
        snippet = text[start:end]
        
        if start > 0:
            snippet = '...' + snippet
        if end < len(text):
            snippet = snippet + '...'
            
        return snippet, best_score
    
    return None, best_score

def lambda_handler(event, context):
    """
    AWS Lambda handler for document search functionality
    Searches across document metadata and OCR results
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration from environment variables
    metadata_table_name = os.environ.get('METADATA_TABLE')
    results_table_name = os.environ.get('RESULTS_TABLE')
    cloudfront_domain = os.environ.get('CLOUDFRONT_DOMAIN')
    
    # Validate environment variables
    if not metadata_table_name or not results_table_name:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Configuration Error',
                'message': 'Missing required environment variables',
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Search parameters
        search_term = query_params.get('q', '').strip()
        publication = query_params.get('publication', '').strip()
        year = query_params.get('year', '').strip()
        title = query_params.get('title', '').strip()
        status = query_params.get('status', '').strip()
        file_id = query_params.get('fileId', '').strip()
        
        # Fuzzy search parameters
        fuzzy = query_params.get('fuzzy', 'false').lower() == 'true'
        fuzzy_threshold = int(query_params.get('fuzzyThreshold', '80'))  # Default 80% similarity
        
        # Pagination parameters
        limit = int(query_params.get('limit', '20'))
        limit = min(limit, 100)  # Cap at 100 items
        
        # Initialize tables
        metadata_table = dynamodb.Table(metadata_table_name)
        results_table = dynamodb.Table(results_table_name)
        
        # Build search results
        search_results = []
        
        # If file_id is provided, do a direct lookup
        if file_id:
            # Query metadata table for specific file
            response = metadata_table.query(
                KeyConditionExpression=Key('file_id').eq(file_id)
            )
            items = response.get('Items', [])
        else:
            # Build filter expression based on search criteria
            filter_expressions = []
            expression_values = {}
            
            # Status filter
            if status:
                filter_expressions.append(Attr('processing_status').eq(status))
            
            # Publication filter
            if publication and not fuzzy:
                filter_expressions.append(Attr('publication').contains(publication))
            
            # Year filter
            if year:
                filter_expressions.append(Attr('year').eq(year))
            
            # Title filter
            if title and not fuzzy:
                filter_expressions.append(Attr('title').contains(title))
            
            # Build scan parameters
            scan_params = {
                'Limit': limit
            }
            
            # Apply filters if any
            if filter_expressions:
                filter_expression = filter_expressions[0]
                for expr in filter_expressions[1:]:
                    filter_expression = filter_expression & expr
                scan_params['FilterExpression'] = filter_expression
            
            # Scan metadata table
            response = metadata_table.scan(**scan_params)
            items = response.get('Items', [])
        
        # If we have a search term, also search in OCR results
        ocr_matched_files = {}  # Changed to dict to store scores
        if search_term and not fuzzy:
            # Exact search in OCR results
            results_response = results_table.scan(
                FilterExpression=Attr('ocr_text').contains(search_term),
                Limit=limit
            )
            
            for result in results_response.get('Items', []):
                ocr_matched_files[result.get('file_id')] = {'match': True, 'score': 100}
        
        # Process items and build response
        fuzzy_results = []  # Store results with fuzzy scores
        
        for item in items:
            # Fuzzy matching on metadata fields
            match_score = 100  # Default score for exact matches
            fuzzy_matched = False
            
            if fuzzy:
                # Check fuzzy match on publication
                if publication and item.get('publication'):
                    matched, score = fuzzy_match(publication, item['publication'], fuzzy_threshold)
                    if matched:
                        fuzzy_matched = True
                        match_score = min(match_score, score)
                    elif publication:  # If search term provided but no match
                        continue
                
                # Check fuzzy match on title
                if title and item.get('title'):
                    matched, score = fuzzy_match(title, item['title'], fuzzy_threshold)
                    if matched:
                        fuzzy_matched = True
                        match_score = min(match_score, score)
                    elif title:  # If search term provided but no match
                        continue
            
            # For non-fuzzy search with search term, check OCR matches
            if search_term and not fuzzy and item.get('file_id') not in ocr_matched_files:
                # Skip items that don't match OCR search
                continue
            
            # Build file URL
            s3_key = item.get('s3_key', '')
            file_url = f"https://{cloudfront_domain}/{s3_key}" if cloudfront_domain and s3_key else None
            
            # Build result item
            result_item = {
                'fileId': item.get('file_id'),
                'fileName': item.get('file_name'),
                'uploadTimestamp': item.get('upload_timestamp'),
                'status': item.get('processing_status', 'unknown'),
                'fileSize': item.get('file_size', 0),
                'contentType': item.get('content_type', 'unknown'),
                'fileUrl': file_url,
                'metadata': {
                    'publication': item.get('publication', ''),
                    'year': item.get('year', ''),
                    'title': item.get('title', ''),
                    'author': item.get('author', ''),
                    'description': item.get('description', ''),
                    'tags': item.get('tags', [])
                }
            }
            
            # Get OCR results if available
            if item.get('processing_status') == 'completed':
                try:
                    ocr_response = results_table.get_item(
                        Key={'file_id': item.get('file_id')}
                    )
                    if 'Item' in ocr_response:
                        ocr_item = ocr_response['Item']
                        result_item['ocrResults'] = {
                            'text': ocr_item.get('ocr_text', ''),
                            'confidence': float(ocr_item.get('confidence', 0)),
                            'processingTime': ocr_item.get('processing_time', 0),
                            'pageCount': ocr_item.get('page_count', 0)
                        }
                        
                        # Add snippet for search results
                        if search_term and 'ocr_text' in ocr_item:
                            text = ocr_item['ocr_text']
                            
                            if fuzzy:
                                # Fuzzy search in OCR text
                                snippet, score = fuzzy_search_in_text(search_term, text, fuzzy_threshold)
                                if snippet:
                                    result_item['snippet'] = snippet
                                    result_item['fuzzyScore'] = score
                                    match_score = min(match_score, score)
                                    fuzzy_matched = True
                                elif search_term:  # If search term provided but no fuzzy match in OCR
                                    continue
                            else:
                                # Exact search
                                index = text.lower().find(search_term.lower())
                                if index != -1:
                                    # Extract snippet around search term
                                    start = max(0, index - 100)
                                    end = min(len(text), index + len(search_term) + 100)
                                    snippet = text[start:end]
                                    if start > 0:
                                        snippet = '...' + snippet
                                    if end < len(text):
                                        snippet = snippet + '...'
                                    result_item['snippet'] = snippet
                except Exception as e:
                    print(f"Error fetching OCR results for {item.get('file_id')}: {str(e)}")
            
            # Add fuzzy match score if applicable
            if fuzzy and fuzzy_matched:
                result_item['matchScore'] = match_score
            
            if fuzzy:
                fuzzy_results.append((result_item, match_score))
            else:
                search_results.append(result_item)
        
        # Sort fuzzy results by score and convert to list
        if fuzzy:
            fuzzy_results.sort(key=lambda x: x[1], reverse=True)
            search_results = [item[0] for item in fuzzy_results]
        
        # Build response
        response_data = {
            'success': True,
            'message': f'Found {len(search_results)} results',
            'query': {
                'searchTerm': search_term,
                'publication': publication,
                'year': year,
                'title': title,
                'status': status,
                'fileId': file_id,
                'fuzzy': fuzzy,
                'fuzzyThreshold': fuzzy_threshold if fuzzy else None
            },
            'fuzzySearchAvailable': FUZZY_SEARCH_AVAILABLE,
            'results': search_results,
            'totalResults': len(search_results),
            'hasMore': response.get('LastEvaluatedKey') is not None,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_data, default=decimal_default)
        }
        
    except Exception as e:
        error_msg = f"Error performing search: {str(e)}"
        print(f"ERROR: {error_msg}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': 'Search failed',
                'details': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }