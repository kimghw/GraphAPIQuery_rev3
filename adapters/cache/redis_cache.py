"""Redis cache adapter implementation."""

import json
import logging
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError

from core.usecases.ports import CachePort
from core.exceptions import SystemException


logger = logging.getLogger(__name__)


class RedisCacheAdapter(CachePort):
    """Redis caching adapter implementation."""
    
    def __init__(self, redis_url: str, default_ttl: int = 3600):
        """
        Initialize Redis cache adapter.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._redis: Optional[redis.Redis] = None
        
        # Cache key prefixes
        self.prefixes = {
            "user": "user:",
            "token": "token:",
            "mail": "mail:",
            "webhook": "webhook:",
            "rate_limit": "rate_limit:",
            "health": "health:",
            "session": "session:"
        }
    
    async def connect(self):
        """Establish Redis connection."""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self._redis.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise SystemException(f"Redis connection failed: {str(e)}")
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed")
    
    async def _ensure_connected(self):
        """Ensure Redis connection is established."""
        if not self._redis:
            await self.connect()
    
    def _make_key(self, prefix: str, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.prefixes.get(prefix, prefix)}{key}"
    
    async def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            prefix: Key prefix type
            
        Returns:
            Cached value or None if not found
        """
        try:
            await self._ensure_connected()
            cache_key = self._make_key(prefix, key)
            
            cached_data = await self._redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get failed for key {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in cache get: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        prefix: str = ""
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            prefix: Key prefix type
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_connected()
            cache_key = self._make_key(prefix, key)
            ttl = ttl or self.default_ttl
            
            serialized_value = json.dumps(value, default=str)
            await self._redis.setex(cache_key, ttl, serialized_value)
            
            logger.debug(f"Cached value for key {cache_key} with TTL {ttl}")
            return True
            
        except (RedisError, json.JSONEncodeError) as e:
            logger.warning(f"Cache set failed for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in cache set: {str(e)}")
            return False
    
    async def delete(self, key: str, prefix: str = "") -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            prefix: Key prefix type
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_connected()
            cache_key = self._make_key(prefix, key)
            
            result = await self._redis.delete(cache_key)
            logger.debug(f"Deleted cache key {cache_key}, result: {result}")
            return result > 0
            
        except RedisError as e:
            logger.warning(f"Cache delete failed for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in cache delete: {str(e)}")
            return False
    
    async def exists(self, key: str, prefix: str = "") -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            prefix: Key prefix type
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            await self._ensure_connected()
            cache_key = self._make_key(prefix, key)
            
            result = await self._redis.exists(cache_key)
            return result > 0
            
        except RedisError as e:
            logger.warning(f"Cache exists check failed for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in cache exists: {str(e)}")
            return False
    
    async def get_ttl(self, key: str, prefix: str = "") -> Optional[int]:
        """
        Get TTL for a key.
        
        Args:
            key: Cache key
            prefix: Key prefix type
            
        Returns:
            TTL in seconds or None if key doesn't exist
        """
        try:
            await self._ensure_connected()
            cache_key = self._make_key(prefix, key)
            
            ttl = await self._redis.ttl(cache_key)
            return ttl if ttl > 0 else None
            
        except RedisError as e:
            logger.warning(f"Cache TTL check failed for key {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in cache TTL: {str(e)}")
            return None
    
    async def extend_ttl(self, key: str, ttl: int, prefix: str = "") -> bool:
        """
        Extend TTL for a key.
        
        Args:
            key: Cache key
            ttl: New TTL in seconds
            prefix: Key prefix type
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_connected()
            cache_key = self._make_key(prefix, key)
            
            result = await self._redis.expire(cache_key, ttl)
            return result
            
        except RedisError as e:
            logger.warning(f"Cache TTL extension failed for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in cache TTL extension: {str(e)}")
            return False
    
    # Specialized cache methods
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user information."""
        return await self.get(user_id, "user")
    
    async def set_user_info(
        self,
        user_id: str,
        user_info: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """Cache user information."""
        return await self.set(user_id, user_info, ttl, "user")
    
    async def invalidate_user_cache(self, user_id: str) -> bool:
        """Invalidate user cache."""
        return await self.delete(user_id, "user")
    
    async def get_token_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get cached token information."""
        return await self.get(account_id, "token")
    
    async def set_token_info(
        self,
        account_id: str,
        token_info: Dict[str, Any],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """Cache token information."""
        return await self.set(account_id, token_info, ttl, "token")
    
    async def invalidate_token_cache(self, account_id: str) -> bool:
        """Invalidate token cache."""
        return await self.delete(account_id, "token")
    
    async def get_mail_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached mail data."""
        return await self.get(cache_key, "mail")
    
    async def set_mail_cache(
        self,
        cache_key: str,
        mail_data: Dict[str, Any],
        ttl: int = 600  # 10 minutes
    ) -> bool:
        """Cache mail data."""
        return await self.set(cache_key, mail_data, ttl, "mail")
    
    async def get_webhook_cache(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Get cached webhook information."""
        return await self.get(webhook_id, "webhook")
    
    async def set_webhook_cache(
        self,
        webhook_id: str,
        webhook_info: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """Cache webhook information."""
        return await self.set(webhook_id, webhook_info, ttl, "webhook")
    
    # Rate limiting support
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> Dict[str, Any]:
        """
        Check rate limit for an identifier.
        
        Args:
            identifier: Rate limit identifier (e.g., user_id, ip_address)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Dict with rate limit status
        """
        try:
            await self._ensure_connected()
            key = self._make_key("rate_limit", identifier)
            
            # Use sliding window log approach
            now = datetime.utcnow().timestamp()
            window_start = now - window
            
            # Remove old entries
            await self._redis.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            current_count = await self._redis.zcard(key)
            
            # Check if limit exceeded
            if current_count >= limit:
                # Get oldest request time for reset calculation
                oldest = await self._redis.zrange(key, 0, 0, withscores=True)
                reset_time = int(oldest[0][1] + window) if oldest else int(now + window)
                
                return {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "retry_after": reset_time - int(now)
                }
            
            # Add current request
            await self._redis.zadd(key, {str(now): now})
            await self._redis.expire(key, window)
            
            return {
                "allowed": True,
                "limit": limit,
                "remaining": limit - current_count - 1,
                "reset_time": int(now + window),
                "retry_after": 0
            }
            
        except RedisError as e:
            logger.warning(f"Rate limit check failed for {identifier}: {str(e)}")
            # Fail open - allow request if Redis is down
            return {
                "allowed": True,
                "limit": limit,
                "remaining": limit - 1,
                "reset_time": int(datetime.utcnow().timestamp() + window),
                "retry_after": 0
            }
    
    # Health and monitoring
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get Redis health status."""
        try:
            await self._ensure_connected()
            
            # Test basic operations
            test_key = "health_check"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            # Test set/get/delete
            await self._redis.setex(test_key, 10, json.dumps(test_value))
            retrieved = await self._redis.get(test_key)
            await self._redis.delete(test_key)
            
            # Get Redis info
            info = await self._redis.info()
            
            return {
                "status": "healthy",
                "connected": True,
                "test_operations": "passed",
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed")
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            await self._ensure_connected()
            
            # Count keys by prefix
            stats = {}
            for prefix_name, prefix in self.prefixes.items():
                pattern = f"{prefix}*"
                keys = await self._redis.keys(pattern)
                stats[f"{prefix_name}_keys"] = len(keys)
            
            # Get Redis memory info
            info = await self._redis.info("memory")
            stats.update({
                "used_memory": info.get("used_memory"),
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak": info.get("used_memory_peak"),
                "used_memory_peak_human": info.get("used_memory_peak_human")
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {"error": str(e)}
    
    async def clear_cache(self, prefix: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            prefix: If specified, only clear keys with this prefix
            
        Returns:
            Number of keys deleted
        """
        try:
            await self._ensure_connected()
            
            if prefix:
                pattern = f"{self.prefixes.get(prefix, prefix)}*"
                keys = await self._redis.keys(pattern)
                if keys:
                    deleted = await self._redis.delete(*keys)
                    logger.info(f"Cleared {deleted} cache keys with prefix {prefix}")
                    return deleted
                return 0
            else:
                # Clear all cache (use with caution)
                await self._redis.flushdb()
                logger.warning("Cleared entire cache database")
                return -1  # Unknown count
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
            return 0


class InMemoryCacheAdapter(CachePort):
    """In-memory cache adapter for testing/development."""
    
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self):
        """No-op for in-memory cache."""
        pass
    
    async def disconnect(self):
        """Clear in-memory cache."""
        self._cache.clear()
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if "expires_at" not in entry:
            return False
        return datetime.utcnow() > entry["expires_at"]
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if self._is_expired(entry)
        ]
        for key in expired_keys:
            del self._cache[key]
    
    async def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """Get value from in-memory cache."""
        self._cleanup_expired()
        cache_key = f"{prefix}{key}"
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not self._is_expired(entry):
                return entry["value"]
            else:
                del self._cache[cache_key]
        
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        prefix: str = ""
    ) -> bool:
        """Set value in in-memory cache."""
        cache_key = f"{prefix}{key}"
        ttl = ttl or self.default_ttl
        
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        self._cache[cache_key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.utcnow()
        }
        
        return True
    
    async def delete(self, key: str, prefix: str = "") -> bool:
        """Delete value from in-memory cache."""
        cache_key = f"{prefix}{key}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            return True
        return False
    
    async def exists(self, key: str, prefix: str = "") -> bool:
        """Check if key exists in in-memory cache."""
        self._cleanup_expired()
        cache_key = f"{prefix}{key}"
        return cache_key in self._cache
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get in-memory cache health status."""
        self._cleanup_expired()
        return {
            "status": "healthy",
            "type": "in_memory",
            "total_keys": len(self._cache),
            "memory_usage": "unknown"
        }


def create_cache_adapter(cache_url: str, default_ttl: int = 3600) -> CachePort:
    """
    Create appropriate cache adapter based on URL.
    
    Args:
        cache_url: Cache connection URL
        default_ttl: Default TTL in seconds
        
    Returns:
        Cache adapter instance
    """
    if cache_url.startswith("redis://") or cache_url.startswith("rediss://"):
        return RedisCacheAdapter(cache_url, default_ttl)
    elif cache_url == "memory://":
        return InMemoryCacheAdapter(default_ttl)
    else:
        raise ValueError(f"Unsupported cache URL: {cache_url}")
