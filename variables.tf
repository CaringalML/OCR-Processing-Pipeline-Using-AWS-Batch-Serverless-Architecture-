variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ocr-processor"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "batch_compute_environment_name" {
  description = "Name for the Batch compute environment"
  type        = string
  default     = "ocr-processor-compute-env"
}

variable "batch_job_queue_name" {
  description = "Name for the Batch job queue"
  type        = string
  default     = "ocr-processor-job-queue"
}

variable "batch_job_definition_name" {
  description = "Name for the Batch job definition"
  type        = string
  default     = "ocr-processor-job-def"
}

variable "api_gateway_name" {
  description = "Name for the API Gateway"
  type        = string
  default     = "ocr-processor-api"
}

variable "lambda_function_name" {
  description = "Name for the Lambda function"
  type        = string
  default     = "ocr-processor-batch-trigger"
}

# Auto-cleanup configuration variables
variable "cleanup_age_hours" {
  description = "Age in hours after which jobs/tasks should be cleaned up"
  type        = number
  default     = 24
  validation {
    condition     = var.cleanup_age_hours > 0 && var.cleanup_age_hours <= 168
    error_message = "Cleanup age must be between 1 and 168 hours (1 week)."
  }
}

variable "cleanup_schedule_expression" {
  description = "CloudWatch Events schedule expression for cleanup (cron or rate format)"
  type        = string
  default     = "rate(6 hours)"
  validation {
    condition     = can(regex("^(rate\\([0-9]+ (minute|minutes|hour|hours|day|days)\\)|cron\\(.+\\))$", var.cleanup_schedule_expression))
    error_message = "Schedule expression must be in rate() or cron() format. Examples: 'rate(6 hours)', 'cron(0 2 * * ? *)'."
  }
}

variable "enable_auto_cleanup" {
  description = "Enable automatic cleanup of old jobs and tasks"
  type        = bool
  default     = true
}

# Optional: Customize cleanup function settings
variable "cleanup_lambda_timeout" {
  description = "Timeout for cleanup Lambda function in seconds"
  type        = number
  default     = 300
  validation {
    condition     = var.cleanup_lambda_timeout >= 60 && var.cleanup_lambda_timeout <= 900
    error_message = "Lambda timeout must be between 60 and 900 seconds."
  }
}

variable "cleanup_lambda_memory" {
  description = "Memory allocation for cleanup Lambda function in MB"
  type        = number
  default     = 256
  validation {
    condition     = var.cleanup_lambda_memory >= 128 && var.cleanup_lambda_memory <= 3008
    error_message = "Lambda memory must be between 128 and 3008 MB."
  }
}

variable "cleanup_log_retention_days" {
  description = "Number of days to retain cleanup Lambda logs"
  type        = number
  default     = 14
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cleanup_log_retention_days)
    error_message = "Log retention must be one of: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653 days."
  }
}

# VPC Endpoints configuration
variable "enable_ssm_endpoints" {
  description = "Enable SSM VPC endpoints for debugging/troubleshooting"
  type        = bool
  default     = true # Changed from false to true
}

# Long-running job configuration
variable "batch_job_timeout_hours" {
  description = "Timeout for batch jobs in hours"
  type        = number
  default     = 24
  validation {
    condition     = var.batch_job_timeout_hours >= 1 && var.batch_job_timeout_hours <= 168
    error_message = "Batch job timeout must be between 1 and 168 hours (1 week)."
  }
}

variable "long_running_cleanup_age_hours" {
  description = "Age in hours for long-running job cleanup (should be longer than job timeout)"
  type        = number
  default     = 48 # 2 days - longer than job timeout
}

# Common tags for all resources
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "file-processor"
    Environment = "dev"
    ManagedBy   = "terraform"
    Purpose     = "file-processing-pipeline"
  }
}

# S3 and file processing configuration
variable "upload_bucket_prefix" {
  description = "Prefix for the upload bucket name"
  type        = string
  default     = "file-processing"
}

variable "max_file_size_mb" {
  description = "Maximum file size allowed for upload in MB"
  type        = number
  default     = 100
  validation {
    condition     = var.max_file_size_mb > 0 && var.max_file_size_mb <= 1000
    error_message = "Max file size must be between 1 and 1000 MB."
  }
}

# SQS configuration
variable "sqs_visibility_timeout_seconds" {
  description = "SQS message visibility timeout in seconds"
  type        = number
  default     = 900 # 15 minutes
  validation {
    condition     = var.sqs_visibility_timeout_seconds >= 30 && var.sqs_visibility_timeout_seconds <= 43200
    error_message = "SQS visibility timeout must be between 30 seconds and 12 hours."
  }
}

variable "sqs_max_receive_count" {
  description = "Maximum number of times a message can be received before moving to DLQ"
  type        = number
  default     = 3
  validation {
    condition     = var.sqs_max_receive_count >= 1 && var.sqs_max_receive_count <= 10
    error_message = "Max receive count must be between 1 and 10."
  }
}

# DynamoDB configuration
variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode"
  type        = string
  default     = "PAY_PER_REQUEST"
  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "DynamoDB billing mode must be either PAY_PER_REQUEST or PROVISIONED."
  }
}

# CloudFront configuration
variable "cloudfront_price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
  validation {
    condition     = contains(["PriceClass_All", "PriceClass_200", "PriceClass_100"], var.cloudfront_price_class)
    error_message = "CloudFront price class must be PriceClass_All, PriceClass_200, or PriceClass_100."
  }
}

# EventBridge configuration
variable "eventbridge_retry_attempts" {
  description = "Number of retry attempts for EventBridge targets"
  type        = number
  default     = 2
  validation {
    condition     = var.eventbridge_retry_attempts >= 0 && var.eventbridge_retry_attempts <= 10
    error_message = "EventBridge retry attempts must be between 0 and 10."
  }
}

variable "eventbridge_max_age_seconds" {
  description = "Maximum age for EventBridge events in seconds"
  type        = number
  default     = 3600 # 1 hour
  validation {
    condition     = var.eventbridge_max_age_seconds >= 60 && var.eventbridge_max_age_seconds <= 86400
    error_message = "EventBridge max age must be between 60 seconds and 24 hours."
  }
}