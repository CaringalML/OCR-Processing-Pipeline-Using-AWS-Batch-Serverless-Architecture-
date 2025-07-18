// batch processing only
const AWS = require('aws-sdk');

// Initialize AWS clients
const s3 = new AWS.S3();
const dynamodb = new AWS.DynamoDB.DocumentClient();
const textract = new AWS.Textract();
const comprehend = new AWS.Comprehend();

// Production logging (reduced verbosity, structured format)
const logLevel = process.env.LOG_LEVEL || 'INFO';
const isDev = process.env.NODE_ENV === 'development';

function log(level, message, data = {}) {
  const levels = { ERROR: 0, WARN: 1, INFO: 2, DEBUG: 3 };
  const currentLevel = levels[logLevel] || 2;
  
  if (levels[level] <= currentLevel) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      message,
      batchJobId: process.env.AWS_BATCH_JOB_ID,
      fileId: process.env.FILE_ID,
      ...data
    };
    console.log(JSON.stringify(logEntry));
  }
}

// Startup logging (minimal in production)
if (isDev || logLevel === 'DEBUG') {
  log('DEBUG', 'Container startup debug info', {
    nodeVersion: process.version,
    environment: {
      AWS_BATCH_JOB_ID: process.env.AWS_BATCH_JOB_ID,
      S3_BUCKET: process.env.S3_BUCKET,
      S3_KEY: process.env.S3_KEY,
      FILE_ID: process.env.FILE_ID,
      DYNAMODB_TABLE: process.env.DYNAMODB_TABLE,
      AWS_REGION: process.env.AWS_REGION
    }
  });
} else {
  log('INFO', 'OCR Processor starting - batch mode only', {
    hasRequiredEnvVars: !!(process.env.S3_BUCKET && process.env.S3_KEY && process.env.FILE_ID && process.env.DYNAMODB_TABLE)
  });
}

// Simple health check for container health monitoring (no web server)
function healthCheck() {
  return {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    mode: 'batch-only',
    version: '2.0.0'
  };
}

