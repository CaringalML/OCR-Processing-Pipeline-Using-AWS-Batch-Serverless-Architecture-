# Auto-Cleanup System for AWS Batch Jobs and ECS Tasks
# This creates automated cleanup using CloudWatch Events and Lambda

# IAM Role for Cleanup Lambda
resource "aws_iam_role" "cleanup_lambda_execution" {
  name = "${var.project_name}-cleanup-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Cleanup Lambda
resource "aws_iam_role_policy" "cleanup_lambda_policy" {
  name = "${var.project_name}-cleanup-lambda-policy"
  role = aws_iam_role.cleanup_lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "batch:ListJobs",
          "batch:CancelJob",
          "batch:TerminateJob",
          "batch:DescribeJobs"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:ListTasks",
          "ecs:DescribeTasks",
          "ecs:StopTask",
          "ecs:ListClusters",
          "ecs:DescribeClusters"
        ]
        Resource = "*"
      }
    ]
  })
}

# Note: Cleanup Lambda Function is defined in lambda.tf as part of the Go lambda functions

# EventBridge Rule for Scheduled Cleanup
resource "aws_cloudwatch_event_rule" "cleanup_schedule" {
  name                = "${var.project_name}-cleanup-schedule"
  description         = "Trigger OCR processing cleanup Lambda on schedule"
  schedule_expression = var.cleanup_schedule_expression
}

# EventBridge Target
resource "aws_cloudwatch_event_target" "cleanup_lambda_target" {
  rule      = aws_cloudwatch_event_rule.cleanup_schedule.name
  target_id = "CleanupLambdaTarget"
  arn       = aws_lambda_function.cleanup_lambda.arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cleanup_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cleanup_schedule.arn
}

# CloudWatch Alarm for Cleanup Failures
resource "aws_cloudwatch_metric_alarm" "cleanup_errors" {
  alarm_name          = "${var.project_name}-cleanup-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors OCR processing cleanup lambda errors"
  alarm_actions       = []

  dimensions = {
    FunctionName = aws_lambda_function.cleanup_lambda.function_name
  }

  tags = {
    Name        = "${var.project_name}-cleanup-alarm"
    Purpose     = "OCR Processing Cleanup Monitoring"
    Environment = var.environment
  }
}