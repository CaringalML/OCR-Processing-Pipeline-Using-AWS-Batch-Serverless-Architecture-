# AWS Batch OCR Processor with Terraform

A complete serverless OCR processing system built with Terraform that demonstrates modern AWS infrastructure best practices. This project creates a cost-optimized AWS Batch environment triggered by API Gateway requests.

## Architecture Overview

```
Internet → API Gateway → Lambda Function → AWS Batch → Docker Container (ECR)
                            ↓
                     CloudWatch Logs & Monitoring
                            ↓
                     Auto-Cleanup System
```

## What This Project Demonstrates

- **Serverless Batch Processing**: AWS Batch with Fargate for container orchestration
- **Cost Optimization**: VPC Endpoints instead of expensive NAT Gateways
- **Infrastructure as Code**: Complete Terraform automation with embedded Lambda code
- **Security Best Practices**: Private subnets, least privilege IAM, and VPC endpoints
- **Auto-Cleanup**: Automated job cleanup to prevent resource accumulation
- **Production Ready**: Comprehensive monitoring, logging, and error handling

## Key Components

### Core Infrastructure
- **API Gateway**: REST endpoint that triggers OCR processing jobs via GET requests
- **Lambda Function**: Serverless trigger that submits jobs to AWS Batch
- **AWS Batch**: Managed container orchestration using Fargate
- **ECR Repository**: Secure Docker image storage with lifecycle policies
- **VPC with VPC Endpoints**: Cost-optimized private networking

### Monitoring & Operations
- **CloudWatch**: Comprehensive logging and monitoring dashboards
- **Auto-Cleanup Lambda**: Automated cleanup of old jobs and tasks
- **EventBridge**: Scheduled triggers for maintenance operations
- **CloudWatch Alarms**: Proactive monitoring of system health

## Cost Optimization Strategy

This infrastructure prioritizes cost efficiency through smart architectural choices:

### VPC Endpoints vs NAT Gateways

**Why VPC Endpoints?**
Traditional AWS Batch setups use NAT Gateways for internet access, but this project uses VPC Endpoints for significant cost savings while maintaining security and functionality.

## Cost Optimization Strategy

This infrastructure prioritizes cost efficiency through smart architectural choices:

### VPC Endpoints vs NAT Gateways

**Why VPC Endpoints?**
Traditional AWS Batch setups use NAT Gateways for internet access, but this project uses VPC Endpoints for significant cost savings while maintaining security and functionality.

### All VPC Endpoints (Active + Non-Active)

| VPC Endpoint | Type | Category | Monthly Cost | Purpose | Status |
|--------------|------|----------|--------------|---------|--------|
| ECR Docker Registry | Interface | Container Registry | $7.20 | Pull Docker images | ✅ Active |
| ECR API | Interface | Container Registry | $7.20 | ECR authentication & metadata | ✅ Active |
| CloudWatch Logs | Interface | Monitoring | $7.20 | Application logging | ✅ Active |
| ECS | Interface | Compute Service | $7.20 | Batch job orchestration | ✅ Active |
| ECS Agent | Interface | Compute Service | $7.20 | Container agent communication | ✅ Active |
| ECS Telemetry | Interface | Monitoring | $7.20 | ECS metrics and monitoring | ✅ Active |
| S3 Gateway | Gateway | Storage | FREE | ECR image layer storage | ✅ Active |
| SSM | Interface | Management | $7.20 | Systems Manager access | ❌ Disabled |
| SSM Messages | Interface | Management | $7.20 | Session Manager communication | ❌ Disabled |
| EC2 Messages | Interface | Management | $7.20 | EC2 Systems Manager | ❌ Disabled |

### Active VPC Endpoints Only

| VPC Endpoint | Type | Category | Monthly Cost | Purpose |
|--------------|------|----------|--------------|---------|
| ECR Docker Registry | Interface | Container Registry | $7.20 | Pull Docker images |
| ECR API | Interface | Container Registry | $7.20 | ECR authentication & metadata |
| CloudWatch Logs | Interface | Monitoring | $7.20 | Application logging |
| ECS | Interface | Compute Service | $7.20 | Batch job orchestration |
| ECS Agent | Interface | Compute Service | $7.20 | Container agent communication |
| ECS Telemetry | Interface | Monitoring | $7.20 | ECS metrics and monitoring |
| S3 Gateway | Gateway | Storage | FREE | ECR image layer storage |
| **TOTAL** | **6 Interface + 1 Gateway** | **All Categories** | **$43.20** | **Complete functionality** |

