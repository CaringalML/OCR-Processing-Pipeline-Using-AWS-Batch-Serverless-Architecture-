import json
import boto3
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    try:
        if isinstance(size_bytes, str):
            size_bytes = float(size_bytes)
        size_bytes = float(size_bytes)
        
        if size_bytes == 0:
            return "0B"
        
        # Define size units
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = size_bytes
        
        # Convert to appropriate unit
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        # Format with appropriate decimal places
        if unit_index == 0:  # Bytes
            return f"{int(size)}B"
        elif size >= 100:  # No decimal for 100+ units
            return f"{int(size)}{units[unit_index]}"
        elif size >= 10:   # 1 decimal for 10-99 units
            return f"{size:.1f}{units[unit_index]}"
        else:              # 2 decimals for less than 10 units
            return f"{size:.2f}{units[unit_index]}"
            
    except (ValueError, TypeError):
        return "Unknown"

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

def fuzzy_match(query, text, threshold=70):
    """
    Perform fuzzy matching between query and text
    Returns True if similarity is above threshold, along with the score
    """
    if not FUZZY_SEARCH_AVAILABLE or not query or not text:
        return False, 0
    
    # Use token_sort_ratio for better matching of words in different order
    score = fuzz.token_sort_ratio(query.lower(), text.lower())
    return score >= threshold, score

def fuzzy_search_in_text(query, text, threshold=70):
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

