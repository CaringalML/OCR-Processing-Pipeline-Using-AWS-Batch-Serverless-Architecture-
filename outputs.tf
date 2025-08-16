# ========================================
# 🚀 API ENDPOINTS - READY TO USE
# ========================================
output "api_endpoints" {
  description = "Complete API endpoints - copy and paste ready"
  value = {
    # 📄 DOCUMENT PROCESSING (Primary Workflow)
    
    # Smart upload with automatic routing (≤300KB → Claude AI, >300KB → AWS Batch)
    upload_document = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/upload"
    
    # Get specific processed document by file ID
    get_processed_file = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed?fileId={file_id}"
    
    # List all processed documents with optional filtering
    list_all_processed = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed"
    
    # Edit OCR results and document metadata
    edit_ocr_results = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/processed/edit?fileId={file_id}"
    
    # 🔍 SEARCH & DISCOVERY
    
    # Search documents with fuzzy matching and metadata filtering (UNIFIED - all documents)
    search_documents = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/search?q={query}"
    
    # 📁 FILE MANAGEMENT & RECYCLE BIN (Now consistent under /batch/)
    
    # Delete processed file (soft delete to recycle bin with 30-day retention)
    delete_processed_file = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/delete/{file_id}"
    
    # View all files in recycle bin with expiry information  
    view_recycle_bin = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/recycle-bin"
    
    # Restore file from recycle bin to active state
    restore_deleted_file = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/restore/{file_id}"
    
    # Permanently delete file (bypasses recycle bin - irreversible)
    permanent_delete_file = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/batch/delete/{file_id}?permanent=true"
    
    # ⚡ FORCED PROCESSING (Bypass Smart Routing)
    
    # Force Claude AI processing (recommended for ≤300KB files)
    force_claude_processing = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/upload"
    
    # Force AWS Batch processing (for large/complex files >300KB)
    force_batch_processing = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/long-batch/upload"
    
    # 🧾 SPECIALIZED INVOICE PROCESSING
    
    # Upload invoices for specialized OCR with 60+ field extraction
    upload_invoice = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/invoices/upload"
    
    # Get processed invoice data with structured business fields
    get_processed_invoice = "https://${aws_api_gateway_rest_api.main.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.main.stage_name}/short-batch/invoices/processed?fileId={file_id}"
  }
}

# ========================================
# 🏗️ INFRASTRUCTURE RESOURCES
# ========================================
output "infrastructure" {
  description = "AWS infrastructure components for monitoring and debugging"
  value = {
    # 🗄️ Storage & CDN
    storage = {
      s3_bucket          = aws_s3_bucket.upload_bucket.id
      cloudfront_url     = "https://${aws_cloudfront_distribution.s3_distribution.domain_name}"
      cloudfront_domain  = aws_cloudfront_distribution.s3_distribution.domain_name
    }
    
    # 🗃️ Database Tables
    database = {
      main_ocr_table     = aws_dynamodb_table.processing_results.name
      invoice_table      = aws_dynamodb_table.invoice_processing_results.name
      recycle_bin_table  = aws_dynamodb_table.recycle_bin.name
    }
    
    # 🔄 Message Queues (for monitoring)
    queues = {
      short_batch_queue  = aws_sqs_queue.short_batch_queue.url
      long_batch_queue   = aws_sqs_queue.batch_queue.url
      invoice_queue      = aws_sqs_queue.invoice_queue.url
      short_batch_dlq    = aws_sqs_queue.short_batch_dlq.url
      long_batch_dlq     = aws_sqs_queue.batch_dlq.url
    }
    
    # 🌍 Environment Info
    environment = {
      aws_region         = var.aws_region
      environment_name   = var.environment
      project_name       = var.project_name
      deployment_time    = timestamp()
    }
  }
}


# ========================================
# 📊 SYSTEM OVERVIEW
# ========================================
output "system_overview" {
  description = "Quick system overview and key features"
  value = {
    # 🔄 Processing Flow
    workflow = "📱 UPLOAD → 🤖 SMART ROUTING → ⚡ PROCESSING → 💾 STORAGE → 🔍 SEARCH"
    
    # 🛤️ Smart Routing Rules
    routing = {
      small_files    = "≤300KB → Claude AI (30s-10min, 15min Lambda max)"
      large_files    = ">300KB → AWS Batch (5-60min, up to 24hrs for very large files)"
      invoices       = "Any size → Specialized invoice processing (60+ fields)"
    }
    
    # ✨ Key Features
    features = [
      "🤖 Smart file size routing",
      "📚 Rich publication metadata", 
      "🗄️ Unified table architecture",
      "⚡ Real-time status tracking",
      "🌐 CloudFront CDN delivery",
      "🔍 Advanced fuzzy search",
      "♻️ Recycle bin (30-day retention)",
      "🔧 File restoration capability"
    ]
    
    # 📋 Metadata Fields
    supported_metadata = "file, publication, year, title, author, description, page, tags"
    
    # 📤 Response Format
    api_response_structure = "{ metadata: {...}, ocrResults: {...}, status: '...', fileId: '...' }"
  }
}