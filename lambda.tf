# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"
  tags = var.common_tags
}

# SNS Topic Subscription for email alerts
resource "aws_sns_topic_subscription" "admin_email_alerts" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = var.sns_email_protocol
  endpoint  = var.admin_alert_email
}

# Archive files for Lambda functions
data "archive_file" "uploader_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/s3_uploader/s3_uploader.zip"
  source_file = "${path.module}/lambda_functions/s3_uploader/s3_uploader.py"
}

data "archive_file" "invoice_uploader_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/invoice_uploader/invoice_uploader.zip"
  source_file = "${path.module}/lambda_functions/invoice_uploader/invoice_uploader.py"
}

# Null resource to detect changes in invoice processor
resource "null_resource" "invoice_processor_dependencies" {
  triggers = {
    requirements_hash   = filemd5("${path.module}/lambda_functions/invoice_processor/requirements.txt")
    source_code_hash    = filemd5("${path.module}/lambda_functions/invoice_processor/invoice_processor.py")
    install_script_hash = filemd5("${path.module}/lambda_functions/invoice_processor/install_dependencies.sh")
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/lambda_functions/invoice_processor"
    command     = "bash -c 'sed -i \"s/\\r$//\" install_dependencies.sh && chmod +x install_dependencies.sh && ./install_dependencies.sh'"
  }
}

# Create a stable hash based on source file content
locals {
  invoice_processor_hash = base64sha256(join("", [
    filemd5("${path.module}/lambda_functions/invoice_processor/requirements.txt"),
    filemd5("${path.module}/lambda_functions/invoice_processor/invoice_processor.py"),
    filemd5("${path.module}/lambda_functions/invoice_processor/install_dependencies.sh")
  ]))
}

data "archive_file" "invoice_reader_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/invoice_reader/invoice_reader.zip"
  source_file = "${path.module}/lambda_functions/invoice_reader/invoice_reader.py"
}

data "archive_file" "reader_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/lambda_reader/lambda_reader.zip"
  source_file = "${path.module}/lambda_functions/lambda_reader/lambda_reader.py"
}

data "archive_file" "sqs_processor_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/sqs_to_batch_submitter/sqs_to_batch_submitter.zip"
  source_file = "${path.module}/lambda_functions/sqs_to_batch_submitter/sqs_to_batch_submitter.py"
}

data "archive_file" "batch_reconciliation_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/batch_status_reconciliation/batch_status_reconciliation.zip"
  source_file = "${path.module}/lambda_functions/batch_status_reconciliation/batch_status_reconciliation.py"
}

data "archive_file" "dead_job_detector_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/dead_job_detector/dead_job_detector.zip"
  source_file = "${path.module}/lambda_functions/dead_job_detector/dead_job_detector.py"
}

# Null resource to build document search dependencies
resource "null_resource" "document_search_dependencies" {
  triggers = {
    requirements_hash   = filemd5("${path.module}/lambda_functions/document_search/requirements.txt")
    source_code_hash    = filemd5("${path.module}/lambda_functions/document_search/document_search.py")
    install_script_hash = filemd5("${path.module}/lambda_functions/document_search/install_dependencies.sh")
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/lambda_functions/document_search"
    command     = "bash -c 'sed -i \"s/\\r$//\" install_dependencies.sh && chmod +x install_dependencies.sh && LOCAL_BUILD=true ./install_dependencies.sh'"
  }
}

data "archive_file" "search_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/document_search/document_search.zip"
  source_dir  = "${path.module}/lambda_functions/document_search"
  excludes    = ["requirements.txt", "package", "__pycache__", "install_dependencies.sh"]

  depends_on = [null_resource.document_search_dependencies]
}

data "archive_file" "editor_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/ocr_editor/ocr_editor.zip"
  source_file = "${path.module}/lambda_functions/ocr_editor/ocr_editor.py"
}

