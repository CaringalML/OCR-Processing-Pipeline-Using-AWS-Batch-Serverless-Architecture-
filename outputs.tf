# API Gateway Outputs with Environment Stages
output "api_gateway" {
  description = "Unified API Gateway with environment stages"
  value = {
    base_url = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}"

    # Unified/General Endpoints (combines both batch types)
    unified_endpoints = {
      smart_upload     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/upload"
      batch_processed  = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed"
      search_all       = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/search"
      edit             = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/edit"
      delete           = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/delete/{fileId}"
      recycle_bin      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/recycle-bin"
      restore          = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/restore/{fileId}"
    }

    long_batch_endpoints = {
      upload      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/upload"
      process     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/process"
      search      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/search"
      edit        = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/edit"
      delete      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/delete/{fileId}"
      recycle_bin = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/recycle-bin"
      restore     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/restore/{fileId}"
    }

    short_batch_endpoints = {
      upload      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/upload"
      process     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/process"
      search      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/search"
      edit        = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/edit"
      delete      = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/delete/{fileId}"
      recycle_bin = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/recycle-bin"
      restore     = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/restore/{fileId}"

      # Invoice Processing Endpoints
      invoice_upload    = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/invoices/upload"
      invoice_processed = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/invoices/processed"
    }
  }
}

