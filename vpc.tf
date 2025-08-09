data "aws_availability_zones" "available" {
  state = var.vpc_availability_zone_state
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = var.vpc_enable_dns_hostnames
  enable_dns_support   = var.vpc_enable_dns_support

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = var.vpc_map_public_ip_on_launch

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
  }
}

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = var.vpc_default_route_cidr
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-private-rt-${count.index + 1}"
  }
}

resource "aws_route_table_association" "public" {
  count = length(var.public_subnet_cidrs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(var.private_subnet_cidrs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${var.project_name}-vpc-endpoints-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for VPC endpoints"

  ingress {
    description = "HTTPS from VPC"
    from_port   = var.vpc_https_port
    to_port     = var.vpc_https_port
    protocol    = var.vpc_protocol_tcp
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "All outbound traffic"
    from_port   = var.vpc_all_ports_start
    to_port     = var.vpc_all_ports_end
    protocol    = var.vpc_protocol_all
    cidr_blocks = [var.vpc_default_route_cidr]
  }

  tags = {
    Name = "${var.project_name}-vpc-endpoints-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Security Group for AWS Batch
resource "aws_security_group" "batch" {
  name_prefix = "${var.project_name}-batch-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for AWS Batch compute environment"

  egress {
    description = "All outbound traffic"
    from_port   = var.vpc_all_ports_start
    to_port     = var.vpc_all_ports_end
    protocol    = var.vpc_protocol_all
    cidr_blocks = [var.vpc_default_route_cidr]
  }

  tags = {
    Name = "${var.project_name}-batch-sg"
  }
}

# ========================================
# VPC ENDPOINTS (Cost-optimized solution)
# ========================================

# S3 Gateway VPC Endpoint (for ECR layer storage - FREE!)
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = var.vpc_endpoint_type_gateway
  route_table_ids   = aws_route_table.private[*].id

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect    = var.iam_effect_allow
        Principal = var.vpc_iam_principal_wildcard
        Action = var.vpc_s3_actions
        Resource = [
          "arn:aws:s3:::prod-${var.aws_region}-starport-layer-bucket/*",
          "arn:aws:s3:::prod-${var.aws_region}-starport-layer-bucket",
          "arn:aws:s3:::${var.project_name}-${var.environment}-uploads/*",
          "arn:aws:s3:::${var.project_name}-${var.environment}-uploads"
        ]
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-s3-endpoint"
  }
}

# DynamoDB Gateway VPC Endpoint (FREE!)
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type = var.vpc_endpoint_type_gateway
  route_table_ids   = aws_route_table.private[*].id

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect    = var.iam_effect_allow
        Principal = var.vpc_iam_principal_wildcard
        Action = var.vpc_dynamodb_actions
        Resource = var.vpc_iam_resource_wildcard
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-dynamodb-endpoint"
  }
}

# ECR Docker Registry VPC Endpoint
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect    = var.iam_effect_allow
        Principal = var.vpc_iam_principal_wildcard
        Action = var.vpc_ecr_actions
        Resource = var.vpc_iam_resource_wildcard
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecr-dkr-endpoint"
  }
}

# ECR API VPC Endpoint
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect    = var.iam_effect_allow
        Principal = var.vpc_iam_principal_wildcard
        Action = var.vpc_ecr_api_actions
        Resource = var.vpc_iam_resource_wildcard
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecr-api-endpoint"
  }
}

# CloudWatch Logs VPC Endpoint
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect    = var.iam_effect_allow
        Principal = var.vpc_iam_principal_wildcard
        Action = var.vpc_logs_actions
        Resource = var.vpc_iam_resource_wildcard
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-logs-endpoint"
  }
}

# ECS VPC Endpoint (for AWS Batch ECS integration)
resource "aws_vpc_endpoint" "ecs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecs"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect    = var.iam_effect_allow
        Principal = var.vpc_iam_principal_wildcard
        Action = var.vpc_ecs_actions
        Resource = var.vpc_iam_resource_wildcard
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-ecs-endpoint"
  }
}

# ECS Agent VPC Endpoint
resource "aws_vpc_endpoint" "ecs_agent" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecs-agent"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  tags = {
    Name = "${var.project_name}-ecs-agent-endpoint"
  }
}

# ECS Telemetry VPC Endpoint
resource "aws_vpc_endpoint" "ecs_telemetry" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecs-telemetry"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  tags = {
    Name = "${var.project_name}-ecs-telemetry-endpoint"
  }
}

# Textract VPC Endpoint (CRITICAL for OCR processing)
resource "aws_vpc_endpoint" "textract" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.textract"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect    = var.iam_effect_allow
        Principal = var.vpc_iam_principal_wildcard
        Action = var.vpc_textract_actions
        Resource = var.vpc_iam_resource_wildcard
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-textract-endpoint"
  }
}

# Comprehend VPC Endpoint (CRITICAL for text analysis)
resource "aws_vpc_endpoint" "comprehend" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.comprehend"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  policy = jsonencode({
    Version = var.iam_policy_version
    Statement = [
      {
        Effect    = var.iam_effect_allow
        Principal = var.vpc_iam_principal_wildcard
        Action = var.vpc_comprehend_actions
        Resource = var.vpc_iam_resource_wildcard
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-comprehend-endpoint"
  }
}

# Optional: SSM VPC Endpoints (for debugging/troubleshooting)
resource "aws_vpc_endpoint" "ssm" {
  count = var.enable_ssm_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ssm"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  tags = {
    Name = "${var.project_name}-ssm-endpoint"
  }
}

resource "aws_vpc_endpoint" "ssm_messages" {
  count = var.enable_ssm_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ssmmessages"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  tags = {
    Name = "${var.project_name}-ssm-messages-endpoint"
  }
}

resource "aws_vpc_endpoint" "ec2_messages" {
  count = var.enable_ssm_endpoints ? 1 : 0

  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ec2messages"
  vpc_endpoint_type   = var.vpc_endpoint_type_interface
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = var.vpc_endpoint_private_dns_enabled

  tags = {
    Name = "${var.project_name}-ec2-messages-endpoint"
  }
}