### Non-Active VPC Endpoints Only

| VPC Endpoint | Type | Category | Monthly Cost | Purpose |
|--------------|------|----------|--------------|---------|
| SSM | Interface | Management | $7.20 | Systems Manager access |
| SSM Messages | Interface | Management | $7.20 | Session Manager communication |
| EC2 Messages | Interface | Management | $7.20 | EC2 Systems Manager |
| **TOTAL** | **3 Interface** | **Management** | **$21.60** | **Debugging and troubleshooting** |

### Cost Summary

| Configuration | Monthly Cost | Annual Cost | Description |
|---------------|--------------|-------------|-------------|
| Current Active Endpoints | $43.20 | $518.40 | Complete AWS Batch functionality |
| If All Endpoints Enabled | $64.80 | $777.60 | Includes SSM debugging capabilities |
| Traditional NAT Gateway Setup | $90-120 | $1,080-1,440 | Legacy expensive approach |
| **Annual Savings** | **$561-922** | - | **Cost optimization achieved** |

*Note: To enable SSM endpoints for debugging, set `enable_ssm_endpoints = true` in your configuration.*

## Quick Start Guide

### Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform >= 1.0 installed
- Docker installed and running
- Basic understanding of AWS services

### 1. Deploy Infrastructure

```bash
# Clone repository and navigate to project directory
git clone <repository-url>
cd aws-batch-terraform

# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Deploy infrastructure
terraform apply
```

### 2. Build and Deploy Application

```bash
# Get ECR commands from Terraform output
terraform output manual_docker_commands

# Build Docker image
docker build -t hello-world-batch .

# Login to ECR
aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin $(terraform output -raw ecr_repository_url)

# Tag and push image
docker tag hello-world-batch:latest $(terraform output -raw ecr_repository_url):latest
docker push $(terraform output -raw ecr_repository_url):latest
```

### 3. Test the System

```bash
# Get API Gateway URL
terraform output api_gateway_invoke_url

# Trigger an OCR processing job
curl $(terraform output -raw api_gateway_invoke_url)

# Expected response:
{
  "success": true,
  "message": "OCR processing job submitted successfully",
  "jobId": "12345678-1234-1234-1234-123456789012",
  "jobName": "ocr-processor-job-20250717-123456-abcd1234",
  "timestamp": "2025-07-17T12:34:56.789Z"
}
```

## Configuration Options

### Essential Variables

Create a `terraform.tfvars` file to customize your deployment:

```hcl
# Basic Configuration
aws_region = "ap-southeast-2"
project_name = "my-ocr-processor"
environment = "dev"

# Cost Optimization
enable_ssm_endpoints = false  # Keep false to save $21.60/month

# Auto-Cleanup Settings
cleanup_age_hours = 24
cleanup_schedule_expression = "rate(6 hours)"
enable_auto_cleanup = true

# Network Configuration
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]
```

### Advanced Configuration

```hcl
# Lambda Function Settings
cleanup_lambda_timeout = 300
cleanup_lambda_memory = 256
cleanup_log_retention_days = 14

# Batch Job Settings
batch_compute_environment_name = "my-ocr-compute-env"
batch_job_queue_name = "my-ocr-job-queue"
batch_job_definition_name = "my-ocr-job-def"
```

## Auto-Cleanup System

The infrastructure includes an intelligent cleanup system that automatically removes old AWS Batch jobs and ECS tasks to prevent cost accumulation and maintain system hygiene.

### How It Works

- **Scheduled Execution**: Runs every 6 hours via EventBridge
- **Age-Based Cleanup**: Removes jobs/tasks older than 24 hours (configurable)
- **Safe Operation**: Only targets completed/stopped resources
- **Comprehensive Logging**: All cleanup actions are logged for audit

### Manual Cleanup

