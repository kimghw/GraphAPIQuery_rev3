"""Configuration validation utilities."""

from typing import Dict, Any, List
from pydantic import field_validator, model_validator
import re
import os


class ConfigValidationMixin:
    """Mixin class for configuration validation."""
    
    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v, info):
        """Validate database URL."""
        if not v:
            raise ValueError('DATABASE_URL is required')
        
        # Check if production environment is using SQLite
        if hasattr(info, 'data') and info.data:
            environment = info.data.get('ENVIRONMENT', 'development')
            if environment == "production" and "sqlite" in v.lower():
                raise ValueError('SQLite cannot be used in production environment')
        
        return v
    
    @field_validator('CLIENT_ID')
    @classmethod
    def validate_client_id(cls, v):
        """Validate Microsoft Graph client ID format."""
        if not v:
            raise ValueError('CLIENT_ID is required')
        
        # Basic GUID format validation
        guid_pattern = re.compile(
            r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        )
        if not guid_pattern.match(v):
            raise ValueError('CLIENT_ID must be a valid GUID format')
        
        return v
    
    @field_validator('TENANT_ID')
    @classmethod
    def validate_tenant_id(cls, v):
        """Validate Microsoft Graph tenant ID format."""
        if not v:
            raise ValueError('TENANT_ID is required')
        
        # Can be GUID or domain name
        guid_pattern = re.compile(
            r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        )
        domain_pattern = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$')
        
        if not (guid_pattern.match(v) or domain_pattern.match(v) or v in ['common', 'organizations', 'consumers']):
            raise ValueError('TENANT_ID must be a valid GUID, domain name, or special value (common/organizations/consumers)')
        
        return v
    
    @field_validator('REDIRECT_URI')
    @classmethod
    def validate_redirect_uri(cls, v):
        """Validate redirect URI format."""
        if not v:
            raise ValueError('REDIRECT_URI is required')
        
        # Basic URL validation
        if not v.startswith(('http://', 'https://')):
            raise ValueError('REDIRECT_URI must be a valid HTTP/HTTPS URL')
        
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of: {", ".join(valid_levels)}')
        
        return v.upper()
    
    @field_validator('PORT')
    @classmethod
    def validate_port(cls, v):
        """Validate port number."""
        if not isinstance(v, int) or v < 1 or v > 65535:
            raise ValueError('PORT must be an integer between 1 and 65535')
        
        return v
    
    @field_validator('EXTERNAL_API_TIMEOUT')
    @classmethod
    def validate_timeout(cls, v):
        """Validate API timeout."""
        if v <= 0 or v > 300:  # Max 5 minutes
            raise ValueError('EXTERNAL_API_TIMEOUT must be between 1 and 300 seconds')
        
        return v
    
    @field_validator('EXTERNAL_API_RETRY_ATTEMPTS')
    @classmethod
    def validate_retry_attempts(cls, v):
        """Validate retry attempts."""
        if v < 0 or v > 10:
            raise ValueError('EXTERNAL_API_RETRY_ATTEMPTS must be between 0 and 10')
        
        return v
    
    @field_validator('ENCRYPTION_KEY')
    @classmethod
    def validate_encryption_key(cls, v):
        """Validate encryption key."""
        if v and len(v) < 32:
            raise ValueError('ENCRYPTION_KEY must be at least 32 characters long')
        
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v):
        """Validate Redis URL format."""
        if v and not v.startswith(('redis://', 'rediss://', 'memory://')):
            raise ValueError('REDIS_URL must start with redis://, rediss://, or memory://')
        
        return v
    
    @model_validator(mode='after')
    def validate_production_config(self):
        """Validate production-specific configuration."""
        environment = getattr(self, 'ENVIRONMENT', 'development')
        
        if environment == 'production':
            # Required fields for production
            required_fields = [
                'CLIENT_SECRET', 'ENCRYPTION_KEY', 'SENTRY_DSN'
            ]
            
            for field in required_fields:
                if not getattr(self, field, None):
                    raise ValueError(f'{field} is required in production environment')
            
            # Security validations for production
            if getattr(self, 'DEBUG', False):
                raise ValueError('DEBUG must be False in production')
            
            cors_origins = getattr(self, 'CORS_ORIGINS', [])
            if '*' in cors_origins:
                raise ValueError('CORS_ORIGINS cannot contain "*" in production')
            
            # Database validation
            database_url = getattr(self, 'DATABASE_URL', '')
            if 'sqlite' in database_url.lower():
                raise ValueError('SQLite cannot be used in production')
        
        return self
    
    @model_validator(mode='after')
    def validate_auth_config(self):
        """Validate authentication configuration."""
        # Check required OAuth fields
        oauth_fields = ['CLIENT_ID', 'TENANT_ID', 'CLIENT_SECRET', 'AUTHORITY']
        missing_fields = [field for field in oauth_fields if not getattr(self, field, None)]
        
        if missing_fields:
            raise ValueError(f'Missing required OAuth fields: {", ".join(missing_fields)}')
        
        # Validate authority URL format
        authority = getattr(self, 'AUTHORITY', '')
        if authority and not authority.startswith('https://login.microsoftonline.com/'):
            raise ValueError('AUTHORITY must be a valid Microsoft login URL')
        
        return self
    
    @model_validator(mode='after')
    def validate_cache_config(self):
        """Validate cache configuration."""
        cache_ttl = getattr(self, 'CACHE_DEFAULT_TTL', 3600)
        
        if cache_ttl <= 0 or cache_ttl > 86400:  # Max 24 hours
            raise ValueError('CACHE_DEFAULT_TTL must be between 1 and 86400 seconds')
        
        return self


