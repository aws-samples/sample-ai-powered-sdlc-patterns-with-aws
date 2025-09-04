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

# CloudFront module for React frontend deployment
# Provides secure, fast content delivery for the AI Assistant frontend
# 
# ACTUAL DEPLOYED RESOURCES:
# - Distribution ID: EL8L41G6CQJCD
# - Domain: dq9tlzfsf1veq.cloudfront.net
# - S3 Origin: ai-assistant-dev-frontend-e5e9acfe.s3.us-west-2.amazonaws.com
# - API Gateway Origin: jpt8wzkowd.execute-api.us-west-2.amazonaws.com

# S3 bucket for frontend static assets
# ACTUAL DEPLOYED: ai-assistant-dev-frontend-e5e9acfe
resource "aws_s3_bucket" "frontend" {
  bucket = "ai-assistant-dev-frontend-e5e9acfe"
  
  tags = merge(var.tags, {
    Name        = "ai-assistant-dev-frontend"
    Purpose     = "Frontend Static Assets"
    Environment = "dev"
  })
}

# S3 bucket versioning for frontend assets
resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket server-side encryption for frontend assets
resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 bucket public access block - CloudFront will access via OAC
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront Origin Access Control for S3 bucket access
# ACTUAL DEPLOYED: EPU4JWFJRCBRU
resource "aws_cloudfront_origin_access_control" "frontend" {
  name                              = "ai-assistant-dev-frontend-oac"
  description                       = "Origin Access Control for ai-assistant frontend S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# S3 bucket policy to allow CloudFront access via OAC
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })
  
  depends_on = [aws_cloudfront_distribution.frontend]
}

# CloudFront distribution for React frontend
# ACTUAL DEPLOYED: EL8L41G6CQJCD (dq9tlzfsf1veq.cloudfront.net)
resource "aws_cloudfront_distribution" "frontend" {
  # S3 origin for static assets
  # ACTUAL DEPLOYED: ai-assistant-dev-frontend-e5e9acfe.s3.us-west-2.amazonaws.com
  origin {
    domain_name              = "ai-assistant-dev-frontend-e5e9acfe.s3.us-west-2.amazonaws.com"
    origin_access_control_id = "EPU4JWFJRCBRU"
    origin_id                = "S3-ai-assistant-dev-frontend-e5e9acfe"
    
    # Custom headers for security
    custom_header {
      name  = "X-Frontend-Origin"
      value = "ai-assistant-dev"
    }
  }

  # API Gateway origin for backend API calls
  # ACTUAL DEPLOYED: jpt8wzkowd.execute-api.us-west-2.amazonaws.com
  origin {
    domain_name = "jpt8wzkowd.execute-api.us-west-2.amazonaws.com"
    origin_id   = "API-Gateway"
    origin_path = "/dev"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      origin_keepalive_timeout = 5
      origin_read_timeout    = 30
    }
    
    custom_header {
      name  = "X-API-Origin"
      value = "ai-assistant-dev"
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "ai-assistant dev React Frontend Distribution"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  # Default cache behavior for static assets (React app)
  # ACTUAL DEPLOYED: Uses S3-ai-assistant-dev-frontend-e5e9acfe as target
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-ai-assistant-dev-frontend-e5e9acfe"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    # Use AWS managed caching policy for SPA
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized

    # Use AWS managed origin request policy
    origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf" # Managed-CORS-S3Origin
    
    # Security headers policy - ACTUAL DEPLOYED: fbf27886-bf55-4b6f-bcec-cc3123fbb49e
    response_headers_policy_id = "fbf27886-bf55-4b6f-bcec-cc3123fbb49e"
  }

  # Cache behavior for API calls - no caching
  # ACTUAL DEPLOYED: /api/* pattern targeting API-Gateway origin
  ordered_cache_behavior {
    path_pattern           = "/api/*"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "API-Gateway"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    # Use AWS managed caching policy for API (no caching)
    cache_policy_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # Managed-CachingDisabled

    # Use AWS managed origin request policy for API Gateway
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # Managed-AllViewerExceptHostHeader
  }

  # Cache behavior for static assets with long TTL
  # ACTUAL DEPLOYED: /static/* pattern targeting S3 origin
  ordered_cache_behavior {
    path_pattern           = "/static/*"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    target_origin_id       = "S3-ai-assistant-dev-frontend-e5e9acfe"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    # Use AWS managed caching policy for static assets (long TTL)
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized
  }

  # Custom error responses for SPA routing
  # ACTUAL DEPLOYED: 403 and 404 errors redirect to /index.html
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }
  
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  # Geographic restrictions (none by default)
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Use CloudFront default certificate
  # ACTUAL DEPLOYED: CloudFront default certificate with TLSv1 minimum
  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1"
  }

  tags = merge(var.tags, {
    Name        = "ai-assistant-dev-frontend-distribution"
    Purpose     = "Frontend Content Delivery"
    Environment = "dev"
  })
}

# CloudFront Response Headers Policy for security
# ACTUAL DEPLOYED: fbf27886-bf55-4b6f-bcec-cc3123fbb49e (ai-assistant-dev-security-headers)
# NOTE: This resource represents the deployed policy but should not be managed by Terraform
resource "aws_cloudfront_response_headers_policy" "security_headers" {
  name    = "ai-assistant-dev-security-headers"
  comment = "Security headers for ai-assistant frontend"

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                   = false  # ACTUAL DEPLOYED: false
      override                  = true
    }
    
    content_type_options {
      override = true
    }
    
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }

  # Custom headers - ACTUAL DEPLOYED: X-Environment and X-Frontend-Version only
  custom_headers_config {
    items {
      header   = "X-Frontend-Version"
      value    = "1.0.0"
      override = true
    }
    
    items {
      header   = "X-Environment"
      value    = "dev"
      override = true
    }
  }

  # CORS configuration - ACTUAL DEPLOYED: Allows all origins and headers
  cors_config {
    access_control_allow_credentials = false
    access_control_allow_headers {
      items = ["*"]
    }
    access_control_allow_methods {
      items = ["DELETE", "GET", "HEAD", "OPTIONS", "POST", "PUT"]
    }
    access_control_allow_origins {
      items = ["*"]
    }
    access_control_max_age_sec = 86400
    origin_override           = true
  }
}

# CloudWatch Log Group for CloudFront access logs (optional)
# ACTUAL DEPLOYED: /aws/cloudfront/ai-assistant-dev
resource "aws_cloudwatch_log_group" "cloudfront_logs" {
  name              = "/aws/cloudfront/ai-assistant-dev"
  retention_in_days = 30
  
  tags = merge(var.tags, {
    Name        = "ai-assistant-dev-cloudfront-logs"
    Purpose     = "CloudFront Access Logs"
    Environment = "dev"
  })
}