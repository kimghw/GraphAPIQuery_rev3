"""Environment-specific configuration management."""

from typing import Dict, Any, List
from enum import Enum
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from core.exceptions import ConfigurationException


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentConfig:
    """Environment-specific configuration provider."""
    
    @staticmethod
    def get_config(env: Environment) -> Dict[str, Any]:
        """Get environment-specific configuration."""
        configs = {
            Environment.DEVELOPMENT: {
                "database_echo": True,
                "log_level": "DEBUG",
                "cors_origins": ["*"],
                "rate_limit_enabled": False,
                "cache_enabled": False,
                "metrics_enabled": False,
                "sentry_enabled": False,
                "webhook_verification": False,
                "token_encryption_enabled": False,
                "background_tasks_enabled": True,
                "max_concurrent_requests": 100,
                "request_timeout": 30,
                "database_pool_size": 5,
                "database_max_overflow": 10,
            },
            Environment.TESTING: {
                "database_echo": False,
                "log_level": "WARNING",
                "cors_origins": ["http://localhost:3000"],
                "rate_limit_enabled": False,
                "cache_enabled": False,
                "metrics_enabled": False,
                "sentry_enabled": False,
                "webhook_verification": False,
                "token_encryption_enabled": True,
                "background_tasks_enabled": False,
                "max_concurrent_requests": 50,
                "request_timeout": 15,
                "database_pool_size": 2,
                "database_max_overflow": 5,
            },
            Environment.STAGING: {
                "database_echo": False,
                "log_level": "INFO",
                "cors_origins": ["https://staging.yourdomain.com"],
                "rate_limit_enabled": True,
                "cache_enabled": True,
                "metrics_enabled": True,
                "sentry_enabled": True,
                "webhook_verification": True,
                "token_encryption_enabled": True,
                "background_tasks_enabled": True,
                "max_concurrent_requests": 200,
                "request_timeout": 30,
                "database_pool_size": 10,
                "database_max_overflow": 20,
            },
            Environment.PRODUCTION: {
                "database_echo": False,
                "log_level": "INFO",
                "cors_origins": ["https://yourdomain.com"],
                "rate_limit_enabled": True,
                "cache_enabled": True,
                "metrics_enabled": True,
                "sentry_enabled": True,
                "webhook_verification": True,
                "token_encryption_enabled": True,
                "background_tasks_enabled": True,
                "max_concurrent_requests": 500,
                "request_timeout": 60,
                "database_pool_size": 20,
                "database_max_overflow": 40,
            }
        }
        return configs.get(env, {})
    
    @staticmethod
    def get_rate_limits(env: Environment) -> Dict[str, str]:
        """Get environment-specific rate limits."""
        rate_limits = {
            Environment.DEVELOPMENT: {
                "auth": "100/minute",
                "mail_query": "1000/minute",
                "mail_send": "100/minute",
                "webhook": "50/minute",
            },
            Environment.TESTING: {
                "auth": "50/minute",
                "mail_query": "500/minute",
                "mail_send": "50/minute",
                "webhook": "25/minute",
            },
            Environment.STAGING: {
                "auth": "60/minute",
                "mail_query": "600/minute",
                "mail_send": "60/minute",
                "webhook": "30/minute",
            },
            Environment.PRODUCTION: {
                "auth": "30/minute",
                "mail_query": "300/minute",
                "mail_send": "30/minute",
                "webhook": "15/minute",
            }
        }
        return rate_limits.get(env, rate_limits[Environment.PRODUCTION])
    
    @staticmethod
    def get_cache_config(env: Environment) -> Dict[str, Any]:
        """Get environment-specific cache configuration."""
        cache_configs = {
            Environment.DEVELOPMENT: {
                "enabled": False,
                "backend": "memory",
                "ttl": 300,  # 5 minutes
                "max_size": 100,
            },
            Environment.TESTING: {
                "enabled": False,
                "backend": "memory",
                "ttl": 60,  # 1 minute
                "max_size": 50,
            },
            Environment.STAGING: {
                "enabled": True,
                "backend": "redis",
                "ttl": 1800,  # 30 minutes
                "max_size": 1000,
                "redis_url": "redis://localhost:6379/1",
            },
            Environment.PRODUCTION: {
                "enabled": True,
                "backend": "redis",
                "ttl": 3600,  # 1 hour
                "max_size": 10000,
                "redis_url": "redis://localhost:6379/0",
            }
        }
        return cache_configs.get(env, cache_configs[Environment.PRODUCTION])


