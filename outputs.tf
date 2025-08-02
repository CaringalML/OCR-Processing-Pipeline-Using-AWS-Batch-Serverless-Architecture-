# API Gateway Outputs with Environment Stages
output "api_gateway" {
  description = "Unified API Gateway with environment stages"
  value = {
    base_url = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}"
    
    long_batch_endpoints = {
      upload      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/upload"
      process     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/process"
      processed   = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/processed"
      search      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/search"
      edit        = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/edit"
      delete      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/delete/{fileId}"
      recycle_bin = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/recycle-bin"
      restore     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/restore/{fileId}"
    }
    
    short_batch_endpoints = {
      upload      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/upload"
      process     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/process"
      processed   = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/processed"
      search      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/search"
      edit        = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/edit"
      delete      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/delete/{fileId}"
      recycle_bin = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/recycle-bin"
      restore     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/restore/{fileId}"
    }
  }
}

# S3 and CloudFront Outputs
output "storage" {
  description = "Storage resources information"
  value = {
    upload_bucket_name     = aws_s3_bucket.upload_bucket.id
    upload_bucket_arn      = aws_s3_bucket.upload_bucket.arn
    cloudfront_domain      = aws_cloudfront_distribution.s3_distribution.domain_name
    cloudfront_url         = "https://${aws_cloudfront_distribution.s3_distribution.domain_name}"
    cloudfront_id          = aws_cloudfront_distribution.s3_distribution.id
    cloudfront_status      = aws_cloudfront_distribution.s3_distribution.status
  }
}

# ECR Repository Outputs
output "ecr" {
  description = "ECR repository information"
  value = {
    repository_url  = aws_ecr_repository.main.repository_url
    repository_name = aws_ecr_repository.main.name
    repository_arn  = aws_ecr_repository.main.arn
    registry_id     = aws_ecr_repository.main.registry_id
  }
}

# Lambda Functions Outputs
output "lambda_functions" {
  description = "All Lambda function information"
  value = {
    uploader = {
      name         = aws_lambda_function.uploader.function_name
      arn          = aws_lambda_function.uploader.arn
      invoke_arn   = aws_lambda_function.uploader.invoke_arn
      memory_size  = aws_lambda_function.uploader.memory_size
      timeout      = aws_lambda_function.uploader.timeout
    }
    reader = {
      name         = aws_lambda_function.reader.function_name
      arn          = aws_lambda_function.reader.arn
      invoke_arn   = aws_lambda_function.reader.invoke_arn
      memory_size  = aws_lambda_function.reader.memory_size
      timeout      = aws_lambda_function.reader.timeout
    }
    search = {
      name         = aws_lambda_function.search.function_name
      arn          = aws_lambda_function.search.arn
      invoke_arn   = aws_lambda_function.search.invoke_arn
      memory_size  = aws_lambda_function.search.memory_size
      timeout      = aws_lambda_function.search.timeout
    }
    editor = {
      name         = aws_lambda_function.editor.function_name
      arn          = aws_lambda_function.editor.arn
      invoke_arn   = aws_lambda_function.editor.invoke_arn
      memory_size  = aws_lambda_function.editor.memory_size
      timeout      = aws_lambda_function.editor.timeout
    }
    short_batch_processor = {
      name         = aws_lambda_function.short_batch_processor.function_name
      arn          = aws_lambda_function.short_batch_processor.arn
      invoke_arn   = aws_lambda_function.short_batch_processor.invoke_arn
      memory_size  = aws_lambda_function.short_batch_processor.memory_size
      timeout      = aws_lambda_function.short_batch_processor.timeout
    }
    sqs_processor = {
      name         = aws_lambda_function.sqs_batch_processor.function_name
      arn          = aws_lambda_function.sqs_batch_processor.arn
      invoke_arn   = aws_lambda_function.sqs_batch_processor.invoke_arn
      memory_size  = aws_lambda_function.sqs_batch_processor.memory_size
      timeout      = aws_lambda_function.sqs_batch_processor.timeout
    }
    batch_reconciliation = {
      name         = aws_lambda_function.batch_status_reconciliation.function_name
      arn          = aws_lambda_function.batch_status_reconciliation.arn
      memory_size  = aws_lambda_function.batch_status_reconciliation.memory_size
      timeout      = aws_lambda_function.batch_status_reconciliation.timeout
    }
    dead_job_detector = {
      name         = aws_lambda_function.dead_job_detector.function_name
      arn          = aws_lambda_function.dead_job_detector.arn
      memory_size  = aws_lambda_function.dead_job_detector.memory_size
      timeout      = aws_lambda_function.dead_job_detector.timeout
    }
    deleter = {
      name         = aws_lambda_function.deleter.function_name
      arn          = aws_lambda_function.deleter.arn
      invoke_arn   = aws_lambda_function.deleter.invoke_arn
      memory_size  = aws_lambda_function.deleter.memory_size
      timeout      = aws_lambda_function.deleter.timeout
    }
    restorer = {
      name         = aws_lambda_function.restorer.function_name
      arn          = aws_lambda_function.restorer.arn
      invoke_arn   = aws_lambda_function.restorer.invoke_arn
      memory_size  = aws_lambda_function.restorer.memory_size
      timeout      = aws_lambda_function.restorer.timeout
    }
    recycle_bin_reader = {
      name         = aws_lambda_function.recycle_bin_reader.function_name
      arn          = aws_lambda_function.recycle_bin_reader.arn
      invoke_arn   = aws_lambda_function.recycle_bin_reader.invoke_arn
      memory_size  = aws_lambda_function.recycle_bin_reader.memory_size
      timeout      = aws_lambda_function.recycle_bin_reader.timeout
    }
    smart_router = {
      name         = aws_lambda_function.smart_router.function_name
      arn          = aws_lambda_function.smart_router.arn
      invoke_arn   = aws_lambda_function.smart_router.invoke_arn
      memory_size  = aws_lambda_function.smart_router.memory_size
      timeout      = aws_lambda_function.smart_router.timeout
    }
    long_batch_uploader = {
      name         = aws_lambda_function.long_batch_uploader.function_name
      arn          = aws_lambda_function.long_batch_uploader.arn
      invoke_arn   = aws_lambda_function.long_batch_uploader.invoke_arn
      memory_size  = aws_lambda_function.long_batch_uploader.memory_size
      timeout      = aws_lambda_function.long_batch_uploader.timeout
    }
    short_batch_uploader = {
      name         = aws_lambda_function.short_batch_uploader.function_name
      arn          = aws_lambda_function.short_batch_uploader.arn
      invoke_arn   = aws_lambda_function.short_batch_uploader.invoke_arn
      memory_size  = aws_lambda_function.short_batch_uploader.memory_size
      timeout      = aws_lambda_function.short_batch_uploader.timeout
    }
    short_batch_submitter = {
      name         = aws_lambda_function.short_batch_submitter.function_name
      arn          = aws_lambda_function.short_batch_submitter.arn
      invoke_arn   = aws_lambda_function.short_batch_submitter.invoke_arn
      memory_size  = aws_lambda_function.short_batch_submitter.memory_size
      timeout      = aws_lambda_function.short_batch_submitter.timeout
    }
  }
}

