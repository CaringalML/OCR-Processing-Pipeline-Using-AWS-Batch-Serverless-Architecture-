
# =============================================================================
# TERRAFORM VARIABLES FOR OCR DOCUMENT PROCESSING SYSTEM
# =============================================================================
#
# This file defines all configurable parameters for the serverless OCR document
# processing and search system. The infrastructure supports intelligent document
# analysis, semantic search, and enterprise-grade document management.
#
# SYSTEM OVERVIEW:
# - Dual processing paths: Lambda (≤300KB) and AWS Batch (>300KB files)  
# - Three-tier API access: Public, Registered (API key), Premium (high limits)
# - Advanced search: Fuzzy matching, semantic processing, multi-field queries
# - Enterprise features: Rate limiting, monitoring, automated cleanup, CDN
# - Cost optimized: Pay-per-use, VPC endpoints, intelligent lifecycle policies
#
# VARIABLE ORGANIZATION:
# The variables are organized into logical sections for easy navigation:
# 1. Core Project Settings (naming, regions, environments)
# 2. Networking (VPC, subnets, security groups)
# 3. Processing Services (Batch, Lambda, API Gateway)
# 4. Storage & Database (S3, DynamoDB, CloudFront)  
# 5. Monitoring & Operations (CloudWatch, SNS, cleanup)
# 6. Security & Access Control (IAM, rate limiting, API keys)
#
# DEPLOYMENT RECOMMENDATIONS:
# - Review all default values before deploying to production
# - Customize common_tags for your organization's tagging strategy
# - Adjust rate limits based on expected traffic patterns
# - Configure admin_alert_email for operational notifications
# - Consider regional data residency requirements when setting aws_region
#
# =============================================================================
# CORE PROJECT CONFIGURATION
# =============================================================================
# These variables define the fundamental settings for the OCR processing system.
# They control the overall project naming, regional deployment, and environment
# setup that affects all infrastructure components.

variable "aws_region" {
  description = "AWS region where all infrastructure will be deployed. Affects costs, latency, and service availability."
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Base name used for all AWS resources. Used in resource naming convention: {project_name}-{environment}-{service}"
  type        = string
  default     = "ocr-processor"
}

variable "environment" {
  description = "Environment identifier (dev/staging/prod). Used in resource naming and tagging for cost allocation and organization."
  type        = string
  default     = "batch"
}

variable "api_stage_name" {
  description = "API Gateway deployment stage name. Appears in API URLs: https://{api-id}.execute-api.{region}.amazonaws.com/{stage}"
  type        = string
  default     = "v1"
}

# =============================================================================
# NETWORKING CONFIGURATION
# =============================================================================
# These variables control the VPC and subnet configuration for the entire system.
# The OCR system uses a multi-tier architecture with public subnets for NAT gateways
# and private subnets for compute resources like AWS Batch and Lambda functions.

variable "vpc_cidr" {
  description = "Primary CIDR block for the VPC. Must be large enough to accommodate all subnets and future growth."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (NAT gateways, ALBs). These subnets have internet gateway routes."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (Batch compute, Lambda functions). Internet access via NAT gateway only."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

# =============================================================================
# AWS BATCH CONFIGURATION
# =============================================================================
# These variables configure the AWS Batch service for processing large files (>300KB).
# Batch provides scalable container-based compute for CPU-intensive OCR tasks.

variable "batch_compute_environment_name" {
  description = "Name for the AWS Batch compute environment. Houses the EC2/Fargate instances for job execution."
  type        = string
  default     = "ocr-processor-compute-env"
}

variable "batch_job_queue_name" {
  description = "Name for the AWS Batch job queue. Jobs are submitted to this queue and executed on the compute environment."
  type        = string
  default     = "ocr-processor-job-queue"
}

variable "batch_job_definition_name" {
  description = "Name for the AWS Batch job definition. Defines the Docker container, CPU/memory, and execution parameters."
  type        = string
  default     = "ocr-processor-job-def"
}

# =============================================================================
# API GATEWAY CONFIGURATION
# =============================================================================
# These variables configure the main API Gateway that serves as the entry point
# for all client requests. The system uses a unified API with multiple endpoints.

variable "api_gateway_name" {
  description = "Name for the main API Gateway REST API. This is the primary entry point for all client interactions."
  type        = string
  default     = "ocr-processor-api"
}

variable "lambda_function_name" {
  description = "Base name for Lambda functions. Individual functions append their specific purpose (e.g., 'batch-trigger')."
  type        = string
  default     = "ocr-processor-batch-trigger"
}

# =============================================================================
# AUTOMATED CLEANUP SYSTEM
# =============================================================================
# These variables configure the automated cleanup system that prevents cost overruns
# by cleaning up old processing jobs, failed tasks, and temporary resources.

variable "cleanup_age_hours" {
  description = "Age in hours after which completed/failed jobs are eligible for cleanup. Balances storage costs with debugging needs."
  type        = number
  default     = 24
  validation {
    condition     = var.cleanup_age_hours > 0 && var.cleanup_age_hours <= 168
    error_message = "Cleanup age must be between 1 and 168 hours (1 week). Values outside this range may impact operations or cost management."
  }
}

variable "cleanup_schedule_expression" {
  description = "CloudWatch Events schedule for cleanup execution. Use rate() for regular intervals or cron() for specific times."
  type        = string
  default     = "rate(6 hours)"
  validation {
    condition     = can(regex("^(rate\\([0-9]+ (minute|minutes|hour|hours|day|days)\\)|cron\\(.+\\))$", var.cleanup_schedule_expression))
    error_message = "Schedule expression must be in rate() or cron() format. Examples: 'rate(6 hours)', 'cron(0 2 * * ? *)'."
  }
}

variable "enable_auto_cleanup" {
  description = "Enable/disable the automated cleanup system. Recommended for production to control costs and resource usage."
  type        = bool
  default     = true
}

# Cleanup Lambda function resource configuration
variable "cleanup_lambda_timeout" {
  description = "Timeout for cleanup Lambda function in seconds. Should be sufficient for cleanup operations across all services."
  type        = number
  default     = 300
  validation {
    condition     = var.cleanup_lambda_timeout >= 60 && var.cleanup_lambda_timeout <= 900
    error_message = "Lambda timeout must be between 60 and 900 seconds. Lower values may cause timeouts, higher values increase costs."
  }
}

variable "cleanup_lambda_memory" {
  description = "Memory allocation for cleanup Lambda function in MB. Higher memory provides more CPU power for faster cleanup operations."
  type        = number
  default     = 256
  validation {
    condition     = var.cleanup_lambda_memory >= 128 && var.cleanup_lambda_memory <= 3008
    error_message = "Lambda memory must be between 128 and 3008 MB. Higher memory increases costs but improves performance."
  }
}

variable "cleanup_log_retention_days" {
  description = "Number of days to retain cleanup Lambda logs. Longer retention aids debugging but increases storage costs."
  type        = number
  default     = 14
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cleanup_log_retention_days)
    error_message = "Log retention must be one of the valid CloudWatch retention periods to ensure proper cost management."
  }
}

# =============================================================================
# VPC ENDPOINTS CONFIGURATION
# =============================================================================
# VPC endpoints reduce data transfer costs and improve security by keeping traffic
# within the AWS network instead of routing through the internet.

variable "enable_ssm_endpoints" {
  description = "Enable SSM VPC endpoints for debugging/troubleshooting batch containers. Adds cost but improves operational capabilities."
  type        = bool
  default     = false
}

# =============================================================================
# BATCH JOB PROCESSING CONFIGURATION
# =============================================================================
# These variables control the execution behavior of long-running batch jobs,
# including timeouts and cleanup policies specific to resource-intensive tasks.

variable "batch_job_timeout_hours" {
  description = "Maximum execution time for batch jobs in hours. Jobs exceeding this limit are terminated to prevent runaway costs."
  type        = number
  default     = 24
  validation {
    condition     = var.batch_job_timeout_hours >= 1 && var.batch_job_timeout_hours <= 168
    error_message = "Batch job timeout must be between 1 and 168 hours (1 week) to balance processing needs with cost control."
  }
}

variable "long_running_cleanup_age_hours" {
  description = "Cleanup age for long-running jobs (should exceed batch_job_timeout_hours). Ensures completed jobs have cleanup buffer time."
  type        = number
  default     = 48 # 2 days - longer than job timeout
}

# =============================================================================
# RESOURCE TAGGING STRATEGY
# =============================================================================
# Consistent tagging enables cost allocation, resource management, and
# operational visibility across the entire infrastructure.

variable "common_tags" {
  description = "Standard tags applied to all AWS resources. Essential for cost tracking, compliance, and resource management."
  type        = map(string)
  default = {
    Project     = "ocr-processor"       # Groups all related resources
    Environment = "batch"               # Distinguishes dev/staging/prod
    ManagedBy   = "terraform"           # Indicates infrastructure as code
    Purpose     = "document-processing" # Business function identifier
    Owner       = "your-team"           # Responsible team/person
    CostCenter  = "engineering"         # Budget allocation
  }
}

# =============================================================================
# EXTERNAL SERVICE INTEGRATION
# =============================================================================
# Configuration for third-party services and APIs used by the OCR system.

variable "anthropic_api_key" {
  description = "API key for Anthropic Claude AI service. Used for intelligent text processing and refinement of OCR results."
  type        = string
  sensitive   = true
}

# =============================================================================
# FILE PROCESSING CONFIGURATION
# =============================================================================
# These variables control file upload limits, processing thresholds, and
# storage bucket configuration for the document processing pipeline.

