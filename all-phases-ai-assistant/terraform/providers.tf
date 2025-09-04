/*
 * ============================================================================
 * WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT
 * ============================================================================
 * 
 * This Terraform configuration is for documentation purposes only.
 * It reflects the current state of AWS infrastructure deployed via AWS CLI.
 * 
 * DO NOT RUN: terraform plan, terraform apply, or terraform destroy
 * 
 * For deployments, use AWS CLI commands as specified in deployment-workflow.md
 * ============================================================================
 */

# Provider configuration for AWS with profile and region requirements
# DOCUMENTATION ONLY - Reflects actual AWS profile and region used
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
  
  # Backend configuration not used - documentation only
  # All infrastructure managed via AWS CLI
}

# Primary AWS provider configuration
# DOCUMENTATION ONLY - Reflects actual AWS profile (aidlc_main) and region (us-west-2)
provider "aws" {
  profile = "aidlc_main"
  region  = "us-west-2"
  
  default_tags {
    tags = {
      Project     = "AI-Assistant"
      Environment = "dev"
      ManagedBy   = "AWS-CLI"  # Actual management method
    }
  }
}

# Additional provider for us-east-1 (for CloudFront SSL certificates if needed)
# DOCUMENTATION ONLY - Reflects actual AWS profile used for global resources
provider "aws" {
  alias   = "us_east_1"
  profile = "aidlc_main"
  region  = "us-east-1"
  
  default_tags {
    tags = {
      Project     = "AI-Assistant"
      Environment = "dev"
      ManagedBy   = "AWS-CLI"  # Actual management method
    }
  }
}