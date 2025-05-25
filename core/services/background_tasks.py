"""Background task management service."""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from core.usecases.auth_usecases import AuthenticationUseCases
from core.usecases.mail_usecases import MailUseCases
from core.exceptions import SystemException, BusinessException
from adapters.monitoring.metrics import get_metrics_collector


logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Background task status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskInfo:
    """Background task information."""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BackgroundTaskService:
    """Background task management service."""
    
    def __init__(
        self,
        mail_usecases: MailUseCases,
        auth_usecases: AuthenticationUseCases,
        metrics_collector=None
    ):
        self.mail_usecases = mail_usecases
        self.auth_usecases = auth_usecases
        self.metrics_collector = metrics_collector
        
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}
        self.task_info: Dict[str, TaskInfo] = {}
        
        # Task intervals (in seconds)
        self.intervals = {
            "token_refresh": 60,      # Check every minute
            "webhook_renewal": 300,   # Check every 5 minutes
            "failed_api_retry": 120,  # Check every 2 minutes
            "cleanup": 3600,          # Check every hour
            "health_check": 300       # Check every 5 minutes
        }
    
    async def start(self):
        """Start all background tasks."""
        if self.running:
            logger.warning("Background tasks already running")
            return
        
        self.running = True
        logger.info("Starting background task service")
        
        # Start individual tasks
        task_configs = [
            ("token_refresh", self._token_refresh_task),
            ("webhook_renewal", self._webhook_renewal_task),
            ("failed_api_retry", self._failed_api_retry_task),
            ("cleanup", self._cleanup_task),
            ("health_check", self._health_check_task)
        ]
        
        for task_type, task_func in task_configs:
            task_id = f"{task_type}_{datetime.utcnow().isoformat()}"
            
            # Create task info
            self.task_info[task_id] = TaskInfo(
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow()
            )
            
            # Start task
            task = asyncio.create_task(self._run_periodic_task(task_id, task_func))
            self.tasks[task_id] = task
            
            logger.info(f"Started background task: {task_type}")
        
        # Update metrics
        if self.metrics_collector:
            self.metrics_collector.set_background_tasks("total", len(self.tasks))
        
        logger.info(f"Background task service started with {len(self.tasks)} tasks")
    
    async def stop(self):
        """Stop all background tasks."""
        if not self.running:
            logger.warning("Background tasks not running")
            return
        
        self.running = False
        logger.info("Stopping background task service")
        
        # Cancel all tasks
        for task_id, task in self.tasks.items():
            if not task.done():
                task.cancel()
                self.task_info[task_id].status = TaskStatus.CANCELLED
                self.task_info[task_id].completed_at = datetime.utcnow()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        
        self.tasks.clear()
        
        # Update metrics
        if self.metrics_collector:
            self.metrics_collector.set_background_tasks("total", 0)
        
        logger.info("Background task service stopped")
    
    async def _run_periodic_task(self, task_id: str, task_func: Callable):
        """Run a periodic task with error handling."""
        task_info = self.task_info[task_id]
        task_info.status = TaskStatus.RUNNING
        task_info.started_at = datetime.utcnow()
        
        interval = self.intervals.get(task_info.task_type, 300)
        
        try:
            while self.running:
                try:
                    await task_func()
                    
                    # Update metrics on successful execution
                    if self.metrics_collector:
                        self.metrics_collector.set_background_tasks(
                            task_info.task_type, 1
                        )
                    
                except Exception as e:
                    logger.error(
                        f"Error in background task {task_info.task_type}: {str(e)}",
                        exc_info=True
                    )
                    
                    # Record error in metrics
                    if self.metrics_collector:
                        self.metrics_collector.record_error(
                            error_type=type(e).__name__,
                            component="background_task"
                        )
                    
                    # Don't stop the task for individual errors
                    task_info.error = str(e)
                
                # Wait for next iteration
                await asyncio.sleep(interval)
                
        except asyncio.CancelledError:
            logger.info(f"Background task {task_info.task_type} cancelled")
            task_info.status = TaskStatus.CANCELLED
        except Exception as e:
            logger.error(
                f"Fatal error in background task {task_info.task_type}: {str(e)}",
                exc_info=True
            )
            task_info.status = TaskStatus.FAILED
            task_info.error = str(e)
        finally:
            task_info.completed_at = datetime.utcnow()
    
    async def _token_refresh_task(self):
        """Automatically refresh expiring tokens."""
        try:
            # Get tokens expiring in the next 5 minutes
            expiring_tokens = await self.auth_usecases.get_expiring_tokens(
                minutes_before=5
            )
            
            if not expiring_tokens:
                logger.debug("No tokens require refresh")
                return
            
            logger.info(f"Found {len(expiring_tokens)} tokens requiring refresh")
            
            refresh_results = {"success": 0, "failed": 0}
            
            for token in expiring_tokens:
                try:
                    await self.auth_usecases.refresh_token(token.account_id)
                    refresh_results["success"] += 1
                    
                    # Record successful refresh
                    if self.metrics_collector:
                        self.metrics_collector.record_token_refresh("success")
                    
                    logger.debug(f"Successfully refreshed token for account {token.account_id}")
                    
                except Exception as e:
                    refresh_results["failed"] += 1
                    
                    # Record failed refresh
                    if self.metrics_collector:
                        self.metrics_collector.record_token_refresh("failed")
                    
                    logger.error(
                        f"Failed to refresh token for account {token.account_id}: {str(e)}"
                    )
            
            logger.info(
                f"Token refresh completed: {refresh_results['success']} success, "
                f"{refresh_results['failed']} failed"
            )
            
        except Exception as e:
            logger.error(f"Token refresh task failed: {str(e)}", exc_info=True)
            raise
    
    async def _webhook_renewal_task(self):
        """Automatically renew expiring webhook subscriptions."""
        try:
            # Get webhook subscriptions expiring in the next 30 minutes
            expiring_webhooks = await self.mail_usecases.get_expiring_webhooks(
                minutes_before=30
            )
            
            if not expiring_webhooks:
                logger.debug("No webhook subscriptions require renewal")
                return
            
            logger.info(f"Found {len(expiring_webhooks)} webhook subscriptions requiring renewal")
            
            renewal_results = {"success": 0, "failed": 0}
            
            for webhook in expiring_webhooks:
                try:
                    await self.mail_usecases.renew_webhook_subscription(
                        webhook.account_id,
                        webhook.subscription_id
                    )
                    renewal_results["success"] += 1
                    
                    logger.debug(
                        f"Successfully renewed webhook subscription {webhook.subscription_id} "
                        f"for account {webhook.account_id}"
                    )
                    
                except Exception as e:
                    renewal_results["failed"] += 1
                    
                    logger.error(
                        f"Failed to renew webhook subscription {webhook.subscription_id} "
                        f"for account {webhook.account_id}: {str(e)}"
                    )
            
            # Update webhook metrics
            if self.metrics_collector:
                active_webhooks = await self.mail_usecases.get_active_webhook_count()
                self.metrics_collector.set_webhook_subscriptions(active_webhooks)
            
            logger.info(
                f"Webhook renewal completed: {renewal_results['success']} success, "
                f"{renewal_results['failed']} failed"
            )
            
        except Exception as e:
            logger.error(f"Webhook renewal task failed: {str(e)}", exc_info=True)
            raise
    
    async def _failed_api_retry_task(self):
        """Retry failed external API calls."""
        try:
            # Get failed API calls that are ready for retry
            failed_calls = await self.mail_usecases.get_failed_api_calls_for_retry()
            
            if not failed_calls:
                logger.debug("No failed API calls require retry")
                return
            
            logger.info(f"Found {len(failed_calls)} failed API calls for retry")
            
            retry_results = {"success": 0, "failed": 0, "skipped": 0}
            
            for failed_call in failed_calls:
                try:
                    # Check if retry limit exceeded
                    if failed_call.retry_count >= 5:  # Max 5 retries
                        retry_results["skipped"] += 1
                        logger.warning(
                            f"Skipping retry for API call {failed_call.id}: "
                            f"retry limit exceeded ({failed_call.retry_count})"
                        )
                        continue
                    
                    # Retry the API call
                    await self.mail_usecases.retry_failed_api_call(failed_call.id)
                    retry_results["success"] += 1
                    
                    logger.debug(f"Successfully retried API call {failed_call.id}")
                    
                except Exception as e:
                    retry_results["failed"] += 1
                    
                    logger.error(
                        f"Failed to retry API call {failed_call.id}: {str(e)}"
                    )
            
            logger.info(
                f"API retry completed: {retry_results['success']} success, "
                f"{retry_results['failed']} failed, {retry_results['skipped']} skipped"
            )
            
        except Exception as e:
            logger.error(f"Failed API retry task failed: {str(e)}", exc_info=True)
            raise
    
    async def _cleanup_task(self):
        """Clean up old data and temporary files."""
        try:
            cleanup_results = {
                "old_tokens": 0,
                "old_logs": 0,
                "temp_files": 0,
                "old_webhooks": 0
            }
            
            # Clean up expired tokens (older than 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            deleted_tokens = await self.auth_usecases.cleanup_expired_tokens(cutoff_date)
            cleanup_results["old_tokens"] = deleted_tokens
            
            # Clean up old mail logs (older than 90 days)
            log_cutoff_date = datetime.utcnow() - timedelta(days=90)
            deleted_logs = await self.mail_usecases.cleanup_old_mail_logs(log_cutoff_date)
            cleanup_results["old_logs"] = deleted_logs
            
            # Clean up old webhook subscriptions (inactive for 7 days)
            webhook_cutoff_date = datetime.utcnow() - timedelta(days=7)
            deleted_webhooks = await self.mail_usecases.cleanup_inactive_webhooks(webhook_cutoff_date)
            cleanup_results["old_webhooks"] = deleted_webhooks
            
            # Clean up temporary files
            import os
            import glob
            temp_files_deleted = 0
            
            for pattern in ["*.tmp", "*.temp", "*.log.old"]:
                for file_path in glob.glob(pattern):
                    try:
                        if os.path.isfile(file_path):
                            file_age = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if file_age < cutoff_date:
                                os.remove(file_path)
                                temp_files_deleted += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {file_path}: {str(e)}")
            
            cleanup_results["temp_files"] = temp_files_deleted
            
            logger.info(
                f"Cleanup completed: {cleanup_results['old_tokens']} tokens, "
                f"{cleanup_results['old_logs']} logs, "
                f"{cleanup_results['temp_files']} temp files, "
                f"{cleanup_results['old_webhooks']} webhooks"
            )
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {str(e)}", exc_info=True)
            raise
    
    async def _health_check_task(self):
        """Perform periodic health checks."""
        try:
            # Check system health
            health_status = await self._check_system_health()
            
            # Log health status
            if health_status["status"] == "healthy":
                logger.debug("System health check: All systems operational")
            elif health_status["status"] == "degraded":
                logger.warning(f"System health check: Degraded - {health_status.get('issues', [])}")
            else:
                logger.error(f"System health check: Unhealthy - {health_status.get('issues', [])}")
            
            # Update health metrics
            if self.metrics_collector:
                for component, status in health_status.get("components", {}).items():
                    if status != "healthy":
                        self.metrics_collector.record_error(
                            error_type="health_check_failed",
                            component=component
                        )
            
        except Exception as e:
            logger.error(f"Health check task failed: {str(e)}", exc_info=True)
            raise
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        health_status = {
            "status": "healthy",
            "components": {},
            "issues": []
        }
        
        try:
            # Check database connectivity
            db_healthy = await self.auth_usecases.check_database_health()
            health_status["components"]["database"] = "healthy" if db_healthy else "unhealthy"
            if not db_healthy:
                health_status["issues"].append("Database connectivity issues")
            
            # Check external API connectivity
            api_healthy = await self.mail_usecases.check_graph_api_health()
            health_status["components"]["graph_api"] = "healthy" if api_healthy else "unhealthy"
            if not api_healthy:
                health_status["issues"].append("Graph API connectivity issues")
            
            # Determine overall status
            if health_status["issues"]:
                if len(health_status["issues"]) == 1:
                    health_status["status"] = "degraded"
                else:
                    health_status["status"] = "unhealthy"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["issues"].append(f"Health check error: {str(e)}")
        
        return health_status
    
    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all background tasks."""
        return {
            "running": self.running,
            "total_tasks": len(self.tasks),
            "task_details": {
                task_id: {
                    "task_type": info.task_type,
                    "status": info.status.value,
                    "created_at": info.created_at.isoformat(),
                    "started_at": info.started_at.isoformat() if info.started_at else None,
                    "completed_at": info.completed_at.isoformat() if info.completed_at else None,
                    "error": info.error,
                    "metadata": info.metadata
                }
                for task_id, info in self.task_info.items()
            }
        }
    
    def get_task_summary(self) -> Dict[str, Any]:
        """Get summary of background task status."""
        status_counts = {}
        for info in self.task_info.values():
            status_counts[info.status.value] = status_counts.get(info.status.value, 0) + 1
        
        return {
            "running": self.running,
            "total_tasks": len(self.task_info),
            "status_counts": status_counts,
            "intervals": self.intervals
        }


def create_background_task_service(
    mail_usecases: MailUseCases,
    auth_usecases: AuthenticationUseCases,
    metrics_collector=None
) -> BackgroundTaskService:
    """Create background task service instance."""
    return BackgroundTaskService(
        mail_usecases=mail_usecases,
        auth_usecases=auth_usecases,
        metrics_collector=metrics_collector
    )