variable "upload_bucket_prefix" {
  description = "Prefix for the S3 upload bucket name. Full bucket name becomes: {prefix}-{project_name}-{environment}-{random_suffix}"
  type        = string
  default     = "file-processing"
}

variable "max_file_size_mb" {
  description = "Maximum file size for upload in MB. Larger files are rejected to control processing costs and API Gateway limits."
  type        = number
  default     = 100
  validation {
    condition     = var.max_file_size_mb > 0 && var.max_file_size_mb <= 1000
    error_message = "Max file size must be between 1 and 1000 MB to balance functionality with cost and performance."
  }
}

# SQS configuration note: Queue-specific settings are now hardcoded in sqs.tf
# for optimal performance per processing type:
# - Long batch: 16min visibility timeout, 2 retries, long polling for efficiency
# - Short batch: 20min visibility timeout, 3 retries, short polling for responsiveness  
# - Invoice: 30min visibility timeout, 3 retries, short polling for business priority

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
# DynamoDB settings for metadata storage, processing results, and system state management.

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode. PAY_PER_REQUEST for variable workloads, PROVISIONED for predictable traffic patterns."
  type        = string
  default     = "PAY_PER_REQUEST"
  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "DynamoDB billing mode must be either PAY_PER_REQUEST or PROVISIONED."
  }
}

# =============================================================================
# CONTENT DELIVERY NETWORK (CDN) CONFIGURATION
# =============================================================================
# CloudFront distribution settings for global file delivery and caching.

variable "cloudfront_price_class" {
  description = "CloudFront price class determines global edge location coverage. Higher classes increase cost but improve performance."
  type        = string
  default     = "PriceClass_100"
  validation {
    condition     = contains(["PriceClass_All", "PriceClass_200", "PriceClass_100"], var.cloudfront_price_class)
    error_message = "CloudFront price class must be PriceClass_All (most expensive, global), PriceClass_200 (medium cost), or PriceClass_100 (lowest cost, US/Europe only)."
  }
}

# EventBridge variables removed - The system now uses direct SQS messaging from
# the uploader Lambda for improved performance and reduced complexity.

# ========================================
# API GATEWAY RATE LIMITING CONFIGURATION
# ========================================
# Comprehensive rate limiting protects the system from abuse and ensures fair resource
# allocation across different user tiers. This implements a three-tier access model.

# =============================================================================
# RATE LIMITING CONTROL
# =============================================================================
# Master switch for the entire rate limiting system

variable "enable_rate_limiting" {
  description = "Master toggle for API Gateway rate limiting. When disabled, removes all throttling but may expose system to abuse."
  type        = bool
  default     = true
}

# =============================================================================
# STAGE-LEVEL THROTTLING (GLOBAL LIMITS)
# =============================================================================
# These limits apply to ALL API methods and override individual method settings
# if they exceed these values. Acts as a system-wide safety net.

variable "api_throttling_rate_limit" {
  description = "Stage-level sustained request rate limit (requests/second). This is the maximum steady-state request rate across ALL API methods."
  type        = number
  default     = 1000
  validation {
    condition     = var.api_throttling_rate_limit >= 1 && var.api_throttling_rate_limit <= 10000
    error_message = "API throttling rate limit must be between 1 and 10,000 requests per second to balance protection with functionality."
  }
}

variable "api_throttling_burst_limit" {
  description = "Stage-level burst capacity. Allows short-term traffic spikes above the rate limit using a token bucket algorithm."
  type        = number
  default     = 2000
  validation {
    condition     = var.api_throttling_burst_limit >= 1 && var.api_throttling_burst_limit <= 20000
    error_message = "API throttling burst limit must be between 1 and 20,000. Should be >= rate limit to allow for traffic spikes."
  }
}

# =============================================================================
# USAGE PLAN CONFIGURATION (TIERED ACCESS)
# =============================================================================
# Three-tier access model: Public (no auth), Registered (API key), Premium (high limits)
# Each tier has different rate limits, burst capacities, and daily quotas.

# PUBLIC TIER: No authentication required, lowest limits
variable "public_rate_limit" {
  description = "Public tier sustained rate limit (requests/second). No API key required - protects against basic abuse."
  type        = number
  default     = 10
  validation {
    condition     = var.public_rate_limit >= 1 && var.public_rate_limit <= 100
    error_message = "Public rate limit should be conservative (1-100 req/sec) to prevent abuse while allowing legitimate usage."
  }
}

variable "public_burst_limit" {
  description = "Public tier burst capacity. Allows brief spikes in anonymous traffic for legitimate users."
  type        = number
  default     = 20
  validation {
    condition     = var.public_burst_limit >= 1 && var.public_burst_limit <= 200
    error_message = "Public burst limit should be 1-200. Must be >= rate limit to be effective."
  }
}

variable "public_quota_limit" {
  description = "Public tier daily quota (requests/day). Prevents sustained abuse over longer time periods."
  type        = number
  default     = 1000
  validation {
    condition     = var.public_quota_limit >= 100 && var.public_quota_limit <= 100000
    error_message = "Public quota should balance accessibility with abuse prevention (100-100,000 requests/day)."
  }
}

# REGISTERED TIER: API key required, moderate limits
variable "registered_rate_limit" {
  description = "Registered tier rate limit (requests/second). Requires API key authentication for higher limits."
  type        = number
  default     = 50
  validation {
    condition     = var.registered_rate_limit >= 10 && var.registered_rate_limit <= 500
    error_message = "Registered rate limit should be 10-500 req/sec, providing meaningful upgrade over public tier."
  }
}

variable "registered_burst_limit" {
  description = "Registered tier burst capacity. Higher burst allowance for authenticated users with legitimate traffic spikes."
  type        = number
  default     = 100
  validation {
    condition     = var.registered_burst_limit >= 1 && var.registered_burst_limit <= 1000
    error_message = "Registered burst limit should be 1-1,000. Must be >= rate limit for effectiveness."
  }
}

variable "registered_quota_limit" {
  description = "Registered tier daily quota (requests/day). Generous limit for regular business use."
  type        = number
  default     = 10000
  validation {
    condition     = var.registered_quota_limit >= 1000 && var.registered_quota_limit <= 1000000
    error_message = "Registered quota should be 1,000-1,000,000 requests/day for business usage patterns."
  }
}

# PREMIUM TIER: Highest limits for enterprise customers
variable "premium_rate_limit" {
  description = "Premium tier rate limit (requests/second). Enterprise-grade limits for high-volume customers."
  type        = number
  default     = 200
  validation {
    condition     = var.premium_rate_limit >= 50 && var.premium_rate_limit <= 1000
    error_message = "Premium rate limit should be 50-1,000 req/sec for enterprise-level usage."
  }
}

variable "premium_burst_limit" {
  description = "Premium tier burst capacity. Maximum burst allowance for enterprise traffic patterns."
  type        = number
  default     = 400
  validation {
    condition     = var.premium_burst_limit >= 1 && var.premium_burst_limit <= 2000
    error_message = "Premium burst limit should be 1-2,000. Must accommodate enterprise traffic spikes."
  }
}

variable "premium_quota_limit" {
  description = "Premium tier daily quota (requests/day). Enterprise-scale daily processing limits."
  type        = number
  default     = 100000
  validation {
    condition     = var.premium_quota_limit >= 10000 && var.premium_quota_limit <= 10000000
    error_message = "Premium quota should be 10,000-10,000,000 requests/day for enterprise workloads."
  }
}

# =============================================================================
# METHOD-LEVEL THROTTLING (SPECIFIC ENDPOINT OVERRIDES)
# =============================================================================
# These settings override usage plan limits for specific API methods.
# Used to further restrict resource-intensive endpoints like file uploads.

variable "upload_method_rate_limit" {
  description = "Upload endpoint rate limit (req/sec). Lower than general limits due to processing overhead. 0 = use stage default."
  type        = number
  default     = 5
  validation {
    condition     = var.upload_method_rate_limit >= 0 && var.upload_method_rate_limit <= 100
    error_message = "Upload method rate limit should be 0-100 req/sec. Lower values protect backend processing capacity."
  }
}

variable "upload_method_burst_limit" {
  description = "Upload endpoint burst capacity. Limited burst for file upload spikes. 0 = use stage default."
  type        = number
  default     = 10
  validation {
    condition     = var.upload_method_burst_limit >= 0 && var.upload_method_burst_limit <= 200
    error_message = "Upload burst limit should be 0-200. Conservative values prevent overwhelming processing pipeline."
  }
}

variable "processed_method_rate_limit" {
  description = "Processed files endpoint rate limit (req/sec). Higher limits for read operations. 0 = use stage default."
  type        = number
  default     = 20
  validation {
    condition     = var.processed_method_rate_limit >= 0 && var.processed_method_rate_limit <= 200
    error_message = "Processed method rate limit should be 0-200 req/sec. Read operations can handle higher throughput."
  }
}

variable "processed_method_burst_limit" {
  description = "Processed files endpoint burst capacity. Higher burst for result retrieval. 0 = use stage default."
  type        = number
  default     = 40
  validation {
    condition     = var.processed_method_burst_limit >= 0 && var.processed_method_burst_limit <= 400
    error_message = "Processed burst limit should be 0-400. Read operations can handle traffic spikes better."
  }
}

# =============================================================================
# API KEY MANAGEMENT
# =============================================================================
# Controls automatic creation of API keys for testing and development purposes.

variable "create_default_api_keys" {
  description = "Auto-create demo API keys for testing registered/premium tiers. Disable in production for security."
  type        = bool
  default     = true
}