# S3 and CloudFront Outputs
output "storage" {
  description = "Storage resources information"
  value = {
    upload_bucket_name = aws_s3_bucket.upload_bucket.id
    upload_bucket_arn  = aws_s3_bucket.upload_bucket.arn
    cloudfront_domain  = aws_cloudfront_distribution.s3_distribution.domain_name
    cloudfront_url     = "https://${aws_cloudfront_distribution.s3_distribution.domain_name}"
    cloudfront_id      = aws_cloudfront_distribution.s3_distribution.id
    cloudfront_status  = aws_cloudfront_distribution.s3_distribution.status
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
      name        = aws_lambda_function.uploader.function_name
      arn         = aws_lambda_function.uploader.arn
      invoke_arn  = aws_lambda_function.uploader.invoke_arn
      memory_size = aws_lambda_function.uploader.memory_size
      timeout     = aws_lambda_function.uploader.timeout
    }
    reader = {
      name        = aws_lambda_function.reader.function_name
      arn         = aws_lambda_function.reader.arn
      invoke_arn  = aws_lambda_function.reader.invoke_arn
      memory_size = aws_lambda_function.reader.memory_size
      timeout     = aws_lambda_function.reader.timeout
    }
    search = {
      name        = aws_lambda_function.search.function_name
      arn         = aws_lambda_function.search.arn
      invoke_arn  = aws_lambda_function.search.invoke_arn
      memory_size = aws_lambda_function.search.memory_size
      timeout     = aws_lambda_function.search.timeout
    }
    editor = {
      name        = aws_lambda_function.editor.function_name
      arn         = aws_lambda_function.editor.arn
      invoke_arn  = aws_lambda_function.editor.invoke_arn
      memory_size = aws_lambda_function.editor.memory_size
      timeout     = aws_lambda_function.editor.timeout
    }
    short_batch_processor = {
      name        = aws_lambda_function.short_batch_processor.function_name
      arn         = aws_lambda_function.short_batch_processor.arn
      invoke_arn  = aws_lambda_function.short_batch_processor.invoke_arn
      memory_size = aws_lambda_function.short_batch_processor.memory_size
      timeout     = aws_lambda_function.short_batch_processor.timeout
    }
    sqs_processor = {
      name        = aws_lambda_function.sqs_batch_processor.function_name
      arn         = aws_lambda_function.sqs_batch_processor.arn
      invoke_arn  = aws_lambda_function.sqs_batch_processor.invoke_arn
      memory_size = aws_lambda_function.sqs_batch_processor.memory_size
      timeout     = aws_lambda_function.sqs_batch_processor.timeout
    }
    batch_reconciliation = {
      name        = aws_lambda_function.batch_status_reconciliation.function_name
      arn         = aws_lambda_function.batch_status_reconciliation.arn
      memory_size = aws_lambda_function.batch_status_reconciliation.memory_size
      timeout     = aws_lambda_function.batch_status_reconciliation.timeout
    }
    dead_job_detector = {
      name        = aws_lambda_function.dead_job_detector.function_name
      arn         = aws_lambda_function.dead_job_detector.arn
      memory_size = aws_lambda_function.dead_job_detector.memory_size
      timeout     = aws_lambda_function.dead_job_detector.timeout
    }
    deleter = {
      name        = aws_lambda_function.deleter.function_name
      arn         = aws_lambda_function.deleter.arn
      invoke_arn  = aws_lambda_function.deleter.invoke_arn
      memory_size = aws_lambda_function.deleter.memory_size
      timeout     = aws_lambda_function.deleter.timeout
    }
    restorer = {
      name        = aws_lambda_function.restorer.function_name
      arn         = aws_lambda_function.restorer.arn
      invoke_arn  = aws_lambda_function.restorer.invoke_arn
      memory_size = aws_lambda_function.restorer.memory_size
      timeout     = aws_lambda_function.restorer.timeout
    }
    recycle_bin_reader = {
      name        = aws_lambda_function.recycle_bin_reader.function_name
      arn         = aws_lambda_function.recycle_bin_reader.arn
      invoke_arn  = aws_lambda_function.recycle_bin_reader.invoke_arn
      memory_size = aws_lambda_function.recycle_bin_reader.memory_size
      timeout     = aws_lambda_function.recycle_bin_reader.timeout
    }
    # long_batch_uploader and short_batch_uploader removed - functionality consolidated into s3_uploader
    short_batch_submitter = {
      name        = aws_lambda_function.short_batch_submitter.function_name
      arn         = aws_lambda_function.short_batch_submitter.arn
      invoke_arn  = aws_lambda_function.short_batch_submitter.invoke_arn
      memory_size = aws_lambda_function.short_batch_submitter.memory_size
      timeout     = aws_lambda_function.short_batch_submitter.timeout
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
      name       = aws_dynamodb_table.processing_results.name
      arn        = aws_dynamodb_table.processing_results.arn
      stream_arn = aws_dynamodb_table.processing_results.stream_arn
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


# SNS Topics Outputs
output "monitoring" {
  description = "Monitoring and alerting resources"
  value = {
    alerts_topic_arn  = aws_sns_topic.alerts.arn
    alerts_topic_name = aws_sns_topic.alerts.name
    admin_email       = var.admin_alert_email
    dlq_alarms = {
      long_batch = {
        message_count_alarm = aws_cloudwatch_metric_alarm.dlq_messages.alarm_name
        high_count_alarm    = aws_cloudwatch_metric_alarm.dlq_high_message_count.alarm_name
        message_age_alarm   = aws_cloudwatch_metric_alarm.dlq_message_age.alarm_name
      }
      short_batch = {
        message_count_alarm = aws_cloudwatch_metric_alarm.short_batch_dlq_messages.alarm_name
        high_count_alarm    = aws_cloudwatch_metric_alarm.short_batch_dlq_high_message_count.alarm_name
        message_age_alarm   = aws_cloudwatch_metric_alarm.short_batch_dlq_message_age.alarm_name
      }
    }
    alert_thresholds = {
      dlq_any_messages     = "Immediately (> 0 messages)"
      dlq_high_count_long  = "More than 10 messages"
      dlq_high_count_short = "More than 5 messages"
      dlq_age_long_batch   = "Messages older than 1 hour"
      dlq_age_short_batch  = "Messages older than 30 minutes"
    }
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
    # Essential API Examples
    smart_upload = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/upload' -F 'file=@document.pdf'"
    get_processed = "curl 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed?fileId=YOUR_FILE_ID'"
    search_all = "curl 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/search?q=electric+cars'"
    process_long = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/process' -H 'Content-Type: application/json' -d '{\"fileId\": \"YOUR_FILE_ID\"}'"
    process_short = "curl -X POST 'https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/process' -H 'Content-Type: application/json' -d '{\"fileId\": \"YOUR_FILE_ID\"}'"
  }
}


# Architecture Overview
output "architecture" {
  description = "System architecture overview"
  value = {
    unified_retrieval = "Unified Processed (/batch/processed) → Reader Lambda → Combines both batch types → CloudFront CDN"
    key_features = [
      "Unified /batch/processed?fileId= endpoint",
      "Smart routing based on file size",
      "Fast Claude AI processing (10-30s)",
      "Heavy AWS Batch processing (5-15min)",
      "Specialized invoice OCR processing"
    ]
  }
}

# Environment Information
output "environment" {
  description = "Deployment environment details"
  value = {
    environment     = var.environment
    project_name    = var.project_name
    aws_region      = var.aws_region
    aws_account_id  = data.aws_caller_identity.current.account_id
    deployment_time = timestamp()
  }
}


