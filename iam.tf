# Lambda execution role
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_batch_policy" {
  name = "${var.project_name}-lambda-batch-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "batch:SubmitJob",
          "batch:DescribeJobs",
          "batch:ListJobs"
        ]
        Resource = var.iam_wildcard_resource
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# AWS Batch service role
resource "aws_iam_role" "batch_service_role" {
  count = var.deployment_mode == "full" ? 1 : 0
  name  = "${var.project_name}-batch-service-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.batch_service_principal
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service_role_policy" {
  count      = var.deployment_mode == "full" ? 1 : 0
  role       = aws_iam_role.batch_service_role[0].name
  policy_arn = var.aws_batch_service_role_policy_arn
}

# ECS instance role for Batch
resource "aws_iam_role" "ecs_instance_role" {
  count = var.deployment_mode == "full" ? 1 : 0
  name  = "${var.project_name}-ecs-instance-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.ec2_service_principal
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role_policy" {
  count      = var.deployment_mode == "full" ? 1 : 0
  role       = aws_iam_role.ecs_instance_role[0].name
  policy_arn = var.ecs_container_service_role_policy_arn
}

resource "aws_iam_instance_profile" "ecs_instance_profile" {
  count = var.deployment_mode == "full" ? 1 : 0
  name  = "${var.project_name}-ecs-instance-profile"
  role  = aws_iam_role.ecs_instance_role[0].name
}

# Task execution role for Batch jobs
resource "aws_iam_role" "batch_task_execution_role" {
  count = var.deployment_mode == "full" ? 1 : 0
  name  = "${var.project_name}-batch-task-execution-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.ecs_tasks_service_principal
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_task_execution_role_policy" {
  count      = var.deployment_mode == "full" ? 1 : 0
  role       = aws_iam_role.batch_task_execution_role[0].name
  policy_arn = var.ecs_task_execution_role_policy_arn
}

# Task role for Batch jobs
resource "aws_iam_role" "batch_task_role" {
  count = var.deployment_mode == "full" ? 1 : 0
  name  = "${var.project_name}-batch-task-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.ecs_tasks_service_principal
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "batch_task_policy" {
  count = var.deployment_mode == "full" ? 1 : 0
  name  = "${var.project_name}-batch-task-policy"
  role  = aws_iam_role.batch_task_role[0].id

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = var.iam_wildcard_resource
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "s3:GetObject",
          "s3:HeadObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:PutItem"
        ]
        Resource = [
          aws_dynamodb_table.processing_results.arn,
          aws_dynamodb_table.processing_results.arn
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "textract:StartDocumentAnalysis",
          "textract:GetDocumentAnalysis",
          "textract:StartDocumentTextDetection",
          "textract:GetDocumentTextDetection"
        ]
        Resource = var.iam_wildcard_resource
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "comprehend:DetectDominantLanguage",
          "comprehend:DetectEntities",
          "comprehend:DetectKeyPhrases",
          "comprehend:DetectSentiment",
          "comprehend:DetectSyntax",
          "comprehend:DetectPiiEntities"
        ]
        Resource = var.iam_wildcard_resource
      },
    ]
  })
}

