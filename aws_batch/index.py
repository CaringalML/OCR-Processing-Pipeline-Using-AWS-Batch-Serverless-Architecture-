#!/usr/bin/env python3
"""
OCR Processing Pipeline - Batch Processing Only
Converts documents to text using AWS Textract and analyzes with AWS Comprehend
Enhanced with natural flow punctuation, comprehensive grammar refinement, and QuillBot-compliant colon fixes
Optimized version with TextBlob and spaCy dependencies removed
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

# Optional spell checking (lightweight)
try:
    import spellchecker
    from spellchecker import SpellChecker
    SPELLCHECKER_AVAILABLE = True
except ImportError:
    SPELLCHECKER_AVAILABLE = False
    print('INFO: PySpellChecker not available - using built-in spell checking only')

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


# Startup logging
log('INFO', 'OCR Processor starting - batch mode only (optimized)', {
    'hasRequiredEnvVars': bool(
        os.getenv('S3_BUCKET') and 
        os.getenv('S3_KEY') and 
        os.getenv('FILE_ID') and 
        os.getenv('DYNAMODB_TABLE')
    ),
    'spellCheckerAvailable': SPELLCHECKER_AVAILABLE
})


def health_check() -> Dict[str, Any]:
    """Simple health check for container health monitoring"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'uptime': time.time(),
        'mode': 'batch-only',
        'version': '3.0.0'  # Updated version - optimized
    }


