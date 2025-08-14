# Dead Letter Queue for failed messages
resource "aws_sqs_queue" "batch_dlq" {
  name                       = "${var.project_name}-${var.environment}-batch-dlq"
  delay_seconds              = var.sqs_delay_seconds
  max_message_size           = var.sqs_max_message_size
  message_retention_seconds  = var.sqs_message_retention_long # 14 days
  receive_wait_time_seconds  = var.sqs_receive_wait_time_short_polling
  visibility_timeout_seconds = var.sqs_visibility_timeout_standard

  lifecycle {
    ignore_changes = [
      name,
      delay_seconds,
      max_message_size,
      message_retention_seconds,
      receive_wait_time_seconds,
      visibility_timeout_seconds
    ]
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-batch-dlq"
  })
}

# Main SQS Queue for Long Batch processing - Direct SQS with Long Polling
resource "aws_sqs_queue" "batch_queue" {
  name                       = "${var.project_name}-${var.environment}-batch-queue"
  delay_seconds              = var.sqs_delay_seconds
  max_message_size           = var.sqs_max_message_size
  message_retention_seconds  = var.sqs_message_retention_long         # 14 days
  receive_wait_time_seconds  = var.sqs_receive_wait_time_long_polling # Long polling enabled for efficiency
  visibility_timeout_seconds = var.sqs_visibility_timeout_batch       # 16 minutes (AWS Batch timeout + buffer)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.batch_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count_standard # Only 2 retries before DLQ
  })

  tags = merge(var.common_tags, {
    Name         = "${var.project_name}-${var.environment}-batch-queue"
    Type         = "Long-Batch Processing"
    Architecture = "Direct-SQS-Trigger"
  })
}

# Note: No SQS Queue Policy needed - Long batch now uses direct SQS messages from Lambda uploader
# Both long-batch and short-batch now use direct API SQS messages for consistency

# CloudWatch Alarm for DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.project_name}-${var.environment}-dlq-messages"
  comparison_operator = var.cloudwatch_comparison_operator_greater_than
  evaluation_periods  = var.cloudwatch_evaluation_periods_single
  metric_name         = var.cloudwatch_metric_messages_visible
  namespace           = var.cloudwatch_namespace_sqs
  period              = var.cloudwatch_period_standard
  statistic           = var.cloudwatch_statistic_average
  threshold           = var.cloudwatch_threshold_zero
  alarm_description   = <<-EOF
    ALERT: Messages detected in Long Batch Dead Letter Queue!
    
    Environment: ${var.environment}
    Project: ${var.project_name}
    Queue: ${var.project_name}-${var.environment}-batch-dlq
    
    This indicates that messages have failed processing after 2 attempts.
    
    Possible causes:
    - Batch job submission failures
    - Invalid message format
    - Lambda function errors
    - AWS Batch service issues
    
    Action required:
    1. Check CloudWatch Logs for Lambda function errors
    2. Review failed messages in DLQ via AWS Console
    3. Check AWS Batch job queue for failed jobs
    4. Investigate and fix root cause
    5. Redrive messages from DLQ once issue is resolved
  EOF
  treat_missing_data  = var.cloudwatch_treat_missing_data

  dimensions = {
    QueueName = aws_sqs_queue.batch_dlq.name
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = var.common_tags
}

# ========================================
# SHORT BATCH SQS QUEUES
# ========================================

# Dead Letter Queue for failed short batch messages
resource "aws_sqs_queue" "short_batch_dlq" {
  name                       = "${var.project_name}-${var.environment}-short-batch-dlq"
  delay_seconds              = var.sqs_delay_seconds
  max_message_size           = var.sqs_max_message_size
  message_retention_seconds  = var.sqs_message_retention_long # 14 days
  receive_wait_time_seconds  = var.sqs_receive_wait_time_short_polling
  visibility_timeout_seconds = var.sqs_visibility_timeout_standard

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-short-batch-dlq"
    Purpose = "Dead letter queue for failed short batch processing"
  })
}

# Main SQS Queue for Short Batch processing with short polling for speed
resource "aws_sqs_queue" "short_batch_queue" {
  name                       = "${var.project_name}-${var.environment}-short-batch-queue"
  delay_seconds              = var.sqs_delay_seconds
  max_message_size           = var.sqs_max_message_size
  message_retention_seconds  = var.sqs_message_retention_short         # 1 day (shorter than long batch)
  receive_wait_time_seconds  = var.sqs_receive_wait_time_short_polling # Short polling for immediate processing
  visibility_timeout_seconds = var.sqs_visibility_timeout_short_batch  # 20 minutes (higher for reliability)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.short_batch_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count_high # Try 3 times before sending to DLQ
  })

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-short-batch-queue"
    Purpose = "Queue for short batch Lambda processing with short polling for speed"
  })
}

