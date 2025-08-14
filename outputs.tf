# ========================================
# ESSENTIAL API ENDPOINTS
# ========================================
output "api_endpoints" {
  description = "Essential API endpoints for developers"
  value = {
    base_url = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}"

    # Main endpoints developers need
    upload                = "POST ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/upload"
    get_processed         = "GET  ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed?fileId={fileId}"
    list_all_processed    = "GET  ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed"
    search                = "GET  ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/search?q={query}"
    edit                  = "PUT  ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/edit"
    delete                = "DELETE ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/delete/{fileId}"
    
    # Force specific processing
    force_short_batch     = "POST ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/process"
    force_long_batch      = "POST ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/process"
    
    # Invoice processing
    invoice_upload        = "POST ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/invoices/upload"
    invoice_processed     = "GET  ${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/invoices/processed"
  }
}

# ========================================
# STORAGE & CDN
# ========================================
output "storage" {
  description = "Storage and CDN URLs"
  value = {
    s3_bucket             = aws_s3_bucket.upload_bucket.id
    cloudfront_url        = "https://${aws_cloudfront_distribution.s3_distribution.domain_name}"
    cloudfront_domain     = aws_cloudfront_distribution.s3_distribution.domain_name
  }
}

# ========================================
# DATABASE TABLES
# ========================================
output "database" {
  description = "Database table names"
  value = {
    main_ocr_table        = aws_dynamodb_table.processing_results.name
    invoice_table         = aws_dynamodb_table.invoice_processing_results.name
    recycle_bin_table     = aws_dynamodb_table.recycle_bin.name
  }
}

# ========================================
# SQS QUEUES (for monitoring)
# ========================================
output "sqs_queues" {
  description = "SQS queue URLs for monitoring"
  value = {
    short_batch_queue     = aws_sqs_queue.short_batch_queue.url
    long_batch_queue      = aws_sqs_queue.batch_queue.url
    invoice_queue         = aws_sqs_queue.invoice_queue.url
    short_batch_dlq       = aws_sqs_queue.short_batch_dlq.url
    long_batch_dlq        = aws_sqs_queue.batch_dlq.url
  }
}

# ========================================
# TESTING EXAMPLES
# ========================================
output "curl_examples" {
  description = "Ready-to-use API testing commands"
  value = {
    upload_with_publication = <<-EOT
    curl -X POST '${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/upload' \
      -F 'file=@document.pdf' \
      -F 'publication=Nature Journal' \
      -F 'year=2024' \
      -F 'title=Climate Study' \
      -F 'author=Dr. Smith' \
      -F 'page=15-23' \
      -F 'tags=climate,research'
    EOT

    get_file = "curl '${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed?fileId=YOUR_FILE_ID'"

    list_all = "curl '${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed'"

    search_by_publication = "curl '${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/search?publication=Nature&year=2024'"
  }
}

# ========================================
# ARCHITECTURE OVERVIEW
# ========================================
output "system_overview" {
  description = "Quick system overview for developers"
  value = {
    processing_flow = <<-EOT
    📱 UPLOAD → 🤖 SMART ROUTING → ⚡ PROCESSING → 💾 STORAGE → 🔍 SEARCH
    
    Routes:
    • ≤300KB → Short-batch (Claude AI, 30s-5min)
    • >300KB → Long-batch (AWS Textract, 5-30min)
    • Invoice → Specialized processing
    
    Publication Metadata:
    • Upload: publication, year, title, author, description, page, tags
    • Storage: Single table with metadata + OCR results
    • Search: Filter by any metadata field
    EOT

    key_features = [
      "✅ Smart file size routing",
      "✅ Publication metadata support", 
      "✅ Single table architecture",
      "✅ Real-time status tracking",
      "✅ CloudFront CDN delivery",
      "✅ Comprehensive search"
    ]

    data_flow = {
      upload_fields = "file, publication, year, title, author, description, page, tags"
      storage_table = aws_dynamodb_table.processing_results.name
      response_format = "{ metadata: {...}, ocrResults: {...} }"
    }
  }
}

# ========================================
# ENVIRONMENT INFO
# ========================================
output "environment" {
  description = "Environment details"
  value = {
    project_name          = var.project_name
    environment           = var.environment
    aws_region            = var.aws_region
    aws_account_id        = data.aws_caller_identity.current.account_id
    deployment_time       = timestamp()
  }
}