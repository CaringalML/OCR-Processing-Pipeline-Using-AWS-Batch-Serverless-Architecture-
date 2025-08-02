resource "aws_ecr_repository" "main" {
  name                 = "${var.project_name}-${var.environment}-app"
  image_tag_mutability = "MUTABLE"
  force_delete         = true # Ensures images are deleted with the repo

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  lifecycle {
    ignore_changes = [
      image_tag_mutability,
      image_scanning_configuration,
      encryption_configuration
    ]
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-app-repo"
  })
}

resource "aws_ecr_lifecycle_policy" "main" {
  repository = aws_ecr_repository.main.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 3 images tagged 'latest'"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["latest"]
          countType     = "imageCountMoreThan"
          countNumber   = 3
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