// Main S3 file processing function
async function processS3File() {
  const bucketName = process.env.S3_BUCKET;
  const objectKey = process.env.S3_KEY;
  const fileId = process.env.FILE_ID;
  const dynamoTable = process.env.DYNAMODB_TABLE;
  
  log('INFO', 'Starting file processing', {
    bucket: bucketName,
    key: objectKey,
    fileId: fileId,
    table: dynamoTable
  });
  
  // Validate required environment variables
  if (!bucketName || !objectKey || !fileId || !dynamoTable) {
    const missingVars = [];
    if (!bucketName) missingVars.push('S3_BUCKET');
    if (!objectKey) missingVars.push('S3_KEY');
    if (!fileId) missingVars.push('FILE_ID');
    if (!dynamoTable) missingVars.push('DYNAMODB_TABLE');
    
    const errorMsg = `Missing required environment variables: ${missingVars.join(', ')}`;
    log('ERROR', errorMsg);
    throw new Error(errorMsg);
  }
  
  try {
    log('INFO', 'Updating status to processing');
    
    // Update processing status to 'processing'
    await updateFileStatus(dynamoTable, fileId, 'processing', {
      processing_started: new Date().toISOString(),
      batch_job_id: process.env.AWS_BATCH_JOB_ID || 'unknown'
    });
    
    log('INFO', 'Retrieving file metadata from S3');
    
    // Get file metadata from S3
    const s3ObjectMetadata = await s3.headObject({
      Bucket: bucketName,
      Key: objectKey
    }).promise();
    
    const fileSize = s3ObjectMetadata.ContentLength;
    const contentType = s3ObjectMetadata.ContentType;
    
    log('INFO', 'File metadata retrieved', {
      size: fileSize,
      contentType: contentType,
      lastModified: s3ObjectMetadata.LastModified
    });
    
    log('INFO', 'Starting Textract OCR processing');
    
    // Process file with AWS Textract
    const startTime = Date.now();
    const extractedData = await processFileWithTextract(bucketName, objectKey);
    const textractTime = (Date.now() - startTime) / 1000;
    
    log('INFO', 'Textract processing completed', {
      processingTimeSeconds: textractTime,
      wordCount: extractedData.wordCount,
      lineCount: extractedData.lineCount,
      confidence: extractedData.confidence
    });
    
    // Process extracted text with AWS Comprehend
    let comprehendData = {};
    if (extractedData.text && extractedData.text.trim().length > 0) {
      log('INFO', 'Starting Comprehend analysis');
      const comprehendStartTime = Date.now();
      comprehendData = await processTextWithComprehend(extractedData.text);
      const comprehendTime = (Date.now() - comprehendStartTime) / 1000;
      
      log('INFO', 'Comprehend analysis completed', {
        processingTimeSeconds: comprehendTime,
        language: comprehendData.language,
        sentiment: comprehendData.sentiment?.Sentiment,
        entitiesCount: comprehendData.entities?.length || 0,
        keyPhrasesCount: comprehendData.keyPhrases?.length || 0
      });
    } else {
      log('INFO', 'Skipping Comprehend analysis - no text extracted');
    }
    
    const totalProcessingTime = (Date.now() - startTime) / 1000;
    
    // Generate processing results
    const processingResults = {
      processed_at: new Date().toISOString(),
      file_size: fileSize,
      content_type: contentType,
      processing_duration: `${totalProcessingTime.toFixed(2)} seconds`,
      extracted_text: extractedData.text,
      analysis: {
        word_count: extractedData.wordCount,
        character_count: extractedData.text.length,
        line_count: extractedData.lineCount,
        confidence: extractedData.confidence
      },
      comprehend_analysis: comprehendData,
      metadata: {
        processor_version: '2.1.0',
        batch_job_id: process.env.AWS_BATCH_JOB_ID || 'unknown',
        textract_job_id: extractedData.jobId,
        textract_duration: `${textractTime.toFixed(2)} seconds`,
        comprehend_duration: comprehendData.processingTime ? `${comprehendData.processingTime.toFixed(2)} seconds` : 'N/A'
      }
    };
    
    log('INFO', 'Storing processing results');
    
    // Store processing results in DynamoDB
    await storeProcessingResults(fileId, processingResults);
    
    log('INFO', 'Updating status to processed');
    
    // Update file status to 'processed'
    await updateFileStatus(dynamoTable, fileId, 'processed', {
      processing_completed: new Date().toISOString(),
      processing_duration: processingResults.processing_duration
    });
    
    log('INFO', 'File processing completed successfully', {
      processingTimeSeconds: totalProcessingTime,
      extractedWords: extractedData.wordCount,
      extractedLines: extractedData.lineCount,
      confidence: extractedData.confidence,
      comprehendLanguage: comprehendData.language,
      comprehendSentiment: comprehendData.sentiment?.Sentiment
    });
    
    return processingResults;
    
  } catch (error) {
    log('ERROR', 'File processing failed', {
      error: error.message,
      stack: error.stack
    });
    
    // Update status to 'failed'
    try {
      await updateFileStatus(dynamoTable, fileId, 'failed', {
        error_message: error.message,
        failed_at: new Date().toISOString()
      });
      log('INFO', 'File status updated to failed');
    } catch (updateError) {
      log('ERROR', 'Failed to update error status', { error: updateError.message });
    }
    
    throw error;
  }
}

