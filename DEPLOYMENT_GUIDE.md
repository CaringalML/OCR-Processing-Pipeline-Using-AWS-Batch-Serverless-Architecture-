# 🚀 OCR System Deployment Guide

A comprehensive guide for deploying the OCR Document Processing & Search System with flexible scaling options.

**Quick Start:** `terraform init && make short-apply` (2-3 minutes) → `make full-apply` (when ready for production)

---

## 🎯 Deployment Modes Overview

| Feature | Short-Batch Mode | Full Mode |
|---------|------------------|-----------|
| **Purpose** | Development, testing, cost-optimization | Production, enterprise, unlimited processing |
| **File Size Limit** | ≤300KB | Unlimited |
| **Processing Engine** | Claude AI only | Claude AI + AWS Textract |
| **Deploy Time** | 2-3 minutes | 5-7 minutes |
| **Monthly Cost** | $20-80 (no VPC interface endpoints) | $176-295 (includes 8 VPC interface endpoints) |
| **API Endpoints** | `/batch/*`, `/short-batch/*` | All including `/long-batch/*` |
| **Infrastructure** | 5 Lambda functions + minimal AWS services | Full enterprise infrastructure |

---

## 🚀 Quick Deployment

### **Option 1: Start Small (Recommended)**
```bash
# 1. Initial setup
terraform init
terraform validate

# 2. Deploy short-batch mode (2-3 minutes)
make short-apply

# 3. Test with small files (≤300KB)
curl -X POST "$(terraform output -raw api_gateway_url)/batch/upload" \
  -F "file=@small-document.pdf" -F "title=Test"

# 4. Scale up when ready (upgrade to full mode)
make full-apply    # Adds AWS Batch capabilities

# 5. Scale down if needed
make long-destroy  # Remove AWS Batch, keep Lambda processing
```

### **Option 2: Full Production Deployment**
```bash
# Deploy complete infrastructure immediately
terraform init && make full-apply

# Includes Docker container deployment for AWS Batch
# GitHub Actions will build and push container automatically
```

---

## 📋 Prerequisites & Setup

### **1. Required Tools**
```bash
# Check versions
aws --version      # AWS CLI v2+ required
terraform --version # v1.0+ required
docker --version   # Latest (only needed for full mode)
make --version     # Standard make utility

# Install if missing
# AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
# Terraform: https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli
```

### **2. AWS Configuration**
```bash
# Configure credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (ap-southeast-2), Output format (json)

# Verify access
aws sts get-caller-identity
```

### **3. Claude AI Setup**
```bash
# Get API key from: https://console.anthropic.com/
# Required for all deployments (short-batch and full mode)

# Method 1: Environment variable (temporary)
export ANTHROPIC_API_KEY="sk-ant-api03-YOUR_KEY_HERE"

# Method 2: Create terraform.tfvars (recommended)
echo 'anthropic_api_key = "sk-ant-api03-YOUR_KEY_HERE"' > terraform.tfvars
```

### **4. GitHub Actions Setup (Optional - Full Mode)**
```bash
# Required GitHub Secrets for automatic Docker builds:
# Repository → Settings → Secrets and variables → Actions

AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=ap-southeast-2
ECR_REPOSITORY=ocr-processor-batch
```

---

## 🎯 Deployment Commands Reference

### **Planning & Validation**
```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Preview short-batch deployment
make short-plan

# Preview full deployment  
make full-plan

# General plan (uses terraform.tfvars or defaults)
terraform plan
```

### **Deployment Commands**
```bash
# Short-batch mode (Lambda-only, ≤300KB files)
make short-apply

# Full mode (Lambda + AWS Batch, unlimited files)  
make full-apply

# Upgrade: short-batch → full mode
make full-apply    # Adds AWS Batch resources

# Scale down: full → short-batch mode
make long-destroy  # Removes AWS Batch, keeps Lambda
```

### **Destruction Commands**
```bash
# Remove all resources
make full-destroy     # Works for both modes

# Remove only AWS Batch components (scale down)
make long-destroy     # Keeps Lambda processing active
```

### **Help & Information**
```bash
# Show available commands
make help

# Get deployment information
terraform output deployment_info

# Get API endpoints
terraform output api_endpoints
```

