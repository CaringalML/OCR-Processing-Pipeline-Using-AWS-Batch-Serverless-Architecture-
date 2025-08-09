# CloudWatch Log Groups - AWS Batch Jobs (OCR processing container logs)
resource "aws_cloudwatch_log_group" "aws_batch_ocr_logs" {
  name              = "/aws/batch/${var.project_name}-${var.environment}-long-batch-processor"
  retention_in_days = var.cloudwatch_log_retention_days
  skip_destroy      = var.cloudwatch_skip_destroy
  tags              = merge(var.common_tags, {
    Purpose = "AWS Batch OCR processing container logs"
    Function = "aws_batch_ocr"
  })
}

# CloudWatch Log Groups - API Gateway (REST API access logs)
resource "aws_cloudwatch_log_group" "api_gateway_access_logs" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}-api-access"
  retention_in_days = var.cloudwatch_log_retention_days
  skip_destroy      = var.cloudwatch_skip_destroy
  tags              = merge(var.common_tags, {
    Purpose = "API Gateway access and error logging"
    Function = "api_gateway"
  })
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
        width  = var.cloudwatch_dashboard_widget_width
        height = var.cloudwatch_dashboard_widget_height
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
          stat   = var.cloudwatch_metric_stat_average
          region = var.aws_region
          title  = "Lambda Metrics"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = var.cloudwatch_dashboard_widget_width
        height = var.cloudwatch_dashboard_widget_height
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
        width  = var.cloudwatch_dashboard_widget_width
        height = var.cloudwatch_dashboard_widget_height
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name],
            [".", "Latency", ".", "."],
            [".", "4XXError", ".", "."],
            [".", "5XXError", ".", "."]
          ]
          period = 300
          stat   = var.cloudwatch_metric_stat_average
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
  comparison_operator = var.cloudwatch_alarm_comparison_operator
  evaluation_periods  = var.cloudwatch_alarm_evaluation_periods_default
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = var.cloudwatch_alarm_period_medium
  statistic           = var.cloudwatch_metric_stat_sum
  threshold           = var.cloudwatch_alarm_lambda_error_threshold
  alarm_description   = "This metric monitors lambda errors"
  alarm_actions       = []

  dimensions = {
    FunctionName = aws_lambda_function.uploader.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "batch_failed_jobs" {
  alarm_name          = "${var.project_name}-batch-failed-jobs"
  comparison_operator = var.cloudwatch_alarm_comparison_operator
  evaluation_periods  = var.cloudwatch_alarm_evaluation_periods_single
  metric_name         = "FailedJobs"
  namespace           = "AWS/Batch"
  period              = var.cloudwatch_alarm_period_default
  statistic           = var.cloudwatch_metric_stat_sum
  threshold           = var.cloudwatch_alarm_batch_failure_threshold
  alarm_description   = "This metric monitors batch job failures"
  alarm_actions       = []

  dimensions = {
    JobQueue = aws_batch_job_queue.main.name
  }
}

# ========================================
# SECURITY AND RATE LIMITING MONITORING
# ========================================

# SNS Topic for Security Alerts
resource "aws_sns_topic" "security_alerts" {
  name = "${var.project_name}-${var.environment}-security-alerts"
  tags = merge(var.common_tags, {
    Purpose = "Security and rate limiting notifications"
    AlertType = "Security"
  })
}

# SNS Topic Subscription for security alerts email
resource "aws_sns_topic_subscription" "security_email_alerts" {
  topic_arn = aws_sns_topic.security_alerts.arn
  protocol  = var.sns_email_protocol
  endpoint  = var.admin_alert_email
}

# ========================================

# CloudWatch Alarm for 4XX errors (includes rate limiting)
resource "aws_cloudwatch_metric_alarm" "api_4xx_errors" {
  count = var.enable_rate_limiting ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-api-4xx-errors"
  comparison_operator = var.cloudwatch_alarm_comparison_operator
  evaluation_periods  = var.cloudwatch_alarm_evaluation_periods_default
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = var.cloudwatch_alarm_period_default
  statistic           = var.cloudwatch_metric_stat_sum
  threshold           = var.cloudwatch_alarm_api_4xx_threshold
  alarm_description   = "This metric monitors API Gateway 4XX errors (including rate limiting)"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  ok_actions          = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = merge(var.common_tags, {
    AlarmType = "RateLimiting"
    Severity  = "Medium"
  })
}

# CloudWatch Alarm for high API Gateway latency
resource "aws_cloudwatch_metric_alarm" "api_high_latency" {
  count = var.enable_rate_limiting ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-api-high-latency"
  comparison_operator = var.cloudwatch_alarm_comparison_operator
  evaluation_periods  = var.cloudwatch_alarm_evaluation_periods_default
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = var.cloudwatch_alarm_period_default
  statistic           = var.cloudwatch_metric_stat_average
  threshold           = var.cloudwatch_alarm_latency_threshold  # 5 seconds
  alarm_description   = "This metric monitors API Gateway latency"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  ok_actions          = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = merge(var.common_tags, {
    AlarmType = "Performance"
    Severity  = "Low"
  })
}

# CloudWatch Alarm for unusual request spikes
resource "aws_cloudwatch_metric_alarm" "api_request_spike" {
  count = var.enable_rate_limiting ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-api-request-spike"
  comparison_operator = var.cloudwatch_alarm_comparison_operator
  evaluation_periods  = var.cloudwatch_alarm_evaluation_periods_default
  metric_name         = "Count"
  namespace           = "AWS/ApiGateway"
  period              = var.cloudwatch_alarm_period_default
  statistic           = var.cloudwatch_metric_stat_sum
  threshold           = var.api_throttling_rate_limit * 300 * 0.8  # 80% of max capacity
  alarm_description   = "This metric monitors unusual request spikes that may indicate abuse"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  ok_actions          = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = merge(var.common_tags, {
    AlarmType = "Security"
    Severity  = "Medium"
  })
}

# CloudWatch Alarm for rapid consecutive 429 errors (rate limiting)
resource "aws_cloudwatch_metric_alarm" "rate_limit_abuse" {
  count = var.enable_rate_limiting ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-rate-limit-abuse"
  comparison_operator = var.cloudwatch_alarm_comparison_operator
  evaluation_periods  = var.cloudwatch_alarm_evaluation_periods_single
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = var.cloudwatch_alarm_period_short  # 1 minute window
  statistic           = var.cloudwatch_metric_stat_sum
  threshold           = var.cloudwatch_alarm_rate_limit_threshold  # More than 50 rate limit errors in 1 minute
  alarm_description   = "Detects rapid rate limiting violations indicating potential abuse"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  ok_actions          = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = merge(var.common_tags, {
    AlarmType = "Security"
    Severity  = "High"
    ThreatLevel = "Suspicious"
  })
}

# CloudWatch Alarm for 5XX errors indicating system stress
resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  count = var.enable_rate_limiting ? 1 : 0

  alarm_name          = "${var.project_name}-${var.environment}-api-5xx-errors"
  comparison_operator = var.cloudwatch_alarm_comparison_operator
  evaluation_periods  = var.cloudwatch_alarm_evaluation_periods_default
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = var.cloudwatch_alarm_period_default
  statistic           = var.cloudwatch_metric_stat_sum
  threshold           = var.cloudwatch_alarm_api_5xx_threshold
  alarm_description   = "This metric monitors API Gateway 5XX errors indicating system stress"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  ok_actions          = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = merge(var.common_tags, {
    AlarmType = "System"
    Severity  = "High"
  })
}

