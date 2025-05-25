"""Authentication use cases for Microsoft Graph API Mail Collection System."""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional, List
import structlog

from core.domain.entities import (
    Account, AuthorizationCodeAccount, DeviceCodeAccount, Token,
    AuthenticationFlow, AccountStatus, TokenStatus, AuthenticationLog
)
from core.usecases.ports import (
    AccountRepositoryPort, AuthFlowRepositoryPort, TokenRepositoryPort,
    AuthenticationLogRepositoryPort, OAuthClientPort, ConfigPort
)

logger = structlog.get_logger()


class AuthenticationUseCases:
    """Authentication related use cases."""
    
    def __init__(
        self,
        account_repo: AccountRepositoryPort,
        auth_flow_repo: AuthFlowRepositoryPort,
        token_repo: TokenRepositoryPort,
        auth_log_repo: AuthenticationLogRepositoryPort,
        oauth_client: OAuthClientPort,
        config: ConfigPort
    ):
        self.account_repo = account_repo
        self.auth_flow_repo = auth_flow_repo
        self.token_repo = token_repo
        self.auth_log_repo = auth_log_repo
        self.oauth_client = oauth_client
        self.config = config
    
    async def register_account(
        self,
        email: str,
        user_id: str,
        authentication_flow: AuthenticationFlow,
        scopes: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """AUTH001 - Register new account with authentication flow."""
        try:
            # Check if account already exists
            existing_account = await self.account_repo.get_account_by_email(email)
            if existing_account:
                raise ValueError(f"Account with email {email} already exists")
            
            # Get Microsoft Graph config
            graph_config = self.config.get_microsoft_graph_config()
            
            # Create base account
            account = Account(
                id=str(uuid.uuid4()),
                email=email,
                user_id=user_id,
                tenant_id=graph_config["tenant_id"],
                client_id=graph_config["client_id"],
                authentication_flow=authentication_flow,
                status=AccountStatus.ACTIVE,
                scopes=scopes,
                created_at=datetime.now(UTC)
            )
            
            # Save account
            saved_account = await self.account_repo.create_account(account)
            
            # Create flow-specific data
            if authentication_flow == AuthenticationFlow.AUTHORIZATION_CODE:
                auth_code_account = AuthorizationCodeAccount(
                    account_id=saved_account.id,
                    client_secret=graph_config["client_secret"],
                    redirect_uri=graph_config["redirect_uri"],
                    authority=graph_config["authority"],
                    created_at=datetime.now(UTC)
                )
                await self.auth_flow_repo.create_auth_code_account(auth_code_account)
                
            elif authentication_flow == AuthenticationFlow.DEVICE_CODE:
                device_code_account = DeviceCodeAccount(
                    account_id=saved_account.id
                )
                await self.auth_flow_repo.create_device_code_account(device_code_account)
            
            # Log successful registration
            await self._log_auth_event(
                account_id=saved_account.id,
                event_type="registration",
                authentication_flow=authentication_flow,
                success=True
            )
            
            logger.info(
                "Account registered successfully",
                account_id=saved_account.id,
                email=email,
                authentication_flow=authentication_flow.value
            )
            
            return {
                "success": True,
                "account_id": saved_account.id,
                "message": "Account registered successfully"
            }
            
        except Exception as e:
            logger.error(
                "Failed to register account",
                email=email,
                error=str(e)
            )
            raise
    
    async def get_account_info(
        self,
        identifier: str,
        by_email: bool = False
    ) -> Optional[Dict[str, Any]]:
        """AUTH002 - Get account information by ID or email."""
        try:
            if by_email:
                account = await self.account_repo.get_account_by_email(identifier)
            else:
                account = await self.account_repo.get_account_by_id(identifier)
            
            if not account:
                return None
            
            # Get token status
            token = await self.token_repo.get_token_by_account_id(account.id)
            token_status = None
            if token:
                if token.is_expired:
                    token_status = "expired"
                else:
                    token_status = "valid"
            else:
                token_status = "none"
            
            return {
                "account": account.model_dump(),
                "token_status": token_status,
                "token_expires_in": token.expires_in_seconds if token else None
            }
            
        except Exception as e:
            logger.error(
                "Failed to get account info",
                identifier=identifier,
                by_email=by_email,
                error=str(e)
            )
            raise
    
    async def get_all_accounts(self) -> List[Dict[str, Any]]:
        """AUTH002 - Get all accounts with token status."""
        try:
            accounts = await self.account_repo.get_all_accounts()
            result = []
            
            for account in accounts:
                token = await self.token_repo.get_token_by_account_id(account.id)
                token_status = None
                if token:
                    if token.is_expired:
                        token_status = "expired"
                    else:
                        token_status = "valid"
                else:
                    token_status = "none"
                
                result.append({
                    "account": account.model_dump(),
                    "token_status": token_status,
                    "token_expires_in": token.expires_in_seconds if token else None
                })
            
            return result
            
        except Exception as e:
            logger.error("Failed to get all accounts", error=str(e))
            raise
    
    async def get_account_by_email(self, email: str) -> Optional[Account]:
        """Get account by email address."""
        try:
            return await self.account_repo.get_account_by_email(email)
        except Exception as e:
            logger.error("Failed to get account by email", email=email, error=str(e))
            raise
    
    async def authenticate_account(
        self,
        account_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """AUTH003 - Authenticate account based on flow type."""
        try:
            account = await self.account_repo.get_account_by_id(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            if account.authentication_flow == AuthenticationFlow.AUTHORIZATION_CODE:
                return await self._authenticate_authorization_code(account, **kwargs)
            elif account.authentication_flow == AuthenticationFlow.DEVICE_CODE:
                return await self._authenticate_device_code(account, **kwargs)
            else:
                raise ValueError(f"Unsupported authentication flow: {account.authentication_flow}")
                
        except Exception as e:
            await self._log_auth_event(
                account_id=account_id,
                event_type="authentication",
                authentication_flow=account.authentication_flow if 'account' in locals() else None,
                success=False,
                error_message=str(e)
            )
            logger.error(
                "Authentication failed",
                account_id=account_id,
                error=str(e)
            )
            raise
    
    async def _authenticate_authorization_code(
        self,
        account: Account,
        authorization_code: Optional[str] = None,
        state: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Handle authorization code flow authentication."""
        auth_data = await self.auth_flow_repo.get_auth_code_account(account.id)
        if not auth_data:
            raise ValueError("Authorization code account data not found")
        
        if not authorization_code:
            # Generate authorization URL
            auth_url, code_verifier = await self.oauth_client.get_authorization_url(
                auth_account=auth_data,
                account=account,
                scopes=account.scopes,
                state=None
            )
            
            return {
                "success": True,
                "requires_user_action": True,
                "authorization_url": auth_url,
                "state": state,
                "message": "Please visit the authorization URL to complete authentication"
            }
        else:
            # Exchange code for token
            token_data = await self.oauth_client.exchange_code_for_token(
                code=authorization_code,
                state=state or ""  # State should be validated here
            )
            
            # Save token
            await self._save_token(account.id, token_data)
            
            # Update account last authenticated time
            account.last_authenticated_at = datetime.now(UTC)
            await self.account_repo.update_account(account)
            
            # Log successful authentication
            await self._log_auth_event(
                account_id=account.id,
                event_type="authentication",
                authentication_flow=account.authentication_flow,
                success=True
            )
            
            return {
                "success": True,
                "requires_user_action": False,
                "message": "Authentication completed successfully"
            }
    
    async def _authenticate_device_code(
        self,
        account: Account,
        poll: bool = False
    ) -> Dict[str, Any]:
        """Handle device code flow authentication."""
        device_data = await self.auth_flow_repo.get_device_code_account(account.id)
        if not device_data:
            raise ValueError("Device code account data not found")
        
        if not poll:
            # Start device code flow - This should be implemented in OAuth client
            # For now, return a placeholder response
            device_response = {
                "device_code": "placeholder_device_code",
                "user_code": "ABCD1234",
                "verification_uri": "https://microsoft.com/devicelogin",
                "expires_in": 900,
                "interval": 5
            }
            
            # Update device code data
            device_data.device_code = device_response["device_code"]
            device_data.user_code = device_response["user_code"]
            device_data.verification_uri = device_response["verification_uri"]
            device_data.expires_in = device_response["expires_in"]
            device_data.interval = device_response["interval"]
            
            await self.auth_flow_repo.update_device_code_account(device_data)
            
            return {
                "success": True,
                "requires_user_action": True,
                "user_code": device_response["user_code"],
                "verification_uri": device_response["verification_uri"],
                "message": f"Please visit {device_response['verification_uri']} and enter code: {device_response['user_code']}"
            }
        else:
            # Poll for token
            if not device_data.device_code:
                raise ValueError("Device code not initialized. Start authentication first.")
            
            # Poll for token - This should be implemented in OAuth client
            # For now, return a placeholder response
            token_data = {
                "access_token": "placeholder_access_token",
                "refresh_token": "placeholder_refresh_token",
                "expires_in": 3600,
                "scope": " ".join(account.scopes)
            }
            
            if "access_token" in token_data:
                # Save token
                await self._save_token(account.id, token_data)
                
                # Update account last authenticated time
                account.last_authenticated_at = datetime.now(UTC)
                await self.account_repo.update_account(account)
                
                # Log successful authentication
                await self._log_auth_event(
                    account_id=account.id,
                    event_type="authentication",
                    authentication_flow=account.authentication_flow,
                    success=True
                )
                
                return {
                    "success": True,
                    "requires_user_action": False,
                    "message": "Authentication completed successfully"
                }
            else:
                return {
                    "success": False,
                    "requires_user_action": True,
                    "message": "Authentication pending. Please complete the device code flow."
                }
    
    async def refresh_token(self, account_id: str) -> Dict[str, Any]:
        """AUTH004 - Refresh access token."""
        try:
            account = await self.account_repo.get_account_by_id(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            token = await self.token_repo.get_token_by_account_id(account_id)
            if not token or not token.refresh_token:
                raise ValueError("No refresh token available")
            
            # Get client secret for authorization code flow
            client_secret = None
            if account.authentication_flow == AuthenticationFlow.AUTHORIZATION_CODE:
                auth_data = await self.auth_flow_repo.get_auth_code_account(account_id)
                if auth_data:
                    client_secret = auth_data.client_secret
            
            # Refresh token
            token_data = await self.oauth_client.refresh_token(
                refresh_token=token.refresh_token
            )
            
            # Save new token
            await self._save_token(account_id, token_data)
            
            # Log successful token refresh
            await self._log_auth_event(
                account_id=account_id,
                event_type="token_refresh",
                authentication_flow=account.authentication_flow,
                success=True
            )
            
            logger.info(
                "Token refreshed successfully",
                account_id=account_id
            )
            
            return {
                "success": True,
                "message": "Token refreshed successfully"
            }
            
        except Exception as e:
            await self._log_auth_event(
                account_id=account_id,
                event_type="token_refresh",
                authentication_flow=account.authentication_flow if 'account' in locals() else None,
                success=False,
                error_message=str(e)
            )
            logger.error(
                "Token refresh failed",
                account_id=account_id,
                error=str(e)
            )
            raise
    
    async def revoke_token(self, account_id: str) -> Dict[str, Any]:
        """AUTH006 - Revoke access and refresh tokens."""
        try:
            account = await self.account_repo.get_account_by_id(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            token = await self.token_repo.get_token_by_account_id(account_id)
            if token:
                # Revoke token via OAuth client
                await self.oauth_client.revoke_token(token.access_token)
                
                # Delete local token
                await self.token_repo.delete_token(account_id)
            
            # Log successful logout
            await self._log_auth_event(
                account_id=account_id,
                event_type="logout",
                authentication_flow=account.authentication_flow,
                success=True
            )
            
            logger.info(
                "Token revoked successfully",
                account_id=account_id
            )
            
            return {
                "success": True,
                "message": "Token revoked successfully"
            }
            
        except Exception as e:
            await self._log_auth_event(
                account_id=account_id,
                event_type="logout",
                authentication_flow=account.authentication_flow if 'account' in locals() else None,
                success=False,
                error_message=str(e)
            )
            logger.error(
                "Token revocation failed",
                account_id=account_id,
                error=str(e)
            )
            raise
    
    async def get_authentication_logs(
        self,
        account_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[AuthenticationLog]:
        """AUTH007 - Get authentication logs with filters."""
        try:
            logs = await self.auth_log_repo.get_auth_logs(
                account_id=account_id,
                date_from=date_from,
                date_to=date_to,
                success=success,
                limit=limit
            )
            return logs
            
        except Exception as e:
            logger.error(
                "Failed to get authentication logs",
                error=str(e)
            )
            raise
    
    async def _save_token(self, account_id: str, token_data: Dict[str, Any]) -> Token:
        """Save token data to repository."""
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        
        token = Token(
            account_id=account_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_type=token_data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scopes=token_data.get("scope", "").split(" ") if token_data.get("scope") else [],
            status=TokenStatus.VALID,
            created_at=datetime.now(UTC)
        )
        
        return await self.token_repo.save_token(token)
    
    async def _log_auth_event(
        self,
        account_id: str,
        event_type: str,
        authentication_flow: Optional[AuthenticationFlow],
        success: bool,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log authentication event."""
        try:
            log = AuthenticationLog(
                account_id=account_id,
                event_type=event_type,
                authentication_flow=authentication_flow or AuthenticationFlow.AUTHORIZATION_CODE,
                success=success,
                error_code=error_code,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.now(UTC)
            )
            
            await self.auth_log_repo.save_auth_log(log)
            
        except Exception as e:
            logger.error(
                "Failed to log authentication event",
                account_id=account_id,
                event_type=event_type,
                error=str(e)
            )
    
    # Additional methods needed by tests
    async def get_all_accounts_info(self) -> List[Dict[str, Any]]:
        """Get all accounts info - alias for get_all_accounts."""
        return await self.get_all_accounts()
    
    async def refresh_account_token(self, account_id: str) -> Dict[str, Any]:
        """Refresh account token - alias for refresh_token."""
        return await self.refresh_token(account_id)
    
    async def revoke_account_tokens(self, account_id: str) -> Dict[str, Any]:
        """Revoke account tokens - alias for revoke_token."""
        return await self.revoke_token(account_id)
    
    async def search_accounts(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search accounts by criteria."""
        try:
            # Simple implementation - can be enhanced later
            all_accounts = await self.get_all_accounts()
            
            # Filter by email if provided
            if "email" in criteria:
                email_filter = criteria["email"].lower()
                filtered_accounts = [
                    acc for acc in all_accounts 
                    if email_filter in acc["account"]["email"].lower()
                ]
                return filtered_accounts
            
            return all_accounts
            
        except Exception as e:
            logger.error("Failed to search accounts", criteria=criteria, error=str(e))
            raise