# AWS Batch Outputs
output "batch" {
  description = "AWS Batch resources information"
  value = {
    job_queue_name     = aws_batch_job_queue.main.name
    job_queue_arn      = aws_batch_job_queue.main.arn
    job_definition     = aws_batch_job_definition.main.name
    job_definition_arn = aws_batch_job_definition.main.arn
    compute_env_name   = aws_batch_compute_environment.main.compute_environment_name
    compute_env_arn    = aws_batch_compute_environment.main.arn
    compute_env_state  = aws_batch_compute_environment.main.state
  }
}

# DynamoDB Tables Outputs
output "dynamodb" {
  description = "DynamoDB tables information"
  value = {
    metadata_table = {
      name       = aws_dynamodb_table.file_metadata.name
      arn        = aws_dynamodb_table.file_metadata.arn
      stream_arn = aws_dynamodb_table.file_metadata.stream_arn
    }
    results_table = {
      name       = aws_dynamodb_table.processing_results.name
      arn        = aws_dynamodb_table.processing_results.arn
      stream_arn = aws_dynamodb_table.processing_results.stream_arn
    }
    recycle_bin_table = {
      name       = aws_dynamodb_table.recycle_bin.name
      arn        = aws_dynamodb_table.recycle_bin.arn
      stream_arn = aws_dynamodb_table.recycle_bin.stream_arn
    }
  }
}

# SQS Queues Outputs
output "sqs" {
  description = "SQS queues information"
  value = {
    main_queue = {
      url                = aws_sqs_queue.batch_queue.url
      arn                = aws_sqs_queue.batch_queue.arn
      name               = aws_sqs_queue.batch_queue.name
      visibility_timeout = aws_sqs_queue.batch_queue.visibility_timeout_seconds
    }
    dead_letter_queue = {
      url  = aws_sqs_queue.batch_dlq.url
      arn  = aws_sqs_queue.batch_dlq.arn
      name = aws_sqs_queue.batch_dlq.name
    }
    short_batch_queue = {
      url                = aws_sqs_queue.short_batch_queue.url
      arn                = aws_sqs_queue.short_batch_queue.arn
      name               = aws_sqs_queue.short_batch_queue.name
      visibility_timeout = aws_sqs_queue.short_batch_queue.visibility_timeout_seconds
    }
    short_batch_dead_letter_queue = {
      url  = aws_sqs_queue.short_batch_dlq.url
      arn  = aws_sqs_queue.short_batch_dlq.arn
      name = aws_sqs_queue.short_batch_dlq.name
    }
  }
}

