.PHONY: a d

a:
	terraform apply --auto-approve

d:
	terraform destroy --auto-approve
