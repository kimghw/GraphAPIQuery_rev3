"""Microsoft Graph API client adapter."""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.domain.entities import (
    Account, Token, MailMessage, MailDirection, MailImportance,
    DeltaLink, WebhookSubscription
)
from core.usecases.ports import GraphAPIClientPort
from config.settings import Settings

logger = structlog.get_logger()


class GraphAPIClientAdapter(GraphAPIClientPort):
    """Microsoft Graph API client implementation."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.timeout = httpx.Timeout(30.0)
        
    async def _get_headers(self, token: Token) -> Dict[str, str]:
        """Get headers for Graph API requests."""
        return {
            "Authorization": f"{token.token_type} {token.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"GraphAPIQuery/{self.settings.VERSION}",
            "Prefer": "outlook.body-content-type=\"text\""
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException))
    )
    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(
                    "Rate limited by Graph API",
                    retry_after=retry_after,
                    url=url
                )
                await asyncio.sleep(retry_after)
                raise httpx.HTTPStatusError(
                    "Rate limited",
                    request=response.request,
                    response=response
                )
            
            response.raise_for_status()
            return response
    
    async def get_user_info(self, token: Token) -> Dict[str, Any]:
        """Get user information from Graph API."""
        headers = await self._get_headers(token)
        url = f"{self.base_url}/me"
        
        try:
            response = await self._make_request("GET", url, headers)
            user_data = response.json()
            
            logger.info(
                "Retrieved user info from Graph API",
                user_id=user_data.get("id"),
                email=user_data.get("mail") or user_data.get("userPrincipalName")
            )
            
            return user_data
            
        except Exception as e:
            logger.error(
                "Failed to get user info from Graph API",
                error=str(e),
                url=url
            )
            raise
    
    async def get_messages(
        self,
        token: Token,
        user_id: Optional[str] = None,
        folder_id: str = "inbox",
        filters: Optional[Dict[str, Any]] = None,
        select_fields: Optional[List[str]] = None,
        top: Optional[int] = None,
        skip: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Get messages from Graph API."""
        headers = await self._get_headers(token)
        
        # Build URL
        if user_id:
            url = f"{self.base_url}/users/{user_id}/mailFolders/{folder_id}/messages"
        else:
            url = f"{self.base_url}/me/mailFolders/{folder_id}/messages"
        
        # Build query parameters
        params = {}
        
        if select_fields:
            params["$select"] = ",".join(select_fields)
        else:
            params["$select"] = (
                "id,internetMessageId,subject,from,toRecipients,ccRecipients,"
                "bccRecipients,bodyPreview,body,importance,isRead,hasAttachments,"
                "receivedDateTime,sentDateTime,categories"
            )
        
        if filters:
            filter_parts = []
            
            # Date filters
            if "date_from" in filters:
                filter_parts.append(f"receivedDateTime ge {filters['date_from']}")
            if "date_to" in filters:
                filter_parts.append(f"receivedDateTime lt {filters['date_to']}")
            
            # Sender filter
            if "sender_email" in filters:
                filter_parts.append(f"from/emailAddress/address eq '{filters['sender_email']}'")
            
            # Read status filter
            if "is_read" in filters:
                filter_parts.append(f"isRead eq {str(filters['is_read']).lower()}")
            
            # Importance filter
            if "importance" in filters:
                filter_parts.append(f"importance eq '{filters['importance']}'")
            
            if filter_parts:
                params["$filter"] = " and ".join(filter_parts)
        
        # Search query
        if filters and "search" in filters:
            params["$search"] = f'"{filters["search"]}"'
        
        # Ordering
        params["$orderby"] = "receivedDateTime desc"
        
        # Pagination
        if top:
            params["$top"] = top
        if skip:
            params["$skip"] = skip
        
        try:
            response = await self._make_request("GET", url, headers, params)
            data = response.json()
            
            messages = data.get("value", [])
            next_link = data.get("@odata.nextLink")
            
            logger.info(
                "Retrieved messages from Graph API",
                count=len(messages),
                has_next=bool(next_link),
                folder_id=folder_id
            )
            
            return messages, next_link
            
        except Exception as e:
            logger.error(
                "Failed to get messages from Graph API",
                error=str(e),
                url=url,
                params=params
            )
            raise
    
    async def send_message(
        self,
        token: Token,
        to_recipients: List[str],
        subject: str,
        body: str,
        body_type: str = "text",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        save_to_sent_items: bool = True
    ) -> Dict[str, Any]:
        """Send message via Graph API."""
        headers = await self._get_headers(token)
        url = f"{self.base_url}/me/sendMail"
        
        # Build message payload
        message = {
            "subject": subject,
            "body": {
                "contentType": body_type,
                "content": body
            },
            "toRecipients": [
                {"emailAddress": {"address": email}} for email in to_recipients
            ]
        }
        
        if cc_recipients:
            message["ccRecipients"] = [
                {"emailAddress": {"address": email}} for email in cc_recipients
            ]
        
        if bcc_recipients:
            message["bccRecipients"] = [
                {"emailAddress": {"address": email}} for email in bcc_recipients
            ]
        
        payload = {
            "message": message,
            "saveToSentItems": save_to_sent_items
        }
        
        try:
            response = await self._make_request("POST", url, headers, json_data=payload)
            
            logger.info(
                "Sent message via Graph API",
                to_recipients=to_recipients,
                subject=subject
            )
            
            return {"success": True, "message_id": None}  # Graph API doesn't return message ID for sendMail
            
        except Exception as e:
            logger.error(
                "Failed to send message via Graph API",
                error=str(e),
                to_recipients=to_recipients,
                subject=subject
            )
            raise
    
    async def get_delta_messages(
        self,
        token: Token,
        user_id: Optional[str] = None,
        folder_id: str = "inbox",
        delta_token: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
        """Get delta messages from Graph API."""
        headers = await self._get_headers(token)
        
        # Build URL
        if user_id:
            base_url = f"{self.base_url}/users/{user_id}/mailFolders/{folder_id}/messages"
        else:
            base_url = f"{self.base_url}/me/mailFolders/{folder_id}/messages"
        
        if delta_token:
            url = f"{base_url}/delta"
            params = {"$deltatoken": delta_token}
        else:
            url = f"{base_url}/delta"
            params = {
                "$select": (
                    "id,internetMessageId,subject,from,toRecipients,ccRecipients,"
                    "bccRecipients,bodyPreview,body,importance,isRead,hasAttachments,"
                    "receivedDateTime,sentDateTime,categories"
                )
            }
        
        try:
            response = await self._make_request("GET", url, headers, params)
            data = response.json()
            
            messages = data.get("value", [])
            next_link = data.get("@odata.nextLink")
            delta_link = data.get("@odata.deltaLink")
            
            # Extract delta token from delta link
            new_delta_token = None
            if delta_link:
                parsed_url = urlparse(delta_link)
                query_params = parse_qs(parsed_url.query)
                new_delta_token = query_params.get("$deltatoken", [None])[0]
            
            logger.info(
                "Retrieved delta messages from Graph API",
                count=len(messages),
                has_next=bool(next_link),
                has_delta=bool(delta_link),
                folder_id=folder_id
            )
            
            return messages, next_link, new_delta_token
            
        except Exception as e:
            logger.error(
                "Failed to get delta messages from Graph API",
                error=str(e),
                url=url
            )
            raise
    
    async def create_webhook_subscription(
        self,
        token: Token,
        resource: str,
        notification_url: str,
        change_types: List[str],
        expiration_datetime: datetime,
        client_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create webhook subscription via Graph API."""
        headers = await self._get_headers(token)
        url = f"{self.base_url}/subscriptions"
        
        if not client_state:
            client_state = str(uuid.uuid4())
        
        payload = {
            "changeType": ",".join(change_types),
            "notificationUrl": notification_url,
            "resource": resource,
            "expirationDateTime": expiration_datetime.isoformat() + "Z",
            "clientState": client_state
        }
        
        try:
            response = await self._make_request("POST", url, headers, json_data=payload)
            subscription_data = response.json()
            
            logger.info(
                "Created webhook subscription",
                subscription_id=subscription_data.get("id"),
                resource=resource,
                notification_url=notification_url
            )
            
            return subscription_data
            
        except Exception as e:
            logger.error(
                "Failed to create webhook subscription",
                error=str(e),
                resource=resource,
                notification_url=notification_url
            )
            raise
    
    async def renew_webhook_subscription(
        self,
        token: Token,
        subscription_id: str,
        expiration_datetime: datetime
    ) -> Dict[str, Any]:
        """Renew webhook subscription via Graph API."""
        headers = await self._get_headers(token)
        url = f"{self.base_url}/subscriptions/{subscription_id}"
        
        payload = {
            "expirationDateTime": expiration_datetime.isoformat() + "Z"
        }
        
        try:
            response = await self._make_request("PATCH", url, headers, json_data=payload)
            subscription_data = response.json()
            
            logger.info(
                "Renewed webhook subscription",
                subscription_id=subscription_id,
                new_expiration=expiration_datetime
            )
            
            return subscription_data
            
        except Exception as e:
            logger.error(
                "Failed to renew webhook subscription",
                error=str(e),
                subscription_id=subscription_id
            )
            raise
    
    async def delete_webhook_subscription(
        self,
        token: Token,
        subscription_id: str
    ) -> bool:
        """Delete webhook subscription via Graph API."""
        headers = await self._get_headers(token)
        url = f"{self.base_url}/subscriptions/{subscription_id}"
        
        try:
            await self._make_request("DELETE", url, headers)
            
            logger.info(
                "Deleted webhook subscription",
                subscription_id=subscription_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete webhook subscription",
                error=str(e),
                subscription_id=subscription_id
            )
            return False
    
    async def revoke_user_sessions(
        self,
        token: Token,
        user_id: Optional[str] = None
    ) -> bool:
        """Revoke user sessions via Graph API."""
        headers = await self._get_headers(token)
        
        if user_id:
            url = f"{self.base_url}/users/{user_id}/revokeSignInSessions"
        else:
            url = f"{self.base_url}/me/revokeSignInSessions"
        
        try:
            response = await self._make_request("POST", url, headers)
            result = response.json()
            
            logger.info(
                "Revoked user sessions",
                user_id=user_id,
                success=result.get("value", False)
            )
            
            return result.get("value", False)
            
        except Exception as e:
            logger.error(
                "Failed to revoke user sessions",
                error=str(e),
                user_id=user_id
            )
            return False
    
    def _parse_graph_message(self, message_data: Dict[str, Any], account_id: str) -> MailMessage:
        """Parse Graph API message data to MailMessage entity."""
        # Extract sender information
        sender_info = message_data.get("from", {}).get("emailAddress", {})
        sender_email = sender_info.get("address")
        sender_name = sender_info.get("name")
        
        # Extract recipients
        recipients = []
        for recipient in message_data.get("toRecipients", []):
            email_addr = recipient.get("emailAddress", {})
            recipients.append({
                "email": email_addr.get("address"),
                "name": email_addr.get("name")
            })
        
        # Extract CC recipients
        cc_recipients = []
        for recipient in message_data.get("ccRecipients", []):
            email_addr = recipient.get("emailAddress", {})
            cc_recipients.append({
                "email": email_addr.get("address"),
                "name": email_addr.get("name")
            })
        
        # Extract BCC recipients
        bcc_recipients = []
        for recipient in message_data.get("bccRecipients", []):
            email_addr = recipient.get("emailAddress", {})
            bcc_recipients.append({
                "email": email_addr.get("address"),
                "name": email_addr.get("name")
            })
        
        # Parse body
        body_data = message_data.get("body", {})
        body_content = body_data.get("content", "")
        body_content_type = body_data.get("contentType", "html").lower()
        
        # Parse importance
        importance_str = message_data.get("importance", "normal").lower()
        importance = MailImportance.NORMAL
        if importance_str == "high":
            importance = MailImportance.HIGH
        elif importance_str == "low":
            importance = MailImportance.LOW
        
        # Parse datetime
        received_datetime = datetime.fromisoformat(
            message_data["receivedDateTime"].replace("Z", "+00:00")
        )
        
        sent_datetime = None
        if message_data.get("sentDateTime"):
            sent_datetime = datetime.fromisoformat(
                message_data["sentDateTime"].replace("Z", "+00:00")
            )
        
        return MailMessage(
            message_id=message_data["id"],
            internet_message_id=message_data.get("internetMessageId"),
            account_id=account_id,
            subject=message_data.get("subject"),
            sender_email=sender_email,
            sender_name=sender_name,
            recipients=recipients,
            cc_recipients=cc_recipients if cc_recipients else None,
            bcc_recipients=bcc_recipients if bcc_recipients else None,
            body_preview=message_data.get("bodyPreview"),
            body_content=body_content,
            body_content_type=body_content_type,
            importance=importance,
            is_read=message_data.get("isRead", False),
            has_attachments=message_data.get("hasAttachments", False),
            received_datetime=received_datetime,
            sent_datetime=sent_datetime,
            direction=MailDirection.RECEIVED,  # Default to received, can be determined by logic
            categories=message_data.get("categories"),
            created_at=datetime.utcnow()
        )
