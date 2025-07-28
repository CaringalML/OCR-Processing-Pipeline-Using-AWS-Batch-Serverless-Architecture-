# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"
  tags = var.common_tags
}

# Archive files for Lambda functions
data "archive_file" "uploader_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/s3_uploader/s3_uploader.zip"
  source_file = "${path.module}/lambda_functions/s3_uploader/s3_uploader.py"
}

data "archive_file" "reader_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/lambda_reader/lambda_reader.zip"
  source_file = "${path.module}/lambda_functions/lambda_reader/lambda_reader.py"
}

data "archive_file" "sqs_processor_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/sqs_to_batch_submitter/sqs_to_batch_submitter.zip"
  source_file = "${path.module}/lambda_functions/sqs_to_batch_submitter/sqs_to_batch_submitter.py"
}

data "archive_file" "batch_reconciliation_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/batch_status_reconciliation/batch_status_reconciliation.zip"
  source_file = "${path.module}/lambda_functions/batch_status_reconciliation/batch_status_reconciliation.py"
}

data "archive_file" "dead_job_detector_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/dead_job_detector/dead_job_detector.zip"
  source_file = "${path.module}/lambda_functions/dead_job_detector/dead_job_detector.py"
}

data "archive_file" "search_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/document_search/document_search.zip"
  source_dir  = "${path.module}/lambda_functions/document_search"
  excludes    = ["requirements.txt", "package", "__pycache__"]
}

data "archive_file" "editor_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/ocr_editor/ocr_editor.zip"
  source_file = "${path.module}/lambda_functions/ocr_editor/ocr_editor.py"
}

data "archive_file" "deleter_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/file_deleter/file_deleter.zip"
  source_file = "${path.module}/lambda_functions/file_deleter/file_deleter.py"
}

data "archive_file" "restorer_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/file_restorer/file_restorer.zip"
  source_file = "${path.module}/lambda_functions/file_restorer/file_restorer.py"
}

data "archive_file" "recycle_bin_reader_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/recycle_bin_reader/recycle_bin_reader.zip"
  source_file = "${path.module}/lambda_functions/recycle_bin_reader/recycle_bin_reader.py"
}

# Uploader Lambda Function (S3 file uploader)
resource "aws_lambda_function" "uploader" {
  filename         = data.archive_file.uploader_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-uploader"
  role             = aws_iam_role.uploader_role.arn
  handler          = "s3_uploader.lambda_handler"
  runtime          = "python3.9"
  timeout          = 300
  memory_size      = 256
  source_code_hash = data.archive_file.uploader_zip.output_base64sha256

  environment {
    variables = {
      UPLOAD_BUCKET_NAME = aws_s3_bucket.upload_bucket.id
      DYNAMODB_TABLE     = aws_dynamodb_table.file_metadata.name
      LOG_LEVEL          = "INFO"
      ENVIRONMENT        = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.uploader_policy,
    aws_cloudwatch_log_group.s3_uploader_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-uploader"
  })
}

# Reader Lambda Function (DynamoDB reader with CloudFront URLs)
resource "aws_lambda_function" "reader" {
  filename         = data.archive_file.reader_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-reader"
  role             = aws_iam_role.reader_role.arn
  handler          = "lambda_reader.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.reader_zip.output_base64sha256

  environment {
    variables = {
      METADATA_TABLE    = aws_dynamodb_table.file_metadata.name
      RESULTS_TABLE     = aws_dynamodb_table.processing_results.name
      CLOUDFRONT_DOMAIN = aws_cloudfront_distribution.s3_distribution.domain_name
      LOG_LEVEL         = "INFO"
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.reader_policy,
    aws_cloudwatch_log_group.lambda_reader_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-reader"
  })
}

# Search Lambda Function (Document search)
resource "aws_lambda_function" "search" {
  filename         = data.archive_file.search_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-search"
  role             = aws_iam_role.search_role.arn
  handler          = "document_search.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 512
  source_code_hash = data.archive_file.search_zip.output_base64sha256

  environment {
    variables = {
      METADATA_TABLE    = aws_dynamodb_table.file_metadata.name
      RESULTS_TABLE     = aws_dynamodb_table.processing_results.name
      CLOUDFRONT_DOMAIN = aws_cloudfront_distribution.s3_distribution.domain_name
      LOG_LEVEL         = "INFO"
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.search_policy,
    aws_cloudwatch_log_group.document_search_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-search"
  })
}

