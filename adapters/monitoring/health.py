"""Comprehensive health check system."""

import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import httpx
from sqlalchemy import text

from config.environments import EnhancedSettings
from adapters.db.database import DatabaseAdapter
from core.exceptions import DatabaseConnectionException, ExternalAPIException


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Individual component health information."""
    
    def __init__(
        self,
        status: HealthStatus,
        response_time_ms: Optional[float] = None,
        details: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.status = status
        self.response_time_ms = response_time_ms
        self.details = details
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "status": self.status.value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.response_time_ms is not None:
            result["response_time_ms"] = round(self.response_time_ms, 2)
        
        if self.details:
            result["details"] = self.details
        
        if self.error:
            result["error"] = self.error
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result


class HealthChecker:
    """Comprehensive health checker for all system components."""
    
    def __init__(self, settings: EnhancedSettings):
        self.settings = settings
        self.db_adapter = DatabaseAdapter(settings)
    
    async def check_all(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check of all components.
        
        Returns:
            Complete health check report
        """
        start_time = time.time()
        
        # Run all health checks concurrently
        checks = await asyncio.gather(
            self._check_database(),
            self._check_graph_api(),
            self._check_external_api(),
            self._check_redis() if self.settings.CACHE_ENABLED else self._skip_check("redis", "Cache disabled"),
            self._check_disk_space(),
            self._check_memory(),
            return_exceptions=True
        )
        
        # Process results
        check_names = ["database", "graph_api", "external_api", "redis", "disk", "memory"]
        health_checks = {}
        
        for i, check in enumerate(checks):
            if isinstance(check, Exception):
                health_checks[check_names[i]] = ComponentHealth(
                    status=HealthStatus.UNHEALTHY,
                    error=str(check)
                ).to_dict()
            else:
                health_checks[check_names[i]] = check.to_dict()
        
        # Determine overall status
        overall_status = self._determine_overall_status(health_checks)
        
        # Calculate total check time
        total_time_ms = (time.time() - start_time) * 1000
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "version": self.settings.APP_VERSION,
            "environment": self.settings.ENVIRONMENT,
            "total_check_time_ms": round(total_time_ms, 2),
            "checks": health_checks,
            "summary": self._generate_summary(health_checks)
        }
    
    async def _check_database(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        start_time = time.time()
        
        try:
            async with self.db_adapter.session_scope() as session:
                # Test basic connectivity
                await session.execute(text("SELECT 1"))
                
                # Test table existence (basic schema check)
                result = await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
                )
                tables = result.fetchall()
                
                response_time = (time.time() - start_time) * 1000
                
                if not tables:
                    return ComponentHealth(
                        status=HealthStatus.DEGRADED,
                        response_time_ms=response_time,
                        details="Database connected but schema may be incomplete",
                        metadata={"tables_found": len(tables)}
                    )
                
                return ComponentHealth(
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    details="Database connection successful",
                    metadata={
                        "database_type": "sqlite" if "sqlite" in self.settings.DATABASE_URL else "postgresql",
                        "tables_found": len(tables)
                    }
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=f"Database connection failed: {str(e)}",
                metadata={"database_url": self.settings.DATABASE_URL.split("@")[-1] if "@" in self.settings.DATABASE_URL else self.settings.DATABASE_URL}
            )
    
    async def _check_graph_api(self) -> ComponentHealth:
        """Check Microsoft Graph API connectivity."""
        start_time = time.time()
        
        try:
            # Test Graph API endpoint accessibility
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.settings.GRAPH_API_ENDPOINT}/$metadata",
                    headers={"Accept": "application/xml"}
                )
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return ComponentHealth(
                        status=HealthStatus.HEALTHY,
                        response_time_ms=response_time,
                        details="Graph API endpoint accessible",
                        metadata={
                            "endpoint": self.settings.GRAPH_API_ENDPOINT,
                            "status_code": response.status_code
                        }
                    )
                else:
                    return ComponentHealth(
                        status=HealthStatus.DEGRADED,
                        response_time_ms=response_time,
                        details=f"Graph API returned status {response.status_code}",
                        metadata={
                            "endpoint": self.settings.GRAPH_API_ENDPOINT,
                            "status_code": response.status_code
                        }
                    )
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=f"Graph API check failed: {str(e)}",
                metadata={"endpoint": self.settings.GRAPH_API_ENDPOINT}
            )
    
    async def _check_external_api(self) -> ComponentHealth:
        """Check external API connectivity."""
        if not self.settings.EXTERNAL_API_ENDPOINT:
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                details="External API not configured",
                metadata={"configured": False}
            )
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.settings.EXTERNAL_API_TIMEOUT) as client:
                # Try to reach the external API endpoint
                response = await client.get(
                    self.settings.EXTERNAL_API_ENDPOINT,
                    headers={"User-Agent": "GraphAPIMailSystem-HealthCheck/1.0"}
                )
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code < 500:
                    return ComponentHealth(
                        status=HealthStatus.HEALTHY,
                        response_time_ms=response_time,
                        details="External API accessible",
                        metadata={
                            "endpoint": self.settings.EXTERNAL_API_ENDPOINT,
                            "status_code": response.status_code
                        }
                    )
                else:
                    return ComponentHealth(
                        status=HealthStatus.DEGRADED,
                        response_time_ms=response_time,
                        details=f"External API returned server error {response.status_code}",
                        metadata={
                            "endpoint": self.settings.EXTERNAL_API_ENDPOINT,
                            "status_code": response.status_code
                        }
                    )
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=f"External API check failed: {str(e)}",
                metadata={"endpoint": self.settings.EXTERNAL_API_ENDPOINT}
            )
    
    async def _check_redis(self) -> ComponentHealth:
        """Check Redis connectivity."""
        if self.settings.CACHE_BACKEND != "redis":
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                details="Redis not configured",
                metadata={"backend": self.settings.CACHE_BACKEND}
            )
        
        start_time = time.time()
        
        try:
            import redis.asyncio as redis
            
            redis_client = redis.from_url(self.settings.REDIS_URL)
            
            # Test basic connectivity
            await redis_client.ping()
            
            # Test set/get operation
            test_key = "health_check_test"
            await redis_client.set(test_key, "test_value", ex=10)
            value = await redis_client.get(test_key)
            await redis_client.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            if value == b"test_value":
                return ComponentHealth(
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    details="Redis connection and operations successful",
                    metadata={"redis_url": self.settings.REDIS_URL.split("@")[-1] if "@" in self.settings.REDIS_URL else self.settings.REDIS_URL}
                )
            else:
                return ComponentHealth(
                    status=HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    details="Redis connected but operations failed",
                    metadata={"redis_url": self.settings.REDIS_URL.split("@")[-1] if "@" in self.settings.REDIS_URL else self.settings.REDIS_URL}
                )
                
        except ImportError:
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                error="Redis client not installed",
                metadata={"redis_url": self.settings.REDIS_URL}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=f"Redis check failed: {str(e)}",
                metadata={"redis_url": self.settings.REDIS_URL.split("@")[-1] if "@" in self.settings.REDIS_URL else self.settings.REDIS_URL}
            )
    
    async def _check_disk_space(self) -> ComponentHealth:
        """Check available disk space."""
        start_time = time.time()
        
        try:
            import shutil
            
            # Check disk space for current directory
            total, used, free = shutil.disk_usage(".")
            
            # Convert to GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            usage_percent = (used / total) * 100
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on free space
            if free_gb < 1.0:  # Less than 1GB free
                status = HealthStatus.UNHEALTHY
                details = f"Critical: Only {free_gb:.2f}GB free space remaining"
            elif usage_percent > 90:  # More than 90% used
                status = HealthStatus.DEGRADED
                details = f"Warning: Disk usage at {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                details = f"Disk usage: {usage_percent:.1f}% ({free_gb:.2f}GB free)"
            
            return ComponentHealth(
                status=status,
                response_time_ms=response_time,
                details=details,
                metadata={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "usage_percent": round(usage_percent, 1)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=f"Disk space check failed: {str(e)}"
            )
    
    async def _check_memory(self) -> ComponentHealth:
        """Check memory usage."""
        start_time = time.time()
        
        try:
            import psutil
            
            # Get memory information
            memory = psutil.virtual_memory()
            
            # Convert to GB
            total_gb = memory.total / (1024**3)
            available_gb = memory.available / (1024**3)
            used_gb = memory.used / (1024**3)
            usage_percent = memory.percent
            
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on memory usage
            if usage_percent > 95:
                status = HealthStatus.UNHEALTHY
                details = f"Critical: Memory usage at {usage_percent:.1f}%"
            elif usage_percent > 85:
                status = HealthStatus.DEGRADED
                details = f"Warning: Memory usage at {usage_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                details = f"Memory usage: {usage_percent:.1f}% ({available_gb:.2f}GB available)"
            
            return ComponentHealth(
                status=status,
                response_time_ms=response_time,
                details=details,
                metadata={
                    "total_gb": round(total_gb, 2),
                    "used_gb": round(used_gb, 2),
                    "available_gb": round(available_gb, 2),
                    "usage_percent": round(usage_percent, 1)
                }
            )
            
        except ImportError:
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                details="Memory monitoring not available (psutil not installed)",
                metadata={"monitoring_available": False}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time,
                error=f"Memory check failed: {str(e)}"
            )
    
    async def _skip_check(self, component: str, reason: str) -> ComponentHealth:
        """Return a skipped check result."""
        return ComponentHealth(
            status=HealthStatus.HEALTHY,
            details=f"{component.title()} check skipped: {reason}",
            metadata={"skipped": True, "reason": reason}
        )
    
    def _determine_overall_status(self, checks: Dict[str, Dict[str, Any]]) -> HealthStatus:
        """Determine overall system health status."""
        statuses = [check["status"] for check in checks.values()]
        
        # If any component is unhealthy, system is unhealthy
        if HealthStatus.UNHEALTHY.value in statuses:
            return HealthStatus.UNHEALTHY
        
        # If any component is degraded, system is degraded
        if HealthStatus.DEGRADED.value in statuses:
            return HealthStatus.DEGRADED
        
        # All components are healthy
        return HealthStatus.HEALTHY
    
    def _generate_summary(self, checks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of health check results."""
        total_checks = len(checks)
        healthy_count = sum(1 for check in checks.values() if check["status"] == HealthStatus.HEALTHY.value)
        degraded_count = sum(1 for check in checks.values() if check["status"] == HealthStatus.DEGRADED.value)
        unhealthy_count = sum(1 for check in checks.values() if check["status"] == HealthStatus.UNHEALTHY.value)
        
        # Calculate average response time (excluding skipped checks)
        response_times = [
            check.get("response_time_ms", 0) 
            for check in checks.values() 
            if "response_time_ms" in check
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_checks": total_checks,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "average_response_time_ms": round(avg_response_time, 2),
            "health_score": round((healthy_count / total_checks) * 100, 1)
        }


async def create_health_checker(settings: EnhancedSettings) -> HealthChecker:
    """Create health checker instance."""
    return HealthChecker(settings)