# Null resource to detect changes in short batch processor
resource "null_resource" "short_batch_processor_dependencies" {
  triggers = {
    requirements_hash   = filemd5("${path.module}/lambda_functions/short_batch_processor/requirements.txt")
    source_code_hash    = filemd5("${path.module}/lambda_functions/short_batch_processor/short_batch_processor.py")
    install_script_hash = filemd5("${path.module}/lambda_functions/short_batch_processor/install_dependencies.sh")
  }

  provisioner "local-exec" {
    working_dir = "${path.module}/lambda_functions/short_batch_processor"
    command     = "bash -c 'sed -i \"s/\\r$//\" install_dependencies.sh && chmod +x install_dependencies.sh && ./install_dependencies.sh'"
  }
}

# Note: short_batch_processor.zip is created by the null_resource provisioner above

# Create a stable hash based on source file content
locals {
  short_batch_processor_hash = base64sha256(join("", [
    filemd5("${path.module}/lambda_functions/short_batch_processor/requirements.txt"),
    filemd5("${path.module}/lambda_functions/short_batch_processor/short_batch_processor.py"),
    filemd5("${path.module}/lambda_functions/short_batch_processor/install_dependencies.sh")
  ]))
}

data "archive_file" "short_batch_submitter_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/short_batch_submitter/short_batch_submitter.zip"
  source_file = "${path.module}/lambda_functions/short_batch_submitter/short_batch_submitter.py"
}

data "archive_file" "deleter_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/file_deleter/file_deleter.zip"
  source_file = "${path.module}/lambda_functions/file_deleter/file_deleter.py"
}

data "archive_file" "restorer_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/file_restorer/file_restorer.zip"
  source_file = "${path.module}/lambda_functions/file_restorer/file_restorer.py"
}

data "archive_file" "recycle_bin_reader_zip" {
  type        = var.archive_file_type
  output_path = "${path.module}/lambda_functions/recycle_bin_reader/recycle_bin_reader.zip"
  source_file = "${path.module}/lambda_functions/recycle_bin_reader/recycle_bin_reader.py"
}

# smart_router removed - routing now integrated into s3_uploader