variable "api_key_names" {
  description = "Names for default API keys to create. Used for development and demonstration purposes only."
  type        = list(string)
  default     = ["demo-registered-user", "demo-premium-user"]
  validation {
    condition     = length(var.api_key_names) <= 10
    error_message = "Maximum 10 API keys can be auto-created to prevent key sprawl and security issues."
  }
}

# =============================================================================
# LAMBDA LAYER CONFIGURATION
# =============================================================================
# Controls cross-account access for Lambda layers (advanced use cases).

variable "allow_cross_account_layer_access" {
  description = "Allow other AWS accounts to use Lambda layers from this deployment. Enable for shared service architectures."
  type        = bool
  default     = false
}

# =============================================================================
# ADMINISTRATIVE CONFIGURATION
# =============================================================================
# System administration and alerting configuration.

variable "admin_alert_email" {
  description = "Email address for critical system alerts (DLQ messages, failures). Should be monitored 24/7 in production."
  type        = string
  default     = "lawrencecaringal5@gmail.com"
  validation {
    condition     = can(regex("^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", var.admin_alert_email))
    error_message = "Must be a valid email address for receiving critical system alerts."
  }
}

# =============================================================================
# API GATEWAY ENDPOINT CONFIGURATION
# =============================================================================
# These variables control the API Gateway setup including endpoints, media types,
# URL structure, and integration patterns used throughout the OCR system.

variable "api_gateway_endpoint_types" {
  description = "API Gateway endpoint types. REGIONAL for lower latency, EDGE for global distribution, PRIVATE for VPC-only access."
  type        = list(string)
  default     = ["REGIONAL"]
  validation {
    condition     = alltrue([for t in var.api_gateway_endpoint_types : contains(["EDGE", "REGIONAL", "PRIVATE"], t)])
    error_message = "Endpoint types must be EDGE (CloudFront integration), REGIONAL (direct regional access), or PRIVATE (VPC only)."
  }
}

# =============================================================================
# BINARY MEDIA TYPE SUPPORT
# =============================================================================
# Defines which content types API Gateway treats as binary data (not text).
# Essential for file upload functionality.

variable "api_gateway_binary_media_types" {
  description = "Binary media types for file uploads. API Gateway treats these as binary data rather than attempting text encoding."
  type        = list(string)
  default = [
    "multipart/form-data",     # Form-based file uploads
    "image/*",                 # All image formats (JPEG, PNG, etc.)
    "application/pdf",         # PDF documents
    "application/zip",         # Archive files
    "application/octet-stream" # Generic binary data
  ]
}

# =============================================================================
# API GATEWAY URL STRUCTURE CONFIGURATION  
# =============================================================================
# These variables define the URL path structure for all API endpoints.
# The system uses a hierarchical structure: /processing-type/action/
# Example URLs:
# - /long-batch/upload     - Upload file for batch processing
# - /short-batch/processed - Get processed short batch results  
# - /invoices/search       - Search processed invoices

variable "api_path_long_batch" {
  description = "Path segment for long batch processing endpoints (files >300KB processed via AWS Batch)"
  type        = string
  default     = "long-batch"
}

variable "api_path_short_batch" {
  description = "Path segment for short batch processing endpoints (files ≤300KB processed via Lambda)"
  type        = string
  default     = "short-batch"
}

variable "api_path_upload" {
  description = "Path segment for file upload actions. Combined with processing type (e.g., /long-batch/upload)"
  type        = string
  default     = "upload"
}

variable "api_path_process" {
  description = "Path segment for processing trigger actions (manual processing initiation)"
  type        = string
  default     = "process"
}

variable "api_path_processed" {
  description = "Path segment for retrieving processed results (GET operations for completed files)"
  type        = string
  default     = "processed"
}

variable "api_path_search" {
  description = "Path segment for document search functionality (fuzzy search across OCR content)"
  type        = string
  default     = "search"
}

variable "api_path_edit" {
  description = "Path segment for editing processed document content (OCR correction capabilities)"
  type        = string
  default     = "edit"
}

variable "api_path_delete" {
  description = "Path segment for file deletion actions (moves files to recycle bin)"
  type        = string
  default     = "delete"
}

variable "api_path_recycle_bin" {
  description = "Path segment for recycle bin operations (manage soft-deleted files)"
  type        = string
  default     = "recycle-bin"
}

variable "api_path_restore" {
  description = "Path segment for file restoration actions (recover from recycle bin)"
  type        = string
  default     = "restore"
}

variable "api_path_invoices" {
  description = "Path segment for invoice-specific processing endpoints (specialized OCR for invoice data)"
  type        = string
  default     = "invoices"
}

# =============================================================================
# API GATEWAY INTEGRATION CONFIGURATION
# =============================================================================
# Controls how API Gateway integrates with backend services (primarily Lambda functions).

variable "api_integration_type" {
  description = "API Gateway integration type. AWS_PROXY for Lambda proxy integration (recommended for serverless)."
  type        = string
  default     = "AWS_PROXY"
  validation {
    condition     = contains(["AWS", "AWS_PROXY", "HTTP", "HTTP_PROXY", "MOCK"], var.api_integration_type)
    error_message = "Integration type must be AWS, AWS_PROXY (Lambda proxy), HTTP, HTTP_PROXY, or MOCK."
  }
}

variable "api_integration_http_method" {
  description = "HTTP method for API Gateway backend integrations. POST is standard for Lambda invocations."
  type        = string
  default     = "POST"
  validation {
    condition     = contains(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"], var.api_integration_http_method)
    error_message = "HTTP method must be a valid HTTP verb."
  }
}

# =============================================================================
# CORS (Cross-Origin Resource Sharing) CONFIGURATION
# =============================================================================
# Enables web browsers to access the API from different domains.

variable "cors_allowed_headers" {
  description = "CORS allowed headers for browser requests. Includes standard auth and content headers."
  type        = string
  default     = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
}

variable "cors_allowed_origin" {
  description = "CORS allowed origin. '*' allows all origins (use specific domains in production for security)."
  type        = string
  default     = "'*'"
}

# =============================================================================
# MOCK INTEGRATION RESPONSE
# =============================================================================
# Template response for API Gateway mock integrations (used for OPTIONS requests).

variable "mock_response_template" {
  description = "Mock integration response template for CORS OPTIONS requests."
  type        = string
  default     = "{\"statusCode\": 200}"
}

# =============================================================================
# AWS BATCH CONFIGURATION VARIABLES
# =============================================================================
# AWS Batch is used for processing large files (>300KB) that require significant
# compute resources. These variables configure the compute environment, job queue,
# job definitions, and container specifications for OCR processing workloads.
# 
# Key components:
# - Compute Environment: Manages the underlying EC2/Fargate infrastructure
# - Job Queue: Queues jobs for execution on the compute environment  
# - Job Definition: Defines container image, CPU/memory, and execution parameters
# - Platform Capabilities: Determines whether to use Fargate or EC2 instances
#
# The batch system scales automatically based on job demand and integrates with
# VPC private subnets for security and cost optimization via VPC endpoints.

# Batch compute environment configuration
variable "batch_compute_environment_type" {
  description = "Type of the compute environment"
  type        = string
  default     = "MANAGED"
  validation {
    condition     = contains(["MANAGED", "UNMANAGED"], var.batch_compute_environment_type)
    error_message = "Compute environment type must be MANAGED or UNMANAGED."
  }
}

variable "batch_compute_environment_state" {
  description = "State of the compute environment"
  type        = string
  default     = "ENABLED"
  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.batch_compute_environment_state)
    error_message = "Compute environment state must be ENABLED or DISABLED."
  }
}

# Batch compute resources configuration
variable "batch_compute_resources_type" {
  description = "Type of compute resources"
  type        = string
  default     = "FARGATE"
  validation {
    condition     = contains(["FARGATE", "FARGATE_SPOT", "EC2", "SPOT"], var.batch_compute_resources_type)
    error_message = "Compute resources type must be FARGATE, FARGATE_SPOT, EC2, or SPOT."
  }
}

variable "batch_max_vcpus" {
  description = "Maximum number of vCPUs for the compute environment"
  type        = number
  default     = 256
  validation {
    condition     = var.batch_max_vcpus > 0 && var.batch_max_vcpus <= 10000
    error_message = "Max vCPUs must be between 1 and 10000."
  }
}

# Batch job queue configuration
variable "batch_job_queue_state" {
  description = "State of the job queue"
  type        = string
  default     = "ENABLED"
  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.batch_job_queue_state)
    error_message = "Job queue state must be ENABLED or DISABLED."
  }
}

variable "batch_job_queue_priority" {
  description = "Priority of the job queue"
  type        = number
  default     = 1
  validation {
    condition     = var.batch_job_queue_priority >= 1 && var.batch_job_queue_priority <= 1000
    error_message = "Job queue priority must be between 1 and 1000."
  }
}

variable "batch_compute_environment_order" {
  description = "Order of the compute environment in the job queue"
  type        = number
  default     = 1
  validation {
    condition     = var.batch_compute_environment_order >= 1
    error_message = "Compute environment order must be at least 1."
  }
}

# Batch job definition configuration
variable "batch_job_definition_type" {
  description = "Type of the job definition"
  type        = string
  default     = "container"
  validation {
    condition     = contains(["container", "multinode"], var.batch_job_definition_type)
    error_message = "Job definition type must be container or multinode."
  }
}

variable "batch_platform_capabilities" {
  description = "Platform capabilities for the job definition"
  type        = list(string)
  default     = ["FARGATE"]
  validation {
    condition     = alltrue([for capability in var.batch_platform_capabilities : contains(["FARGATE", "EC2"], capability)])
    error_message = "Platform capabilities must be FARGATE or EC2."
  }
}

