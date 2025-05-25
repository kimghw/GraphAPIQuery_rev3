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
    result = await auth_usecases.register_account(
        user_id="test-user-id",
        email="test@example.com",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    assert result["success"] is True
    assert "account_id" in result
    assert result["message"] == "Account registered successfully"
    
    # Verify account was created by getting it
    account_info = await auth_usecases.get_account_info(result["account_id"])
    assert account_info is not None
    account = account_info["account"]
    assert account["email"] == "test@example.com"
    assert account["user_id"] == "test-user-id"
    assert account["authentication_flow"] == AuthenticationFlow.AUTHORIZATION_CODE.value
    assert account["status"] == AccountStatus.ACTIVE.value
    assert "offline_access" in account["scopes"]
    assert "User.Read" in account["scopes"]
    assert "Mail.Read" in account["scopes"]


@pytest.mark.asyncio
async def test_create_account_device_code(auth_usecases: AuthenticationUseCases):
    """Test creating an account with device code flow."""
    result = await auth_usecases.register_account(
        user_id="test-user-id",
        email="test@example.com",
        authentication_flow=AuthenticationFlow.DEVICE_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"]
    )
    
    assert result["success"] is True
    assert "account_id" in result
    assert result["message"] == "Account registered successfully"
    
    # Verify account was created by getting it
    account_info = await auth_usecases.get_account_info(result["account_id"])
    assert account_info is not None
    account = account_info["account"]
    assert account["email"] == "test@example.com"
    assert account["authentication_flow"] == AuthenticationFlow.DEVICE_CODE.value
    assert account["status"] == AccountStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_get_account_info(auth_usecases: AuthenticationUseCases):
    """Test getting account info."""
    # Create account first
    result = await auth_usecases.register_account(
        user_id="test-user-id",
        email="test@example.com",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Get account info
    account_info = await auth_usecases.get_account_info(result["account_id"])
    
    assert account_info is not None
    account = account_info["account"]
    assert account["id"] == result["account_id"]
    assert account["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_authenticate_authorization_code(
    auth_usecases: AuthenticationUseCases,
    mock_oauth_client: AsyncMock
):
    """Test authenticating with authorization code flow."""
    # Create account first
    result = await auth_usecases.register_account(
        user_id="test-user-id",
        email="test@example.com",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Authenticate
    auth_result = await auth_usecases.authenticate_account(
        result["account_id"],
        authorization_code="test-code",
        state="test-state"
    )
    
    assert auth_result["success"] is True
    assert auth_result["requires_user_action"] is False
    assert "message" in auth_result
    
    # Verify OAuth client was called
    mock_oauth_client.exchange_code_for_token.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token_flow(
    auth_usecases: AuthenticationUseCases,
    mock_oauth_client: AsyncMock
):
    """Test refreshing token."""
    # Create account and authenticate first
    result = await auth_usecases.register_account(
        user_id="test-user-id",
        email="test@example.com",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Authenticate to create initial token
    await auth_usecases.authenticate_account(
        result["account_id"],
        authorization_code="test-code",
        state="test-state"
    )
    
    # Refresh token
    refresh_result = await auth_usecases.refresh_account_token(result["account_id"])
    
    assert refresh_result["success"] is True
    assert "message" in refresh_result
    
    # Verify OAuth client was called for refresh
    mock_oauth_client.refresh_token.assert_called()


@pytest.mark.asyncio
async def test_get_all_accounts_info(auth_usecases: AuthenticationUseCases):
    """Test getting all accounts info."""
    # Create multiple accounts
    result1 = await auth_usecases.register_account(
        user_id="test-user-id-1",
        email="test1@example.com",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    result2 = await auth_usecases.register_account(
        user_id="test-user-id-2",
        email="test2@example.com",
        authentication_flow=AuthenticationFlow.DEVICE_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"]
    )
    
    # Get all accounts - returns a list directly
    accounts_info = await auth_usecases.get_all_accounts_info()
    
    assert len(accounts_info) == 2
    emails = [acc["account"]["email"] for acc in accounts_info]
    assert "test1@example.com" in emails
    assert "test2@example.com" in emails


@pytest.mark.asyncio
async def test_revoke_account_tokens(auth_usecases: AuthenticationUseCases):
    """Test revoking account tokens."""
    # Create account and authenticate first
    result = await auth_usecases.register_account(
        user_id="test-user-id",
        email="test@example.com",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Authenticate to create token
    await auth_usecases.authenticate_account(
        result["account_id"],
        authorization_code="test-code",
        state="test-state"
    )
    
    # Revoke tokens
    revoke_result = await auth_usecases.revoke_account_tokens(result["account_id"])
    
    assert revoke_result["success"] is True
    assert revoke_result["message"] == "Token revoked successfully"


@pytest.mark.asyncio
async def test_search_accounts(auth_usecases: AuthenticationUseCases):
    """Test searching accounts."""
    # Create account first
    await auth_usecases.register_account(
        user_id="test-user-id",
        email="test@example.com",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Search accounts - returns a list directly
    search_result = await auth_usecases.search_accounts({"email": "test@example.com"})
    
    assert len(search_result) == 1
    assert search_result[0]["account"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_authentication_logs(auth_usecases: AuthenticationUseCases):
    """Test getting authentication logs."""
    # Create account and authenticate to generate logs
    result = await auth_usecases.register_account(
        user_id="test-user-id",
        email="test@example.com",
        authentication_flow=AuthenticationFlow.AUTHORIZATION_CODE,
        scopes=["offline_access", "User.Read", "Mail.Read"],
        client_secret="test-secret",
        redirect_uri="http://localhost:8000/auth/callback"
    )
    
    # Get authentication logs - returns a list directly
    logs_result = await auth_usecases.get_authentication_logs()
    
    assert isinstance(logs_result, list)
    assert len(logs_result) > 0
    
    # Check that registration was logged
    registration_logs = [log for log in logs_result if log.event_type == "registration"]
    assert len(registration_logs) > 0
