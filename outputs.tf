# API Gateway Outputs
output "api_gateway_base_url" {
  description = "Base URL of the API Gateway"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}"
}

output "api_upload_url" {
  description = "Upload endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/upload"
}

output "api_processed_url" {
  description = "Processed files endpoint URL"
  value       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/processed"
}

# S3 and CloudFront Outputs
output "upload_bucket_name" {
  description = "Name of the S3 upload bucket"
  value       = aws_s3_bucket.upload_bucket.id
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.s3_distribution.domain_name
}

output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.s3_distribution.domain_name}"
}

# ECR Repository Outputs
output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.main.repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.main.name
}

# Lambda Function Outputs
output "uploader_lambda_name" {
  description = "Name of the uploader Lambda function"
  value       = aws_lambda_function.uploader.function_name
}

output "reader_lambda_name" {
  description = "Name of the reader Lambda function"
  value       = aws_lambda_function.reader.function_name
}

output "sqs_processor_lambda_name" {
  description = "Name of the SQS processor Lambda function"
  value       = aws_lambda_function.sqs_batch_processor.function_name
}

output "batch_status_reconciliation_lambda_name" {
  description = "Name of the batch status reconciliation Lambda function"
  value       = aws_lambda_function.batch_status_reconciliation.function_name
}

output "dead_job_detector_lambda_name" {
  description = "Name of the dead job detector Lambda function"
  value       = aws_lambda_function.dead_job_detector.function_name
}

# Batch Outputs
output "batch_job_queue_name" {
  description = "Name of the Batch job queue"
  value       = aws_batch_job_queue.main.name
}

output "batch_job_definition_name" {
  description = "Name of the Batch job definition"
  value       = aws_batch_job_definition.main.name
}

output "batch_compute_environment_name" {
  description = "Name of the Batch compute environment"
  value       = aws_batch_compute_environment.main.compute_environment_name
}

# DynamoDB Outputs
output "metadata_table_name" {
  description = "Name of the file metadata DynamoDB table"
  value       = aws_dynamodb_table.file_metadata.name
}

output "results_table_name" {
  description = "Name of the processing results DynamoDB table"
  value       = aws_dynamodb_table.processing_results.name
}

# SQS Outputs
output "sqs_queue_url" {
  description = "URL of the main SQS queue"
  value       = aws_sqs_queue.batch_queue.url
}

output "sqs_dlq_url" {
  description = "URL of the SQS dead letter queue"
  value       = aws_sqs_queue.batch_dlq.url
}

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

# Manual Commands for Setup
output "docker_build_commands" {
  description = "Commands to build and push Docker image to ECR"
  value       = <<-EOT
    # Login to ECR
    aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.main.repository_url}
    
    # Build and tag the image
    docker build -t ${aws_ecr_repository.main.name} ./aws_batch
    docker tag ${aws_ecr_repository.main.name}:latest ${aws_ecr_repository.main.repository_url}:latest
    
    # Push to ECR
    docker push ${aws_ecr_repository.main.repository_url}:latest
  EOT
}

output "test_upload_command" {
  description = "Example curl command to test file upload"
  value       = <<-EOT
    # Test file upload (replace with actual base64 encoded file)
    curl -X POST ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/upload \
      -H "Content-Type: application/json" \
      -d '{
        "fileName": "test.txt",
        "fileContent": "SGVsbG8gV29ybGQ=",
        "contentType": "text/plain"
      }'
  EOT
}

output "test_processed_command" {
  description = "Example curl command to check processed files"
  value       = <<-EOT
    # Get all processed files (public rate limit)
    curl "${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/processed"
    
    # Get files by status with API key (higher rate limit)
    curl -H "X-API-Key: YOUR_API_KEY" \
      "${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/processed?status=processing"
    
    # Get specific file
    curl "${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/processed?fileId=YOUR_FILE_ID"
  EOT
}