# Batch container resource requirements
variable "batch_container_vcpu" {
  description = "vCPU requirement for batch container"
  type        = string
  default     = "0.25"
  validation {
    condition     = can(tonumber(var.batch_container_vcpu)) && tonumber(var.batch_container_vcpu) > 0
    error_message = "Container vCPU must be a positive number."
  }
}

variable "batch_container_memory" {
  description = "Memory requirement for batch container in MB"
  type        = string
  default     = "512"
  validation {
    condition     = can(tonumber(var.batch_container_memory)) && tonumber(var.batch_container_memory) > 0
    error_message = "Container memory must be a positive number."
  }
}

# Batch network configuration
variable "batch_assign_public_ip" {
  description = "Whether to assign public IP to batch containers"
  type        = string
  default     = "DISABLED"
  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.batch_assign_public_ip)
    error_message = "Assign public IP must be ENABLED or DISABLED."
  }
}

# Batch logging configuration
variable "batch_log_driver" {
  description = "Log driver for batch containers"
  type        = string
  default     = "awslogs"
  validation {
    condition     = contains(["awslogs", "fluentd", "gelf", "json-file", "journald", "logentries", "splunk", "syslog"], var.batch_log_driver)
    error_message = "Log driver must be one of the supported Docker log drivers."
  }
}

variable "batch_log_stream_prefix" {
  description = "Log stream prefix for batch containers"
  type        = string
  default     = "batch"
}

# Batch retry strategy
variable "batch_retry_attempts" {
  description = "Number of retry attempts for failed jobs"
  type        = number
  default     = 1
  validation {
    condition     = var.batch_retry_attempts >= 1 && var.batch_retry_attempts <= 10
    error_message = "Retry attempts must be between 1 and 10."
  }
}

# ========================================
# CLEANUP SYSTEM CONFIGURATION VARIABLES
# ========================================

# Cleanup Lambda configuration
variable "cleanup_lambda_runtime" {
  description = "Runtime for cleanup Lambda function"
  type        = string
  default     = "python3.12"
  validation {
    condition     = contains(["python3.8", "python3.9", "python3.10", "python3.11", "python3.12"], var.cleanup_lambda_runtime)
    error_message = "Lambda runtime must be a supported Python version."
  }
}

variable "cleanup_lambda_handler" {
  description = "Handler for cleanup Lambda function"
  type        = string
  default     = "cleanup_processor.lambda_handler"
}

variable "cleanup_log_level" {
  description = "Log level for cleanup Lambda function"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.cleanup_log_level)
    error_message = "Log level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."
  }
}

variable "cleanup_processing_type" {
  description = "Processing type identifier for cleanup system"
  type        = string
  default     = "OCR"
}

# CloudWatch alarm configuration for cleanup
variable "cleanup_alarm_comparison_operator" {
  description = "Comparison operator for cleanup CloudWatch alarm"
  type        = string
  default     = "GreaterThanThreshold"
  validation {
    condition     = contains(["GreaterThanOrEqualToThreshold", "GreaterThanThreshold", "LessThanThreshold", "LessThanOrEqualToThreshold"], var.cleanup_alarm_comparison_operator)
    error_message = "Comparison operator must be a valid CloudWatch alarm operator."
  }
}

variable "cleanup_alarm_evaluation_periods" {
  description = "Number of evaluation periods for cleanup alarm"
  type        = string
  default     = "1"
  validation {
    condition     = can(tonumber(var.cleanup_alarm_evaluation_periods)) && tonumber(var.cleanup_alarm_evaluation_periods) >= 1
    error_message = "Evaluation periods must be a positive number."
  }
}

variable "cleanup_alarm_period" {
  description = "Period in seconds for cleanup alarm evaluation"
  type        = string
  default     = "300"
  validation {
    condition     = can(tonumber(var.cleanup_alarm_period)) && tonumber(var.cleanup_alarm_period) >= 60
    error_message = "Alarm period must be at least 60 seconds."
  }
}

variable "cleanup_alarm_statistic" {
  description = "Statistic for cleanup alarm"
  type        = string
  default     = "Sum"
  validation {
    condition     = contains(["Average", "Maximum", "Minimum", "SampleCount", "Sum"], var.cleanup_alarm_statistic)
    error_message = "Statistic must be Average, Maximum, Minimum, SampleCount, or Sum."
  }
}

variable "cleanup_alarm_threshold" {
  description = "Threshold value for cleanup alarm"
  type        = string
  default     = "0"
  validation {
    condition     = can(tonumber(var.cleanup_alarm_threshold))
    error_message = "Alarm threshold must be a valid number."
  }
}

# EventBridge configuration
variable "cleanup_eventbridge_target_id" {
  description = "Target ID for cleanup EventBridge rule"
  type        = string
  default     = "CleanupLambdaTarget"
}

# IAM policy version
variable "iam_policy_version" {
  description = "Version for IAM policies"
  type        = string
  default     = "2012-10-17"
}

# ========================================
# CLOUDFRONT CONFIGURATION VARIABLES
# ========================================

# Origin Access Control configuration
variable "cloudfront_oac_origin_type" {
  description = "Origin type for CloudFront Origin Access Control"
  type        = string
  default     = "s3"
  validation {
    condition     = contains(["s3"], var.cloudfront_oac_origin_type)
    error_message = "Origin Access Control origin type must be s3."
  }
}

variable "cloudfront_oac_signing_behavior" {
  description = "Signing behavior for CloudFront Origin Access Control"
  type        = string
  default     = "always"
  validation {
    condition     = contains(["always", "never", "no-override"], var.cloudfront_oac_signing_behavior)
    error_message = "Signing behavior must be always, never, or no-override."
  }
}

variable "cloudfront_oac_signing_protocol" {
  description = "Signing protocol for CloudFront Origin Access Control"
  type        = string
  default     = "sigv4"
  validation {
    condition     = contains(["sigv4"], var.cloudfront_oac_signing_protocol)
    error_message = "Signing protocol must be sigv4."
  }
}

# CloudFront Distribution configuration
variable "cloudfront_enabled" {
  description = "Whether the CloudFront distribution is enabled"
  type        = bool
  default     = true
}

variable "cloudfront_ipv6_enabled" {
  description = "Whether IPv6 is enabled for CloudFront distribution"
  type        = bool
  default     = true
}

variable "cloudfront_default_root_object" {
  description = "Default root object for CloudFront distribution"
  type        = string
  default     = "index.html"
}

# Cache behavior configuration
variable "cloudfront_allowed_methods_full" {
  description = "Allowed HTTP methods for CloudFront (full set)"
  type        = list(string)
  default     = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
}

variable "cloudfront_allowed_methods_read_only" {
  description = "Allowed HTTP methods for CloudFront (read-only)"
  type        = list(string)
  default     = ["GET", "HEAD", "OPTIONS"]
}

variable "cloudfront_cached_methods" {
  description = "Cached HTTP methods for CloudFront"
  type        = list(string)
  default     = ["GET", "HEAD"]
}

variable "cloudfront_query_string_forwarding" {
  description = "Whether to forward query strings in CloudFront"
  type        = bool
  default     = false
}

variable "cloudfront_cookies_forwarding" {
  description = "Cookie forwarding behavior for CloudFront"
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "whitelist", "all"], var.cloudfront_cookies_forwarding)
    error_message = "Cookies forwarding must be none, whitelist, or all."
  }
}

variable "cloudfront_viewer_protocol_policy" {
  description = "Viewer protocol policy for CloudFront"
  type        = string
  default     = "redirect-to-https"
  validation {
    condition     = contains(["allow-all", "redirect-to-https", "https-only"], var.cloudfront_viewer_protocol_policy)
    error_message = "Viewer protocol policy must be allow-all, redirect-to-https, or https-only."
  }
}

# TTL configuration
variable "cloudfront_min_ttl" {
  description = "Minimum TTL for CloudFront cache"
  type        = number
  default     = 0
  validation {
    condition     = var.cloudfront_min_ttl >= 0
    error_message = "Minimum TTL must be 0 or greater."
  }
}

variable "cloudfront_default_ttl" {
  description = "Default TTL for CloudFront cache"
  type        = number
  default     = 3600
  validation {
    condition     = var.cloudfront_default_ttl >= 0
    error_message = "Default TTL must be 0 or greater."
  }
}

variable "cloudfront_max_ttl" {
  description = "Maximum TTL for CloudFront cache"
  type        = number
  default     = 86400
  validation {
    condition     = var.cloudfront_max_ttl >= 0
    error_message = "Maximum TTL must be 0 or greater."
  }
}

variable "cloudfront_uploads_default_ttl" {
  description = "Default TTL for uploads path pattern"
  type        = number
  default     = 86400
}

variable "cloudfront_uploads_max_ttl" {
  description = "Maximum TTL for uploads path pattern"
  type        = number
  default     = 31536000
}

variable "cloudfront_compression_enabled" {
  description = "Whether compression is enabled for CloudFront"
  type        = bool
  default     = true
}

# Path patterns
variable "cloudfront_uploads_path_pattern" {
  description = "Path pattern for uploads in CloudFront"
  type        = string
  default     = "uploads/*"
}

variable "cloudfront_forwarded_headers" {
  description = "Headers to forward for uploads path pattern"
  type        = list(string)
  default     = ["Origin"]
}

# Geographic restrictions
variable "cloudfront_geo_restriction_type" {
  description = "Geographic restriction type for CloudFront"
  type        = string
  default     = "none"
  validation {
    condition     = contains(["none", "whitelist", "blacklist"], var.cloudfront_geo_restriction_type)
    error_message = "Geographic restriction type must be none, whitelist, or blacklist."
  }
}