# Uploader Lambda Function (S3 file uploader)
resource "aws_lambda_function" "uploader" {
  filename         = data.archive_file.uploader_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-uploader"
  role             = aws_iam_role.uploader_role.arn
  handler          = "s3_uploader.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_long
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.uploader_zip.output_base64sha256

  environment {
    variables = {
      UPLOAD_BUCKET_NAME     = aws_s3_bucket.upload_bucket.id
      DYNAMODB_TABLE         = aws_dynamodb_table.processing_results.name
      SHORT_BATCH_QUEUE_URL  = aws_sqs_queue.short_batch_queue.url
      LONG_BATCH_QUEUE_URL   = aws_sqs_queue.batch_queue.url
      FILE_SIZE_THRESHOLD_KB = var.file_size_threshold_kb
      LOG_LEVEL              = var.lambda_log_level
      ENVIRONMENT            = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.uploader_policy,
    aws_cloudwatch_log_group.s3_uploader_logs
  ]

  # Removed ignore_changes to allow code updates

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
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.reader_zip.output_base64sha256

  environment {
    variables = {
      RESULTS_TABLE     = aws_dynamodb_table.processing_results.name
      CLOUDFRONT_DOMAIN = aws_cloudfront_distribution.s3_distribution.domain_name
      LOG_LEVEL         = var.lambda_log_level
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.reader_policy,
    aws_cloudwatch_log_group.lambda_reader_logs
  ]

  # Removed ignore_changes to allow code updates

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
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_medium
  source_code_hash = data.archive_file.search_zip.output_base64sha256

  environment {
    variables = {
      RESULTS_TABLE     = aws_dynamodb_table.processing_results.name
      CLOUDFRONT_DOMAIN = aws_cloudfront_distribution.s3_distribution.domain_name
      LOG_LEVEL         = var.lambda_log_level
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.search_policy,
    aws_cloudwatch_log_group.document_search_logs,
    null_resource.document_search_dependencies
  ]

  # Removed ignore_changes to allow code updates

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
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.editor_zip.output_base64sha256

  environment {
    variables = {
      RESULTS_TABLE  = aws_dynamodb_table.processing_results.name
      LOG_LEVEL      = var.lambda_log_level
      ENVIRONMENT    = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.editor_policy,
    aws_cloudwatch_log_group.ocr_editor_logs
  ]

  # Removed ignore_changes to allow code updates

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-editor"
  })
}

# Short Batch Submitter Lambda Function (API Gateway -> SQS)
resource "aws_lambda_function" "short_batch_submitter" {
  filename         = data.archive_file.short_batch_submitter_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-short-batch-submitter"
  role             = aws_iam_role.short_batch_submitter_role.arn
  handler          = "short_batch_submitter.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_short # Quick response for API Gateway
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.short_batch_submitter_zip.output_base64sha256

  environment {
    variables = {
      SQS_QUEUE_URL  = aws_sqs_queue.short_batch_queue.url
      RESULTS_TABLE  = aws_dynamodb_table.processing_results.name
      LOG_LEVEL      = var.lambda_log_level
      ENVIRONMENT    = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.short_batch_submitter_policy,
    aws_cloudwatch_log_group.short_batch_submitter_logs
  ]

  # Removed ignore_changes to allow code updates

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-short-batch-submitter"
    Purpose = "Submit short batch jobs to SQS queue"
  })
}

# Short Batch Processor Lambda Function (SQS -> Processing)
resource "aws_lambda_function" "short_batch_processor" {
  filename         = "${path.module}/lambda_functions/short_batch_processor/short_batch_processor.zip"
  function_name    = "${var.project_name}-${var.environment}-short-batch-processor"
  role             = aws_iam_role.short_batch_processor_role.arn
  handler          = "short_batch_processor.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_extended # 15 minutes timeout for processing
  memory_size      = var.lambda_memory_large     # More memory for faster processing
  source_code_hash = local.short_batch_processor_hash
  # reserved_concurrent_executions removed due to account limits


  environment {
    variables = {
      DOCUMENTS_TABLE       = aws_dynamodb_table.processing_results.name
      RESULTS_TABLE         = aws_dynamodb_table.processing_results.name
      PROCESSED_BUCKET      = aws_s3_bucket.upload_bucket.id
      DEAD_LETTER_QUEUE_URL = aws_sqs_queue.short_batch_dlq.url
      SNS_TOPIC_ARN         = aws_sns_topic.alerts.arn
      ANTHROPIC_API_KEY     = var.anthropic_api_key
      BUDGET_LIMIT          = var.budget_limit_default
      LOG_LEVEL             = var.lambda_log_level
      ENVIRONMENT           = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.short_batch_processor_policy,
    aws_cloudwatch_log_group.short_batch_processor_logs,
    null_resource.short_batch_processor_dependencies
  ]

  # Removed ignore_changes to allow code updates

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-short-batch-processor"
    Purpose = "Process small files from SQS with comprehensive text refinement"
  })
}

# Lambda Event Source Mapping for Long Batch Queue with Long Polling
resource "aws_lambda_event_source_mapping" "long_batch_sqs_trigger" {
  event_source_arn = aws_sqs_queue.batch_queue.arn
  function_name    = aws_lambda_function.sqs_batch_processor.arn

  # Batch configuration optimized for long polling efficiency
  batch_size                         = var.event_source_batch_size_large         # Process up to 10 messages per invocation
  maximum_batching_window_in_seconds = var.event_source_batching_window_standard # Wait up to 5 seconds to fill batch

  # Enable partial batch response to handle individual message failures
  function_response_types = var.event_source_response_types

  # Configure visibility timeout for long-running batch job submissions
  scaling_config {
    maximum_concurrency = var.event_source_max_concurrency # Limit concurrency to avoid overwhelming AWS Batch
  }

  tags = merge(var.common_tags, {
    Name         = "${var.project_name}-${var.environment}-long-batch-sqs-trigger"
    Purpose      = "Direct SQS trigger for long batch processing"
    Architecture = "SQS-Lambda-Batch"
  })
}

# Lambda Event Source Mapping for Short Batch Queue with Short Polling
resource "aws_lambda_event_source_mapping" "short_batch_sqs_trigger" {
  event_source_arn = aws_sqs_queue.short_batch_queue.arn
  function_name    = aws_lambda_function.short_batch_processor.arn

  # Batch configuration optimized for speed
  batch_size                         = var.event_source_batch_size_single         # Process messages immediately (no batching delay)
  maximum_batching_window_in_seconds = var.event_source_batching_window_immediate # No batching window for immediate processing

  # Enable partial batch response to handle individual message failures
  function_response_types = var.event_source_response_types

  # The queue uses short polling (0 seconds) for immediate message pickup

  depends_on = [
    aws_iam_role_policy_attachment.short_batch_processor_policy
  ]
}

