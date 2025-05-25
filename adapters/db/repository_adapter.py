"""Database repository adapter implementation."""

from typing import List, Optional
from adapters.db.database import DatabaseAdapter
from adapters.db.repositories import (
    AccountRepository, AuthFlowRepository, TokenRepository,
    MailRepository, MailQueryHistoryRepository, DeltaLinkRepository,
    WebhookRepository, ExternalAPIRepository, AuthenticationLogRepository
)
from core.domain.entities import (
    Account, AuthorizationCodeAccount, DeviceCodeAccount, Token,
    MailMessage, MailQueryHistory, DeltaLink, WebhookSubscription,
    ExternalAPICall, AuthenticationLog
)


class DatabaseRepositoryAdapter:
    """Database repository adapter that implements all repository ports."""
    
    def __init__(self, db_adapter: DatabaseAdapter):
        self.db_adapter = db_adapter
    
    # Account methods
    async def create_account(self, account: Account) -> Account:
        """Create account."""
        async with self.db_adapter.session_scope() as session:
            repo = AccountRepository(session)
            return await repo.create_account(account)
    
    async def get_account_by_id(self, account_id: str) -> Optional[Account]:
        """Get account by ID."""
        async with self.db_adapter.session_scope() as session:
            repo = AccountRepository(session)
            return await repo.get_account_by_id(account_id)
    
    async def get_account_by_email(self, email: str) -> Optional[Account]:
        """Get account by email."""
        async with self.db_adapter.session_scope() as session:
            repo = AccountRepository(session)
            return await repo.get_account_by_email(email)
    
    async def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        async with self.db_adapter.session_scope() as session:
            repo = AccountRepository(session)
            return await repo.get_all_accounts()
    
    async def update_account(self, account: Account) -> Account:
        """Update account."""
        async with self.db_adapter.session_scope() as session:
            repo = AccountRepository(session)
            return await repo.update_account(account)
    
    async def delete_account(self, account_id: str) -> bool:
        """Delete account."""
        async with self.db_adapter.session_scope() as session:
            repo = AccountRepository(session)
            return await repo.delete_account(account_id)
    
    # Auth flow methods
    async def create_auth_code_account(self, auth_account: AuthorizationCodeAccount) -> AuthorizationCodeAccount:
        """Create authorization code account."""
        async with self.db_adapter.session_scope() as session:
            repo = AuthFlowRepository(session)
            return await repo.create_auth_code_account(auth_account)
    
    async def get_auth_code_account(self, account_id: str) -> Optional[AuthorizationCodeAccount]:
        """Get authorization code account."""
        async with self.db_adapter.session_scope() as session:
            repo = AuthFlowRepository(session)
            return await repo.get_auth_code_account(account_id)
    
    async def create_device_code_account(self, device_account: DeviceCodeAccount) -> DeviceCodeAccount:
        """Create device code account."""
        async with self.db_adapter.session_scope() as session:
            repo = AuthFlowRepository(session)
            return await repo.create_device_code_account(device_account)
    
    async def get_device_code_account(self, account_id: str) -> Optional[DeviceCodeAccount]:
        """Get device code account."""
        async with self.db_adapter.session_scope() as session:
            repo = AuthFlowRepository(session)
            return await repo.get_device_code_account(account_id)
    
    async def update_device_code_account(self, device_account: DeviceCodeAccount) -> DeviceCodeAccount:
        """Update device code account."""
        async with self.db_adapter.session_scope() as session:
            repo = AuthFlowRepository(session)
            return await repo.update_device_code_account(device_account)
    
    # Token methods
    async def save_token(self, token: Token) -> Token:
        """Save token."""
        async with self.db_adapter.session_scope() as session:
            repo = TokenRepository(session)
            return await repo.save_token(token)
    
    async def get_token_by_account_id(self, account_id: str) -> Optional[Token]:
        """Get token by account ID."""
        async with self.db_adapter.session_scope() as session:
            repo = TokenRepository(session)
            return await repo.get_token_by_account_id(account_id)
    
    async def delete_token(self, account_id: str) -> bool:
        """Delete token."""
        async with self.db_adapter.session_scope() as session:
            repo = TokenRepository(session)
            return await repo.delete_token(account_id)
    
    # Mail methods
    async def save_mail_message(self, message: MailMessage) -> MailMessage:
        """Save mail message."""
        async with self.db_adapter.session_scope() as session:
            repo = MailRepository(session)
            return await repo.save_mail_message(message)
    
    async def get_mail_by_message_id(self, message_id: str) -> Optional[MailMessage]:
        """Get mail by message ID."""
        async with self.db_adapter.session_scope() as session:
            repo = MailRepository(session)
            return await repo.get_mail_by_message_id(message_id)
    
    async def mail_exists(self, message_id: str, account_id: str) -> bool:
        """Check if mail exists."""
        async with self.db_adapter.session_scope() as session:
            repo = MailRepository(session)
            return await repo.mail_exists(message_id, account_id)
    
    async def get_mails_by_account(
        self,
        account_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[MailMessage]:
        """Get mails by account."""
        async with self.db_adapter.session_scope() as session:
            repo = MailRepository(session)
            return await repo.get_mails_by_account(account_id, limit, offset)
    
    # Query history methods
    async def save_query_history(self, history: MailQueryHistory) -> MailQueryHistory:
        """Save query history."""
        async with self.db_adapter.session_scope() as session:
            repo = MailQueryHistoryRepository(session)
            return await repo.save_query_history(history)
    
    async def get_query_histories(
        self,
        account_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[MailQueryHistory]:
        """Get query histories."""
        async with self.db_adapter.session_scope() as session:
            repo = MailQueryHistoryRepository(session)
            return await repo.get_query_histories(account_id, limit)
    
    # Auth log methods
    async def save_auth_log(self, log: AuthenticationLog) -> AuthenticationLog:
        """Save authentication log."""
        async with self.db_adapter.session_scope() as session:
            repo = AuthenticationLogRepository(session)
            return await repo.save_auth_log(log)
    
    async def get_auth_logs(
        self,
        account_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        success: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[AuthenticationLog]:
        """Get authentication logs."""
        async with self.db_adapter.session_scope() as session:
            repo = AuthenticationLogRepository(session)
            return await repo.get_auth_logs(account_id, date_from, date_to, success, limit)
    
    # Delta link methods
    async def save_delta_link(self, delta_link: DeltaLink) -> DeltaLink:
        """Save delta link."""
        async with self.db_adapter.session_scope() as session:
            repo = DeltaLinkRepository(session)
            return await repo.save_delta_link(delta_link)
    
    async def get_delta_link(self, account_id: str, folder_id: str) -> Optional[DeltaLink]:
        """Get delta link."""
        async with self.db_adapter.session_scope() as session:
            repo = DeltaLinkRepository(session)
            return await repo.get_delta_link(account_id, folder_id)
    
    # Webhook methods
    async def save_webhook_subscription(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Save webhook subscription."""
        async with self.db_adapter.session_scope() as session:
            repo = WebhookRepository(session)
            return await repo.save_webhook_subscription(subscription)
    
    async def get_webhook_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Get webhook subscription."""
        async with self.db_adapter.session_scope() as session:
            repo = WebhookRepository(session)
            return await repo.get_webhook_subscription(subscription_id)
    
    # External API methods
    async def save_external_api_call(self, api_call: ExternalAPICall) -> ExternalAPICall:
        """Save external API call."""
        async with self.db_adapter.session_scope() as session:
            repo = ExternalAPIRepository(session)
            return await repo.save_external_api_call(api_call)
    
    async def get_external_api_calls(
        self,
        account_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ExternalAPICall]:
        """Get external API calls."""
        async with self.db_adapter.session_scope() as session:
            repo = ExternalAPIRepository(session)
            return await repo.get_external_api_calls(account_id, limit)
