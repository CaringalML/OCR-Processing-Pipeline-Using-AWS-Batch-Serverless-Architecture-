# =============================================================================
# AWS COGNITO USER POOL CONFIGURATION
# =============================================================================
# This file configures AWS Cognito for user authentication and authorization.
# All users have equal access - no premium tiers or API key management.
# =============================================================================

# User Pool - Main authentication service
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-${var.environment}-user-pool"

  # Username configuration - use email as username
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  
  # Case sensitivity
  username_configuration {
    case_sensitive = false
  }

  # Password policy
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  # MFA configuration (optional for now, can be enabled later)
  mfa_configuration = "OFF"

  # Email verification configuration
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Your ${var.project_name} Verification Code"
    email_message        = "Your verification code is {####}"
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Email configuration (using Cognito default)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # User attributes schema
  schema {
    name                     = "email"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    required                 = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    name                     = "name"
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    required                 = false

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Deletion protection
  deletion_protection = var.environment == "prod" ? "ACTIVE" : "INACTIVE"

  # Lambda triggers
  lambda_config {
    pre_sign_up    = aws_lambda_function.cognito_pre_signup.arn
    post_confirmation = aws_lambda_function.cognito_post_confirmation.arn
    pre_authentication = aws_lambda_function.cognito_pre_authentication.arn
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-user-pool"
    Purpose = "User authentication for OCR processing system"
  })
}

# User Pool Client - For React frontend
resource "aws_cognito_user_pool_client" "web_client" {
  name         = "${var.project_name}-web-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # OAuth flows
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_CUSTOM_AUTH"
  ]

  # Token validity periods
  access_token_validity  = 1  # hours
  id_token_validity      = 1  # hours
  refresh_token_validity = 30 # days

  # Token units
  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # Read and write attributes - removed explicit lists to allow all defined attributes
  # This allows reading all attributes defined in the user pool schema

  # No client secret for public client (React app)
  generate_secret = false

  # Callback and logout URLs using frontend domain variable
  callback_urls = [var.frontend_domain]
  logout_urls = [var.frontend_domain]

  # Allowed OAuth flows and scopes (for future use)
  allowed_oauth_flows_user_pool_client = false
  supported_identity_providers         = ["COGNITO"]

  depends_on = [
    aws_cognito_user_pool.main
  ]
}

# User Pool Domain (for hosted UI - optional)
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${var.environment}-${random_string.cognito_domain_suffix.result}"
  user_pool_id = aws_cognito_user_pool.main.id
}

# Random string for unique domain
resource "random_string" "cognito_domain_suffix" {
  length  = 8
  special = false
  upper   = false
}

# API Gateway Authorizer
resource "aws_api_gateway_authorizer" "cognito" {
  name                   = "${var.project_name}-cognito-authorizer"
  type                   = "COGNITO_USER_POOLS"
  rest_api_id           = aws_api_gateway_rest_api.main.id
  provider_arns         = [aws_cognito_user_pool.main.arn]
  identity_source       = "method.request.header.Authorization"
  
  # Cache auth results for 5 minutes
  authorizer_result_ttl_in_seconds = 300
}

# Lambda permissions for Cognito triggers
resource "aws_lambda_permission" "cognito_pre_signup" {
  statement_id  = "AllowCognitoInvokePreSignup"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cognito_pre_signup.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}

resource "aws_lambda_permission" "cognito_post_confirmation" {
  statement_id  = "AllowCognitoInvokePostConfirmation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cognito_post_confirmation.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}

resource "aws_lambda_permission" "cognito_pre_authentication" {
  statement_id  = "AllowCognitoInvokePreAuthentication"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cognito_pre_authentication.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}

# Outputs for frontend configuration
output "cognito_user_pool_id" {
  value       = aws_cognito_user_pool.main.id
  description = "The ID of the Cognito User Pool"
}

output "cognito_client_id" {
  value       = aws_cognito_user_pool_client.web_client.id
  description = "The ID of the Cognito User Pool Client"
}

output "cognito_domain" {
  value       = aws_cognito_user_pool_domain.main.domain
  description = "The Cognito domain for hosted UI"
}

output "cognito_region" {
  value       = var.aws_region
  description = "The AWS region for Cognito"
}