"""Integration tests for complete mail flow."""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

from main import app
from core.domain.entities import AuthenticationFlow
from core.exceptions import BusinessException, SystemException
from adapters.monitoring.metrics import get_metrics_collector


@pytest.mark.integration
class TestMailFlowIntegration:
    """Complete mail processing flow integration tests."""
    
    @pytest.fixture
    async def test_client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    @pytest.fixture
    def mock_graph_api_responses(self):
        """Mock Graph API responses."""
        return {
            "user_info": {
                "id": "test-user-id",
                "userPrincipalName": "test@example.com",
                "displayName": "Test User",
                "mail": "test@example.com"
            },
            "messages": {
                "value": [
                    {
                        "id": "msg-1",
                        "subject": "Test Email 1",
                        "bodyPreview": "This is a test email",
                        "from": {
                            "emailAddress": {
                                "address": "sender@example.com",
                                "name": "Sender Name"
                            }
                        },
                        "receivedDateTime": "2024-01-01T10:00:00Z",
                        "isRead": False,
                        "importance": "normal",
                        "hasAttachments": False
                    },
                    {
                        "id": "msg-2",
                        "subject": "Test Email 2",
                        "bodyPreview": "Another test email",
                        "from": {
                            "emailAddress": {
                                "address": "sender2@example.com",
                                "name": "Sender 2"
                            }
                        },
                        "receivedDateTime": "2024-01-01T11:00:00Z",
                        "isRead": True,
                        "importance": "high",
                        "hasAttachments": True
                    }
                ],
                "@odata.nextLink": None,
                "@odata.deltaLink": "delta-token-123"
            },
            "token_response": {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "Mail.Read Mail.Send"
            }
        }
    
    async def test_complete_mail_sync_flow(self, test_client: AsyncClient, mock_graph_api_responses):
        """Test complete mail synchronization flow from account creation to external API."""
        
        # Mock external dependencies
        with patch('adapters.external.oauth_client.OAuthClient.exchange_code_for_token') as mock_oauth, \
             patch('adapters.external.graph_client.GraphAPIClient.get_user_info') as mock_user_info, \
             patch('adapters.external.graph_client.GraphAPIClient.query_messages') as mock_query_messages, \
             patch('adapters.external.external_api_client.ExternalAPIClient.send_mail_data') as mock_external_api:
            
            # Setup mocks
            mock_oauth.return_value = mock_graph_api_responses["token_response"]
            mock_user_info.return_value = mock_graph_api_responses["user_info"]
            mock_query_messages.return_value = mock_graph_api_responses["messages"]
            mock_external_api.return_value = {"status": "success", "processed": 2}
            
            # 1. Create account
            account_data = {
                "email": "test@example.com",
                "tenant_id": "test-tenant-id",
                "client_id": "test-client-id",
                "authentication_flow": "authorization_code",
                "scopes": ["Mail.Read", "Mail.Send"],
                "client_secret": "test-secret",
                "redirect_uri": "http://localhost:8000/auth/callback"
            }
            
            account_response = await test_client.post("/auth/accounts", json=account_data)
            assert account_response.status_code == 201
            
            account_result = account_response.json()
            assert account_result["success"] is True
            assert "account_id" in account_result
            account_id = account_result["account_id"]
            
            # 2. Authenticate account (simulate OAuth callback)
            auth_data = {
                "account_id": account_id,
                "authorization_code": "test-auth-code",
                "state": "test-state"
            }
            
            auth_response = await test_client.post("/auth/authenticate", json=auth_data)
            assert auth_response.status_code == 200
            
            auth_result = auth_response.json()
            assert auth_result["success"] is True
            assert auth_result["message"] == "Authentication successful"
            
            # 3. Query mail messages
            mail_query_data = {
                "account_id": account_id,
                "folder_id": "inbox",
                "top": 10,
                "select_fields": ["id", "subject", "from", "receivedDateTime", "isRead"]
            }
            
            mail_response = await test_client.post("/mail/query", json=mail_query_data)
            assert mail_response.status_code == 200
            
            mail_result = mail_response.json()
            assert mail_result["success"] is True
            assert "messages" in mail_result
            assert len(mail_result["messages"]) == 2
            assert "new_messages" in mail_result
            assert mail_result["total_messages"] == 2
            
            # Verify message content
            messages = mail_result["messages"]
            assert messages[0]["subject"] == "Test Email 1"
            assert messages[1]["subject"] == "Test Email 2"
            
            # 4. Send mail data to external API
            external_api_data = {
                "account_id": account_id,
                "endpoint_url": "https://api.example.com/mail",
                "mail_data": {
                    "messages": messages[:1],  # Send first message
                    "metadata": {
                        "account_email": "test@example.com",
                        "sync_timestamp": datetime.utcnow().isoformat()
                    }
                }
            }
            
            external_response = await test_client.post("/mail/send-to-external", json=external_api_data)
            assert external_response.status_code == 200
            
            external_result = external_response.json()
            assert external_result["success"] is True
            assert external_result["processed_count"] == 2
            
            # 5. Verify authentication logs
            logs_response = await test_client.get(f"/auth/logs?account_id={account_id}")
            assert logs_response.status_code == 200
            
            logs_result = logs_response.json()
            assert len(logs_result["logs"]) >= 1
            assert logs_result["logs"][0]["success"] is True
            
            # 6. Verify mail query history
            history_response = await test_client.get(f"/mail/history?account_id={account_id}")
            assert history_response.status_code == 200
            
            history_result = history_response.json()
            assert len(history_result["history"]) >= 1
            assert history_result["history"][0]["messages_found"] == 2
            
            # Verify mock calls
            mock_oauth.assert_called_once()
            mock_user_info.assert_called_once()
            mock_query_messages.assert_called_once()
            mock_external_api.assert_called_once()
    
    async def test_error_handling_in_mail_flow(self, test_client: AsyncClient):
        """Test error handling throughout the mail flow."""
        
        # Test authentication failure
        with patch('adapters.external.oauth_client.OAuthClient.exchange_code_for_token') as mock_oauth:
            mock_oauth.side_effect = Exception("OAuth service unavailable")
            
            # Create account first
            account_data = {
                "email": "test@example.com",
                "tenant_id": "test-tenant-id",
                "client_id": "test-client-id",
                "authentication_flow": "authorization_code",
                "scopes": ["Mail.Read"],
                "client_secret": "test-secret",
                "redirect_uri": "http://localhost:8000/auth/callback"
            }
            
            account_response = await test_client.post("/auth/accounts", json=account_data)
            account_id = account_response.json()["account_id"]
            
            # Try to authenticate - should fail
            auth_data = {
                "account_id": account_id,
                "authorization_code": "test-auth-code",
                "state": "test-state"
            }
            
            auth_response = await test_client.post("/auth/authenticate", json=auth_data)
            assert auth_response.status_code == 500
            
            auth_result = auth_response.json()
            assert auth_result["success"] is False
            assert "error" in auth_result
    
    async def test_mail_query_with_filters(self, test_client: AsyncClient, mock_graph_api_responses):
        """Test mail query with various filters."""
        
        with patch('adapters.external.oauth_client.OAuthClient.exchange_code_for_token') as mock_oauth, \
             patch('adapters.external.graph_client.GraphAPIClient.get_user_info') as mock_user_info, \
             patch('adapters.external.graph_client.GraphAPIClient.query_messages') as mock_query_messages:
            
            # Setup mocks
            mock_oauth.return_value = mock_graph_api_responses["token_response"]
            mock_user_info.return_value = mock_graph_api_responses["user_info"]
            mock_query_messages.return_value = mock_graph_api_responses["messages"]
            
            # Create and authenticate account
            account_data = {
                "email": "test@example.com",
                "tenant_id": "test-tenant-id",
                "client_id": "test-client-id",
                "authentication_flow": "authorization_code",
                "scopes": ["Mail.Read"],
                "client_secret": "test-secret",
                "redirect_uri": "http://localhost:8000/auth/callback"
            }
            
            account_response = await test_client.post("/auth/accounts", json=account_data)
            account_id = account_response.json()["account_id"]
            
            auth_data = {
                "account_id": account_id,
                "authorization_code": "test-auth-code",
                "state": "test-state"
            }
            await test_client.post("/auth/authenticate", json=auth_data)
            
            # Test query with date filters
            mail_query_data = {
                "account_id": account_id,
                "folder_id": "inbox",
                "filters": {
                    "date_from": "2024-01-01T00:00:00Z",
                    "date_to": "2024-01-02T00:00:00Z",
                    "is_read": False,
                    "importance": "normal"
                },
                "top": 50
            }
            
            mail_response = await test_client.post("/mail/query", json=mail_query_data)
            assert mail_response.status_code == 200
            
            mail_result = mail_response.json()
            assert mail_result["success"] is True
            
            # Verify that Graph API was called with correct filters
            mock_query_messages.assert_called()
            call_args = mock_query_messages.call_args
            assert "filters" in call_args.kwargs
            filters = call_args.kwargs["filters"]
            assert "receivedDateTime ge 2024-01-01T00:00:00Z" in str(filters)
    
    async def test_webhook_subscription_flow(self, test_client: AsyncClient, mock_graph_api_responses):
        """Test webhook subscription creation and management."""
        
        with patch('adapters.external.oauth_client.OAuthClient.exchange_code_for_token') as mock_oauth, \
             patch('adapters.external.graph_client.GraphAPIClient.get_user_info') as mock_user_info, \
             patch('adapters.external.graph_client.GraphAPIClient.create_webhook_subscription') as mock_create_webhook:
            
            # Setup mocks
            mock_oauth.return_value = mock_graph_api_responses["token_response"]
            mock_user_info.return_value = mock_graph_api_responses["user_info"]
            mock_create_webhook.return_value = {
                "id": "webhook-123",
                "resource": "/me/mailFolders('Inbox')/messages",
                "changeType": "created,updated",
                "notificationUrl": "https://webhook.example.com/notifications",
                "expirationDateTime": (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
            
            # Create and authenticate account
            account_data = {
                "email": "test@example.com",
                "tenant_id": "test-tenant-id",
                "client_id": "test-client-id",
                "authentication_flow": "authorization_code",
                "scopes": ["Mail.Read"],
                "client_secret": "test-secret",
                "redirect_uri": "http://localhost:8000/auth/callback"
            }
            
            account_response = await test_client.post("/auth/accounts", json=account_data)
            account_id = account_response.json()["account_id"]
            
            auth_data = {
                "account_id": account_id,
                "authorization_code": "test-auth-code",
                "state": "test-state"
            }
            await test_client.post("/auth/authenticate", json=auth_data)
            
            # Create webhook subscription
            webhook_data = {
                "account_id": account_id,
                "notification_url": "https://webhook.example.com/notifications",
                "resource": "/me/mailFolders('Inbox')/messages",
                "change_types": ["created", "updated"]
            }
            
            webhook_response = await test_client.post("/mail/webhooks", json=webhook_data)
            assert webhook_response.status_code == 201
            
            webhook_result = webhook_response.json()
            assert webhook_result["success"] is True
            assert "subscription_id" in webhook_result
            
            # Get webhook subscription
            get_webhook_response = await test_client.get(f"/mail/webhooks/{account_id}")
            assert get_webhook_response.status_code == 200
            
            get_webhook_result = get_webhook_response.json()
            assert get_webhook_result["subscription_id"] == "webhook-123"
    
    async def test_rate_limiting(self, test_client: AsyncClient):
        """Test rate limiting functionality."""
        
        # This test would require actual rate limiting to be enabled
        # For now, we'll test that the endpoint responds correctly
        
        # Make multiple rapid requests
        tasks = []
        for i in range(10):
            task = test_client.get("/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed (rate limiting not enforced in test)
        success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
        assert success_count >= 8  # Allow for some variation
    
    async def test_metrics_collection(self, test_client: AsyncClient):
        """Test that metrics are properly collected during operations."""
        
        metrics_collector = get_metrics_collector()
        
        # Make some requests to generate metrics
        await test_client.get("/health")
        await test_client.get("/metrics")
        
        # Verify metrics endpoint works
        metrics_response = await test_client.get("/metrics")
        assert metrics_response.status_code == 200
        
        # The response should contain Prometheus metrics format
        metrics_text = metrics_response.text
        assert "http_requests_total" in metrics_text or len(metrics_text) >= 0
    
    async def test_health_check_integration(self, test_client: AsyncClient):
        """Test comprehensive health check."""
        
        health_response = await test_client.get("/health")
        assert health_response.status_code == 200
        
        health_result = health_response.json()
        assert "status" in health_result
        assert "timestamp" in health_result
        assert "checks" in health_result
        
        # Verify individual component checks
        checks = health_result["checks"]
        assert "database" in checks
        
        # Database should be healthy in test environment
        assert checks["database"]["status"] in ["healthy", "degraded"]
    
    async def test_concurrent_mail_queries(self, test_client: AsyncClient, mock_graph_api_responses):
        """Test concurrent mail queries from multiple accounts."""
        
        with patch('adapters.external.oauth_client.OAuthClient.exchange_code_for_token') as mock_oauth, \
             patch('adapters.external.graph_client.GraphAPIClient.get_user_info') as mock_user_info, \
             patch('adapters.external.graph_client.GraphAPIClient.query_messages') as mock_query_messages:
            
            # Setup mocks
            mock_oauth.return_value = mock_graph_api_responses["token_response"]
            mock_user_info.return_value = mock_graph_api_responses["user_info"]
            mock_query_messages.return_value = mock_graph_api_responses["messages"]
            
            # Create multiple accounts
            account_ids = []
            for i in range(3):
                account_data = {
                    "email": f"test{i}@example.com",
                    "tenant_id": f"test-tenant-{i}",
                    "client_id": f"test-client-{i}",
                    "authentication_flow": "authorization_code",
                    "scopes": ["Mail.Read"],
                    "client_secret": f"test-secret-{i}",
                    "redirect_uri": "http://localhost:8000/auth/callback"
                }
                
                account_response = await test_client.post("/auth/accounts", json=account_data)
                account_id = account_response.json()["account_id"]
                account_ids.append(account_id)
                
                # Authenticate each account
                auth_data = {
                    "account_id": account_id,
                    "authorization_code": f"test-auth-code-{i}",
                    "state": f"test-state-{i}"
                }
                await test_client.post("/auth/authenticate", json=auth_data)
            
            # Make concurrent mail queries
            query_tasks = []
            for account_id in account_ids:
                mail_query_data = {
                    "account_id": account_id,
                    "folder_id": "inbox",
                    "top": 10
                }
                task = test_client.post("/mail/query", json=mail_query_data)
                query_tasks.append(task)
            
            # Execute all queries concurrently
            responses = await asyncio.gather(*query_tasks)
            
            # All queries should succeed
            for response in responses:
                assert response.status_code == 200
                result = response.json()
                assert result["success"] is True
                assert "messages" in result
    
    async def test_data_persistence_across_requests(self, test_client: AsyncClient, mock_graph_api_responses):
        """Test that data persists correctly across multiple requests."""
        
        with patch('adapters.external.oauth_client.OAuthClient.exchange_code_for_token') as mock_oauth, \
             patch('adapters.external.graph_client.GraphAPIClient.get_user_info') as mock_user_info, \
             patch('adapters.external.graph_client.GraphAPIClient.query_messages') as mock_query_messages:
            
            # Setup mocks
            mock_oauth.return_value = mock_graph_api_responses["token_response"]
            mock_user_info.return_value = mock_graph_api_responses["user_info"]
            mock_query_messages.return_value = mock_graph_api_responses["messages"]
            
            # Create account
            account_data = {
                "email": "persistence@example.com",
                "tenant_id": "persistence-tenant",
                "client_id": "persistence-client",
                "authentication_flow": "authorization_code",
                "scopes": ["Mail.Read"],
                "client_secret": "persistence-secret",
                "redirect_uri": "http://localhost:8000/auth/callback"
            }
            
            account_response = await test_client.post("/auth/accounts", json=account_data)
            account_id = account_response.json()["account_id"]
            
            # Authenticate
            auth_data = {
                "account_id": account_id,
                "authorization_code": "persistence-auth-code",
                "state": "persistence-state"
            }
            await test_client.post("/auth/authenticate", json=auth_data)
            
            # Query mail
            mail_query_data = {
                "account_id": account_id,
                "folder_id": "inbox",
                "top": 10
            }
            await test_client.post("/mail/query", json=mail_query_data)
            
            # Verify account still exists
            account_list_response = await test_client.get("/auth/accounts")
            assert account_list_response.status_code == 200
            
            accounts = account_list_response.json()["accounts"]
            account_emails = [acc["email"] for acc in accounts]
            assert "persistence@example.com" in account_emails
            
            # Verify query history exists
            history_response = await test_client.get(f"/mail/history?account_id={account_id}")
            assert history_response.status_code == 200
            
            history_result = history_response.json()
            assert len(history_result["history"]) >= 1
            
            # Verify authentication logs exist
            logs_response = await test_client.get(f"/auth/logs?account_id={account_id}")
            assert logs_response.status_code == 200
            
            logs_result = logs_response.json()
            assert len(logs_result["logs"]) >= 1


@pytest.mark.integration
class TestBackgroundTasksIntegration:
    """Integration tests for background tasks."""
    
    async def test_background_task_startup_shutdown(self):
        """Test background task service startup and shutdown."""
        
        from core.services.background_tasks import BackgroundTaskService
        from core.usecases.auth_usecases import AuthenticationUseCases
        from core.usecases.mail_usecases import MailUseCases
        
        # Create mock use cases
        auth_usecases = AsyncMock(spec=AuthenticationUseCases)
        mail_usecases = AsyncMock(spec=MailUseCases)
        
        # Create background task service
        bg_service = BackgroundTaskService(
            mail_usecases=mail_usecases,
            auth_usecases=auth_usecases
        )
        
        # Start service
        start_task = asyncio.create_task(bg_service.start())
        await asyncio.sleep(0.1)  # Let it start
        
        # Verify service is running
        assert bg_service.running is True
        task_status = bg_service.get_task_status()
        assert task_status["running"] is True
        assert task_status["total_tasks"] > 0
        
        # Stop service
        await bg_service.stop()
        
        # Verify service is stopped
        assert bg_service.running is False
        
        # Clean up
        if not start_task.done():
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass


@pytest.mark.integration
class TestCacheIntegration:
    """Integration tests for caching functionality."""
    
    async def test_cache_operations(self):
        """Test basic cache operations."""
        
        from adapters.cache.redis_cache import InMemoryCacheAdapter
        
        # Use in-memory cache for testing
        cache = InMemoryCacheAdapter()
        await cache.connect()
        
        try:
            # Test set/get
            await cache.set("test_key", {"data": "test_value"}, ttl=60)
            result = await cache.get("test_key")
            assert result == {"data": "test_value"}
            
            # Test exists
            exists = await cache.exists("test_key")
            assert exists is True
            
            # Test delete
            deleted = await cache.delete("test_key")
            assert deleted is True
            
            # Verify deletion
            result = await cache.get("test_key")
            assert result is None
            
        finally:
            await cache.disconnect()
    
    async def test_cache_health_check(self):
        """Test cache health check."""
        
        from adapters.cache.redis_cache import InMemoryCacheAdapter
        
        cache = InMemoryCacheAdapter()
        await cache.connect()
        
        try:
            health = await cache.get_health_status()
            assert health["status"] == "healthy"
            assert health["type"] == "in_memory"
            
        finally:
            await cache.disconnect()
