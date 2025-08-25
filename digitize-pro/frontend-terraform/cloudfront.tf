resource "aws_cloudfront_origin_access_control" "s3_oac" {
  name                              = "${var.oac_name}-${var.environment}"
  description                       = "Origin Access Control for React frontend S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "s3_distribution" {
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = var.cloudfront_price_class
  default_root_object = "index.html"
  comment             = "React Frontend CDN Distribution"

  origin {
    domain_name              = aws_s3_bucket.storage_bucket.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.s3_oac.id
    origin_id                = var.origin_id
    origin_path              = var.react_app_path
  }


  default_cache_behavior {
    allowed_methods        = var.cloudfront_allowed_methods
    cached_methods         = var.cloudfront_cached_methods
    target_origin_id       = var.origin_id
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = true
      headers      = var.forwarded_headers
      cookies {
        forward = "none"
      }
    }

    min_ttl     = var.cloudfront_ttl.min
    default_ttl = var.cloudfront_ttl.default
    max_ttl     = var.cloudfront_ttl.max

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.rewrite_uri.arn
    }
  }

  dynamic "custom_error_response" {
    for_each = var.error_responses
    content {
      error_code         = custom_error_response.value.error_code
      response_code      = custom_error_response.value.response_code
      response_page_path = custom_error_response.value.response_page_path
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      Name        = "${var.environment}-${var.distribution_name}"
      Purpose     = "React Frontend CDN"
      Component   = "Frontend Infrastructure"
    }
  )
}

resource "aws_cloudfront_function" "rewrite_uri" {
  name    = "${var.function_name}-${var.environment}"
  runtime = var.cloudfront_function_runtime
  comment = "SPA Router - Redirects non-file requests to index.html"
  publish = true

  code = <<EOF
function handler(event) {
    var request = event.request;
    var uri = request.uri;
    
    if (!uri.includes('.')) {
        request.uri = '/index.html';
    }
    
    return request;
}
EOF

  lifecycle {
    create_before_destroy = true
  }
}