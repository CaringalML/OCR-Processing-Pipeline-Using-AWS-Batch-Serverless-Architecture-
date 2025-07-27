# API Gateway REST API
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-${var.environment}-api"
  description = "API Gateway for file processing and management"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  binary_media_types = [
    "multipart/form-data",
    "image/*",
    "application/pdf",
    "application/zip",
    "application/octet-stream"
  ]

  tags = var.common_tags
}

# API Gateway Resource - Upload
resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "upload"
}

# API Gateway Resource - Processed
resource "aws_api_gateway_resource" "processed" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "processed"
}

# API Gateway Resource - Search
resource "aws_api_gateway_resource" "search" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "search"
}

# API Gateway Resource - Processed with fileId
resource "aws_api_gateway_resource" "processed_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.processed.id
  path_part   = "{fileId}"
}

# Upload endpoint - POST method
resource "aws_api_gateway_method" "upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "NONE"
  
  # API key is optional - users can use public plan or provide key for higher limits
  api_key_required = false
  
  # Request validation when rate limiting is enabled
  request_validator_id = var.enable_rate_limiting ? aws_api_gateway_request_validator.upload_validator[0].id : null
  
  request_parameters = var.enable_rate_limiting ? {
    "method.request.header.X-API-Key" = false  # Optional API key
  } : {}
}

# Upload endpoint - OPTIONS method (CORS)
resource "aws_api_gateway_method" "upload_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Processed endpoint - GET method
resource "aws_api_gateway_method" "processed_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.processed.id
  http_method   = "GET"
  authorization = "NONE"
  
  # API key is optional - users can use public plan or provide key for higher limits
  api_key_required = false
  
  # Request validation when rate limiting is enabled
  request_validator_id = var.enable_rate_limiting ? aws_api_gateway_request_validator.processed_validator[0].id : null
  
  request_parameters = var.enable_rate_limiting ? {
    "method.request.header.X-API-Key"         = false  # Optional API key
    "method.request.querystring.status"       = false  # Optional filter
    "method.request.querystring.fileId"       = false  # Optional filter
    "method.request.querystring.limit"        = false  # Optional pagination
  } : {}
}

# Processed endpoint - OPTIONS method (CORS)
resource "aws_api_gateway_method" "processed_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.processed.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Search endpoint - GET method
resource "aws_api_gateway_method" "search_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.search.id
  http_method   = "GET"
  authorization = "NONE"
  
  # API key is optional - users can use public plan or provide key for higher limits
  api_key_required = false
  
  # Request validation when rate limiting is enabled
  request_validator_id = var.enable_rate_limiting ? aws_api_gateway_request_validator.search_validator[0].id : null
  
  request_parameters = var.enable_rate_limiting ? {
    "method.request.header.X-API-Key"         = false  # Optional API key
    "method.request.querystring.q"            = false  # Search term
    "method.request.querystring.publication"  = false  # Publication filter
    "method.request.querystring.year"         = false  # Year filter
    "method.request.querystring.title"        = false  # Title filter
    "method.request.querystring.status"       = false  # Status filter
    "method.request.querystring.fileId"       = false  # Specific file ID
    "method.request.querystring.limit"        = false  # Pagination
  } : {}
}

# Search endpoint - OPTIONS method (CORS)
resource "aws_api_gateway_method" "search_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.search.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Edit endpoint - PATCH method
resource "aws_api_gateway_method" "processed_patch" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.processed_file_id.id
  http_method   = "PATCH"
  authorization = "NONE"
  
  # API key is optional
  api_key_required = false
  
  request_parameters = {
    "method.request.path.fileId" = true
  }
}

# Edit endpoint - OPTIONS method (CORS)
resource "aws_api_gateway_method" "processed_patch_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.processed_file_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Upload Integration with Lambda
resource "aws_api_gateway_integration" "upload_integration" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.uploader.invoke_arn
}

# Processed Integration with Lambda Reader
resource "aws_api_gateway_integration" "processed_integration" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed.id
  http_method = aws_api_gateway_method.processed_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.reader.invoke_arn
}

