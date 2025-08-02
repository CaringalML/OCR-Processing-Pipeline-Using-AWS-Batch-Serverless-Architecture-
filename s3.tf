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
      sse_algorithm = "AES256"
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

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

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
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
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
    status = "Enabled"

    filter {
      prefix = "short-batch-files/"
    }

    # Standard → Standard-IA (30 days)
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Standard-IA → Glacier Instant Retrieval (365 days / 1 year)
    transition {
      days          = 365
      storage_class = "GLACIER_IR"
    }

    # Glacier IR → Glacier Flexible (1095 days / 3 years)
    transition {
      days          = 1095
      storage_class = "GLACIER"
    }

    # Glacier → Deep Archive (3650 days / 10 years)
    transition {
      days          = 3650
      storage_class = "DEEP_ARCHIVE"
    }
  }

  # Rule for long-batch-files folder
  rule {
    id     = "long-batch-storage-transitions"
    status = "Enabled"

    filter {
      prefix = "long-batch-files/"
    }

    # Standard → Standard-IA (30 days)
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    # Standard-IA → Glacier Instant Retrieval (365 days / 1 year)
    transition {
      days          = 365
      storage_class = "GLACIER_IR"
    }

    # Glacier IR → Glacier Flexible (1095 days / 3 years)
    transition {
      days          = 1095
      storage_class = "GLACIER"
    }

    # Glacier → Deep Archive (3650 days / 10 years)
    transition {
      days          = 3650
      storage_class = "DEEP_ARCHIVE"
    }
  }

  lifecycle {
    ignore_changes = [
      rule
    ]
  }
}

# S3 Bucket Event Notification to EventBridge
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket      = aws_s3_bucket.upload_bucket.id
  eventbridge = true
  
  depends_on = [
    aws_s3_bucket_public_access_block.upload_bucket_pab,
    aws_s3_bucket_server_side_encryption_configuration.upload_bucket_encryption
  ]

  lifecycle {
    ignore_changes = [
      eventbridge
    ]
  }
}

# S3 Bucket Policy for CloudFront OAC
data "aws_iam_policy_document" "s3_bucket_policy" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.upload_bucket.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.s3_distribution.arn]
    }
  }

  statement {
    actions   = ["s3:PutObject", "s3:PutObjectAcl"]
    resources = ["${aws_s3_bucket.upload_bucket.arn}/*"]

    principals {
      type        = "AWS"
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