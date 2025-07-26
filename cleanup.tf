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

# CloudWatch Log Group for Cleanup Lambda
# CloudWatch Log Groups - Cleanup Processor (automated resource cleanup)
resource "aws_cloudwatch_log_group" "cleanup_processor_logs" {
  name              = "/aws/lambda/${var.project_name}-${var.environment}-cleanup-processor"
  retention_in_days = 7  # 1 week retention
  tags              = merge(var.common_tags, {
    Purpose = "Automated resource cleanup logging"
    Function = "cleanup_processor"
  })
}

# Cleanup Lambda Function Code
resource "local_file" "cleanup_processor" {
  content = <<EOF
import json
import boto3
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Auto-cleanup Lambda function for AWS Batch OCR processing jobs and ECS tasks
    """
    logger.info("Starting automated cleanup process for OCR processing infrastructure...")
    
    # Initialize AWS clients
    batch_client = boto3.client('batch')
    ecs_client = boto3.client('ecs')
    
    # Configuration from environment variables
    job_queue = os.environ.get('BATCH_JOB_QUEUE')
    cleanup_age_hours = int(os.environ.get('CLEANUP_AGE_HOURS', '24'))
    
    results = {
        "ocr_batch_jobs_cleaned": 0,
        "ecs_tasks_cleaned": 0,
        "errors": []
    }
    
    logger.info(f"OCR Cleanup Configuration - Job Queue: {job_queue}, Cleanup Age: {cleanup_age_hours} hours")
    
    try:
        # Clean up AWS Batch OCR processing jobs
        results["ocr_batch_jobs_cleaned"] = cleanup_ocr_batch_jobs(
            batch_client, job_queue, cleanup_age_hours
        )
        
        # Clean up ECS tasks
        results["ecs_tasks_cleaned"] = cleanup_ecs_tasks(
            ecs_client, cleanup_age_hours
        )
        
        logger.info(f"OCR cleanup completed successfully: {results}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'OCR processing cleanup completed successfully',
                'results': results,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        error_msg = f"OCR cleanup failed: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'OCR processing cleanup failed',
                'error': str(e),
                'results': results,
                'timestamp': datetime.utcnow().isoformat()
            })
        }

def cleanup_ocr_batch_jobs(batch_client: Any, job_queue: str, age_hours: int) -> int:
    """Clean up old AWS Batch OCR processing jobs"""
    logger.info(f"Cleaning up OCR Batch jobs older than {age_hours} hours...")
    
    cleanup_count = 0
    cutoff_time = datetime.utcnow() - timedelta(hours=age_hours)
    
    # Get OCR processing jobs in different states
    job_states = ['SUCCEEDED', 'FAILED']
    
    for state in job_states:
        try:
            response = batch_client.list_jobs(
                jobQueue=job_queue,
                jobStatus=state,
                maxResults=100
            )
            
            jobs_to_cleanup = []
            
            for job in response.get('jobList', []):
                # Only process OCR processor jobs
                if 'ocr-processor-job-' in job.get('jobName', ''):
                    # Check job age
                    if 'stoppedAt' in job:
                        stopped_time = datetime.fromtimestamp(job['stoppedAt'] / 1000)
                        if stopped_time < cutoff_time:
                            jobs_to_cleanup.append(job['jobId'])
                    elif 'createdAt' in job:
                        created_time = datetime.fromtimestamp(job['createdAt'] / 1000)
                        if created_time < cutoff_time:
                            jobs_to_cleanup.append(job['jobId'])
            
            # Clean up old OCR processing jobs
            for job_id in jobs_to_cleanup:
                try:
                    logger.info(f"Found old OCR Batch job for cleanup: {job_id} (state: {state})")
                    # For succeeded/failed jobs, we mainly log them as they auto-cleanup
                    # Only cancel if they're somehow still in a cancelable state
                    job_detail = batch_client.describe_jobs(jobs=[job_id])
                    if job_detail['jobs'] and job_detail['jobs'][0]['jobStatus'] in ['RUNNABLE', 'PENDING', 'RUNNING']:
                        batch_client.cancel_job(
                            jobId=job_id,
                            reason=f"Automated OCR cleanup - job older than {age_hours} hours"
                        )
                        logger.info(f"Cancelled running OCR job: {job_id}")
                    cleanup_count += 1
                except Exception as e:
                    logger.error(f"Failed to process OCR job {job_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error listing {state} OCR jobs: {str(e)}")
    
    logger.info(f"Processed {cleanup_count} OCR Batch jobs")
    return cleanup_count

def cleanup_ecs_tasks(ecs_client: Any, age_hours: int) -> int:
    """Clean up old ECS tasks related to OCR processing"""
    logger.info(f"Cleaning up ECS OCR processing tasks older than {age_hours} hours...")
    
    cleanup_count = 0
    cutoff_time = datetime.utcnow() - timedelta(hours=age_hours)
    
    try:
        # List all clusters
        clusters_response = ecs_client.list_clusters()
        
        for cluster_arn in clusters_response.get('clusterArns', []):
            try:
                # List tasks in cluster
                tasks_response = ecs_client.list_tasks(
                    cluster=cluster_arn,
                    desiredStatus='STOPPED',
                    maxResults=100
                )
                
                if not tasks_response.get('taskArns'):
                    continue
                
                # Describe tasks to get details
                task_details = ecs_client.describe_tasks(
                    cluster=cluster_arn,
                    tasks=tasks_response['taskArns']
                )
                
                tasks_to_cleanup = []
                
                for task in task_details.get('tasks', []):
                    # Only process OCR processor related tasks
                    task_definition = task.get('taskDefinitionArn', '')
                    if 'ocr-processor' in task_definition:
                        if 'stoppedAt' in task:
                            stopped_time = task['stoppedAt'].replace(tzinfo=None)
                            if stopped_time < cutoff_time:
                                tasks_to_cleanup.append(task['taskArn'])
                        elif 'createdAt' in task:
                            created_time = task['createdAt'].replace(tzinfo=None)
                            if created_time < cutoff_time:
                                tasks_to_cleanup.append(task['taskArn'])
                
                # Log old OCR tasks (ECS automatically cleans up stopped tasks)
                for task_arn in tasks_to_cleanup:
                    try:
                        logger.info(f"Found old OCR ECS task: {task_arn}")
                        cleanup_count += 1
                    except Exception as e:
                        logger.info(f"OCR task {task_arn} cleanup note: {str(e)}")
                        
            except Exception as e:
                logger.error(f"Error processing cluster {cluster_arn}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error listing ECS clusters: {str(e)}")
    
    logger.info(f"Processed {cleanup_count} OCR ECS tasks")
    return cleanup_count
EOF

  filename = "${path.module}/lambda_functions/cleanup_processor/cleanup_processor.py"
}

# Automatic cleanup of old Cleanup Lambda files when content changes
resource "null_resource" "cleanup_lambda_cleanup" {
  triggers = {
    # Trigger cleanup when Cleanup Lambda function content changes
    cleanup_content_hash = sha256(local_file.cleanup_processor.content)
    function_name        = "${var.project_name}-auto-cleanup"
    timestamp            = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Cleaning up old Cleanup Lambda files..."
      rm -f ${path.module}/lambda_functions/cleanup_processor/cleanup_processor.zip
      rm -f ${path.module}/lambda_functions/cleanup_processor/cleanup_processor.py.backup
      echo "Cleanup Lambda cleanup completed"
    EOT
  }

  depends_on = [local_file.cleanup_processor]
}

# Create ZIP file for Cleanup Lambda
data "archive_file" "cleanup_lambda_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/cleanup_processor/cleanup_processor.zip"
  source_file = local_file.cleanup_processor.filename

  depends_on = [
    local_file.cleanup_processor,
    null_resource.cleanup_lambda_cleanup
  ]
}

# Cleanup Lambda Function
resource "aws_lambda_function" "cleanup_function" {
  filename         = data.archive_file.cleanup_lambda_zip.output_path
  function_name    = "${var.project_name}-auto-cleanup"
  role             = aws_iam_role.cleanup_lambda_execution.arn
  handler          = "cleanup_processor.lambda_handler"
  runtime          = "python3.9"
  timeout          = 300 # 5 minutes
  memory_size      = 256
  source_code_hash = data.archive_file.cleanup_lambda_zip.output_base64sha256

  environment {
    variables = {
      BATCH_JOB_QUEUE   = aws_batch_job_queue.main.name
      CLEANUP_AGE_HOURS = var.cleanup_age_hours
      LOG_LEVEL         = "INFO"
      PROCESSING_TYPE   = "OCR"
    }
  }

  depends_on = [
    aws_iam_role_policy.cleanup_lambda_policy,
    aws_cloudwatch_log_group.cleanup_processor_logs,
    data.archive_file.cleanup_lambda_zip
  ]

  tags = {
    Name        = "${var.project_name}-auto-cleanup"
    Purpose     = "OCR Processing Cleanup"
    Environment = var.environment
  }
}

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
  arn       = aws_lambda_function.cleanup_function.arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cleanup_function.function_name
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
    FunctionName = aws_lambda_function.cleanup_function.function_name
  }

  tags = {
    Name        = "${var.project_name}-cleanup-alarm"
    Purpose     = "OCR Processing Cleanup Monitoring"
    Environment = var.environment
  }
}