# Search Integration with Lambda Search
resource "aws_api_gateway_integration" "search_integration" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.search.id
  http_method = aws_api_gateway_method.search_get.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.search.invoke_arn
}

# CORS Integration for Upload OPTIONS
resource "aws_api_gateway_integration" "upload_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# CORS Integration for Processed OPTIONS
resource "aws_api_gateway_integration" "processed_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed.id
  http_method = aws_api_gateway_method.processed_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# CORS Integration for Search OPTIONS
resource "aws_api_gateway_integration" "search_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.search.id
  http_method = aws_api_gateway_method.search_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Edit Integration with Lambda Editor
resource "aws_api_gateway_integration" "processed_patch_integration" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed_file_id.id
  http_method = aws_api_gateway_method.processed_patch.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.editor.invoke_arn
}

# CORS Integration for Edit OPTIONS
resource "aws_api_gateway_integration" "processed_patch_options_integration" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed_file_id.id
  http_method = aws_api_gateway_method.processed_patch_options.http_method

  type = "MOCK"
  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Method Responses
resource "aws_api_gateway_method_response" "upload_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "processed_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed.id
  http_method = aws_api_gateway_method.processed_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

resource "aws_api_gateway_method_response" "search_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.search.id
  http_method = aws_api_gateway_method.search_get.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# Method Response for Edit endpoint
resource "aws_api_gateway_method_response" "processed_patch_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed_file_id.id
  http_method = aws_api_gateway_method.processed_patch.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# CORS Method Responses
resource "aws_api_gateway_method_response" "upload_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_method_response" "processed_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed.id
  http_method = aws_api_gateway_method.processed_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_method_response" "search_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.search.id
  http_method = aws_api_gateway_method.search_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_method_response" "processed_patch_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed_file_id.id
  http_method = aws_api_gateway_method.processed_patch_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Integration Responses
resource "aws_api_gateway_integration_response" "upload_response" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_post.http_method
  status_code = aws_api_gateway_method_response.upload_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_integration.upload_integration]
}

resource "aws_api_gateway_integration_response" "processed_response" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed.id
  http_method = aws_api_gateway_method.processed_get.http_method
  status_code = aws_api_gateway_method_response.processed_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_integration.processed_integration]
}

resource "aws_api_gateway_integration_response" "search_response" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.search.id
  http_method = aws_api_gateway_method.search_get.http_method
  status_code = aws_api_gateway_method_response.search_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_integration.search_integration]
}

# Integration Response for Edit endpoint
resource "aws_api_gateway_integration_response" "processed_patch_response" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed_file_id.id
  http_method = aws_api_gateway_method.processed_patch.http_method
  status_code = aws_api_gateway_method_response.processed_patch_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
  }

  depends_on = [aws_api_gateway_integration.processed_patch_integration]
}

# CORS Integration Responses
resource "aws_api_gateway_integration_response" "upload_options_response" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload.id
  http_method = aws_api_gateway_method.upload_options.http_method
  status_code = aws_api_gateway_method_response.upload_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-API-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.upload_options_integration]
}

resource "aws_api_gateway_integration_response" "processed_options_response" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed.id
  http_method = aws_api_gateway_method.processed_options.http_method
  status_code = aws_api_gateway_method_response.processed_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-API-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.processed_options_integration]
}

resource "aws_api_gateway_integration_response" "search_options_response" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.search.id
  http_method = aws_api_gateway_method.search_options.http_method
  status_code = aws_api_gateway_method_response.search_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-API-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.search_options_integration]
}

resource "aws_api_gateway_integration_response" "processed_patch_options_response" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.processed_file_id.id
  http_method = aws_api_gateway_method.processed_patch_options.http_method
  status_code = aws_api_gateway_method_response.processed_patch_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-API-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'PATCH,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.processed_patch_options_integration]
}