# Editor Lambda Function (OCR results editor)
resource "aws_lambda_function" "editor" {
  filename         = data.archive_file.editor_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-editor"
  role             = aws_iam_role.editor_role.arn
  handler          = "ocr_editor.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.editor_zip.output_base64sha256

  environment {
    variables = {
      METADATA_TABLE = aws_dynamodb_table.file_metadata.name
      RESULTS_TABLE  = aws_dynamodb_table.processing_results.name
      LOG_LEVEL      = "INFO"
      ENVIRONMENT    = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.editor_policy,
    aws_cloudwatch_log_group.ocr_editor_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-editor"
  })
}

# SQS to Batch Processor Lambda Function
resource "aws_lambda_function" "sqs_batch_processor" {
  filename         = data.archive_file.sqs_processor_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-sqs-batch-processor"
  role             = aws_iam_role.sqs_processor_role.arn
  handler          = "sqs_to_batch_submitter.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.sqs_processor_zip.output_base64sha256

  environment {
    variables = {
      BATCH_JOB_QUEUE      = aws_batch_job_queue.main.name
      BATCH_JOB_DEFINITION = aws_batch_job_definition.main.name
      SQS_QUEUE_URL        = aws_sqs_queue.batch_queue.url
      DYNAMODB_TABLE       = aws_dynamodb_table.file_metadata.name
      LOG_LEVEL            = "INFO"
      ENVIRONMENT          = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.sqs_processor_policy,
    aws_cloudwatch_log_group.sqs_to_batch_submitter_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-sqs-batch-processor"
  })
}

# CloudWatch Log Groups - S3 Uploader (handles file uploads with metadata)
resource "aws_cloudwatch_log_group" "s3_uploader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-s3-uploader"
  retention_in_days = 7  # 1 week retention
  tags              = merge(var.common_tags, {
    Purpose = "S3 file upload with metadata logging"
    Function = "s3_uploader"
  })
}

# CloudWatch Log Groups - Lambda Reader (retrieves processed files with metadata)
resource "aws_cloudwatch_log_group" "lambda_reader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-lambda-reader"
  retention_in_days = 7  # 1 week retention
  tags              = merge(var.common_tags, {
    Purpose = "File retrieval and metadata display logging"
    Function = "lambda_reader"
  })
}

# CloudWatch Log Groups - Document Search (fuzzy search functionality)
resource "aws_cloudwatch_log_group" "document_search_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-document-search"
  retention_in_days = 7  # 1 week retention
  tags              = merge(var.common_tags, {
    Purpose = "Document fuzzy search logging"
    Function = "document_search"
  })
}

# CloudWatch Log Groups - OCR Editor (edits refined and formatted text)
resource "aws_cloudwatch_log_group" "ocr_editor_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-ocr-editor"
  retention_in_days = 7  # 1 week retention
  tags              = merge(var.common_tags, {
    Purpose = "OCR result editing logging"
    Function = "ocr_editor"
  })
}

# CloudWatch Log Groups - SQS to Batch Submitter (processes queue messages)
resource "aws_cloudwatch_log_group" "sqs_to_batch_submitter_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-sqs-to-batch-submitter"
  retention_in_days = 7  # 1 week retention
  tags              = merge(var.common_tags, {
    Purpose = "SQS to AWS Batch job submission logging"
    Function = "sqs_to_batch_submitter"
  })
}

# Batch Status Reconciliation Lambda Function
resource "aws_lambda_function" "batch_status_reconciliation" {
  filename         = data.archive_file.batch_reconciliation_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-batch-status-reconciliation"
  role             = aws_iam_role.batch_reconciliation_role.arn
  handler          = "batch_status_reconciliation.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.batch_reconciliation_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.file_metadata.name
      LOG_LEVEL      = "INFO"
      ENVIRONMENT    = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.batch_reconciliation_policy,
    aws_cloudwatch_log_group.batch_status_reconciliation_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-batch-status-reconciliation"
  })
}

# CloudWatch Log Groups - Batch Status Reconciliation (updates job status)
resource "aws_cloudwatch_log_group" "batch_status_reconciliation_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-batch-status-reconciliation"
  retention_in_days = 7  # 1 week retention
  tags              = merge(var.common_tags, {
    Purpose = "AWS Batch job status reconciliation logging"
    Function = "batch_status_reconciliation"
  })
}

