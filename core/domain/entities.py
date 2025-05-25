"""Domain entities for the Microsoft Graph API Mail Collection System."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr


class AuthenticationFlow(str, Enum):
    """Authentication flow types."""
    AUTHORIZATION_CODE = "authorization_code"
    DEVICE_CODE = "device_code"


class TokenStatus(str, Enum):
    """Token status types."""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"


class MailDirection(str, Enum):
    """Mail direction types."""
    SENT = "sent"
    RECEIVED = "received"
    BOTH = "both"


class MailImportance(str, Enum):
    """Mail importance levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class AccountStatus(str, Enum):
    """Account status types."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Account(BaseModel):
    """User account entity."""
    
    id: Optional[str] = None
    email: EmailStr
    user_id: str
    tenant_id: str
    client_id: str
    authentication_flow: AuthenticationFlow
    status: AccountStatus = AccountStatus.ACTIVE
    scopes: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_authenticated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class AuthorizationCodeAccount(BaseModel):
    """Authorization Code Flow specific account data."""
    
    account_id: str
    client_secret: str
    redirect_uri: str
    authority: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class DeviceCodeAccount(BaseModel):
    """Device Code Flow specific account data."""
    
    account_id: str
    device_code: Optional[str] = None
    user_code: Optional[str] = None
    verification_uri: Optional[str] = None
    expires_in: Optional[int] = None
    interval: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class Token(BaseModel):
    """OAuth token entity."""
    
    id: Optional[str] = None
    account_id: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: datetime
    scopes: List[str] = Field(default_factory=list)
    status: TokenStatus = TokenStatus.VALID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() >= self.expires_at
    
    @property
    def expires_in_seconds(self) -> int:
        """Get seconds until token expires."""
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


class MailMessage(BaseModel):
    """Email message entity."""
    
    id: Optional[str] = None
    message_id: str  # Graph API message ID
    internet_message_id: Optional[str] = None
    account_id: str
    subject: str
    sender_email: EmailStr
    sender_name: Optional[str] = None
    recipients: List[EmailStr] = Field(default_factory=list)
    cc_recipients: List[EmailStr] = Field(default_factory=list)
    bcc_recipients: List[EmailStr] = Field(default_factory=list)
    body_preview: Optional[str] = None
    body_content: Optional[str] = None
    body_content_type: str = "html"  # html or text
    importance: MailImportance = MailImportance.NORMAL
    is_read: bool = False
    has_attachments: bool = False
    received_datetime: datetime
    sent_datetime: Optional[datetime] = None
    direction: MailDirection
    folder_name: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class MailAttachment(BaseModel):
    """Email attachment entity."""
    
    id: Optional[str] = None
    message_id: str
    attachment_id: str  # Graph API attachment ID
    name: str
    content_type: str
    size: int
    is_inline: bool = False
    content_id: Optional[str] = None
    content_location: Optional[str] = None
    storage_url: Optional[str] = None  # For large attachments stored externally
    created_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class MailQueryHistory(BaseModel):
    """Mail query history entity."""
    
    id: Optional[str] = None
    account_id: str
    query_type: str  # "manual", "delta", "webhook"
    query_parameters: Dict[str, Any] = Field(default_factory=dict)
    messages_found: int = 0
    new_messages: int = 0
    query_datetime: datetime
    execution_time_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True


class DeltaLink(BaseModel):
    """Delta link for incremental synchronization."""
    
    id: Optional[str] = None
    account_id: str
    folder_id: str = "Inbox"
    delta_token: str
    next_link: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        use_enum_values = True


class WebhookSubscription(BaseModel):
    """Webhook subscription entity."""
    
    id: Optional[str] = None
    subscription_id: str  # Graph API subscription ID
    account_id: str
    resource: str
    change_types: List[str] = Field(default_factory=list)
    notification_url: str
    client_state: str
    expires_datetime: datetime
    created_at: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        use_enum_values = True


class AuthenticationLog(BaseModel):
    """Authentication event log entity."""
    
    id: Optional[str] = None
    account_id: str
    event_type: str  # "login", "token_refresh", "logout", "error"
    authentication_flow: AuthenticationFlow
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime
    
    class Config:
        use_enum_values = True


class ExternalAPICall(BaseModel):
    """External API call tracking entity."""
    
    id: Optional[str] = None
    message_id: str
    endpoint_url: str
    http_method: str = "POST"
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    success: bool = False
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[datetime] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class NotificationRule(BaseModel):
    """User notification rule entity."""
    
    id: Optional[str] = None
    account_id: str
    name: str
    keywords: List[str] = Field(default_factory=list)
    sender_filters: List[str] = Field(default_factory=list)
    importance_filter: Optional[MailImportance] = None
    notification_channels: List[str] = Field(default_factory=list)  # slack, discord, sms
    webhook_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
