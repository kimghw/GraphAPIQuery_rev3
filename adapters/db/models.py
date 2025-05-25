"""SQLAlchemy models for Microsoft Graph API Mail Collection System."""

import json
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Text, JSON, 
    ForeignKey, Enum as SQLEnum, Index
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, VARCHAR

from core.domain.entities import (
    AuthenticationFlow, AccountStatus, TokenStatus, MailDirection, MailImportance
)

class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """Platform-independent GUID type."""
    impl = VARCHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(VARCHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return str(value)


class JSONType(TypeDecorator):
    """JSON type that works with both SQLite and PostgreSQL."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return value


class AccountModel(Base):
    """Account table model."""
    __tablename__ = "accounts"

    id = Column(GUID, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)
    client_id = Column(String(255), nullable=False)
    authentication_flow = Column(SQLEnum(AuthenticationFlow), nullable=False)
    status = Column(SQLEnum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)
    scopes = Column(JSONType, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))
    last_authenticated_at = Column(DateTime, nullable=True)

    # Relationships
    tokens = relationship("TokenModel", back_populates="account", cascade="all, delete-orphan")
    auth_code_account = relationship("AuthorizationCodeAccountModel", back_populates="account", uselist=False, cascade="all, delete-orphan")
    device_code_account = relationship("DeviceCodeAccountModel", back_populates="account", uselist=False, cascade="all, delete-orphan")
    mail_messages = relationship("MailMessageModel", back_populates="account", cascade="all, delete-orphan")
    query_histories = relationship("MailQueryHistoryModel", back_populates="account", cascade="all, delete-orphan")
    delta_links = relationship("DeltaLinkModel", back_populates="account", cascade="all, delete-orphan")
    webhook_subscriptions = relationship("WebhookSubscriptionModel", back_populates="account", cascade="all, delete-orphan")
    auth_logs = relationship("AuthenticationLogModel", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_accounts_email', 'email'),
        Index('idx_accounts_user_id', 'user_id'),
        Index('idx_accounts_status', 'status'),
    )


class AuthorizationCodeAccountModel(Base):
    """Authorization Code Account table model."""
    __tablename__ = "authorization_code_accounts"

    account_id = Column(GUID, ForeignKey("accounts.id"), primary_key=True)
    client_secret = Column(String(255), nullable=False)
    redirect_uri = Column(String(500), nullable=False)
    authority = Column(String(500), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    # Relationships
    account = relationship("AccountModel", back_populates="auth_code_account")


class DeviceCodeAccountModel(Base):
    """Device Code Account table model."""
    __tablename__ = "device_code_accounts"

    account_id = Column(GUID, ForeignKey("accounts.id"), primary_key=True)
    device_code = Column(String(500), nullable=True)
    user_code = Column(String(50), nullable=True)
    verification_uri = Column(String(500), nullable=True)
    expires_in = Column(Integer, nullable=True)
    interval = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))

    # Relationships
    account = relationship("AccountModel", back_populates="device_code_account")


class TokenModel(Base):
    """Token table model."""
    __tablename__ = "tokens"

    account_id = Column(GUID, ForeignKey("accounts.id"), primary_key=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(50), nullable=False, default="Bearer")
    expires_at = Column(DateTime, nullable=False)
    scopes = Column(JSONType, nullable=False)
    status = Column(SQLEnum(TokenStatus), nullable=False, default=TokenStatus.VALID)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, nullable=True, onupdate=lambda: datetime.now(UTC))

    # Relationships
    account = relationship("AccountModel", back_populates="tokens")

    __table_args__ = (
        Index('idx_tokens_account_id', 'account_id'),
        Index('idx_tokens_expires_at', 'expires_at'),
        Index('idx_tokens_status', 'status'),
    )


class MailMessageModel(Base):
    """Mail Message table model."""
    __tablename__ = "mail_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(255), nullable=False, index=True)
    internet_message_id = Column(String(255), nullable=True)
    account_id = Column(GUID, ForeignKey("accounts.id"), nullable=False)
    subject = Column(Text, nullable=True)
    sender_email = Column(String(255), nullable=True, index=True)
    sender_name = Column(String(255), nullable=True)
    recipients = Column(JSONType, nullable=False)
    cc_recipients = Column(JSONType, nullable=True)
    bcc_recipients = Column(JSONType, nullable=True)
    body_preview = Column(Text, nullable=True)
    body_content = Column(Text, nullable=True)
    body_content_type = Column(String(20), nullable=False, default="html")
    importance = Column(SQLEnum(MailImportance), nullable=False, default=MailImportance.NORMAL)
    is_read = Column(Boolean, nullable=False, default=False)
    has_attachments = Column(Boolean, nullable=False, default=False)
    received_datetime = Column(DateTime, nullable=False)
    sent_datetime = Column(DateTime, nullable=True)
    direction = Column(SQLEnum(MailDirection), nullable=False)
    categories = Column(JSONType, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    # Relationships
    account = relationship("AccountModel", back_populates="mail_messages")
    external_api_calls = relationship("ExternalAPICallModel", back_populates="mail_message", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_mail_messages_message_id', 'message_id'),
        Index('idx_mail_messages_account_id', 'account_id'),
        Index('idx_mail_messages_sender_email', 'sender_email'),
        Index('idx_mail_messages_received_datetime', 'received_datetime'),
        Index('idx_mail_messages_direction', 'direction'),
        Index('idx_mail_messages_is_read', 'is_read'),
        Index('idx_mail_messages_importance', 'importance'),
        Index('idx_mail_messages_account_message', 'account_id', 'message_id'),
    )


class MailQueryHistoryModel(Base):
    """Mail Query History table model."""
    __tablename__ = "mail_query_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(GUID, ForeignKey("accounts.id"), nullable=False)
    query_type = Column(String(50), nullable=False)
    query_parameters = Column(JSONType, nullable=False)
    messages_found = Column(Integer, nullable=False, default=0)
    new_messages = Column(Integer, nullable=False, default=0)
    query_datetime = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    execution_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    account = relationship("AccountModel", back_populates="query_histories")

    __table_args__ = (
        Index('idx_query_histories_account_id', 'account_id'),
        Index('idx_query_histories_query_datetime', 'query_datetime'),
        Index('idx_query_histories_query_type', 'query_type'),
        Index('idx_query_histories_success', 'success'),
    )


class DeltaLinkModel(Base):
    """Delta Link table model."""
    __tablename__ = "delta_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(GUID, ForeignKey("accounts.id"), nullable=False)
    folder_id = Column(String(255), nullable=False)
    delta_token = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    last_used_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    account = relationship("AccountModel", back_populates="delta_links")

    __table_args__ = (
        Index('idx_delta_links_account_folder', 'account_id', 'folder_id'),
        Index('idx_delta_links_is_active', 'is_active'),
        Index('idx_delta_links_last_used_at', 'last_used_at'),
    )


class WebhookSubscriptionModel(Base):
    """Webhook Subscription table model."""
    __tablename__ = "webhook_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(String(255), nullable=False, unique=True, index=True)
    account_id = Column(GUID, ForeignKey("accounts.id"), nullable=False)
    resource = Column(String(500), nullable=False)
    change_types = Column(JSONType, nullable=False)
    notification_url = Column(String(500), nullable=False)
    client_state = Column(String(255), nullable=False)
    expires_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    account = relationship("AccountModel", back_populates="webhook_subscriptions")

    __table_args__ = (
        Index('idx_webhook_subscriptions_account_id', 'account_id'),
        Index('idx_webhook_subscriptions_expires_datetime', 'expires_datetime'),
        Index('idx_webhook_subscriptions_is_active', 'is_active'),
    )


class ExternalAPICallModel(Base):
    """External API Call table model."""
    __tablename__ = "external_api_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(255), ForeignKey("mail_messages.message_id"), nullable=False)
    endpoint_url = Column(String(500), nullable=False)
    http_method = Column(String(10), nullable=False, default="POST")
    request_payload = Column(JSONType, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    mail_message = relationship("MailMessageModel", back_populates="external_api_calls")

    __table_args__ = (
        Index('idx_external_api_calls_message_id', 'message_id'),
        Index('idx_external_api_calls_success', 'success'),
        Index('idx_external_api_calls_created_at', 'created_at'),
        Index('idx_external_api_calls_retry_count', 'retry_count'),
    )


class AuthenticationLogModel(Base):
    """Authentication Log table model."""
    __tablename__ = "authentication_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(GUID, ForeignKey("accounts.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    authentication_flow = Column(SQLEnum(AuthenticationFlow), nullable=False)
    success = Column(Boolean, nullable=False)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    # Relationships
    account = relationship("AccountModel", back_populates="auth_logs")

    __table_args__ = (
        Index('idx_auth_logs_account_id', 'account_id'),
        Index('idx_auth_logs_timestamp', 'timestamp'),
        Index('idx_auth_logs_event_type', 'event_type'),
        Index('idx_auth_logs_success', 'success'),
        Index('idx_auth_logs_authentication_flow', 'authentication_flow'),
    )
