.PHONY: help init short-plan full-plan short-apply full-apply short-destroy full-destroy long-destroy

# Default target - show help
help:
	@echo "OCR Processor Infrastructure Management"
	@echo "======================================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  make init          - Initialize Terraform"
	@echo ""
	@echo "Planning:"
	@echo "  make short-plan    - Preview short-batch deployment"
	@echo "  make full-plan     - Preview full deployment"
	@echo ""
	@echo "Deployment:"
	@echo "  make short-apply   - Deploy short-batch only (Lambda processing for ≤300KB files)"
	@echo "  make full-apply    - Deploy full infrastructure (Lambda + AWS Batch)"
	@echo ""
	@echo "Scaling Down:"
	@echo "  make long-destroy  - Remove AWS Batch components only (revert full → short-batch)"
	@echo ""
	@echo "Full Destruction:"
	@echo "  make short-destroy - Destroy entire short-batch deployment"
	@echo "  make full-destroy  - Destroy entire full deployment"

# Initialize Terraform
init:
	terraform init

# Preview short-batch deployment
short-plan:
	terraform plan -var="deployment_mode=short-batch"

# Preview full deployment
full-plan:
	terraform plan -var="deployment_mode=full"

# Deploy short-batch only (Lambda processing for small files)
short-apply:
	terraform apply -var="deployment_mode=short-batch" --auto-approve

# Deploy full infrastructure (Lambda + AWS Batch)
full-apply:
	terraform apply -var="deployment_mode=full" --auto-approve

# Remove only AWS Batch components (scale down from full to short-batch)
# This is done by applying short-batch mode, which removes long-batch resources
long-destroy:
	@echo "Removing AWS Batch components while preserving Lambda infrastructure..."
	terraform apply -var="deployment_mode=short-batch" --auto-approve

# Destroy entire short-batch deployment
short-destroy:
	terraform destroy -var="deployment_mode=short-batch" --auto-approve

# Destroy entire full deployment
full-destroy:
	terraform destroy -var="deployment_mode=full" --auto-approve
