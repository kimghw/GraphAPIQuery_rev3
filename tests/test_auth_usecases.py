"""Tests for authentication use cases."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from core.usecases.auth_usecases import AuthenticationUseCases
from core.domain.entities import AuthenticationFlow, AccountStatus
from adapters.db.repositories import DatabaseRepositoryAdapter


@pytest.mark.asyncio
async def test_create_account_authorization_code(auth_usecases: AuthenticationUseCases):
    """Test creating an account with authorization code flow."""
    account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    assert account.email == "test@example.com"
    assert account.tenant_id == "test-tenant"
    assert account.client_id == "test-client"
    assert account.authentication_flow == AuthenticationFlow.AUTHORIZATION_CODE
    assert account.status == AccountStatus.ACTIVE
    assert "offline_access" in account.scopes
    assert "User.Read" in account.scopes
    assert "Mail.Read" in account.scopes


@pytest.mark.asyncio
async def test_create_account_device_code(auth_usecases: AuthenticationUseCases):
    """Test creating an account with device code flow."""
    account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.DEVICE_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"]
    )
    
    assert account.email == "test@example.com"
    assert account.authentication_flow == AuthenticationFlow.DEVICE_CODE
    assert account.status == AccountStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_account_by_email(auth_usecases: AuthenticationUseCases):
    """Test getting account by email."""
    # Create account first
    created_account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Get account by email
    account = await auth_usecases.get_account_by_email("test@example.com")
    
    assert account is not None
    assert account.id == created_account.id
    assert account.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_account_by_id(auth_usecases: AuthenticationUseCases):
    """Test getting account by ID."""
    # Create account first
    created_account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Get account by ID
    account = await auth_usecases.get_account_by_id(created_account.id)
    
    assert account is not None
    assert account.id == created_account.id
    assert account.email == "test@example.com"


@pytest.mark.asyncio
async def test_start_authorization_code_flow(auth_usecases: AuthenticationUseCases):
    """Test starting authorization code flow."""
    # Create account first
    account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Start authorization flow
    auth_url, state = await auth_usecases.start_authorization_code_flow(account.id)
    
    assert auth_url.startswith("https://login.microsoftonline.com")
    assert state == "test-state"


@pytest.mark.asyncio
async def test_exchange_authorization_code(
    auth_usecases: AuthenticationUseCases,
    mock_oauth_client: AsyncMock
):
    """Test exchanging authorization code for token."""
    # Create account first
    account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Exchange code for token
    token = await auth_usecases.exchange_authorization_code(
        account.id,
        "test-code",
        "test-state"
    )
    
    assert token is not None
    assert token.account_id == account.id
    assert token.access_token == "test-access-token"
    assert token.refresh_token == "test-refresh-token"
    
    # Verify OAuth client was called
    mock_oauth_client.exchange_code_for_token.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token(
    auth_usecases: AuthenticationUseCases,
    mock_oauth_client: AsyncMock
):
    """Test refreshing token."""
    # Create account and token first
    account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Create initial token
    await auth_usecases.exchange_authorization_code(
        account.id,
        "test-code",
        "test-state"
    )
    
    # Refresh token
    new_token = await auth_usecases.refresh_token(account.id)
    
    assert new_token is not None
    assert new_token.account_id == account.id
    assert new_token.access_token == "new-access-token"
    assert new_token.refresh_token == "new-refresh-token"
    
    # Verify OAuth client was called
    mock_oauth_client.refresh_token.assert_called()


@pytest.mark.asyncio
async def test_get_all_accounts(auth_usecases: AuthenticationUseCases):
    """Test getting all accounts."""
    # Create multiple accounts
    await auth_usecases.create_account(
        email="test1@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    await auth_usecases.create_account(
        email="test2@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.DEVICE_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"]
    )
    
    # Get all accounts
    accounts = await auth_usecases.get_all_accounts()
    
    assert len(accounts) == 2
    emails = [account.email for account in accounts]
    assert "test1@example.com" in emails
    assert "test2@example.com" in emails


@pytest.mark.asyncio
async def test_delete_account(auth_usecases: AuthenticationUseCases):
    """Test deleting an account."""
    # Create account first
    account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Delete account
    success = await auth_usecases.delete_account(account.id)
    
    assert success is True
    
    # Verify account is deleted
    deleted_account = await auth_usecases.get_account_by_id(account.id)
    assert deleted_account is None


@pytest.mark.asyncio
async def test_get_token_status(auth_usecases: AuthenticationUseCases):
    """Test getting token status."""
    # Create account and token first
    account = await auth_usecases.create_account(
        email="test@example.com",
        tenant_id="test-tenant",
        client_id="test-client",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Create token
    await auth_usecases.exchange_authorization_code(
        account.id,
        "test-code",
        "test-state"
    )
    
    # Get token status
    token = await auth_usecases.get_token_status(account.id)
    
    assert token is not None
    assert token.account_id == account.id
    assert token.access_token == "test-access-token"