# SQS to Batch Processor Lambda Function
resource "aws_lambda_function" "sqs_batch_processor" {
  filename         = data.archive_file.sqs_processor_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-sqs-batch-processor"
  role             = aws_iam_role.sqs_processor_role.arn
  handler          = "sqs_to_batch_submitter.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.sqs_processor_zip.output_base64sha256

  environment {
    variables = {
      BATCH_JOB_QUEUE      = aws_batch_job_queue.main.name
      BATCH_JOB_DEFINITION = aws_batch_job_definition.main.name
      SQS_QUEUE_URL        = aws_sqs_queue.batch_queue.url
      DYNAMODB_TABLE       = aws_dynamodb_table.processing_results.name
      RESULTS_TABLE        = aws_dynamodb_table.processing_results.name
      LOG_LEVEL            = var.lambda_log_level
      ENVIRONMENT          = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.sqs_processor_policy,
    aws_cloudwatch_log_group.sqs_to_batch_submitter_logs
  ]

  # Removed ignore_changes to allow code updates

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-sqs-batch-processor"
  })
}

# CloudWatch Log Groups - S3 Uploader (handles file uploads with metadata)
resource "aws_cloudwatch_log_group" "s3_uploader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-s3-uploader"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "S3 file upload with metadata logging"
    Function = "s3_uploader"
  })
}

# CloudWatch Log Groups - Lambda Reader (retrieves processed files with metadata)
resource "aws_cloudwatch_log_group" "lambda_reader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-lambda-reader"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "File retrieval and metadata display logging"
    Function = "lambda_reader"
  })
}

# CloudWatch Log Groups - Document Search (fuzzy search functionality)
resource "aws_cloudwatch_log_group" "document_search_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-document-search"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "Document fuzzy search logging"
    Function = "document_search"
  })
}

# CloudWatch Log Groups - OCR Editor (edits refined and formatted text)
resource "aws_cloudwatch_log_group" "ocr_editor_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-ocr-editor"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "OCR result editing logging"
    Function = "ocr_editor"
  })
}

# CloudWatch Log Groups - Short Batch Submitter (submits to SQS)
resource "aws_cloudwatch_log_group" "short_batch_submitter_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-short-batch-submitter"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "Submit short batch jobs to SQS"
    Function = "short_batch_submitter"
  })
}

# CloudWatch Log Groups - Short Batch Processor (processes from SQS)
resource "aws_cloudwatch_log_group" "short_batch_processor_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-short-batch-processor"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "Short batch processing for small files"
    Function = "short_batch_processor"
  })
}

# CloudWatch Log Groups - SQS to Batch Submitter (processes queue messages)
resource "aws_cloudwatch_log_group" "sqs_to_batch_submitter_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-sqs-to-batch-submitter"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "SQS to AWS Batch job submission logging"
    Function = "sqs_to_batch_submitter"
  })
}

# Batch Status Reconciliation Lambda Function
resource "aws_lambda_function" "batch_status_reconciliation" {
  filename         = data.archive_file.batch_reconciliation_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-batch-status-reconciliation"
  role             = aws_iam_role.batch_reconciliation_role.arn
  handler          = "batch_status_reconciliation.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.batch_reconciliation_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.processing_results.name
      LOG_LEVEL      = var.lambda_log_level
      ENVIRONMENT    = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.batch_reconciliation_policy,
    aws_cloudwatch_log_group.batch_status_reconciliation_logs
  ]

  # Removed ignore_changes to allow code updates

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-batch-status-reconciliation"
  })
}

# CloudWatch Log Groups - Batch Status Reconciliation (updates job status)
resource "aws_cloudwatch_log_group" "batch_status_reconciliation_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-batch-status-reconciliation"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "AWS Batch job status reconciliation logging"
    Function = "batch_status_reconciliation"
  })
}

