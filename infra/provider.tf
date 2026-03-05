provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Confidentiality = "C3"
      Environment     = "PROD"
      ManagedBy       = "aws-vfgroup-onenet@vodafone.com"
      Project         = "GET-UC-ONENET"
      TaggingVersion  = "V2.3"
      SecurityZone    = "X1"
    }
  }
}

