"""Port interfaces for the Microsoft Graph API Mail Collection System."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime

from core.domain.entities import (
    Account, AuthorizationCodeAccount, DeviceCodeAccount, Token,
    MailMessage, MailAttachment, MailQueryHistory, DeltaLink,
    WebhookSubscription, AuthenticationLog, ExternalAPICall,
    NotificationRule, AuthenticationFlow, MailDirection, MailImportance
)


class AccountRepositoryPort(ABC):
    """Port for account data persistence."""
    
    @abstractmethod
    async def create_account(self, account: Account) -> Account:
        """Create a new account."""
        pass
    
    @abstractmethod
    async def get_account_by_id(self, account_id: str) -> Optional[Account]:
        """Get account by ID."""
        pass
    
    @abstractmethod
    async def get_account_by_email(self, email: str) -> Optional[Account]:
        """Get account by email."""
        pass
    
    @abstractmethod
    async def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        pass
    
    @abstractmethod
    async def update_account(self, account: Account) -> Account:
        """Update an existing account."""
        pass
    
    @abstractmethod
    async def delete_account(self, account_id: str) -> bool:
        """Delete an account."""
        pass
    
    @abstractmethod
    async def search_accounts(self, query: str) -> List[Account]:
        """Search accounts by query."""
        pass


class AuthFlowRepositoryPort(ABC):
    """Port for authentication flow specific data."""
    
    @abstractmethod
    async def create_auth_code_account(self, auth_account: AuthorizationCodeAccount) -> AuthorizationCodeAccount:
        """Create authorization code account data."""
        pass
    
    @abstractmethod
    async def get_auth_code_account(self, account_id: str) -> Optional[AuthorizationCodeAccount]:
        """Get authorization code account data."""
        pass
    
    @abstractmethod
    async def create_device_code_account(self, device_account: DeviceCodeAccount) -> DeviceCodeAccount:
        """Create device code account data."""
        pass
    
    @abstractmethod
    async def get_device_code_account(self, account_id: str) -> Optional[DeviceCodeAccount]:
        """Get device code account data."""
        pass
    
    @abstractmethod
    async def update_device_code_account(self, device_account: DeviceCodeAccount) -> DeviceCodeAccount:
        """Update device code account data."""
        pass


class TokenRepositoryPort(ABC):
    """Port for token data persistence."""
    
    @abstractmethod
    async def save_token(self, token: Token) -> Token:
        """Save or update a token."""
        pass
    
    @abstractmethod
    async def get_token_by_account_id(self, account_id: str) -> Optional[Token]:
        """Get token by account ID."""
        pass
    
    @abstractmethod
    async def get_all_tokens(self) -> List[Token]:
        """Get all tokens."""
        pass
    
    @abstractmethod
    async def delete_token(self, account_id: str) -> bool:
        """Delete a token."""
        pass
    
    @abstractmethod
    async def get_expired_tokens(self) -> List[Token]:
        """Get all expired tokens."""
        pass


class MailRepositoryPort(ABC):
    """Port for mail data persistence."""
    
    @abstractmethod
    async def save_mail_message(self, message: MailMessage) -> MailMessage:
        """Save a mail message."""
        pass
    
    @abstractmethod
    async def get_mail_by_message_id(self, message_id: str) -> Optional[MailMessage]:
        """Get mail by message ID."""
        pass
    
    @abstractmethod
    async def get_mails_by_account_id(
        self, 
        account_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[MailMessage]:
        """Get mails by account ID."""
        pass
    
    @abstractmethod
    async def search_mails(
        self,
        account_id: Optional[str] = None,
        sender_email: Optional[str] = None,
        subject_contains: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        is_read: Optional[bool] = None,
        importance: Optional[MailImportance] = None,
        direction: Optional[MailDirection] = None,
        limit: Optional[int] = None
    ) -> List[MailMessage]:
        """Search mails with filters."""
        pass
    
    @abstractmethod
    async def mail_exists(self, message_id: str, account_id: str) -> bool:
        """Check if mail exists."""
        pass


class MailQueryHistoryRepositoryPort(ABC):
    """Port for mail query history persistence."""
    
    @abstractmethod
    async def save_query_history(self, history: MailQueryHistory) -> MailQueryHistory:
        """Save query history."""
        pass
    
    @abstractmethod
    async def get_query_history(
        self,
        account_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[MailQueryHistory]:
        """Get query history with filters."""
        pass


class DeltaLinkRepositoryPort(ABC):
    """Port for delta link persistence."""
    
    @abstractmethod
    async def save_delta_link(self, delta_link: DeltaLink) -> DeltaLink:
        """Save or update delta link."""
        pass
    
    @abstractmethod
    async def get_delta_link(self, account_id: str, folder_id: str = "Inbox") -> Optional[DeltaLink]:
        """Get delta link for account and folder."""
        pass
    
    @abstractmethod
    async def delete_delta_link(self, account_id: str, folder_id: str = "Inbox") -> bool:
        """Delete delta link."""
        pass


class WebhookRepositoryPort(ABC):
    """Port for webhook subscription persistence."""
    
    @abstractmethod
    async def save_webhook_subscription(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Save webhook subscription."""
        pass
    
    @abstractmethod
    async def get_webhook_subscription(self, account_id: str) -> Optional[WebhookSubscription]:
        """Get webhook subscription by account ID."""
        pass
    
    @abstractmethod
    async def get_expired_subscriptions(self) -> List[WebhookSubscription]:
        """Get expired webhook subscriptions."""
        pass
    
    @abstractmethod
    async def delete_webhook_subscription(self, subscription_id: str) -> bool:
        """Delete webhook subscription."""
        pass


