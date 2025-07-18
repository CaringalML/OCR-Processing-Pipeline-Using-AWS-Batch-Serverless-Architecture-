resource "aws_cloudwatch_log_group" "batch_logs" {
  name              = "/aws/batch/${var.project_name}-${var.environment}-job-def"
  retention_in_days = 14
  tags              = var.common_tags
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}-api"
  retention_in_days = var.cleanup_log_retention_days
  tags              = var.common_tags
}

# CloudWatch Dashboard for monitoring
resource "aws_cloudwatch_dashboard" "ocr_processor_dashboard" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.uploader.function_name],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."],
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.reader.function_name],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."],
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.sqs_batch_processor.function_name],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Lambda Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Batch", "SubmittedJobs", "JobQueue", aws_batch_job_queue.main.name],
            [".", "RunnableJobs", ".", "."],
            [".", "RunningJobs", ".", "."],
            [".", "CompletedJobs", ".", "."],
            [".", "FailedJobs", ".", "."]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Batch Job Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name],
            [".", "Latency", ".", "."],
            [".", "4XXError", ".", "."],
            [".", "5XXError", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "API Gateway Metrics"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "120"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = []

  dimensions = {
    FunctionName = aws_lambda_function.uploader.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "batch_failed_jobs" {
  alarm_name          = "${var.project_name}-batch-failed-jobs"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FailedJobs"
  namespace           = "AWS/Batch"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors batch job failures"
  alarm_actions       = []

  dimensions = {
    JobQueue = aws_batch_job_queue.main.name
  }
}