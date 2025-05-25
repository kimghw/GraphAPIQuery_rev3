"""OAuth 2.0 authentication client adapter."""

import asyncio
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs
import httpx
import structlog

from core.domain.entities import (
    Account, AuthorizationCodeAccount, DeviceCodeAccount, Token,
    AuthenticationFlow, TokenStatus
)
from core.usecases.ports import OAuthClientPort
from config.settings import Settings

logger = structlog.get_logger()


class OAuthClientAdapter(OAuthClientPort):
    """OAuth 2.0 client implementation for Microsoft Graph API."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.timeout = httpx.Timeout(30.0)
        
    def _get_authority_url(self, tenant_id: str) -> str:
        """Get authority URL for tenant."""
        return f"https://login.microsoftonline.com/{tenant_id}"
    
    def _get_token_endpoint(self, tenant_id: str) -> str:
        """Get token endpoint URL."""
        return f"{self._get_authority_url(tenant_id)}/oauth2/v2.0/token"
    
    def _get_device_code_endpoint(self, tenant_id: str) -> str:
        """Get device code endpoint URL."""
        return f"{self._get_authority_url(tenant_id)}/oauth2/v2.0/devicecode"
    
    async def get_authorization_url(
        self,
        auth_account: AuthorizationCodeAccount,
        account: Account,
        scopes: list[str],
        state: Optional[str] = None
    ) -> Tuple[str, str]:
        """Get authorization URL for Authorization Code Flow."""
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Generate PKCE parameters
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = code_verifier  # For simplicity, using plain method
        
        params = {
            "client_id": account.client_id,
            "response_type": "code",
            "redirect_uri": auth_account.redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "plain",
            "response_mode": "query"
        }
        
        auth_url = f"{self._get_authority_url(account.tenant_id)}/oauth2/v2.0/authorize"
        full_url = f"{auth_url}?{urlencode(params)}"
        
        logger.info(
            "Generated authorization URL",
            client_id=account.client_id,
            redirect_uri=auth_account.redirect_uri,
            scopes=scopes
        )
        
        return full_url, code_verifier
    
    async def exchange_code_for_token(
        self,
        auth_account: AuthorizationCodeAccount,
        authorization_code: str,
        code_verifier: str,
        scopes: list[str]
    ) -> Token:
        """Exchange authorization code for access token."""
        token_url = self._get_token_endpoint(auth_account.account.tenant_id)
        
        data = {
            "client_id": auth_account.account.client_id,
            "client_secret": auth_account.client_secret,
            "code": authorization_code,
            "redirect_uri": auth_account.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
            "scope": " ".join(scopes)
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(token_url, data=data, headers=headers)
                response.raise_for_status()
                
                token_data = response.json()
                
                # Calculate expiration time
                expires_in = token_data.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                token = Token(
                    account_id=auth_account.account_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=expires_at,
                    scopes=token_data.get("scope", " ".join(scopes)).split(),
                    status=TokenStatus.VALID,
                    created_at=datetime.utcnow()
                )
                
                logger.info(
                    "Successfully exchanged authorization code for token",
                    account_id=auth_account.account_id,
                    expires_at=expires_at,
                    has_refresh_token=bool(token.refresh_token)
                )
                
                return token
                
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass
            
            logger.error(
                "Failed to exchange authorization code for token",
                account_id=auth_account.account_id,
                status_code=e.response.status_code,
                error=error_data.get("error"),
                error_description=error_data.get("error_description")
            )
            raise
        
        except Exception as e:
            logger.error(
                "Unexpected error during token exchange",
                account_id=auth_account.account_id,
                error=str(e)
            )
            raise
    
    async def initiate_device_flow(
        self,
        device_account: DeviceCodeAccount,
        scopes: list[str]
    ) -> DeviceCodeAccount:
        """Initiate device code flow."""
        device_code_url = self._get_device_code_endpoint(device_account.account.tenant_id)
        
        data = {
            "client_id": device_account.account.client_id,
            "scope": " ".join(scopes)
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(device_code_url, data=data, headers=headers)
                response.raise_for_status()
                
                device_data = response.json()
                
                # Update device account with response data
                updated_device_account = DeviceCodeAccount(
                    account_id=device_account.account_id,
                    device_code=device_data["device_code"],
                    user_code=device_data["user_code"],
                    verification_uri=device_data["verification_uri"],
                    expires_in=device_data["expires_in"],
                    interval=device_data.get("interval", 5),
                    created_at=device_account.created_at,
                    updated_at=datetime.utcnow()
                )
                
                logger.info(
                    "Initiated device code flow",
                    account_id=device_account.account_id,
                    user_code=device_data["user_code"],
                    verification_uri=device_data["verification_uri"],
                    expires_in=device_data["expires_in"]
                )
                
                return updated_device_account
                
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass
            
            logger.error(
                "Failed to initiate device code flow",
                account_id=device_account.account_id,
                status_code=e.response.status_code,
                error=error_data.get("error"),
                error_description=error_data.get("error_description")
            )
            raise
        
        except Exception as e:
            logger.error(
                "Unexpected error during device flow initiation",
                account_id=device_account.account_id,
                error=str(e)
            )
            raise
    
    async def poll_device_token(
        self,
        device_account: DeviceCodeAccount,
        scopes: list[str]
    ) -> Optional[Token]:
        """Poll for device token."""
        token_url = self._get_token_endpoint(device_account.account.tenant_id)
        
        data = {
            "client_id": device_account.account.client_id,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_account.device_code
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(token_url, data=data, headers=headers)
                
                if response.status_code == 200:
                    token_data = response.json()
                    
                    # Calculate expiration time
                    expires_in = token_data.get("expires_in", 3600)
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    
                    token = Token(
                        account_id=device_account.account_id,
                        access_token=token_data["access_token"],
                        refresh_token=token_data.get("refresh_token"),
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_at=expires_at,
                        scopes=token_data.get("scope", " ".join(scopes)).split(),
                        status=TokenStatus.VALID,
                        created_at=datetime.utcnow()
                    )
                    
                    logger.info(
                        "Successfully obtained device token",
                        account_id=device_account.account_id,
                        expires_at=expires_at,
                        has_refresh_token=bool(token.refresh_token)
                    )
                    
                    return token
                
                elif response.status_code == 400:
                    error_data = response.json()
                    error_code = error_data.get("error")
                    
                    if error_code == "authorization_pending":
                        # User hasn't completed authorization yet
                        logger.debug(
                            "Device authorization still pending",
                            account_id=device_account.account_id
                        )
                        return None
                    
                    elif error_code == "slow_down":
                        # Need to slow down polling
                        logger.warning(
                            "Device polling rate limited, slowing down",
                            account_id=device_account.account_id
                        )
                        return None
                    
                    elif error_code in ["authorization_declined", "bad_verification_code", "expired_token"]:
                        # Terminal errors
                        logger.error(
                            "Device authorization failed",
                            account_id=device_account.account_id,
                            error=error_code,
                            error_description=error_data.get("error_description")
                        )
                        raise Exception(f"Device authorization failed: {error_code}")
                    
                    else:
                        logger.error(
                            "Unknown device polling error",
                            account_id=device_account.account_id,
                            error=error_code,
                            error_description=error_data.get("error_description")
                        )
                        raise Exception(f"Device polling error: {error_code}")
                
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 400:  # 400 errors are handled above
                logger.error(
                    "HTTP error during device token polling",
                    account_id=device_account.account_id,
                    status_code=e.response.status_code
                )
                raise
        
        except Exception as e:
            logger.error(
                "Unexpected error during device token polling",
                account_id=device_account.account_id,
                error=str(e)
            )
            raise
        
        return None
    
    async def refresh_token(
        self,
        account: Account,
        current_token: Token
    ) -> Token:
        """Refresh access token using refresh token."""
        if not current_token.refresh_token:
            raise ValueError("No refresh token available")
        
        token_url = self._get_token_endpoint(account.tenant_id)
        
        data = {
            "client_id": account.client_id,
            "grant_type": "refresh_token",
            "refresh_token": current_token.refresh_token,
            "scope": " ".join(current_token.scopes)
        }
        
        # Add client secret for authorization code flow
        if account.authentication_flow == AuthenticationFlow.AUTHORIZATION_CODE:
            # Note: In a real implementation, you'd need to get the client secret
            # from the AuthorizationCodeAccount. For now, we'll assume it's available.
            pass
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(token_url, data=data, headers=headers)
                response.raise_for_status()
                
                token_data = response.json()
                
                # Calculate expiration time
                expires_in = token_data.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                # Create new token
                new_token = Token(
                    account_id=account.id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", current_token.refresh_token),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=expires_at,
                    scopes=token_data.get("scope", " ".join(current_token.scopes)).split(),
                    status=TokenStatus.VALID,
                    created_at=datetime.utcnow()
                )
                
                logger.info(
                    "Successfully refreshed token",
                    account_id=account.id,
                    expires_at=expires_at,
                    new_refresh_token=token_data.get("refresh_token") != current_token.refresh_token
                )
                
                return new_token
                
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except:
                pass
            
            logger.error(
                "Failed to refresh token",
                account_id=account.id,
                status_code=e.response.status_code,
                error=error_data.get("error"),
                error_description=error_data.get("error_description")
            )
            
            # Mark token as invalid if refresh fails
            current_token.status = TokenStatus.INVALID
            raise
        
        except Exception as e:
            logger.error(
                "Unexpected error during token refresh",
                account_id=account.id,
                error=str(e)
            )
            raise
    
    async def validate_token(self, token: Token) -> bool:
        """Validate token by making a test request to Graph API."""
        headers = {
            "Authorization": f"{token.token_type} {token.access_token}",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers=headers
                )
                
                if response.status_code == 200:
                    logger.debug(
                        "Token validation successful",
                        account_id=token.account_id
                    )
                    return True
                
                elif response.status_code == 401:
                    logger.warning(
                        "Token validation failed - unauthorized",
                        account_id=token.account_id
                    )
                    return False
                
                else:
                    logger.warning(
                        "Token validation failed - unexpected status",
                        account_id=token.account_id,
                        status_code=response.status_code
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Error during token validation",
                account_id=token.account_id,
                error=str(e)
            )
            return False
    
    def is_token_expired(self, token: Token, buffer_minutes: int = 5) -> bool:
        """Check if token is expired or will expire soon."""
        buffer_time = timedelta(minutes=buffer_minutes)
        return datetime.utcnow() + buffer_time >= token.expires_at
    
    async def revoke_token(self, account: Account, token: Token) -> bool:
        """Revoke token (logout)."""
        # Microsoft Graph doesn't have a direct token revocation endpoint
        # Instead, we use the revokeSignInSessions endpoint
        headers = {
            "Authorization": f"{token.token_type} {token.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://graph.microsoft.com/v1.0/me/revokeSignInSessions",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    success = result.get("value", False)
                    
                    logger.info(
                        "Token revocation completed",
                        account_id=account.id,
                        success=success
                    )
                    
                    return success
                
                else:
                    logger.warning(
                        "Token revocation failed",
                        account_id=account.id,
                        status_code=response.status_code
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Error during token revocation",
                account_id=account.id,
                error=str(e)
            )
            return False