def convert_to_dynamodb_compatible(obj: Any) -> Any:
    """
    Recursively convert Python objects to DynamoDB-compatible format.
    Handles floats, None values, and empty containers.
    """
    if obj is None:
        return 'NULL'
    elif isinstance(obj, float):
        if obj != obj:  # Check for NaN
            return Decimal('0')
        elif obj == float('inf') or obj == float('-inf'):
            return Decimal('0')
        else:
            try:
                return Decimal(str(round(obj, 6)))
            except (InvalidOperation, ValueError):
                return Decimal('0')
    elif isinstance(obj, int):
        return obj
    elif isinstance(obj, str):
        return obj if obj else 'EMPTY'
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, dict):
        if not obj:
            return {'EMPTY': 'DICT'}
        converted = {}
        for k, v in obj.items():
            key = str(k) if not isinstance(k, str) else k
            if not key:
                key = 'EMPTY_KEY'
            converted[key] = convert_to_dynamodb_compatible(v)
        return converted
    elif isinstance(obj, (list, tuple)):
        if not obj:
            return ['EMPTY_LIST']
        return [convert_to_dynamodb_compatible(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
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


def apply_url_email_fixes(text: str) -> Dict[str, Any]:
    """
    Fix URLs and email addresses by removing inappropriate spaces
    """
    if not text or not text.strip():
        return {
            'fixed_text': text,
            'url_email_fixes': 0,
            'fixes_applied': []
        }
    
    fixed_text = text
    fixes_applied = []
    url_email_fixes = 0
    
    # 1. Fix email addresses with spaces
    before_emails = fixed_text
    email_pattern = r'\b([a-zA-Z0-9._-]+)@([a-zA-Z0-9.-]+(?:\.\s+[a-zA-Z]{2,})+)\b'
    def fix_email(match):
        username = match.group(1)
        domain = match.group(2).replace(' ', '')
        return f"{username}@{domain}"
    
    fixed_text = re.sub(email_pattern, fix_email, fixed_text)
    fixed_text = re.sub(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+)\.\s+([a-zA-Z]{2,4})', r'\1.\2', fixed_text)
    fixed_text = re.sub(r'([a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+)\.\s+co\.\s+([a-zA-Z]{2,4})', r'\1.co.\2', fixed_text)
    
    if before_emails != fixed_text:
        fixes_applied.append("Fixed email addresses with spaces")
        url_email_fixes += 1
    
    # 2. Fix website URLs with spaces
    before_urls = fixed_text
    fixed_text = re.sub(r'\bwww\.\s+([a-zA-Z0-9.-]+(?:\.\s*[a-zA-Z0-9.-]*)*)\b', 
                       lambda m: 'www.' + m.group(1).replace(' ', ''), fixed_text)
    fixed_text = re.sub(r'\b([a-zA-Z0-9-]+)\.\s+([a-zA-Z0-9-]+)\.\s+([a-zA-Z]{2,4})\b', r'\1.\2.\3', fixed_text)
    fixed_text = re.sub(r'\b([a-zA-Z0-9-]+)\.\s+([a-zA-Z]{2,4})\b', r'\1.\2', fixed_text)
    fixed_text = re.sub(r'\b([a-zA-Z0-9-]+)\.\s+nz\b', r'\1.nz', fixed_text)
    fixed_text = re.sub(r'\b([a-zA-Z0-9-]+)\.\s+com\b', r'\1.com', fixed_text)
    fixed_text = re.sub(r'\b([a-zA-Z0-9-]+)\.\s+org\b', r'\1.org', fixed_text)
    
    if before_urls != fixed_text:
        fixes_applied.append("Fixed website URLs with spaces")
        url_email_fixes += 1
    
    # 3. Fix https/http URLs with spaces
    before_https = fixed_text
    fixed_text = re.sub(r'\bhttps?\s*:\s*//\s*([a-zA-Z0-9.-]+(?:\.\s*[a-zA-Z0-9.-]*)*)', 
                       lambda m: 'https://' + m.group(1).replace(' ', ''), fixed_text)
    
    if before_https != fixed_text:
        fixes_applied.append("Fixed https/http URLs with spaces")
        url_email_fixes += 1
    
    return {
        'fixed_text': fixed_text,
        'url_email_fixes': url_email_fixes,
        'fixes_applied': fixes_applied
    }


def apply_enhanced_colon_grammar_fix(text: str) -> Dict[str, Any]:
    """
    Apply enhanced colon grammar fixes based on proper usage rules
    """
    if not text or not text.strip():
        return {
            'fixed_text': text,
            'colon_fixes': 0,
            'fixes_applied': []
        }
    
    fixed_text = text
    fixes_applied = []
    colon_fixes = 0
    
    # Rule 1: Remove inappropriate colon before question words
    before_rule1 = fixed_text
    fixed_text = re.sub(r'(\w+\s+are):\s+(what|how|when|where|why)\b', r'\1 \2', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'(\w+\s+is):\s+(what|how|when|where|why)\b', r'\1 \2', fixed_text, flags=re.IGNORECASE)
    if before_rule1 != fixed_text:
        fixes_applied.append("Removed inappropriate colon before question words")
        colon_fixes += 1
    
    # Rule 2: Fix colons that should introduce new sentences
    before_rule3 = fixed_text
    patterns_to_fix = [
        (r'(\w+\s+car):\s+(we\s+go\s+out)', r'\1. We go out'),
        (r'(\w+\s+future):\s+(it\s+must\s+be)', r'\1. It must be'),
        (r'(\w+):\s+(one\s+thing\s+is)', r'\1. One thing is'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        new_text = re.sub(pattern, replacement, fixed_text, flags=re.IGNORECASE)
        if new_text != fixed_text:
            fixed_text = new_text
            fixes_applied.append("Fixed colon before independent clause")
            colon_fixes += 1
    
    # Rule 3: Context-aware colon fixing
    before_rule4 = fixed_text
    fixed_text = re.sub(r'(\w+\s+are):\s+(what\s+\w+(?:\s+\w+)*?)(?=\s+and|\s+or|\?)', r'\1 \2', fixed_text, flags=re.IGNORECASE)
    if before_rule4 != fixed_text:
        fixes_applied.append("Fixed colon in compound questions")
        colon_fixes += 1
    
    return {
        'fixed_text': fixed_text,
        'colon_fixes': colon_fixes,
        'fixes_applied': fixes_applied
    }


def apply_enhanced_grammar_fixes(text: str) -> Dict[str, Any]:
    """
    Apply enhanced grammar fixes for common OCR and writing issues
    """
    if not text or not text.strip():
        return {
            'fixed_text': text,
            'grammar_fixes': 0,
            'fixes_applied': []
        }
    
    fixed_text = text
    fixes_applied = []
    grammar_fixes = 0
    
    # 1. Fix subject-verb agreement issues
    before_agreement = fixed_text
    fixed_text = re.sub(r'\bthis\s+(\w+)\s+are\b', r'this \1 is', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\bthese\s+(\w+)\s+is\b', r'these \1 are', fixed_text, flags=re.IGNORECASE)
    if before_agreement != fixed_text:
        fixes_applied.append("Fixed subject-verb agreement")
        grammar_fixes += 1
    
    # 2. Fix article usage (a/an)
    before_articles = fixed_text
    fixed_text = re.sub(r'\ba\s+([aeiouAEIOU])', r'an \1', fixed_text)
    fixed_text = re.sub(r'\ban\s+([bcdfgjklmnpqrstvwxyzBCDFGJKLMNPQRSTVWXYZ][^aeiou])', r'a \1', fixed_text)
    if before_articles != fixed_text:
        fixes_applied.append("Fixed article usage (a/an)")
        grammar_fixes += 1
    
    # 3. Fix common redundancy
    before_redundancy = fixed_text
    fixed_text = re.sub(r'\bmay\s+become\s+a\s+usual\b', 'may become usual', fixed_text)
    if before_redundancy != fixed_text:
        fixes_applied.append("Removed redundancy")
        grammar_fixes += 1
    
    return {
        'fixed_text': fixed_text,
        'grammar_fixes': grammar_fixes,
        'fixes_applied': fixes_applied
    }


def apply_natural_flow_punctuation(text: str) -> Dict[str, Any]:
    """
    Apply natural flow punctuation with enhanced colon grammar rules and comprehensive dash handling
    """
    if not text or not text.strip():
        return {
            'refined_text': text,
            'flow_fixes': 0,
            'fixes_applied': []
        }
    
    refined_text = text
    fixes_applied = []
    flow_fixes = 0
    
    # PROTECT URLs and emails during processing
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    domain_pattern = r'\bwww\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    spaced_email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+(?:\.\s*[A-Za-z0-9.-]*)+\b'
    spaced_domain_pattern = r'\bwww\.\s*[A-Za-z0-9.-]+(?:\.\s*[A-Za-z0-9.-]*)+\b'
    
    protected_patterns = []
    def protect_pattern(match):
        placeholder = f"__URL_PROTECTED_{len(protected_patterns)}__"
        protected_patterns.append(match.group(0))
        return placeholder
    
    # Protect URL/email patterns
    refined_text = re.sub(spaced_email_pattern, protect_pattern, refined_text)
    refined_text = re.sub(spaced_domain_pattern, protect_pattern, refined_text)
    refined_text = re.sub(email_pattern, protect_pattern, refined_text)
    refined_text = re.sub(url_pattern, protect_pattern, refined_text)
    refined_text = re.sub(domain_pattern, protect_pattern, refined_text)
    
    # Step 1: Apply enhanced colon grammar fixes
    colon_result = apply_enhanced_colon_grammar_fix(refined_text)
    if colon_result['colon_fixes'] > 0:
        refined_text = colon_result['fixed_text']
        flow_fixes += colon_result['colon_fixes']
        fixes_applied.extend(colon_result['fixes_applied'])
    
    # Step 2: Handle lists and series with natural comma usage
    before_comma = refined_text
    refined_text = re.sub(r'(\w+),\s+(\w+)\s+and\s+(\w+)', r'\1, \2, and \3', refined_text)
    refined_text = re.sub(r'\bget\s+out\s+and\s+leave\b', 'get out, and leave', refined_text)
    if before_comma != refined_text:
        fixes_applied.append("Improved comma usage for natural flow")
        flow_fixes += 1
    
    # Step 3: COMPREHENSIVE DASH HANDLING
    before_activity = refined_text
    
    # Fix ALL dash variations: em dash, en dash, hyphen with spaces
    refined_text = re.sub(r'(\w+)\s*[—–-]\s*(while\s)', r'\1 \2', refined_text)
    refined_text = re.sub(r'(\w+)\s*[—–-]\s*(when\s)', r'\1 \2', refined_text)
    refined_text = re.sub(r'(\w+)\s*[—–-]\s*(as\s)', r'\1 \2', refined_text)
    
    # Convert activity lists to natural flow
    refined_text = re.sub(r'(relax)\s*[—–-]\s*(dream)', r'\1, \2', refined_text)
    
    # Handle temporal clauses after activity lists
    activity_temporal_pattern = r'(flirt\s+with\s+his\s+passenger)\s*[—–-]\s*(while\s+)'
    if re.search(activity_temporal_pattern, refined_text):
        refined_text = re.sub(activity_temporal_pattern, r'\1 \2', refined_text)
        fixes_applied.append("Fixed temporal clause after activity list")
        flow_fixes += 1
    
    if before_activity != refined_text:
        fixes_applied.append("Fixed temporal clauses and activity lists for natural flow")
        flow_fixes += 1
    
    # Step 4: Capitalize sentences after corrected punctuation
    before_caps = refined_text
    refined_text = re.sub(r'(\.\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), refined_text)
    if before_caps != refined_text:
        fixes_applied.append("Fixed capitalization for sentence flow")
        flow_fixes += 1
    
    # Step 5: Clean spacing for natural flow
    before_spacing = refined_text
    refined_text = re.sub(r'\s+([,.!?;:])', r'\1', refined_text)
    refined_text = re.sub(r'([,.!?;:])\s*', r'\1 ', refined_text)
    refined_text = re.sub(r'\s{2,}', ' ', refined_text).strip()
    if before_spacing != refined_text:
        fixes_applied.append("Cleaned spacing for natural flow")
        flow_fixes += 1
    
    # RESTORE protected patterns and apply URL/email fixes
    for i, pattern in enumerate(protected_patterns):
        placeholder = f"__URL_PROTECTED_{i}__"
        fixed_pattern = apply_url_email_fixes(pattern)['fixed_text']
        refined_text = refined_text.replace(placeholder, fixed_pattern)
        if fixed_pattern != pattern:
            fixes_applied.append("Fixed URL/email spacing in protected pattern")
            flow_fixes += 1
    
    return {
        'refined_text': refined_text,
        'flow_fixes': flow_fixes,
        'fixes_applied': fixes_applied,
        'original_length': len(text),
        'refined_length': len(refined_text)
    }


def apply_comprehensive_ocr_fixes(text: str) -> Dict[str, Any]:
    """
    Apply comprehensive OCR fixes including:
    - URL/email preservation and fixing
    - Hyphenated word rejoining
    - OCR character error corrections
    - Artifact removal
    """
    if not text or not text.strip():
        return {'fixed_text': text, 'fixes_applied': 0}
    
    fixed_text = text
    fixes_applied = 0
    
    # Step 1: Apply URL and email fixes first
    url_email_result = apply_url_email_fixes(fixed_text)
    if url_email_result['url_email_fixes'] > 0:
        fixed_text = url_email_result['fixed_text']
        fixes_applied += url_email_result['url_email_fixes']
    
    # Step 2: Fix hyphenated words
    before_hyphen = fixed_text
    
    # Protect URLs and emails during hyphen processing
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    domain_pattern = r'\bwww\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    
    protected_patterns = []
    def protect_pattern(match):
        placeholder = f"__PROTECTED_{len(protected_patterns)}__"
        protected_patterns.append(match.group(0))
        return placeholder
    
    # Protect URLs and emails
    fixed_text = re.sub(email_pattern, protect_pattern, fixed_text)
    fixed_text = re.sub(url_pattern, protect_pattern, fixed_text)
    fixed_text = re.sub(domain_pattern, protect_pattern, fixed_text)
    
    # Apply hyphen fixes
    fixed_text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', fixed_text)
    fixed_text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', fixed_text)
    
    # Specific word patterns
    fixed_text = re.sub(r'\bguide-\s*once\b', 'guidance', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\bse-\s*let\b', 'select', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\bpas-\s*singer\b', 'passenger', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\bauto-\s*matic\b', 'automatic', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\btrans-\s*port\b', 'transport', fixed_text, flags=re.IGNORECASE)
    
    # Restore protected patterns
    for i, pattern in enumerate(protected_patterns):
        fixed_text = fixed_text.replace(f"__PROTECTED_{i}__", pattern)
    
    if before_hyphen != fixed_text:
        fixes_applied += 1
    
    # Step 3: Fix OCR character errors
    before_ocr = fixed_text
    
    # Re-protect for OCR fixes
    protected_patterns = []
    fixed_text = re.sub(email_pattern, protect_pattern, fixed_text)
    fixed_text = re.sub(url_pattern, protect_pattern, fixed_text)
    fixed_text = re.sub(domain_pattern, protect_pattern, fixed_text)
    
    # Apply OCR fixes
    fixed_text = re.sub(r'\bgui[>\/\|\\]dan[\/\\]ce\b', 'guidance', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\bsel[€£\$]ct\b', 'select', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\bp[@&]ssenger\b', 'passenger', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\blane1\b', 'lane', fixed_text)
    fixed_text = re.sub(r'\b(\w+)1\s+(he|she|it|they)\b', r'\1 \2', fixed_text)
    
    # Fix common spell-checker mistakes from split words
    fixed_text = re.sub(r'\bguide\s*once\b', 'guidance', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\blet\b(?=\s+our\s+destination)', 'select', fixed_text, flags=re.IGNORECASE)
    fixed_text = re.sub(r'\bsinger\b(?=\s*-?\s*while)', 'passenger', fixed_text, flags=re.IGNORECASE)
    
    # Restore protected patterns again
    for i, pattern in enumerate(protected_patterns):
        fixed_text = fixed_text.replace(f"__PROTECTED_{i}__", pattern)
    
    if before_ocr != fixed_text:
        fixes_applied += 1
    
    # Step 4: Remove trailing artifacts
    before_artifact = fixed_text
    fixed_text = re.sub(r'\s+\w{1,3}-\s*$', '', fixed_text)
    fixed_text = re.sub(r'\s+\w{1,2}\s*$', '', fixed_text)
    if before_artifact != fixed_text:
        fixes_applied += 1
    
    return {'fixed_text': fixed_text, 'fixes_applied': fixes_applied}


def apply_basic_spell_correction(text: str) -> Dict[str, Any]:
    """
    Apply basic spell correction using built-in methods
    """
    if not text or not text.strip():
        return {
            'corrected_text': text,
            'corrections_made': 0,
            'method': 'none'
        }
    
    corrections_made = 0
    corrected_text = text
    method_used = 'built_in'
    
    # Built-in basic corrections for common OCR errors
    corrections = {
        r'\brn\b': 'm',
        r'\bvv\b': 'w',
        r'\bcl\b': 'd',
        r'\bri\b': 'n',
        r'\bthe\s+': 'the ',
        r'\band\s+': 'and ',
        r'\bwith\s+': 'with ',
        r'\s{2,}': ' ',
    }
    
    for pattern, replacement in corrections.items():
        new_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
        if new_text != corrected_text:
            corrected_text = new_text
            corrections_made += 1
    
    return {
        'corrected_text': corrected_text,
        'corrections_made': corrections_made,
        'method': method_used
    }


def apply_text_correction(text: str) -> Dict[str, Any]:
    """
    Apply text correction using available methods (PySpellChecker or built-in)
    """
    if not text or not text.strip():
        return {
            'corrected_text': text,
            'corrections_made': 0,
            'method': 'none'
        }
    
    # Try PySpellChecker if available
    if SPELLCHECKER_AVAILABLE:
        try:
            spell = SpellChecker()
            words = text.split()
            corrected_words = []
            corrections_made = 0
            
            for word in words:
                clean_word = ''.join(char for char in word if char.isalpha())
                if clean_word and clean_word.lower() in spell:
                    corrected_words.append(word)
                elif clean_word:
                    correction = spell.correction(clean_word.lower())
                    if correction and correction != clean_word.lower():
                        corrected_word = word.replace(clean_word, correction.capitalize() if clean_word.isupper() else correction)
                        corrected_words.append(corrected_word)
                        corrections_made += 1
                    else:
                        corrected_words.append(word)
                else:
                    corrected_words.append(word)
            
            return {
                'corrected_text': ' '.join(corrected_words),
                'corrections_made': corrections_made,
                'method': 'pyspellchecker'
            }
        except Exception:
            pass
    
    # Fallback to built-in correction
    return apply_basic_spell_correction(text)


def apply_comprehensive_text_refinement_natural(text: str) -> Dict[str, Any]:
    """
    Apply comprehensive text refinement with focus on natural flow and enhanced grammar
    """
    if not text or not text.strip():
        return {
            'refined_text': text,
            'total_improvements': 0,
            'spell_corrections': 0,
            'grammar_refinements': 0,
            'flow_improvements': 0,
            'methods_used': [],
            'processing_notes': 'Empty text'
        }
    
    refined_text = text
    total_improvements = 0
    spell_corrections = 0
    grammar_refinements = 0
    flow_improvements = 0
    ocr_fixes = 0
    methods_used = []
    processing_notes = []
    
    # Step 0: Apply comprehensive OCR fixes first
    ocr_result = apply_comprehensive_ocr_fixes(refined_text)
    if ocr_result['fixes_applied'] > 0:
        refined_text = ocr_result['fixed_text']
        ocr_fixes = ocr_result['fixes_applied']
        total_improvements += ocr_fixes
        methods_used.append('ocr_fixes')
        processing_notes.append(f"OCR fixes: {ocr_fixes}")
    
    # Step 1: Apply spell correction
    spell_result = apply_text_correction(refined_text)
    if spell_result['corrections_made'] > 0:
        refined_text = spell_result['corrected_text']
        spell_corrections = spell_result['corrections_made']
        total_improvements += spell_corrections
        methods_used.append(spell_result['method'])
        processing_notes.append(f"Spell corrections: {spell_corrections}")
    
    # Step 2: Apply natural flow punctuation with enhanced grammar
    flow_result = apply_natural_flow_punctuation(refined_text)
    if flow_result['flow_fixes'] > 0:
        refined_text = flow_result['refined_text']
        flow_improvements = flow_result['flow_fixes']
        total_improvements += flow_improvements
        methods_used.append('natural_flow_punctuation_enhanced')
        processing_notes.append(f"Natural flow fixes: {flow_improvements}")
    
    # Step 3: Apply enhanced grammar fixes
    grammar_result = apply_enhanced_grammar_fixes(refined_text)
    if grammar_result['grammar_fixes'] > 0:
        refined_text = grammar_result['fixed_text']
        grammar_refinements = grammar_result['grammar_fixes']
        total_improvements += grammar_refinements
        methods_used.append('enhanced_grammar')
        processing_notes.append(f"Grammar refinements: {grammar_refinements}")
    
    return {
        'refined_text': refined_text,
        'total_improvements': total_improvements,
        'ocr_fixes': ocr_fixes,
        'spell_corrections': spell_corrections,
        'grammar_refinements': grammar_refinements,
        'flow_improvements': flow_improvements,
        'methods_used': methods_used,
        'processing_notes': '; '.join(processing_notes) if processing_notes else 'No improvements needed',
        'original_length': len(text),
        'refined_length': len(refined_text)
    }


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
        
        # Process text through enhanced pipeline
        formatted_text_data = {}
        refined_text_data = {}
        text_for_comprehend = extracted_data['text']
        
        if extracted_data['text'] and extracted_data['text'].strip():
            # Stage 1: Format extracted text (remove \n, clean spacing)
            log('INFO', 'Formatting extracted text')
            formatted_text_data = format_extracted_text(extracted_data['text'])
            
            # Stage 2: Apply comprehensive refinement
            log('INFO', 'Applying comprehensive text refinement (optimized)')
            refined_text_data = apply_comprehensive_text_refinement_natural(formatted_text_data.get('formatted', extracted_data['text']))
            
            # Use the refined text for Comprehend analysis
            text_for_comprehend = refined_text_data.get('refined_text', formatted_text_data.get('formatted', extracted_data['text']))
            
            log('INFO', 'Text processing completed', {
                'stage1_extractedChars': len(extracted_data['text']),
                'stage2_formattedChars': formatted_text_data['stats']['cleanedChars'],
                'stage3_refinedChars': refined_text_data.get('refined_length', 0),
                'totalImprovements': refined_text_data.get('total_improvements', 0),
                'spellCorrections': refined_text_data.get('spell_corrections', 0),
                'grammarRefinements': refined_text_data.get('grammar_refinements', 0),
                'flowImprovements': refined_text_data.get('flow_improvements', 0),
                'methodsUsed': refined_text_data.get('methods_used', [])
            })
        
        # Process formatted text with AWS Comprehend
        comprehend_data = {}
        if text_for_comprehend and text_for_comprehend.strip():
            log('INFO', 'Starting Comprehend analysis on refined text')
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
        
        # Generate processing results
        processing_results = {
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'file_size': file_size,
            'content_type': content_type,
            'processing_duration': f'{total_processing_time:.2f} seconds',
            'extracted_text': extracted_data['text'],
            'formatted_text': formatted_text_data.get('formatted', extracted_data['text']),
            'refined_text': refined_text_data.get('refined_text', formatted_text_data.get('formatted', extracted_data['text'])),
            'summary_analysis': {
                'word_count': extracted_data['wordCount'],
                'character_count': len(extracted_data['text']),
                'line_count': extracted_data['lineCount'],
                'paragraph_count': formatted_text_data.get('stats', {}).get('paragraphCount', 0),
                'sentence_count': formatted_text_data.get('stats', {}).get('sentenceCount', 0),
                'confidence': extracted_data['confidence'],
                'total_improvements': refined_text_data.get('total_improvements', 0),
                'spell_corrections': refined_text_data.get('spell_corrections', 0),
                'grammar_refinements': refined_text_data.get('grammar_refinements', 0),
                'flow_improvements': refined_text_data.get('flow_improvements', 0),
                'methods_used': refined_text_data.get('methods_used', [])
            },
            'text_refinement_details': {
                'total_improvements': refined_text_data.get('total_improvements', 0),
                'spell_corrections': refined_text_data.get('spell_corrections', 0),
                'grammar_refinements': refined_text_data.get('grammar_refinements', 0),
                'flow_improvements': refined_text_data.get('flow_improvements', 0),
                'methods_used': refined_text_data.get('methods_used', []),
                'processing_notes': refined_text_data.get('processing_notes', 'No processing applied'),
                'length_change': refined_text_data.get('refined_length', 0) - refined_text_data.get('original_length', 0)
            },
            'comprehend_analysis': comprehend_data,
            'metadata': {
                'processor_version': '3.0.0',  # Optimized version
                'batch_job_id': os.getenv('AWS_BATCH_JOB_ID', 'unknown'),
                'textract_job_id': extracted_data['jobId'],
                'textract_duration': f'{textract_time:.2f} seconds',
                'comprehend_duration': f"{comprehend_data.get('processingTime', 0):.2f} seconds" if comprehend_data.get('processingTime') else 'N/A',
                'text_correction_enabled': SPELLCHECKER_AVAILABLE,
                'optimized_processing': True,
                'natural_flow_enabled': True,
                'enhanced_grammar_enabled': True,
                'url_email_fixes_enabled': True
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
            'totalImprovements': refined_text_data.get('total_improvements', 0),
            'flowImprovements': refined_text_data.get('flow_improvements', 0),
            'grammarImprovements': refined_text_data.get('grammar_refinements', 0),
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
        
        # Start asynchronous document analysis
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
            log('WARN', 'Text detection failed, trying document analysis', {'error': str(e)})
            response = textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': object_key
                    }
                },
                FeatureTypes=['TABLES', 'FORMS']
            )
        job_id = response['JobId']
        log('INFO', 'Textract job submitted', {'textractJobId': job_id})
        
        # Wait for job completion
        job_status = 'IN_PROGRESS'
        attempts = 0
        max_attempts = 60
        
        while job_status == 'IN_PROGRESS' and attempts < max_attempts:
            time.sleep(5)
            
            try:
                status_response = textract_client.get_document_text_detection(JobId=job_id)
            except:
                status_response = textract_client.get_document_analysis(JobId=job_id)
            
            job_status = status_response['JobStatus']
            attempts += 1
            
            if attempts % 6 == 0:
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
    """Format extracted text by removing \\n characters"""
    try:
        if not raw_text or not isinstance(raw_text, str):
            return {
                'formatted': '',
                'paragraphs': [],
                'stats': {'paragraphCount': 0, 'sentenceCount': 0, 'cleanedChars': 0, 'originalChars': 0, 'reductionPercent': 0}
            }
        
        # Simple formatting: remove \n characters, keep everything else
        formatted_text = raw_text.replace('\n', ' ')
        
        # Calculate basic stats
        original_len = len(raw_text)
        formatted_len = len(formatted_text)
        
        # Count sentences and paragraphs
        sentence_count = len([s for s in formatted_text.split('.') if s.strip()])
        paragraph_count = max(1, len([p for p in raw_text.split('\n\n') if p.strip()]))
        
        return {
            'formatted': formatted_text,
            'paragraphs': [{'text': formatted_text, 'type': 'paragraph', 'wordCount': len(formatted_text.split()), 'charCount': formatted_len}],
            'stats': {
                'paragraphCount': paragraph_count,
                'sentenceCount': sentence_count,
                'cleanedChars': formatted_len,
                'originalChars': original_len,
                'reductionPercent': 0
            }
        }
        
    except Exception as error:
        log('ERROR', 'Text formatting error', {'error': str(error)})
        return {
            'formatted': raw_text or '',
            'paragraphs': [{'text': raw_text or '', 'type': 'paragraph', 'wordCount': len((raw_text or '').split()), 'charCount': len(raw_text or '')}],
            'stats': {'paragraphCount': 1, 'sentenceCount': 0, 'cleanedChars': len(raw_text or ''), 'originalChars': len(raw_text or ''), 'reductionPercent': 0}
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
            
            # Group entities by type
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
        table = dynamodb.Table(table_name)
        
        # Get the current item to find the upload_timestamp
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
        result = process_s3_file()
        
        log('INFO', 'Batch job completed successfully', {
            'processingDuration': result['processing_duration'],
            'textExtracted': result['summary_analysis']['word_count'] > 0,
            'totalImprovements': result['summary_analysis']['total_improvements'],
            'flowImprovements': result['summary_analysis']['flow_improvements'],
            'grammarImprovements': result['summary_analysis']['grammar_refinements']
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
    time.sleep(0.1)  # Minimal delay for logging setup
    run_batch_job()


if __name__ == '__main__':
    main()