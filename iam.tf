# Lambda execution role
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-role"

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

resource "aws_iam_role_policy" "lambda_batch_policy" {
  name = "${var.project_name}-lambda-batch-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "batch:SubmitJob",
          "batch:DescribeJobs",
          "batch:ListJobs"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
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
  name = "${var.project_name}-batch-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "batch.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_service_role_policy" {
  role       = aws_iam_role.batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# ECS instance role for Batch
resource "aws_iam_role" "ecs_instance_role" {
  name = "${var.project_name}-ecs-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role_policy" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance_profile" {
  name = "${var.project_name}-ecs-instance-profile"
  role = aws_iam_role.ecs_instance_role.name
}

# Task execution role for Batch jobs
resource "aws_iam_role" "batch_task_execution_role" {
  name = "${var.project_name}-batch-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "batch_task_execution_role_policy" {
  role       = aws_iam_role.batch_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task role for Batch jobs
resource "aws_iam_role" "batch_task_role" {
  name = "${var.project_name}-batch-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "batch_task_policy" {
  name = "${var.project_name}-batch-task-policy"
  role = aws_iam_role.batch_task_role.id

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
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:HeadObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:PutItem"
        ]
        Resource = [
          aws_dynamodb_table.file_metadata.arn,
          aws_dynamodb_table.processing_results.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "textract:StartDocumentAnalysis",
          "textract:GetDocumentAnalysis",
          "textract:StartDocumentTextDetection",
          "textract:GetDocumentTextDetection"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "comprehend:DetectDominantLanguage",
          "comprehend:DetectEntities",
          "comprehend:DetectKeyPhrases",
          "comprehend:DetectSentiment",
          "comprehend:DetectSyntax",
          "comprehend:DetectPiiEntities"
        ]
        Resource = "*"
      }
    ]
  })
}

# Uploader Lambda Role
resource "aws_iam_role" "uploader_role" {
  name = "${var.project_name}-${var.environment}-uploader-role"

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

  tags = var.common_tags
}

# Reader Lambda Role
resource "aws_iam_role" "reader_role" {
  name = "${var.project_name}-${var.environment}-reader-role"

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

  tags = var.common_tags
}

# Search Lambda Role
resource "aws_iam_role" "search_role" {
  name = "${var.project_name}-${var.environment}-search-role"

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

  tags = var.common_tags
}

# Editor Lambda Role
resource "aws_iam_role" "editor_role" {
  name = "${var.project_name}-${var.environment}-editor-role"

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

  tags = var.common_tags
}

# SQS Processor Lambda Role
resource "aws_iam_role" "sqs_processor_role" {
  name = "${var.project_name}-${var.environment}-sqs-processor-role"

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

  tags = var.common_tags
}

# Uploader Lambda Policy
resource "aws_iam_policy" "uploader_policy" {
  name = "${var.project_name}-${var.environment}-uploader-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.upload_bucket.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.file_metadata.arn
      }
    ]
  })
}

# Reader Lambda Policy
resource "aws_iam_policy" "reader_policy" {
  name = "${var.project_name}-${var.environment}-reader-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.file_metadata.arn,
          "${aws_dynamodb_table.file_metadata.arn}/index/*",
          aws_dynamodb_table.processing_results.arn
        ]
      }
    ]
  })
}

# Search Lambda Policy
resource "aws_iam_policy" "search_policy" {
  name = "${var.project_name}-${var.environment}-search-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:GetItem"
        ]
        Resource = [
          aws_dynamodb_table.file_metadata.arn,
          "${aws_dynamodb_table.file_metadata.arn}/index/*",
          aws_dynamodb_table.processing_results.arn
        ]
      }
    ]
  })
}

# Editor Lambda Policy
resource "aws_iam_policy" "editor_policy" {
  name = "${var.project_name}-${var.environment}-editor-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = [
          aws_dynamodb_table.file_metadata.arn,
          "${aws_dynamodb_table.file_metadata.arn}/index/*",
          aws_dynamodb_table.processing_results.arn
        ]
      }
    ]
  })
}

# SQS Processor Lambda Policy
resource "aws_iam_policy" "sqs_processor_policy" {
  name = "${var.project_name}-${var.environment}-sqs-processor-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.batch_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "batch:SubmitJob",
          "batch:DescribeJobs"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.file_metadata.arn
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

resource "aws_iam_role_policy_attachment" "editor_policy" {
  role       = aws_iam_role.editor_role.name
  policy_arn = aws_iam_policy.editor_policy.arn
}

resource "aws_iam_role_policy_attachment" "sqs_processor_policy" {
  role       = aws_iam_role.sqs_processor_role.name
  policy_arn = aws_iam_policy.sqs_processor_policy.arn
}

# Batch Status Reconciliation Lambda Role
resource "aws_iam_role" "batch_reconciliation_role" {
  name = "${var.project_name}-${var.environment}-batch-reconciliation-role"

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

  tags = var.common_tags
}

# Batch Status Reconciliation Lambda Policy
resource "aws_iam_policy" "batch_reconciliation_policy" {
  name = "${var.project_name}-${var.environment}-batch-reconciliation-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.file_metadata.arn
      },
      {
        Effect = "Allow"
        Action = [
          "batch:DescribeJobs"
        ]
        Resource = "*"
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

  tags = var.common_tags
}

# Dead Job Detector Lambda Policy
resource "aws_iam_policy" "dead_job_detector_policy" {
  name = "${var.project_name}-${var.environment}-dead-job-detector-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.file_metadata.arn
      },
      {
        Effect = "Allow"
        Action = [
          "batch:DescribeJobs"
        ]
        Resource = "*"
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

  tags = var.common_tags
}

# File Deleter Lambda Policy
resource "aws_iam_policy" "deleter_policy" {
  name = "${var.project_name}-${var.environment}-file-deleter-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.file_metadata.arn,
          aws_dynamodb_table.processing_results.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:DeleteItem"
        ]
        Resource = aws_dynamodb_table.recycle_bin.arn
      },
      {
        Effect = "Allow"
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

  tags = var.common_tags
}

# File Restorer Lambda Policy
resource "aws_iam_policy" "restorer_policy" {
  name = "${var.project_name}-${var.environment}-file-restorer-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.file_metadata.arn,
          aws_dynamodb_table.processing_results.arn
        ]
      },
      {
        Effect = "Allow"
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

  tags = var.common_tags
}

# Recycle Bin Reader Lambda Policy
resource "aws_iam_policy" "recycle_bin_reader_policy" {
  name = "${var.project_name}-${var.environment}-recycle-bin-reader-policy"

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
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
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