# Uploader Lambda Role
resource "aws_iam_role" "uploader_role" {
  name = "${var.project_name}-${var.environment}-uploader-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Reader Lambda Role
resource "aws_iam_role" "reader_role" {
  name = "${var.project_name}-${var.environment}-reader-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Search Lambda Role
resource "aws_iam_role" "search_role" {
  name = "${var.project_name}-${var.environment}-search-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}


# Finalizer Lambda Role
resource "aws_iam_role" "finalizer_role" {
  name = "${var.project_name}-${var.environment}-finalizer-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Finalized Editor Lambda Role
resource "aws_iam_role" "finalized_editor_role" {
  name = "${var.project_name}-${var.environment}-finalized-editor-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Short Batch Processor Lambda Role
resource "aws_iam_role" "short_batch_processor_role" {
  name = "${var.project_name}-${var.environment}-short-batch-processor-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Short Batch Submitter Lambda Role
resource "aws_iam_role" "short_batch_submitter_role" {
  name = "${var.project_name}-${var.environment}-short-batch-submitter-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# SQS Processor Lambda Role (Full Mode Only)
resource "aws_iam_role" "sqs_processor_role" {
  count = var.deployment_mode == "full" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-sqs-processor-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Uploader Lambda Policy
resource "aws_iam_policy" "uploader_policy" {
  name = "${var.project_name}-${var.environment}-uploader-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.processing_results.arn
      },
      # SQS - Send messages to processing queues
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = concat([
          aws_sqs_queue.short_batch_queue.arn
        ], var.deployment_mode == "full" ? [aws_sqs_queue.batch_queue[0].arn] : [])
      }
    ]
  })
}

# Reader Lambda Policy
resource "aws_iam_policy" "reader_policy" {
  name = "${var.project_name}-${var.environment}-reader-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.processing_results.arn,
          "${aws_dynamodb_table.processing_results.arn}/index/*",
          aws_dynamodb_table.ocr_finalized.arn,
          "${aws_dynamodb_table.ocr_finalized.arn}/index/*",
          aws_dynamodb_table.edit_history.arn,
          "${aws_dynamodb_table.edit_history.arn}/index/*"
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "batch:DescribeJobs"
        ]
        Resource = "*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:*:log-group:/aws/batch/job:*",
          "arn:aws:logs:${var.aws_region}:*:log-group:/aws/batch/ocr-processor-batch-long-batch-processor:*",
          "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/ocr-processor-batch-sqs-batch-processor:*"
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:GetQueueAttributes"
        ]
        Resource = "arn:aws:sqs:${var.aws_region}:*:ocr-processor-batch-batch-queue"
      }
    ]
  })
}

# Search Lambda Policy
resource "aws_iam_policy" "search_policy" {
  name = "${var.project_name}-${var.environment}-search-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:GetItem"
        ]
        Resource = [
          aws_dynamodb_table.ocr_finalized.arn,
          "${aws_dynamodb_table.ocr_finalized.arn}/index/*"
        ]
      }
    ]
  })
}


# Finalizer Lambda Policy
resource "aws_iam_policy" "finalizer_policy" {
  name = "${var.project_name}-${var.environment}-finalizer-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.processing_results.arn
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.ocr_finalized.arn,
          "${aws_dynamodb_table.ocr_finalized.arn}/index/*"
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:PutItem"
        ]
        Resource = [
          aws_dynamodb_table.edit_history.arn,
          "${aws_dynamodb_table.edit_history.arn}/index/*"
        ]
      }
    ]
  })
}

# Finalized Editor Lambda Policy
resource "aws_iam_policy" "finalized_editor_policy" {
  name = "${var.project_name}-${var.environment}-finalized-editor-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.ocr_finalized.arn,
          "${aws_dynamodb_table.ocr_finalized.arn}/index/*"
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.edit_history.arn,
          "${aws_dynamodb_table.edit_history.arn}/index/*"
        ]
      }
    ]
  })
}

# Short Batch Submitter Lambda Policy
resource "aws_iam_policy" "short_batch_submitter_policy" {
  name = "${var.project_name}-${var.environment}-short-batch-submitter-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.processing_results.arn,
          "${aws_dynamodb_table.processing_results.arn}/index/*"
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.short_batch_queue.arn
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.short_batch_dlq.arn
      }
    ]
  })
}

# Short Batch Processor Lambda Policy
resource "aws_iam_policy" "short_batch_processor_policy" {
  name = "${var.project_name}-${var.environment}-short-batch-processor-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:PutItem"
        ]
        Resource = [
          aws_dynamodb_table.processing_results.arn,
          "${aws_dynamodb_table.processing_results.arn}/index/*",
          aws_dynamodb_table.processing_results.arn,
          aws_dynamodb_table.ocr_budget_tracking.arn
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.critical_alerts.arn
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.short_batch_queue.arn,
          aws_sqs_queue.short_batch_dlq.arn
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:SendMessage"
        ]
        Resource = concat(
          var.deployment_mode == "full" ? [aws_sqs_queue.batch_queue[0].arn] : [],
          [aws_sqs_queue.short_batch_dlq.arn]
        )
      }
    ]
  })
}