# Lambda Permissions for API Gateway
resource "aws_lambda_permission" "api_gateway_uploader" {
  statement_id  = "AllowExecutionFromAPIGatewayUploader"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.uploader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_reader" {
  statement_id  = "AllowExecutionFromAPIGatewayReader"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_search" {
  statement_id  = "AllowExecutionFromAPIGatewaySearch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.search.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_editor" {
  statement_id  = "AllowExecutionFromAPIGatewayEditor"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.editor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  # Force redeployment when endpoints are added/modified
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.upload.id,
      aws_api_gateway_resource.processed.id,
      aws_api_gateway_resource.search.id,
      aws_api_gateway_resource.processed_file_id.id,
      aws_api_gateway_method.upload_post.id,
      aws_api_gateway_method.processed_get.id,
      aws_api_gateway_method.search_get.id,
      aws_api_gateway_method.processed_patch.id,
      aws_api_gateway_integration.upload_integration.id,
      aws_api_gateway_integration.processed_integration.id,
      aws_api_gateway_integration.search_integration.id,
      aws_api_gateway_integration.processed_patch_integration.id,
    ]))
  }

  depends_on = [
    aws_api_gateway_method.upload_post,
    aws_api_gateway_method.upload_options,
    aws_api_gateway_method.processed_get,
    aws_api_gateway_method.processed_options,
    aws_api_gateway_method.search_get,
    aws_api_gateway_method.search_options,
    aws_api_gateway_method.processed_patch,
    aws_api_gateway_method.processed_patch_options,
    aws_api_gateway_integration.upload_integration,
    aws_api_gateway_integration.processed_integration,
    aws_api_gateway_integration.search_integration,
    aws_api_gateway_integration.processed_patch_integration,
    aws_api_gateway_integration.upload_options_integration,
    aws_api_gateway_integration.processed_options_integration,
    aws_api_gateway_integration.search_options_integration,
    aws_api_gateway_integration.processed_patch_options_integration
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage with Rate Limiting
resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  # Stage-level throttling settings (handled by method settings instead)

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_access_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      # Rate limiting metrics
      apiKeyId       = "$context.identity.apiKeyId"
      usageplan      = "$context.identity.userArn"
      error          = "$context.error.message"
      errorType      = "$context.error.messageString"
    })
  }

  tags = var.common_tags
}

# ========================================
# RATE LIMITING: USAGE PLANS
# ========================================

# Public Usage Plan (no API key required, basic limits)
resource "aws_api_gateway_usage_plan" "public" {
  count = var.enable_rate_limiting ? 1 : 0

  name        = "${var.project_name}-${var.environment}-public-plan"
  description = "Public usage plan with basic rate limits for anonymous users"

  api_stages {
    api_id = aws_api_gateway_rest_api.main.id
    stage  = aws_api_gateway_stage.main.stage_name

    # Method-specific throttling for public users
    dynamic "throttle" {
      for_each = var.upload_method_rate_limit > 0 ? [1] : []
      content {
        path        = "/upload/POST"
        rate_limit  = var.upload_method_rate_limit
        burst_limit = var.upload_method_burst_limit
      }
    }

    dynamic "throttle" {
      for_each = var.processed_method_rate_limit > 0 ? [1] : []
      content {
        path        = "/processed/GET"
        rate_limit  = var.processed_method_rate_limit
        burst_limit = var.processed_method_burst_limit
      }
    }
  }

  quota_settings {
    limit  = var.public_quota_limit
    period = "DAY"
  }

  throttle_settings {
    rate_limit  = var.public_rate_limit
    burst_limit = var.public_burst_limit
  }

  tags = merge(var.common_tags, {
    PlanType = "Public"
    ApiKeyRequired = "false"
  })
}