async function processFileWithTextract(bucketName, objectKey) {
  try {
    log('INFO', 'Starting Textract document analysis', {
      s3Uri: `s3://${bucketName}/${objectKey}`
    });
    
    // Start asynchronous document analysis
    const startParams = {
      DocumentLocation: {
        S3Object: {
          Bucket: bucketName,
          Name: objectKey
        }
      },
      FeatureTypes: ['TABLES', 'FORMS'] // Extract tables and forms in addition to text
    };
    
    const { JobId } = await textract.startDocumentAnalysis(startParams).promise();
    log('INFO', 'Textract job submitted', { textractJobId: JobId });
    
    // Wait for job completion
    let jobStatus = 'IN_PROGRESS';
    let attempts = 0;
    const maxAttempts = 60; // 5 minutes timeout (5 seconds * 60)
    
    while (jobStatus === 'IN_PROGRESS' && attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
      
      const statusResponse = await textract.getDocumentAnalysis({ JobId }).promise();
      jobStatus = statusResponse.JobStatus;
      attempts++;
      
      if (attempts % 6 === 0) { // Log every 30 seconds
        log('INFO', 'Waiting for Textract completion', {
          status: jobStatus,
          attempt: attempts,
          maxAttempts: maxAttempts
        });
      }
      
      if (jobStatus === 'FAILED') {
        const statusReason = statusResponse.StatusReason || 'Unknown error';
        throw new Error(`Textract job failed: ${statusReason}`);
      }
    }
    
    if (jobStatus !== 'SUCCEEDED') {
      throw new Error(`Textract job failed with status: ${jobStatus} after ${attempts} attempts`);
    }
    
    log('INFO', 'Textract job completed, retrieving results');
    
    // Get all results (handle pagination)
    let nextToken = null;
    let allBlocks = [];
    let pageCount = 0;
    
    do {
      const params = {
        JobId,
        NextToken: nextToken
      };
      
      const response = await textract.getDocumentAnalysis(params).promise();
      allBlocks = allBlocks.concat(response.Blocks || []);
      nextToken = response.NextToken;
      pageCount++;
    } while (nextToken);
    
    log('DEBUG', 'Textract results retrieved', {
      totalBlocks: allBlocks.length,
      pages: pageCount
    });
    
    // Extract text from blocks
    const extractedText = [];
    let totalConfidence = 0;
    let confidenceCount = 0;
    
    for (const block of allBlocks) {
      if (block.BlockType === 'LINE' && block.Text) {
        extractedText.push(block.Text);
        if (block.Confidence) {
          totalConfidence += block.Confidence;
          confidenceCount++;
        }
      }
    }
    
    const fullText = extractedText.join('\n');
    const words = fullText.split(/\s+/).filter(word => word.length > 0);
    
    const result = {
      text: fullText,
      wordCount: words.length,
      lineCount: extractedText.length,
      confidence: confidenceCount > 0 ? (totalConfidence / confidenceCount).toFixed(2) : 0,
      jobId: JobId
    };
    
    return result;
    
  } catch (error) {
    log('ERROR', 'Textract processing error', { error: error.message });
    
    // Fallback for non-supported file types or errors
    if (error.code === 'UnsupportedDocumentException' || error.code === 'InvalidParameterException') {
      log('WARN', 'File type not supported by Textract', { errorCode: error.code });
      return {
        text: 'File type not supported for text extraction',
        wordCount: 0,
        lineCount: 0,
        confidence: 0,
        jobId: 'N/A'
      };
    }
    
    throw error;
  }
}

