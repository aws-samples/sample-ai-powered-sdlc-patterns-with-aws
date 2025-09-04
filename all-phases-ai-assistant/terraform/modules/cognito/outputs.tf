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

# Outputs for Cognito module - ACTUAL DEPLOYED VALUES

output "user_pool_id" {
  description = "ID of the Cognito User Pool (actual deployed value)"
  value       = "us-west-2_FLJTm8Xt8"  # Actual deployed User Pool ID
}

output "user_pool_arn" {
  description = "ARN of the Cognito User Pool (actual deployed value)"
  value       = "arn:aws:cognito-idp:us-west-2:254539707041:userpool/us-west-2_FLJTm8Xt8"  # Actual deployed ARN
}

output "user_pool_client_id" {
  description = "ID of the Cognito User Pool Client (actual deployed value)"
  value       = "3gr32ei5n768d88h02klhmpn8v"  # Actual deployed Client ID
}

output "user_pool_domain" {
  description = "Domain of the Cognito User Pool (actual deployed value)"
  value       = "ai-assistant-auth-3gja49wa"  # Actual deployed domain
}

output "user_pool_domain_cloudfront" {
  description = "CloudFront distribution for Cognito domain (actual deployed value)"
  value       = "dpp0gtxikpq3y.cloudfront.net"  # Actual CloudFront distribution
}

output "user_pool_endpoint" {
  description = "Endpoint of the Cognito User Pool (actual deployed value)"
  value       = "cognito-idp.us-west-2.amazonaws.com/us-west-2_FLJTm8Xt8"  # Actual endpoint
}

output "admin_group_name" {
  description = "Name of the admin user group (actual deployed value)"
  value       = "admin"  # Actual deployed group name
}

output "user_group_name" {
  description = "Name of the standard user group (actual deployed value)"
  value       = "user"  # Actual deployed group name
}

# Additional outputs reflecting actual deployed configuration
output "user_pool_name" {
  description = "Name of the Cognito User Pool (actual deployed value)"
  value       = "ai-assistant-user-pool"  # Actual deployed name
}

output "client_name" {
  description = "Name of the Cognito User Pool Client (actual deployed value)"
  value       = "ai-assistant-client"  # Actual deployed client name
}

output "oauth_enabled" {
  description = "Whether OAuth flows are enabled (actual deployed value)"
  value       = false  # OAuth not enabled in deployed client
}

output "token_validity" {
  description = "Token validity configuration (actual deployed values)"
  value = {
    access_token  = "1 hour"
    id_token      = "1 hour"
    refresh_token = "30 days"
  }
}

output "auth_flows" {
  description = "Enabled authentication flows (actual deployed values)"
  value = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
}