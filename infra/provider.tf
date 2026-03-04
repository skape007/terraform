provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "azure-automations"
      Environment = var.stack_name
      ManagedBy   = "terraform"
    }
  }
}