# SSL Certificate
variable "cloudfront_default_certificate" {
  description = "Whether to use CloudFront default certificate"
  type        = bool
  default     = true
}

# Custom error pages
variable "cloudfront_error_403_code" {
  description = "Error code for 403 responses"
  type        = number
  default     = 403
}

variable "cloudfront_error_404_code" {
  description = "Error code for 404 responses"
  type        = number
  default     = 404
}

variable "cloudfront_error_response_code" {
  description = "Response code for error pages"
  type        = number
  default     = 404
}

variable "cloudfront_error_response_page_path" {
  description = "Response page path for error pages"
  type        = string
  default     = "/404.html"
}

# =============================================================================
# CLOUDWATCH MONITORING & ALERTING CONFIGURATION
# =============================================================================
# CloudWatch provides comprehensive monitoring, logging, and alerting for the entire
# OCR processing pipeline. These variables configure log retention, dashboards,
# metrics collection, and alarm thresholds for operational visibility.
#
# Key monitoring areas:
# - Lambda function performance and errors
# - API Gateway request rates and latency  
# - Batch job success/failure rates
# - SQS queue depth and message age
# - DynamoDB read/write capacity utilization
# - Dead letter queue alerts for failed processing
#
# The monitoring system provides proactive alerting to prevent service degradation
# and enables rapid troubleshooting when issues occur.

# CloudWatch Log Group configuration
variable "cloudwatch_log_retention_days" {
  description = "Log retention days for CloudWatch log groups"
  type        = number
  default     = 7
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cloudwatch_log_retention_days)
    error_message = "Log retention must be one of the valid CloudWatch log retention values."
  }
}

variable "cloudwatch_skip_destroy" {
  description = "Whether to skip destroy for CloudWatch log groups"
  type        = bool
  default     = false
}

# CloudWatch Dashboard widget positioning
variable "cloudwatch_dashboard_widget_width" {
  description = "Default width for CloudWatch dashboard widgets"
  type        = number
  default     = 12
  validation {
    condition     = var.cloudwatch_dashboard_widget_width >= 1 && var.cloudwatch_dashboard_widget_width <= 24
    error_message = "Widget width must be between 1 and 24."
  }
}

variable "cloudwatch_dashboard_widget_height" {
  description = "Default height for CloudWatch dashboard widgets"
  type        = number
  default     = 6
  validation {
    condition     = var.cloudwatch_dashboard_widget_height >= 1 && var.cloudwatch_dashboard_widget_height <= 1000
    error_message = "Widget height must be between 1 and 1000."
  }
}

# CloudWatch metrics configuration
variable "cloudwatch_metric_period" {
  description = "Default period for CloudWatch metrics"
  type        = number
  default     = 300
  validation {
    condition     = contains([1, 5, 10, 30, 60, 300, 900, 3600, 21600, 43200, 86400], var.cloudwatch_metric_period)
    error_message = "Period must be a valid CloudWatch metric period."
  }
}

variable "cloudwatch_metric_stat_average" {
  description = "Average statistic for CloudWatch metrics"
  type        = string
  default     = "Average"
  validation {
    condition     = contains(["Average", "Maximum", "Minimum", "Sum", "SampleCount"], var.cloudwatch_metric_stat_average)
    error_message = "Statistic must be a valid CloudWatch metric statistic."
  }
}

variable "cloudwatch_metric_stat_sum" {
  description = "Sum statistic for CloudWatch metrics"
  type        = string
  default     = "Sum"
  validation {
    condition     = contains(["Average", "Maximum", "Minimum", "Sum", "SampleCount"], var.cloudwatch_metric_stat_sum)
    error_message = "Statistic must be a valid CloudWatch metric statistic."
  }
}

# CloudWatch dashboard view settings
variable "cloudwatch_dashboard_view_timeseries" {
  description = "Time series view for CloudWatch dashboard"
  type        = string
  default     = "timeSeries"
}

variable "cloudwatch_dashboard_view_single_value" {
  description = "Single value view for CloudWatch dashboard"
  type        = string
  default     = "singleValue"
}

variable "cloudwatch_dashboard_stacked" {
  description = "Whether to stack metrics in CloudWatch dashboard"
  type        = bool
  default     = false
}

# CloudWatch Alarm configuration
variable "cloudwatch_alarm_comparison_operator" {
  description = "Default comparison operator for CloudWatch alarms"
  type        = string
  default     = "GreaterThanThreshold"
  validation {
    condition     = contains(["GreaterThanOrEqualToThreshold", "GreaterThanThreshold", "LessThanThreshold", "LessThanOrEqualToThreshold"], var.cloudwatch_alarm_comparison_operator)
    error_message = "Comparison operator must be a valid CloudWatch alarm operator."
  }
}

variable "cloudwatch_alarm_evaluation_periods_default" {
  description = "Default evaluation periods for CloudWatch alarms"
  type        = string
  default     = "2"
  validation {
    condition     = can(tonumber(var.cloudwatch_alarm_evaluation_periods_default)) && tonumber(var.cloudwatch_alarm_evaluation_periods_default) >= 1
    error_message = "Evaluation periods must be a positive number."
  }
}

variable "cloudwatch_alarm_evaluation_periods_single" {
  description = "Single evaluation period for CloudWatch alarms"
  type        = string
  default     = "1"
  validation {
    condition     = can(tonumber(var.cloudwatch_alarm_evaluation_periods_single)) && tonumber(var.cloudwatch_alarm_evaluation_periods_single) >= 1
    error_message = "Evaluation periods must be a positive number."
  }
}

# Alarm period configurations
variable "cloudwatch_alarm_period_short" {
  description = "Short period for CloudWatch alarms (1 minute)"
  type        = string
  default     = "60"
}

variable "cloudwatch_alarm_period_medium" {
  description = "Medium period for CloudWatch alarms (2 minutes)"
  type        = string
  default     = "120"
}

variable "cloudwatch_alarm_period_default" {
  description = "Default period for CloudWatch alarms (5 minutes)"
  type        = string
  default     = "300"
}

# Alarm threshold configurations
variable "cloudwatch_alarm_lambda_error_threshold" {
  description = "Threshold for Lambda error alarms"
  type        = string
  default     = "1"
}

variable "cloudwatch_alarm_batch_failure_threshold" {
  description = "Threshold for Batch job failure alarms"
  type        = string
  default     = "0"
}

variable "cloudwatch_alarm_api_4xx_threshold" {
  description = "Threshold for API Gateway 4XX error alarms"
  type        = string
  default     = "20"
}

variable "cloudwatch_alarm_api_5xx_threshold" {
  description = "Threshold for API Gateway 5XX error alarms"
  type        = string
  default     = "10"
}

variable "cloudwatch_alarm_latency_threshold" {
  description = "Threshold for API Gateway latency alarms (milliseconds)"
  type        = string
  default     = "5000"
}

variable "cloudwatch_alarm_rate_limit_threshold" {
  description = "Threshold for rate limiting abuse detection"
  type        = string
  default     = "50"
}

variable "cloudwatch_alarm_lambda_error_spike_threshold" {
  description = "Threshold for Lambda error spike detection"
  type        = string
  default     = "20"
}

# SNS configuration
variable "sns_email_protocol" {
  description = "Protocol for SNS email subscriptions"
  type        = string
  default     = "email"
  validation {
    condition     = contains(["email", "email-json", "sms", "sqs", "application", "lambda", "http", "https"], var.sns_email_protocol)
    error_message = "SNS protocol must be a valid protocol type."
  }
}

# =============================================================================
# DYNAMODB DATABASE CONFIGURATION
# =============================================================================
# DynamoDB serves as the primary database for the OCR system, storing file metadata,
# processing results, recycle bin records, and budget tracking information.
# All tables use pay-per-request billing for cost optimization.
#
# Table structure:
# - File Metadata: Stores upload info, file paths, processing status
# - Processing Results: Contains OCR text, refined content, search metadata  
# - Recycle Bin: Tracks soft-deleted files with TTL for automatic cleanup
# - Budget Tracking: Monitors API usage costs and limits per user/key
#
# Global Secondary Indexes (GSIs) enable efficient querying by status, bucket,
# deletion date, and other access patterns. TTL attributes automatically clean
# up expired records to control storage costs.

# DynamoDB table key configurations
variable "dynamodb_file_metadata_hash_key" {
  description = "Hash key for file metadata table"
  type        = string
  default     = "file_id"
}

variable "dynamodb_file_metadata_range_key" {
  description = "Range key for file metadata table"
  type        = string
  default     = "upload_timestamp"
}

variable "dynamodb_processing_results_hash_key" {
  description = "Hash key for processing results table"
  type        = string
  default     = "file_id"
}

variable "dynamodb_recycle_bin_hash_key" {
  description = "Hash key for recycle bin table"
  type        = string
  default     = "file_id"
}

variable "dynamodb_recycle_bin_range_key" {
  description = "Range key for recycle bin table"
  type        = string
  default     = "deleted_timestamp"
}

variable "dynamodb_budget_tracking_hash_key" {
  description = "Hash key for budget tracking table"
  type        = string
  default     = "id"
}

# DynamoDB attribute type
variable "dynamodb_attribute_type_string" {
  description = "String attribute type for DynamoDB"
  type        = string
  default     = "S"
  validation {
    condition     = contains(["S", "N", "B"], var.dynamodb_attribute_type_string)
    error_message = "Attribute type must be S (String), N (Number), or B (Binary)."
  }
}