# Registered User Usage Plan (requires API key)
resource "aws_api_gateway_usage_plan" "registered" {
  count = var.enable_rate_limiting ? 1 : 0

  name        = "${var.project_name}-${var.environment}-registered-plan"
  description = "Registered user usage plan with moderate rate limits"

  api_stages {
    api_id = aws_api_gateway_rest_api.main.id
    stage  = aws_api_gateway_stage.main.stage_name

    # Higher limits for registered users
    dynamic "throttle" {
      for_each = var.upload_method_rate_limit > 0 ? [1] : []
      content {
        path        = "/upload/POST"
        rate_limit  = min(var.upload_method_rate_limit * 5, var.registered_rate_limit)
        burst_limit = min(var.upload_method_burst_limit * 5, var.registered_burst_limit)
      }
    }

    dynamic "throttle" {
      for_each = var.processed_method_rate_limit > 0 ? [1] : []
      content {
        path        = "/processed/GET"
        rate_limit  = min(var.processed_method_rate_limit * 3, var.registered_rate_limit)
        burst_limit = min(var.processed_method_burst_limit * 3, var.registered_burst_limit)
      }
    }
  }

  quota_settings {
    limit  = var.registered_quota_limit
    period = "DAY"
  }

  throttle_settings {
    rate_limit  = var.registered_rate_limit
    burst_limit = var.registered_burst_limit
  }

  tags = merge(var.common_tags, {
    PlanType = "Registered"
    ApiKeyRequired = "true"
  })
}

# Premium Usage Plan (highest limits)
resource "aws_api_gateway_usage_plan" "premium" {
  count = var.enable_rate_limiting ? 1 : 0

  name        = "${var.project_name}-${var.environment}-premium-plan"
  description = "Premium usage plan with high rate limits for premium users"

  api_stages {
    api_id = aws_api_gateway_rest_api.main.id
    stage  = aws_api_gateway_stage.main.stage_name

    # Premium limits - much higher
    dynamic "throttle" {
      for_each = var.upload_method_rate_limit > 0 ? [1] : []
      content {
        path        = "/upload/POST"
        rate_limit  = min(var.upload_method_rate_limit * 10, var.premium_rate_limit)
        burst_limit = min(var.upload_method_burst_limit * 10, var.premium_burst_limit)
      }
    }

    dynamic "throttle" {
      for_each = var.processed_method_rate_limit > 0 ? [1] : []
      content {
        path        = "/processed/GET"
        rate_limit  = min(var.processed_method_rate_limit * 5, var.premium_rate_limit)
        burst_limit = min(var.processed_method_burst_limit * 5, var.premium_burst_limit)
      }
    }
  }

  quota_settings {
    limit  = var.premium_quota_limit
    period = "DAY"
  }

  throttle_settings {
    rate_limit  = var.premium_rate_limit
    burst_limit = var.premium_burst_limit
  }

  tags = merge(var.common_tags, {
    PlanType = "Premium"
    ApiKeyRequired = "true"
  })
}

# ========================================
# RATE LIMITING: API KEYS
# ========================================

# Create demo API keys for testing
resource "aws_api_gateway_api_key" "demo_keys" {
  count = var.enable_rate_limiting && var.create_default_api_keys ? length(var.api_key_names) : 0

  name        = "${var.project_name}-${var.environment}-${var.api_key_names[count.index]}"
  description = "Demo API key for ${var.api_key_names[count.index]}"
  enabled     = true

  tags = merge(var.common_tags, {
    KeyType = strcontains(var.api_key_names[count.index], "premium") ? "Premium" : "Registered"
    Purpose = "Demo"
  })
}

# Associate registered user API keys with registered plan
resource "aws_api_gateway_usage_plan_key" "registered_keys" {
  count = var.enable_rate_limiting && var.create_default_api_keys ? 1 : 0

  key_id        = aws_api_gateway_api_key.demo_keys[0].id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.registered[0].id
}

# Associate premium API keys with premium plan
resource "aws_api_gateway_usage_plan_key" "premium_keys" {
  count = var.enable_rate_limiting && var.create_default_api_keys && length(var.api_key_names) > 1 ? 1 : 0

  key_id        = aws_api_gateway_api_key.demo_keys[1].id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.premium[0].id
}

