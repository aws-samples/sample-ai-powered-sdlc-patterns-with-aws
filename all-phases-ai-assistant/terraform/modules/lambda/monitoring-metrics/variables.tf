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

# Variables for Monitoring Metrics Lambda Module (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-monitoring-metrics

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  type        = string
}

variable "metrics_log_group_name" {
  description = "Name of the CloudWatch log group for metrics"
  type        = string
}

variable "audit_log_group_name" {
  description = "Name of the CloudWatch log group for audit logs"
  type        = string
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}