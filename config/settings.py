"""Application settings with environment-based configuration."""

import os
from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Main application settings with validation."""
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Application
    APP_NAME: str = "Microsoft Graph API Mail Collection System"
    APP_VERSION: str = "1.0.0"
    
    # Database
    DATABASE_URL: str = "sqlite:///./graphapi.db"
    DATABASE_ECHO: bool = False
    
    # Microsoft Graph API
    CLIENT_ID: str
    TENANT_ID: str
    CLIENT_SECRET: str
    USER_ID: str
    SCOPES: List[str] = ["https://graph.microsoft.com/Mail.Read", "https://graph.microsoft.com/Mail.Send"]
    REDIRECT_URI: str = "http://localhost:5000/auth/callback"
    GRAPH_API_ENDPOINT: str = "https://graph.microsoft.com/v1.0"
    AUTHORITY: str
    TOKEN_CACHE_FILE: str = ".token_cache.json"
    
    # External API
    EXTERNAL_API_ENDPOINT: Optional[str] = None
    EXTERNAL_API_TIMEOUT: int = 30
    EXTERNAL_API_RETRY_ATTEMPTS: int = 3
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Security
    ENCRYPTION_KEY: Optional[str] = None
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # Cache
    REDIS_URL: Optional[str] = None
    CACHE_DEFAULT_TTL: int = 3600
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    METRICS_ENABLED: bool = True
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Background Tasks
    BACKGROUND_TASKS_ENABLED: bool = True
    TOKEN_REFRESH_INTERVAL: int = 300  # 5 minutes
    WEBHOOK_RENEWAL_INTERVAL: int = 1800  # 30 minutes
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        if v.lower() not in ["development", "testing", "production"]:
            raise ValueError("ENVIRONMENT must be one of: development, testing, production")
        return v.lower()
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins."""
        if isinstance(v, str):
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @field_validator("SCOPES", mode="before")
    @classmethod
    def validate_scopes(cls, v):
        """Validate and parse scopes."""
        if isinstance(v, str):
            # Handle JSON string or comma-separated
            if v.startswith('[') and v.endswith(']'):
                import json
                return json.loads(v)
            else:
                return [scope.strip() for scope in v.split(',')]
        return v
    
    @field_validator("RATE_LIMIT_REQUESTS")
    @classmethod
    def validate_rate_limit_requests(cls, v):
        """Validate rate limit requests."""
        if v <= 0 or v > 10000:
            raise ValueError("RATE_LIMIT_REQUESTS must be between 1 and 10000")
        return v
    
    @field_validator("RATE_LIMIT_WINDOW")
    @classmethod
    def validate_rate_limit_window(cls, v):
        """Validate rate limit window."""
        if v <= 0 or v > 3600:  # Max 1 hour
            raise ValueError("RATE_LIMIT_WINDOW must be between 1 and 3600 seconds")
        return v
    
    @field_validator("TOKEN_REFRESH_INTERVAL")
    @classmethod
    def validate_token_refresh_interval(cls, v):
        """Validate token refresh interval."""
        if v < 60 or v > 3600:  # Between 1 minute and 1 hour
            raise ValueError("TOKEN_REFRESH_INTERVAL must be between 60 and 3600 seconds")
        return v
    
    @field_validator("WEBHOOK_RENEWAL_INTERVAL")
    @classmethod
    def validate_webhook_renewal_interval(cls, v):
        """Validate webhook renewal interval."""
        if v < 300 or v > 7200:  # Between 5 minutes and 2 hours
            raise ValueError("WEBHOOK_RENEWAL_INTERVAL must be between 300 and 7200 seconds")
        return v
    
    @model_validator(mode='after')
    def validate_production_config(self):
        """Validate production-specific configuration."""
        if self.ENVIRONMENT == 'production':
            # Security validations for production
            if self.DEBUG:
                raise ValueError('DEBUG must be False in production')
            
            if "*" in self.CORS_ORIGINS:
                raise ValueError('CORS_ORIGINS cannot contain "*" in production')
            
            # Database validation
            if 'sqlite' in self.DATABASE_URL.lower():
                raise ValueError('SQLite cannot be used in production')
            
            if self.SECRET_KEY == "dev-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be changed from default value in production")
        
        return self
    
    def get_microsoft_graph_config(self) -> dict:
        """Get Microsoft Graph configuration."""
        return {
            "client_id": self.CLIENT_ID,
            "tenant_id": self.TENANT_ID,
            "client_secret": self.CLIENT_SECRET,
            "authority": self.AUTHORITY,
            "redirect_uri": self.REDIRECT_URI,
            "graph_api_endpoint": self.GRAPH_API_ENDPOINT,
            "scopes": self.SCOPES,
            "token_cache_file": self.TOKEN_CACHE_FILE
        }
    
    def get_database_config(self) -> dict:
        """Get database configuration."""
        return {
            "url": self.DATABASE_URL,
            "echo": self.DATABASE_ECHO
        }
    
    def get_cache_config(self) -> dict:
        """Get cache configuration."""
        return {
            "redis_url": self.REDIS_URL,
            "default_ttl": self.CACHE_DEFAULT_TTL,
            "enabled": bool(self.REDIS_URL)
        }
    
    def get_security_config(self) -> dict:
        """Get security configuration."""
        return {
            "encryption_key": self.ENCRYPTION_KEY,
            "secret_key": self.SECRET_KEY,
            "cors_origins": self.CORS_ORIGINS
        }
    
    def get_monitoring_config(self) -> dict:
        """Get monitoring configuration."""
        return {
            "sentry_dsn": self.SENTRY_DSN,
            "metrics_enabled": self.METRICS_ENABLED,
            "environment": self.ENVIRONMENT
        }
    
    def get_rate_limit_config(self) -> dict:
        """Get rate limiting configuration."""
        return {
            "enabled": self.RATE_LIMIT_ENABLED,
            "requests": self.RATE_LIMIT_REQUESTS,
            "window": self.RATE_LIMIT_WINDOW
        }
    
    def get_background_tasks_config(self) -> dict:
        """Get background tasks configuration."""
        return {
            "enabled": self.BACKGROUND_TASKS_ENABLED,
            "token_refresh_interval": self.TOKEN_REFRESH_INTERVAL,
            "webhook_renewal_interval": self.WEBHOOK_RENEWAL_INTERVAL
        }
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.ENVIRONMENT == "testing"
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()


def validate_settings() -> dict:
    """
    Validate settings and return results.
    
    Returns:
        Dictionary with validation results
    """
    try:
        settings = get_settings()
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "summary": {
                "environment": settings.ENVIRONMENT,
                "debug_mode": settings.DEBUG,
                "database_type": "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql",
                "cache_enabled": bool(settings.REDIS_URL),
                "external_api_configured": bool(settings.EXTERNAL_API_ENDPOINT),
                "encryption_enabled": bool(settings.ENCRYPTION_KEY),
                "monitoring_enabled": bool(settings.SENTRY_DSN),
                "cors_origins_count": len(settings.CORS_ORIGINS),
                "log_level": settings.LOG_LEVEL,
                "server_config": {
                    "host": settings.HOST,
                    "port": settings.PORT
                }
            }
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to load settings: {str(e)}"],
            "warnings": [],
            "summary": {}
        }


# Global settings instance
settings = get_settings()
