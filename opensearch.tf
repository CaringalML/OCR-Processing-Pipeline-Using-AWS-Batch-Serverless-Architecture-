# OpenSearch Serverless Configuration for OCR Document Search
# This creates a serverless OpenSearch collection for full-text search of processed documents

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "ocr_search" {
  name        = "${var.project_name}-search-${var.environment}"
  type        = "SEARCH"
  description = "OCR document search collection"

  depends_on = [
    aws_opensearchserverless_security_policy.ocr_search_security,
    aws_opensearchserverless_security_policy.ocr_search_network
  ]

  tags = {
    Name        = "${var.project_name}-opensearch-serverless"
    Environment = var.environment
    Purpose     = "Document Search"
  }
}

# Security Policy for OpenSearch Serverless
resource "aws_opensearchserverless_security_policy" "ocr_search_security" {
  name        = "${var.project_name}-security"
  type        = "encryption"
  description = "Encryption policy for OCR search collection"

  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/${var.project_name}-search-${var.environment}"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

# Network Policy for OpenSearch Serverless (VPC access)
resource "aws_opensearchserverless_security_policy" "ocr_search_network" {
  name        = "${var.project_name}-network"
  type        = "network"
  description = "Network policy for OCR search collection"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.project_name}-search-${var.environment}"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "collection/${var.project_name}-search-${var.environment}"
          ]
          ResourceType = "dashboard"
        }
      ]
      AllowFromPublic = false
      SourceVPCEs = [
        aws_opensearchserverless_vpc_endpoint.ocr_search.id
      ]
    }
  ])
}

# VPC Endpoint for OpenSearch Serverless
resource "aws_opensearchserverless_vpc_endpoint" "ocr_search" {
  name               = "${var.project_name}-vpce"
  vpc_id             = aws_vpc.main.id
  subnet_ids         = aws_subnet.private[*].id
  security_group_ids = [aws_security_group.opensearch.id]
}

# Data Access Policy for OpenSearch Serverless
resource "aws_opensearchserverless_access_policy" "ocr_search_data" {
  name        = "${var.project_name}-data"
  type        = "data"
  description = "Data access policy for OCR search collection"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.project_name}-search-${var.environment}"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems", 
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "index/${var.project_name}-search-${var.environment}/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        aws_iam_role.opensearch_lambda_execution.arn,
        aws_iam_role.lambda_execution.arn,
        data.aws_caller_identity.current.arn
      ]
    }
  ])
}

# Security Group for OpenSearch Serverless
resource "aws_security_group" "opensearch" {
  name        = "${var.project_name}-opensearch-serverless-sg"
  description = "Security group for OpenSearch Serverless VPC endpoint"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.opensearch_lambda.id]
    description     = "HTTPS from Lambda functions"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "HTTPS from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-opensearch-serverless-sg"
  }
}

# Security Group for OpenSearch Lambda Functions
resource "aws_security_group" "opensearch_lambda" {
  name        = "${var.project_name}-opensearch-lambda-sg"
  description = "Security group for OpenSearch Lambda functions"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS to OpenSearch and AWS services"
  }

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP for package downloads"
  }

  tags = {
    Name = "${var.project_name}-opensearch-lambda-sg"
  }
}

# CloudWatch Log Groups for Lambda functions
resource "aws_cloudwatch_log_group" "opensearch_lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-opensearch-function"
  retention_in_days = 14

  tags = {
    Name        = "${var.project_name}-opensearch-lambda-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "opensearch_indexing_logs" {
  name              = "/aws/lambda/${var.project_name}-opensearch-indexing"
  retention_in_days = 14

  tags = {
    Name        = "${var.project_name}-opensearch-indexing-logs"
    Environment = var.environment
  }
}

# Lambda Execution Role for OpenSearch Serverless
resource "aws_iam_role" "opensearch_lambda_execution" {
  name = "${var.project_name}-opensearch-lambda-execution-role"

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

  tags = {
    Name        = "${var.project_name}-opensearch-lambda-role"
    Environment = var.environment
  }
}