# Rate Limiting Test Commands
output "rate_limiting_test_commands" {
  description = "Commands to test rate limiting functionality"
  value = var.enable_rate_limiting ? "Rate limiting test commands available - check terraform.tfvars.example for examples" : "Rate limiting is disabled"
}

# API Key Retrieval Commands  
output "api_key_commands" {
  description = "Commands to retrieve and manage API keys"
  value = var.enable_rate_limiting && var.create_default_api_keys ? "API key commands available - use 'terraform output demo_api_keys' to get keys" : "No demo API keys created"
}

# Cost Optimization Summary
output "cost_optimization_summary" {
  description = "Summary of cost optimization features"
  value       = <<-EOT
    Cost Optimization Features:
    - VPC Endpoints instead of NAT Gateways: Save $75-105/month
    - DynamoDB Pay-per-Request: Only pay for actual usage
    - CloudFront PriceClass_100: Optimized for cost
    - S3 Lifecycle policies: Automatic transition to cheaper storage
    - Lambda pay-per-use: No idle costs
    - Fargate on-demand: No EC2 instance management
    
    Estimated Monthly Costs:
    - VPC Endpoints: $43.20
    - CloudFront: $1-10 (depends on usage)
    - DynamoDB: $0.25 per million requests
    - S3: $0.023 per GB
    - Lambda: $0.20 per million requests
    
    Annual Savings vs Traditional Setup: $900-1,260
  EOT
}

# Rate Limiting Information
output "rate_limiting_summary" {
  description = "Summary of API Gateway rate limiting configuration"
  value = var.enable_rate_limiting ? "Rate limiting enabled with public (${var.public_rate_limit}/sec), registered (${var.registered_rate_limit}/sec), and premium (${var.premium_rate_limit}/sec) tiers" : "Rate limiting is disabled"
}

output "demo_api_keys" {
  description = "Demo API keys for testing (sensitive output)"
  value = var.enable_rate_limiting && var.create_default_api_keys ? {
    for idx, key in aws_api_gateway_api_key.demo_keys : 
    var.api_key_names[idx] => {
      id    = key.id
      value = key.value
      name  = key.name
      plan  = strcontains(var.api_key_names[idx], "premium") ? "premium" : "registered"
    }
  } : {}
  sensitive = true
}

output "usage_plan_ids" {
  description = "Usage plan IDs for API management"
  value = var.enable_rate_limiting ? {
    public     = var.enable_rate_limiting ? aws_api_gateway_usage_plan.public[0].id : null
    registered = var.enable_rate_limiting ? aws_api_gateway_usage_plan.registered[0].id : null
    premium    = var.enable_rate_limiting ? aws_api_gateway_usage_plan.premium[0].id : null
  } : {}
}

# Architecture Summary
output "architecture_summary" {
  description = "Summary of the deployed architecture"
  value       = <<-EOT
    File Processing Pipeline Architecture:
    
    1. Upload Flow:
       API Gateway (/upload) → Uploader Lambda → S3 Bucket → DynamoDB Metadata
    
    2. Processing Flow:
       S3 Event → EventBridge → SQS Queue → SQS Processor Lambda → AWS Batch → DynamoDB Results
    
    3. Retrieval Flow:
       API Gateway (/processed) → Reader Lambda → DynamoDB Query → CloudFront URLs
    
    4. Error Handling:
       SQS Dead Letter Queue → CloudWatch Alarms → SNS Notifications
    
    5. Access:
       Users access files via CloudFront URLs in browser
    
    6. Rate Limiting:
       ${var.enable_rate_limiting ? "Multi-tier rate limiting with public, registered, and premium plans" : "Rate limiting disabled"}
    
    Key Features:
    - Serverless and cost-optimized
    - Automatic retry and error handling
    - Scalable processing with AWS Batch
    - Secure file access via CloudFront
    - Comprehensive monitoring and logging
    - ${var.enable_rate_limiting ? "Advanced rate limiting protection" : "No rate limiting"}
  EOT
}