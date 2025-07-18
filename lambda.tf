# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"
  tags = var.common_tags
}

# Archive files for Lambda functions
data "archive_file" "uploader_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_function.zip"
  source_file = "${path.module}/lambda_function.py"
}

data "archive_file" "reader_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_reader.zip"
  source_file = "${path.module}/lambda_reader.py"
}

data "archive_file" "sqs_processor_zip" {
  type        = "zip"
  output_path = "${path.module}/sqs_batch_processor.zip"
  source_file = "${path.module}/sqs_batch_processor.py"
}

data "archive_file" "batch_reconciliation_zip" {
  type        = "zip"
  output_path = "${path.module}/batch_status_reconciliation.zip"
  source_file = "${path.module}/batch_status_reconciliation.py"
}

data "archive_file" "dead_job_detector_zip" {
  type        = "zip"
  output_path = "${path.module}/dead_job_detector.zip"
  source_file = "${path.module}/dead_job_detector.py"
}

# Uploader Lambda Function (S3 file uploader)
resource "aws_lambda_function" "uploader" {
  filename         = data.archive_file.uploader_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-uploader"
  role             = aws_iam_role.uploader_role.arn
  handler          = "lambda_function.lambda_handler"
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
    aws_cloudwatch_log_group.uploader_logs
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
    aws_cloudwatch_log_group.reader_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-reader"
  })
}

# SQS to Batch Processor Lambda Function
resource "aws_lambda_function" "sqs_batch_processor" {
  filename         = data.archive_file.sqs_processor_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-sqs-batch-processor"
  role             = aws_iam_role.sqs_processor_role.arn
  handler          = "sqs_batch_processor.lambda_handler"
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
    aws_cloudwatch_log_group.sqs_processor_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-sqs-batch-processor"
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "uploader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-uploader"
  retention_in_days = var.cleanup_log_retention_days
  tags              = var.common_tags
}

resource "aws_cloudwatch_log_group" "reader_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-reader"
  retention_in_days = var.cleanup_log_retention_days
  tags              = var.common_tags
}

resource "aws_cloudwatch_log_group" "sqs_processor_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-sqs-batch-processor"
  retention_in_days = var.cleanup_log_retention_days
  tags              = var.common_tags
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
    aws_cloudwatch_log_group.batch_reconciliation_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-batch-status-reconciliation"
  })
}

resource "aws_cloudwatch_log_group" "batch_reconciliation_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-batch-status-reconciliation"
  retention_in_days = var.cleanup_log_retention_days
  tags              = var.common_tags
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

resource "aws_cloudwatch_log_group" "dead_job_detector_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-dead-job-detector"
  retention_in_days = var.cleanup_log_retention_days
  tags              = var.common_tags
}