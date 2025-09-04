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

# Provider configuration for chat handler Lambda function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYMENT: AWS CLI with aidlc_main profile in us-west-2

# AWS Provider configuration - MUST use us-west-2 and aidlc_main profile
provider "aws" {
  region  = "us-west-2"
  profile = "aidlc_main"
  
  default_tags {
    tags = {
      Project     = "ai-assistant"
      ManagedBy   = "terraform"
      Environment = var.environment
    }
  }
}