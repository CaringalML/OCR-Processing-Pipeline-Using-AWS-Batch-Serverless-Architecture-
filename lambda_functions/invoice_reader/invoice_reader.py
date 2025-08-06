#!/usr/bin/env python3
"""
Invoice Reader Lambda Function
==============================

Specialized Lambda function for reading and presenting processed invoice data
with enhanced formatting and invoice-specific field organization.

Features:
- Invoice-specific data presentation and formatting
- Enhanced structured data display
- Financial data validation and formatting
- Invoice status tracking and metadata
- Integration with CloudFront for file access
- Specialized filtering for invoice documents

Version: 1.0.0
Author: OCR Processing System
Updated: 2025-08-04
"""

import json
import os
import logging
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

def format_currency_amount(amount_str, currency='USD'):
    """Format currency amounts consistently"""
    if not amount_str:
        return None
    
    try:
        # Remove any existing currency symbols and whitespace
        clean_amount = str(amount_str).replace('$', '').replace(',', '').strip()
        amount = float(clean_amount)
        
        # Format with appropriate currency symbol
        currency_symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'AUD': 'A$',
            'CAD': 'C$',
            'NZD': 'NZ$'
        }
        
        symbol = currency_symbols.get(currency, currency + ' ')
        return f"{symbol}{amount:,.2f}"
    except (ValueError, TypeError):
        return amount_str

def format_date(date_str):
    """Format date string to DD MMM YYYY format (e.g., '15 Mar 2024')"""
    if not date_str or date_str.strip() == '':
        return ''
    
    # Common date formats to try parsing
    date_formats = [
        '%Y-%m-%d',      # 2024-03-15
        '%Y/%m/%d',      # 2024/03/15
        '%m/%d/%Y',      # 03/15/2024
        '%d/%m/%Y',      # 15/03/2024
        '%m-%d-%Y',      # 03-15-2024
        '%d-%m-%Y',      # 15-03-2024
        '%Y.%m.%d',      # 2024.03.15
        '%d.%m.%Y',      # 15.03.2024
        '%B %d, %Y',     # March 15, 2024
        '%d %B %Y',      # 15 March 2024
        '%b %d, %Y',     # Mar 15, 2024
        '%d %b %Y'       # 15 Mar 2024
    ]
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str.strip(), fmt)
            return parsed_date.strftime('%d %b %Y')  # Format as '15 Mar 2024'
        except ValueError:
            continue
    
    # If no format matches, return the original string
    return date_str

