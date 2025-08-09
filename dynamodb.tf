# DynamoDB Table for File Metadata
resource "aws_dynamodb_table" "file_metadata" {
  name         = "${var.project_name}-${var.environment}-file-metadata"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = var.dynamodb_file_metadata_hash_key
  range_key    = var.dynamodb_file_metadata_range_key

  lifecycle {
    prevent_destroy = false
    ignore_changes = [
      name,
      billing_mode,
      global_secondary_index,
      ttl,
      point_in_time_recovery
    ]
  }

  attribute {
    name = var.dynamodb_file_metadata_hash_key
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = var.dynamodb_file_metadata_range_key
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = var.dynamodb_bucket_attribute_name
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = var.dynamodb_processing_status_attribute_name
    type = var.dynamodb_attribute_type_string
  }

  # Global Secondary Index for querying by bucket
  global_secondary_index {
    name            = var.dynamodb_bucket_index_name
    hash_key        = var.dynamodb_bucket_attribute_name
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by status
  global_secondary_index {
    name            = var.dynamodb_status_index_name
    hash_key        = var.dynamodb_processing_status_attribute_name
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = var.dynamodb_file_metadata_ttl_attribute
    enabled        = var.dynamodb_ttl_enabled
  }

  point_in_time_recovery {
    enabled = var.dynamodb_point_in_time_recovery_enabled
  }

  server_side_encryption {
    enabled = var.dynamodb_server_side_encryption_enabled
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-file-metadata"
  })
}

# DynamoDB Table for Processing Results
resource "aws_dynamodb_table" "processing_results" {
  name         = "${var.project_name}-${var.environment}-processing-results"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = var.dynamodb_processing_results_hash_key

  attribute {
    name = var.dynamodb_file_metadata_hash_key
    type = var.dynamodb_attribute_type_string
  }

  server_side_encryption {
    enabled = var.dynamodb_server_side_encryption_enabled
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-processing-results"
  })
}

# DynamoDB Table for Recycle Bin
resource "aws_dynamodb_table" "recycle_bin" {
  name         = "${var.project_name}-${var.environment}-recycle-bin"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = var.dynamodb_recycle_bin_hash_key
  range_key    = var.dynamodb_recycle_bin_range_key

  attribute {
    name = var.dynamodb_file_metadata_hash_key
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "deleted_timestamp"
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "deletion_date"
    type = var.dynamodb_attribute_type_string
  }

  # Global Secondary Index for querying by deletion date (for cleanup)
  global_secondary_index {
    name            = var.dynamodb_deletion_date_index_name
    hash_key        = var.dynamodb_deletion_date_attribute_name
    range_key       = var.dynamodb_recycle_bin_range_key
    projection_type = "ALL"
  }

  # TTL for automatic deletion after 30 days
  ttl {
    attribute_name = var.dynamodb_recycle_bin_ttl_attribute
    enabled        = true
  }

  server_side_encryption {
    enabled = var.dynamodb_server_side_encryption_enabled
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-recycle-bin"
  })
}

# DynamoDB Table for OCR Budget Tracking
resource "aws_dynamodb_table" "ocr_budget_tracking" {
  name         = var.dynamodb_budget_tracking_table_name
  billing_mode = var.dynamodb_billing_mode
  hash_key     = var.dynamodb_budget_tracking_hash_key

  attribute {
    name = var.dynamodb_budget_tracking_hash_key
    type = var.dynamodb_attribute_type_string
  }

  server_side_encryption {
    enabled = var.dynamodb_server_side_encryption_enabled
  }

  tags = merge(var.common_tags, {
    Name    = "ocr-budget-tracking"
    Purpose = "Track Claude API usage costs for OCR processing"
  })
}

# ========================================
# DEDICATED INVOICE PROCESSING TABLES - DEPRECATED
# ========================================
# These tables have been consolidated into the main file_metadata and processing_results tables
# All invoice processing now uses the main tables with processing_route = 'invoice-ocr'
# This consolidation fixes the "Invoice Not Found" issue and simplifies the architecture

# DEPRECATED: Invoice Metadata Table - Now using file_metadata table
# resource "aws_dynamodb_table" "invoice_metadata" {
#   name         = "${var.project_name}-${var.environment}-invoice-metadata"
#   billing_mode = var.dynamodb_billing_mode
#   hash_key     = "invoice_id"
#   range_key    = "upload_timestamp"