class EnhancedSettings(BaseSettings):
    """Enhanced settings with environment-specific configuration."""
    
    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # Application
    APP_NAME: str = Field(default="Microsoft Graph API Mail Collection System", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    
    # Database
    DATABASE_URL: str = Field(default="sqlite:///./graphapi.db", env="DATABASE_URL")
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    DATABASE_POOL_SIZE: int = Field(default=5, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
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
    
    # Security
    ENCRYPTION_KEY: str = Field(default="", env="ENCRYPTION_KEY")
    TOKEN_ENCRYPTION_ENABLED: bool = Field(default=False, env="TOKEN_ENCRYPTION_ENABLED")
    WEBHOOK_VERIFICATION: bool = Field(default=False, env="WEBHOOK_VERIFICATION")
    WEBHOOK_SECRET: str = Field(default="", env="WEBHOOK_SECRET")
    
    # External API
    EXTERNAL_API_ENDPOINT: str = Field(default="", env="EXTERNAL_API_ENDPOINT")
    EXTERNAL_API_TIMEOUT: int = Field(default=30, env="EXTERNAL_API_TIMEOUT")
    EXTERNAL_API_RETRY_ATTEMPTS: int = Field(default=3, env="EXTERNAL_API_RETRY_ATTEMPTS")
    
    # Server
    HOST: str = Field(default="127.0.0.1", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    MAX_CONCURRENT_REQUESTS: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    REQUEST_TIMEOUT: int = Field(default=30, env="REQUEST_TIMEOUT")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=False, env="RATE_LIMIT_ENABLED")
    
    # Caching
    CACHE_ENABLED: bool = Field(default=False, env="CACHE_ENABLED")
    CACHE_BACKEND: str = Field(default="memory", env="CACHE_BACKEND")
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")
    CACHE_MAX_SIZE: int = Field(default=100, env="CACHE_MAX_SIZE")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Monitoring
    METRICS_ENABLED: bool = Field(default=False, env="METRICS_ENABLED")
    SENTRY_ENABLED: bool = Field(default=False, env="SENTRY_ENABLED")
    SENTRY_DSN: str = Field(default="", env="SENTRY_DSN")
    
    # Background Tasks
    BACKGROUND_TASKS_ENABLED: bool = Field(default=True, env="BACKGROUND_TASKS_ENABLED")
    TOKEN_REFRESH_INTERVAL: int = Field(default=300, env="TOKEN_REFRESH_INTERVAL")  # 5 minutes
    WEBHOOK_RENEWAL_INTERVAL: int = Field(default=3600, env="WEBHOOK_RENEWAL_INTERVAL")  # 1 hour
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._apply_environment_config()
        self._validate_configuration()
    
    def _apply_environment_config(self):
        """Apply environment-specific configuration."""
        try:
            env = Environment(self.ENVIRONMENT.lower())
            env_config = EnvironmentConfig.get_config(env)
            
            # Apply environment-specific settings
            for key, value in env_config.items():
                if hasattr(self, key.upper()):
                    setattr(self, key.upper(), value)
            
            # Apply rate limits
            self._rate_limits = EnvironmentConfig.get_rate_limits(env)
            
            # Apply cache config
            cache_config = EnvironmentConfig.get_cache_config(env)
            self.CACHE_ENABLED = cache_config["enabled"]
            self.CACHE_BACKEND = cache_config["backend"]
            self.CACHE_TTL = cache_config["ttl"]
            self.CACHE_MAX_SIZE = cache_config["max_size"]
            if "redis_url" in cache_config:
                self.REDIS_URL = cache_config["redis_url"]
                
        except ValueError as e:
            raise ConfigurationException("ENVIRONMENT", str(e))
    
    def _validate_configuration(self):
        """Validate configuration based on environment."""
        env = Environment(self.ENVIRONMENT.lower())
        
        # Production-specific validations
        if env == Environment.PRODUCTION:
            if "sqlite" in self.DATABASE_URL.lower():
                raise ConfigurationException(
                    "DATABASE_URL", 
                    "SQLite cannot be used in production environment"
                )
            
            if not self.CLIENT_SECRET:
                raise ConfigurationException(
                    "CLIENT_SECRET", 
                    "Client secret is required in production"
                )
            
            if not self.ENCRYPTION_KEY:
                raise ConfigurationException(
                    "ENCRYPTION_KEY", 
                    "Encryption key is required in production"
                )
            
            if self.DEBUG:
                raise ConfigurationException(
                    "DEBUG", 
                    "Debug mode must be disabled in production"
                )
            
            if "*" in self.CORS_ORIGINS:
                raise ConfigurationException(
                    "CORS_ORIGINS", 
                    "Wildcard CORS origins not allowed in production"
                )
        
        # Staging-specific validations
        if env == Environment.STAGING:
            if not self.ENCRYPTION_KEY:
                raise ConfigurationException(
                    "ENCRYPTION_KEY", 
                    "Encryption key is required in staging"
                )
        
        # General validations
        if self.TOKEN_ENCRYPTION_ENABLED and not self.ENCRYPTION_KEY:
            raise ConfigurationException(
                "ENCRYPTION_KEY", 
                "Encryption key is required when token encryption is enabled"
            )
        
        if self.WEBHOOK_VERIFICATION and not self.WEBHOOK_SECRET:
            raise ConfigurationException(
                "WEBHOOK_SECRET", 
                "Webhook secret is required when webhook verification is enabled"
            )
        
        if self.SENTRY_ENABLED and not self.SENTRY_DSN:
            raise ConfigurationException(
                "SENTRY_DSN", 
                "Sentry DSN is required when Sentry is enabled"
            )
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        valid_envs = [e.value for e in Environment]
        if v.lower() not in valid_envs:
            raise ValueError(f"ENVIRONMENT must be one of: {', '.join(valid_envs)}")
        return v.lower()
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v.upper()
    
    @field_validator("CACHE_BACKEND")
    @classmethod
    def validate_cache_backend(cls, v: str) -> str:
        """Validate cache backend."""
        valid_backends = ["memory", "redis"]
        if v.lower() not in valid_backends:
            raise ValueError(f"CACHE_BACKEND must be one of: {', '.join(valid_backends)}")
        return v.lower()
    
    def get_microsoft_graph_config(self) -> Dict[str, Any]:
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
    
    def get_rate_limits(self) -> Dict[str, str]:
        """Get rate limits for current environment."""
        return getattr(self, '_rate_limits', {})
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT.value
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == Environment.TESTING.value
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENVIRONMENT == Environment.STAGING.value
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == Environment.PRODUCTION.value


def get_enhanced_settings() -> EnhancedSettings:
    """Get enhanced settings instance."""
    return EnhancedSettings()