# DynamoDB Global Secondary Index configurations
variable "dynamodb_bucket_index_name" {
  description = "Name for bucket index GSI"
  type        = string
  default     = "BucketIndex"
}

variable "dynamodb_status_index_name" {
  description = "Name for status index GSI"
  type        = string
  default     = "StatusIndex"
}

variable "dynamodb_deletion_date_index_name" {
  description = "Name for deletion date index GSI"
  type        = string
  default     = "DeletionDateIndex"
}

variable "dynamodb_gsi_projection_type" {
  description = "Projection type for Global Secondary Indexes"
  type        = string
  default     = "ALL"
  validation {
    condition     = contains(["ALL", "KEYS_ONLY", "INCLUDE"], var.dynamodb_gsi_projection_type)
    error_message = "Projection type must be ALL, KEYS_ONLY, or INCLUDE."
  }
}

# DynamoDB lifecycle settings
variable "dynamodb_prevent_destroy" {
  description = "Whether to prevent destruction of DynamoDB tables"
  type        = bool
  default     = false
}

# DynamoDB TTL configurations
variable "dynamodb_file_metadata_ttl_attribute" {
  description = "TTL attribute name for file metadata table"
  type        = string
  default     = "expiration_time"
}

variable "dynamodb_recycle_bin_ttl_attribute" {
  description = "TTL attribute name for recycle bin table"
  type        = string
  default     = "ttl"
}

variable "dynamodb_ttl_enabled" {
  description = "Whether TTL is enabled for DynamoDB tables"
  type        = bool
  default     = true
}

# DynamoDB point-in-time recovery
variable "dynamodb_point_in_time_recovery_enabled" {
  description = "Whether point-in-time recovery is enabled for DynamoDB tables"
  type        = bool
  default     = false
}

# DynamoDB server-side encryption
variable "dynamodb_server_side_encryption_enabled" {
  description = "Whether server-side encryption is enabled for DynamoDB tables"
  type        = bool
  default     = true
}

# DynamoDB table names (for tables that don't follow the standard naming pattern)
variable "dynamodb_budget_tracking_table_name" {
  description = "Name for the OCR budget tracking table"
  type        = string
  default     = "ocr_budget_tracking"
}

# DynamoDB attribute names
variable "dynamodb_bucket_attribute_name" {
  description = "Attribute name for bucket field"
  type        = string
  default     = "bucket_name"
}

variable "dynamodb_processing_status_attribute_name" {
  description = "Attribute name for processing status field"
  type        = string
  default     = "processing_status"
}

variable "dynamodb_deletion_date_attribute_name" {
  description = "Attribute name for deletion date field"
  type        = string
  default     = "deletion_date"
}

# ========================================
# ECR CONFIGURATION VARIABLES
# ========================================

# ECR repository configuration
variable "ecr_image_tag_mutability" {
  description = "Image tag mutability setting for ECR repository"
  type        = string
  default     = "MUTABLE"
  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.ecr_image_tag_mutability)
    error_message = "Image tag mutability must be MUTABLE or IMMUTABLE."
  }
}

variable "ecr_force_delete" {
  description = "Whether to force delete ECR repository with images"
  type        = bool
  default     = true
}

variable "ecr_scan_on_push" {
  description = "Whether to scan images on push to ECR repository"
  type        = bool
  default     = true
}

variable "ecr_encryption_type" {
  description = "Encryption type for ECR repository"
  type        = string
  default     = "AES256"
  validation {
    condition     = contains(["AES256", "KMS"], var.ecr_encryption_type)
    error_message = "Encryption type must be AES256 or KMS."
  }
}

# ECR lifecycle policy configuration
variable "ecr_lifecycle_tagged_rule_priority" {
  description = "Priority for tagged images lifecycle rule"
  type        = number
  default     = 1
  validation {
    condition     = var.ecr_lifecycle_tagged_rule_priority >= 1 && var.ecr_lifecycle_tagged_rule_priority <= 999
    error_message = "Rule priority must be between 1 and 999."
  }
}

variable "ecr_lifecycle_tagged_rule_description" {
  description = "Description for tagged images lifecycle rule"
  type        = string
  default     = "Keep last 3 images tagged 'latest'"
}

variable "ecr_lifecycle_tagged_status" {
  description = "Tag status for tagged images lifecycle rule"
  type        = string
  default     = "tagged"
  validation {
    condition     = contains(["tagged", "untagged", "any"], var.ecr_lifecycle_tagged_status)
    error_message = "Tag status must be tagged, untagged, or any."
  }
}

variable "ecr_lifecycle_tag_prefix_list" {
  description = "Tag prefix list for tagged images lifecycle rule"
  type        = list(string)
  default     = ["latest"]
}

variable "ecr_lifecycle_tagged_count_type" {
  description = "Count type for tagged images lifecycle rule"
  type        = string
  default     = "imageCountMoreThan"
  validation {
    condition     = contains(["imageCountMoreThan", "sinceImagePushed"], var.ecr_lifecycle_tagged_count_type)
    error_message = "Count type must be imageCountMoreThan or sinceImagePushed."
  }
}

variable "ecr_lifecycle_tagged_count_number" {
  description = "Count number for tagged images lifecycle rule"
  type        = number
  default     = 3
  validation {
    condition     = var.ecr_lifecycle_tagged_count_number >= 1
    error_message = "Count number must be at least 1."
  }
}

variable "ecr_lifecycle_untagged_rule_priority" {
  description = "Priority for untagged images lifecycle rule"
  type        = number
  default     = 2
  validation {
    condition     = var.ecr_lifecycle_untagged_rule_priority >= 1 && var.ecr_lifecycle_untagged_rule_priority <= 999
    error_message = "Rule priority must be between 1 and 999."
  }
}

variable "ecr_lifecycle_untagged_rule_description" {
  description = "Description for untagged images lifecycle rule"
  type        = string
  default     = "Delete untagged images older than 1 day"
}

variable "ecr_lifecycle_untagged_status" {
  description = "Tag status for untagged images lifecycle rule"
  type        = string
  default     = "untagged"
  validation {
    condition     = contains(["tagged", "untagged", "any"], var.ecr_lifecycle_untagged_status)
    error_message = "Tag status must be tagged, untagged, or any."
  }
}

variable "ecr_lifecycle_untagged_count_type" {
  description = "Count type for untagged images lifecycle rule"
  type        = string
  default     = "sinceImagePushed"
  validation {
    condition     = contains(["imageCountMoreThan", "sinceImagePushed"], var.ecr_lifecycle_untagged_count_type)
    error_message = "Count type must be imageCountMoreThan or sinceImagePushed."
  }
}

variable "ecr_lifecycle_untagged_count_unit" {
  description = "Count unit for untagged images lifecycle rule"
  type        = string
  default     = "days"
  validation {
    condition     = contains(["days"], var.ecr_lifecycle_untagged_count_unit)
    error_message = "Count unit must be days."
  }
}

variable "ecr_lifecycle_untagged_count_number" {
  description = "Count number for untagged images lifecycle rule"
  type        = number
  default     = 1
  validation {
    condition     = var.ecr_lifecycle_untagged_count_number >= 1
    error_message = "Count number must be at least 1."
  }
}

variable "ecr_lifecycle_action_type" {
  description = "Action type for ECR lifecycle policy rules"
  type        = string
  default     = "expire"
  validation {
    condition     = contains(["expire"], var.ecr_lifecycle_action_type)
    error_message = "Action type must be expire."
  }
}

# ========================================
# EVENTBRIDGE CONFIGURATION VARIABLES
# ========================================

# EventBridge rule configuration for Batch job state changes
variable "eventbridge_batch_event_source" {
  description = "Event source for Batch job state changes"
  type        = list(string)
  default     = ["aws.batch"]
}

variable "eventbridge_batch_detail_type" {
  description = "Detail type for Batch job state changes"
  type        = list(string)
  default     = ["Batch Job State Change"]
}

variable "eventbridge_batch_job_status" {
  description = "Job statuses to monitor for Batch job state changes"
  type        = list(string)
  default     = ["SUCCEEDED", "FAILED"]
  validation {
    condition     = alltrue([for status in var.eventbridge_batch_job_status : contains(["SUBMITTED", "PENDING", "RUNNABLE", "STARTING", "RUNNING", "SUCCEEDED", "FAILED"], status)])
    error_message = "Job statuses must be valid AWS Batch job statuses."
  }
}

# EventBridge target configuration
variable "eventbridge_batch_reconciliation_target_id" {
  description = "Target ID for Batch job state reconciliation"
  type        = string
  default     = "BatchJobStateReconciliation"
}

variable "eventbridge_dead_job_detection_target_id" {
  description = "Target ID for dead job detection"
  type        = string
  default     = "DeadJobDetection"
}

# EventBridge dead job detection configuration
variable "eventbridge_dead_job_schedule_expression" {
  description = "Schedule expression for dead job detection"
  type        = string
  default     = "rate(30 minutes)"
  validation {
    condition     = can(regex("^(rate\\([0-9]+ (minute|minutes|hour|hours|day|days)\\)|cron\\(.+\\))$", var.eventbridge_dead_job_schedule_expression))
    error_message = "Schedule expression must be in rate() or cron() format."
  }
}

variable "eventbridge_rule_state" {
  description = "State for EventBridge rules"
  type        = string
  default     = "ENABLED"
  validation {
    condition     = contains(["ENABLED", "DISABLED"], var.eventbridge_rule_state)
    error_message = "EventBridge rule state must be ENABLED or DISABLED."
  }
}

