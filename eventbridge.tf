# EventBridge Rule for S3 Upload Events
resource "aws_cloudwatch_event_rule" "s3_upload_rule" {
  name        = "${var.project_name}-${var.environment}-s3-upload-rule"
  description = "Capture S3 upload events and trigger batch processing"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.upload_bucket.id]
      }
    }
  })

  tags = var.common_tags
}

# EventBridge Target - SQS Queue
resource "aws_cloudwatch_event_target" "sqs_target" {
  rule      = aws_cloudwatch_event_rule.s3_upload_rule.name
  target_id = "SendToSQS"
  arn       = aws_sqs_queue.batch_queue.arn


  retry_policy {
    maximum_event_age_in_seconds = var.eventbridge_max_age_seconds
    maximum_retry_attempts       = var.eventbridge_retry_attempts
  }
}

# EventBridge Rule for SQS to Batch
resource "aws_cloudwatch_event_rule" "sqs_to_batch_rule" {
  name                = "${var.project_name}-${var.environment}-sqs-batch-rule"
  description         = "Process SQS messages by submitting Batch jobs"
  schedule_expression = "rate(1 minute)"
  state               = "ENABLED"

  tags = var.common_tags
}

# Lambda function is defined in lambda.tf

# EventBridge Target - Lambda for SQS processing
resource "aws_cloudwatch_event_target" "lambda_batch_job_submitter" {
  rule      = aws_cloudwatch_event_rule.sqs_to_batch_rule.name
  target_id = "ProcessSQSMessages"
  arn       = aws_lambda_function.batch_job_submitter.arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge_batch_job_submitter" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_job_submitter.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.sqs_to_batch_rule.arn
}

# EventBridge Rule for AWS Batch Job State Changes
resource "aws_cloudwatch_event_rule" "batch_job_state_change_rule" {
  name        = "${var.project_name}-${var.environment}-batch-job-state-change"
  description = "Capture AWS Batch job state changes"

  event_pattern = jsonencode({
    source      = ["aws.batch"]
    detail-type = ["Batch Job State Change"]
    detail = {
      jobQueue = [aws_batch_job_queue.main.arn]
      jobStatus = ["SUCCEEDED", "FAILED"]
    }
  })

  tags = var.common_tags
}

# EventBridge Target - Lambda for Batch job state reconciliation
resource "aws_cloudwatch_event_target" "lambda_batch_reconciliation" {
  rule      = aws_cloudwatch_event_rule.batch_job_state_change_rule.name
  target_id = "BatchJobStateReconciliation"
  arn       = aws_lambda_function.batch_status_reconciliation.arn
}

# Lambda permission for Batch state change EventBridge
resource "aws_lambda_permission" "allow_eventbridge_batch_reconciliation" {
  statement_id  = "AllowExecutionFromEventBridgeBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.batch_status_reconciliation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.batch_job_state_change_rule.arn
}

# EventBridge Rule for Dead Job Detection (runs every 30 minutes)
resource "aws_cloudwatch_event_rule" "dead_job_detection_rule" {
  name                = "${var.project_name}-${var.environment}-dead-job-detection"
  description         = "Detect and handle jobs stuck in processing status"
  schedule_expression = "rate(30 minutes)"
  state               = "ENABLED"

  tags = var.common_tags
}

# EventBridge Target - Lambda for Dead Job Detection
resource "aws_cloudwatch_event_target" "lambda_dead_job_detector" {
  rule      = aws_cloudwatch_event_rule.dead_job_detection_rule.name
  target_id = "DeadJobDetection"
  arn       = aws_lambda_function.dead_job_detector.arn
}

# Lambda permission for Dead Job Detection EventBridge
resource "aws_lambda_permission" "allow_eventbridge_dead_job_detector" {
  statement_id  = "AllowExecutionFromEventBridgeDeadJob"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dead_job_detector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.dead_job_detection_rule.arn
}