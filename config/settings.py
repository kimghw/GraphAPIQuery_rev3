"""Application settings with environment-based configuration."""

import os
from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Application
    APP_NAME: str = Field(default="Microsoft Graph API Mail Collection System", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./graphapi.db", env="DATABASE_URL")
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Microsoft Graph API
    CLIENT_ID: str = Field(..., env="CLIENT_ID")
    TENANT_ID: str = Field(..., env="TENANT_ID")
    CLIENT_SECRET: str = Field(..., env="CLIENT_SECRET")
    USER_ID: str = Field(..., env="USER_ID")
    SCOPES: str = Field(default='["https://graph.microsoft.com/Mail.Read", "https://graph.microsoft.com/Mail.Send"]', env="SCOPES")
    REDIRECT_URI: str = Field(default="http://localhost:5000/auth/callback", env="REDIRECT_URI")
    GRAPH_API_ENDPOINT: str = Field(default="https://graph.microsoft.com/v1.0", env="GRAPH_API_ENDPOINT")
    AUTHORITY: str = Field(..., env="AUTHORITY")
    TOKEN_CACHE_FILE: str = Field(default=".token_cache.json", env="TOKEN_CACHE_FILE")
    
    # External API
    EXTERNAL_API_ENDPOINT: Optional[str] = Field(default=None, env="EXTERNAL_API_ENDPOINT")
    EXTERNAL_API_TIMEOUT: int = Field(default=30, env="EXTERNAL_API_TIMEOUT")
    EXTERNAL_API_RETRY_ATTEMPTS: int = Field(default=3, env="EXTERNAL_API_RETRY_ATTEMPTS")
    
    # Server
    HOST: str = Field(default="127.0.0.1", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Allow extra fields from .env
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        if v.lower() not in ["development", "testing", "production"]:
            raise ValueError("ENVIRONMENT must be one of: development, testing, production")
        return v.lower()


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