# Lambda permission configuration for EventBridge
variable "eventbridge_lambda_action" {
  description = "Lambda action for EventBridge permissions"
  type        = string
  default     = "lambda:InvokeFunction"
}

variable "eventbridge_lambda_principal" {
  description = "Principal for EventBridge Lambda permissions"
  type        = string
  default     = "events.amazonaws.com"
}

variable "eventbridge_batch_permission_statement_id" {
  description = "Statement ID for Batch EventBridge Lambda permission"
  type        = string
  default     = "AllowExecutionFromEventBridgeBatch"
}

variable "eventbridge_dead_job_permission_statement_id" {
  description = "Statement ID for dead job detection EventBridge Lambda permission"
  type        = string
  default     = "AllowExecutionFromEventBridgeDeadJob"
}

# =============================================================================
# IAM CONFIGURATION
# =============================================================================


variable "iam_assume_role_action" {
  description = "Action for AssumeRole in IAM policies"
  type        = string
  default     = "sts:AssumeRole"
}

variable "iam_effect_allow" {
  description = "IAM policy effect value for Allow"
  type        = string
  default     = "Allow"
}

variable "lambda_service_principal" {
  description = "Service principal for Lambda functions"
  type        = string
  default     = "lambda.amazonaws.com"
}

variable "batch_service_principal" {
  description = "Service principal for AWS Batch service"
  type        = string
  default     = "batch.amazonaws.com"
}

variable "ec2_service_principal" {
  description = "Service principal for EC2 instances"
  type        = string
  default     = "ec2.amazonaws.com"
}

variable "ecs_tasks_service_principal" {
  description = "Service principal for ECS tasks"
  type        = string
  default     = "ecs-tasks.amazonaws.com"
}

