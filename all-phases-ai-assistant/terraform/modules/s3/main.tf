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

# S3 Bucket for Document Storage
# Actual bucket: ai-assistant-dev-documents-993738bb
resource "aws_s3_bucket" "documents" {
  bucket = "ai-assistant-dev-documents-993738bb"

  tags = {
    Name        = "AI Assistant Documents"
    Environment = "dev"
    Project     = "ai-assistant"
    Purpose     = "document-storage"
  }
}

# S3 Bucket for Frontend Assets
# Actual bucket: ai-assistant-dev-frontend-e5e9acfe
resource "aws_s3_bucket" "frontend" {
  bucket = "ai-assistant-dev-frontend-e5e9acfe"

  tags = {
    Name        = "AI Assistant Frontend"
    Environment = "dev"
    Project     = "ai-assistant"
    Purpose     = "frontend-hosting"
  }
}

# Versioning Configuration for Documents Bucket
resource "aws_s3_bucket_versioning" "documents_versioning" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Versioning Configuration for Frontend Bucket
resource "aws_s3_bucket_versioning" "frontend_versioning" {
  bucket = aws_s3_bucket.frontend.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side Encryption for Documents Bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "documents_encryption" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Server-side Encryption for Frontend Bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "frontend_encryption" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Public Access Block for Documents Bucket
resource "aws_s3_bucket_public_access_block" "documents_pab" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Public Access Block for Frontend Bucket
resource "aws_s3_bucket_public_access_block" "frontend_pab" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket Policy for Frontend (CloudFront Access)
# Actual CloudFront Distribution: EL8L41G6CQJCD
resource "aws_s3_bucket_policy" "frontend_policy" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = "arn:aws:cloudfront::254539707041:distribution/EL8L41G6CQJCD"
          }
        }
      }
    ]
  })
}

# CORS Configuration for Documents Bucket (if needed for uploads)
resource "aws_s3_bucket_cors_configuration" "documents_cors" {
  bucket = aws_s3_bucket.documents.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = [
      "https://dq9tlzfsf1veq.cloudfront.net",
      "https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com"
    ]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}