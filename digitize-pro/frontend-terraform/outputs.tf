
output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name for React application"
  value       = aws_cloudfront_distribution.s3_distribution.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation and management operations"
  value       = aws_cloudfront_distribution.s3_distribution.id
}

output "s3_bucket_name" {
  description = "S3 bucket name storing React build artifacts for deployment scripts"
  value       = aws_s3_bucket.storage_bucket.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN for IAM policy references and cross-service integration"
  value       = aws_s3_bucket.storage_bucket.arn
}

output "s3_bucket_regional_domain_name" {
  description = "S3 bucket regional domain name for direct API access (if needed)"
  value       = aws_s3_bucket.storage_bucket.bucket_regional_domain_name
}

output "website_url" {
  description = "Primary HTTPS URL for accessing the React application"
  value       = "https://${aws_cloudfront_distribution.s3_distribution.domain_name}"
}

output "origin_access_control_id" {
  description = "CloudFront Origin Access Control ID for S3 security configuration"
  value       = aws_cloudfront_origin_access_control.s3_oac.id
}

output "react_build_path" {
  description = "S3 path where React build artifacts should be uploaded"
  value       = "s3://${aws_s3_bucket.storage_bucket.id}${var.react_app_path}/"
}

output "deployment_commands" {
  description = "Useful commands for deploying and managing the React application"
  value = {
    upload_build     = "aws s3 sync ./build/ s3://${aws_s3_bucket.storage_bucket.id}${var.react_app_path}/ --delete"
    invalidate_cache = "aws cloudfront create-invalidation --distribution-id ${aws_cloudfront_distribution.s3_distribution.id} --paths '/*'"
    list_objects     = "aws s3 ls s3://${aws_s3_bucket.storage_bucket.id}${var.react_app_path}/ --recursive"
  }
}

output "infrastructure_info" {
  description = "Summary of deployed frontend infrastructure"
  value = {
    component       = "React Frontend Infrastructure"
    environment     = var.environment
    aws_region      = var.aws_region
    price_class     = var.cloudfront_price_class
    deployment_date = timestamp()
  }
}