def validate_environment_file(env_file_path: str = ".env") -> Dict[str, Any]:
    """
    Validate environment file exists and contains required variables.
    
    Args:
        env_file_path: Path to environment file
        
    Returns:
        Dictionary of validation results
    """
    validation_results = {
        "file_exists": False,
        "required_vars_present": [],
        "missing_vars": [],
        "warnings": [],
        "errors": []
    }
    
    # Check if file exists
    if not os.path.exists(env_file_path):
        validation_results["errors"].append(f"Environment file {env_file_path} not found")
        return validation_results
    
    validation_results["file_exists"] = True
    
    # Required environment variables
    required_vars = [
        'CLIENT_ID',
        'TENANT_ID', 
        'CLIENT_SECRET',
        'USER_ID',
        'AUTHORITY'
    ]
    
    # Read environment file
    try:
        with open(env_file_path, 'r') as f:
            env_content = f.read()
        
        # Check for required variables
        for var in required_vars:
            if f"{var}=" in env_content:
                validation_results["required_vars_present"].append(var)
            else:
                validation_results["missing_vars"].append(var)
        
        # Check for common issues
        if "CLIENT_SECRET=" in env_content and "your-client-secret" in env_content:
            validation_results["warnings"].append("CLIENT_SECRET appears to contain placeholder value")
        
        if "sqlite" in env_content.lower() and "ENVIRONMENT=production" in env_content:
            validation_results["errors"].append("SQLite database detected in production environment")
        
    except Exception as e:
        validation_results["errors"].append(f"Error reading environment file: {str(e)}")
    
    return validation_results


def get_config_summary(settings) -> Dict[str, Any]:
    """
    Get a summary of current configuration.
    
    Args:
        settings: Settings instance
        
    Returns:
        Configuration summary
    """
    return {
        "environment": settings.ENVIRONMENT,
        "debug_mode": settings.DEBUG,
        "database_type": "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql",
        "cache_enabled": bool(getattr(settings, 'REDIS_URL', None)),
        "external_api_configured": bool(settings.EXTERNAL_API_ENDPOINT),
        "encryption_enabled": bool(getattr(settings, 'ENCRYPTION_KEY', None)),
        "monitoring_enabled": bool(getattr(settings, 'SENTRY_DSN', None)),
        "cors_origins_count": len(settings.CORS_ORIGINS),
        "log_level": settings.LOG_LEVEL,
        "server_config": {
            "host": settings.HOST,
            "port": settings.PORT
        }
    }


def check_security_configuration(settings) -> List[str]:
    """
    Check security configuration and return warnings.
    
    Args:
        settings: Settings instance
        
    Returns:
        List of security warnings
    """
    warnings = []
    
    # Check debug mode in production
    if settings.ENVIRONMENT == "production" and settings.DEBUG:
        warnings.append("DEBUG mode is enabled in production")
    
    # Check CORS configuration
    if "*" in settings.CORS_ORIGINS and settings.ENVIRONMENT == "production":
        warnings.append("CORS allows all origins in production")
    
    # Check database configuration
    if "sqlite" in settings.DATABASE_URL and settings.ENVIRONMENT == "production":
        warnings.append("SQLite database used in production")
    
    # Check encryption
    if not getattr(settings, 'ENCRYPTION_KEY', None):
        warnings.append("No encryption key configured")
    
    # Check HTTPS
    if not settings.REDIRECT_URI.startswith('https://') and settings.ENVIRONMENT == "production":
        warnings.append("Redirect URI is not HTTPS in production")
    
    return warnings
