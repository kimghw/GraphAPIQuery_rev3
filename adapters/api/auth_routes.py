"""Authentication API routes."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
import structlog

from core.usecases.auth_usecases import AuthenticationUseCases
from core.domain.entities import AuthenticationFlow
from adapters.api.dependencies import get_auth_usecases
from adapters.api.schemas import (
    CreateAccountRequest, AccountResponse, UpdateAccountRequest,
    AccountListResponse, AuthenticationRequest, AuthorizationUrlResponse,
    AuthorizationCallbackRequest, DeviceCodeResponse, TokenResponse,
    TokenStatusResponse, AuthLogQueryRequest, AuthLogListResponse,
    BaseResponse, ErrorResponse
)

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new account",
    description="Create a new Microsoft 365 account for authentication"
)
async def create_account(
    request: CreateAccountRequest,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> AccountResponse:
    """Create a new account."""
    try:
        result = await auth_usecases.register_account(
            email=request.email,
            user_id=request.email,  # Use email as user_id for now
            authentication_flow=request.authentication_flow,
            scopes=request.scopes
        )
        
        # Get the created account
        account = await auth_usecases.get_account_by_email(request.email)
        if not account:
            raise ValueError("Failed to retrieve created account")
        
        return AccountResponse(
            id=account.id,
            email=account.email,
            user_id=account.user_id,
            tenant_id=account.tenant_id,
            client_id=account.client_id,
            authentication_flow=account.authentication_flow,
            status=account.status,
            scopes=account.scopes,
            created_at=account.created_at,
            updated_at=account.updated_at,
            last_authenticated_at=account.last_authenticated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to create account", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )


@router.get(
    "/accounts",
    response_model=AccountListResponse,
    summary="List all accounts",
    description="Get list of all registered accounts"
)
async def list_accounts(
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> AccountListResponse:
    """List all accounts."""
    try:
        accounts_data = await auth_usecases.get_all_accounts()
        
        account_responses = []
        for account_data in accounts_data:
            account = account_data["account"]
            account_responses.append(
                AccountResponse(
                    id=account["id"],
                    email=account["email"],
                    user_id=account["user_id"],
                    tenant_id=account["tenant_id"],
                    client_id=account["client_id"],
                    authentication_flow=account["authentication_flow"],
                    status=account["status"],
                    scopes=account["scopes"],
                    created_at=account["created_at"],
                    updated_at=account.get("updated_at"),
                    last_authenticated_at=account.get("last_authenticated_at")
                )
            )
        
        return AccountListResponse(
            accounts=account_responses,
            total=len(account_responses)
        )
        
    except Exception as e:
        logger.error("Failed to list accounts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list accounts"
        )


@router.get(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    summary="Get account by ID",
    description="Get account details by account ID"
)
async def get_account(
    account_id: str,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> AccountResponse:
    """Get account by ID."""
    try:
        account = await auth_usecases.get_account_by_id(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        return AccountResponse(
            id=account.id,
            email=account.email,
            user_id=account.user_id,
            tenant_id=account.tenant_id,
            client_id=account.client_id,
            authentication_flow=account.authentication_flow,
            status=account.status,
            scopes=account.scopes,
            created_at=account.created_at,
            updated_at=account.updated_at,
            last_authenticated_at=account.last_authenticated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get account", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get account"
        )


@router.put(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    summary="Update account",
    description="Update account details"
)
async def update_account(
    account_id: str,
    request: UpdateAccountRequest,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> AccountResponse:
    """Update account."""
    try:
        account = await auth_usecases.update_account(
            account_id=account_id,
            email=request.email,
            scopes=request.scopes,
            status=request.status
        )
        
        return AccountResponse(
            id=account.id,
            email=account.email,
            user_id=account.user_id,
            tenant_id=account.tenant_id,
            client_id=account.client_id,
            authentication_flow=account.authentication_flow,
            status=account.status,
            scopes=account.scopes,
            created_at=account.created_at,
            updated_at=account.updated_at,
            last_authenticated_at=account.last_authenticated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to update account", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update account"
        )


@router.delete(
    "/accounts/{account_id}",
    response_model=BaseResponse,
    summary="Delete account",
    description="Delete account and associated data"
)
async def delete_account(
    account_id: str,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> BaseResponse:
    """Delete account."""
    try:
        success = await auth_usecases.delete_account(account_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        return BaseResponse(message="Account deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete account", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )


@router.post(
    "/authenticate",
    response_model=AuthorizationUrlResponse,
    summary="Start authentication",
    description="Start authentication process for an account"
)
async def authenticate(
    request: AuthenticationRequest,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> AuthorizationUrlResponse:
    """Start authentication process."""
    try:
        # Get account
        if request.account_id:
            account = await auth_usecases.get_account_by_id(request.account_id)
        elif request.email:
            account = await auth_usecases.get_account_by_email(request.email)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either account_id or email must be provided"
            )
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        if account.authentication_flow == AuthenticationFlow.AUTHORIZATION_CODE:
            result = await auth_usecases.authenticate_account(account.id)
            
            if result.get("requires_user_action") and result.get("authorization_url"):
                return AuthorizationUrlResponse(
                    authorization_url=result["authorization_url"],
                    state=result.get("state", ""),
                    expires_at=datetime.utcnow().replace(hour=23, minute=59, second=59),
                    instructions=result.get("message", "Please visit the authorization URL to complete authentication")
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate authorization URL"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use /auth/device-code endpoint for device code flow"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start authentication", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start authentication"
        )


@router.post(
    "/device-code",
    response_model=DeviceCodeResponse,
    summary="Start device code flow",
    description="Start device code authentication flow"
)
async def start_device_code_flow(
    request: AuthenticationRequest,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> DeviceCodeResponse:
    """Start device code flow."""
    try:
        # Get account
        if request.account_id:
            account = await auth_usecases.get_account_by_id(request.account_id)
        elif request.email:
            account = await auth_usecases.get_account_by_email(request.email)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either account_id or email must be provided"
            )
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found"
            )
        
        if account.authentication_flow != AuthenticationFlow.DEVICE_CODE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is not configured for device code flow"
            )
        
        device_account = await auth_usecases.start_device_code_flow(account.id)
        
        return DeviceCodeResponse(
            device_code=device_account.device_code,
            user_code=device_account.user_code,
            verification_uri=device_account.verification_uri,
            expires_in=device_account.expires_in,
            interval=device_account.interval,
            instructions=f"Go to {device_account.verification_uri} and enter code: {device_account.user_code}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start device code flow", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start device code flow"
        )


@router.post(
    "/device-code/poll/{account_id}",
    response_model=TokenResponse,
    summary="Poll device code",
    description="Poll for device code authentication completion"
)
async def poll_device_code(
    account_id: str,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> TokenResponse:
    """Poll device code for completion."""
    try:
        token = await auth_usecases.poll_device_code_flow(account_id)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Authentication still pending"
            )
        
        return TokenResponse(
            account_id=token.account_id,
            token_type=token.token_type,
            expires_at=token.expires_at,
            scopes=token.scopes,
            status=token.status,
            created_at=token.created_at,
            updated_at=token.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to poll device code", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to poll device code"
        )


@router.get(
    "/callback",
    summary="OAuth callback",
    description="OAuth authorization callback endpoint"
)
async def oauth_callback(
    code: str,
    state: str,
    account_id: str,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
):
    """Handle OAuth callback."""
    try:
        token = await auth_usecases.handle_authorization_callback(
            account_id=account_id,
            authorization_code=code,
            state=state
        )
        
        # Redirect to success page or return success response
        return RedirectResponse(
            url=f"/auth/success?account_id={account_id}",
            status_code=status.HTTP_302_FOUND
        )
        
    except Exception as e:
        logger.error("OAuth callback failed", error=str(e))
        return RedirectResponse(
            url=f"/auth/error?error={str(e)}",
            status_code=status.HTTP_302_FOUND
        )


@router.post(
    "/refresh/{account_id}",
    response_model=TokenResponse,
    summary="Refresh token",
    description="Refresh access token for an account"
)
async def refresh_token(
    account_id: str,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> TokenResponse:
    """Refresh token."""
    try:
        token = await auth_usecases.refresh_token(account_id)
        
        return TokenResponse(
            account_id=token.account_id,
            token_type=token.token_type,
            expires_at=token.expires_at,
            scopes=token.scopes,
            status=token.status,
            created_at=token.created_at,
            updated_at=token.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to refresh token", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.post(
    "/revoke/{account_id}",
    response_model=BaseResponse,
    summary="Revoke token",
    description="Revoke access token and logout user"
)
async def revoke_token(
    account_id: str,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> BaseResponse:
    """Revoke token."""
    try:
        success = await auth_usecases.revoke_token(account_id)
        
        return BaseResponse(
            success=success,
            message="Token revoked successfully" if success else "Failed to revoke token"
        )
        
    except Exception as e:
        logger.error("Failed to revoke token", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke token"
        )


@router.get(
    "/tokens",
    response_model=TokenStatusResponse,
    summary="Get token status",
    description="Get token status for all accounts or specific account"
)
async def get_token_status(
    account_id: Optional[str] = None,
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> TokenStatusResponse:
    """Get token status."""
    try:
        if account_id:
            token = await auth_usecases.get_token_status(account_id)
            tokens = [token] if token else []
        else:
            tokens = await auth_usecases.get_all_token_status()
        
        token_responses = [
            TokenResponse(
                account_id=token.account_id,
                token_type=token.token_type,
                expires_at=token.expires_at,
                scopes=token.scopes,
                status=token.status,
                created_at=token.created_at,
                updated_at=token.updated_at
            )
            for token in tokens
        ]
        
        return TokenStatusResponse(tokens=token_responses)
        
    except Exception as e:
        logger.error("Failed to get token status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get token status"
        )


@router.get(
    "/logs",
    response_model=AuthLogListResponse,
    summary="Get authentication logs",
    description="Get authentication logs with optional filters"
)
async def get_auth_logs(
    request: AuthLogQueryRequest = Depends(),
    auth_usecases: AuthenticationUseCases = Depends(get_auth_usecases)
) -> AuthLogListResponse:
    """Get authentication logs."""
    try:
        logs = await auth_usecases.get_authentication_logs(
            account_id=request.account_id,
            date_from=request.date_from,
            date_to=request.date_to,
            success=request.success,
            limit=request.limit
        )
        
        log_responses = [
            {
                "account_id": log.account_id,
                "event_type": log.event_type,
                "authentication_flow": log.authentication_flow,
                "success": log.success,
                "error_code": log.error_code,
                "error_message": log.error_message,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp
            }
            for log in logs
        ]
        
        return AuthLogListResponse(
            logs=log_responses,
            total=len(log_responses)
        )
        
    except Exception as e:
        logger.error("Failed to get authentication logs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get authentication logs"
        )