# ========================================
# RATE LIMITING: METHOD SETTINGS
# ========================================

# Method settings for upload endpoint
resource "aws_api_gateway_method_settings" "upload_settings" {
  count = var.enable_rate_limiting ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "${aws_api_gateway_resource.upload.path_part}/${aws_api_gateway_method.upload_post.http_method}"

  settings {
    # Enable detailed CloudWatch metrics
    metrics_enabled = true
    logging_level   = "INFO"
    
    # Cache settings (disabled for upload to ensure real-time processing)
    caching_enabled      = false
    cache_ttl_in_seconds = 0
    
    # Method-specific throttling (if specified)
    throttling_rate_limit  = var.upload_method_rate_limit > 0 ? var.upload_method_rate_limit : var.api_throttling_rate_limit
    throttling_burst_limit = var.upload_method_burst_limit > 0 ? var.upload_method_burst_limit : var.api_throttling_burst_limit
    
    # Data trace settings for debugging
    data_trace_enabled = var.environment != "production"
  }
}

# Method settings for processed endpoint
resource "aws_api_gateway_method_settings" "processed_settings" {
  count = var.enable_rate_limiting ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "${aws_api_gateway_resource.processed.path_part}/${aws_api_gateway_method.processed_get.http_method}"

  settings {
    # Enable detailed CloudWatch metrics
    metrics_enabled = true
    logging_level   = "INFO"
    
    # Cache settings (enable short caching for read operations)
    caching_enabled      = true
    cache_ttl_in_seconds = 60  # 1 minute cache
    
    # Method-specific throttling
    throttling_rate_limit  = var.processed_method_rate_limit > 0 ? var.processed_method_rate_limit : var.api_throttling_rate_limit
    throttling_burst_limit = var.processed_method_burst_limit > 0 ? var.processed_method_burst_limit : var.api_throttling_burst_limit
    
    # Data trace settings
    data_trace_enabled = var.environment != "production"
  }
}

# Method settings for search endpoint
resource "aws_api_gateway_method_settings" "search_settings" {
  count = var.enable_rate_limiting ? 1 : 0

  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "${aws_api_gateway_resource.search.path_part}/${aws_api_gateway_method.search_get.http_method}"

  settings {
    # Enable detailed CloudWatch metrics
    metrics_enabled = true
    logging_level   = "INFO"
    
    # Cache settings (enable short caching for search results)
    caching_enabled      = true
    cache_ttl_in_seconds = 300  # 5 minute cache for search results
    
    # Method-specific throttling
    throttling_rate_limit  = var.processed_method_rate_limit > 0 ? var.processed_method_rate_limit : var.api_throttling_rate_limit
    throttling_burst_limit = var.processed_method_burst_limit > 0 ? var.processed_method_burst_limit : var.api_throttling_burst_limit
    
    # Data trace settings
    data_trace_enabled = var.environment != "production"
  }
}

# ========================================
# RATE LIMITING: REQUEST VALIDATORS
# ========================================

# Request validator to prevent malformed requests from consuming quota
resource "aws_api_gateway_request_validator" "upload_validator" {
  count = var.enable_rate_limiting ? 1 : 0

  name                        = "${var.project_name}-${var.environment}-upload-validator"
  rest_api_id                 = aws_api_gateway_rest_api.main.id
  validate_request_body       = true
  validate_request_parameters = true
}

resource "aws_api_gateway_request_validator" "processed_validator" {
  count = var.enable_rate_limiting ? 1 : 0

  name                        = "${var.project_name}-${var.environment}-processed-validator"
  rest_api_id                 = aws_api_gateway_rest_api.main.id
  validate_request_body       = false
  validate_request_parameters = true
}

resource "aws_api_gateway_request_validator" "search_validator" {
  count = var.enable_rate_limiting ? 1 : 0

  name                        = "${var.project_name}-${var.environment}-search-validator"
  rest_api_id                 = aws_api_gateway_rest_api.main.id
  validate_request_body       = false
  validate_request_parameters = true
}