# CloudWatch Alarm for Lambda function errors (potential attack vectors)
resource "aws_cloudwatch_metric_alarm" "lambda_error_spike" {
  alarm_name          = "${var.project_name}-${var.environment}-lambda-error-spike"
  comparison_operator = var.cloudwatch_alarm_comparison_operator
  evaluation_periods  = var.cloudwatch_alarm_evaluation_periods_default
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = var.cloudwatch_alarm_period_default
  statistic           = var.cloudwatch_metric_stat_sum
  threshold           = var.cloudwatch_alarm_api_4xx_threshold
  alarm_description   = "Detects unusual Lambda error spikes that may indicate attacks"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]
  ok_actions          = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.uploader.function_name
  }

  tags = merge(var.common_tags, {
    AlarmType = "Security"
    Severity  = "Medium"
    Component = "Lambda"
  })
}

# CloudWatch Dashboard for Rate Limiting Monitoring
resource "aws_cloudwatch_dashboard" "rate_limiting_dashboard" {
  count = var.enable_rate_limiting ? 1 : 0

  dashboard_name = "${var.project_name}-${var.environment}-rate-limiting"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = var.cloudwatch_dashboard_widget_width
        height = var.cloudwatch_dashboard_widget_height

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name],
            [".", "4XXError", ".", ".", ".", "."],
            [".", "5XXError", ".", ".", ".", "."]
          ]
          view    = var.cloudwatch_dashboard_view_timeseries
          stacked = var.cloudwatch_dashboard_stacked
          region  = var.aws_region
          title   = "API Gateway Request Metrics"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = var.cloudwatch_dashboard_widget_width
        height = var.cloudwatch_dashboard_widget_height

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name],
            [".", "IntegrationLatency", ".", ".", ".", "."]
          ]
          view    = var.cloudwatch_dashboard_view_timeseries
          stacked = var.cloudwatch_dashboard_stacked
          region  = var.aws_region
          title   = "API Gateway Latency Metrics"
          period  = 300
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = var.cloudwatch_dashboard_widget_width
        height = var.cloudwatch_dashboard_widget_height

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name, "Method", "POST", "Resource", "/upload"],
            [".", ".", ".", ".", ".", ".", ".", "GET", ".", "/processed"]
          ]
          view    = var.cloudwatch_dashboard_view_timeseries
          stacked = var.cloudwatch_dashboard_stacked
          region  = var.aws_region
          title   = "Method-specific Request Counts"
          period  = 300
          stat    = "Sum"
        }
      },
      {
        type   = "number"
        x      = 12
        y      = 6
        width  = var.cloudwatch_dashboard_widget_width
        height = var.cloudwatch_dashboard_widget_height

        properties = {
          metrics = [
            ["AWS/ApiGateway", "4XXError", "ApiName", aws_api_gateway_rest_api.main.name, "Stage", aws_api_gateway_stage.main.stage_name]
          ]
          view    = var.cloudwatch_dashboard_view_single_value
          region  = var.aws_region
          title   = "Rate Limiting Events (4XX Errors)"
          period  = 300
          stat    = "Sum"
        }
      }
    ]
  })

}