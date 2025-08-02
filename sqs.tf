# Dead Letter Queue for failed messages
resource "aws_sqs_queue" "batch_dlq" {
  name                       = "${var.project_name}-${var.environment}-batch-dlq"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600 # 14 days
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 300

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

# Main SQS Queue for Batch processing
resource "aws_sqs_queue" "batch_queue" {
  name                       = "${var.project_name}-${var.environment}-batch-queue"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.batch_dlq.arn
    maxReceiveCount     = var.sqs_max_receive_count
  })

  lifecycle {
    ignore_changes = [
      name,
      delay_seconds,
      max_message_size,
      message_retention_seconds,
      receive_wait_time_seconds,
      visibility_timeout_seconds,
      redrive_policy
    ]
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-batch-queue"
  })
}

# SQS Queue Policy to allow EventBridge to send messages
resource "aws_sqs_queue_policy" "batch_queue_policy" {
  queue_url = aws_sqs_queue.batch_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.batch_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.s3_long_batch_upload_rule.arn
          }
        }
      }
    ]
  })
}

# Short batch queue does not need EventBridge policy - uses direct API SQS messages only

# CloudWatch Alarm for DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.project_name}-${var.environment}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors messages in the DLQ"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.batch_dlq.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.common_tags
}

# ========================================
# SHORT BATCH SQS QUEUES
# ========================================

# Dead Letter Queue for failed short batch messages
resource "aws_sqs_queue" "short_batch_dlq" {
  name                       = "${var.project_name}-${var.environment}-short-batch-dlq"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 1209600 # 14 days
  receive_wait_time_seconds  = 0
  visibility_timeout_seconds = 300

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-short-batch-dlq"
    Purpose = "Dead letter queue for failed short batch processing"
  })
}

# Main SQS Queue for Short Batch processing with short polling for speed
resource "aws_sqs_queue" "short_batch_queue" {
  name                       = "${var.project_name}-${var.environment}-short-batch-queue"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 86400  # 1 day (shorter than long batch)
  receive_wait_time_seconds  = 0      # Short polling for immediate processing
  visibility_timeout_seconds = 1200   # 20 minutes (higher for reliability)

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.short_batch_dlq.arn
    maxReceiveCount     = 3  # Try 3 times before sending to DLQ
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-short-batch-queue"
    Purpose = "Queue for short batch Lambda processing with short polling for speed"
  })
}

# CloudWatch Alarm for Short Batch DLQ
resource "aws_cloudwatch_metric_alarm" "short_batch_dlq_messages" {
  alarm_name          = "${var.project_name}-${var.environment}-short-batch-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "300"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors messages in the Short Batch DLQ"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.short_batch_dlq.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = var.common_tags
}