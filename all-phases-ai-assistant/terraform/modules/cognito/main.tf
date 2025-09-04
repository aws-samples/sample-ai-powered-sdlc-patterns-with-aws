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

# Cognito User Pool for AI Assistant Authentication
# This module documents the deployed Cognito User Pool with email authentication and user roles

# Data source for current AWS caller identity
data "aws_caller_identity" "current" {}

# Cognito User Pool - ACTUAL DEPLOYED CONFIGURATION
# User Pool ID: us-west-2_FLJTm8Xt8
# Name: ai-assistant-user-pool
resource "aws_cognito_user_pool" "ai_assistant" {
  # ACTUAL VALUES FROM DEPLOYED INFRASTRUCTURE
  name = "ai-assistant-user-pool"  # Actual deployed name

  # Email as username (matches deployed config)
  username_attributes = ["email"]
  
  # Auto-verify email addresses (matches deployed config)
  auto_verified_attributes = ["email"]

  # Password policy (matches deployed config)
  password_policy {
    minimum_length                   = 12
    require_lowercase               = true
    require_numbers                 = true
    require_symbols                 = true
    require_uppercase               = true
    temporary_password_validity_days = 7
  }

  # Email configuration (matches deployed config)
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Custom attributes for user roles (matches deployed config)
  schema {
    name                = "role"
    attribute_data_type = "String"
    mutable            = true
    required           = false
    
    string_attribute_constraints {
      min_length = 4
      max_length = 10
    }
  }

  # Account recovery settings (matches deployed config)
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # User pool add-ons for advanced security (matches deployed config)
  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
  }

  # Account lockout policy (matches deployed config)
  admin_create_user_config {
    allow_admin_create_user_only = false
    
    invite_message_template {
      email_message = "Your username is {username} and temporary password is {####}. Please sign in and change your password."
      email_subject = "Your temporary password"
      sms_message   = "Your username is {username} and temporary password is {####}"
    }
  }

  # Device configuration for enhanced security (matches deployed config)
  device_configuration {
    challenge_required_on_new_device      = true
    device_only_remembered_on_user_prompt = true
  }

  tags = var.tags
}

# Cognito User Pool Client - ACTUAL DEPLOYED CONFIGURATION
# Client ID: 3gr32ei5n768d88h02klhmpn8v
# Name: ai-assistant-client
resource "aws_cognito_user_pool_client" "ai_assistant_client" {
  # ACTUAL VALUES FROM DEPLOYED INFRASTRUCTURE
  name         = "ai-assistant-client"  # Actual deployed name
  user_pool_id = "us-west-2_FLJTm8Xt8"  # Actual deployed user pool ID

  # OAuth configuration (matches deployed config - OAuth disabled)
  allowed_oauth_flows_user_pool_client = false  # Actual deployed value
  # Note: OAuth flows and scopes not configured in deployed client
  
  # Callback URLs and logout URLs not configured in deployed client
  # callback_urls = var.callback_urls
  # logout_urls   = var.logout_urls

  # Supported identity providers (matches deployed config)
  supported_identity_providers = ["COGNITO"]

  # Token validity (matches deployed config)
  access_token_validity  = 1  # 1 hour
  id_token_validity     = 1  # 1 hour
  refresh_token_validity = 30 # 30 days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  # Explicit auth flows (matches deployed config)
  explicit_auth_flows = [
    "ALLOW_ADMIN_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  # Prevent user existence errors (matches deployed config)
  prevent_user_existence_errors = "ENABLED"

  # Enable token revocation (matches deployed config)
  enable_token_revocation = true

  # Auth session validity (matches deployed config)
  auth_session_validity = 3  # 3 minutes

  # Read and write attributes not explicitly configured in deployed client
  # Using default behavior
}

# Cognito User Pool Domain - ACTUAL DEPLOYED CONFIGURATION
# Domain: ai-assistant-auth-3gja49wa
# CloudFront Distribution: dpp0gtxikpq3y.cloudfront.net
resource "aws_cognito_user_pool_domain" "ai_assistant_domain" {
  # ACTUAL VALUES FROM DEPLOYED INFRASTRUCTURE
  domain       = "ai-assistant-auth-3gja49wa"  # Actual deployed domain
  user_pool_id = "us-west-2_FLJTm8Xt8"        # Actual deployed user pool ID
}

# Note: Random string resource not needed for documentation
# The actual domain suffix "3gja49wa" is already deployed

# Cognito User Groups - ACTUAL DEPLOYED CONFIGURATION
resource "aws_cognito_user_group" "admin_group" {
  # ACTUAL VALUES FROM DEPLOYED INFRASTRUCTURE
  name         = "admin"                        # Actual deployed group name
  user_pool_id = "us-west-2_FLJTm8Xt8"        # Actual deployed user pool ID
  description  = "Administrator group with full system access"  # Actual deployed description
  # Note: precedence and role_arn not configured in deployed groups
}

resource "aws_cognito_user_group" "user_group" {
  # ACTUAL VALUES FROM DEPLOYED INFRASTRUCTURE
  name         = "user"                         # Actual deployed group name
  user_pool_id = "us-west-2_FLJTm8Xt8"        # Actual deployed user pool ID
  description  = "Regular user group with standard access"  # Actual deployed description
  # Note: precedence and role_arn not configured in deployed groups
}