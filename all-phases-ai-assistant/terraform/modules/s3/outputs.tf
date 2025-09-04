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

# Documents Bucket Outputs
output "documents_bucket_id" {
  description = "Actual documents bucket ID"
  value       = "ai-assistant-dev-documents-993738bb"
}

output "documents_bucket_arn" {
  description = "Actual documents bucket ARN"
  value       = "arn:aws:s3:::ai-assistant-dev-documents-993738bb"
}

output "documents_bucket_domain_name" {
  description = "Actual documents bucket domain name"
  value       = "ai-assistant-dev-documents-993738bb.s3.amazonaws.com"
}

output "documents_bucket_regional_domain_name" {
  description = "Actual documents bucket regional domain name"
  value       = "ai-assistant-dev-documents-993738bb.s3.us-west-2.amazonaws.com"
}

# Frontend Bucket Outputs
output "frontend_bucket_id" {
  description = "Actual frontend bucket ID"
  value       = "ai-assistant-dev-frontend-e5e9acfe"
}

output "frontend_bucket_arn" {
  description = "Actual frontend bucket ARN"
  value       = "arn:aws:s3:::ai-assistant-dev-frontend-e5e9acfe"
}

output "frontend_bucket_domain_name" {
  description = "Actual frontend bucket domain name"
  value       = "ai-assistant-dev-frontend-e5e9acfe.s3.amazonaws.com"
}

output "frontend_bucket_regional_domain_name" {
  description = "Actual frontend bucket regional domain name"
  value       = "ai-assistant-dev-frontend-e5e9acfe.s3.us-west-2.amazonaws.com"
}

# Configuration Outputs
output "versioning_enabled" {
  description = "Versioning status for both buckets"
  value = {
    documents = "Enabled"
    frontend  = "Enabled"
  }
}

output "encryption_configuration" {
  description = "Encryption configuration for both buckets"
  value = {
    documents = {
      sse_algorithm      = "AES256"
      bucket_key_enabled = true
    }
    frontend = {
      sse_algorithm      = "AES256"
      bucket_key_enabled = true
    }
  }
}

output "public_access_block" {
  description = "Public access block configuration for both buckets"
  value = {
    documents = {
      block_public_acls       = true
      block_public_policy     = true
      ignore_public_acls      = true
      restrict_public_buckets = true
    }
    frontend = {
      block_public_acls       = true
      block_public_policy     = true
      ignore_public_acls      = true
      restrict_public_buckets = true
    }
  }
}