# Local exec to build Go binaries
resource "null_resource" "build_go_lambdas" {
  triggers = {
    uploader_hash = filebase64sha256("${path.module}/file_uploader/src/file_uploader.go")
    reader_hash = filebase64sha256("${path.module}/file_reader/src/file_reader.go")
    sqs_processor_hash = filebase64sha256("${path.module}/sqs_processor/src/sqs_processor.go")
    status_reconciliation_hash = filebase64sha256("${path.module}/batch_status_reconciliation/src/batch_status_reconciliation.go")
    dead_job_detector_hash = filebase64sha256("${path.module}/dead_job_detector/src/dead_job_detector.go")
    cleanup_lambda_hash = filebase64sha256("${path.module}/cleanup_lambda/src/cleanup_lambda.go")
  }

  provisioner "local-exec" {
    command = "cd ${path.module} && cd file_uploader/src && go mod tidy && GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -ldflags='-s -w' -o bootstrap file_uploader.go && zip ../file_uploader.zip bootstrap && cd ../.. && cd file_reader/src && go mod tidy && GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -ldflags='-s -w' -o bootstrap file_reader.go && zip ../file_reader.zip bootstrap && cd ../.. && cd sqs_processor/src && go mod tidy && GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -ldflags='-s -w' -o bootstrap sqs_processor.go && zip ../sqs_processor.zip bootstrap && cd ../.. && cd batch_status_reconciliation/src && go mod tidy && GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -ldflags='-s -w' -o bootstrap batch_status_reconciliation.go && zip ../batch_status_reconciliation.zip bootstrap && cd ../.. && cd dead_job_detector/src && go mod tidy && GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -ldflags='-s -w' -o bootstrap dead_job_detector.go && zip ../dead_job_detector.zip bootstrap && cd ../.. && cd cleanup_lambda/src && go mod tidy && GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -ldflags='-s -w' -o bootstrap cleanup_lambda.go && zip ../cleanup_lambda.zip bootstrap && cd ../.."
  }
}

# Archive files for Lambda functions (using build script output)
data "archive_file" "uploader_zip" {
  type        = "zip"
  source_file = "${path.module}/file_uploader/src/bootstrap"
  output_path = "${path.module}/file_uploader/file_uploader.zip"
  depends_on  = [null_resource.build_go_lambdas]
}

data "archive_file" "reader_zip" {
  type        = "zip"
  source_file = "${path.module}/file_reader/src/bootstrap"
  output_path = "${path.module}/file_reader/file_reader.zip"
  depends_on  = [null_resource.build_go_lambdas]
}

data "archive_file" "sqs_processor_zip" {
  type        = "zip"
  source_file = "${path.module}/sqs_processor/src/bootstrap"
  output_path = "${path.module}/sqs_processor/sqs_processor.zip"
  depends_on  = [null_resource.build_go_lambdas]
}

data "archive_file" "batch_reconciliation_zip" {
  type        = "zip"
  source_file = "${path.module}/batch_status_reconciliation/src/bootstrap"
  output_path = "${path.module}/batch_status_reconciliation/batch_status_reconciliation.zip"
  depends_on  = [null_resource.build_go_lambdas]
}

data "archive_file" "dead_job_detector_zip" {
  type        = "zip"
  source_file = "${path.module}/dead_job_detector/src/bootstrap"
  output_path = "${path.module}/dead_job_detector/dead_job_detector.zip"
  depends_on  = [null_resource.build_go_lambdas]
}

data "archive_file" "cleanup_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/cleanup_lambda/src/bootstrap"
  output_path = "${path.module}/cleanup_lambda/cleanup_lambda.zip"
  depends_on  = [null_resource.build_go_lambdas]
}

# Uploader Lambda Function (S3 file uploader)
resource "aws_lambda_function" "uploader" {
  filename         = data.archive_file.uploader_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-uploader"
  role             = aws_iam_role.uploader_role.arn
  handler          = "bootstrap"
  runtime          = "provided.al2"
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
  handler          = "bootstrap"
  runtime          = "provided.al2"
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
  handler          = "bootstrap"
  runtime          = "provided.al2"
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

resource "aws_cloudwatch_log_group" "cleanup_lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-cleanup-lambda"
  retention_in_days = var.cleanup_log_retention_days
  tags              = var.common_tags
}

# Batch Status Reconciliation Lambda Function
resource "aws_lambda_function" "batch_status_reconciliation" {
  filename         = data.archive_file.batch_reconciliation_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-batch-status-reconciliation"
  role             = aws_iam_role.batch_reconciliation_role.arn
  handler          = "bootstrap"
  runtime          = "provided.al2"
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

# Dead Job Detector Lambda Function
resource "aws_lambda_function" "dead_job_detector" {
  filename         = data.archive_file.dead_job_detector_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-dead-job-detector"
  role             = aws_iam_role.dead_job_detector_role.arn
  handler          = "bootstrap"
  runtime          = "provided.al2"
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

# Cleanup Lambda Function (Automated cleanup of old jobs and tasks)
resource "aws_lambda_function" "cleanup_lambda" {
  filename         = data.archive_file.cleanup_lambda_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-cleanup-lambda"
  role             = aws_iam_role.cleanup_lambda_execution.arn
  handler          = "bootstrap"
  runtime          = "provided.al2"
  timeout          = 300
  memory_size      = 256
  source_code_hash = data.archive_file.cleanup_lambda_zip.output_base64sha256

  environment {
    variables = {
      BATCH_JOB_QUEUE   = aws_batch_job_queue.main.name
      CLEANUP_AGE_HOURS = var.cleanup_age_hours
      LOG_LEVEL         = "INFO"
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy.cleanup_lambda_policy,
    aws_cloudwatch_log_group.cleanup_lambda_logs
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-cleanup-lambda"
  })
}