def extract_year_from_date(date_string):
    """
    Extract year from various date formats including modern calendar picker formats:
    - Year only: '1925'
    - DD/MM/YYYY: '05/08/1925' (modern calendar default)
    - MM/DD/YYYY: '08/05/1925' (US format)
    - YYYY-MM-DD: '1925-08-05' (ISO format)
    - And other variations
    """
    if not date_string or not isinstance(date_string, str):
        return None
    
    import re
    
    # Clean the input string
    date_string = date_string.strip()
    
    # First priority: Check if it's a pure 4-digit year (most common from modern picker)
    if re.match(r'^\d{4}$', date_string):
        year_int = int(date_string)
        if 1000 <= year_int <= 3000:  # Expanded range for historical documents
            return year_int
    
    # Second priority: Find any 4-digit year in the string (for mixed content)
    year_match = re.search(r'\b(1[0-9]\d{2}|20[0-9]\d|21[0-2]\d)\b', date_string)
    if year_match:
        return int(year_match.group())
    
    # Third priority: Parse structured date formats
    date_patterns = [
        # DD/MM/YYYY format (modern calendar default)
        (r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$', 'day_month_year'),
        # MM/DD/YYYY format (US style)  
        (r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$', 'month_day_year'),
        # YYYY/MM/DD or YYYY-MM-DD format (ISO style)
        (r'^(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})$', 'year_month_day'),
        # DD/MM/YY format with 2-digit year
        (r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})$', 'day_month_year2'),
    ]
    
    for pattern, format_type in date_patterns:
        match = re.match(pattern, date_string)
        if match:
            parts = match.groups()
            
            try:
                if format_type == 'year_month_day':
                    year = int(parts[0])
                    if 1000 <= year <= 3000:
                        return year
                        
                elif format_type in ['day_month_year', 'month_day_year']:
                    year = int(parts[2])
                    if 1000 <= year <= 3000:
                        return year
                        
                elif format_type == 'day_month_year2':
                    # Handle 2-digit years
                    year_2digit = int(parts[2])
                    if year_2digit <= 30:
                        year = 2000 + year_2digit
                    else:
                        year = 1900 + year_2digit
                    return year
                    
            except (ValueError, IndexError):
                continue
    
    # Fourth priority: Look for standalone year patterns in text
    # This handles cases like "year 1925" or "in 1925"
    year_in_text = re.search(r'\b(?:year|in|from|since)?\s*(\d{4})\b', date_string, re.IGNORECASE)
    if year_in_text:
        year = int(year_in_text.group(1))
        if 1000 <= year <= 3000:
            return year
    
    return None

def lambda_handler(event, context):
    """
    AWS Lambda handler for unified document search functionality
    Searches across document metadata and refined OCR text content
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration from environment variables
    results_table_name = os.environ.get('FINALIZED_TABLE', 'ocr-processor-batch-finalized-results')
    cloudfront_domain = os.environ.get('CLOUDFRONT_DOMAIN')
    
    # Validate environment variables
    if not results_table_name:
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
        # Parse query parameters - simplified to only essential parameters
        query_params = event.get('queryStringParameters', {}) or {}
        
        # Core search parameters
        search_term = query_params.get('q', '').strip()
        
        # Academic search parameters (Google Scholar style)
        author = query_params.get('author', '').strip()
        publication = query_params.get('publication', '').strip()
        year_start = query_params.get('as_ylo', '').strip()  # Year low (from)
        year_end = query_params.get('as_yhi', '').strip()    # Year high (to)
        sort_by = query_params.get('scisbd', 'relevance')    # Scholar sort by date/relevance
        collection = query_params.get('collection', '').strip()
        document_type = query_params.get('document_type', '').strip()
        
        # Enhanced smart date search detection for modern calendar picker formats
        import re
        if search_term and not year_start and not year_end:
            # Check for pure year input (most common from modern picker)
            if re.match(r'^\d{4}$', search_term.strip()):
                year = search_term.strip()
                if 1000 <= int(year) <= 3000:
                    year_start = year
                    year_end = year
                    search_term = ''  # Clear search term since we're doing a pure date search
            
            # Check for full date formats from modern picker
            elif re.match(r'^\d{1,2}[/.-]\d{1,2}[/.-]\d{4}$', search_term.strip()):
                # Handle DD/MM/YYYY or MM/DD/YYYY formats
                extracted_year = extract_year_from_date(search_term.strip())
                if extracted_year:
                    year_start = str(extracted_year)
                    year_end = str(extracted_year)
                    search_term = ''  # Clear search term since we're doing a pure date search
            
            # Check for "year YYYY" pattern
            elif re.match(r'^year\s+\d{4}$', search_term.strip(), re.IGNORECASE):
                year_match = re.search(r'\b(\d{4})\b', search_term)
                if year_match:
                    year = year_match.group()
                    if 1000 <= int(year) <= 3000:
                        year_start = year
                        year_end = year
                        search_term = ''
        
        # Intelligent fuzzy search - automatically enabled when needed
        fuzzy_explicit = query_params.get('fuzzy', '').lower()
        fuzzy_threshold = int(query_params.get('fuzzyThreshold', '70'))  # Lower default for better user experience
        
        # Auto-enable fuzzy search in these scenarios:
        auto_fuzzy_conditions = [
            len(search_term) > 8,  # Long words likely have typos
            any(char.isdigit() for char in search_term),  # Mixed alphanumeric
            search_term.count(' ') >= 3,  # Complex phrases
        ]
        
        # Determine fuzzy search mode
        if fuzzy_explicit == 'true':
            fuzzy = True
        elif fuzzy_explicit == 'false':
            fuzzy = False  # User explicitly disabled
        else:
            # Auto-enable fuzzy for better user experience
            fuzzy = any(auto_fuzzy_conditions)
        
        # Pagination parameters
        limit = int(query_params.get('num', '20'))  # Scholar uses 'num' parameter
        limit = min(limit, 100)
        
        # Validate search parameters - allow empty search_term if year filters are provided
        if not search_term and not year_start and not year_end and not author and not publication:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Bad Request',
                    'message': 'Search term (q) or year filters are required',
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        # Initialize results table
        results_table = dynamodb.Table(results_table_name)
        
        # Build search results
        search_results = []
        
        # Academic search with scholarly filters
        filter_expressions = []
        
        # Primary content search (if search term provided)
        if search_term:
            content_filters = [
                Attr('finalized_text').contains(search_term),
                Attr('publication_title').contains(search_term),
                Attr('publication_description').contains(search_term),
                Attr('file_name').contains(search_term)
            ]
            content_filter = content_filters[0]
            for expr in content_filters[1:]:
                content_filter = content_filter | expr
            filter_expressions.append(content_filter)
        
        # Academic filters (Google Scholar style)
        if author:
            filter_expressions.append(Attr('publication_author').contains(author))
        
        if publication:
            filter_expressions.append(Attr('publication').contains(publication))
        
        # Store year filters for post-processing since date parsing in DynamoDB filters is complex
        # We'll apply year filtering after retrieving results for better accuracy
        year_start_int = int(year_start) if year_start and year_start.isdigit() else None
        year_end_int = int(year_end) if year_end and year_end.isdigit() else None
        
        # Collection and Document Type filters
        if collection:
            filter_expressions.append(Attr('publication_collection').contains(collection))
        
        if document_type:
            filter_expressions.append(Attr('publication_document_type').contains(document_type))
        
        # Build final filter with AND logic for academic precision
        if filter_expressions:
            combined_filter = filter_expressions[0]
            for expr in filter_expressions[1:]:
                combined_filter = combined_filter & expr  # AND logic for academic search
        else:
            # If no filters, search all documents
            combined_filter = None
        
        # Execute search with academic projections
        scan_params = {
            'Limit': limit * 2 if fuzzy else limit,
            'ProjectionExpression': 'file_id, file_name, upload_timestamp, processing_status, file_size, content_type, #key, publication, publication_year, publication_date, #date, publication_title, publication_author, publication_description, publication_page, publication_tags, publication_collection, publication_document_type, finalized_text, text_source, finalized_timestamp, total_pages',
            'ExpressionAttributeNames': {'#key': 'key', '#date': 'date'}
        }
        
        # For fuzzy search, scan all documents and apply fuzzy matching in code
        # For exact search, use DynamoDB filters for efficiency
        if fuzzy:
            # Fuzzy search: scan all documents, apply non-text filters only
            non_text_filters = []
            if author:
                non_text_filters.append(Attr('publication_author').contains(author))
            if publication:
                non_text_filters.append(Attr('publication').contains(publication))
            # Note: Year filtering will be applied in post-processing for accuracy
            if collection:
                non_text_filters.append(Attr('publication_collection').contains(collection))
            if document_type:
                non_text_filters.append(Attr('publication_document_type').contains(document_type))
            
            if non_text_filters:
                combined_non_text_filter = non_text_filters[0]
                for expr in non_text_filters[1:]:
                    combined_non_text_filter = combined_non_text_filter & expr
                scan_params['FilterExpression'] = combined_non_text_filter
        else:
            # Exact search: use all filters including text filters
            if combined_filter:
                scan_params['FilterExpression'] = combined_filter
        
        response = results_table.scan(**scan_params)
        items = response.get('Items', [])
        
        # Smart fallback: if no results found with exact search, automatically try fuzzy
        fallback_to_fuzzy = False
        if not items and not fuzzy and search_term:
            print(f"No exact matches found for '{search_term}', trying fuzzy search...")
            fuzzy = True
            fallback_to_fuzzy = True
            # Re-run scan without text filters for fuzzy processing
            scan_params_fallback = {
                'Limit': limit * 2,
                'ProjectionExpression': 'file_id, file_name, upload_timestamp, processing_status, file_size, content_type, #key, publication, publication_year, publication_date, #date, publication_title, publication_author, publication_description, publication_page, publication_tags, publication_collection, publication_document_type, finalized_text, text_source, finalized_timestamp, total_pages',
                'ExpressionAttributeNames': {'#key': 'key', '#date': 'date'}
            }
            response = results_table.scan(**scan_params_fallback)
            items = response.get('Items', [])
        
        # Process items and build response
        fuzzy_results = []  # Store results with fuzzy scores
        
        for item in items:
            match_score = 100  # Default score for exact matches
            fuzzy_matched = False
            
            # Apply year filtering in post-processing for better accuracy
            if year_start_int or year_end_int:
                # Extract year from multiple possible date fields
                item_year = None
                for date_field in ['publication_year', 'publication_date', 'date']:
                    date_value = item.get(date_field, '')
                    if date_value:
                        item_year = extract_year_from_date(str(date_value))
                        if item_year:
                            break
                
                # Also check upload timestamp year if no publication date found
                if not item_year and item.get('upload_timestamp'):
                    upload_year = extract_year_from_date(item.get('upload_timestamp', ''))
                    if upload_year:
                        item_year = upload_year
                
                # Filter by year range
                if item_year:
                    if year_start_int and item_year < year_start_int:
                        continue
                    if year_end_int and item_year > year_end_int:
                        continue
                elif year_start_int or year_end_int:
                    # If year filtering is specified but no year found, skip this item
                    continue
            
            # Build file URL from results table data
            s3_key = item.get('key', '')  # 'key' is the field name in results table
            file_url = f"https://{cloudfront_domain}/{s3_key}" if cloudfront_domain and s3_key else None
            
            # Build Google Scholar-style result item with smart date handling
            # Try multiple date sources: publication_year, publication_date, or date field
            date_value = item.get('publication_year', '') or item.get('publication_date', '') or item.get('date', '')
            
            result_item = {
                'fileId': item.get('file_id'),
                'title': item.get('publication_title', item.get('file_name', 'Untitled')),
                'authors': [item.get('publication_author', '')] if item.get('publication_author') else [],
                'publication': item.get('publication', ''),
                'date': date_value,
                'description': item.get('publication_description', ''),
                'page': item.get('publication_page', ''),
                'tags': item.get('publication_tags', []),
                'collection': item.get('publication_collection', ''),
                'documentType': item.get('publication_document_type', ''),
                'fileUrl': file_url,
                'fileType': item.get('content_type', 'unknown'),
                'fileSize': format_file_size(item.get('file_size', 0)),
                'uploadDate': item.get('upload_timestamp', ''),
                'processingStatus': item.get('processing_status', 'unknown')
            }
            
            # Process OCR results - use finalized_text
            finalized_text = item.get('finalized_text', '')
            if finalized_text:
                result_item['ocrResults'] = {
                    'finalizedText': finalized_text,
                    'textSource': item.get('text_source', ''),
                    'finalizedAt': item.get('finalized_timestamp', ''),
                    'pageCount': item.get('total_pages', 0)
                }
                
                # Generate snippet based on search term
                if fuzzy:
                    # Fuzzy search in refined text and metadata
                    fuzzy_matches = []
                    
                    # Check finalized text
                    snippet, score = fuzzy_search_in_text(search_term, finalized_text, fuzzy_threshold)
                    if snippet:
                        fuzzy_matches.append(('text', snippet, score))
                    
                    # Check metadata fields for fuzzy matches
                    for field_name, field_value in [
                        ('publication', item.get('publication', '')),
                        ('title', item.get('publication_title', '')),
                        ('author', item.get('publication_author', '')),
                        ('description', item.get('publication_description', '')),
                        ('filename', item.get('file_name', ''))
                    ]:
                        if field_value:
                            matched, score = fuzzy_match(search_term, field_value, fuzzy_threshold)
                            if matched:
                                fuzzy_matches.append((field_name, field_value, score))
                    
                    if fuzzy_matches:
                        # Use the best match
                        best_match = max(fuzzy_matches, key=lambda x: x[2])
                        result_item['snippet'] = best_match[1]
                        result_item['fuzzyScore'] = best_match[2]
                        result_item['matchField'] = best_match[0]
                        match_score = best_match[2]
                        fuzzy_matched = True
                else:
                    # Enhanced exact search - create optimal snippet from finalized text
                    search_term_lower = search_term.lower()
                    finalized_text_lower = finalized_text.lower()
                    index = finalized_text_lower.find(search_term_lower)
                    
                    if index != -1:
                        # Create contextual snippet with more intelligent boundaries
                        snippet_start = max(0, index - 80)
                        snippet_end = min(len(finalized_text), index + len(search_term) + 120)
                        
                        # Try to break at word boundaries for better readability
                        if snippet_start > 0:
                            word_start = finalized_text.rfind(' ', snippet_start - 20, snippet_start + 20)
                            if word_start != -1:
                                snippet_start = word_start + 1
                        
                        if snippet_end < len(finalized_text):
                            word_end = finalized_text.find(' ', snippet_end - 20, snippet_end + 20)
                            if word_end != -1:
                                snippet_end = word_end
                        
                        snippet = finalized_text[snippet_start:snippet_end]
                        
                        # Add ellipsis for truncated content
                        if snippet_start > 0:
                            snippet = '...' + snippet
                        if snippet_end < len(finalized_text):
                            snippet = snippet + '...'
                        
                        result_item['snippet'] = snippet.strip()
                        
                        # Add match information for better relevance indication
                        result_item['matchField'] = 'text'
                    else:
                        # Check if match was found in metadata fields
                        for field_name, field_value in [
                            ('publication', item.get('publication', '')),
                            ('title', item.get('publication_title', '')),
                            ('author', item.get('publication_author', '')),
                            ('description', item.get('publication_description', '')),
                            ('filename', item.get('file_name', ''))
                        ]:
                            if field_value and search_term_lower in field_value.lower():
                                result_item['snippet'] = field_value
                                result_item['matchField'] = field_name
                                break
            
            # For fuzzy search, only include items that matched
            if fuzzy and not fuzzy_matched:
                continue
            
            # Add fuzzy match score if applicable
            if fuzzy and fuzzy_matched:
                result_item['matchScore'] = match_score
                fuzzy_results.append((result_item, match_score))
            else:
                search_results.append(result_item)
        
        # Enhanced result processing and ranking
        if fuzzy:
            # Sort fuzzy results by score (highest first)
            fuzzy_results.sort(key=lambda x: x[1], reverse=True)
            search_results = [item[0] for item in fuzzy_results[:limit]]
        else:
            # Academic relevance scoring (Google Scholar style)
            def academic_relevance_score(result):
                score = 0
                
                # Academic relevance factors
                # Title matches are most important in academic search
                if result.get('matchField') == 'title':
                    score += 200
                
                # Author matches are highly relevant
                elif result.get('matchField') == 'author':
                    score += 150
                
                # Publication/journal matches are important
                elif result.get('matchField') == 'publication':
                    score += 120
                
                # Full text content matches
                elif result.get('matchField') == 'text':
                    score += 80
                
                # Description/abstract matches
                elif result.get('matchField') == 'description':
                    score += 100
                
                # Academic publication boost (has proper academic metadata)
                if result.get('authors') and result.get('publication') and result.get('date'):
                    score += 50
                
                # Publication year recency (academic preference for recent work)
                year = result.get('date', '')
                if year and year.isdigit():
                    year_num = int(year)
                    if year_num >= 2020:
                        score += 30
                    elif year_num >= 2010:
                        score += 20
                    elif year_num >= 2000:
                        score += 10
                
                # Known academic publication boost
                publication = result.get('publication', '').lower()
                academic_terms = ['journal', 'proceedings', 'conference', 'review', 'research', 'nature', 'science']
                if any(term in publication for term in academic_terms):
                    score += 25
                
                return score
            
            # Sort by academic relevance or date
            if sort_by == 'date':
                search_results.sort(key=lambda x: x.get('date', '0'), reverse=True)
            else:
                search_results.sort(key=academic_relevance_score, reverse=True)
            
            search_results = search_results[:limit]
        
        # Build Google Scholar-style response with enhanced date search messaging
        date_search_performed = bool(year_start or year_end)
        
        # Determine search message based on date search type
        search_message = f'About {len(search_results)} results'
        if date_search_performed and not search_term:
            if year_start == year_end:
                search_message += f' from {year_start}'
            else:
                search_message += f' from {year_start} to {year_end}'
        elif search_term and date_search_performed:
            search_message += f' for "{search_term}"'
            if year_start == year_end:
                search_message += f' in {year_start}'
            else:
                search_message += f' ({year_start}-{year_end})'
        elif search_term:
            search_message += f' for "{search_term}"'
        
        response_data = {
            'success': True,
            'message': search_message,
            'query': {
                'q': search_term,
                'author': author,
                'publication': publication,
                'as_ylo': year_start,
                'as_yhi': year_end,
                'scisbd': sort_by,
                'fuzzy': fuzzy,
                'fuzzyThreshold': fuzzy_threshold if fuzzy else None
            },
            'searchInfo': {
                'searchType': 'academic',
                'sortBy': sort_by,
                'yearRange': f"{year_start}-{year_end}" if year_start or year_end else None,
                'searchFields': ['title', 'authors', 'publication', 'abstract', 'fulltext'],
                'fuzzySearchAvailable': FUZZY_SEARCH_AVAILABLE,
                'fuzzySearchUsed': fuzzy,
                'autoFuzzyTriggered': fallback_to_fuzzy or (fuzzy and fuzzy_explicit == ''),
                'totalScanned': len(items),
                'resultsReturned': len(search_results)
            },
            'results': search_results,
            'pagination': {
                'num': limit,
                'hasMore': response.get('LastEvaluatedKey') is not None if 'response' in locals() else False
            },
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