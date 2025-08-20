# ========================================
# UNIFIED API GATEWAY WITH ENVIRONMENT STAGES
# ========================================

# Main API Gateway REST API
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-api"
  description = "Unified API Gateway for file processing with environment stages"

  endpoint_configuration {
    types = var.api_gateway_endpoint_types
  }

  binary_media_types = var.api_gateway_binary_media_types

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-api"
    Purpose = "Unified file processing API"
  })
}

# ========================================
# LONG-BATCH RESOURCES
# ========================================

# Long Batch Resource
resource "aws_api_gateway_resource" "long_batch" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = var.api_path_long_batch
}

# Long Batch - Upload
resource "aws_api_gateway_resource" "long_batch_upload" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.long_batch.id
  path_part   = var.api_path_upload
}

# Long Batch - Processed
resource "aws_api_gateway_resource" "long_batch_processed" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.long_batch.id
  path_part   = var.api_path_processed
}


# Long Batch - Delete
resource "aws_api_gateway_resource" "long_batch_delete" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.long_batch.id
  path_part   = var.api_path_delete
}

# Long Batch - Delete with fileId
resource "aws_api_gateway_resource" "long_batch_delete_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.long_batch_delete.id
  path_part   = "{fileId}"
}

# Long Batch - Recycle Bin
resource "aws_api_gateway_resource" "long_batch_recycle_bin" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.long_batch.id
  path_part   = var.api_path_recycle_bin
}

# Long Batch - Restore
resource "aws_api_gateway_resource" "long_batch_restore" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.long_batch.id
  path_part   = var.api_path_restore
}

# ========================================
# NEUTRAL/SHARED RESOURCES (ROOT LEVEL)
# ========================================

# Upload Resource (smart routing)
# Upload resource moved to /batch/upload for consistency
# See batch_upload resource below

# Smart route endpoint removed - routing now integrated into /upload endpoint

# Batch Resource
resource "aws_api_gateway_resource" "batch" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "batch"
}

# Batch Upload Resource (unified upload endpoint)
resource "aws_api_gateway_resource" "batch_upload" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch.id
  path_part   = var.api_path_upload
}

# Batch Processed Resource (view processed files)
resource "aws_api_gateway_resource" "batch_processed" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch.id
  path_part   = var.api_path_processed
}


# Batch Processed Finalize Resource (finalize processed files)
resource "aws_api_gateway_resource" "batch_processed_finalize" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch_processed.id
  path_part   = "finalize"
}

# Batch Processed Finalize with fileId
resource "aws_api_gateway_resource" "batch_processed_finalize_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch_processed_finalize.id
  path_part   = "{fileId}"
}


# Batch Delete Resource (file management under /batch/)
resource "aws_api_gateway_resource" "batch_delete" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch.id
  path_part   = var.api_path_delete
}

# Batch Delete with fileId
resource "aws_api_gateway_resource" "batch_delete_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch_delete.id
  path_part   = "{fileId}"
}

# Batch Recycle Bin Resource (recycle bin management under /batch/)
resource "aws_api_gateway_resource" "batch_recycle_bin" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch.id
  path_part   = var.api_path_recycle_bin
}

# Batch Restore Resource (restore from recycle bin under /batch/)
resource "aws_api_gateway_resource" "batch_restore" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch.id
  path_part   = var.api_path_restore
}

# Batch Restore with fileId
resource "aws_api_gateway_resource" "batch_restore_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch_restore.id
  path_part   = "{fileId}"
}

# Batch Search Resource (unified search under /batch/)
resource "aws_api_gateway_resource" "batch_search" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.batch.id
  path_part   = var.api_path_search
}

# Finalized Documents Edit Resource (edit finalized documents under /finalized/)
resource "aws_api_gateway_resource" "finalized" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "finalized"
}

# Finalized Edit Resource
resource "aws_api_gateway_resource" "finalized_edit" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.finalized.id
  path_part   = "edit"
}