# SQS Processor Lambda Policy (Full Mode Only)
resource "aws_iam_policy" "sqs_processor_policy" {
  count = var.deployment_mode == "full" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-sqs-processor-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.batch_queue[0].arn
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "batch:SubmitJob",
          "batch:DescribeJobs"
        ]
        Resource = var.iam_wildcard_resource
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.processing_results.arn
      }
    ]
  })
}

# Attach policies to roles
resource "aws_iam_role_policy_attachment" "uploader_policy" {
  role       = aws_iam_role.uploader_role.name
  policy_arn = aws_iam_policy.uploader_policy.arn
}

resource "aws_iam_role_policy_attachment" "reader_policy" {
  role       = aws_iam_role.reader_role.name
  policy_arn = aws_iam_policy.reader_policy.arn
}

resource "aws_iam_role_policy_attachment" "search_policy" {
  role       = aws_iam_role.search_role.name
  policy_arn = aws_iam_policy.search_policy.arn
}


resource "aws_iam_role_policy_attachment" "finalizer_policy" {
  role       = aws_iam_role.finalizer_role.name
  policy_arn = aws_iam_policy.finalizer_policy.arn
}

resource "aws_iam_role_policy_attachment" "finalized_editor_policy" {
  role       = aws_iam_role.finalized_editor_role.name
  policy_arn = aws_iam_policy.finalized_editor_policy.arn
}

resource "aws_iam_role_policy_attachment" "short_batch_submitter_policy" {
  role       = aws_iam_role.short_batch_submitter_role.name
  policy_arn = aws_iam_policy.short_batch_submitter_policy.arn
}

resource "aws_iam_role_policy_attachment" "short_batch_processor_policy" {
  role       = aws_iam_role.short_batch_processor_role.name
  policy_arn = aws_iam_policy.short_batch_processor_policy.arn
}

resource "aws_iam_role_policy_attachment" "sqs_processor_policy" {
  count      = var.deployment_mode == "full" ? 1 : 0
  role       = aws_iam_role.sqs_processor_role[0].name
  policy_arn = aws_iam_policy.sqs_processor_policy[0].arn
}

# Batch Status Reconciliation Lambda Role
resource "aws_iam_role" "batch_reconciliation_role" {
  name = "${var.project_name}-${var.environment}-batch-reconciliation-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Batch Status Reconciliation Lambda Policy
resource "aws_iam_policy" "batch_reconciliation_policy" {
  name = "${var.project_name}-${var.environment}-batch-reconciliation-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.processing_results.arn
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "batch:DescribeJobs"
        ]
        Resource = var.iam_wildcard_resource
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_reconciliation_policy" {
  role       = aws_iam_role.batch_reconciliation_role.name
  policy_arn = aws_iam_policy.batch_reconciliation_policy.arn
}

