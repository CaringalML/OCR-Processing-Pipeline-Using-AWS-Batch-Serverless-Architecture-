# REMOVED: File Metadata Table - Now using unified results table
# All file metadata is now stored in ocr-processor-batch-processing-results table

# DynamoDB Table for Processing Results - Shared by both short-batch and long-batch
resource "aws_dynamodb_table" "processing_results" {
  name         = "ocr-processor-batch-processing-results"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = var.dynamodb_processing_results_hash_key

  attribute {
    name = var.dynamodb_file_metadata_hash_key
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "user_id"
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "upload_timestamp"
    type = var.dynamodb_attribute_type_string
  }

  # Global Secondary Index for user-based queries
  global_secondary_index {
    name            = "UserIndex"
    hash_key        = "user_id"
    range_key       = "upload_timestamp"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = var.dynamodb_server_side_encryption_enabled
  }

  tags = merge(var.common_tags, {
    Name = "ocr-processor-batch-processing-results",
    Purpose = "Shared OCR results storage for both short-batch and long-batch processing with user isolation"
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

  attribute {
    name = "user_id"
    type = var.dynamodb_attribute_type_string
  }

  # Global Secondary Index for querying by deletion date (for cleanup)
  global_secondary_index {
    name            = var.dynamodb_deletion_date_index_name
    hash_key        = var.dynamodb_deletion_date_attribute_name
    range_key       = var.dynamodb_recycle_bin_range_key
    projection_type = "ALL"
  }

  # Global Secondary Index for user-based queries
  global_secondary_index {
    name            = "UserRecycleIndex"
    hash_key        = "user_id"
    range_key       = "deleted_timestamp"
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

# DynamoDB Table for Invoice Processing Results
resource "aws_dynamodb_table" "invoice_processing_results" {
  name         = "ocr-processor-batch-invoice-processing-results"
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
    Name = "ocr-processor-batch-invoice-processing-results",
    Purpose = "Invoice OCR processing results storage"
  })
}

# DynamoDB Table for Finalized OCR Results
resource "aws_dynamodb_table" "ocr_finalized" {
  name         = "ocr-processor-batch-finalized-results"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = var.dynamodb_file_metadata_hash_key
  range_key    = "finalized_timestamp"

  attribute {
    name = var.dynamodb_file_metadata_hash_key
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "finalized_timestamp"
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "text_source"
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "user_id"
    type = var.dynamodb_attribute_type_string
  }

  # Global Secondary Index for querying by text source type
  global_secondary_index {
    name            = "TextSourceIndex"
    hash_key        = "text_source"
    range_key       = "finalized_timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for user-based queries
  global_secondary_index {
    name            = "UserFinalizedIndex"
    hash_key        = "user_id"
    range_key       = "finalized_timestamp"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = var.dynamodb_server_side_encryption_enabled
  }

  tags = merge(var.common_tags, {
    Name = "ocr-processor-batch-finalized-results",
    Purpose = "Store finalized OCR results with user-selected text version and user isolation"
  })
}

# DynamoDB Table for Edit History with TTL
resource "aws_dynamodb_table" "edit_history" {
  name         = "ocr-processor-edit-history"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = var.dynamodb_file_metadata_hash_key
  range_key    = "edit_timestamp"

  attribute {
    name = var.dynamodb_file_metadata_hash_key
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "edit_timestamp"
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "user_id"
    type = var.dynamodb_attribute_type_string
  }

  # Global Secondary Index for user-based queries
  global_secondary_index {
    name            = "UserEditHistoryIndex"
    hash_key        = "user_id"
    range_key       = "edit_timestamp"
    projection_type = "ALL"
  }

  # TTL configuration for automatic cleanup (30 days)
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = var.dynamodb_server_side_encryption_enabled
  }

  tags = merge(var.common_tags, {
    Name = "ocr-processor-edit-history",
    Purpose = "Store edit history entries with automatic 30-day cleanup via TTL and user isolation"
  })
}



# =============================================================================
# USER AUTHENTICATION & PROFILES TABLES
# =============================================================================
# These tables support the Cognito authentication system and user data isolation.
# All other tables in this file already include user_id GSIs for user-scoped queries.
# =============================================================================

# User Profiles Table - Stores extended user information
resource "aws_dynamodb_table" "user_profiles" {
  name         = "ocr-processor-user-profiles"
  billing_mode = var.dynamodb_billing_mode
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = var.dynamodb_attribute_type_string
  }

  attribute {
    name = "email"
    type = var.dynamodb_attribute_type_string
  }

  # Global Secondary Index for email lookup
  global_secondary_index {
    name            = "EmailIndex"
    hash_key        = "email"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = var.dynamodb_server_side_encryption_enabled
  }

  tags = merge(var.common_tags, {
    Name    = "ocr-processor-user-profiles"
    Purpose = "Store user profiles and settings for authenticated users"
  })
}