# Finalized Edit with fileId
resource "aws_api_gateway_resource" "finalized_edit_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.finalized_edit.id
  path_part   = "{fileId}"
}

# Smart route methods and integrations removed - routing now integrated into /upload endpoint

# ========================================
# NEUTRAL ENDPOINT METHODS & INTEGRATIONS
# ========================================

# Batch Upload POST Method (smart routing)
resource "aws_api_gateway_method" "batch_upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.batch_upload.id
  http_method   = "POST"
  authorization = "NONE"
}

# Batch Upload POST Integration (to uploader Lambda)
resource "aws_api_gateway_integration" "batch_upload_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_upload.id
  http_method = aws_api_gateway_method.batch_upload_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.uploader.invoke_arn
}

# Lambda Permission for Batch Upload
resource "aws_lambda_permission" "batch_upload_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayBatchUpload"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.uploader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/POST/batch/upload"
}

# Batch Processed GET Method (view processed files)
resource "aws_api_gateway_method" "batch_processed_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.batch_processed.id
  http_method   = "GET"
  authorization = "NONE"
}

# Batch Processed GET Integration (to reader Lambda)
resource "aws_api_gateway_integration" "batch_processed_get" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_processed.id
  http_method = aws_api_gateway_method.batch_processed_get.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.reader.invoke_arn
}


# Lambda Permission for Batch Processed GET
resource "aws_lambda_permission" "batch_processed_get_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayBatchGet"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/GET/batch/processed"
}


# Batch Processed Finalize POST Method (finalize processed files)
resource "aws_api_gateway_method" "batch_processed_finalize_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.batch_processed_finalize_file_id.id
  http_method   = "POST"
  authorization = "NONE"
}

# Batch Processed Finalize POST Integration (to finalizer Lambda)
resource "aws_api_gateway_integration" "batch_processed_finalize_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_processed_finalize_file_id.id
  http_method = aws_api_gateway_method.batch_processed_finalize_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.finalizer.invoke_arn
}

# Lambda Permission for Batch Processed Finalize POST
resource "aws_lambda_permission" "batch_processed_finalize_post_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayBatchFinalizePost"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finalizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/POST/batch/processed/finalize/{fileId}"
}

# Batch Processed Finalize OPTIONS Method (for CORS)
resource "aws_api_gateway_method" "batch_processed_finalize_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.batch_processed_finalize_file_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Batch Processed Finalize OPTIONS Integration (for CORS)
resource "aws_api_gateway_integration" "batch_processed_finalize_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_processed_finalize_file_id.id
  http_method = aws_api_gateway_method.batch_processed_finalize_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = var.mock_response_template
  }
}

# Batch Processed Finalize OPTIONS Method Response
resource "aws_api_gateway_method_response" "batch_processed_finalize_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_processed_finalize_file_id.id
  http_method = aws_api_gateway_method.batch_processed_finalize_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Batch Processed Finalize OPTIONS Integration Response
resource "aws_api_gateway_integration_response" "batch_processed_finalize_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_processed_finalize_file_id.id
  http_method = aws_api_gateway_method.batch_processed_finalize_options.http_method
  status_code = aws_api_gateway_method_response.batch_processed_finalize_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = var.cors_allowed_headers
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = var.cors_allowed_origin
  }
}


# Batch Delete Method (delete file)
resource "aws_api_gateway_method" "batch_delete_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.batch_delete_file_id.id
  http_method   = "DELETE"
  authorization = "NONE"
}

# Batch Delete Integration (to deleter Lambda)
resource "aws_api_gateway_integration" "batch_delete_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_delete_file_id.id
  http_method = aws_api_gateway_method.batch_delete_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.deleter.invoke_arn
}

