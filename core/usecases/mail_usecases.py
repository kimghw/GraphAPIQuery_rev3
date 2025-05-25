"""Mail use cases for Microsoft Graph API Mail Collection System."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import structlog

from core.domain.entities import (
    MailMessage, MailQueryHistory, DeltaLink, WebhookSubscription,
    ExternalAPICall, MailDirection, MailImportance
)
from core.usecases.ports import (
    AccountRepositoryPort, TokenRepositoryPort, MailRepositoryPort,
    MailQueryHistoryRepositoryPort, DeltaLinkRepositoryPort,
    WebhookRepositoryPort, ExternalAPIRepositoryPort,
    MicrosoftGraphClientPort, ExternalAPIClientPort, ConfigPort
)

logger = structlog.get_logger()


class MailUseCases:
    """Mail related use cases."""
    
    def __init__(
        self,
        account_repo: AccountRepositoryPort,
        token_repo: TokenRepositoryPort,
        mail_repo: MailRepositoryPort,
        query_history_repo: MailQueryHistoryRepositoryPort,
        delta_link_repo: DeltaLinkRepositoryPort,
        webhook_repo: WebhookRepositoryPort,
        external_api_repo: ExternalAPIRepositoryPort,
        graph_client: MicrosoftGraphClientPort,
        external_api_client: ExternalAPIClientPort,
        config: ConfigPort
    ):
        self.account_repo = account_repo
        self.token_repo = token_repo
        self.mail_repo = mail_repo
        self.query_history_repo = query_history_repo
        self.delta_link_repo = delta_link_repo
        self.webhook_repo = webhook_repo
        self.external_api_repo = external_api_repo
        self.graph_client = graph_client
        self.external_api_client = external_api_client
        self.config = config
    
    async def query_mails(
        self,
        account_id: Optional[str] = None,
        folder: str = "Inbox",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sender_email: Optional[str] = None,
        subject_contains: Optional[str] = None,
        is_read: Optional[bool] = None,
        importance: Optional[MailImportance] = None,
        direction: Optional[MailDirection] = None,
        body_type: str = "html",
        top: Optional[int] = None,
        order_by: str = "receivedDateTime desc"
    ) -> Dict[str, Any]:
        """MAIL001 - Query mails with filters."""
        start_time = datetime.utcnow()
        
        try:
            accounts_to_query = []
            
            if account_id:
                account = await self.account_repo.get_account_by_id(account_id)
                if not account:
                    raise ValueError(f"Account {account_id} not found")
                accounts_to_query = [account]
            else:
                accounts_to_query = await self.account_repo.get_all_accounts()
            
            all_messages = []
            total_new_messages = 0
            
            for account in accounts_to_query:
                # Get valid token
                token = await self.token_repo.get_token_by_account_id(account.id)
                if not token or token.is_expired:
                    logger.warning(
                        "No valid token for account",
                        account_id=account.id,
                        email=account.email
                    )
                    continue
                
                # Build filter query
                filter_parts = []
                
                if date_from:
                    filter_parts.append(f"receivedDateTime ge {date_from.isoformat()}Z")
                if date_to:
                    filter_parts.append(f"receivedDateTime lt {date_to.isoformat()}Z")
                if sender_email:
                    filter_parts.append(f"from/emailAddress/address eq '{sender_email}'")
                if is_read is not None:
                    filter_parts.append(f"isRead eq {str(is_read).lower()}")
                if importance:
                    filter_parts.append(f"importance eq '{importance.value}'")
                
                filter_query = " and ".join(filter_parts) if filter_parts else None
                
                # Select fields
                select_fields = [
                    "id", "internetMessageId", "subject", "from", "toRecipients",
                    "ccRecipients", "bccRecipients", "bodyPreview", "body",
                    "importance", "isRead", "hasAttachments", "receivedDateTime",
                    "sentDateTime", "parentFolderId", "categories"
                ]
                
                # Query messages from Graph API
                response = await self.graph_client.get_messages(
                    access_token=token.access_token,
                    user_id=account.user_id,
                    folder=folder,
                    filter_query=filter_query,
                    select_fields=select_fields,
                    top=top,
                    order_by=order_by
                )
                
                # Process messages
                messages = response.get("value", [])
                new_messages_count = 0
                
                for msg_data in messages:
                    # Check if message already exists
                    existing = await self.mail_repo.mail_exists(
                        message_id=msg_data["id"],
                        account_id=account.id
                    )
                    
                    if not existing:
                        # Create mail message entity
                        mail_message = self._create_mail_message(msg_data, account.id, direction)
                        
                        # Save to database
                        saved_message = await self.mail_repo.save_mail_message(mail_message)
                        all_messages.append(saved_message)
                        new_messages_count += 1
                        
                        # Send to external API if configured
                        await self._send_to_external_api(saved_message)
                    else:
                        # Add existing message to results
                        existing_message = await self.mail_repo.get_mail_by_message_id(msg_data["id"])
                        if existing_message:
                            all_messages.append(existing_message)
                
                total_new_messages += new_messages_count
                
                # Log query history
                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                await self._log_query_history(
                    account_id=account.id,
                    query_type="manual",
                    query_parameters={
                        "folder": folder,
                        "filter_query": filter_query,
                        "top": top,
                        "order_by": order_by
                    },
                    messages_found=len(messages),
                    new_messages=new_messages_count,
                    execution_time_ms=execution_time
                )
            
            logger.info(
                "Mail query completed",
                accounts_queried=len(accounts_to_query),
                total_messages=len(all_messages),
                new_messages=total_new_messages
            )
            
            return {
                "success": True,
                "messages": [msg.dict() for msg in all_messages],
                "total_messages": len(all_messages),
                "new_messages": total_new_messages,
                "accounts_queried": len(accounts_to_query)
            }
            
        except Exception as e:
            logger.error(
                "Mail query failed",
                account_id=account_id,
                error=str(e)
            )
            raise
    
    async def send_mail(
        self,
        account_id: str,
        to_recipients: List[str],
        subject: str,
        body: str,
        body_type: str = "html",
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        importance: MailImportance = MailImportance.NORMAL
    ) -> Dict[str, Any]:
        """MAIL003 - Send email message."""
        try:
            account = await self.account_repo.get_account_by_id(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            token = await self.token_repo.get_token_by_account_id(account_id)
            if not token or token.is_expired:
                raise ValueError("No valid token available")
            
            # Prepare message data
            message_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": body_type,
                        "content": body
                    },
                    "toRecipients": [
                        {"emailAddress": {"address": email}} for email in to_recipients
                    ],
                    "importance": importance.value
                }
            }
            
            if cc_recipients:
                message_data["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in cc_recipients
                ]
            
            if bcc_recipients:
                message_data["message"]["bccRecipients"] = [
                    {"emailAddress": {"address": email}} for email in bcc_recipients
                ]
            
            # Send message
            response = await self.graph_client.send_message(
                access_token=token.access_token,
                user_id=account.user_id,
                message_data=message_data
            )
            
            logger.info(
                "Mail sent successfully",
                account_id=account_id,
                subject=subject,
                recipients=len(to_recipients)
            )
            
            return {
                "success": True,
                "message": "Email sent successfully",
                "message_id": response.get("id")
            }
            
        except Exception as e:
            logger.error(
                "Failed to send mail",
                account_id=account_id,
                subject=subject,
                error=str(e)
            )
            raise
    
    async def sync_delta_mails(
        self,
        account_id: Optional[str] = None,
        folder: str = "Inbox"
    ) -> Dict[str, Any]:
        """MAIL004 - Sync mails using delta links."""
        try:
            accounts_to_sync = []
            
            if account_id:
                account = await self.account_repo.get_account_by_id(account_id)
                if not account:
                    raise ValueError(f"Account {account_id} not found")
                accounts_to_sync = [account]
            else:
                accounts_to_sync = await self.account_repo.get_all_accounts()
            
            total_new_messages = 0
            
            for account in accounts_to_sync:
                token = await self.token_repo.get_token_by_account_id(account.id)
                if not token or token.is_expired:
                    continue
                
                # Get existing delta link
                delta_link = await self.delta_link_repo.get_delta_link(account.id, folder)
                delta_token = delta_link.delta_token if delta_link else None
                
                # Get delta messages
                response = await self.graph_client.get_delta_messages(
                    access_token=token.access_token,
                    user_id=account.user_id,
                    folder=folder,
                    delta_token=delta_token
                )
                
                messages = response.get("value", [])
                new_messages_count = 0
                
                for msg_data in messages:
                    # Check if message already exists
                    existing = await self.mail_repo.mail_exists(
                        message_id=msg_data["id"],
                        account_id=account.id
                    )
                    
                    if not existing:
                        mail_message = self._create_mail_message(msg_data, account.id, MailDirection.RECEIVED)
                        saved_message = await self.mail_repo.save_mail_message(mail_message)
                        new_messages_count += 1
                        
                        # Send to external API
                        await self._send_to_external_api(saved_message)
                
                total_new_messages += new_messages_count
                
                # Update delta link
                new_delta_token = self._extract_delta_token(response)
                if new_delta_token:
                    new_delta_link = DeltaLink(
                        account_id=account.id,
                        folder_id=folder,
                        delta_token=new_delta_token,
                        created_at=datetime.utcnow(),
                        last_used_at=datetime.utcnow(),
                        is_active=True
                    )
                    await self.delta_link_repo.save_delta_link(new_delta_link)
                
                # Log query history
                await self._log_query_history(
                    account_id=account.id,
                    query_type="delta",
                    query_parameters={"folder": folder, "delta_token": delta_token},
                    messages_found=len(messages),
                    new_messages=new_messages_count
                )
            
            logger.info(
                "Delta sync completed",
                accounts_synced=len(accounts_to_sync),
                new_messages=total_new_messages
            )
            
            return {
                "success": True,
                "accounts_synced": len(accounts_to_sync),
                "new_messages": total_new_messages
            }
            
        except Exception as e:
            logger.error(
                "Delta sync failed",
                account_id=account_id,
                error=str(e)
            )
            raise
    
    async def setup_webhook(
        self,
        account_id: str,
        notification_url: str,
        resource: str = "/me/mailFolders('Inbox')/messages",
        change_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """MAIL008 - Setup webhook subscription."""
        try:
            if not change_types:
                change_types = ["created", "updated"]
            
            account = await self.account_repo.get_account_by_id(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            token = await self.token_repo.get_token_by_account_id(account_id)
            if not token or token.is_expired:
                raise ValueError("No valid token available")
            
            # Generate client state
            client_state = str(uuid.uuid4())
            
            # Create webhook subscription
            response = await self.graph_client.create_webhook_subscription(
                access_token=token.access_token,
                user_id=account.user_id,
                notification_url=notification_url,
                resource=resource,
                change_types=change_types,
                client_state=client_state
            )
            
            # Save subscription
            subscription = WebhookSubscription(
                subscription_id=response["id"],
                account_id=account_id,
                resource=resource,
                change_types=change_types,
                notification_url=notification_url,
                client_state=client_state,
                expires_datetime=datetime.fromisoformat(response["expirationDateTime"].replace("Z", "+00:00")),
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            await self.webhook_repo.save_webhook_subscription(subscription)
            
            logger.info(
                "Webhook subscription created",
                account_id=account_id,
                subscription_id=response["id"]
            )
            
            return {
                "success": True,
                "subscription_id": response["id"],
                "expires_at": subscription.expires_datetime.isoformat()
            }
            
        except Exception as e:
            logger.error(
                "Failed to setup webhook",
                account_id=account_id,
                error=str(e)
            )
            raise
    
    async def process_webhook_notification(
        self,
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process incoming webhook notification."""
        try:
            # Validate notification
            client_state = notification_data.get("clientState")
            if not client_state:
                raise ValueError("Missing client state")
            
            # Find subscription
            # Note: This is simplified - in practice, you'd validate the client_state
            
            # Process each notification
            notifications = notification_data.get("value", [])
            processed_count = 0
            
            for notification in notifications:
                subscription_id = notification.get("subscriptionId")
                resource = notification.get("resource")
                change_type = notification.get("changeType")
                
                # Find account by subscription
                subscription = await self.webhook_repo.get_webhook_subscription(subscription_id)
                if not subscription:
                    continue
                
                # Trigger delta sync for the account
                await self.sync_delta_mails(account_id=subscription.account_id)
                processed_count += 1
            
            logger.info(
                "Webhook notifications processed",
                notifications_count=len(notifications),
                processed_count=processed_count
            )
            
            return {
                "success": True,
                "processed_count": processed_count
            }
            
        except Exception as e:
            logger.error(
                "Failed to process webhook notification",
                error=str(e)
            )
            raise
    
    def _create_mail_message(
        self,
        msg_data: Dict[str, Any],
        account_id: str,
        direction: MailDirection
    ) -> MailMessage:
        """Create MailMessage entity from Graph API response."""
        from_data = msg_data.get("from", {}).get("emailAddress", {})
        
        # Extract recipients
        to_recipients = [
            recipient["emailAddress"]["address"]
            for recipient in msg_data.get("toRecipients", [])
            if recipient.get("emailAddress", {}).get("address")
        ]
        
        cc_recipients = [
            recipient["emailAddress"]["address"]
            for recipient in msg_data.get("ccRecipients", [])
            if recipient.get("emailAddress", {}).get("address")
        ]
        
        bcc_recipients = [
            recipient["emailAddress"]["address"]
            for recipient in msg_data.get("bccRecipients", [])
            if recipient.get("emailAddress", {}).get("address")
        ]
        
        # Parse datetime
        received_datetime = datetime.fromisoformat(
            msg_data["receivedDateTime"].replace("Z", "+00:00")
        ).replace(tzinfo=None)
        
        sent_datetime = None
        if msg_data.get("sentDateTime"):
            sent_datetime = datetime.fromisoformat(
                msg_data["sentDateTime"].replace("Z", "+00:00")
            ).replace(tzinfo=None)
        
        return MailMessage(
            message_id=msg_data["id"],
            internet_message_id=msg_data.get("internetMessageId"),
            account_id=account_id,
            subject=msg_data.get("subject", ""),
            sender_email=from_data.get("address", ""),
            sender_name=from_data.get("name"),
            recipients=to_recipients,
            cc_recipients=cc_recipients,
            bcc_recipients=bcc_recipients,
            body_preview=msg_data.get("bodyPreview"),
            body_content=msg_data.get("body", {}).get("content"),
            body_content_type=msg_data.get("body", {}).get("contentType", "html").lower(),
            importance=MailImportance(msg_data.get("importance", "normal").lower()),
            is_read=msg_data.get("isRead", False),
            has_attachments=msg_data.get("hasAttachments", False),
            received_datetime=received_datetime,
            sent_datetime=sent_datetime,
            direction=direction,
            categories=msg_data.get("categories", []),
            created_at=datetime.utcnow()
        )
    
    async def _send_to_external_api(self, message: MailMessage) -> None:
        """Send mail message to external API."""
        try:
            external_config = self.config.get_external_api_config()
            endpoint_url = external_config.get("endpoint_url")
            
            if not endpoint_url:
                return
            
            # Prepare payload
            payload = {
                "message_id": message.message_id,
                "subject": message.subject,
                "sender_email": message.sender_email,
                "sender_name": message.sender_name,
                "body_content": message.body_content,
                "body_preview": message.body_preview,
                "received_datetime": message.received_datetime.isoformat(),
                "importance": message.importance.value,
                "direction": message.direction.value
            }
            
            # Create API call record
            api_call = ExternalAPICall(
                message_id=message.message_id,
                endpoint_url=endpoint_url,
                http_method="POST",
                request_payload=payload,
                created_at=datetime.utcnow()
            )
            
            try:
                # Send to external API
                response = await self.external_api_client.send_mail_data(
                    endpoint_url=endpoint_url,
                    mail_data=payload,
                    timeout=external_config.get("timeout", 30)
                )
                
                # Update API call record
                api_call.success = True
                api_call.response_status = response.get("status_code", 200)
                api_call.response_body = str(response)
                api_call.completed_at = datetime.utcnow()
                
            except Exception as e:
                # Update API call record with error
                api_call.success = False
                api_call.response_body = str(e)
                api_call.completed_at = datetime.utcnow()
                
                logger.error(
                    "Failed to send to external API",
                    message_id=message.message_id,
                    error=str(e)
                )
            
            # Save API call record
            await self.external_api_repo.save_api_call(api_call)
            
        except Exception as e:
            logger.error(
                "Error in external API call handling",
                message_id=message.message_id,
                error=str(e)
            )
    
    async def _log_query_history(
        self,
        account_id: str,
        query_type: str,
        query_parameters: Dict[str, Any],
        messages_found: int,
        new_messages: int,
        execution_time_ms: Optional[int] = None
    ) -> None:
        """Log mail query history."""
        try:
            history = MailQueryHistory(
                account_id=account_id,
                query_type=query_type,
                query_parameters=query_parameters,
                messages_found=messages_found,
                new_messages=new_messages,
                query_datetime=datetime.utcnow(),
                execution_time_ms=execution_time_ms,
                success=True
            )
            
            await self.query_history_repo.save_query_history(history)
            
        except Exception as e:
            logger.error(
                "Failed to log query history",
                account_id=account_id,
                error=str(e)
            )
    
    def _extract_delta_token(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract delta token from Graph API response."""
        delta_link = response.get("@odata.deltaLink")
        if delta_link and "$deltatoken=" in delta_link:
            return delta_link.split("$deltatoken=")[1].split("&")[0]
        return None
