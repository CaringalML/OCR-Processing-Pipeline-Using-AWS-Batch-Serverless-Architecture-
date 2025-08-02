# Short Batch Processor Lambda Function

## Overview
This Lambda function processes small files (< 10MB) through a comprehensive OCR pipeline with text enhancement features.

## Features
- **OCR Processing**: AWS Textract for text extraction
- **Text Enhancement**: Comprehensive fixes including:
  - OCR character error corrections
  - URL/email pattern preservation
  - Grammar refinements using TextBlob
  - Natural flow punctuation improvements
  - Enhanced colon usage fixes
- **NLP Analysis**: AWS Comprehend for sentiment, entities, and key phrases
- **Statistics Tracking**: Detailed improvement metrics and processing notes

## Files Structure
```
short_batch_processor/
├── short_batch_processor.py     # Main Lambda function code
├── requirements.txt             # Python dependencies
├── install_dependencies.sh                   # Smart packaging script with change detection
├── download_models.py          # Model download utility (optional)
├── .gitignore                  # Git ignore patterns
└── README.md                   # This file
```

## Dependencies
- `boto3==1.39.14` - AWS SDK
- `botocore==1.39.14` - AWS core library
- `textblob==0.17.1` - Text processing and grammar correction
- `spacy==3.7.2` - Advanced NLP processing
- `pyspellchecker==0.8.1` - Spell checking
- `nltk==3.8.1` - Natural language toolkit

## Deployment

### Smart Packaging (Recommended)
The `install_dependencies.sh` script automatically detects changes and only rebuilds when necessary:

```bash
# Run smart packaging with change detection
./install_dependencies.sh
```

**Features:**
- ✅ **Change Detection**: Only rebuilds if source code or dependencies changed
- ✅ **Automatic ZIP Creation**: Creates optimized deployment package
- ✅ **Optional Deployment**: Prompts to deploy to AWS Lambda
- ✅ **Size Optimization**: Removes unnecessary files and cache
- ✅ **Checksum Tracking**: Remembers what was last packaged

### Manual Deployment
```bash
# Quick code-only deployment (no dependencies)
zip -r short_batch_processor.zip short_batch_processor.py
aws lambda update-function-code --function-name ocr-processor-batch-short-batch-processor --zip-file fileb://short_batch_processor.zip
rm short_batch_processor.zip
```

## Environment Variables
- `METADATA_TABLE`: DynamoDB table for file metadata
- `RESULTS_TABLE`: DynamoDB table for processing results
- `MAX_FILE_SIZE_MB`: Maximum file size (default: 10)
- `MAX_RETRIES`: Maximum retry attempts (default: 3)
- `RETRY_DELAY`: Delay between retries in seconds (default: 2)
- `LOG_LEVEL`: Logging level (default: INFO)

## Processing Pipeline
1. **File Validation**: Check file size and format
2. **Textract OCR**: Extract raw text from document
3. **Text Formatting**: Clean and structure extracted text
4. **Text Enhancement**: Apply comprehensive improvements:
   - OCR fixes (character corrections)
   - Grammar refinements (TextBlob)
   - Natural flow punctuation
   - URL/email preservation
5. **Comprehend Analysis**: Extract sentiment, entities, key phrases
6. **Results Storage**: Store in both results and metadata tables

## Output Format
The function provides comprehensive statistics including:
- Total improvements applied
- OCR fixes count
- Grammar refinements count
- Flow improvements count
- Processing methods used
- Entity and sentiment analysis
- Processing duration and confidence scores

## Performance
- **Processing Time**: ~1-2 seconds for typical documents
- **Memory Usage**: 1024MB allocated
- **Timeout**: 900 seconds (15 minutes)
- **File Size Limit**: 10MB for short-batch processing

## Version History
- **v2.8.0**: Added comprehensive OCR features matching AWS Batch version
- **v2.7.0**: Enhanced metadata storage and API integration
- **v2.6.0**: Initial comprehensive text refinement implementation