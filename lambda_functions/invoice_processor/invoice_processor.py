#!/usr/bin/env python3
"""
Invoice OCR Processing Pipeline - Lambda Function
===============================================

Specialized Lambda function for OCR processing of invoices using Claude AI 
with enhanced prompts for structured invoice data extraction.

Features:
- Invoice-specific OCR prompts for structured data extraction
- Enhanced field recognition (vendor, amounts, dates, line items)
- Invoice validation and quality assessment
- JSON structured output for invoice fields
- Integration with DynamoDB for invoice metadata storage
- Budget management and cost tracking

Version: 1.0.0
Author: OCR Processing System
Updated: 2025-08-04
"""

import json
import os
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from collections.abc import Mapping
import base64
from decimal import Decimal
import re
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables with validation
DOCUMENTS_TABLE = os.environ.get('DOCUMENTS_TABLE')
PROCESSED_BUCKET = os.environ.get('PROCESSED_BUCKET')
DEAD_LETTER_QUEUE_URL = os.environ.get('DEAD_LETTER_QUEUE_URL')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
BUDGET_LIMIT = float(os.environ.get('BUDGET_LIMIT', '10.0'))

# Claude 4 model configuration
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Claude Sonnet 4 model

# Initialize AWS clients (lazy loading)
_aws_clients = {}

def get_aws_client(service_name: str):
    """Get or create AWS client with caching"""
    if service_name not in _aws_clients:
        if service_name == 'dynamodb':
            _aws_clients[service_name] = boto3.resource(service_name)
        else:
            _aws_clients[service_name] = boto3.client(service_name)
    return _aws_clients[service_name]

# Initialize Claude client with lazy loading
_anthropic_client = None