---

## 🔄 Deployment Workflows

### **Workflow 1: Development → Production**
```bash
# Stage 1: Development (cost-optimized)
make short-apply
# Test with small files, develop features, validate setup
# Cost: ~$20-80/month

# Stage 2: Production (full capabilities) 
make full-apply
# Handle files of any size, enterprise features
# Cost: ~$64-183/month
```

### **Workflow 2: Temporary Scale-Up**
```bash
# Normal operation: short-batch mode
make short-apply

# Temporary scale-up for large file batch
make full-apply
# Process large files as needed

# Scale back down to save costs
make long-destroy
# Back to Lambda-only processing
```

### **Workflow 3: Production with Cost Control**
```bash
# Deploy full mode for production
make full-apply

# During low-activity periods (nights/weekends)
make long-destroy    # Disable expensive AWS Batch

# Re-enable for business hours
make full-apply      # Full capabilities restored
```

---

## 🚨 Troubleshooting & Common Issues

### **Deployment Failures**

#### **Terraform Validation Errors**
```bash
# Fix: Update Terraform to latest version
terraform version
# If < 1.0, update from: https://developer.hashicorp.com/terraform/downloads

# Re-initialize after updates
terraform init -upgrade
```

#### **AWS Permission Issues**
```bash
# Check current permissions
aws sts get-caller-identity

# Required IAM permissions for deployment:
# - Lambda: Full access for function management
# - API Gateway: Full access for endpoint creation
# - DynamoDB: Full access for table management
# - S3: Full access for bucket operations
# - IAM: Role and policy creation permissions
# - VPC: Network resource management (full mode)
# - Batch: Container service management (full mode)
```

#### **Claude API Key Issues**
```bash
# Test API key directly
curl -X POST https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'

# Should return a response, not an error
```

### **Docker & ECR Issues (Full Mode)**

#### **ECR Login Failures**
```bash
# Manual ECR login
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url)

# Check repository exists
aws ecr describe-repositories --repository-names ocr-processor-batch-app
```

#### **GitHub Actions Failures**
```bash
# Verify secrets are configured correctly
# GitHub Repository → Settings → Secrets and variables → Actions

# Check workflow status
# GitHub Repository → Actions tab → View latest workflow run

# Manual Docker build test
cd aws_batch
docker build -t test-ocr .
docker run --rm test-ocr python index.py --help
```

### **Runtime Issues**

#### **Large File Rejections in Short-Batch Mode**
```bash
# Expected behavior - files >300KB rejected with helpful error:
{
  "error": "Large file processing unavailable", 
  "message": "This deployment only supports files ≤300KB. Contact administrator to enable full deployment mode.",
  "deployment_mode": "short-batch",
  "max_file_size": "300KB"
}

# Solution: Upgrade to full mode
make full-apply
```

#### **Processing Failures**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/ocr-processor-prod-s3-uploader --follow

# Check DynamoDB for failed records
aws dynamodb scan --table-name ocr-processor-prod-processing-results \
  --filter-expression "#status = :status" \
  --expression-attribute-names '{"#status": "processing_status"}' \
  --expression-attribute-values '{":status": {"S": "failed"}}'

# Check SQS queue depths
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw sqs_short_batch_queue_url) \
  --attribute-names ApproximateNumberOfMessages
```

---

## 📊 Monitoring & Operations

### **Health Checks**
```bash
# Basic API health check
curl $(terraform output -raw api_gateway_url)/health

# Check deployment info
terraform output deployment_info

# View infrastructure resources
terraform output infrastructure
```

### **Cost Monitoring**
```bash
# Check current AWS costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '30 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost

# Monitor specific services
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

### **Performance Monitoring**
```bash
# Lambda execution metrics
aws logs insights start-query \
  --log-group-name /aws/lambda/ocr-processor-prod-s3-uploader \
  --start-time $(date -d '24 hours ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @duration, @billedDuration | filter @type = "REPORT" | sort @timestamp desc | limit 100'

# DynamoDB performance
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=ocr-processor-prod-processing-results \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Sum
```

---

## 🔧 Advanced Configuration