```bash
# Trigger cleanup immediately
terraform output manual_cleanup_command
# Then execute the provided command

# View cleanup logs
terraform output cleanup_logs_command
# Then execute the provided command

# Check cleanup configuration
terraform output cleanup_configuration_summary
```

### Cleanup Schedule Options

```hcl
# Every 6 hours (default)
cleanup_schedule_expression = "rate(6 hours)"

# Daily at 2 AM UTC
cleanup_schedule_expression = "cron(0 2 * * ? *)"

# Every 4 hours
cleanup_schedule_expression = "rate(4 hours)"
```

## Monitoring and Observability

### CloudWatch Integration

**Dashboards:**
- Batch job metrics (submitted, running, succeeded, failed)
- Lambda function performance (duration, errors, invocations)
- API Gateway metrics (requests, latency, error rates)

**Log Groups:**
- `/aws/lambda/ocr-processor-batch-trigger` - Lambda execution logs
- `/aws/batch/ocr-processor-job-def` - Batch job application logs
- `/aws/lambda/ocr-processor-auto-cleanup` - Cleanup operation logs

**Alarms:**
- Lambda function errors
- Batch job failures
- Cleanup operation failures

### Accessing Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/ocr-processor-batch-trigger --follow

# View Batch job logs
aws logs tail /aws/batch/ocr-processor-job-def --follow

# View cleanup logs
aws logs tail /aws/lambda/ocr-processor-auto-cleanup --follow
```

## Node.js Application Details

The containerized application demonstrates best practices for AWS Batch OCR workloads:

### Key Features

- **Environment Detection**: Automatically detects AWS Batch environment vs local development
- **Graceful Shutdown**: Proper container lifecycle management
- **Health Endpoints**: Built-in health checks for monitoring
- **Error Handling**: Comprehensive error handling and logging
- **Security**: Runs as non-root user with minimal privileges

### Application Behavior

**In AWS Batch Environment:**
```
Container starts → Runs OCR processing logic → Outputs results → Exits cleanly
Job Status: "Succeeded" ✅
```

**In Local Development:**
```
Container starts → Runs OCR processing logic → Starts web server → Continues running
Access: http://localhost:3000/process
```

### Container Optimization

- **Multi-stage build**: Optimized for production
- **Security scanning**: ECR automatically scans for vulnerabilities
- **Minimal base image**: Node.js Alpine for reduced attack surface
- **Build optimization**: `.dockerignore` excludes unnecessary files

## Security Considerations

### Network Security

- **Private Subnets**: Batch jobs run in private subnets with no direct internet access
- **VPC Endpoints**: Secure communication to AWS services without internet routing
- **Security Groups**: Minimal required access with explicit rules

### Access Control

- **IAM Roles**: Least privilege principle with service-specific permissions
- **Resource Isolation**: Clear separation between Lambda, Batch, and cleanup roles
- **API Security**: API Gateway with proper CORS configuration

### Container Security

- **Non-root Execution**: Containers run as dedicated user account
- **Image Scanning**: Automatic vulnerability scanning in ECR
- **Minimal Dependencies**: Only production dependencies in final image
- **Secret Management**: Environment-based configuration (extensible to Parameter Store)

## Troubleshooting Guide

### Common Issues

**Batch Jobs Not Starting:**
```bash
# Check job queue status
aws batch describe-job-queues --job-queues hello-world-job-queue

# Check compute environment
aws batch describe-compute-environments --compute-environments hello-world-compute-env

# Verify ECR image exists
aws ecr describe-images --repository-name batch-hello-world-hello-world
```

**Lambda Function Errors:**
```bash
# View Lambda logs
aws logs tail /aws/lambda/batch-hello-world-batch-trigger --follow

# Test Lambda directly
aws lambda invoke --function-name batch-hello-world-batch-trigger response.json
cat response.json
```

**API Gateway Issues:**
```bash
# Test API Gateway
curl -v $(terraform output -raw api_gateway_invoke_url)

# Check API Gateway logs
aws logs tail /aws/apigateway/hello-world-api --follow
```

### Useful Commands

```bash
# Get all Terraform outputs
terraform output