async function processTextWithComprehend(text) {
  try {
    // Comprehend has a 5000 character limit for most operations
    const maxLength = 5000;
    const textToAnalyze = text.length > maxLength ? text.substring(0, maxLength) : text;
    
    log('INFO', 'Starting Comprehend analysis', {
      originalLength: text.length,
      analyzedLength: textToAnalyze.length,
      truncated: text.length > maxLength
    });
    
    const startTime = Date.now();
    const results = {};
    
    // Language detection
    try {
      const languageResult = await comprehend.detectDominantLanguage({
        Text: textToAnalyze
      }).promise();
      
      results.language = languageResult.Languages[0]?.LanguageCode || 'unknown';
      results.languageScore = languageResult.Languages[0]?.Score || 0;
      
      log('DEBUG', 'Language detection completed', {
        language: results.language,
        score: results.languageScore
      });
    } catch (error) {
      log('WARN', 'Language detection failed', { error: error.message });
      results.language = 'unknown';
      results.languageScore = 0;
    }
    
    // Sentiment analysis
    try {
      const sentimentResult = await comprehend.detectSentiment({
        Text: textToAnalyze,
        LanguageCode: results.language === 'unknown' ? 'en' : results.language
      }).promise();
      
      results.sentiment = {
        Sentiment: sentimentResult.Sentiment,
        SentimentScore: sentimentResult.SentimentScore
      };
      
      log('DEBUG', 'Sentiment analysis completed', {
        sentiment: results.sentiment.Sentiment,
        positive: results.sentiment.SentimentScore.Positive,
        negative: results.sentiment.SentimentScore.Negative,
        neutral: results.sentiment.SentimentScore.Neutral,
        mixed: results.sentiment.SentimentScore.Mixed
      });
    } catch (error) {
      log('WARN', 'Sentiment analysis failed', { error: error.message });
      results.sentiment = null;
    }
    
    // Entity detection
    try {
      const entityResult = await comprehend.detectEntities({
        Text: textToAnalyze,
        LanguageCode: results.language === 'unknown' ? 'en' : results.language
      }).promise();
      
      results.entities = entityResult.Entities.map(entity => ({
        Text: entity.Text,
        Type: entity.Type,
        Score: entity.Score,
        BeginOffset: entity.BeginOffset,
        EndOffset: entity.EndOffset
      }));
      
      log('DEBUG', 'Entity detection completed', {
        entitiesCount: results.entities.length,
        types: [...new Set(results.entities.map(e => e.Type))]
      });
    } catch (error) {
      log('WARN', 'Entity detection failed', { error: error.message });
      results.entities = [];
    }
    
    // Key phrases extraction
    try {
      const keyPhrasesResult = await comprehend.detectKeyPhrases({
        Text: textToAnalyze,
        LanguageCode: results.language === 'unknown' ? 'en' : results.language
      }).promise();
      
      results.keyPhrases = keyPhrasesResult.KeyPhrases.map(phrase => ({
        Text: phrase.Text,
        Score: phrase.Score,
        BeginOffset: phrase.BeginOffset,
        EndOffset: phrase.EndOffset
      }));
      
      log('DEBUG', 'Key phrases extraction completed', {
        keyPhrasesCount: results.keyPhrases.length
      });
    } catch (error) {
      log('WARN', 'Key phrases extraction failed', { error: error.message });
      results.keyPhrases = [];
    }
    
    // Syntax analysis (PII detection requires special setup, skipping for now)
    try {
      const syntaxResult = await comprehend.detectSyntax({
        Text: textToAnalyze,
        LanguageCode: results.language === 'unknown' ? 'en' : results.language
      }).promise();
      
      results.syntax = syntaxResult.SyntaxTokens.map(token => ({
        Text: token.Text,
        PartOfSpeech: token.PartOfSpeech.Tag,
        Score: token.PartOfSpeech.Score,
        BeginOffset: token.BeginOffset,
        EndOffset: token.EndOffset
      }));
      
      log('DEBUG', 'Syntax analysis completed', {
        tokensCount: results.syntax.length
      });
    } catch (error) {
      log('WARN', 'Syntax analysis failed', { error: error.message });
      results.syntax = [];
    }
    
    const processingTime = (Date.now() - startTime) / 1000;
    results.processingTime = processingTime;
    results.analyzedTextLength = textToAnalyze.length;
    results.originalTextLength = text.length;
    results.truncated = text.length > maxLength;
    
    return results;
    
  } catch (error) {
    log('ERROR', 'Comprehend processing error', { error: error.message });
    
    // Return empty results on error
    return {
      language: 'unknown',
      languageScore: 0,
      sentiment: null,
      entities: [],
      keyPhrases: [],
      syntax: [],
      processingTime: 0,
      analyzedTextLength: 0,
      originalTextLength: text.length,
      truncated: false,
      error: error.message
    };
  }
}