variable "aws_batch_service_role_policy_arn" {
  description = "ARN for AWS Batch service role managed policy"
  type        = string
  default     = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

variable "ecs_container_service_role_policy_arn" {
  description = "ARN for ECS container service role managed policy"
  type        = string
  default     = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

variable "ecs_task_execution_role_policy_arn" {
  description = "ARN for ECS task execution role managed policy"
  type        = string
  default     = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

variable "iam_wildcard_resource" {
  description = "Wildcard resource ARN for IAM policies"
  type        = string
  default     = "*"
}

# =============================================================================
# LAMBDA FUNCTIONS CONFIGURATION
# =============================================================================
# Lambda functions power the serverless processing pipeline, handling file uploads,
# OCR processing for small files, API requests, and system maintenance tasks.
# These variables configure runtimes, timeouts, memory allocation, and logging.
#
# Function categories:
# - API Handlers: Process API Gateway requests (upload, search, edit, delete)
# - Short Batch Processor: OCR processing for files ≤300KB  
# - System Functions: Cleanup, monitoring, dead job detection
# - Integration Functions: SQS-to-Batch submission, status reconciliation
#
# Memory and timeout settings are optimized for each function's workload profile,
# balancing performance with cost efficiency. All functions use environment
# variables for configuration to support different deployment environments.

variable "lambda_runtime" {
  description = "Python runtime for Lambda functions"
  type        = string
  default     = "python3.12"
  validation {
    condition     = contains(["python3.10", "python3.11", "python3.12"], var.lambda_runtime)
    error_message = "Lambda runtime must be a supported Python version (3.10, 3.11, or 3.12)."
  }
}

variable "lambda_timeout_standard" {
  description = "Standard timeout for Lambda functions (60 seconds)"
  type        = number
  default     = 60
}

variable "lambda_timeout_short" {
  description = "Short timeout for API Gateway Lambda functions (30 seconds)"
  type        = number
  default     = 30
}

variable "lambda_timeout_long" {
  description = "Long timeout for processing Lambda functions (300 seconds)"
  type        = number
  default     = 300
}

variable "lambda_timeout_extended" {
  description = "Extended timeout for intensive processing (900 seconds)"
  type        = number
  default     = 900
}

variable "lambda_memory_small" {
  description = "Small memory size for Lambda functions (256 MB)"
  type        = number
  default     = 256
}

variable "lambda_memory_medium" {
  description = "Medium memory size for Lambda functions (512 MB)"
  type        = number
  default     = 512
}

variable "lambda_memory_large" {
  description = "Large memory size for Lambda functions (1024 MB)"
  type        = number
  default     = 1024
}

variable "archive_file_type" {
  description = "Archive file type for Lambda deployment packages"
  type        = string
  default     = "zip"
}


variable "lambda_log_level" {
  description = "Log level for Lambda functions"
  type        = string
  default     = "INFO"
}

variable "file_size_threshold_kb" {
  description = "File size threshold in KB for routing decisions"
  type        = string
  default     = "300"
}

variable "budget_limit_default" {
  description = "Default budget limit for OCR processing"
  type        = string
  default     = "10.0"
}

variable "max_processing_minutes" {
  description = "Maximum processing time in minutes before job is considered dead"
  type        = string
  default     = "120"
}


variable "cloudwatch_log_skip_destroy" {
  description = "Whether to skip destroy for CloudWatch log groups"
  type        = bool
  default     = false
}

variable "event_source_batch_size_large" {
  description = "Large batch size for event source mappings"
  type        = number
  default     = 10
}

variable "event_source_batch_size_single" {
  description = "Single message batch size for event source mappings"
  type        = number
  default     = 1
}

variable "event_source_batching_window_standard" {
  description = "Standard batching window in seconds for event source mappings"
  type        = number
  default     = 5
}

variable "event_source_batching_window_immediate" {
  description = "Immediate batching window (no delay) for event source mappings"
  type        = number
  default     = 0
}

variable "event_source_max_concurrency" {
  description = "Maximum concurrency for event source mappings"
  type        = number
  default     = 2
}

variable "event_source_response_types" {
  description = "Function response types for event source mappings"
  type        = list(string)
  default     = ["ReportBatchItemFailures"]
}

# =============================================================================
# S3 CONFIGURATION
# =============================================================================

variable "s3_prevent_destroy" {
  description = "Whether to prevent destruction of S3 bucket"
  type        = bool
  default     = false
}

variable "s3_sse_algorithm" {
  description = "Server-side encryption algorithm for S3 bucket"
  type        = string
  default     = "AES256"
}

variable "s3_block_public_acls" {
  description = "Whether to block public ACLs for S3 bucket"
  type        = bool
  default     = true
}

variable "s3_block_public_policy" {
  description = "Whether to block public policies for S3 bucket"
  type        = bool
  default     = true
}

variable "s3_ignore_public_acls" {
  description = "Whether to ignore public ACLs for S3 bucket"
  type        = bool
  default     = true
}

variable "s3_restrict_public_buckets" {
  description = "Whether to restrict public buckets for S3 bucket"
  type        = bool
  default     = true
}

variable "s3_cors_allowed_headers" {
  description = "Allowed headers for S3 CORS configuration"
  type        = list(string)
  default     = ["*"]
}

variable "s3_cors_allowed_methods" {
  description = "Allowed methods for S3 CORS configuration"
  type        = list(string)
  default     = ["GET", "PUT", "POST", "DELETE", "HEAD"]
}

variable "s3_cors_allowed_origins" {
  description = "Allowed origins for S3 CORS configuration"
  type        = list(string)
  default     = ["*"]
}

variable "s3_cors_expose_headers" {
  description = "Exposed headers for S3 CORS configuration"
  type        = list(string)
  default     = ["ETag"]
}

variable "s3_cors_max_age_seconds" {
  description = "Max age in seconds for S3 CORS configuration"
  type        = number
  default     = 3000
}

variable "s3_lifecycle_rule_status" {
  description = "Status for S3 lifecycle rules"
  type        = string
  default     = "Enabled"
}

variable "s3_short_batch_prefix" {
  description = "Prefix for short batch files in S3"
  type        = string
  default     = "short-batch-files/"
}

variable "s3_long_batch_prefix" {
  description = "Prefix for long batch files in S3"
  type        = string
  default     = "long-batch-files/"
}

variable "s3_transition_to_ia_days" {
  description = "Days until transition to Standard-IA storage class"
  type        = number
  default     = 30
}

variable "s3_transition_to_glacier_ir_days" {
  description = "Days until transition to Glacier Instant Retrieval storage class"
  type        = number
  default     = 365
}

variable "s3_transition_to_glacier_days" {
  description = "Days until transition to Glacier storage class"
  type        = number
  default     = 1095
}

variable "s3_transition_to_deep_archive_days" {
  description = "Days until transition to Deep Archive storage class"
  type        = number
  default     = 3650
}

variable "s3_storage_class_standard_ia" {
  description = "Standard-IA storage class name"
  type        = string
  default     = "STANDARD_IA"
}

variable "s3_storage_class_glacier_ir" {
  description = "Glacier Instant Retrieval storage class name"
  type        = string
  default     = "GLACIER_IR"
}

variable "s3_storage_class_glacier" {
  description = "Glacier storage class name"
  type        = string
  default     = "GLACIER"
}

variable "s3_storage_class_deep_archive" {
  description = "Deep Archive storage class name"
  type        = string
  default     = "DEEP_ARCHIVE"
}

# s3_eventbridge_enabled variable removed - EventBridge S3 notifications no longer used
# Long batch processing now uses direct SQS messaging from uploader Lambda

variable "s3_get_object_actions" {
  description = "S3 actions for getting objects"
  type        = list(string)
  default     = ["s3:GetObject"]
}

variable "s3_put_object_actions" {
  description = "S3 actions for putting objects"
  type        = list(string)
  default     = ["s3:PutObject", "s3:PutObjectAcl"]
}

variable "cloudfront_service_principal" {
  description = "Service principal for CloudFront"
  type        = string
  default     = "cloudfront.amazonaws.com"
}

variable "iam_principal_type_service" {
  description = "IAM principal type for service"
  type        = string
  default     = "Service"
}

variable "iam_principal_type_aws" {
  description = "IAM principal type for AWS"
  type        = string
  default     = "AWS"
}

variable "iam_condition_test_string_equals" {
  description = "IAM condition test for string equals"
  type        = string
  default     = "StringEquals"
}

variable "iam_condition_variable_source_arn" {
  description = "IAM condition variable for source ARN"
  type        = string
  default     = "AWS:SourceArn"
}

# =============================================================================
# SQS CONFIGURATION
# =============================================================================

variable "sqs_delay_seconds" {
  description = "Delay seconds for SQS queues"
  type        = number
  default     = 0
}

variable "sqs_max_message_size" {
  description = "Maximum message size for SQS queues in bytes"
  type        = number
  default     = 262144
}

variable "sqs_message_retention_long" {
  description = "Message retention period for long-term queues (14 days)"
  type        = number
  default     = 1209600
}

variable "sqs_message_retention_short" {
  description = "Message retention period for short-term queues (1 day)"
  type        = number
  default     = 86400
}

variable "sqs_receive_wait_time_short_polling" {
  description = "Receive wait time for short polling (immediate)"
  type        = number
  default     = 0
}

variable "sqs_receive_wait_time_long_polling" {
  description = "Receive wait time for long polling"
  type        = number
  default     = 20
}

variable "sqs_visibility_timeout_standard" {
  description = "Standard visibility timeout for SQS queues (5 minutes)"
  type        = number
  default     = 300
}

variable "sqs_visibility_timeout_batch" {
  description = "Visibility timeout for batch processing (16 minutes)"
  type        = number
  default     = 960
}

variable "sqs_visibility_timeout_short_batch" {
  description = "Visibility timeout for short batch processing (20 minutes)"
  type        = number
  default     = 1200
}

variable "sqs_visibility_timeout_invoice" {
  description = "Visibility timeout for invoice processing (30 minutes)"
  type        = number
  default     = 1800
}

variable "sqs_max_receive_count_standard" {
  description = "Max receive count before sending to DLQ (standard)"
  type        = number
  default     = 2
}

variable "sqs_max_receive_count_high" {
  description = "Max receive count before sending to DLQ (high reliability)"
  type        = number
  default     = 3
}

variable "cloudwatch_comparison_operator_greater_than" {
  description = "CloudWatch comparison operator for greater than threshold"
  type        = string
  default     = "GreaterThanThreshold"
}

variable "cloudwatch_evaluation_periods_single" {
  description = "Single evaluation period for CloudWatch alarms"
  type        = string
  default     = "1"
}

variable "cloudwatch_evaluation_periods_double" {
  description = "Double evaluation periods for CloudWatch alarms"
  type        = string
  default     = "2"
}

variable "cloudwatch_metric_messages_visible" {
  description = "CloudWatch metric name for approximate number of messages visible"
  type        = string
  default     = "ApproximateNumberOfMessagesVisible"
}

variable "cloudwatch_metric_message_age" {
  description = "CloudWatch metric name for approximate age of oldest message"
  type        = string
  default     = "ApproximateAgeOfOldestMessage"
}

variable "cloudwatch_namespace_sqs" {
  description = "CloudWatch namespace for SQS metrics"
  type        = string
  default     = "AWS/SQS"
}

variable "cloudwatch_period_standard" {
  description = "Standard period for CloudWatch metrics (5 minutes)"
  type        = string
  default     = "300"
}

variable "cloudwatch_statistic_average" {
  description = "Average statistic for CloudWatch metrics"
  type        = string
  default     = "Average"
}

variable "cloudwatch_statistic_maximum" {
  description = "Maximum statistic for CloudWatch metrics"
  type        = string
  default     = "Maximum"
}

variable "cloudwatch_threshold_zero" {
  description = "Zero threshold for CloudWatch alarms"
  type        = string
  default     = "0"
}

variable "cloudwatch_threshold_message_age_batch" {
  description = "Message age threshold for batch DLQ (1 hour)"
  type        = string
  default     = "3600"
}

variable "cloudwatch_threshold_message_age_short" {
  description = "Message age threshold for short batch DLQ (30 minutes)"
  type        = string
  default     = "1800"
}

variable "cloudwatch_threshold_high_count_batch" {
  description = "High message count threshold for batch DLQ"
  type        = string
  default     = "10"
}

variable "cloudwatch_threshold_high_count_short" {
  description = "High message count threshold for short batch and invoice DLQ"
  type        = string
  default     = "5"
}

variable "cloudwatch_treat_missing_data" {
  description = "How to treat missing data in CloudWatch alarms"
  type        = string
  default     = "notBreaching"
}

# =============================================================================
# VPC CONFIGURATION
# =============================================================================

variable "vpc_availability_zone_state" {
  description = "State filter for availability zones"
  type        = string
  default     = "available"
}

variable "vpc_enable_dns_hostnames" {
  description = "Enable DNS hostnames in VPC"
  type        = bool
  default     = true
}

variable "vpc_enable_dns_support" {
  description = "Enable DNS support in VPC"
  type        = bool
  default     = true
}

variable "vpc_map_public_ip_on_launch" {
  description = "Map public IP on launch for public subnets"
  type        = bool
  default     = true
}

variable "vpc_default_route_cidr" {
  description = "Default route CIDR block"
  type        = string
  default     = "0.0.0.0/0"
}

variable "vpc_https_port" {
  description = "HTTPS port for security groups"
  type        = number
  default     = 443
}

variable "vpc_all_ports_start" {
  description = "Start port for all traffic"
  type        = number
  default     = 0
}

variable "vpc_all_ports_end" {
  description = "End port for all traffic"
  type        = number
  default     = 0
}

variable "vpc_protocol_tcp" {
  description = "TCP protocol identifier"
  type        = string
  default     = "tcp"
}

variable "vpc_protocol_all" {
  description = "All protocols identifier"
  type        = string
  default     = "-1"
}

variable "vpc_endpoint_type_gateway" {
  description = "Gateway VPC endpoint type"
  type        = string
  default     = "Gateway"
}

variable "vpc_endpoint_type_interface" {
  description = "Interface VPC endpoint type"
  type        = string
  default     = "Interface"
}

variable "vpc_endpoint_private_dns_enabled" {
  description = "Enable private DNS for VPC endpoints"
  type        = bool
  default     = true
}

variable "vpc_lifecycle_create_before_destroy" {
  description = "Create before destroy lifecycle setting"
  type        = bool
  default     = true
}

variable "vpc_iam_principal_wildcard" {
  description = "Wildcard principal for IAM policies"
  type        = string
  default     = "*"
}

variable "vpc_iam_resource_wildcard" {
  description = "Wildcard resource for IAM policies"
  type        = string
  default     = "*"
}

# VPC Endpoint service actions
variable "vpc_s3_actions" {
  description = "S3 actions for VPC endpoint policies"
  type        = list(string)
  default = [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket",
    "s3:HeadObject"
  ]
}

variable "vpc_dynamodb_actions" {
  description = "DynamoDB actions for VPC endpoint policies"
  type        = list(string)
  default = [
    "dynamodb:Query",
    "dynamodb:UpdateItem",
    "dynamodb:PutItem",
    "dynamodb:GetItem",
    "dynamodb:Scan"
  ]
}

variable "vpc_ecr_actions" {
  description = "ECR actions for VPC endpoint policies"
  type        = list(string)
  default = [
    "ecr:GetAuthorizationToken",
    "ecr:BatchCheckLayerAvailability",
    "ecr:GetDownloadUrlForLayer",
    "ecr:BatchGetImage"
  ]
}

variable "vpc_ecr_api_actions" {
  description = "ECR API actions for VPC endpoint policies"
  type        = list(string)
  default = [
    "ecr:GetAuthorizationToken",
    "ecr:DescribeRepositories",
    "ecr:DescribeImages",
    "ecr:BatchCheckLayerAvailability",
    "ecr:GetDownloadUrlForLayer",
    "ecr:BatchGetImage"
  ]
}

variable "vpc_logs_actions" {
  description = "CloudWatch Logs actions for VPC endpoint policies"
  type        = list(string)
  default = [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "logs:DescribeLogGroups",
    "logs:DescribeLogStreams"
  ]
}

variable "vpc_ecs_actions" {
  description = "ECS actions for VPC endpoint policies"
  type        = list(string)
  default = [
    "ecs:CreateCluster",
    "ecs:DescribeClusters",
    "ecs:RegisterTaskDefinition",
    "ecs:RunTask",
    "ecs:StopTask",
    "ecs:DescribeTasks",
    "ecs:ListTasks"
  ]
}

variable "vpc_textract_actions" {
  description = "Textract actions for VPC endpoint policies"
  type        = list(string)
  default = [
    "textract:StartDocumentAnalysis",
    "textract:GetDocumentAnalysis",
    "textract:StartDocumentTextDetection",
    "textract:GetDocumentTextDetection"
  ]
}

variable "vpc_comprehend_actions" {
  description = "Comprehend actions for VPC endpoint policies"
  type        = list(string)
  default = [
    "comprehend:DetectDominantLanguage",
    "comprehend:DetectEntities",
    "comprehend:DetectKeyPhrases",
    "comprehend:DetectSentiment",
    "comprehend:DetectSyntax",
    "comprehend:DetectPiiEntities"
  ]
}