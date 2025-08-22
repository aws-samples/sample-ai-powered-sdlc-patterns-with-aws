"""Application configuration settings."""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings and configuration."""
    
    # Server configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # AWS configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    CLAUDE_MODEL_ID: str = os.getenv("CLAUDE_MODEL_ID")
    
    # S3 configuration
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    S3_REGION: str = os.getenv("S3_REGION", AWS_REGION)
    S3_ACCESS_KEY_ID: Optional[str] = os.getenv("S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY: Optional[str] = os.getenv("S3_SECRET_ACCESS_KEY")
    S3_ENDPOINT_URL: Optional[str] = os.getenv("S3_ENDPOINT_URL")  # For LocalStack or custom S3 endpoints
    S3_USE_SSL: bool = os.getenv("S3_USE_SSL", "true").lower() == "true"
    S3_VERIFY_SSL: bool = os.getenv("S3_VERIFY_SSL", "true").lower() == "true"
    
    # MCP configuration
    MCP_ENVIRONMENT: str = os.getenv("MCP_ENVIRONMENT", "development")
    
    # Session configuration
    MAX_SESSIONS: int = 1000
    SESSION_TIMEOUT_HOURS: int = 24
    
    # Authentication configuration (AWS Cognito)
    COGNITO_USER_POOL_ID: Optional[str] = os.getenv("COGNITO_USER_POOL_ID")
    COGNITO_CLIENT_ID: Optional[str] = os.getenv("COGNITO_CLIENT_ID")
    COGNITO_CLIENT_SECRET: Optional[str] = os.getenv("COGNITO_CLIENT_SECRET")
    COGNITO_IDENTITY_POOL_ID: Optional[str] = os.getenv("COGNITO_IDENTITY_POOL_ID")
    COGNITO_REGION: str = os.getenv("COGNITO_REGION", AWS_REGION)
    
    # JWT configuration
    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "RS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    
    # Authentication settings
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    REQUIRE_EMAIL_VERIFICATION: bool = os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").lower() == "true"
    ALLOW_SELF_REGISTRATION: bool = os.getenv("ALLOW_SELF_REGISTRATION", "false").lower() == "true"
    
    # OAuth configuration (Atlassian/Jira)
    ATLASSIAN_CLIENT_ID: Optional[str] = os.getenv("ATLASSIAN_CLIENT_ID")
    ATLASSIAN_CLIENT_SECRET: Optional[str] = os.getenv("ATLASSIAN_CLIENT_SECRET")
    ATLASSIAN_REDIRECT_URI: str = os.getenv("ATLASSIAN_REDIRECT_URI", "http://localhost:3000/callback.html")
    
    # File paths
    CONVERSATIONS_DIR: str = "conversations"
    GENERATED_CODE_DIR: str = "generated_code"
    # PROJECTS_DIR removed - projects are now stored only in S3
    # DIAGRAMS_DIR removed - diagrams are stored in S3 only


settings = Settings()