# IAM Policy for OpenSearch Serverless Lambda
resource "aws_iam_role_policy" "opensearch_lambda_policy" {
  name = "${var.project_name}-opensearch-lambda-policy"
  role = aws_iam_role.opensearch_lambda_execution.id

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
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.ocr_search.arn,
          "${aws_opensearchserverless_collection.ocr_search.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.file_metadata.arn,
          aws_dynamodb_table.processing_results.arn,
          "${aws_dynamodb_table.processing_results.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "ec2:AssignPrivateIpAddresses",
          "ec2:UnassignPrivateIpAddresses"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach VPC execution policy to Lambda role
resource "aws_iam_role_policy_attachment" "opensearch_lambda_vpc_policy" {
  role       = aws_iam_role.opensearch_lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Lambda Function for OpenSearch
resource "aws_lambda_function" "opensearch_function" {
  filename         = data.archive_file.opensearch_zip.output_path
  function_name    = "${var.project_name}-opensearch-function"
  role            = aws_iam_role.opensearch_lambda_execution.arn
  handler         = "opensearch_lambda.lambda_handler"
  runtime         = "python3.9"
  timeout         = 60
  memory_size     = 512
  source_code_hash = data.archive_file.opensearch_zip.output_base64sha256

  environment {
    variables = {
      OPENSEARCH_ENDPOINT = aws_opensearchserverless_collection.ocr_search.collection_endpoint
      OPENSEARCH_REGION   = data.aws_region.current.name
      DYNAMODB_TABLE      = aws_dynamodb_table.processing_results.name
      INDEX_NAME          = "ocr-documents"
      COLLECTION_NAME     = aws_opensearchserverless_collection.ocr_search.name
      USE_SERVERLESS      = "true"
    }
  }

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.opensearch_lambda.id]
  }

  depends_on = [
    aws_iam_role_policy.opensearch_lambda_policy,
    aws_iam_role_policy_attachment.opensearch_lambda_vpc_policy,
    aws_cloudwatch_log_group.opensearch_lambda_logs,
    aws_opensearchserverless_collection.ocr_search
  ]

  tags = {
    Name        = "${var.project_name}-opensearch-function"
    Environment = var.environment
  }
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "opensearch_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.opensearch_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# EventBridge Rule for Indexing New Documents
resource "aws_cloudwatch_event_rule" "opensearch_indexing_rule" {
  name        = "${var.project_name}-opensearch-indexing"
  description = "Trigger OpenSearch indexing when OCR processing completes"

  event_pattern = jsonencode({
    source      = ["aws.batch"]
    detail-type = ["Batch Job State Change"]
    detail = {
      status = ["SUCCEEDED"]
      jobQueue = [aws_batch_job_queue.main.arn]
    }
  })

  tags = {
    Name        = "${var.project_name}-opensearch-indexing-rule"
    Environment = var.environment
  }
}

# EventBridge Target for OpenSearch Indexing
resource "aws_cloudwatch_event_target" "opensearch_indexing_target" {
  rule      = aws_cloudwatch_event_rule.opensearch_indexing_rule.name
  target_id = "OpenSearchIndexingTarget"
  arn       = aws_lambda_function.opensearch_indexing.arn
}

# Lambda Function for Automatic Indexing
resource "aws_lambda_function" "opensearch_indexing" {
  filename         = data.archive_file.opensearch_indexing_zip.output_path
  function_name    = "${var.project_name}-opensearch-indexing"
  role            = aws_iam_role.opensearch_lambda_execution.arn
  handler         = "opensearch_indexing.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 1024
  source_code_hash = data.archive_file.opensearch_indexing_zip.output_base64sha256

  environment {
    variables = {
      OPENSEARCH_ENDPOINT   = aws_opensearchserverless_collection.ocr_search.collection_endpoint
      OPENSEARCH_REGION     = data.aws_region.current.name
      DYNAMODB_TABLE        = aws_dynamodb_table.processing_results.name
      FILE_METADATA_TABLE   = aws_dynamodb_table.file_metadata.name
      INDEX_NAME            = "ocr-documents"
      BATCH_SIZE            = "10"
      COLLECTION_NAME       = aws_opensearchserverless_collection.ocr_search.name
      USE_SERVERLESS        = "true"
    }
  }

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.opensearch_lambda.id]
  }

  depends_on = [
    aws_iam_role_policy.opensearch_lambda_policy,
    aws_iam_role_policy_attachment.opensearch_lambda_vpc_policy,
    aws_cloudwatch_log_group.opensearch_indexing_logs,
    aws_opensearchserverless_collection.ocr_search
  ]

  tags = {
    Name        = "${var.project_name}-opensearch-indexing"
    Environment = var.environment
  }
}

# Lambda Permission for EventBridge (Indexing)
resource "aws_lambda_permission" "opensearch_indexing_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.opensearch_indexing.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.opensearch_indexing_rule.arn
}

# Lambda Function ZIP Archives
# Note: For Lambda functions with dependencies, you need to install them first
# Run: pip install -r lambda_functions/opensearch_lambda/requirements.txt -t lambda_functions/opensearch_lambda/
# Run: pip install -r lambda_functions/opensearch_indexing/requirements.txt -t lambda_functions/opensearch_indexing/
data "archive_file" "opensearch_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/opensearch_lambda/opensearch_lambda.zip"
  source_dir  = "${path.module}/lambda_functions/opensearch_lambda"
  excludes    = ["requirements.txt", "*.zip"]
}

data "archive_file" "opensearch_indexing_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_functions/opensearch_indexing/opensearch_indexing.zip"
  source_dir  = "${path.module}/lambda_functions/opensearch_indexing"
  excludes    = ["requirements.txt", "*.zip"]
}

# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Outputs
output "opensearch_collection_endpoint" {
  value       = aws_opensearchserverless_collection.ocr_search.collection_endpoint
  description = "OpenSearch Serverless collection endpoint"
}

output "opensearch_dashboard_url" {
  value       = aws_opensearchserverless_collection.ocr_search.dashboard_endpoint
  description = "OpenSearch Serverless Dashboards URL"
}

output "opensearch_collection_arn" {
  value       = aws_opensearchserverless_collection.ocr_search.arn
  description = "OpenSearch Serverless collection ARN"
}