#   lifecycle {
#     prevent_destroy = var.dynamodb_prevent_destroy
#     ignore_changes = [
#       name,
#       billing_mode,
#       global_secondary_index,
#       ttl,
#       point_in_time_recovery
#     ]
#   }
# 
#   attribute {
#     name = "invoice_id"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = var.dynamodb_file_metadata_range_key
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "vendor_name"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "invoice_number"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = var.dynamodb_processing_status_attribute_name
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "invoice_date"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "business_category"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   # Global Secondary Index for querying by vendor name
#   global_secondary_index {
#     name            = "VendorIndex"
#     hash_key        = "vendor_name"
#     range_key       = "upload_timestamp"
#     projection_type = "ALL"
#   }
# 
#   # Global Secondary Index for querying by invoice number
#   global_secondary_index {
#     name            = "InvoiceNumberIndex"
#     hash_key        = "invoice_number"
#     range_key       = "upload_timestamp"
#     projection_type = "ALL"
#   }
# 
#   # Global Secondary Index for querying by processing status
#   global_secondary_index {
#     name            = "ProcessingStatusIndex"
#     hash_key        = var.dynamodb_processing_status_attribute_name
#     range_key       = "upload_timestamp"
#     projection_type = "ALL"
#   }
# 
#   # Global Secondary Index for querying by invoice date
#   global_secondary_index {
#     name            = "InvoiceDateIndex"
#     hash_key        = "invoice_date"
#     range_key       = "upload_timestamp"
#     projection_type = "ALL"
#   }
# 
#   # Global Secondary Index for querying by business category
#   global_secondary_index {
#     name            = "BusinessCategoryIndex"
#     hash_key        = "business_category"
#     range_key       = "upload_timestamp"
#     projection_type = "ALL"
#   }
# 
#   ttl {
#     attribute_name = "expiration_time"
#     enabled        = true
#   }
# 
#   point_in_time_recovery {
#     enabled = false
#   }
# 
#   server_side_encryption {
#     enabled = true
#   }
# 
#   tags = merge(var.common_tags, {
#     Name = "${var.project_name}-${var.environment}-invoice-metadata"
#     Purpose = "Dedicated storage for invoice document metadata with specialized indexing"
#   })
# }

# DEPRECATED: Invoice Processing Results Table - Now using processing_results table
# resource "aws_dynamodb_table" "invoice_processing_results" {
#   name         = "${var.project_name}-${var.environment}-invoice-processing-results"
#   billing_mode = var.dynamodb_billing_mode
#   hash_key     = "invoice_id"
#   range_key    = "processing_timestamp"
# 
#   lifecycle {
#     prevent_destroy = var.dynamodb_prevent_destroy
#     ignore_changes = [
#       name,
#       billing_mode,
#       global_secondary_index,
#       ttl,
#       point_in_time_recovery
#     ]
#   }
# 
#   attribute {
#     name = "invoice_id"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "processing_timestamp"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "extraction_confidence"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "processing_method"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   # Global Secondary Index for querying by extraction confidence
#   global_secondary_index {
#     name            = "ConfidenceIndex"
#     hash_key        = "extraction_confidence"
#     range_key       = "processing_timestamp"
#     projection_type = "ALL"
#   }
# 
#   # Global Secondary Index for querying by processing method
#   global_secondary_index {
#     name            = "ProcessingMethodIndex"
#     hash_key        = "processing_method"
#     range_key       = "processing_timestamp"
#     projection_type = "ALL"
#   }
# 
#   ttl {
#     attribute_name = "expiration_time"
#     enabled        = true
#   }
# 
#   point_in_time_recovery {
#     enabled = false
#   }
# 
#   server_side_encryption {
#     enabled = true
#   }
# 
#   tags = merge(var.common_tags, {
#     Name = "${var.project_name}-${var.environment}-invoice-processing-results"
#     Purpose = "Dedicated storage for invoice OCR processing results and structured data"
#   })
# }

# DEPRECATED: Invoice Recycle Bin Table - Now using main recycle_bin table
# resource "aws_dynamodb_table" "invoice_recycle_bin" {
#   name         = "${var.project_name}-${var.environment}-invoice-recycle-bin"
#   billing_mode = var.dynamodb_billing_mode
#   hash_key     = "invoice_id"
#   range_key    = "deleted_timestamp"
# 
#   lifecycle {
#     prevent_destroy = var.dynamodb_prevent_destroy
#     ignore_changes = [
#       name,
#       billing_mode,
#       global_secondary_index,
#       ttl,
#       point_in_time_recovery
#     ]
#   }
# 
#   attribute {
#     name = "invoice_id"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "deleted_timestamp"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "deletion_date"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   attribute {
#     name = "vendor_name"
#     type = var.dynamodb_attribute_type_string
#   }
# 
#   # Global Secondary Index for querying by deletion date (for cleanup)
#   global_secondary_index {
#     name            = var.dynamodb_deletion_date_index_name
#     hash_key        = var.dynamodb_deletion_date_attribute_name
#     range_key       = var.dynamodb_recycle_bin_range_key
#     projection_type = "ALL"
#   }
# 
#   # Global Secondary Index for querying deleted invoices by vendor
#   global_secondary_index {
#     name            = "DeletedVendorIndex"
#     hash_key        = "vendor_name"
#     range_key       = var.dynamodb_recycle_bin_range_key
#     projection_type = "ALL"
#   }
# 
#   # TTL for automatic deletion after 90 days (longer retention for invoices)
#   ttl {
#     attribute_name = var.dynamodb_recycle_bin_ttl_attribute
#     enabled        = true
#   }
# 
#   point_in_time_recovery {
#     enabled = false
#   }
# 
#   server_side_encryption {
#     enabled = true
#   }
# 
#   tags = merge(var.common_tags, {
#     Name = "${var.project_name}-${var.environment}-invoice-recycle-bin"
#     Purpose = "Dedicated recycle bin for deleted invoice documents with extended retention"
#   })
# }