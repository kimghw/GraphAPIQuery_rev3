"""Database repository implementations."""

from datetime import datetime, UTC
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from core.domain.entities import (
    Account, AuthorizationCodeAccount, DeviceCodeAccount, Token,
    MailMessage, MailQueryHistory, DeltaLink, WebhookSubscription,
    ExternalAPICall, AuthenticationLog, AuthenticationFlow
)
from core.usecases.ports import (
    AccountRepositoryPort, AuthFlowRepositoryPort, TokenRepositoryPort,
    MailRepositoryPort, MailQueryHistoryRepositoryPort, DeltaLinkRepositoryPort,
    WebhookRepositoryPort, ExternalAPIRepositoryPort, AuthenticationLogRepositoryPort
)
from adapters.db.models import (
    AccountModel, AuthorizationCodeAccountModel, DeviceCodeAccountModel,
    TokenModel, MailMessageModel, MailQueryHistoryModel, DeltaLinkModel,
    WebhookSubscriptionModel, ExternalAPICallModel, AuthenticationLogModel
)
from adapters.db.database import DatabaseAdapter

logger = structlog.get_logger()


class AccountRepository(AccountRepositoryPort):
    """Account repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_account(self, account: Account) -> Account:
        """Create a new account."""
        model = AccountModel(
            id=account.id,
            email=account.email,
            user_id=account.user_id,
            tenant_id=account.tenant_id,
            client_id=account.client_id,
            authentication_flow=account.authentication_flow,
            status=account.status,
            scopes=account.scopes,
            created_at=account.created_at,
            last_authenticated_at=account.last_authenticated_at
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._model_to_entity(model)
    
    async def get_account_by_id(self, account_id: str) -> Optional[Account]:
        """Get account by ID."""
        stmt = select(AccountModel).where(AccountModel.id == account_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def get_account_by_email(self, email: str) -> Optional[Account]:
        """Get account by email."""
        stmt = select(AccountModel).where(AccountModel.email == email)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def get_all_accounts(self) -> List[Account]:
        """Get all accounts."""
        stmt = select(AccountModel).order_by(AccountModel.created_at.desc())
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def update_account(self, account: Account) -> Account:
        """Update account."""
        stmt = (
            update(AccountModel)
            .where(AccountModel.id == account.id)
            .values(
                email=account.email,
                user_id=account.user_id,
                tenant_id=account.tenant_id,
                client_id=account.client_id,
                authentication_flow=account.authentication_flow,
                status=account.status,
                scopes=account.scopes,
                updated_at=datetime.now(UTC),
                last_authenticated_at=account.last_authenticated_at
            )
        )
        
        await self.session.execute(stmt)
        return await self.get_account_by_id(account.id)
    
    async def delete_account(self, account_id: str) -> bool:
        """Delete account."""
        stmt = delete(AccountModel).where(AccountModel.id == account_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def search_accounts(self, filters: Dict[str, Any]) -> List[Account]:
        """Search accounts with filters."""
        stmt = select(AccountModel)
        
        conditions = []
        
        # Email filter
        if "email" in filters and filters["email"]:
            conditions.append(AccountModel.email.ilike(f"%{filters['email']}%"))
        
        # User ID filter
        if "user_id" in filters and filters["user_id"]:
            conditions.append(AccountModel.user_id == filters["user_id"])
        
        # Tenant ID filter
        if "tenant_id" in filters and filters["tenant_id"]:
            conditions.append(AccountModel.tenant_id == filters["tenant_id"])
        
        # Authentication flow filter
        if "authentication_flow" in filters and filters["authentication_flow"]:
            conditions.append(AccountModel.authentication_flow == filters["authentication_flow"])
        
        # Status filter
        if "status" in filters and filters["status"]:
            conditions.append(AccountModel.status == filters["status"])
        
        # Apply conditions
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Order by created_at desc
        stmt = stmt.order_by(AccountModel.created_at.desc())
        
        # Apply limit if specified
        if "limit" in filters and filters["limit"]:
            stmt = stmt.limit(filters["limit"])
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: AccountModel) -> Account:
        """Convert model to entity."""
        return Account(
            id=model.id,
            email=model.email,
            user_id=model.user_id,
            tenant_id=model.tenant_id,
            client_id=model.client_id,
            authentication_flow=model.authentication_flow,
            status=model.status,
            scopes=model.scopes,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_authenticated_at=model.last_authenticated_at
        )


class AuthFlowRepository(AuthFlowRepositoryPort):
    """Authentication flow repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_auth_code_account(self, auth_account: AuthorizationCodeAccount) -> AuthorizationCodeAccount:
        """Create authorization code account."""
        model = AuthorizationCodeAccountModel(
            account_id=auth_account.account_id,
            client_secret=auth_account.client_secret,
            redirect_uri=auth_account.redirect_uri,
            authority=auth_account.authority,
            created_at=auth_account.created_at
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._auth_code_model_to_entity(model)
    
    async def get_auth_code_account(self, account_id: str) -> Optional[AuthorizationCodeAccount]:
        """Get authorization code account."""
        stmt = select(AuthorizationCodeAccountModel).where(
            AuthorizationCodeAccountModel.account_id == account_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._auth_code_model_to_entity(model) if model else None
    
    async def create_device_code_account(self, device_account: DeviceCodeAccount) -> DeviceCodeAccount:
        """Create device code account."""
        model = DeviceCodeAccountModel(
            account_id=device_account.account_id,
            device_code=device_account.device_code,
            user_code=device_account.user_code,
            verification_uri=device_account.verification_uri,
            expires_in=device_account.expires_in,
            interval=device_account.interval,
            created_at=device_account.created_at
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._device_code_model_to_entity(model)
    
    async def get_device_code_account(self, account_id: str) -> Optional[DeviceCodeAccount]:
        """Get device code account."""
        stmt = select(DeviceCodeAccountModel).where(
            DeviceCodeAccountModel.account_id == account_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._device_code_model_to_entity(model) if model else None
    
    async def update_device_code_account(self, device_account: DeviceCodeAccount) -> DeviceCodeAccount:
        """Update device code account."""
        stmt = (
            update(DeviceCodeAccountModel)
            .where(DeviceCodeAccountModel.account_id == device_account.account_id)
            .values(
                device_code=device_account.device_code,
                user_code=device_account.user_code,
                verification_uri=device_account.verification_uri,
                expires_in=device_account.expires_in,
                interval=device_account.interval,
                updated_at=datetime.now(UTC)
            )
        )
        
        await self.session.execute(stmt)
        return await self.get_device_code_account(device_account.account_id)
    
    def _auth_code_model_to_entity(self, model: AuthorizationCodeAccountModel) -> AuthorizationCodeAccount:
        """Convert auth code model to entity."""
        return AuthorizationCodeAccount(
            account_id=model.account_id,
            client_secret=model.client_secret,
            redirect_uri=model.redirect_uri,
            authority=model.authority,
            created_at=model.created_at
        )
    
    def _device_code_model_to_entity(self, model: DeviceCodeAccountModel) -> DeviceCodeAccount:
        """Convert device code model to entity."""
        return DeviceCodeAccount(
            account_id=model.account_id,
            device_code=model.device_code,
            user_code=model.user_code,
            verification_uri=model.verification_uri,
            expires_in=model.expires_in,
            interval=model.interval,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


class TokenRepository(TokenRepositoryPort):
    """Token repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_token(self, token: Token) -> Token:
        """Save or update token."""
        # Check if token exists
        existing_stmt = select(TokenModel).where(TokenModel.account_id == token.account_id)
        result = await self.session.execute(existing_stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing token
            stmt = (
                update(TokenModel)
                .where(TokenModel.account_id == token.account_id)
                .values(
                    access_token=token.access_token,
                    refresh_token=token.refresh_token,
                    token_type=token.token_type,
                    expires_at=token.expires_at,
                    scopes=token.scopes,
                    status=token.status,
                    updated_at=datetime.now(UTC)
                )
            )
            await self.session.execute(stmt)
        else:
            # Create new token
            model = TokenModel(
                account_id=token.account_id,
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                token_type=token.token_type,
                expires_at=token.expires_at,
                scopes=token.scopes,
                status=token.status,
                created_at=token.created_at
            )
            self.session.add(model)
        
        await self.session.flush()
        return await self.get_token_by_account_id(token.account_id)
    
    async def get_token_by_account_id(self, account_id: str) -> Optional[Token]:
        """Get token by account ID."""
        stmt = select(TokenModel).where(TokenModel.account_id == account_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def delete_token(self, account_id: str) -> bool:
        """Delete token."""
        stmt = delete(TokenModel).where(TokenModel.account_id == account_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def get_all_tokens(self) -> List[Token]:
        """Get all tokens."""
        stmt = select(TokenModel).order_by(TokenModel.created_at.desc())
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    async def get_expired_tokens(self) -> List[Token]:
        """Get expired tokens."""
        stmt = select(TokenModel).where(
            TokenModel.expires_at <= datetime.now(UTC)
        ).order_by(TokenModel.expires_at.asc())
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: TokenModel) -> Token:
        """Convert model to entity."""
        return Token(
            account_id=model.account_id,
            access_token=model.access_token,
            refresh_token=model.refresh_token,
            token_type=model.token_type,
            expires_at=model.expires_at,
            scopes=model.scopes,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at
        )


class MailRepository(MailRepositoryPort):
    """Mail repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_mail_message(self, message: MailMessage) -> MailMessage:
        """Save mail message."""
        model = MailMessageModel(
            message_id=message.message_id,
            internet_message_id=message.internet_message_id,
            account_id=message.account_id,
            subject=message.subject,
            sender_email=message.sender_email,
            sender_name=message.sender_name,
            recipients=message.recipients,
            cc_recipients=message.cc_recipients,
            bcc_recipients=message.bcc_recipients,
            body_preview=message.body_preview,
            body_content=message.body_content,
            body_content_type=message.body_content_type,
            importance=message.importance,
            is_read=message.is_read,
            has_attachments=message.has_attachments,
            received_datetime=message.received_datetime,
            sent_datetime=message.sent_datetime,
            direction=message.direction,
            categories=message.categories,
            created_at=message.created_at
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._model_to_entity(model)
    
    async def get_mail_by_message_id(self, message_id: str) -> Optional[MailMessage]:
        """Get mail by message ID."""
        stmt = select(MailMessageModel).where(MailMessageModel.message_id == message_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    async def mail_exists(self, message_id: str, account_id: str) -> bool:
        """Check if mail exists."""
        stmt = select(MailMessageModel.id).where(
            and_(
                MailMessageModel.message_id == message_id,
                MailMessageModel.account_id == account_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    async def get_mails_by_account(
        self,
        account_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[MailMessage]:
        """Get mails by account."""
        stmt = select(MailMessageModel).where(
            MailMessageModel.account_id == account_id
        ).order_by(MailMessageModel.received_datetime.desc())
        
        if limit:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: MailMessageModel) -> MailMessage:
        """Convert model to entity."""
        return MailMessage(
            message_id=model.message_id,
            internet_message_id=model.internet_message_id,
            account_id=model.account_id,
            subject=model.subject,
            sender_email=model.sender_email,
            sender_name=model.sender_name,
            recipients=model.recipients,
            cc_recipients=model.cc_recipients,
            bcc_recipients=model.bcc_recipients,
            body_preview=model.body_preview,
            body_content=model.body_content,
            body_content_type=model.body_content_type,
            importance=model.importance,
            is_read=model.is_read,
            has_attachments=model.has_attachments,
            received_datetime=model.received_datetime,
            sent_datetime=model.sent_datetime,
            direction=model.direction,
            categories=model.categories,
            created_at=model.created_at
        )


class MailQueryHistoryRepository(MailQueryHistoryRepositoryPort):
    """Mail query history repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_query_history(self, history: MailQueryHistory) -> MailQueryHistory:
        """Save query history."""
        model = MailQueryHistoryModel(
            account_id=history.account_id,
            query_type=history.query_type,
            query_parameters=history.query_parameters,
            messages_found=history.messages_found,
            new_messages=history.new_messages,
            query_datetime=history.query_datetime,
            execution_time_ms=history.execution_time_ms,
            success=history.success,
            error_message=history.error_message
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._model_to_entity(model)
    
    async def get_query_histories(
        self,
        account_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[MailQueryHistory]:
        """Get query histories."""
        stmt = select(MailQueryHistoryModel)
        
        if account_id:
            stmt = stmt.where(MailQueryHistoryModel.account_id == account_id)
        
        stmt = stmt.order_by(MailQueryHistoryModel.query_datetime.desc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: MailQueryHistoryModel) -> MailQueryHistory:
        """Convert model to entity."""
        return MailQueryHistory(
            account_id=model.account_id,
            query_type=model.query_type,
            query_parameters=model.query_parameters,
            messages_found=model.messages_found,
            new_messages=model.new_messages,
            query_datetime=model.query_datetime,
            execution_time_ms=model.execution_time_ms,
            success=model.success,
            error_message=model.error_message
        )


class DeltaLinkRepository(DeltaLinkRepositoryPort):
    """Delta link repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_delta_link(self, delta_link: DeltaLink) -> DeltaLink:
        """Save delta link."""
        # Deactivate existing delta links for the same account/folder
        deactivate_stmt = (
            update(DeltaLinkModel)
            .where(
                and_(
                    DeltaLinkModel.account_id == delta_link.account_id,
                    DeltaLinkModel.folder_id == delta_link.folder_id,
                    DeltaLinkModel.is_active == True
                )
            )
            .values(is_active=False)
        )
        await self.session.execute(deactivate_stmt)
        
        # Create new delta link
        model = DeltaLinkModel(
            account_id=delta_link.account_id,
            folder_id=delta_link.folder_id,
            delta_token=delta_link.delta_token,
            created_at=delta_link.created_at,
            last_used_at=delta_link.last_used_at,
            is_active=delta_link.is_active
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._model_to_entity(model)
    
    async def get_delta_link(self, account_id: str, folder_id: str) -> Optional[DeltaLink]:
        """Get active delta link."""
        stmt = select(DeltaLinkModel).where(
            and_(
                DeltaLinkModel.account_id == account_id,
                DeltaLinkModel.folder_id == folder_id,
                DeltaLinkModel.is_active == True
            )
        ).order_by(DeltaLinkModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    def _model_to_entity(self, model: DeltaLinkModel) -> DeltaLink:
        """Convert model to entity."""
        return DeltaLink(
            account_id=model.account_id,
            folder_id=model.folder_id,
            delta_token=model.delta_token,
            created_at=model.created_at,
            last_used_at=model.last_used_at,
            is_active=model.is_active
        )


class WebhookRepository(WebhookRepositoryPort):
    """Webhook repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_webhook_subscription(self, subscription: WebhookSubscription) -> WebhookSubscription:
        """Save webhook subscription."""
        model = WebhookSubscriptionModel(
            subscription_id=subscription.subscription_id,
            account_id=subscription.account_id,
            resource=subscription.resource,
            change_types=subscription.change_types,
            notification_url=subscription.notification_url,
            client_state=subscription.client_state,
            expires_datetime=subscription.expires_datetime,
            created_at=subscription.created_at,
            is_active=subscription.is_active
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._model_to_entity(model)
    
    async def get_webhook_subscription(self, subscription_id: str) -> Optional[WebhookSubscription]:
        """Get webhook subscription."""
        stmt = select(WebhookSubscriptionModel).where(
            WebhookSubscriptionModel.subscription_id == subscription_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        return self._model_to_entity(model) if model else None
    
    def _model_to_entity(self, model: WebhookSubscriptionModel) -> WebhookSubscription:
        """Convert model to entity."""
        return WebhookSubscription(
            subscription_id=model.subscription_id,
            account_id=model.account_id,
            resource=model.resource,
            change_types=model.change_types,
            notification_url=model.notification_url,
            client_state=model.client_state,
            expires_datetime=model.expires_datetime,
            created_at=model.created_at,
            is_active=model.is_active
        )


class ExternalAPIRepository(ExternalAPIRepositoryPort):
    """External API repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_api_call(self, api_call: ExternalAPICall) -> ExternalAPICall:
        """Save API call record."""
        model = ExternalAPICallModel(
            message_id=api_call.message_id,
            endpoint_url=api_call.endpoint_url,
            http_method=api_call.http_method,
            request_payload=api_call.request_payload,
            response_status=api_call.response_status,
            response_body=api_call.response_body,
            success=api_call.success,
            retry_count=api_call.retry_count,
            created_at=api_call.created_at,
            completed_at=api_call.completed_at
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._model_to_entity(model)
    
    async def get_failed_api_calls(self, limit: Optional[int] = None) -> List[ExternalAPICall]:
        """Get failed API calls for retry."""
        stmt = select(ExternalAPICallModel).where(
            and_(
                ExternalAPICallModel.success == False,
                ExternalAPICallModel.retry_count < 3
            )
        ).order_by(ExternalAPICallModel.created_at.asc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: ExternalAPICallModel) -> ExternalAPICall:
        """Convert model to entity."""
        return ExternalAPICall(
            message_id=model.message_id,
            endpoint_url=model.endpoint_url,
            http_method=model.http_method,
            request_payload=model.request_payload,
            response_status=model.response_status,
            response_body=model.response_body,
            success=model.success,
            retry_count=model.retry_count,
            created_at=model.created_at,
            completed_at=model.completed_at
        )


class AuthenticationLogRepository(AuthenticationLogRepositoryPort):
    """Authentication log repository implementation."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_auth_log(self, log: AuthenticationLog) -> AuthenticationLog:
        """Save authentication log."""
        model = AuthenticationLogModel(
            account_id=log.account_id,
            event_type=log.event_type,
            authentication_flow=log.authentication_flow,
            success=log.success,
            error_code=log.error_code,
            error_message=log.error_message,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            timestamp=log.timestamp
        )
        
        self.session.add(model)
        await self.session.flush()
        
        return self._model_to_entity(model)
    
    async def get_auth_logs(
        self,
        account_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: Optional[int] = None
    ) -> List[AuthenticationLog]:
        """Get authentication logs with filters."""
        stmt = select(AuthenticationLogModel)
        
        conditions = []
        if account_id:
            conditions.append(AuthenticationLogModel.account_id == account_id)
        if date_from:
            conditions.append(AuthenticationLogModel.timestamp >= date_from)
        if date_to:
            conditions.append(AuthenticationLogModel.timestamp <= date_to)
        if success is not None:
            conditions.append(AuthenticationLogModel.success == success)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(AuthenticationLogModel.timestamp.desc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]
    
    def _model_to_entity(self, model: AuthenticationLogModel) -> AuthenticationLog:
        """Convert model to entity."""
        return AuthenticationLog(
            account_id=model.account_id,
            event_type=model.event_type,
            authentication_flow=model.authentication_flow,
            success=model.success,
            error_code=model.error_code,
            error_message=model.error_message,
            ip_address=model.ip_address,
            user_agent=model.user_agent,
            timestamp=model.timestamp
        )


class DatabaseRepositoryAdapter:
    """Database repository adapter that implements all repository ports."""
    
    def __init__(self, db_adapter: DatabaseAdapter):
        self.db_adapter = db_adapter
    
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