# Dead Job Detector Lambda Function
resource "aws_lambda_function" "dead_job_detector" {
  filename         = data.archive_file.dead_job_detector_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-dead-job-detector"
  role             = aws_iam_role.dead_job_detector_role.arn
  handler          = "dead_job_detector.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_long
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.dead_job_detector_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE         = aws_dynamodb_table.processing_results.name
      MAX_PROCESSING_MINUTES = var.max_processing_minutes
      LOG_LEVEL              = var.lambda_log_level
      ENVIRONMENT            = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.dead_job_detector_policy,
    aws_cloudwatch_log_group.dead_job_detector_logs
  ]

  # Removed ignore_changes to allow code updates

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-dead-job-detector"
  })
}

# CloudWatch Log Groups - Dead Job Detector (detects stuck jobs)
resource "aws_cloudwatch_log_group" "dead_job_detector_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-dead-job-detector"
  retention_in_days = var.cloudwatch_log_retention_days # 1 week retention
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "Dead job detection and cleanup logging"
    Function = "dead_job_detector"
  })
}

# File Deleter Lambda Function (moves files to recycle bin)
resource "aws_lambda_function" "deleter" {
  filename         = data.archive_file.deleter_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-file-deleter"
  role             = aws_iam_role.deleter_role.arn
  handler          = "file_deleter.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.deleter_zip.output_base64sha256

  environment {
    variables = {
      RESULTS_TABLE     = aws_dynamodb_table.processing_results.name
      RECYCLE_BIN_TABLE = aws_dynamodb_table.recycle_bin.name
      S3_BUCKET         = aws_s3_bucket.upload_bucket.id
      LOG_LEVEL         = var.lambda_log_level
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.deleter_policy,
    aws_cloudwatch_log_group.file_deleter_logs
  ]

  # Removed ignore_changes to allow code updates

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
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.restorer_zip.output_base64sha256

  environment {
    variables = {
      RESULTS_TABLE     = aws_dynamodb_table.processing_results.name
      RECYCLE_BIN_TABLE = aws_dynamodb_table.recycle_bin.name
      LOG_LEVEL         = var.lambda_log_level
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.restorer_policy,
    aws_cloudwatch_log_group.file_restorer_logs
  ]

  # Removed ignore_changes to allow code updates

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
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_small
  source_code_hash = data.archive_file.recycle_bin_reader_zip.output_base64sha256

  environment {
    variables = {
      RECYCLE_BIN_TABLE = aws_dynamodb_table.recycle_bin.name
      LOG_LEVEL         = var.lambda_log_level
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.recycle_bin_reader_policy,
    aws_cloudwatch_log_group.recycle_bin_reader_logs
  ]

  # Removed ignore_changes to allow code updates

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-recycle-bin-reader"
  })
}

# Smart Router removed - routing now integrated into s3_uploader Lambda



# CloudWatch Log Groups - File Deleter
resource "aws_cloudwatch_log_group" "file_deleter_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-file-deleter"
  retention_in_days = var.cloudwatch_log_retention_days
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "File deletion and recycle bin logging"
    Function = "file_deleter"
  })
}

# CloudWatch Log Groups - File Restorer
resource "aws_cloudwatch_log_group" "file_restorer_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-file-restorer"
  retention_in_days = var.cloudwatch_log_retention_days
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "File restoration from recycle bin logging"
    Function = "file_restorer"
  })
}

# CloudWatch Log Groups - Recycle Bin Reader
resource "aws_cloudwatch_log_group" "recycle_bin_reader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-recycle-bin-reader"
  retention_in_days = var.cloudwatch_log_retention_days
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "Recycle bin listing and querying logging"
    Function = "recycle_bin_reader"
  })
}

# Smart Router CloudWatch logs removed - routing now integrated into s3_uploader



# ========================================
# INVOICE PROCESSING LAMBDA FUNCTIONS
# ========================================

