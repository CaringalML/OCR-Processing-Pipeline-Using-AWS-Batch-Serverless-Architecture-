# DynamoDB Table for File Metadata
resource "aws_dynamodb_table" "file_metadata" {
  name         = "${var.project_name}-${var.environment}-file-metadata"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "file_id"
  range_key    = "upload_timestamp"

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
    name = "file_id"
    type = "S"
  }

  attribute {
    name = "upload_timestamp"
    type = "S"
  }

  attribute {
    name = "bucket_name"
    type = "S"
  }

  attribute {
    name = "processing_status"
    type = "S"
  }

  # Global Secondary Index for querying by bucket
  global_secondary_index {
    name            = "BucketIndex"
    hash_key        = "bucket_name"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by status
  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "processing_status"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-file-metadata"
  })
}

# DynamoDB Table for Processing Results
resource "aws_dynamodb_table" "processing_results" {
  name         = "${var.project_name}-${var.environment}-processing-results"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "file_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-processing-results"
  })
}

# DynamoDB Table for Recycle Bin
resource "aws_dynamodb_table" "recycle_bin" {
  name         = "${var.project_name}-${var.environment}-recycle-bin"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "file_id"
  range_key    = "deleted_timestamp"

  attribute {
    name = "file_id"
    type = "S"
  }

  attribute {
    name = "deleted_timestamp"
    type = "S"
  }

  attribute {
    name = "deletion_date"
    type = "S"
  }

  # Global Secondary Index for querying by deletion date (for cleanup)
  global_secondary_index {
    name            = "DeletionDateIndex"
    hash_key        = "deletion_date"
    range_key       = "deleted_timestamp"
    projection_type = "ALL"
  }

  # TTL for automatic deletion after 30 days
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-recycle-bin"
  })
}

# DynamoDB Table for OCR Budget Tracking
resource "aws_dynamodb_table" "ocr_budget_tracking" {
  name         = "ocr_budget_tracking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.common_tags, {
    Name = "ocr-budget-tracking"
    Purpose = "Track Claude API usage costs for OCR processing"
  })
}

# ========================================
# DEDICATED INVOICE PROCESSING TABLES
# ========================================

# DynamoDB Table for Invoice Metadata
resource "aws_dynamodb_table" "invoice_metadata" {
  name         = "${var.project_name}-${var.environment}-invoice-metadata"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "invoice_id"
  range_key    = "upload_timestamp"

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
    name = "invoice_id"
    type = "S"
  }

  attribute {
    name = "upload_timestamp"
    type = "S"
  }

  attribute {
    name = "vendor_name"
    type = "S"
  }

  attribute {
    name = "invoice_number"
    type = "S"
  }

  attribute {
    name = "processing_status"
    type = "S"
  }

  attribute {
    name = "invoice_date"
    type = "S"
  }

  attribute {
    name = "business_category"
    type = "S"
  }

  # Global Secondary Index for querying by vendor name
  global_secondary_index {
    name            = "VendorIndex"
    hash_key        = "vendor_name"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by invoice number
  global_secondary_index {
    name            = "InvoiceNumberIndex"
    hash_key        = "invoice_number"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by processing status
  global_secondary_index {
    name            = "ProcessingStatusIndex"
    hash_key        = "processing_status"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by invoice date
  global_secondary_index {
    name            = "InvoiceDateIndex"
    hash_key        = "invoice_date"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by business category
  global_secondary_index {
    name            = "BusinessCategoryIndex"
    hash_key        = "business_category"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-invoice-metadata"
    Purpose = "Dedicated storage for invoice document metadata with specialized indexing"
  })
}

# DynamoDB Table for Invoice Processing Results
resource "aws_dynamodb_table" "invoice_processing_results" {
  name         = "${var.project_name}-${var.environment}-invoice-processing-results"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "invoice_id"
  range_key    = "processing_timestamp"

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
    name = "invoice_id"
    type = "S"
  }

  attribute {
    name = "processing_timestamp"
    type = "S"
  }

  attribute {
    name = "extraction_confidence"
    type = "S"
  }

  attribute {
    name = "processing_method"
    type = "S"
  }

  # Global Secondary Index for querying by extraction confidence
  global_secondary_index {
    name            = "ConfidenceIndex"
    hash_key        = "extraction_confidence"
    range_key       = "processing_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by processing method
  global_secondary_index {
    name            = "ProcessingMethodIndex"
    hash_key        = "processing_method"
    range_key       = "processing_timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-invoice-processing-results"
    Purpose = "Dedicated storage for invoice OCR processing results and structured data"
  })
}

# DynamoDB Table for Invoice Recycle Bin
resource "aws_dynamodb_table" "invoice_recycle_bin" {
  name         = "${var.project_name}-${var.environment}-invoice-recycle-bin"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "invoice_id"
  range_key    = "deleted_timestamp"

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
    name = "invoice_id"
    type = "S"
  }

  attribute {
    name = "deleted_timestamp"
    type = "S"
  }

  attribute {
    name = "deletion_date"
    type = "S"
  }

  attribute {
    name = "vendor_name"
    type = "S"
  }

  # Global Secondary Index for querying by deletion date (for cleanup)
  global_secondary_index {
    name            = "DeletionDateIndex"
    hash_key        = "deletion_date"
    range_key       = "deleted_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying deleted invoices by vendor
  global_secondary_index {
    name            = "DeletedVendorIndex"
    hash_key        = "vendor_name"
    range_key       = "deleted_timestamp"
    projection_type = "ALL"
  }

  # TTL for automatic deletion after 90 days (longer retention for invoices)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = false
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-invoice-recycle-bin"
    Purpose = "Dedicated recycle bin for deleted invoice documents with extended retention"
  })
}