def format_invoice_data(structured_data, file_metadata):
    """Format comprehensive structured invoice data for presentation"""
    if not structured_data:
        return None
    
    # Extract currency information from new structure
    financial_summary = structured_data.get('financial_summary', {})
    currency_code = financial_summary.get('currency_code', 'USD')
    currency_symbol = financial_summary.get('currency_symbol', '$')
    
    formatted_invoice = {
        'businessInformation': {
            'extractionConfidence': f"{structured_data.get('business_info', {}).get('extraction_confidence', 0)}%",
            'businessName': structured_data.get('business_info', {}).get('business_name', ''),
            'tradingName': structured_data.get('business_info', {}).get('trading_name', ''),
            'addressLine1': structured_data.get('business_info', {}).get('address_line_1', ''),
            'addressLine2': structured_data.get('business_info', {}).get('address_line_2', ''),
            'city': structured_data.get('business_info', {}).get('city', ''),
            'stateProvince': structured_data.get('business_info', {}).get('state_province', ''),
            'postalCode': structured_data.get('business_info', {}).get('postal_code', ''),
            'country': structured_data.get('business_info', {}).get('country', ''),
            'fullAddress': structured_data.get('business_info', {}).get('full_address', ''),
            'phone': structured_data.get('business_info', {}).get('phone', ''),
            'email': structured_data.get('business_info', {}).get('email', ''),
            'website': structured_data.get('business_info', {}).get('website', ''),
            'taxId': structured_data.get('business_info', {}).get('tax_id', ''),
            'businessNumber': structured_data.get('business_info', {}).get('business_number', ''),
            'logoPresent': structured_data.get('business_info', {}).get('logo_present', False)
        },
        
        'clientInformation': {
            'extractionConfidence': f"{structured_data.get('client_info', {}).get('extraction_confidence', 0)}%",
            'clientName': structured_data.get('client_info', {}).get('client_name', ''),
            'contactPerson': structured_data.get('client_info', {}).get('contact_person', ''),
            'addressLine1': structured_data.get('client_info', {}).get('address_line_1', ''),
            'addressLine2': structured_data.get('client_info', {}).get('address_line_2', ''),
            'city': structured_data.get('client_info', {}).get('city', ''),
            'stateProvince': structured_data.get('client_info', {}).get('state_province', ''),
            'postalCode': structured_data.get('client_info', {}).get('postal_code', ''),
            'country': structured_data.get('client_info', {}).get('country', ''),
            'fullAddress': structured_data.get('client_info', {}).get('full_address', ''),
            'phone': structured_data.get('client_info', {}).get('phone', ''),
            'email': structured_data.get('client_info', {}).get('email', '')
        },
        
        'invoiceDetails': {
            'extractionConfidence': f"{structured_data.get('invoice_details', {}).get('extraction_confidence', 0)}%",
            'invoiceNumber': structured_data.get('invoice_details', {}).get('invoice_number', ''),
            'issueDate': format_date(structured_data.get('invoice_details', {}).get('issue_date', '')),
            'dueDate': format_date(structured_data.get('invoice_details', {}).get('due_date', '')),
            'referenceNumber': structured_data.get('invoice_details', {}).get('reference_number', ''),
            'purchaseOrder': structured_data.get('invoice_details', {}).get('purchase_order', ''),
            'customerId': structured_data.get('invoice_details', {}).get('customer_id', ''),
            'projectCode': structured_data.get('invoice_details', {}).get('project_code', ''),
            'invoiceType': structured_data.get('invoice_details', {}).get('invoice_type', 'standard')
        },
        
        'financialSummary': {
            'extractionConfidence': f"{financial_summary.get('extraction_confidence', 0)}%",
            'subtotal': format_currency_amount(financial_summary.get('subtotal', ''), currency_code),
            'discountAmount': format_currency_amount(financial_summary.get('discount_amount', ''), currency_code),
            'discountPercentage': financial_summary.get('discount_percentage', ''),
            'taxAmount': format_currency_amount(financial_summary.get('tax_amount', ''), currency_code),
            'taxRate': financial_summary.get('tax_rate', ''),
            'taxType': financial_summary.get('tax_type', ''),
            'shippingCost': format_currency_amount(financial_summary.get('shipping_cost', ''), currency_code),
            'otherCharges': format_currency_amount(financial_summary.get('other_charges', ''), currency_code),
            'totalBeforeTax': format_currency_amount(financial_summary.get('total_before_tax', ''), currency_code),
            'totalAmount': format_currency_amount(financial_summary.get('total_amount', ''), currency_code),
            'totalDue': format_currency_amount(financial_summary.get('total_due', ''), currency_code),
            'currencyCode': currency_code,
            'currencySymbol': currency_symbol
        },
        
        'lineItems': {
            'extractionConfidence': f"{structured_data.get('line_items', {}).get('extraction_confidence', 0)}%",
            'items': []
        },
        
        'paymentInformation': {
            'extractionConfidence': f"{structured_data.get('payment_info', {}).get('extraction_confidence', 0)}%",
            'paymentTerms': structured_data.get('payment_info', {}).get('payment_terms', ''),
            'paymentDueDays': structured_data.get('payment_info', {}).get('payment_due_days', ''),
            'paymentMethods': structured_data.get('payment_info', {}).get('payment_methods', ''),
            'bankName': structured_data.get('payment_info', {}).get('bank_name', ''),
            'accountNumber': structured_data.get('payment_info', {}).get('account_number', ''),
            'routingNumber': structured_data.get('payment_info', {}).get('routing_number', ''),
            'swiftCode': structured_data.get('payment_info', {}).get('swift_code', ''),
            'paymentReference': structured_data.get('payment_info', {}).get('payment_reference', '')
        },
        
        'additionalInformation': {
            'extractionConfidence': f"{structured_data.get('additional_info', {}).get('extraction_confidence', 0)}%",
            'notes': structured_data.get('additional_info', {}).get('notes', ''),
            'termsConditions': structured_data.get('additional_info', {}).get('terms_conditions', ''),
            'signaturePresent': structured_data.get('additional_info', {}).get('signature_present', False),
            'signatureText': structured_data.get('additional_info', {}).get('signature_text', ''),
            'authorizedBy': structured_data.get('additional_info', {}).get('authorized_by', ''),
            'documentFooter': structured_data.get('additional_info', {}).get('document_footer', ''),
            'watermarks': structured_data.get('additional_info', {}).get('watermarks', ''),
            'pageNumbers': structured_data.get('additional_info', {}).get('page_numbers', '')
        },
        
        'documentMetadata': {
            'extractionConfidence': f"{structured_data.get('document_metadata', {}).get('extraction_confidence', 0)}%",
            'detectedLanguage': structured_data.get('document_metadata', {}).get('detected_language', 'unknown'),
            'documentQuality': structured_data.get('document_metadata', {}).get('document_quality', 'unknown'),
            'fieldsExtractedCount': structured_data.get('document_metadata', {}).get('fields_extracted_count', 0),
            'missingFields': structured_data.get('document_metadata', {}).get('missing_fields', []),
            'dataValidationNotes': structured_data.get('document_metadata', {}).get('data_validation_notes', ''),
            'processingModel': 'claude-sonnet-4-20250514',
            'totalFieldsAvailable': len([k for k, v in structured_data.items() if v and k != 'raw_text'])
        },
        
        'processingCostDetails': {
            'totalCost': file_metadata.get('processing_cost', 0),
            'inputTokens': file_metadata.get('input_tokens', 0),
            'outputTokens': file_metadata.get('output_tokens', 0),
            'totalTokens': file_metadata.get('total_tokens', 0),
            'inputCost': file_metadata.get('input_cost', 0),
            'outputCost': file_metadata.get('output_cost', 0),
            'costPer1kInputTokens': file_metadata.get('cost_per_1k_input_tokens', 0),
            'costPer1kOutputTokens': file_metadata.get('cost_per_1k_output_tokens', 0),
            'ocrLlmProvider': file_metadata.get('ocr_llm_provider', 'Claude API'),
            'currency': 'USD'
        }
    }
    
    # Format enhanced line items with all details
    line_items_data = structured_data.get('line_items', {})
    # Handle both old format (direct array) and new format (with confidence and items array)
    if isinstance(line_items_data, list):
        # Old format - direct array of items
        items_array = line_items_data
    else:
        # New format - with confidence and items array
        items_array = line_items_data.get('items', [])
    
    for item in items_array:
        formatted_item = {
            'itemNumber': item.get('item_number', ''),
            'description': item.get('description', ''),
            'category': item.get('category', ''),
            'quantity': item.get('quantity', ''),
            'unitOfMeasure': item.get('unit_of_measure', ''),
            'unitPrice': format_currency_amount(item.get('unit_price', ''), currency_code),
            'lineTotal': format_currency_amount(item.get('line_total', ''), currency_code),
            'taxIncluded': item.get('tax_included', False),
            'discountApplied': item.get('discount_applied', '')
        }
        formatted_invoice['lineItems']['items'].append(formatted_item)
    
    
    return formatted_invoice