# DLQ alarms moved to cloudwatch.tf for centralized monitoring
# Additional CloudWatch Alarms for enhanced DLQ monitoring

# Alarm for messages aging in Long Batch DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_message_age" {
  alarm_name          = "${var.project_name}-${var.environment}-dlq-message-age"
  comparison_operator = var.cloudwatch_comparison_operator_greater_than
  evaluation_periods  = var.cloudwatch_evaluation_periods_single
  metric_name         = var.cloudwatch_metric_message_age
  namespace           = var.cloudwatch_namespace_sqs
  period              = var.cloudwatch_period_standard
  statistic           = var.cloudwatch_statistic_maximum
  threshold           = var.cloudwatch_threshold_message_age_batch # 1 hour
  alarm_description   = <<-DESC
    WARNING: Messages in Long Batch DLQ are aging\!
    
    Environment: ${var.environment}
    Queue: ${var.project_name}-${var.environment}-batch-dlq
    
    Messages have been in the DLQ for more than 1 hour.
    This requires immediate attention to prevent message loss.
    
    The DLQ retention period is 14 days - messages will be permanently lost after this time.
  DESC
  treat_missing_data  = var.cloudwatch_treat_missing_data

  dimensions = {
    QueueName = aws_sqs_queue.batch_dlq.name
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = var.common_tags
}

# Alarm for high message count in Long Batch DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_high_message_count" {
  alarm_name          = "${var.project_name}-${var.environment}-dlq-high-count"
  comparison_operator = var.cloudwatch_comparison_operator_greater_than
  evaluation_periods  = var.cloudwatch_evaluation_periods_double
  metric_name         = var.cloudwatch_metric_messages_visible
  namespace           = var.cloudwatch_namespace_sqs
  period              = var.cloudwatch_period_standard
  statistic           = var.cloudwatch_statistic_average
  threshold           = var.cloudwatch_threshold_high_count_batch
  alarm_description   = <<-DESC
    CRITICAL: High number of messages in Long Batch DLQ\!
    
    Environment: ${var.environment}
    Queue: ${var.project_name}-${var.environment}-batch-dlq
    Threshold: More than 10 messages
    
    This indicates a systemic issue affecting multiple messages.
    Immediate investigation required to prevent further failures.
  DESC
  treat_missing_data  = var.cloudwatch_treat_missing_data

  dimensions = {
    QueueName = aws_sqs_queue.batch_dlq.name
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = var.common_tags
}

# Alarm for messages aging in Short Batch DLQ
resource "aws_cloudwatch_metric_alarm" "short_batch_dlq_message_age" {
  alarm_name          = "${var.project_name}-${var.environment}-short-batch-dlq-message-age"
  comparison_operator = var.cloudwatch_comparison_operator_greater_than
  evaluation_periods  = var.cloudwatch_evaluation_periods_single
  metric_name         = var.cloudwatch_metric_message_age
  namespace           = var.cloudwatch_namespace_sqs
  period              = var.cloudwatch_period_standard
  statistic           = var.cloudwatch_statistic_maximum
  threshold           = var.cloudwatch_threshold_message_age_short # 30 minutes
  alarm_description   = <<-DESC
    WARNING: Messages in Short Batch DLQ are aging\!
    
    Environment: ${var.environment}
    Queue: ${var.project_name}-${var.environment}-short-batch-dlq
    
    Messages have been in the DLQ for more than 30 minutes.
    Short batch jobs should be processed quickly - this indicates a problem.
    
    The DLQ retention period is 14 days - messages will be permanently lost after this time.
  DESC
  treat_missing_data  = var.cloudwatch_treat_missing_data

  dimensions = {
    QueueName = aws_sqs_queue.short_batch_dlq.name
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = var.common_tags
}

# Alarm for high message count in Short Batch DLQ
resource "aws_cloudwatch_metric_alarm" "short_batch_dlq_high_message_count" {
  alarm_name          = "${var.project_name}-${var.environment}-short-batch-dlq-high-count"
  comparison_operator = var.cloudwatch_comparison_operator_greater_than
  evaluation_periods  = var.cloudwatch_evaluation_periods_double
  metric_name         = var.cloudwatch_metric_messages_visible
  namespace           = var.cloudwatch_namespace_sqs
  period              = var.cloudwatch_period_standard
  statistic           = var.cloudwatch_statistic_average
  threshold           = var.cloudwatch_threshold_high_count_short
  alarm_description   = <<-DESC
    CRITICAL: High number of messages in Short Batch DLQ\!
    
    Environment: ${var.environment}
    Queue: ${var.project_name}-${var.environment}-short-batch-dlq
    Threshold: More than 5 messages
    
    Short batch processing should be reliable - multiple failures indicate a critical issue.
    Immediate investigation required.
  DESC
  treat_missing_data  = var.cloudwatch_treat_missing_data

  dimensions = {
    QueueName = aws_sqs_queue.short_batch_dlq.name
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = var.common_tags
}

# ========================================
# INVOICE PROCESSING SQS QUEUES
# ========================================

# Dead Letter Queue for failed invoice messages
resource "aws_sqs_queue" "invoice_dlq" {
  name                       = "${var.project_name}-${var.environment}-invoice-dlq"
  delay_seconds              = var.sqs_delay_seconds
  max_message_size           = var.sqs_max_message_size
  message_retention_seconds  = var.sqs_message_retention_long # 14 days
  receive_wait_time_seconds  = var.sqs_receive_wait_time_short_polling
  visibility_timeout_seconds = var.sqs_visibility_timeout_standard

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-invoice-dlq"
    Purpose = "Dead letter queue for failed invoice processing"
  })
}