### **Custom Variables**
```bash
# Create terraform.tfvars for customization
cat > terraform.tfvars << EOF
# Required
anthropic_api_key = "sk-ant-api03-YOUR_KEY"

# Optional customizations
deployment_mode = "short-batch"  # or "full"
project_name = "my-ocr-system"
environment = "production"
aws_region = "us-east-1"

# Rate limiting
public_rate_limit = 20
registered_rate_limit = 100

# Monitoring
admin_alert_email = "ops@company.com"
enable_monitoring = true

# Cost optimization
enable_ssm_endpoints = false  # Save $21/month
EOF
```

### **Multi-Environment Setup**
```bash
# Environment-specific deployments
# Development
terraform workspace new dev
terraform apply -var="environment=dev" -var="deployment_mode=short-batch"

# Production  
terraform workspace new prod
terraform apply -var="environment=prod" -var="deployment_mode=full"

# Switch between environments
terraform workspace select dev
terraform workspace select prod
```

### **Custom Domain Setup** 
```bash
# Add to terraform.tfvars
custom_domain = "ocr.yourcompany.com"
certificate_arn = "arn:aws:acm:region:account:certificate/cert-id"

# Deploy with custom domain
terraform apply
```

---

## 🎯 Best Practices

### **Development Workflow**
1. **Start with short-batch mode** for development and testing
2. **Use version control** for terraform.tfvars (exclude sensitive data)
3. **Test with small files first** before attempting large files
4. **Monitor costs regularly** especially during development
5. **Scale up only when needed** to control expenses

### **Production Deployment**
1. **Use full mode** for production workloads
2. **Set up monitoring** with CloudWatch dashboards and SNS alerts
3. **Configure backups** for critical DynamoDB tables
4. **Implement proper tagging** for cost allocation
5. **Document your configuration** for team members

### **Security Considerations**
1. **Rotate API keys regularly** for Claude AI
2. **Use least-privilege IAM policies** for deployment roles
3. **Enable CloudTrail logging** for audit compliance
4. **Configure VPC endpoints** for cost-optimized private networking (full mode uses 8 interface endpoints, short-batch uses free gateway endpoints only)
5. **Monitor for unusual activity** through CloudWatch alarms

### **Networking Architecture**
- **Short-batch mode**: Uses free VPC gateway endpoints (S3, DynamoDB) - no additional network costs
- **Full mode**: Adds 8 VPC interface endpoints (~$155/month) for secure AWS Batch communication
- **No NAT gateways**: Cost-optimized design using VPC endpoints instead of expensive NAT gateways

---

## 📞 Support & Resources

### **Documentation**
- **Main README.md**: Complete feature overview and examples
- **variables.tf**: Detailed configuration options
- **outputs.tf**: API endpoints and infrastructure details
- **GitHub Issues**: Bug reports and feature requests

### **Useful Commands Summary**
```bash
# Quick reference card
make help                    # Show all available commands
terraform output            # Show all outputs
terraform output deployment_info  # Current deployment status
terraform output api_endpoints    # Ready-to-use API URLs
terraform state list        # Show all managed resources
terraform refresh           # Sync state with real infrastructure
```

### **Emergency Procedures**
```bash
# Complete system removal (emergency)
make full-destroy    # Works for both modes
terraform state list # Should be empty

# Restore from backup (if configured)
terraform import aws_dynamodb_table.processing_results table-name

# Force resource recreation
terraform apply -replace="aws_lambda_function.s3_uploader"
```

---

## 🏁 Conclusion

The OCR system's flexible deployment modes allow you to:

- **Start small** with short-batch mode ($20-80/month)
- **Scale up seamlessly** to full mode when needed
- **Scale down temporarily** to control costs during low usage
- **Deploy confidently** with comprehensive monitoring and troubleshooting guides

**Next Steps:**
1. Complete initial deployment: `make short-apply` or `make full-apply`
2. Test with your documents using the API endpoints
3. Set up monitoring and alerts for production use
4. Scale as your needs grow

**Need help?** Check the troubleshooting section above or open a GitHub issue with detailed error messages and deployment configuration.

---

*Last Updated: August 2025 - Covers deployment modes, scaling options, and production best practices*