# REMOVED: S3 EventBridge rules - Long batch now uses direct SQS messages from uploader
# REMOVED: SQS polling EventBridge rules - Long batch now uses direct SQS event source mapping
# This simplifies the architecture and improves performance by removing the 1-minute polling delay

# Note: Both long-batch and short-batch now use direct SQS event source mapping
# This provides consistent architecture and immediate processing without EventBridge overhead

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