# VPC and Networking Outputs
output "networking" {
  description = "VPC and networking information"
  value = {
    vpc_id             = aws_vpc.main.id
    vpc_cidr           = aws_vpc.main.cidr_block
    private_subnet_ids = aws_subnet.private[*].id
    public_subnet_ids  = aws_subnet.public[*].id
    internet_gateway   = aws_internet_gateway.main.id
  }
}

# CloudWatch Logs Outputs
output "cloudwatch_logs" {
  description = "CloudWatch log groups"
  value = {
    s3_uploader          = aws_cloudwatch_log_group.s3_uploader_logs.name
    lambda_reader        = aws_cloudwatch_log_group.lambda_reader_logs.name
    document_search      = aws_cloudwatch_log_group.document_search_logs.name
    sqs_to_batch         = aws_cloudwatch_log_group.sqs_to_batch_submitter_logs.name
    batch_reconciliation = aws_cloudwatch_log_group.batch_status_reconciliation_logs.name
    dead_job_detector    = aws_cloudwatch_log_group.dead_job_detector_logs.name
    file_deleter         = aws_cloudwatch_log_group.file_deleter_logs.name
    file_restorer        = aws_cloudwatch_log_group.file_restorer_logs.name
    recycle_bin_reader   = aws_cloudwatch_log_group.recycle_bin_reader_logs.name
    short_batch_processor = aws_cloudwatch_log_group.short_batch_processor_logs.name
    smart_router          = aws_cloudwatch_log_group.smart_router_logs.name
    long_batch_uploader   = aws_cloudwatch_log_group.long_batch_uploader_logs.name
    short_batch_uploader  = aws_cloudwatch_log_group.short_batch_uploader_logs.name
    short_batch_submitter = aws_cloudwatch_log_group.short_batch_submitter_logs.name
    ocr_editor           = aws_cloudwatch_log_group.ocr_editor_logs.name
    cleanup_processor    = aws_cloudwatch_log_group.cleanup_processor_logs.name
  }
}

# SNS Topics Outputs
output "monitoring" {
  description = "Monitoring and alerting resources"
  value = {
    alerts_topic_arn  = aws_sns_topic.alerts.arn
    alerts_topic_name = aws_sns_topic.alerts.name
  }
}

# Rate Limiting Outputs
output "rate_limiting" {
  description = "API rate limiting configuration"
  value = {
    enabled = var.enable_rate_limiting
    message = var.enable_rate_limiting ? "Rate limiting enabled with multi-tier protection" : "Rate limiting is disabled"
    tiers = var.enable_rate_limiting ? {
      public = {
        rate_limit  = var.public_rate_limit
        burst_limit = var.public_burst_limit
      }
      registered = {
        rate_limit  = var.registered_rate_limit
        burst_limit = var.registered_burst_limit
      }
      premium = {
        rate_limit  = var.premium_rate_limit
        burst_limit = var.premium_burst_limit
      }
    } : null
  }
}

# Deployment Commands
output "deployment_commands" {
  description = "Essential deployment commands"
  value = {
    ecr_login = "aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.main.repository_url}"
    
    docker_build = <<-EOT
      cd aws_batch
      docker build -t ${aws_ecr_repository.main.name} .
      docker tag ${aws_ecr_repository.main.name}:latest ${aws_ecr_repository.main.repository_url}:latest
      docker push ${aws_ecr_repository.main.repository_url}:latest
    EOT
  }
}

