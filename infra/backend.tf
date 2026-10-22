# Remote state is intentionally commented out.
# `terraform init -backend=false` and `terraform validate` then run with no
# AWS account, no state bucket, and no credentials. Uncomment and adjust the
# bucket before sharing this stack across a team.
#
# terraform {
#   backend "s3" {
#     bucket         = "example-terraform-state"
#     key            = "weather-etl/terraform.tfstate"
#     region         = "us-east-1"
#     dynamodb_table = "example-terraform-locks"
#     encrypt        = true
#   }
# }