def lambda_handler(event, context):
    """
    Lambda function to read processed invoices from DynamoDB and generate CloudFront URLs
    Triggered by API Gateway GET requests to /short-batch/invoices/processed endpoint
    """
    
    # Initialize AWS clients
    dynamodb = boto3.resource('dynamodb')
    
    # Get configuration
    metadata_table_name = os.environ.get('METADATA_TABLE')
    results_table_name = os.environ.get('RESULTS_TABLE')
    cloudfront_domain = os.environ.get('CLOUDFRONT_DOMAIN')
    
    logger.info(f"Invoice reader configuration - METADATA_TABLE: {metadata_table_name}, RESULTS_TABLE: {results_table_name}, CLOUDFRONT_DOMAIN: {cloudfront_domain}")
    
    if not all([metadata_table_name, results_table_name, cloudfront_domain]):
        logger.error("Missing required environment variables")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Configuration Error',
                'message': 'Missing required environment variables',
                'debug': {
                    'METADATA_TABLE': metadata_table_name,
                    'RESULTS_TABLE': results_table_name,
                    'CLOUDFRONT_DOMAIN': cloudfront_domain
                }
            })
        }
    
    try:
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        status_filter = query_params.get('status', 'completed')  # Default to completed for invoices
        limit = int(query_params.get('limit', '50'))
        file_id = query_params.get('fileId')
        vendor_name = query_params.get('vendorName')
        invoice_number = query_params.get('invoiceNumber')
        date_from = query_params.get('dateFrom')
        date_to = query_params.get('dateTo')
        
        metadata_table = dynamodb.Table(metadata_table_name)
        results_table = dynamodb.Table(results_table_name)
        
        # If specific file_id is requested
        if file_id:
            # Get invoice metadata - handle composite key (invoice_id + upload_timestamp)
            # Since we don't know the upload_timestamp and there's no GSI for file_id alone,
            # we need to scan the table filtering by file_id
            logger.info(f"Searching for invoice with ID: {file_id}")
            
            try:
                # Try multiple approaches to find the record
                metadata_response = None
                
                # Approach 1: Scan with Attr (correct for FilterExpression)
                logger.info(f"Trying scan with FilterExpression for file_id: {file_id}")
                metadata_response = metadata_table.scan(
                    FilterExpression=Attr('file_id').eq(file_id),
                    Limit=10  # Get a few records in case there are multiple with different timestamps
                )
                
                if not metadata_response.get('Items'):
                    # Approach 2: Try query if there's a GSI we can use
                    logger.info(f"Scan found no items, trying query with all possible timestamp patterns")
                    
                    # If scan fails, let's try a broader scan to see what's actually in the table
                    logger.info("Attempting broader scan to debug table contents")
                    debug_response = metadata_table.scan(Limit=5)
                    if debug_response.get('Items'):
                        logger.info(f"DEBUG: Found {len(debug_response['Items'])} items in table")
                        for i, item in enumerate(debug_response['Items'][:2]):  # Log first 2 items
                            logger.info(f"DEBUG: Sample item {i}: file_id='{item.get('file_id')}', upload_timestamp='{item.get('upload_timestamp')}', keys={list(item.keys())}")
                    else:
                        logger.error("DEBUG: Table appears to be empty or inaccessible")
                
            except Exception as query_error:
                logger.error(f"Error during database query: {query_error}")
                metadata_response = {'Items': []}
            
            if not metadata_response['Items']:
                logger.error(f"Invoice {file_id} not found in database table {metadata_table_name}")
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Invoice Not Found',
                        'message': f'Invoice {file_id} not found in table {metadata_table_name}. Check logs for debug information.',
                        'debug': {
                            'searchedId': file_id,
                            'tableName': metadata_table_name,
                            'searchMethod': 'scan_with_filter'
                        }
                    })
                }
            
            file_metadata = decimal_to_json(metadata_response['Items'][0])
            logger.info(f"DEBUG: Raw file_metadata keys: {list(file_metadata.keys())}")
            logger.info(f"DEBUG: file_metadata values - original_filename: '{file_metadata.get('original_filename')}', file_name: '{file_metadata.get('file_name')}', file_size: '{file_metadata.get('file_size')}', content_type: '{file_metadata.get('content_type')}', s3_key: '{file_metadata.get('s3_key')}'")
            
            # Additional debugging for filename resolution
            resolved_filename = file_metadata.get('original_filename') or file_metadata.get('file_name') or 'Unknown'
            logger.info(f"DEBUG: Resolved filename: '{resolved_filename}' (original_filename: '{file_metadata.get('original_filename')}', file_name: '{file_metadata.get('file_name')}')")
            
            # Since we're using dedicated invoice tables, all records are invoices
            # No need to check processing_route
            
            # Generate CloudFront URL (following same pattern as working lambda_reader)
            s3_key = file_metadata.get('s3_key')
            if not s3_key:
                # Try alternative key name
                s3_key = file_metadata.get('s3Key')
            
            if not s3_key:
                # Generate fallback s3_key based on file extension
                file_extension = file_metadata.get('file_extension', 'unknown')
                if file_extension == 'unknown' and file_metadata.get('content_type'):
                    # Try to determine extension from content type
                    content_type = file_metadata.get('content_type', '')
                    if 'pdf' in content_type.lower():
                        file_extension = 'pdf'
                    elif 'png' in content_type.lower():
                        file_extension = 'png'
                    elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                        file_extension = 'jpg'
                
                s3_key = f"invoice-files/{file_id}.{file_extension}"
                logger.warning(f"No s3_key found for invoice: {file_id}, using fallback: {s3_key}")
            
            # Only generate CloudFront URL if we have a valid s3_key
            if s3_key:
                cloudfront_url = f"https://{cloudfront_domain}/{s3_key}"
                logger.info(f"Generated CloudFront URL for {file_id}: {cloudfront_url}")
            else:
                cloudfront_url = None
                logger.error(f"Unable to generate CloudFront URL for invoice {file_id}: no valid s3_key")
            
            # Calculate processing duration if available
            processing_duration = None
            if file_metadata.get('upload_timestamp') and file_metadata.get('processed_at'):
                try:
                    from datetime import datetime
                    upload_time = datetime.fromisoformat(file_metadata['upload_timestamp'].replace('Z', '+00:00'))
                    processed_time = datetime.fromisoformat(file_metadata['processed_at'].replace('Z', '+00:00'))
                    duration_seconds = (processed_time - upload_time).total_seconds()
                    processing_duration = f"{duration_seconds:.2f} seconds"
                except Exception as e:
                    logger.warning(f"Could not calculate processing duration: {e}")
                    processing_duration = "Unknown"
            
            # Build response data with improved field mapping
            response_data = {
                'fileId': file_id,
                'fileName': file_metadata.get('original_filename') or file_metadata.get('file_name') or 'Unknown',
                'uploadTimestamp': file_metadata.get('upload_timestamp', ''),
                'processingStatus': file_metadata.get('processing_status', ''),
                'fileSize': int(file_metadata.get('file_size', 0)),
                'contentType': file_metadata.get('content_type') or 'application/octet-stream',
                'cloudFrontUrl': cloudfront_url or '',
                'processingRoute': 'invoice-ocr',
                'processingType': 'specialized-invoice',
                'processingDuration': processing_duration,
                'overallConfidence': f"{file_metadata.get('extraction_confidence', 0)}%"
            }
            
            # Add invoice-specific OCR results
            if file_metadata.get('processing_status') == 'completed':
                structured_data = file_metadata.get('structured_invoice_data', {})
                
                if structured_data:
                    # Format the structured invoice data
                    formatted_invoice = format_invoice_data(structured_data, file_metadata)
                    
                    response_data['invoiceData'] = formatted_invoice
                    response_data['rawOcrText'] = file_metadata.get('raw_ocr_text', '')
                    response_data['processingMethod'] = file_metadata.get('processing_method', 'claude_invoice_ocr')
                    response_data['invoiceFieldsExtracted'] = file_metadata.get('invoice_fields_extracted', 0)
                    response_data['processedAt'] = file_metadata.get('processed_at', '')
                else:
                    response_data['invoiceData'] = None
                    response_data['message'] = 'Invoice processing completed but no structured data available'
            else:
                response_data['invoiceData'] = None
                response_data['message'] = f'Invoice processing status: {file_metadata.get("processing_status", "unknown")}'
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response_data)
            }
        
        else:
            # Query invoices with filters - using dedicated invoice table so no need for processing_route filter
            filter_expression = None
            
            # Add status filter
            if status_filter != 'all':
                filter_expression = Attr('processing_status').eq(status_filter)
            
            # Add vendor name filter (skip PENDING_OCR entries)
            if vendor_name:
                vendor_filter = Attr('vendor_name').contains(vendor_name) & Attr('vendor_name').ne('PENDING_OCR')
                if filter_expression:
                    filter_expression = filter_expression & vendor_filter
                else:
                    filter_expression = vendor_filter
            else:
                # Always exclude PENDING_OCR entries from general queries
                pending_filter = Attr('vendor_name').ne('PENDING_OCR')
                if filter_expression:
                    filter_expression = filter_expression & pending_filter
                else:
                    filter_expression = pending_filter
            
            # Add invoice number filter (skip PENDING_OCR entries)
            if invoice_number:
                invoice_filter = Attr('invoice_number').contains(invoice_number) & Attr('invoice_number').ne('PENDING_OCR')
                if filter_expression:
                    filter_expression = filter_expression & invoice_filter
                else:
                    filter_expression = invoice_filter
            
            # Scan for invoices (could be optimized with GSI for large datasets)
            if filter_expression:
                response = metadata_table.scan(
                    FilterExpression=filter_expression,
                    Limit=limit
                )
            else:
                response = metadata_table.scan(
                    Limit=limit
                )
            
            items = decimal_to_json(response.get('Items', []))
            
            # Debug logging for first item if available
            if items:
                logger.info(f"DEBUG: First item keys: {list(items[0].keys())}")
                logger.info(f"DEBUG: First item values - original_filename: '{items[0].get('original_filename')}', file_name: '{items[0].get('file_name')}', file_size: '{items[0].get('file_size')}', content_type: '{items[0].get('content_type')}', s3_key: '{items[0].get('s3_key')}'")
            
            # Sort by upload timestamp (most recent first)
            items.sort(key=lambda x: x.get('upload_timestamp', ''), reverse=True)
            
            # Format items for invoice presentation
            processed_invoices = []
            for item in items:
                # Generate CloudFront URL (following same pattern as working lambda_reader)
                s3_key = item.get('s3_key')
                if not s3_key:
                    # Try alternative key name
                    s3_key = item.get('s3Key')
                
                if not s3_key:
                    # Generate fallback s3_key based on file extension
                    file_extension = item.get('file_extension', 'unknown')
                    if file_extension == 'unknown' and item.get('content_type'):
                        # Try to determine extension from content type
                        content_type = item.get('content_type', '')
                        if 'pdf' in content_type.lower():
                            file_extension = 'pdf'
                        elif 'png' in content_type.lower():
                            file_extension = 'png'
                        elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                            file_extension = 'jpg'
                    
                    file_id = item.get('file_id', 'unknown')
                    s3_key = f"invoice-files/{file_id}.{file_extension}"
                    logger.warning(f"No s3_key found for file: {file_id}, using fallback: {s3_key}")
                
                # Only generate CloudFront URL if we have a valid s3_key
                if s3_key:
                    cloudfront_url = f"https://{cloudfront_domain}/{s3_key}"
                else:
                    cloudfront_url = None
                    logger.error(f"Unable to generate CloudFront URL for file {file_id}: no valid s3_key")
                
                # Calculate processing duration if available
                processing_duration = None
                if item.get('upload_timestamp') and item.get('processed_at'):
                    try:
                        from datetime import datetime
                        upload_time = datetime.fromisoformat(item['upload_timestamp'].replace('Z', '+00:00'))
                        processed_time = datetime.fromisoformat(item['processed_at'].replace('Z', '+00:00'))
                        duration_seconds = (processed_time - upload_time).total_seconds()
                        processing_duration = f"{duration_seconds:.2f} seconds"
                    except Exception as e:
                        logger.warning(f"Could not calculate processing duration: {e}")
                        processing_duration = "Unknown"
                
                # Build invoice summary data with improved field mapping
                invoice_summary = {
                    'fileId': item['file_id'],
                    'fileName': item.get('original_filename') or item.get('file_name') or 'Unknown',
                    'uploadTimestamp': item.get('upload_timestamp', ''),
                    'processingStatus': item.get('processing_status', ''),
                    'fileSize': int(item.get('file_size', 0)),
                    'contentType': item.get('content_type') or 'application/octet-stream',
                    'cloudFrontUrl': cloudfront_url or '',
                    'processingDuration': processing_duration,
                    'overallConfidence': f"{item.get('extraction_confidence', 0)}%",
                    
                    # Invoice-specific summary fields (OCR-extracted or pending)
                    'vendorName': item.get('vendor_name', '') if item.get('vendor_name') != 'PENDING_OCR' else 'Processing...',
                    'invoiceNumber': item.get('invoice_number', '') if item.get('invoice_number') != 'PENDING_OCR' else 'Processing...',
                    'invoiceDate': item.get('invoice_date', '') if item.get('invoice_date') != 'PENDING_OCR' else 'Processing...',
                    'totalAmount': item.get('total_amount', ''),
                    'currency': item.get('currency', 'USD'),
                    'invoiceType': item.get('invoice_type', 'standard'),
                    'businessCategory': item.get('business_category', ''),
                    'processingPriority': item.get('processing_priority', 'normal'),
                    'invoiceFieldsExtracted': item.get('invoice_fields_extracted', 0),
                    'processedAt': item.get('processed_at', ''),
                    'processingCost': item.get('processing_cost', 0)
                }
                
                # Format total amount with currency
                if invoice_summary['totalAmount']:
                    invoice_summary['formattedTotal'] = format_currency_amount(
                        invoice_summary['totalAmount'], 
                        invoice_summary['currency']
                    )
                
                processed_invoices.append(invoice_summary)
            
            response_data = {
                'invoices': processed_invoices,
                'count': len(processed_invoices),
                'hasMore': response.get('LastEvaluatedKey') is not None,
                'filters': {
                    'status': status_filter,
                    'vendorName': vendor_name,
                    'invoiceNumber': invoice_number,
                    'dateFrom': date_from,
                    'dateTo': date_to
                },
                'processingType': 'invoice-ocr'
            }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(response_data)
            }
        
    except KeyError as e:
        logger.error(f"KeyError in invoice reader: {str(e)}")
        logger.error(f"Available fields in record: {list(items[0].keys()) if 'items' in locals() and items else 'No items found'}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Missing Field Error',
                'message': f'Required field missing: {str(e)}',
                'debug': 'Check Lambda logs for available fields'
            })
        }
    except Exception as e:
        logger.error(f"ERROR in invoice reader: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e),
                'error_type': type(e).__name__
            })
        }