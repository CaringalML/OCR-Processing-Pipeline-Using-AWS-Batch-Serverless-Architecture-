# S3 Bucket for file uploads
resource "aws_s3_bucket" "upload_bucket" {
  bucket = "${var.project_name}-${var.environment}-uploads"

  lifecycle {
    prevent_destroy = false
    ignore_changes = [
      bucket,
      tags["Name"]
    ]
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-uploads"
  })
}

# S3 Bucket Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "upload_bucket_encryption" {
  bucket = aws_s3_bucket.upload_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = var.s3_sse_algorithm
    }
  }

  lifecycle {
    ignore_changes = [
      rule
    ]
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "upload_bucket_pab" {
  bucket = aws_s3_bucket.upload_bucket.id

  block_public_acls       = var.s3_block_public_acls
  block_public_policy     = var.s3_block_public_policy
  ignore_public_acls      = var.s3_ignore_public_acls
  restrict_public_buckets = var.s3_restrict_public_buckets

  lifecycle {
    ignore_changes = [
      block_public_acls,
      block_public_policy,
      ignore_public_acls,
      restrict_public_buckets
    ]
  }
}

# S3 Bucket CORS Configuration for uploads
resource "aws_s3_bucket_cors_configuration" "upload_bucket_cors" {
  bucket = aws_s3_bucket.upload_bucket.id

  depends_on = [
    aws_s3_bucket_public_access_block.upload_bucket_pab,
    aws_s3_bucket_server_side_encryption_configuration.upload_bucket_encryption
  ]

  cors_rule {
    allowed_headers = var.s3_cors_allowed_headers
    allowed_methods = var.s3_cors_allowed_methods
    allowed_origins = var.s3_cors_allowed_origins
    expose_headers  = var.s3_cors_expose_headers
    max_age_seconds = var.s3_cors_max_age_seconds
  }

  lifecycle {
    ignore_changes = [
      cors_rule
    ]
  }
}

# S3 Bucket Lifecycle Rule
resource "aws_s3_bucket_lifecycle_configuration" "upload_bucket_lifecycle" {
  bucket = aws_s3_bucket.upload_bucket.id

  depends_on = [
    aws_s3_bucket_public_access_block.upload_bucket_pab,
    aws_s3_bucket_server_side_encryption_configuration.upload_bucket_encryption
  ]

  # Rule for short-batch-files folder
  rule {
    id     = "short-batch-storage-transitions"
    status = var.s3_lifecycle_rule_status

    filter {
      prefix = var.s3_short_batch_prefix
    }

    # Standard → Standard-IA (30 days)
    transition {
      days          = var.s3_transition_to_ia_days
      storage_class = var.s3_storage_class_standard_ia
    }

    # Standard-IA → Glacier Instant Retrieval (365 days / 1 year)
    transition {
      days          = var.s3_transition_to_glacier_ir_days
      storage_class = var.s3_storage_class_glacier_ir
    }

    # Glacier IR → Glacier Flexible (1095 days / 3 years)
    transition {
      days          = var.s3_transition_to_glacier_days
      storage_class = var.s3_storage_class_glacier
    }

    # Glacier → Deep Archive (3650 days / 10 years)
    transition {
      days          = var.s3_transition_to_deep_archive_days
      storage_class = var.s3_storage_class_deep_archive
    }
  }

  # Rule for long-batch-files folder
  rule {
    id     = "long-batch-storage-transitions"
    status = var.s3_lifecycle_rule_status

    filter {
      prefix = var.s3_long_batch_prefix
    }

    # Standard → Standard-IA (30 days)
    transition {
      days          = var.s3_transition_to_ia_days
      storage_class = var.s3_storage_class_standard_ia
    }

    # Standard-IA → Glacier Instant Retrieval (365 days / 1 year)
    transition {
      days          = var.s3_transition_to_glacier_ir_days
      storage_class = var.s3_storage_class_glacier_ir
    }

    # Glacier IR → Glacier Flexible (1095 days / 3 years)
    transition {
      days          = var.s3_transition_to_glacier_days
      storage_class = var.s3_storage_class_glacier
    }

    # Glacier → Deep Archive (3650 days / 10 years)
    transition {
      days          = var.s3_transition_to_deep_archive_days
      storage_class = var.s3_storage_class_deep_archive
    }
  }

  lifecycle {
    ignore_changes = [
      rule
    ]
  }
}

# S3 Bucket Event Notification to EventBridge - REMOVED
# Long batch processing now uses direct SQS messaging from uploader Lambda
# No EventBridge rules consume S3 events, so this configuration is obsolete

# S3 Bucket Policy for CloudFront OAC
data "aws_iam_policy_document" "s3_bucket_policy" {
  statement {
    actions   = var.s3_get_object_actions
    resources = ["${aws_s3_bucket.upload_bucket.arn}/*"]

    principals {
      type        = var.iam_principal_type_service
      identifiers = [var.cloudfront_service_principal]
    }

    condition {
      test     = var.iam_condition_test_string_equals
      variable = var.iam_condition_variable_source_arn
      values   = [aws_cloudfront_distribution.s3_distribution.arn]
    }
  }

  statement {
    actions   = var.s3_put_object_actions
    resources = ["${aws_s3_bucket.upload_bucket.arn}/*"]

    principals {
      type        = var.iam_principal_type_aws
      identifiers = [aws_iam_role.uploader_role.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "upload_bucket_policy" {
  bucket = aws_s3_bucket.upload_bucket.id
  policy = data.aws_iam_policy_document.s3_bucket_policy.json

  lifecycle {
    ignore_changes = [
      policy
    ]
  }
}