# Origin Access Control for CloudFront
resource "aws_cloudfront_origin_access_control" "main" {
  name                              = "${var.project_name}-${var.environment}-oac"
  description                       = "OAC for S3 bucket access"
  origin_access_control_origin_type = var.cloudfront_oac_origin_type
  signing_behavior                  = var.cloudfront_oac_signing_behavior
  signing_protocol                  = var.cloudfront_oac_signing_protocol
}

# CloudFront Distribution for S3 bucket
resource "aws_cloudfront_distribution" "s3_distribution" {
  origin {
    domain_name              = aws_s3_bucket.upload_bucket.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.main.id
    origin_id                = "S3-${aws_s3_bucket.upload_bucket.id}"
  }

  enabled             = var.cloudfront_enabled
  is_ipv6_enabled     = var.cloudfront_ipv6_enabled
  comment             = "CloudFront distribution for ${var.project_name} file processing"
  default_root_object = var.cloudfront_default_root_object

  # Cache behavior for upload files
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = var.cloudfront_cached_methods
    target_origin_id = "S3-${aws_s3_bucket.upload_bucket.id}"

    forwarded_values {
      query_string = var.cloudfront_query_string_forwarding
      cookies {
        forward = var.cloudfront_cookies_forwarding
      }
    }

    viewer_protocol_policy = var.cloudfront_viewer_protocol_policy
    min_ttl                = var.cloudfront_min_ttl
    default_ttl            = var.cloudfront_default_ttl
    max_ttl                = var.cloudfront_max_ttl
    compress               = var.cloudfront_compression_enabled
  }

  # Cache behavior for images
  ordered_cache_behavior {
    path_pattern     = var.cloudfront_uploads_path_pattern
    allowed_methods  = var.cloudfront_allowed_methods_read_only
    cached_methods   = var.cloudfront_cached_methods
    target_origin_id = "S3-${aws_s3_bucket.upload_bucket.id}"

    forwarded_values {
      query_string = var.cloudfront_query_string_forwarding
      headers      = var.cloudfront_forwarded_headers
      cookies {
        forward = var.cloudfront_cookies_forwarding
      }
    }

    min_ttl                = var.cloudfront_min_ttl
    default_ttl            = var.cloudfront_uploads_default_ttl
    max_ttl                = var.cloudfront_uploads_max_ttl
    compress               = var.cloudfront_compression_enabled
    viewer_protocol_policy = var.cloudfront_viewer_protocol_policy
  }

  # Geographic restrictions
  restrictions {
    geo_restriction {
      restriction_type = var.cloudfront_geo_restriction_type
    }
  }

  # SSL Certificate
  viewer_certificate {
    cloudfront_default_certificate = var.cloudfront_default_certificate
  }

  # Price class
  price_class = var.cloudfront_price_class

  # Custom error pages
  custom_error_response {
    error_code         = var.cloudfront_error_403_code
    response_code      = var.cloudfront_error_response_code
    response_page_path = var.cloudfront_error_response_page_path
  }

  custom_error_response {
    error_code         = var.cloudfront_error_404_code
    response_code      = var.cloudfront_error_response_code
    response_page_path = var.cloudfront_error_response_page_path
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-cloudfront"
  })
}

# CloudWatch Log Group for CloudFront
resource "aws_cloudwatch_log_group" "cloudfront_logs" {
  name              = "/aws/cloudfront/${var.project_name}-${var.environment}"
  retention_in_days = var.cleanup_log_retention_days

  tags = var.common_tags
}