def get_anthropic_client():
    """Get or create Anthropic client with proper error handling"""
    global _anthropic_client
    
    if _anthropic_client is None:
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            logger.info("Anthropic client initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import anthropic module: {e}")
            raise RuntimeError(
                "Anthropic module not available. Ensure the package is installed "
                "or use a Lambda Layer with anthropic dependencies."
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {e}")
            raise RuntimeError(f"Anthropic client initialization failed: {e}") from e
    
    return _anthropic_client

# Budget tracking - Updated for Claude 4 pricing
COST_PER_1K_TOKENS = {
    'input': 0.003,  # $3 per million input tokens
    'output': 0.015  # $15 per million output tokens
}

def get_current_budget_usage() -> float:
    """Get current budget usage from DynamoDB"""
    try:
        # Use environment variable for budget tracking table
        budget_table = os.environ.get('BUDGET_TRACKING_TABLE', 'ocr_budget_tracking')
        
        dynamodb = get_aws_client('dynamodb')
        table = dynamodb.Table(budget_table)
        response = table.get_item(Key={'id': 'current_month'})
        
        if 'Item' in response:
            return float(response['Item'].get('total_cost', 0))
        return 0.0
    except Exception as e:
        logger.warning(f"Failed to get budget usage: {e}")
        return 0.0

def update_budget_usage(cost: float) -> None:
    """Update budget usage in DynamoDB"""
    try:
        # Use environment variable for budget tracking table
        budget_table = os.environ.get('BUDGET_TRACKING_TABLE', 'ocr_budget_tracking')
        
        dynamodb = get_aws_client('dynamodb')
        table = dynamodb.Table(budget_table)
        table.update_item(
            Key={'id': 'current_month'},
            UpdateExpression='ADD total_cost :cost',
            ExpressionAttributeValues={':cost': Decimal(str(cost))}
        )
    except Exception as e:
        logger.error(f"Failed to update budget usage: {e}")

def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost based on token usage"""
    input_cost = (input_tokens / 1000) * COST_PER_1K_TOKENS['input']
    output_cost = (output_tokens / 1000) * COST_PER_1K_TOKENS['output']
    return input_cost + output_cost

def send_budget_alert(message: str) -> None:
    """Send SNS notification for budget alerts"""
    try:
        if not SNS_TOPIC_ARN:
            logger.warning("SNS_TOPIC_ARN not configured")
            return
            
        sns_client = get_aws_client('sns')
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='Invoice OCR Budget Alert',
            Message=message
        )
        logger.info(f"Budget alert sent: {message}")
    except Exception as e:
        logger.error(f"Failed to send budget alert: {e}")

def get_media_type_for_claude(file_extension: str, content_type: str = None) -> str:
    """Determine the appropriate media type for Claude API based on file extension"""
    file_extension = file_extension.lower()
    
    # Handle images
    image_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg', 
        'png': 'image/png',
        'webp': 'image/webp'
    }
    
    if file_extension in image_types:
        return image_types[file_extension]
    
    # Handle documents - Claude can process these as images for OCR
    document_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain',
        'rtf': 'application/rtf'
    }
    
    if file_extension in document_types:
        return document_types[file_extension]
    
    # Default to image/jpeg for unknown types
    return 'image/jpeg'

def parse_invoice_data(claude_response: str) -> dict:
    """Parse structured invoice data from Claude's response"""
    invoice_data = {
        'vendor_info': {},
        'invoice_details': {},
        'amounts': {},
        'line_items': [],
        'payment_info': {},
        'raw_text': '',
        'extraction_confidence': 'unknown'
    }
    
    if "---STRUCTURED_DATA---" in claude_response:
        parts = claude_response.split("---STRUCTURED_DATA---")
        invoice_data['raw_text'] = parts[0].strip()
        
        if len(parts) > 1:
            structured_section = parts[1].strip()
            
            # Parse structured data (expecting JSON format)
            try:
                # Look for JSON block
                json_start = structured_section.find('{')
                json_end = structured_section.rfind('}')
                
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    json_str = structured_section[json_start:json_end+1]
                    parsed_data = json.loads(json_str)
                    
                    # Update invoice_data with parsed JSON
                    invoice_data.update(parsed_data)
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON structure from Claude response: {e}")
                # Fall back to text parsing
                lines = structured_section.split('\n')
                current_section = None
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('Vendor:'):
                        invoice_data['vendor_info']['name'] = line.replace('Vendor:', '').strip()
                    elif line.startswith('Invoice Number:'):
                        invoice_data['invoice_details']['number'] = line.replace('Invoice Number:', '').strip()
                    elif line.startswith('Date:'):
                        invoice_data['invoice_details']['date'] = line.replace('Date:', '').strip()
                    elif line.startswith('Total:'):
                        invoice_data['amounts']['total'] = line.replace('Total:', '').strip()
                    elif line.startswith('Tax:'):
                        invoice_data['amounts']['tax'] = line.replace('Tax:', '').strip()
                    elif line.startswith('Subtotal:'):
                        invoice_data['amounts']['subtotal'] = line.replace('Subtotal:', '').strip()
    else:
        invoice_data['raw_text'] = claude_response
    
    return invoice_data

def process_invoice_with_claude_ocr(document_bytes: bytes, document_id: str, content_type: str = None, upload_timestamp: str = None) -> dict[str, Any]:
    """Process invoice document using Claude AI for structured OCR"""
    try:
        # Check budget before processing
        current_usage = get_current_budget_usage()
        if current_usage >= BUDGET_LIMIT:
            raise Exception(f"Budget limit exceeded: ${current_usage:.2f} >= ${BUDGET_LIMIT:.2f}")
        
        # Get Anthropic client
        anthropic_client = get_anthropic_client()
        
        # Determine document type and media type
        file_extension = document_id.split('.')[-1].lower() if '.' in document_id else 'unknown'
        
        if file_extension == 'unknown' or file_extension == document_id.lower():
            if content_type:
                if 'jpeg' in content_type:
                    file_extension = 'jpeg'
                elif 'png' in content_type:
                    file_extension = 'png'
                elif 'pdf' in content_type:
                    file_extension = 'pdf'
        
        media_type = get_media_type_for_claude(file_extension, content_type)
        
        logger.info(f"Processing {file_extension} invoice with Claude OCR (media_type: {media_type})")
        
        # Encode document to base64
        document_base64 = base64.b64encode(document_bytes).decode('utf-8')
        
        start_time = time.time()
        
        # Call Claude API with invoice-specific OCR prompt
        ocr_response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16384,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": document_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": f"""Extract ALL information from this INVOICE document with comprehensive structured data extraction:

INVOICE OCR EXTRACTION REQUIREMENTS:
1. Extract the complete text content exactly as it appears
2. Identify and extract ALL invoice fields with maximum detail
3. Preserve proper formatting for addresses, line items, and amounts
4. Maintain exact spacing and alignment for tabular data
5. Keep all numbers, dates, and reference codes intact
6. Extract header information, client details, and signature areas
7. Identify logos, watermarks, and visual elements

COMPREHENSIVE FIELD IDENTIFICATION:
- Business/Vendor information (name, address, contact details, logo presence)
- Client/Customer information (bill-to details)
- Invoice metadata (number, dates, references, status)
- Detailed line items with descriptions, quantities, unit prices, amounts
- Financial summary (subtotals, taxes, discounts, totals)
- Payment information (terms, methods, bank details)
- Additional notes, terms, and signature areas
- Document formatting and visual elements

After extracting the complete text, provide comprehensive structured data:

---STRUCTURED_DATA---
{{
  "business_info": {{
    "extraction_confidence": "[0-100]",
    "business_name": "[Full Business/Company Name]",
    "trading_name": "[Trading/Brand Name if different]",
    "address_line_1": "[Street Address]",
    "address_line_2": "[Suite/Unit if present]", 
    "city": "[City]",
    "state_province": "[State/Province]",
    "postal_code": "[ZIP/Postal Code]",
    "country": "[Country]",
    "full_address": "[Complete formatted address]",
    "phone": "[Phone Number]",
    "email": "[Email Address]",
    "website": "[Website if present]",
    "tax_id": "[Tax ID/ABN/VAT Number]",
    "business_number": "[Business Registration Number]",
    "logo_present": true/false
  }},
  "client_info": {{
    "extraction_confidence": "[0-100]",
    "client_name": "[Client/Customer Name]",
    "contact_person": "[Contact Person if specified]",
    "address_line_1": "[Client Street Address]",
    "address_line_2": "[Client Suite/Unit if present]",
    "city": "[Client City]", 
    "state_province": "[Client State/Province]",
    "postal_code": "[Client ZIP/Postal Code]",
    "country": "[Client Country]",
    "full_address": "[Complete client address]",
    "phone": "[Client Phone]",
    "email": "[Client Email]"
  }},
  "invoice_details": {{
    "extraction_confidence": "[0-100]",
    "invoice_number": "[Invoice Number]",
    "issue_date": "[Issue/Invoice Date]",
    "due_date": "[Due Date]",
    "reference_number": "[Reference Number]",
    "purchase_order": "[PO Number if present]",
    "customer_id": "[Customer ID if present]",
    "project_code": "[Project Code if present]",
    "invoice_type": "standard|credit_note|receipt|proforma|estimate"
  }},
  "financial_summary": {{
    "extraction_confidence": "[0-100]",
    "subtotal": "[Subtotal Amount]",
    "discount_amount": "[Discount Amount if present]",
    "discount_percentage": "[Discount % if present]",
    "tax_amount": "[Tax Amount]",
    "tax_rate": "[Tax Rate %]",
    "tax_type": "[Tax Type: GST/VAT/Sales Tax]",
    "shipping_cost": "[Shipping/Delivery Cost if present]",
    "other_charges": "[Other Charges if present]",
    "total_before_tax": "[Total before tax]",
    "total_amount": "[Final Total Amount]",
    "total_due": "[Total Due Amount]",
    "currency_code": "[Currency Code: USD/NZD/AUD etc]",
    "currency_symbol": "[Currency Symbol: $/£/€ etc]"
  }},
  "line_items": {{
    "extraction_confidence": "[0-100]",
    "items": [
      {{
        "item_number": "[Item/SKU Number if present]",
        "description": "[Full Item Description]",
        "category": "[Item Category if specified]",
        "quantity": "[Quantity]",
        "unit_of_measure": "[Unit: hours/pieces/kg etc]",
        "unit_price": "[Unit Price]",
        "line_total": "[Line Total Amount]",
        "tax_included": true/false,
        "discount_applied": "[Line discount if present]"
      }}
    ]
  }},
  "payment_info": {{
    "extraction_confidence": "[0-100]",
    "payment_terms": "[Payment Terms]",
    "payment_due_days": "[Days until due]",
    "payment_methods": "[Accepted payment methods]",
    "bank_name": "[Bank Name if present]",
    "account_number": "[Account Number if present]",
    "routing_number": "[Routing/Sort Code if present]",
    "swift_code": "[SWIFT/BIC Code if present]",
    "payment_reference": "[Payment Reference if specified]"
  }},
  "additional_info": {{
    "extraction_confidence": "[0-100]",
    "notes": "[Additional notes or terms]",
    "terms_conditions": "[Terms and conditions text]",
    "signature_present": true/false,
    "signature_text": "[Signature line text]",
    "authorized_by": "[Authorized by information]",
    "document_footer": "[Footer text]",
    "watermarks": "[Watermark text if present]",
    "page_numbers": "[Page numbering if multi-page]"
  }},
  "document_metadata": {{
    "extraction_confidence": "[0-100]",
    "detected_language": "[Primary language]",
    "document_quality": "excellent|good|fair|poor",
    "fields_extracted_count": "[Number of fields successfully extracted]",
    "missing_fields": "[List of standard fields not found]",
    "data_validation_notes": "[Any data validation concerns]"
  }}
}}

CONFIDENCE SCORING GUIDELINES:
- extraction_confidence should be a number from 0-100 representing percentage confidence
- Apply confidence scoring to EACH SECTION based on field clarity and completeness
- 90-100%: All key fields clearly visible and extracted with high certainty
- 80-89%: Most fields extracted successfully, minor uncertainty on some values
- 70-79%: Good extraction but some fields unclear or missing
- 60-69%: Moderate extraction quality, several fields uncertain or missing
- 50-59%: Fair extraction, document readable but many fields problematic
- 30-49%: Poor extraction, document quality issues affecting readability
- 0-29%: Very poor extraction, document barely readable or heavily corrupted

SECTION-SPECIFIC CONFIDENCE:
- business_info: Rate based on company name, address, contact details clarity
- client_info: Rate based on customer details visibility and completeness
- invoice_details: Rate based on invoice number, dates, and reference data clarity
- financial_summary: Rate based on amounts, taxes, and calculations visibility
- line_items: Rate based on item descriptions, quantities, and prices clarity
- payment_info: Rate based on payment terms and banking details visibility
- additional_info: Rate based on notes, terms, and signature area clarity
- document_metadata: Overall document quality and extraction success rate

ENHANCED QUALITY REQUIREMENTS:
- Extract all monetary amounts with exact formatting and currency symbols
- Preserve date formats exactly as shown (MM/DD/YYYY, DD/MM/YYYY etc)
- Maintain proper capitalization for names and addresses
- Identify and extract table structures precisely
- Note any calculation discrepancies or missing totals
- Preserve special characters and formatting in descriptions
- Extract all visible text including headers, footers, and watermarks
- Identify visual elements like logos and signature areas"""
                        }
                    ]
                }
            ]
        )
        
        # Parse the response
        raw_response = ocr_response.content[0].text
        invoice_data = parse_invoice_data(raw_response)
        
        # Extract basic text (formattedText equivalent)
        formatted_text = invoice_data['raw_text']
        
        # For invoices, the "refined" text is the structured JSON data
        refined_text = json.dumps(invoice_data, indent=2)
        
        ocr_input_tokens = ocr_response.usage.input_tokens
        ocr_output_tokens = ocr_response.usage.output_tokens
        
        processing_time = time.time() - start_time
        
        logger.info(f"Invoice OCR completed. Text length: {len(formatted_text)} characters")
        logger.info(f"Structured data extracted: {len(invoice_data)} fields")
        
        # Calculate detailed cost breakdown
        input_cost = (ocr_input_tokens / 1000) * COST_PER_1K_TOKENS['input']
        output_cost = (ocr_output_tokens / 1000) * COST_PER_1K_TOKENS['output']
        total_cost = input_cost + output_cost
        
        # Update budget usage
        update_budget_usage(total_cost)
        
        # Check if we're approaching budget limit
        new_usage = current_usage + total_cost
        if new_usage >= BUDGET_LIMIT * 0.9:  # 90% threshold
            percentage = (new_usage / BUDGET_LIMIT) * 100
            send_budget_alert(f"Invoice OCR budget is at {percentage:.1f}% of limit (${new_usage:.2f}/${BUDGET_LIMIT:.2f})")
        
        return {
            'success': True,
            'formatted_text': formatted_text,
            'refined_text': refined_text,
            'structured_data': invoice_data,
            'processing_time': processing_time,
            'input_tokens': ocr_input_tokens,
            'output_tokens': ocr_output_tokens,
            'total_tokens': ocr_input_tokens + ocr_output_tokens,
            'cost': total_cost,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'cost_per_1k_input_tokens': COST_PER_1K_TOKENS['input'],
            'cost_per_1k_output_tokens': COST_PER_1K_TOKENS['output'],
            'model': CLAUDE_MODEL,
            'ocr_llm_provider': 'Claude API',
            'processing_method': 'claude_invoice_ocr',
            'file_type': file_extension,
            'media_type': media_type,
            'extraction_confidence': invoice_data.get('document_metadata', {}).get('extraction_confidence', 0),
            'invoice_fields_extracted': len([k for k, v in invoice_data.items() if v and k != 'raw_text'])
        }
        
    except Exception as e:
        logger.error(f"Invoice OCR error: {e}")
        return {
            'success': False,
            'error': str(e),
            'formatted_text': '',
            'refined_text': '',
            'structured_data': {},
            'file_type': file_extension if 'file_extension' in locals() else 'unknown'
        }

