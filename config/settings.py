"""Application settings with environment-based configuration."""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field, validator
from enum import Enum


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(default="sqlite:///./graphapi.db", env="DATABASE_URL")
    echo: bool = Field(default=False, env="DATABASE_ECHO")
    pool_size: int = Field(default=5, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    @validator("url")
    def validate_database_url(cls, v: str) -> str:
        """Convert SQLite URL to async version."""
        if v.startswith("sqlite:///"):
            return v.replace("sqlite:///", "sqlite+aiosqlite:///")
        return v


class MicrosoftGraphSettings(BaseSettings):
    """Microsoft Graph API configuration."""
    
    client_id: str = Field(..., env="CLIENT_ID")
    tenant_id: str = Field(..., env="TENANT_ID")
    client_secret: str = Field(..., env="CLIENT_SECRET")
    user_id: str = Field(..., env="USER_ID")
    scopes: List[str] = Field(
        default=["https://graph.microsoft.com/Mail.Read", "https://graph.microsoft.com/Mail.Send"],
        env="SCOPES"
    )
    redirect_uri: str = Field(default="http://localhost:5000/auth/callback", env="REDIRECT_URI")
    graph_api_endpoint: str = Field(default="https://graph.microsoft.com/v1.0", env="GRAPH_API_ENDPOINT")
    authority: str = Field(..., env="AUTHORITY")
    token_cache_file: str = Field(default=".token_cache.json", env="TOKEN_CACHE_FILE")
    
    @validator("authority")
    def build_authority(cls, v: str, values: dict) -> str:
        """Build authority URL with tenant ID."""
        if "${TENANT_ID}" in v and "tenant_id" in values:
            return v.replace("${TENANT_ID}", values["tenant_id"])
        return v


class RedisSettings(BaseSettings):
    """Redis configuration for caching and message broker."""
    
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = Field(default=0, env="REDIS_DB")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    @property
    def url(self) -> str:
        """Build Redis URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class LoggingSettings(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")


class APISettings(BaseSettings):
    """API server configuration."""
    
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    reload: bool = Field(default=False, env="API_RELOAD")
    workers: int = Field(default=1, env="API_WORKERS")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Application
    app_name: str = Field(default="Microsoft Graph API Mail Collection System", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    
    # Sub-settings
    database: DatabaseSettings = DatabaseSettings()
    microsoft_graph: MicrosoftGraphSettings = MicrosoftGraphSettings()
    redis: RedisSettings = RedisSettings()
    logging: LoggingSettings = LoggingSettings()
    api: APISettings = APISettings()
    
    # External API
    external_api_endpoint: Optional[str] = Field(default=None, env="EXTERNAL_API_ENDPOINT")
    external_api_timeout: int = Field(default=30, env="EXTERNAL_API_TIMEOUT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("environment", pre=True)
    def validate_environment(cls, v):
        """Validate environment value."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v
    
    @validator("debug")
    def set_debug_based_on_environment(cls, v: bool, values: dict) -> bool:
        """Set debug mode based on environment."""
        if "environment" in values:
            if values["environment"] == Environment.DEVELOPMENT:
                return True
            elif values["environment"] == Environment.PRODUCTION:
                return False
        return v


class DevelopmentSettings(Settings):
    """Development environment settings."""
    
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.database.echo = True
        self.logging.level = "DEBUG"
        self.api.reload = True


class TestingSettings(Settings):
    """Testing environment settings."""
    
    environment: Environment = Environment.TESTING
    debug: bool = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.database.url = "sqlite+aiosqlite:///./test_graphapi.db"
        self.database.echo = False
        self.logging.level = "WARNING"
        self.microsoft_graph.token_cache_file = ".test_token_cache.json"


class ProductionSettings(Settings):
    """Production environment settings."""
    
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logging.level = "INFO"
        self.api.reload = False
        
    @validator("database")
    def validate_production_database(cls, v: DatabaseSettings) -> DatabaseSettings:
        """Ensure production doesn't use SQLite."""
        if "sqlite" in v.url.lower():
            raise ValueError("SQLite는 운영환경에서 사용할 수 없습니다")
        return v


def get_settings() -> Settings:
    """Get settings based on environment variable."""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()