# Dead Job Detector Lambda Role
resource "aws_iam_role" "dead_job_detector_role" {
  name = "${var.project_name}-${var.environment}-dead-job-detector-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Dead Job Detector Lambda Policy
resource "aws_iam_policy" "dead_job_detector_policy" {
  name = "${var.project_name}-${var.environment}-dead-job-detector-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.processing_results.arn
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "batch:DescribeJobs"
        ]
        Resource = var.iam_wildcard_resource
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "dead_job_detector_policy" {
  role       = aws_iam_role.dead_job_detector_role.name
  policy_arn = aws_iam_policy.dead_job_detector_policy.arn
}

# File Deleter Lambda Role
resource "aws_iam_role" "deleter_role" {
  name = "${var.project_name}-${var.environment}-file-deleter-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# File Deleter Lambda Policy
resource "aws_iam_policy" "deleter_policy" {
  name = "${var.project_name}-${var.environment}-file-deleter-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:DeleteItem",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.processing_results.arn,
          aws_dynamodb_table.ocr_finalized.arn
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.recycle_bin.arn
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "deleter_policy" {
  role       = aws_iam_role.deleter_role.name
  policy_arn = aws_iam_policy.deleter_policy.arn
}

# File Restorer Lambda Role
resource "aws_iam_role" "restorer_role" {
  name = "${var.project_name}-${var.environment}-file-restorer-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# File Restorer Lambda Policy
resource "aws_iam_policy" "restorer_policy" {
  name = "${var.project_name}-${var.environment}-file-restorer-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.processing_results.arn,
          "${aws_dynamodb_table.processing_results.arn}/index/*",
          aws_dynamodb_table.ocr_finalized.arn,
          "${aws_dynamodb_table.ocr_finalized.arn}/index/*"
        ]
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Query",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.recycle_bin.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "restorer_policy" {
  role       = aws_iam_role.restorer_role.name
  policy_arn = aws_iam_policy.restorer_policy.arn
}

# Recycle Bin Reader Lambda Role
resource "aws_iam_role" "recycle_bin_reader_role" {
  name = "${var.project_name}-${var.environment}-recycle-bin-reader-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Recycle Bin Reader Lambda Policy
resource "aws_iam_policy" "recycle_bin_reader_policy" {
  name = "${var.project_name}-${var.environment}-recycle-bin-reader-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.recycle_bin.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "recycle_bin_reader_policy" {
  role       = aws_iam_role.recycle_bin_reader_role.name
  policy_arn = aws_iam_policy.recycle_bin_reader_policy.arn
}

# ========================================
# SMART ROUTER REMOVED - Routing now integrated into s3_uploader
# ========================================



# ========================================
# INVOICE PROCESSING IAM ROLES AND POLICIES
# ========================================

# Invoice Uploader Lambda Role
resource "aws_iam_role" "invoice_uploader_role" {
  name = "${var.project_name}-${var.environment}-invoice-uploader-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Invoice Processor Lambda Role
resource "aws_iam_role" "invoice_processor_role" {
  name = "${var.project_name}-${var.environment}-invoice-processor-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Invoice Reader Lambda Role
resource "aws_iam_role" "invoice_reader_role" {
  name = "${var.project_name}-${var.environment}-invoice-reader-role"

  assume_role_policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Action = var.iam_assume_role_action
        Effect = var.iam_effect_allow
        Principal = {
          Service = var.lambda_service_principal
        }
      }
    ]
  })

  tags = var.common_tags
}

# Invoice Uploader Lambda Policy
resource "aws_iam_policy" "invoice_uploader_policy" {
  name = "${var.project_name}-${var.environment}-invoice-uploader-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      # CloudWatch Logs
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      # S3 - Upload to bucket
      {
        Effect = var.iam_effect_allow
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      # DynamoDB - Write invoice metadata to dedicated tables
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.processing_results.arn,
          "${aws_dynamodb_table.processing_results.arn}/index/*"
        ]
      },
      # SQS - Send messages to invoice queue
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.invoice_queue.arn
      }
    ]
  })
}

# Invoice Processor Lambda Policy
resource "aws_iam_policy" "invoice_processor_policy" {
  name = "${var.project_name}-${var.environment}-invoice-processor-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      # CloudWatch Logs
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      # S3 - Read from upload bucket and write processed results
      {
        Effect = var.iam_effect_allow
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      {
        Effect = var.iam_effect_allow
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      # DynamoDB - Read and write invoice metadata and results to dedicated tables
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:PutItem"
        ]
        Resource = [
          aws_dynamodb_table.invoice_processing_results.arn,
          "${aws_dynamodb_table.invoice_processing_results.arn}/index/*",
          aws_dynamodb_table.ocr_budget_tracking.arn
        ]
      },
      # SNS - Send notifications
      {
        Effect = var.iam_effect_allow
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.critical_alerts.arn
      },
      # SQS - Receive and delete messages from invoice queue
      {
        Effect = var.iam_effect_allow
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.invoice_queue.arn,
          aws_sqs_queue.invoice_dlq.arn
        ]
      }
    ]
  })
}

