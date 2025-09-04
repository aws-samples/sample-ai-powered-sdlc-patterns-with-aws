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

# Backend configuration for Terraform state management
# DOCUMENTATION ONLY - Not used for actual deployments

terraform {
  # Backend configuration is not used since this is documentation only
  # All infrastructure is managed via AWS CLI
  # backend "s3" {
  #   # Configuration would be provided via backend config file
  # }
}

# Note: Local backend for documentation purposes only
# Actual infrastructure is managed via AWS CLI, not Terraform state