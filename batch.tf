resource "aws_batch_compute_environment" "main" {
  compute_environment_name = "${var.project_name}-${var.environment}-compute-env"
  type                     = var.batch_compute_environment_type
  state                    = var.batch_compute_environment_state
  service_role             = aws_iam_role.batch_service_role.arn

  compute_resources {
    type               = var.batch_compute_resources_type
    max_vcpus          = var.batch_max_vcpus
    security_group_ids = [aws_security_group.batch.id]
    subnets            = aws_subnet.private[*].id
  }

  depends_on = [aws_iam_role_policy_attachment.batch_service_role_policy]

  tags = var.common_tags
}

resource "aws_batch_job_queue" "main" {
  name     = "${var.project_name}-${var.environment}-job-queue"
  state    = var.batch_job_queue_state
  priority = var.batch_job_queue_priority

  compute_environment_order {
    order               = var.batch_compute_environment_order
    compute_environment = aws_batch_compute_environment.main.arn
  }

  depends_on = [aws_batch_compute_environment.main]

  tags = var.common_tags
}

resource "aws_batch_job_definition" "main" {
  name = "${var.project_name}-${var.environment}-job-def"
  type = var.batch_job_definition_type

  platform_capabilities = var.batch_platform_capabilities

  container_properties = jsonencode({
    # Note: Update this image URL after manually pushing to ECR
    # Example: 123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/ocr-processor-app:latest
    image = "${aws_ecr_repository.main.repository_url}:latest"

    resourceRequirements = [
      {
        type  = "VCPU"
        value = var.batch_container_vcpu
      },
      {
        type  = "MEMORY"
        value = var.batch_container_memory
      }
    ]

    networkConfiguration = {
      assignPublicIp = var.batch_assign_public_ip
    }

    executionRoleArn = aws_iam_role.batch_task_execution_role.arn
    jobRoleArn       = aws_iam_role.batch_task_role.arn

    logConfiguration = {
      logDriver = var.batch_log_driver
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.aws_batch_ocr_logs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = var.batch_log_stream_prefix
      }
    }
  })

  retry_strategy {
    attempts = var.batch_retry_attempts
  }

  timeout {
    attempt_duration_seconds = var.batch_job_timeout_hours * 3600 # Convert hours to seconds
  }

  depends_on = [
    aws_iam_role_policy_attachment.batch_task_execution_role_policy,
    aws_cloudwatch_log_group.aws_batch_ocr_logs
  ]

  lifecycle {
    ignore_changes = [
      container_properties,
      platform_capabilities
    ]
  }
}