# Invoice Reader Lambda Policy
resource "aws_iam_policy" "invoice_reader_policy" {
  name = "${var.project_name}-${var.environment}-invoice-reader-policy"

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      # CloudWatch Logs
      {
        Effect = var.iam_effect_allow
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      # DynamoDB - Read invoice metadata and results from dedicated tables
      {
        Effect = var.iam_effect_allow
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.invoice_processing_results.arn,
          "${aws_dynamodb_table.invoice_processing_results.arn}/index/*"
        ]
      }
    ]
  })
}

# Attach policies to roles
resource "aws_iam_role_policy_attachment" "invoice_uploader_policy" {
  role       = aws_iam_role.invoice_uploader_role.name
  policy_arn = aws_iam_policy.invoice_uploader_policy.arn
}

resource "aws_iam_role_policy_attachment" "invoice_processor_policy" {
  role       = aws_iam_role.invoice_processor_role.name
  policy_arn = aws_iam_policy.invoice_processor_policy.arn
}

resource "aws_iam_role_policy_attachment" "invoice_reader_policy" {
  role       = aws_iam_role.invoice_reader_role.name
  policy_arn = aws_iam_policy.invoice_reader_policy.arn
}
# =============================================================================
# IAM ROLES FOR COGNITO AUTHENTICATION
# =============================================================================

# IAM Role for Cognito Trigger Lambda Functions
resource "aws_iam_role" "cognito_trigger_role" {
  name = "${var.project_name}-${var.environment}-cognito-trigger-role"

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

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-cognito-trigger-role"
    Purpose = "IAM role for Cognito Lambda triggers"
  })
}

# IAM Policy for Cognito Trigger Lambda Functions
resource "aws_iam_role_policy" "cognito_trigger_policy" {
  name = "${var.project_name}-${var.environment}-cognito-trigger-policy"
  role = aws_iam_role.cognito_trigger_role.id

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
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.user_profiles.arn,
          "${aws_dynamodb_table.user_profiles.arn}/index/*"
        ]
      }
    ]
  })
}

# Attach managed policy for basic Lambda execution
resource "aws_iam_role_policy_attachment" "cognito_trigger_policy" {
  role       = aws_iam_role.cognito_trigger_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# IAM Role for Auth API Lambda Functions
resource "aws_iam_role" "auth_api_role" {
  name = "${var.project_name}-${var.environment}-auth-api-role"

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

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-${var.environment}-auth-api-role"
    Purpose = "IAM role for authentication API Lambda functions"
  })
}

# IAM Policy for Auth API Lambda Functions
resource "aws_iam_role_policy" "auth_api_policy" {
  name = "${var.project_name}-${var.environment}-auth-api-policy"
  role = aws_iam_role.auth_api_role.id

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
          "cognito-idp:SignUp",
          "cognito-idp:ConfirmSignUp",
          "cognito-idp:InitiateAuth",
          "cognito-idp:RespondToAuthChallenge",
          "cognito-idp:GetUser",
          "cognito-idp:ResendConfirmationCode",
          "cognito-idp:ForgotPassword",
          "cognito-idp:ConfirmForgotPassword",
          "cognito-idp:ChangePassword",
          "cognito-idp:GlobalSignOut"
        ]
        Resource = [
          aws_cognito_user_pool.main.arn,
          "${aws_cognito_user_pool.main.arn}/*"
        ]
      }
    ]
  })
}

# Attach managed policy for basic Lambda execution
resource "aws_iam_role_policy_attachment" "auth_api_policy" {
  role       = aws_iam_role.auth_api_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