class AuthenticationLogRepositoryPort(ABC):
    """Port for authentication log persistence."""
    
    @abstractmethod
    async def save_auth_log(self, log: AuthenticationLog) -> AuthenticationLog:
        """Save authentication log."""
        pass
    
    @abstractmethod
    async def get_auth_logs(
        self,
        account_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[AuthenticationLog]:
        """Get authentication logs with filters."""
        pass


class ExternalAPIRepositoryPort(ABC):
    """External API repository port."""
    
    @abstractmethod
    async def save_api_call(self, api_call: ExternalAPICall) -> ExternalAPICall:
        """Save API call record."""
        pass
    
    @abstractmethod
    async def get_failed_api_calls(self, limit: Optional[int] = None) -> List[ExternalAPICall]:
        """Get failed API calls for retry."""
        pass


# External service ports
class GraphAPIClientPort(ABC):
    """Graph API client port."""
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information."""
        pass
    
    @abstractmethod
    async def query_messages(
        self,
        access_token: str,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
        select_fields: Optional[List[str]] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None
    ) -> Dict[str, Any]:
        """Query messages from Graph API."""
        pass
    
    @abstractmethod
    async def send_message(
        self,
        access_token: str,
        user_id: str,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send message via Graph API."""
        pass
    
    @abstractmethod
    async def get_delta_messages(
        self,
        access_token: str,
        user_id: str,
        delta_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get delta messages."""
        pass


class OAuthClientPort(ABC):
    """OAuth client port."""
    
    @abstractmethod
    async def get_authorization_url(
        self,
        scopes: List[str],
        state: Optional[str] = None
    ) -> Tuple[str, str]:
        """Get authorization URL and state."""
        pass
    
    @abstractmethod
    async def exchange_code_for_token(
        self,
        code: str,
        state: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for token."""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        pass
    
    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """Revoke token."""
        pass


class ExternalAPIClientPort(ABC):
    """Port for external API client (embedding service)."""
    
    @abstractmethod
    async def send_mail_data(
        self,
        endpoint_url: str,
        mail_data: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Send mail data to external API."""
        pass


class NotificationServicePort(ABC):
    """Port for notification service."""
    
    @abstractmethod
    async def send_notification(
        self,
        channel: str,
        message: str,
        webhook_url: Optional[str] = None
    ) -> bool:
        """Send notification to specified channel."""
        pass


class CacheServicePort(ABC):
    """Port for caching service."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass


class CachePort(ABC):
    """Enhanced cache port for advanced caching operations."""
    
    @abstractmethod
    async def connect(self):
        """Establish cache connection."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close cache connection."""
        pass
    
    @abstractmethod
    async def get(self, key: str, prefix: str = "") -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        prefix: str = ""
    ) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str, prefix: str = "") -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str, prefix: str = "") -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """Get cache health status."""
        pass


class ConfigPort(ABC):
    """Port for configuration management."""
    
    @abstractmethod
    def get_database_url(self) -> str:
        """Get database URL."""
        pass
    
    @abstractmethod
    def get_microsoft_graph_config(self) -> Dict[str, Any]:
        """Get Microsoft Graph configuration."""
        pass
    
    @abstractmethod
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration."""
        pass
    
    @abstractmethod
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration."""
        pass
    
    @abstractmethod
    def get_external_api_config(self) -> Dict[str, Any]:
        """Get external API configuration."""
        pass
