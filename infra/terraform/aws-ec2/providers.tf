provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "opendays-finance-platform"
      Environment = "demo"
      ManagedBy   = "terraform"
    }
  }
}