def process_invoice(message: dict[str, Any]) -> dict[str, Any]:
    """Process a single invoice using Claude AI OCR"""
    bucket = message.get('bucket')
    key = message.get('key')
    document_id = message.get('document_id')
    upload_timestamp = message.get('upload_timestamp')
    
    if not all([bucket, key, document_id, upload_timestamp]):
        raise ValueError("Missing required fields: bucket, key, document_id, or upload_timestamp")
        
    logger.info(f"DEBUG: Processing invoice with document_id: '{document_id}', upload_timestamp: '{upload_timestamp}'")
    
    try:
        # Update status to downloading
        if DOCUMENTS_TABLE:
            dynamodb = get_aws_client('dynamodb')
            table = dynamodb.Table(DOCUMENTS_TABLE)
            table.update_item(
                Key={'file_id': document_id, 'upload_timestamp': upload_timestamp},
                UpdateExpression='SET processing_status = :status',
                ExpressionAttributeValues={':status': 'downloading_invoice'}
            )
        
        # Download invoice from S3
        logger.info(f"Downloading invoice from S3: {bucket}/{key}")
        s3_client = get_aws_client('s3')
        response = s3_client.get_object(Bucket=bucket, Key=key)
        document_bytes = response['Body'].read()
        content_type = response.get('ContentType', '')
        
        logger.info(f"Invoice downloaded. Size: {len(document_bytes)} bytes, Content-Type: {content_type}")
        
        # Update status to processing
        if DOCUMENTS_TABLE:
            table.update_item(
                Key={'file_id': document_id, 'upload_timestamp': upload_timestamp},
                UpdateExpression='SET processing_status = :status',
                ExpressionAttributeValues={':status': 'processing_invoice_ocr'}
            )
        
        # Process with Claude Invoice OCR
        logger.info(f"Processing invoice with Claude AI OCR")
        ocr_result = process_invoice_with_claude_ocr(document_bytes, document_id, content_type, upload_timestamp)
        
        if not ocr_result['success']:
            # Check if it's a budget issue
            if 'budget limit exceeded' in ocr_result.get('error', '').lower():
                raise Exception(ocr_result['error'])
            else:
                raise Exception(f"Invoice OCR processing failed: {ocr_result.get('error', 'Unknown error')}")
        
        # Prepare result with enhanced cost details
        result = {
            'document_id': document_id,
            'upload_timestamp': upload_timestamp,
            'bucket': bucket,
            'key': key,
            'formatted_text': ocr_result['formatted_text'],
            'refined_text': ocr_result['refined_text'],
            'structured_data': ocr_result['structured_data'],
            'processing_time': ocr_result['processing_time'],
            'input_tokens': ocr_result['input_tokens'],
            'output_tokens': ocr_result['output_tokens'],
            'total_tokens': ocr_result['total_tokens'],
            'cost': ocr_result['cost'],
            'input_cost': ocr_result['input_cost'],
            'output_cost': ocr_result['output_cost'],
            'cost_per_1k_input_tokens': ocr_result['cost_per_1k_input_tokens'],
            'cost_per_1k_output_tokens': ocr_result['cost_per_1k_output_tokens'],
            'model': ocr_result['model'],
            'ocr_llm_provider': ocr_result['ocr_llm_provider'],
            'processing_method': ocr_result.get('processing_method', 'claude_invoice_ocr'),
            'file_type': ocr_result.get('file_type', 'unknown'),
            'media_type': ocr_result.get('media_type', 'unknown'),
            'extraction_confidence': ocr_result.get('extraction_confidence', 'unknown'),
            'invoice_fields_extracted': ocr_result.get('invoice_fields_extracted', 0),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Update status to saving results
        if DOCUMENTS_TABLE:
            table.update_item(
                Key={'file_id': document_id, 'upload_timestamp': upload_timestamp},
                UpdateExpression='SET processing_status = :status',
                ExpressionAttributeValues={':status': 'saving_invoice_results'}
            )
        
        # Save to processed bucket in invoice-files folder
        if PROCESSED_BUCKET:
            processed_key = f"invoice-files/processed/{document_id}_invoice_ocr.json"
            s3_client.put_object(
                Bucket=PROCESSED_BUCKET,
                Key=processed_key,
                Body=json.dumps(result, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Invoice result saved to S3: {processed_key}")
        
        # Update DynamoDB with final results including OCR-extracted metadata
        if DOCUMENTS_TABLE:
            # First, get the current record to debug what's there
            try:
                dynamodb = get_aws_client('dynamodb')
                table = dynamodb.Table(DOCUMENTS_TABLE)
                
                # Get existing record to debug
                existing_response = table.get_item(
                    Key={'file_id': document_id, 'upload_timestamp': upload_timestamp}
                )
                
                if existing_response.get('Item'):
                    existing_item = existing_response['Item']
                    logger.info(f"DEBUG: Existing record keys: {list(existing_item.keys())}")
                    logger.info(f"DEBUG: Existing record - original_filename: '{existing_item.get('original_filename')}', file_name: '{existing_item.get('file_name')}', file_size: '{existing_item.get('file_size')}', content_type: '{existing_item.get('content_type')}', s3_key: '{existing_item.get('s3_key')}'")
                else:
                    logger.error(f"DEBUG: No existing record found for file_id: {document_id}, upload_timestamp: {upload_timestamp}")
                    
            except Exception as debug_error:
                logger.error(f"DEBUG: Failed to get existing record: {debug_error}")
            
            # Extract key fields from OCR results for indexing
            structured_data = ocr_result['structured_data']
            business_info = structured_data.get('business_info', {})
            client_info = structured_data.get('client_info', {})
            invoice_details = structured_data.get('invoice_details', {})
            financial_summary = structured_data.get('financial_summary', {})
            
            # Prepare update expression with OCR-extracted metadata and enhanced cost details
            update_expression = 'SET processing_status = :status, raw_ocr_text = :raw_text, refined_ocr_text = :refined_text, structured_invoice_data = :structured, processed_at = :timestamp, processing_cost = :cost, input_tokens = :input_tokens, output_tokens = :output_tokens, total_tokens = :total_tokens, input_cost = :input_cost, output_cost = :output_cost, cost_per_1k_input_tokens = :cost_per_1k_input, cost_per_1k_output_tokens = :cost_per_1k_output, ocr_llm_provider = :llm_provider, processing_method = :method, file_type = :file_type, extraction_confidence = :confidence, invoice_fields_extracted = :fields_count'
            
            expression_values = {
                ':status': 'completed',
                ':raw_text': ocr_result['formatted_text'],
                ':refined_text': ocr_result['refined_text'],
                ':structured': ocr_result['structured_data'],
                ':timestamp': result['timestamp'],
                ':cost': Decimal(str(ocr_result['cost'])),
                ':input_tokens': ocr_result['input_tokens'],
                ':output_tokens': ocr_result['output_tokens'],
                ':total_tokens': ocr_result['total_tokens'],
                ':input_cost': Decimal(str(ocr_result['input_cost'])),
                ':output_cost': Decimal(str(ocr_result['output_cost'])),
                ':cost_per_1k_input': Decimal(str(ocr_result['cost_per_1k_input_tokens'])),
                ':cost_per_1k_output': Decimal(str(ocr_result['cost_per_1k_output_tokens'])),
                ':llm_provider': ocr_result['ocr_llm_provider'],
                ':method': ocr_result.get('processing_method', 'claude_invoice_ocr'),
                ':file_type': ocr_result.get('file_type', 'unknown'),
                ':confidence': ocr_result.get('structured_data', {}).get('document_metadata', {}).get('extraction_confidence', 0),
                ':fields_count': ocr_result.get('invoice_fields_extracted', 0)
            }
            
            # Add OCR-extracted fields for DynamoDB indexing
            if business_info.get('business_name'):
                update_expression += ', vendor_name = :vendor_name'
                expression_values[':vendor_name'] = business_info.get('business_name', 'Unknown')
            
            if invoice_details.get('invoice_number'):
                update_expression += ', invoice_number = :invoice_number'
                expression_values[':invoice_number'] = invoice_details.get('invoice_number', 'Unknown')
                
            if invoice_details.get('issue_date'):
                update_expression += ', invoice_date = :invoice_date'
                expression_values[':invoice_date'] = invoice_details.get('issue_date', 'Unknown')
                
            if invoice_details.get('due_date'):
                update_expression += ', due_date = :due_date'
                expression_values[':due_date'] = invoice_details.get('due_date', '')
                
            if financial_summary.get('total_amount'):
                update_expression += ', total_amount = :total_amount'
                expression_values[':total_amount'] = financial_summary.get('total_amount', '')
                
            if financial_summary.get('currency_code'):
                update_expression += ', currency = :currency'
                expression_values[':currency'] = financial_summary.get('currency_code', 'USD')
            
            table.update_item(
                Key={
                    'file_id': document_id,
                    'upload_timestamp': upload_timestamp
                },
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            logger.info(f"DynamoDB updated for invoice: {document_id}")
            
            # Debug: Get the record again after update to see what happened
            try:
                updated_response = table.get_item(
                    Key={'file_id': document_id, 'upload_timestamp': upload_timestamp}
                )
                
                if updated_response.get('Item'):
                    updated_item = updated_response['Item']
                    logger.info(f"DEBUG: After update record keys: {list(updated_item.keys())}")
                    logger.info(f"DEBUG: After update - original_filename: '{updated_item.get('original_filename')}', file_name: '{updated_item.get('file_name')}', file_size: '{updated_item.get('file_size')}', content_type: '{updated_item.get('content_type')}', s3_key: '{updated_item.get('s3_key')}'")
                else:
                    logger.error(f"DEBUG: No record found after update for file_id: {document_id}")
                    
            except Exception as after_debug_error:
                logger.error(f"DEBUG: Failed to get record after update: {after_debug_error}")
        
        logger.info(f"Successfully processed invoice: {document_id} using Claude AI OCR")
        return result
        
    except Exception as e:
        logger.error(f"Error processing invoice {document_id}: {e}")
        
        # Update DynamoDB with error status
        try:
            if DOCUMENTS_TABLE:
                dynamodb = get_aws_client('dynamodb')
                table = dynamodb.Table(DOCUMENTS_TABLE)
                table.update_item(
                    Key={
                        'file_id': document_id,
                        'upload_timestamp': upload_timestamp
                    },
                    UpdateExpression='SET processing_status = :status, error_message = :error',
                    ExpressionAttributeValues={
                        ':status': 'failed',
                        ':error': str(e)[:500]
                    }
                )
        except Exception as db_error:
            logger.error(f"Failed to update DynamoDB: {db_error}")
        
        raise

def lambda_handler(event, context):
    """Main Lambda handler for Invoice OCR processing"""
    logger.info(f"Invoice OCR Lambda Handler Started")
    logger.info(f"Function: {context.function_name if context else 'Local'}")
    logger.info(f"Request ID: {context.aws_request_id if context else 'N/A'}")
    logger.info(f"Using Claude Model: {CLAUDE_MODEL}")
    
    # Validate environment
    if not ANTHROPIC_API_KEY:
        error_msg = "ANTHROPIC_API_KEY environment variable is not set"
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }
    
    # Process records
    logger.info(f"Processing {len(event.get('Records', []))} invoice records with Claude AI OCR")
    
    results = []
    errors = []
    
    for record in event.get('Records', []):
        try:
            # Parse SQS message
            logger.info(f"Raw SQS record: {record}")
            message_body = json.loads(record['body'])
            logger.info(f"Parsed message body: {message_body}")
            
            # Extract metadata from the message
            metadata = message_body.get('metadata', {})
            
            # Map the actual message format to expected format
            mapped_message = {
                'bucket': metadata.get('s3_bucket') or metadata.get('bucket_name'),
                'key': metadata.get('s3_key'),
                'document_id': message_body.get('fileId') or metadata.get('file_id'),
                'upload_timestamp': metadata.get('upload_timestamp') or message_body.get('timestamp'),
                'original_filename': metadata.get('original_filename'),
                'content_type': metadata.get('content_type'),
                'file_size': metadata.get('file_size'),
                'invoice_metadata': {
                    'vendor_name': metadata.get('vendor_name'),
                    'invoice_number': metadata.get('invoice_number'),
                    'invoice_date': metadata.get('invoice_date'),
                    'total_amount': metadata.get('total_amount'),
                    'currency': metadata.get('currency'),
                    'invoice_type': metadata.get('invoice_type'),
                    'business_category': metadata.get('business_category'),
                    'processing_priority': metadata.get('processing_priority')
                }
            }
            
            # Validate required fields
            required_fields = ['bucket', 'key', 'document_id', 'upload_timestamp']
            missing_fields = [field for field in required_fields if not mapped_message.get(field)]
            
            if missing_fields:
                logger.error(f"Missing required fields: {missing_fields}")
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
            logger.info(f"Mapped invoice message: {mapped_message}")
            
            # Process invoice with Claude AI OCR
            result = process_invoice(mapped_message)
            results.append(result)
            
        except Exception as e:
            error_msg = f"Failed to process invoice record: {e}"
            logger.error(error_msg)
            errors.append({
                'message': message_body if 'message_body' in locals() else record['body'],
                'error': str(e)
            })
    
    # Return summary
    return {
        'statusCode': 200 if not errors else 207,
        'body': json.dumps({
            'processed': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors,
            'processing_engine': 'Claude AI Invoice OCR',
            'model': CLAUDE_MODEL,
            'runtime': 'Python 3.12'
        })
    }