# Check specific job status
aws batch describe-jobs --jobs <JOB_ID>

# List recent jobs
aws batch list-jobs --job-queue hello-world-job-queue

# View cost optimization summary
terraform output cost_optimization_summary

# Check VPC endpoints
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=$(terraform output -raw vpc_id)"
```

## File Structure

```
ocr-processor-terraform/
├── Infrastructure Files
│   ├── versions.tf              # Provider versions and requirements
│   ├── variables.tf             # Input variables and validation
│   ├── vpc.tf                   # VPC with cost-optimized endpoints
│   ├── iam.tf                   # IAM roles and policies
│   ├── ecr.tf                   # ECR repository configuration
│   ├── batch.tf                 # AWS Batch resources
│   ├── lambda.tf                # Lambda function with embedded code
│   ├── api_gateway.tf           # API Gateway configuration
│   ├── cloudwatch.tf            # Monitoring and logging
│   ├── cleanup.tf               # Auto-cleanup system
│   └── outputs.tf               # Output values and commands
├── Application Files
│   ├── Dockerfile               # Multi-stage container build
│   ├── .dockerignore            # Build optimization
│   ├── package.json             # Node.js dependencies
│   └── index.js                 # OCR processing application code
├── Generated Files (auto-created)
│   ├── lambda_function.py       # Generated Lambda code
│   ├── lambda_function.zip      # Lambda deployment package
│   ├── cleanup_lambda_function.py
│   └── cleanup_lambda_function.zip
└── Documentation
    └── README.md                # This file
```

## Best Practices Demonstrated

### Infrastructure as Code
- **Modular Design**: Logical separation of resources across files
- **Variable Validation**: Input validation prevents configuration errors
- **Output Management**: Useful outputs for operations and debugging

### Cost Management
- **VPC Endpoints**: 85% reduction in networking costs
- **Fargate**: Pay-per-use compute model
- **Auto-cleanup**: Prevents resource accumulation
- **Lifecycle Policies**: Automatic cleanup of old images and logs

### Operations
- **Monitoring**: Comprehensive observability stack
- **Automation**: Minimal manual intervention required
- **Documentation**: Clear operational procedures
- **Troubleshooting**: Built-in debugging capabilities

### Security
- **Defense in Depth**: Multiple layers of security controls
- **Least Privilege**: Minimal required permissions
- **Network Isolation**: Private subnets with controlled access
- **Container Hardening**: Security-focused container practices

## Extending the Project

### Adding New Batch Jobs

1. Create new job definition in `batch.tf`
2. Update Lambda function to handle different job types
3. Add appropriate IAM permissions
4. Create new Docker images for different workloads

### Integrating with Other AWS Services

- **SQS**: Add queue-based job triggering
- **EventBridge**: Integrate with custom events
- **Step Functions**: Orchestrate complex workflows
- **Parameter Store**: Centralized configuration management

### Production Enhancements

- **Multi-environment**: Separate dev/staging/production
- **CI/CD Integration**: Automated testing and deployment
- **Secrets Management**: Integration with AWS Secrets Manager
- **Advanced Monitoring**: Custom metrics and alerting

## Cost Estimation

### Monthly Costs (ap-southeast-2)

**Fixed Costs:**
- VPC Endpoints: $43.20
- CloudWatch Log Groups: ~$2-5 (depending on volume)

**Variable Costs:**
- AWS Batch (Fargate): Pay per job execution
- Lambda: Pay per invocation (very minimal)
- API Gateway: Pay per request

**Example Usage:**
- 1000 batch jobs/month: ~$50-70 total
- 10,000 batch jobs/month: ~$100-150 total

**Cost Optimization:**
- Keep SSM endpoints disabled: Save $21.60/month
- Use ECR lifecycle policies: Automatic image cleanup
- Monitor CloudWatch log retention: Prevent excessive log costs


## CloudWatch Monitoring
 for the AWS Batch itself - /aws/batch/ocr-processor-job-def

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests for any improvements.

## Support

For issues and questions:
1. Check the troubleshooting guide above
2. Review CloudWatch logs for detailed error information
3. Use `terraform output` commands for operational guidance
4. Submit issues for bugs or feature requests