"""Test configuration and fixtures."""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config.settings import Settings
from adapters.db.database import DatabaseAdapter, Base
from adapters.db.repositories import DatabaseRepositoryAdapter
from adapters.external.graph_client import GraphAPIAdapter
from adapters.external.oauth_client import OAuthAdapter
from core.usecases.auth_usecases import AuthenticationUseCases
from core.usecases.mail_usecases import MailUseCases
from core.domain.entities import (
    Account, Token, MailMessage, AuthenticationFlow, 
    AccountStatus, TokenStatus, MailDirection, MailImportance
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Test settings."""
    return Settings(
        ENVIRONMENT="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        DATABASE_ECHO=False,
        MICROSOFT_TENANT_ID="test-tenant",
        MICROSOFT_CLIENT_ID="test-client",
        MICROSOFT_CLIENT_SECRET="test-secret",
        MICROSOFT_REDIRECT_URI="http://localhost:8000/auth/callback",
        EXTERNAL_API_ENDPOINT="http://localhost:9000/api/messages",
        EXTERNAL_API_TIMEOUT=30,
        EXTERNAL_API_RETRY_ATTEMPTS=3,
        HOST="127.0.0.1",
        PORT=8000,
        CORS_ORIGINS=["*"]
    )


@pytest_asyncio.fixture
async def db_adapter(test_settings: Settings) -> AsyncGenerator[DatabaseAdapter, None]:
    """Database adapter for testing."""
    # Create in-memory SQLite database
    engine = create_async_engine(
        test_settings.DATABASE_URL,
        echo=test_settings.DATABASE_ECHO,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    adapter = DatabaseAdapter(engine, async_session_factory)
    
    yield adapter
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def repo_adapter(db_adapter: DatabaseAdapter) -> DatabaseRepositoryAdapter:
    """Repository adapter for testing."""
    return DatabaseRepositoryAdapter(db_adapter)


@pytest.fixture
def mock_graph_client() -> AsyncMock:
    """Mock Graph API client."""
    mock = AsyncMock(spec=GraphAPIAdapter)
    
    # Mock common methods
    mock.get_user_info.return_value = {
        "id": "test-user-id",
        "userPrincipalName": "test@example.com",
        "displayName": "Test User"
    }
    
    mock.query_messages.return_value = {
        "value": [],
        "@odata.count": 0,
        "@odata.nextLink": None
    }
    
    mock.send_message.return_value = {
        "id": "test-message-id"
    }
    
    return mock


@pytest.fixture
def mock_oauth_client() -> AsyncMock:
    """Mock OAuth client."""
    mock = AsyncMock(spec=OAuthAdapter)
    
    # Mock common methods
    mock.get_authorization_url.return_value = (
        "https://login.microsoftonline.com/authorize?...",
        "test-state"
    )
    
    mock.exchange_code_for_token.return_value = {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "expires_in": 3600,
        "scope": "offline_access User.Read Mail.Read"
    }
    
    mock.refresh_token.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "expires_in": 3600,
        "scope": "offline_access User.Read Mail.Read"
    }
    
    return mock


@pytest_asyncio.fixture
async def auth_usecases(
    repo_adapter: DatabaseRepositoryAdapter,
    mock_oauth_client: AsyncMock,
    test_settings: Settings
) -> AuthenticationUseCases:
    """Authentication use cases for testing."""
    return AuthenticationUseCases(
        account_repo=repo_adapter,
        token_repo=repo_adapter,
        auth_log_repo=repo_adapter,
        oauth_client=mock_oauth_client,
        config=test_settings
    )


@pytest_asyncio.fixture
async def mail_usecases(
    repo_adapter: DatabaseRepositoryAdapter,
    mock_graph_client: AsyncMock,
    test_settings: Settings
) -> MailUseCases:
    """Mail use cases for testing."""
    return MailUseCases(
        account_repo=repo_adapter,
        token_repo=repo_adapter,
        mail_repo=repo_adapter,
        query_history_repo=repo_adapter,
        webhook_repo=repo_adapter,
        external_api_repo=repo_adapter,
        graph_client=mock_graph_client,
        config=test_settings
    )


@pytest.fixture
def sample_account() -> Account:
    """Sample account for testing."""
    return Account(
        id="test-account-id",
        email="test@example.com",
        user_id="test-user-id",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        status=AccountStatus.ACTIVE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        created_at=datetime.utcnow(),
        updated_at=None,
        last_authenticated_at=None
    )


@pytest.fixture
def sample_token() -> Token:
    """Sample token for testing."""
    return Token(
        id="test-token-id",
        account_id="test-account-id",
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        token_type="Bearer",
        expires_at=datetime.utcnow(),
        scopes=["offline_access", "User.Read", "Mail.Read"],
        status=TokenStatus.VALID,
        created_at=datetime.utcnow(),
        updated_at=None
    )


@pytest.fixture
def sample_mail_message() -> MailMessage:
    """Sample mail message for testing."""
    return MailMessage(
        message_id="test-message-id",
        internet_message_id="<test@example.com>",
        account_id="test-account-id",
        subject="Test Subject",
        sender_email="sender@example.com",
        sender_name="Test Sender",
        recipients=[],
        cc_recipients=None,
        bcc_recipients=None,
        body_preview="Test body preview",
        body_content="Test body content",
        body_content_type="text",
        importance=MailImportance.NORMAL,
        is_read=False,
        has_attachments=False,
        received_datetime=datetime.utcnow(),
        sent_datetime=datetime.utcnow(),
        direction=MailDirection.INBOUND,
        categories=None,
        created_at=datetime.utcnow()
    )


@pytest.fixture
def sample_graph_message() -> dict:
    """Sample Graph API message response."""
    return {
        "id": "test-message-id",
        "internetMessageId": "<test@example.com>",
        "subject": "Test Subject",
        "bodyPreview": "Test body preview",
        "body": {
            "contentType": "text",
            "content": "Test body content"
        },
        "importance": "normal",
        "isRead": False,
        "hasAttachments": False,
        "receivedDateTime": "2023-01-01T12:00:00Z",
        "sentDateTime": "2023-01-01T12:00:00Z",
        "from": {
            "emailAddress": {
                "address": "sender@example.com",
                "name": "Test Sender"
            }
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "address": "recipient@example.com",
                    "name": "Test Recipient"
                }
            }
        ],
        "ccRecipients": [],
        "bccRecipients": [],
        "categories": []
    }


# Async test helpers
class AsyncContextManager:
    """Helper for async context managers in tests."""
    
    def __init__(self, async_func):
        self.async_func = async_func
    
    async def __aenter__(self):
        return await self.async_func()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def async_mock_context(return_value=None):
    """Create an async mock context manager."""
    mock = AsyncMock()
    mock.return_value = return_value
    return AsyncContextManager(mock)