async function updateFileStatus(tableName, fileId, status, additionalData = {}) {
  try {
    // First, get the current item to find the upload_timestamp
    const getParams = {
      TableName: tableName,
      KeyConditionExpression: 'file_id = :fileId',
      ExpressionAttributeValues: {
        ':fileId': fileId
      },
      Limit: 1
    };
    
    const result = await dynamodb.query(getParams).promise();
    
    if (result.Items.length === 0) {
      throw new Error(`File with ID ${fileId} not found in database`);
    }
    
    const uploadTimestamp = result.Items[0].upload_timestamp;
    
    // Update the item
    const updateParams = {
      TableName: tableName,
      Key: {
        file_id: fileId,
        upload_timestamp: uploadTimestamp
      },
      UpdateExpression: 'SET processing_status = :status, last_updated = :updated',
      ExpressionAttributeValues: {
        ':status': status,
        ':updated': new Date().toISOString()
      }
    };
    
    // Add additional data to the update
    Object.keys(additionalData).forEach((key, index) => {
      const attrName = `:val${index}`;
      updateParams.UpdateExpression += `, ${key} = ${attrName}`;
      updateParams.ExpressionAttributeValues[attrName] = additionalData[key];
    });
    
    await dynamodb.update(updateParams).promise();
    log('DEBUG', 'DynamoDB status updated', { fileId, status });
    
  } catch (error) {
    log('ERROR', 'Failed to update file status', {
      fileId,
      status,
      error: error.message
    });
    throw error;
  }
}

async function storeProcessingResults(fileId, results) {
  const resultsTable = process.env.DYNAMODB_TABLE.replace('-file-metadata', '-processing-results');
  
  try {
    const params = {
      TableName: resultsTable,
      Item: {
        file_id: fileId,
        ...results
      }
    };
    
    await dynamodb.put(params).promise();
    log('DEBUG', 'Processing results stored', { fileId, table: resultsTable });
    
  } catch (error) {
    log('ERROR', 'Failed to store processing results', {
      fileId,
      error: error.message
    });
    throw error;
  }
}

// Batch-only execution logic
async function runBatchJob() {
  // Validate required environment variables
  const requiredVars = ['S3_BUCKET', 'S3_KEY', 'FILE_ID', 'DYNAMODB_TABLE'];
  const missingVars = requiredVars.filter(varName => !process.env[varName]);
  
  if (missingVars.length > 0) {
    log('ERROR', 'Missing required environment variables', { missingVars });
    process.exit(1);
  }
  
  log('INFO', 'Starting batch processing', {
    batchJobId: process.env.AWS_BATCH_JOB_ID,
    jobQueue: process.env.AWS_BATCH_JQ_NAME
  });
  
  try {
    const result = await processS3File();
    log('INFO', 'Batch job completed successfully', {
      processingDuration: result.processing_duration,
      textExtracted: result.analysis.word_count > 0
    });
    process.exit(0);
  } catch (error) {
    log('ERROR', 'Batch job failed', {
      error: error.message,
      stack: error.stack
    });
    process.exit(1);
  }
}

// Enhanced error handling
process.on('SIGTERM', () => {
  log('INFO', 'Received SIGTERM, shutting down gracefully');
  process.exit(0);
});

process.on('SIGINT', () => {
  log('INFO', 'Received SIGINT, shutting down gracefully');
  process.exit(0);
});

process.on('uncaughtException', (error) => {
  log('ERROR', 'Uncaught exception', {
    error: error.message,
    stack: error.stack
  });
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  log('ERROR', 'Unhandled promise rejection', {
    reason: reason?.toString(),
    promise: promise?.toString()
  });
  process.exit(1);
});

// Graceful startup with error handling
setTimeout(() => {
  runBatchJob().catch((error) => {
    log('ERROR', 'Batch job startup failed', {
      error: error.message,
      stack: error.stack
    });
    process.exit(1);
  });
}, 100); // Minimal delay for logging setup