# Main SQS Queue for Invoice processing
resource "aws_sqs_queue" "invoice_queue" {
  name                       = "${var.project_name}-${var.environment}-invoice-queue"
  delay_seconds              = var.sqs_delay_seconds
  max_message_size           = var.sqs_max_message_size
  message_retention_seconds  = 86400                                   # 1 day
  receive_wait_time_seconds  = var.sqs_receive_wait_time_short_polling # Short polling for immediate processing
  visibility_timeout_seconds = var.sqs_visibility_timeout_invoice      # 30 minutes for invoice processing

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.invoice_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count_high # Try 3 times before sending to DLQ
  })

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-invoice-queue"
    Purpose = "Queue for specialized invoice OCR processing with Claude AI"
  })
}

# CloudWatch Alarm for Invoice DLQ
resource "aws_cloudwatch_metric_alarm" "invoice_dlq_messages" {
  alarm_name          = "${var.project_name}-${var.environment}-invoice-dlq-messages"
  comparison_operator = var.cloudwatch_comparison_operator_greater_than
  evaluation_periods  = var.cloudwatch_evaluation_periods_single
  metric_name         = var.cloudwatch_metric_messages_visible
  namespace           = var.cloudwatch_namespace_sqs
  period              = var.cloudwatch_period_standard
  statistic           = var.cloudwatch_statistic_average
  threshold           = var.cloudwatch_threshold_zero
  alarm_description   = <<-EOF
    ALERT: Messages detected in Invoice Processing Dead Letter Queue!
    
    Environment: ${var.environment}
    Project: ${var.project_name}
    Queue: ${var.project_name}-${var.environment}-invoice-dlq
    
    This indicates that invoice processing messages have failed after 3 attempts.
    
    Possible causes:
    - Claude API errors or rate limits
    - S3 access issues
    - DynamoDB write failures
    - Invalid invoice format or unreadable content
    - Timeout issues (current limit: 30 minutes)
    - Budget limit exceeded
    
    Action required:
    1. Check invoice_processor Lambda logs in CloudWatch
    2. Review failed messages in DLQ via AWS Console
    3. Verify Claude API key and budget limits
    4. Check S3 bucket permissions and file accessibility
    5. Validate invoice file formats and readability
    6. Investigate and fix root cause
    7. Redrive messages from DLQ once issue is resolved
  EOF
  treat_missing_data  = var.cloudwatch_treat_missing_data

  dimensions = {
    QueueName = aws_sqs_queue.invoice_dlq.name
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = var.common_tags
}

# Alarm for high message count in Invoice DLQ
resource "aws_cloudwatch_metric_alarm" "invoice_dlq_high_message_count" {
  alarm_name          = "${var.project_name}-${var.environment}-invoice-dlq-high-count"
  comparison_operator = var.cloudwatch_comparison_operator_greater_than
  evaluation_periods  = var.cloudwatch_evaluation_periods_double
  metric_name         = var.cloudwatch_metric_messages_visible
  namespace           = var.cloudwatch_namespace_sqs
  period              = var.cloudwatch_period_standard
  statistic           = var.cloudwatch_statistic_average
  threshold           = var.cloudwatch_threshold_high_count_short
  alarm_description   = <<-DESC
    CRITICAL: High number of messages in Invoice DLQ\!
    
    Environment: ${var.environment}
    Queue: ${var.project_name}-${var.environment}-invoice-dlq
    Threshold: More than 5 messages
    
    Multiple invoice processing failures indicate a systemic issue.
    This could impact business operations - immediate investigation required.
  DESC
  treat_missing_data  = var.cloudwatch_treat_missing_data

  dimensions = {
    QueueName = aws_sqs_queue.invoice_dlq.name
  }

  alarm_actions = [aws_sns_topic.critical_alerts.arn]

  tags = var.common_tags
}

