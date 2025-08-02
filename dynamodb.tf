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