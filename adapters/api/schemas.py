"""API request/response schemas."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum

from core.domain.entities import (
    AuthenticationFlow, AccountStatus, TokenStatus,
    MailDirection, MailImportance
)


# Base schemas
class BaseResponse(BaseModel):
    """Base response schema."""
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    success: bool = False
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None


# Account schemas
class CreateAccountRequest(BaseModel):
    """Create account request schema."""
    email: EmailStr
    tenant_id: str
    client_id: str
    authentication_flow: AuthenticationFlow
    scopes: List[str] = Field(default_factory=lambda: [
        "offline_access", "User.Read", "Mail.Read", "Mail.ReadWrite", "Mail.Send"
    ])
    
    # Authorization Code Flow specific
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    authority: Optional[str] = None


class AccountResponse(BaseModel):
    """Account response schema."""
    id: str
    email: str
    user_id: Optional[str]
    tenant_id: str
    client_id: str
    authentication_flow: AuthenticationFlow
    status: AccountStatus
    scopes: List[str]
    created_at: datetime
    updated_at: Optional[datetime]
    last_authenticated_at: Optional[datetime]


class UpdateAccountRequest(BaseModel):
    """Update account request schema."""
    email: Optional[EmailStr] = None
    scopes: Optional[List[str]] = None
    status: Optional[AccountStatus] = None


class AccountListResponse(BaseResponse):
    """Account list response schema."""
    accounts: List[AccountResponse]
    total: int


# Authentication schemas
class AuthenticationRequest(BaseModel):
    """Authentication request schema."""
    account_id: Optional[str] = None
    email: Optional[EmailStr] = None


class AuthorizationUrlResponse(BaseResponse):
    """Authorization URL response schema."""
    authorization_url: str
    state: str
    expires_at: datetime
    instructions: str = "Please visit the authorization URL to complete authentication"


class AuthorizationCallbackRequest(BaseModel):
    """Authorization callback request schema."""
    code: str
    state: str
    account_id: str


class DeviceCodeResponse(BaseResponse):
    """Device code response schema."""
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int
    instructions: str


class TokenResponse(BaseModel):
    """Token response schema."""
    account_id: str
    token_type: str
    expires_at: datetime
    scopes: List[str]
    status: TokenStatus
    created_at: datetime
    updated_at: Optional[datetime]


class TokenStatusResponse(BaseResponse):
    """Token status response schema."""
    tokens: List[TokenResponse]


# Mail schemas
class MailQueryRequest(BaseModel):
    """Mail query request schema."""
    account_id: Optional[str] = None
    folder_id: str = "inbox"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sender_email: Optional[str] = None
    is_read: Optional[bool] = None
    importance: Optional[MailImportance] = None
    search: Optional[str] = None
    top: Optional[int] = Field(default=10, ge=1, le=1000)
    skip: Optional[int] = Field(default=0, ge=0)


class RecipientInfo(BaseModel):
    """Recipient information schema."""
    email: str
    name: Optional[str] = None


class MailMessageResponse(BaseModel):
    """Mail message response schema."""
    message_id: str
    internet_message_id: Optional[str]
    account_id: str
    subject: Optional[str]
    sender_email: Optional[str]
    sender_name: Optional[str]
    recipients: List[RecipientInfo]
    cc_recipients: Optional[List[RecipientInfo]]
    bcc_recipients: Optional[List[RecipientInfo]]
    body_preview: Optional[str]
    body_content: Optional[str]
    body_content_type: str
    importance: MailImportance
    is_read: bool
    has_attachments: bool
    received_datetime: datetime
    sent_datetime: Optional[datetime]
    direction: MailDirection
    categories: Optional[List[str]]
    created_at: datetime


class MailQueryResponse(BaseResponse):
    """Mail query response schema."""
    messages: List[MailMessageResponse]
    total_found: int
    new_messages: int
    has_more: bool
    next_skip: Optional[int]


class SendMailRequest(BaseModel):
    """Send mail request schema."""
    account_id: Optional[str] = None
    to_recipients: List[EmailStr]
    subject: str
    body: str
    body_type: str = Field(default="text", regex="^(text|html)$")
    cc_recipients: Optional[List[EmailStr]] = None
    bcc_recipients: Optional[List[EmailStr]] = None
    save_to_sent_items: bool = True


class SendMailResponse(BaseResponse):
    """Send mail response schema."""
    message_id: Optional[str]
    sent_at: datetime


# Delta sync schemas
class DeltaSyncRequest(BaseModel):
    """Delta sync request schema."""
    account_id: Optional[str] = None
    folder_id: str = "inbox"


class DeltaSyncResponse(BaseResponse):
    """Delta sync response schema."""
    messages: List[MailMessageResponse]
    new_messages: int
    updated_messages: int
    deleted_messages: int
    delta_token: Optional[str]
    next_sync_available: bool


# Webhook schemas
class CreateWebhookRequest(BaseModel):
    """Create webhook request schema."""
    account_id: str
    resource: str = "me/mailFolders('Inbox')/messages"
    change_types: List[str] = Field(default_factory=lambda: ["created", "updated"])
    notification_url: str
    expiration_hours: int = Field(default=6, ge=1, le=4230)  # Max 4230 minutes for Graph API


class WebhookResponse(BaseModel):
    """Webhook response schema."""
    subscription_id: str
    account_id: str
    resource: str
    change_types: List[str]
    notification_url: str
    expires_datetime: datetime
    is_active: bool
    created_at: datetime


class WebhookNotification(BaseModel):
    """Webhook notification schema."""
    subscription_id: str
    change_type: str
    client_state: str
    resource: str
    resource_data: Dict[str, Any]


class WebhookValidationRequest(BaseModel):
    """Webhook validation request schema."""
    validation_token: str


# Query history schemas
class MailQueryHistoryResponse(BaseModel):
    """Mail query history response schema."""
    account_id: str
    query_type: str
    query_parameters: Dict[str, Any]
    messages_found: int
    new_messages: int
    query_datetime: datetime
    execution_time_ms: int
    success: bool
    error_message: Optional[str]


class QueryHistoryListResponse(BaseResponse):
    """Query history list response schema."""
    histories: List[MailQueryHistoryResponse]
    total: int


# Authentication log schemas
class AuthenticationLogResponse(BaseModel):
    """Authentication log response schema."""
    account_id: str
    event_type: str
    authentication_flow: AuthenticationFlow
    success: bool
    error_code: Optional[str]
    error_message: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime


class AuthLogQueryRequest(BaseModel):
    """Authentication log query request schema."""
    account_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    success: Optional[bool] = None
    limit: Optional[int] = Field(default=100, ge=1, le=1000)


class AuthLogListResponse(BaseResponse):
    """Authentication log list response schema."""
    logs: List[AuthenticationLogResponse]
    total: int


# External API schemas
class ExternalAPICallResponse(BaseModel):
    """External API call response schema."""
    message_id: str
    endpoint_url: str
    http_method: str
    request_payload: Optional[Dict[str, Any]]
    response_status: Optional[int]
    response_body: Optional[str]
    success: bool
    retry_count: int
    created_at: datetime
    completed_at: Optional[datetime]


class ExternalAPIListResponse(BaseResponse):
    """External API list response schema."""
    api_calls: List[ExternalAPICallResponse]
    total: int


# Health check schemas
class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    status: str = "healthy"
    timestamp: datetime
    version: str
    database: str = "connected"
    services: Dict[str, str] = Field(default_factory=dict)
