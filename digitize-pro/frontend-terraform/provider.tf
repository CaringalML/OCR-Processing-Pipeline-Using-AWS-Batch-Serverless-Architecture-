provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Component   = "Frontend Infrastructure"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}