# Dead Job Detector Lambda Function
resource "aws_lambda_function" "dead_job_detector" {
  filename         = data.archive_file.dead_job_detector_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-dead-job-detector"
  role             = aws_iam_role.dead_job_detector_role.arn
  handler          = "dead_job_detector.lambda_handler"
  runtime          = "python3.9"
  timeout          = 300
  memory_size      = 256
  source_code_hash = data.archive_file.dead_job_detector_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE           = aws_dynamodb_table.file_metadata.name
      MAX_PROCESSING_MINUTES   = "120"
      LOG_LEVEL               = "INFO"
      ENVIRONMENT             = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.dead_job_detector_policy,
    aws_cloudwatch_log_group.dead_job_detector_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-dead-job-detector"
  })
}

# CloudWatch Log Groups - Dead Job Detector (detects stuck jobs)
resource "aws_cloudwatch_log_group" "dead_job_detector_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-dead-job-detector"
  retention_in_days = 7  # 1 week retention
  tags              = merge(var.common_tags, {
    Purpose = "Dead job detection and cleanup logging"
    Function = "dead_job_detector"
  })
}

# File Deleter Lambda Function (moves files to recycle bin)
resource "aws_lambda_function" "deleter" {
  filename         = data.archive_file.deleter_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-file-deleter"
  role             = aws_iam_role.deleter_role.arn
  handler          = "file_deleter.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.deleter_zip.output_base64sha256

  environment {
    variables = {
      METADATA_TABLE    = aws_dynamodb_table.file_metadata.name
      RESULTS_TABLE     = aws_dynamodb_table.processing_results.name
      RECYCLE_BIN_TABLE = aws_dynamodb_table.recycle_bin.name
      S3_BUCKET         = aws_s3_bucket.upload_bucket.id
      LOG_LEVEL         = "INFO"
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.deleter_policy,
    aws_cloudwatch_log_group.file_deleter_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-file-deleter"
  })
}

# File Restorer Lambda Function (restores files from recycle bin)
resource "aws_lambda_function" "restorer" {
  filename         = data.archive_file.restorer_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-file-restorer"
  role             = aws_iam_role.restorer_role.arn
  handler          = "file_restorer.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.restorer_zip.output_base64sha256

  environment {
    variables = {
      METADATA_TABLE    = aws_dynamodb_table.file_metadata.name
      RESULTS_TABLE     = aws_dynamodb_table.processing_results.name
      RECYCLE_BIN_TABLE = aws_dynamodb_table.recycle_bin.name
      LOG_LEVEL         = "INFO"
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.restorer_policy,
    aws_cloudwatch_log_group.file_restorer_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-file-restorer"
  })
}

# Recycle Bin Reader Lambda Function (lists files in recycle bin)
resource "aws_lambda_function" "recycle_bin_reader" {
  filename         = data.archive_file.recycle_bin_reader_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-recycle-bin-reader"
  role             = aws_iam_role.recycle_bin_reader_role.arn
  handler          = "recycle_bin_reader.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.recycle_bin_reader_zip.output_base64sha256

  environment {
    variables = {
      RECYCLE_BIN_TABLE = aws_dynamodb_table.recycle_bin.name
      LOG_LEVEL         = "INFO"
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.recycle_bin_reader_policy,
    aws_cloudwatch_log_group.recycle_bin_reader_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-recycle-bin-reader"
  })
}

# CloudWatch Log Groups - File Deleter
resource "aws_cloudwatch_log_group" "file_deleter_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-file-deleter"
  retention_in_days = 7
  tags              = merge(var.common_tags, {
    Purpose = "File deletion and recycle bin logging"
    Function = "file_deleter"
  })
}

# CloudWatch Log Groups - File Restorer
resource "aws_cloudwatch_log_group" "file_restorer_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-file-restorer"
  retention_in_days = 7
  tags              = merge(var.common_tags, {
    Purpose = "File restoration from recycle bin logging"
    Function = "file_restorer"
  })
}

# CloudWatch Log Groups - Recycle Bin Reader
resource "aws_cloudwatch_log_group" "recycle_bin_reader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-recycle-bin-reader"
  retention_in_days = 7
  tags              = merge(var.common_tags, {
    Purpose = "Recycle bin listing and querying logging"
    Function = "recycle_bin_reader"
  })
}