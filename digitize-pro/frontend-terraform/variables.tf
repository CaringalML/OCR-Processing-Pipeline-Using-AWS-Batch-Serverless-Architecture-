
variable "aws_region" {
  description = "AWS region for deploying frontend infrastructure"
  type        = string
  default     = "ap-southeast-2"
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "AWS region must be in the format like 'us-east-1' or 'ap-southeast-2'."
  }
}

variable "environment" {
  description = "Deployment environment (production, staging, development)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be one of: production, staging, development."
  }
}


variable "s3_bucket_name" {
  description = "Name of the S3 bucket storing React build artifacts"
  type        = string
  default     = "digitize-pro-frontend"
  validation {
    condition     = can(regex("^[a-z0-9.-]+$", var.s3_bucket_name)) && length(var.s3_bucket_name) >= 3 && length(var.s3_bucket_name) <= 63
    error_message = "S3 bucket name must be 3-63 characters, lowercase letters, numbers, dots, and hyphens only."
  }
}

variable "oac_name" {
  description = "Name for the CloudFront Origin Access Control securing S3 access"
  type        = string
  default     = "digitize-pro-oac"
}

variable "function_name" {
  description = "Name for the CloudFront Function handling React Router SPA routing"
  type        = string
  default     = "digitize-pro-function"
}

variable "distribution_name" {
  description = "Name for the CloudFront distribution serving the React application"
  type        = string
  default     = "digitize-pro-distribution"
}


variable "origin_id" {
  description = "Origin ID for the S3 bucket in CloudFront distribution"
  type        = string
  default     = "S3-Frontend-App"
}

variable "react_app_path" {
  description = "Path to the React build artifacts within the S3 bucket"
  type        = string
  default     = "/frontend-build"
  validation {
    condition     = can(regex("^/[a-zA-Z0-9_-]+", var.react_app_path))
    error_message = "React app path must start with '/' and contain valid characters."
  }
}


variable "cloudfront_price_class" {
  description = "CloudFront distribution price class"
  type        = string
  default     = "PriceClass_100"
  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.cloudfront_price_class)
    error_message = "Price class must be PriceClass_100, PriceClass_200, or PriceClass_All."
  }
}

variable "cloudfront_ttl" {
  description = "CloudFront distribution TTL cache settings in seconds"
  type = object({
    min     = number
    default = number
    max     = number
  })
  default = {
    min     = 0
    default = 3600
    max     = 86400
  }
  validation {
    condition     = var.cloudfront_ttl.min >= 0 && var.cloudfront_ttl.default >= var.cloudfront_ttl.min && var.cloudfront_ttl.max >= var.cloudfront_ttl.default
    error_message = "TTL values must be: min >= 0, default >= min, max >= default."
  }
}

variable "cloudfront_allowed_methods" {
  description = "HTTP methods allowed by CloudFront"
  type        = list(string)
  default     = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
}

variable "cloudfront_cached_methods" {
  description = "HTTP methods cached by CloudFront"
  type        = list(string)
  default     = ["GET", "HEAD"]
  validation {
    condition     = alltrue([for method in var.cloudfront_cached_methods : contains(["GET", "HEAD"], method)])
    error_message = "Only GET and HEAD methods should be cached for optimal performance."
  }
}

variable "forwarded_headers" {
  description = "Headers forwarded to origin for API communication"
  type        = list(string)
  default     = ["Origin", "Authorization", "Content-Type", "Accept"]
}

variable "error_responses" {
  description = "Custom error responses for React SPA routing"
  type = list(object({
    error_code         = number
    response_code      = number
    response_page_path = string
  }))
  default = [
    {
      error_code         = 403
      response_code      = 200
      response_page_path = "/index.html"
    },
    {
      error_code         = 404
      response_code      = 200
      response_page_path = "/index.html"
    }
  ]
}


variable "cors_allowed_headers" {
  description = "Headers allowed in CORS requests"
  type        = list(string)
  default     = ["*"]
}

variable "cors_allowed_methods" {
  description = "HTTP methods allowed for CORS requests"
  type        = list(string)
  default     = ["GET", "HEAD", "PUT", "POST", "DELETE"]
  validation {
    condition     = length(var.cors_allowed_methods) > 0
    error_message = "At least one CORS method must be allowed."
  }
}

variable "cors_max_age_seconds" {
  description = "Maximum time in seconds that browsers can cache CORS preflight responses"
  type        = number
  default     = 3600
  validation {
    condition     = var.cors_max_age_seconds >= 0 && var.cors_max_age_seconds <= 86400
    error_message = "CORS max age must be between 0 and 86400 seconds (24 hours)."
  }
}


variable "tags" {
  description = "Common tags applied to all frontend infrastructure resources"
  type        = map(string)
  default = {
    Project     = "Digitize-pro"
    Environment = "dev"
    ManagedBy   = "Terraform"
    Component   = "Frontend Infrastructure"
    Owner       = "Martin Caringal"
  }
}


variable "force_destroy" {
  description = "Allow S3 bucket deletion even with objects"
  type        = bool
  default     = true
}

variable "versioning_enabled" {
  description = "Enable S3 bucket versioning for React build artifacts"
  type        = bool
  default     = false
}


variable "cloudfront_function_runtime" {
  description = "JavaScript runtime version for CloudFront Functions"
  type        = string
  default     = "cloudfront-js-1.0"
  validation {
    condition     = contains(["cloudfront-js-1.0"], var.cloudfront_function_runtime)
    error_message = "CloudFront function runtime must be 'cloudfront-js-1.0'."
  }
}