# Lambda Permission for Batch Delete
resource "aws_lambda_permission" "batch_delete_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayBatchDelete"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.deleter.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/DELETE/batch/delete/*"
}

# Batch Recycle Bin GET Method (view recycle bin)
resource "aws_api_gateway_method" "batch_recycle_bin_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.batch_recycle_bin.id
  http_method   = "GET"
  authorization = "NONE"
}

# Batch Recycle Bin GET Integration (to recycle bin reader Lambda)
resource "aws_api_gateway_integration" "batch_recycle_bin_get" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_recycle_bin.id
  http_method = aws_api_gateway_method.batch_recycle_bin_get.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.recycle_bin_reader.invoke_arn
}

# Lambda Permission for Batch Recycle Bin
resource "aws_lambda_permission" "batch_recycle_bin_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayBatchRecycleBin"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recycle_bin_reader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/GET/batch/recycle-bin"
}

# Batch Restore POST Method (restore from recycle bin)
resource "aws_api_gateway_method" "batch_restore_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.batch_restore_file_id.id
  http_method   = "POST"
  authorization = "NONE"
}

# Batch Restore POST Integration (to restorer Lambda)
resource "aws_api_gateway_integration" "batch_restore_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_restore_file_id.id
  http_method = aws_api_gateway_method.batch_restore_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.restorer.invoke_arn
}

# Lambda Permission for Batch Restore
resource "aws_lambda_permission" "batch_restore_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayBatchRestore"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.restorer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/POST/batch/restore/*"
}

# Batch Search GET Method (unified search)
resource "aws_api_gateway_method" "batch_search_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.batch_search.id
  http_method   = "GET"
  authorization = "NONE"
}

# Batch Search GET Integration (to search Lambda)
resource "aws_api_gateway_integration" "batch_search_get" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.batch_search.id
  http_method = aws_api_gateway_method.batch_search_get.http_method
  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.search.invoke_arn
}

# Lambda Permission for Batch Search
resource "aws_lambda_permission" "batch_search_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayBatchSearch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.search.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/GET/batch/search"
}

# Finalized Edit PUT Method (edit finalized documents)
resource "aws_api_gateway_method" "finalized_edit_put" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.finalized_edit_file_id.id
  http_method   = "PUT"
  authorization = "NONE"
}

# Finalized Edit PUT Integration (to finalized_editor Lambda)
resource "aws_api_gateway_integration" "finalized_edit_put" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.finalized_edit_file_id.id
  http_method = aws_api_gateway_method.finalized_edit_put.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.finalized_editor.invoke_arn
}

# Lambda Permission for Finalized Edit PUT
resource "aws_lambda_permission" "finalized_edit_put_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayFinalizedEditPut"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finalized_editor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/PUT/finalized/edit/{fileId}"
}

# Long Batch - Restore with fileId
resource "aws_api_gateway_resource" "long_batch_restore_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.long_batch_restore.id
  path_part   = "{fileId}"
}

# ========================================
# SHORT-BATCH RESOURCES
# ========================================

# Short Batch Resource
resource "aws_api_gateway_resource" "short_batch" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = var.api_path_short_batch
}

# Short Batch - Upload
resource "aws_api_gateway_resource" "short_batch_upload" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch.id
  path_part   = var.api_path_upload
}

# Short Batch - Processed
resource "aws_api_gateway_resource" "short_batch_processed" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch.id
  path_part   = var.api_path_processed
}


# Short Batch - Delete
resource "aws_api_gateway_resource" "short_batch_delete" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch.id
  path_part   = var.api_path_delete
}

# Short Batch - Delete with fileId
resource "aws_api_gateway_resource" "short_batch_delete_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch_delete.id
  path_part   = "{fileId}"
}

# Short Batch - Recycle Bin
resource "aws_api_gateway_resource" "short_batch_recycle_bin" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch.id
  path_part   = var.api_path_recycle_bin
}

# Short Batch - Restore
resource "aws_api_gateway_resource" "short_batch_restore" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch.id
  path_part   = var.api_path_restore
}

# Short Batch - Restore with fileId
resource "aws_api_gateway_resource" "short_batch_restore_file_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch_restore.id
  path_part   = "{fileId}"
}

# ========================================
# INVOICE PROCESSING RESOURCES
# ========================================

# Short Batch - Invoices
resource "aws_api_gateway_resource" "short_batch_invoices" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch.id
  path_part   = var.api_path_invoices
}

# Short Batch - Invoices - Upload
resource "aws_api_gateway_resource" "short_batch_invoices_upload" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch_invoices.id
  path_part   = var.api_path_upload
}

# Short Batch Invoices - Processed
resource "aws_api_gateway_resource" "short_batch_invoices_processed" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.short_batch_invoices.id
  path_part   = var.api_path_processed
}

# ========================================
# LONG BATCH METHODS
# ========================================

# Long Batch Upload POST Method
resource "aws_api_gateway_method" "long_batch_upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.long_batch_upload.id
  http_method   = "POST"
  authorization = "NONE"
}

# Long Batch Upload POST Integration (now uses unified uploader)
resource "aws_api_gateway_integration" "long_batch_upload_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.long_batch_upload.id
  http_method = aws_api_gateway_method.long_batch_upload_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.uploader.invoke_arn
}


# Long Batch Delete Method
resource "aws_api_gateway_method" "long_batch_delete_delete" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.long_batch_delete_file_id.id
  http_method   = "DELETE"
  authorization = "NONE"
}

# Long Batch Delete Integration
resource "aws_api_gateway_integration" "long_batch_delete_delete" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.long_batch_delete_file_id.id
  http_method = aws_api_gateway_method.long_batch_delete_delete.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.deleter.invoke_arn
}

# Long Batch Recycle Bin GET Method
resource "aws_api_gateway_method" "long_batch_recycle_bin_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.long_batch_recycle_bin.id
  http_method   = "GET"
  authorization = "NONE"
}

# Long Batch Recycle Bin GET Integration
resource "aws_api_gateway_integration" "long_batch_recycle_bin_get" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.long_batch_recycle_bin.id
  http_method = aws_api_gateway_method.long_batch_recycle_bin_get.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.recycle_bin_reader.invoke_arn
}

# Long Batch Restore POST Method
resource "aws_api_gateway_method" "long_batch_restore_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.long_batch_restore_file_id.id
  http_method   = "POST"
  authorization = "NONE"
}

# Long Batch Restore POST Integration
resource "aws_api_gateway_integration" "long_batch_restore_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.long_batch_restore_file_id.id
  http_method = aws_api_gateway_method.long_batch_restore_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.restorer.invoke_arn
}

# ========================================
# SHORT BATCH METHODS
# ========================================

# Short Batch Upload POST Method
resource "aws_api_gateway_method" "short_batch_upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.short_batch_upload.id
  http_method   = "POST"
  authorization = "NONE"
}

# Short Batch Upload POST Integration (now uses unified uploader)
resource "aws_api_gateway_integration" "short_batch_upload_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_upload.id
  http_method = aws_api_gateway_method.short_batch_upload_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.uploader.invoke_arn
}


# Short Batch Delete Method
resource "aws_api_gateway_method" "short_batch_delete_delete" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.short_batch_delete_file_id.id
  http_method   = "DELETE"
  authorization = "NONE"
}

# Short Batch Delete Integration
resource "aws_api_gateway_integration" "short_batch_delete_delete" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_delete_file_id.id
  http_method = aws_api_gateway_method.short_batch_delete_delete.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.deleter.invoke_arn
}

# Short Batch Recycle Bin GET Method
resource "aws_api_gateway_method" "short_batch_recycle_bin_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.short_batch_recycle_bin.id
  http_method   = "GET"
  authorization = "NONE"
}

# Short Batch Recycle Bin GET Integration
resource "aws_api_gateway_integration" "short_batch_recycle_bin_get" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_recycle_bin.id
  http_method = aws_api_gateway_method.short_batch_recycle_bin_get.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.recycle_bin_reader.invoke_arn
}

# Short Batch Restore POST Method
resource "aws_api_gateway_method" "short_batch_restore_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.short_batch_restore_file_id.id
  http_method   = "POST"
  authorization = "NONE"
}

# Short Batch Restore POST Integration
resource "aws_api_gateway_integration" "short_batch_restore_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_restore_file_id.id
  http_method = aws_api_gateway_method.short_batch_restore_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.restorer.invoke_arn
}

# ========================================
# INVOICE PROCESSING METHODS
# ========================================

# Invoice Upload POST Method
resource "aws_api_gateway_method" "invoice_upload_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.short_batch_invoices_upload.id
  http_method   = "POST"
  authorization = "NONE"
}

# Invoice Upload POST Integration
resource "aws_api_gateway_integration" "invoice_upload_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_invoices_upload.id
  http_method = aws_api_gateway_method.invoice_upload_post.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.invoice_uploader.invoke_arn
}

# Invoice Upload OPTIONS Method (for CORS)
resource "aws_api_gateway_method" "invoice_upload_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.short_batch_invoices_upload.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Invoice Upload OPTIONS Integration (for CORS)
resource "aws_api_gateway_integration" "invoice_upload_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_invoices_upload.id
  http_method = aws_api_gateway_method.invoice_upload_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = var.mock_response_template
  }
}

# Invoice Upload OPTIONS Method Response
resource "aws_api_gateway_method_response" "invoice_upload_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_invoices_upload.id
  http_method = aws_api_gateway_method.invoice_upload_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Invoice Upload OPTIONS Integration Response
resource "aws_api_gateway_integration_response" "invoice_upload_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_invoices_upload.id
  http_method = aws_api_gateway_method.invoice_upload_options.http_method
  status_code = aws_api_gateway_method_response.invoice_upload_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = var.cors_allowed_headers
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = var.cors_allowed_origin
  }
}

# Invoice Processed GET Method
resource "aws_api_gateway_method" "invoice_processed_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.short_batch_invoices_processed.id
  http_method   = "GET"
  authorization = "NONE"
}

# Invoice Processed GET Integration
resource "aws_api_gateway_integration" "invoice_processed_get" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_invoices_processed.id
  http_method = aws_api_gateway_method.invoice_processed_get.http_method

  integration_http_method = var.api_integration_http_method
  type                    = var.api_integration_type
  uri                     = aws_lambda_function.invoice_reader.invoke_arn
}

# Invoice Processed OPTIONS Method (for CORS)
resource "aws_api_gateway_method" "invoice_processed_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.short_batch_invoices_processed.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Invoice Processed OPTIONS Integration (for CORS)
resource "aws_api_gateway_integration" "invoice_processed_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_invoices_processed.id
  http_method = aws_api_gateway_method.invoice_processed_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = var.mock_response_template
  }
}

# Invoice Processed OPTIONS Method Response
resource "aws_api_gateway_method_response" "invoice_processed_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_invoices_processed.id
  http_method = aws_api_gateway_method.invoice_processed_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

# Invoice Processed OPTIONS Integration Response
resource "aws_api_gateway_integration_response" "invoice_processed_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.short_batch_invoices_processed.id
  http_method = aws_api_gateway_method.invoice_processed_options.http_method
  status_code = aws_api_gateway_method_response.invoice_processed_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = var.cors_allowed_headers
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = var.cors_allowed_origin
  }
}


# ========================================
# DEPLOYMENT AND STAGE
# ========================================

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  depends_on = [
    # Unified Batch Dependencies
    aws_api_gateway_integration.batch_upload_post,
    aws_api_gateway_integration.batch_processed_get,
    aws_api_gateway_integration.batch_processed_finalize_post,
    aws_api_gateway_integration.batch_processed_finalize_options,
    # New Unified Batch File Management
    aws_api_gateway_integration.batch_delete_post,
    aws_api_gateway_integration.batch_recycle_bin_get,
    aws_api_gateway_integration.batch_restore_post,
    aws_api_gateway_integration.batch_search_get,
    aws_api_gateway_integration.finalized_edit_put,
    # Long Batch Dependencies
    aws_api_gateway_integration.long_batch_upload_post,
    aws_api_gateway_integration.long_batch_delete_delete,
    aws_api_gateway_integration.long_batch_recycle_bin_get,
    aws_api_gateway_integration.long_batch_restore_post,
    # Short Batch Dependencies
    aws_api_gateway_integration.short_batch_upload_post,
    aws_api_gateway_integration.short_batch_delete_delete,
    aws_api_gateway_integration.short_batch_recycle_bin_get,
    aws_api_gateway_integration.short_batch_restore_post,
    # Invoice Processing Dependencies
    aws_api_gateway_integration.invoice_upload_post,
    aws_api_gateway_integration.invoice_processed_get,
  ]

  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.batch.id,
      aws_api_gateway_resource.batch_upload.id,
      aws_api_gateway_resource.batch_processed.id,
      aws_api_gateway_resource.batch_processed_finalize.id,
      aws_api_gateway_resource.batch_processed_finalize_file_id.id,
      aws_api_gateway_resource.batch_search.id,
      aws_api_gateway_resource.finalized.id,
      aws_api_gateway_resource.finalized_edit.id,
      aws_api_gateway_resource.finalized_edit_file_id.id,
      aws_api_gateway_integration.batch_upload_post.id,
      aws_api_gateway_integration.batch_processed_get.id,
      aws_api_gateway_integration.batch_processed_finalize_post.id,
      aws_api_gateway_integration.batch_processed_finalize_options.id,
      aws_api_gateway_integration.batch_search_get.id,
      aws_api_gateway_integration.finalized_edit_put.id,
      aws_api_gateway_resource.long_batch.id,
      aws_api_gateway_resource.short_batch.id,
      aws_api_gateway_resource.long_batch_upload.id,
      aws_api_gateway_resource.short_batch_upload.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage (using api_stage_name for URL structure)
resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.api_stage_name

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.api_stage_name}-stage"
  })
}

# ========================================
# LAMBDA PERMISSIONS
# ========================================

# Lambda permissions for API Gateway (now using unified uploader)
resource "aws_lambda_permission" "uploader_long_batch_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayLongBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.uploader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/POST/long-batch/upload"
}

resource "aws_lambda_permission" "uploader_short_batch_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayShortBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.uploader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/POST/short-batch/upload"
}

resource "aws_lambda_permission" "invoice_uploader_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayInvoice"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.invoice_uploader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/POST/short-batch/invoices/upload"
}

resource "aws_lambda_permission" "invoice_reader_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGatewayInvoiceReader"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.invoice_reader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/GET/short-batch/invoices/processed"
}


resource "aws_lambda_permission" "deleter_long_batch" {
  statement_id  = "AllowExecutionFromAPIGatewayLongBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.deleter.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/DELETE/long-batch/delete/*"
}

resource "aws_lambda_permission" "deleter_short_batch" {
  statement_id  = "AllowExecutionFromAPIGatewayShortBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.deleter.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/DELETE/short-batch/delete/*"
}

resource "aws_lambda_permission" "recycle_bin_reader_long_batch" {
  statement_id  = "AllowExecutionFromAPIGatewayLongBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recycle_bin_reader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/GET/long-batch/recycle-bin"
}

resource "aws_lambda_permission" "recycle_bin_reader_short_batch" {
  statement_id  = "AllowExecutionFromAPIGatewayShortBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recycle_bin_reader.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/GET/short-batch/recycle-bin"
}

resource "aws_lambda_permission" "restorer_long_batch" {
  statement_id  = "AllowExecutionFromAPIGatewayLongBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.restorer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/POST/long-batch/restore/*"
}

resource "aws_lambda_permission" "restorer_short_batch" {
  statement_id  = "AllowExecutionFromAPIGatewayShortBatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.restorer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/${var.api_stage_name}/POST/short-batch/restore/*"
}