# Invoice Uploader Lambda Function
resource "aws_lambda_function" "invoice_uploader" {
  filename         = data.archive_file.invoice_uploader_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-invoice-uploader"
  role             = aws_iam_role.invoice_uploader_role.arn
  handler          = "invoice_uploader.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_medium
  source_code_hash = data.archive_file.invoice_uploader_zip.output_base64sha256

  environment {
    variables = {
      UPLOAD_BUCKET     = aws_s3_bucket.upload_bucket.bucket
      INVOICE_TABLE     = aws_dynamodb_table.invoice_processing_results.name
      INVOICE_QUEUE_URL = aws_sqs_queue.invoice_queue.url
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.invoice_uploader_policy,
    aws_cloudwatch_log_group.invoice_uploader_logs
  ]

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-invoice-uploader"
    Purpose = "Specialized uploader for invoice OCR processing"
  })
}

# Invoice Processor Lambda Function
resource "aws_lambda_function" "invoice_processor" {
  filename         = "${path.module}/lambda_functions/invoice_processor/invoice_processor.zip"
  function_name    = "${var.project_name}-${var.environment}-invoice-processor"
  role             = aws_iam_role.invoice_processor_role.arn
  handler          = "invoice_processor.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_extended # 15 minutes for invoice processing
  memory_size      = var.lambda_memory_large
  source_code_hash = local.invoice_processor_hash

  environment {
    variables = {
      DOCUMENTS_TABLE       = aws_dynamodb_table.processing_results.name
      RESULTS_TABLE         = aws_dynamodb_table.processing_results.name
      PROCESSED_BUCKET      = aws_s3_bucket.upload_bucket.bucket
      DEAD_LETTER_QUEUE_URL = "" # Will be set if needed
      SNS_TOPIC_ARN         = aws_sns_topic.alerts.arn
      ANTHROPIC_API_KEY     = var.anthropic_api_key
      BUDGET_LIMIT          = "10.0"
      BUDGET_TRACKING_TABLE = aws_dynamodb_table.ocr_budget_tracking.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.invoice_processor_policy,
    aws_cloudwatch_log_group.invoice_processor_logs,
    null_resource.invoice_processor_dependencies
  ]

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-invoice-processor"
    Purpose = "Specialized invoice OCR processing with Claude AI"
  })
}

# CloudWatch Log Groups - Invoice Uploader
resource "aws_cloudwatch_log_group" "invoice_uploader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-invoice-uploader"
  retention_in_days = var.cloudwatch_log_retention_days
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "Invoice upload and queuing logging"
    Function = "invoice_uploader"
  })
}

# CloudWatch Log Groups - Invoice Processor
resource "aws_cloudwatch_log_group" "invoice_processor_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-invoice-processor"
  retention_in_days = var.cloudwatch_log_retention_days
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "Invoice OCR processing with Claude AI logging"
    Function = "invoice_processor"
  })
}

# Invoice Reader Lambda Function
resource "aws_lambda_function" "invoice_reader" {
  filename         = data.archive_file.invoice_reader_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-invoice-reader"
  role             = aws_iam_role.invoice_reader_role.arn
  handler          = "invoice_reader.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout_standard
  memory_size      = var.lambda_memory_medium
  source_code_hash = data.archive_file.invoice_reader_zip.output_base64sha256

  environment {
    variables = {
      INVOICE_TABLE     = aws_dynamodb_table.invoice_processing_results.name
      CLOUDFRONT_DOMAIN = aws_cloudfront_distribution.s3_distribution.domain_name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.invoice_reader_policy,
    aws_cloudwatch_log_group.invoice_reader_logs
  ]

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-invoice-reader"
    Purpose = "Specialized reader for processed invoice data with enhanced formatting"
  })
}

# CloudWatch Log Groups - Invoice Reader
resource "aws_cloudwatch_log_group" "invoice_reader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-invoice-reader"
  retention_in_days = var.cloudwatch_log_retention_days
  skip_destroy      = var.cloudwatch_log_skip_destroy
  tags = merge(var.common_tags, {
    Purpose  = "Invoice data reading and presentation logging"
    Function = "invoice_reader"
  })
}

# SQS Event Source Mapping for Invoice Processor
resource "aws_lambda_event_source_mapping" "invoice_processor_sqs" {
  event_source_arn                   = aws_sqs_queue.invoice_queue.arn
  function_name                      = aws_lambda_function.invoice_processor.arn
  batch_size                         = 1
  maximum_batching_window_in_seconds = var.event_source_batching_window_standard

  depends_on = [
    aws_iam_role_policy_attachment.invoice_processor_policy
  ]
}