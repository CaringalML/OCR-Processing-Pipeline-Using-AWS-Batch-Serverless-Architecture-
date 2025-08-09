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
    source      = var.eventbridge_batch_event_source
    detail-type = var.eventbridge_batch_detail_type
    detail = {
      jobQueue = [aws_batch_job_queue.main.arn]
      jobStatus = var.eventbridge_batch_job_status
    }
  })

  tags = var.common_tags
}

# EventBridge Target - Lambda for Batch job state reconciliation
resource "aws_cloudwatch_event_target" "lambda_batch_reconciliation" {
  rule      = aws_cloudwatch_event_rule.batch_job_state_change_rule.name
  target_id = var.eventbridge_batch_reconciliation_target_id
  arn       = aws_lambda_function.batch_status_reconciliation.arn
}

# Lambda permission for Batch state change EventBridge
resource "aws_lambda_permission" "allow_eventbridge_batch_reconciliation" {
  statement_id  = var.eventbridge_batch_permission_statement_id
  action        = var.eventbridge_lambda_action
  function_name = aws_lambda_function.batch_status_reconciliation.function_name
  principal     = var.eventbridge_lambda_principal
  source_arn    = aws_cloudwatch_event_rule.batch_job_state_change_rule.arn
}

# EventBridge Rule for Dead Job Detection (runs every 30 minutes)
resource "aws_cloudwatch_event_rule" "dead_job_detection_rule" {
  name                = "${var.project_name}-${var.environment}-dead-job-detection"
  description         = "Detect and handle jobs stuck in processing status"
  schedule_expression = var.eventbridge_dead_job_schedule_expression
  state               = var.eventbridge_rule_state

  tags = var.common_tags
}

# EventBridge Target - Lambda for Dead Job Detection
resource "aws_cloudwatch_event_target" "lambda_dead_job_detector" {
  rule      = aws_cloudwatch_event_rule.dead_job_detection_rule.name
  target_id = var.eventbridge_dead_job_detection_target_id
  arn       = aws_lambda_function.dead_job_detector.arn
}

# Lambda permission for Dead Job Detection EventBridge
resource "aws_lambda_permission" "allow_eventbridge_dead_job_detector" {
  statement_id  = var.eventbridge_dead_job_permission_statement_id
  action        = var.eventbridge_lambda_action
  function_name = aws_lambda_function.dead_job_detector.function_name
  principal     = var.eventbridge_lambda_principal
  source_arn    = aws_cloudwatch_event_rule.dead_job_detection_rule.arn
}