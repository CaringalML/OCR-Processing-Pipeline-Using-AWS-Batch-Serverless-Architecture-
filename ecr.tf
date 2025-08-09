resource "aws_ecr_repository" "main" {
  name                 = "${var.project_name}-${var.environment}-app"
  image_tag_mutability = var.ecr_image_tag_mutability
  force_delete         = var.ecr_force_delete # Ensures images are deleted with the repo

  image_scanning_configuration {
    scan_on_push = var.ecr_scan_on_push
  }

  encryption_configuration {
    encryption_type = var.ecr_encryption_type
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
        rulePriority = var.ecr_lifecycle_tagged_rule_priority
        description  = var.ecr_lifecycle_tagged_rule_description
        selection = {
          tagStatus     = var.ecr_lifecycle_tagged_status
          tagPrefixList = var.ecr_lifecycle_tag_prefix_list
          countType     = var.ecr_lifecycle_tagged_count_type
          countNumber   = var.ecr_lifecycle_tagged_count_number
        }
        action = {
          type = var.ecr_lifecycle_action_type
        }
      },
      {
        rulePriority = var.ecr_lifecycle_untagged_rule_priority
        description  = var.ecr_lifecycle_untagged_rule_description
        selection = {
          tagStatus   = var.ecr_lifecycle_untagged_status
          countType   = var.ecr_lifecycle_untagged_count_type
          countUnit   = var.ecr_lifecycle_untagged_count_unit
          countNumber = var.ecr_lifecycle_untagged_count_number
        }
        action = {
          type = var.ecr_lifecycle_action_type
        }
      }
    ]
  })
}