# API Test Examples
output "api_examples" {
  description = "Example API calls for testing"
  value = {
    # Long Batch Examples
    long_batch_search = "curl 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/search?q=electric+cars'"
    
    long_batch_process = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/process' -H 'Content-Type: application/json' -d '{\"fileId\": \"YOUR_FILE_ID\"}'"
    
    long_batch_get_by_id = "curl 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/processed?fileId=YOUR_FILE_ID'"
    
    # Short Batch Examples  
    short_batch_search = "curl 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/search?q=electrik+kars&fuzzy=true&fuzzyThreshold=80'"
    
    short_batch_process = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/process' -H 'Content-Type: application/json' -d '{\"fileId\": \"YOUR_FILE_ID\"}'"
    
    short_batch_get_by_id = "curl 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/processed?fileId=YOUR_FILE_ID'"
    
    # Upload examples (dedicated endpoints for forced routing)
    long_batch_upload = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/upload' -F 'file=@document.pdf'"
    
    short_batch_upload = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/upload' -F 'file=@document.pdf'"
    
    # Smart routing upload (size-based decision)
    smart_upload = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/upload' -F 'file=@document.pdf'"
    
    # Common operations (available on both APIs)
    delete_file = "curl -X DELETE 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/delete/YOUR_FILE_ID'"
    
    list_recycle_bin = "curl 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/recycle-bin'"
    
    restore_file = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/restore/YOUR_FILE_ID'"
  }
}

# Cost Optimization Summary
output "cost_summary" {
  description = "Cost optimization and estimates"
  value = {
    optimizations = [
      "VPC Endpoints instead of NAT Gateways (save $75-105/month)",
      "DynamoDB Pay-per-Request pricing",
      "S3 Lifecycle policies for automatic archival",
      "Lambda pay-per-use (no idle costs)",
      "Fargate Spot for batch processing",
      "CloudFront PriceClass_100 for cost-effective CDN"
    ]
    
    estimated_monthly_costs = {
      vpc_endpoints = "$43.20"
      cloudfront    = "$1-10 (usage based)"
      dynamodb      = "$0.25 per million requests"
      s3_storage    = "$0.023 per GB"
      lambda        = "$0.20 per million requests"
      batch_fargate = "$0.04 per vCPU hour"
    }
    
    annual_savings = "$900-1,260 vs traditional EC2/RDS setup"
  }
}

# Architecture Overview
output "architecture" {
  description = "System architecture overview"
  value = {
    upload_flow        = "Smart Router → Size-based routing OR Forced routing via dedicated endpoints"
    long_batch_flow    = "Long Batch Upload → Direct to long-batch-files → AWS Batch → DynamoDB"
    short_batch_flow   = "Short Batch Upload → Direct to short-batch-files → Lambda → Textract/Comprehend → DynamoDB"
    smart_routing      = "Generic Upload → Smart Router → Size/type-based decision → Appropriate processing pipeline"
    search_flow        = "Both APIs → Search Lambda → DynamoDB (Fuzzy Search)"
    retrieval_flow     = "Both APIs → Reader Lambda → CloudFront CDN"
    delete_flow        = "Both APIs → Deleter Lambda → Recycle Bin → TTL (30 days)"
    restore_flow       = "Both APIs → Restorer Lambda → DynamoDB (Restore)"
    
    key_features = [
      "Dual API architecture (Long & Short batch)",
      "Smart routing based on file size and type",
      "Forced routing via dedicated endpoints",
      "Serverless auto-scaling processing",
      "Fast processing for small files (10-30s)",
      "Heavy processing for complex files (5-15min)",
      "Fuzzy search with RapidFuzz",
      "Semantic text processing",
      "Cost-optimized infrastructure",
      "Comprehensive monitoring",
      "Recycle bin with 30-day retention",
      "Soft delete and restore functionality"
    ]
  }
}

# Environment Information
output "environment" {
  description = "Deployment environment details"
  value = {
    environment      = var.environment
    project_name     = var.project_name
    aws_region       = var.aws_region
    aws_account_id   = data.aws_caller_identity.current.account_id
    deployment_time  = timestamp()
  }
}

# Troubleshooting Information
output "troubleshooting" {
  description = "Helpful troubleshooting information"
  value = {
    logs_insights_query = <<-EOT
      fields @timestamp, @message
      | filter @message like /ERROR/
      | sort @timestamp desc
      | limit 20
    EOT
    
    check_batch_jobs = "aws batch list-jobs --job-queue ${aws_batch_job_queue.main.name} --job-status FAILED"
    
    check_dlq = "aws sqs receive-message --queue-url ${aws_sqs_queue.batch_dlq.url}"
    
    lambda_errors = "aws logs tail /aws/lambda/${var.project_name}-${var.environment}-* --follow --filter-pattern ERROR"
  }
}

# Security Information
output "security" {
  description = "Security configuration summary"
  value = {
    encryption = {
      s3_buckets       = "AES-256 encryption enabled"
      dynamodb_tables  = "Encryption at rest enabled"
      cloudfront       = "HTTPS only with TLS 1.2+"
    }
    
    access_control = {
      s3_public_access = "Blocked"
      api_authentication = var.enable_rate_limiting ? "API keys required for higher limits" : "Public access"
      cloudfront_oai   = "Origin Access Identity configured"
    }
    
    network_security = {
      vpc_isolation    = "Private subnets for compute"
      security_groups  = "Least privilege rules"
      vpc_endpoints    = "Private AWS service access"
    }
  }
}