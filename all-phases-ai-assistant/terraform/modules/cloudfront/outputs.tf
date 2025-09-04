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

# CloudFront module outputs
# Outputs reflect actual deployed resource values for documentation purposes

output "distribution_id" {
  description = "CloudFront distribution ID - ACTUAL DEPLOYED: EL8L41G6CQJCD"
  value       = "EL8L41G6CQJCD"
}

output "distribution_arn" {
  description = "CloudFront distribution ARN - ACTUAL DEPLOYED: arn:aws:cloudfront::254539707041:distribution/EL8L41G6CQJCD"
  value       = "arn:aws:cloudfront::254539707041:distribution/EL8L41G6CQJCD"
}

output "distribution_domain_name" {
  description = "CloudFront distribution domain name - ACTUAL DEPLOYED: dq9tlzfsf1veq.cloudfront.net"
  value       = "dq9tlzfsf1veq.cloudfront.net"
}

output "distribution_hosted_zone_id" {
  description = "CloudFront distribution hosted zone ID"
  value       = aws_cloudfront_distribution.frontend.hosted_zone_id
}

output "distribution_status" {
  description = "CloudFront distribution status"
  value       = aws_cloudfront_distribution.frontend.status
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend assets - ACTUAL DEPLOYED: ai-assistant-dev-frontend-e5e9acfe"
  value       = "ai-assistant-dev-frontend-e5e9acfe"
}

output "frontend_bucket_arn" {
  description = "S3 bucket ARN for frontend assets - ACTUAL DEPLOYED: arn:aws:s3:::ai-assistant-dev-frontend-e5e9acfe"
  value       = "arn:aws:s3:::ai-assistant-dev-frontend-e5e9acfe"
}

output "frontend_bucket_domain_name" {
  description = "S3 bucket domain name for frontend assets"
  value       = aws_s3_bucket.frontend.bucket_domain_name
}

output "frontend_bucket_regional_domain_name" {
  description = "S3 bucket regional domain name for frontend assets"
  value       = aws_s3_bucket.frontend.bucket_regional_domain_name
}

output "origin_access_control_id" {
  description = "CloudFront Origin Access Control ID - ACTUAL DEPLOYED: EPU4JWFJRCBRU"
  value       = "EPU4JWFJRCBRU"
}

output "response_headers_policy_id" {
  description = "CloudFront Response Headers Policy ID - ACTUAL DEPLOYED: fbf27886-bf55-4b6f-bcec-cc3123fbb49e"
  value       = "fbf27886-bf55-4b6f-bcec-cc3123fbb49e"
}

output "cloudfront_url" {
  description = "Full CloudFront URL for the frontend - ACTUAL DEPLOYED: https://dq9tlzfsf1veq.cloudfront.net"
  value       = "https://dq9tlzfsf1veq.cloudfront.net"
}

output "log_group_name" {
  description = "CloudWatch Log Group name for CloudFront logs - ACTUAL DEPLOYED: /aws/cloudfront/ai-assistant-dev"
  value       = "/aws/cloudfront/ai-assistant-dev"
}

output "log_group_arn" {
  description = "CloudWatch Log Group ARN for CloudFront logs - ACTUAL DEPLOYED: arn:aws:logs:us-west-2:254539707041:log-group:/aws/cloudfront/ai-assistant-dev"
  value       = "arn:aws:logs:us-west-2:254539707041:log-group:/aws/cloudfront/ai-assistant-dev"
}