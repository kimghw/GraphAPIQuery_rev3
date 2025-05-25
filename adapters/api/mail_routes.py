"""Mail API routes."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
import structlog

from core.usecases.mail_usecases import MailUseCases
from adapters.api.dependencies import get_mail_usecases
from adapters.api.schemas import (
    MailQueryRequest, MailQueryResponse, MailMessageResponse,
    SendMailRequest, SendMailResponse, DeltaSyncRequest, DeltaSyncResponse,
    CreateWebhookRequest, WebhookResponse, WebhookNotification,
    WebhookValidationRequest, QueryHistoryListResponse,
    ExternalAPIListResponse, BaseResponse, RecipientInfo
)

logger = structlog.get_logger()

router = APIRouter(prefix="/mail", tags=["Mail"])


@router.post(
    "/query",
    response_model=MailQueryResponse,
    summary="Query mail messages",
    description="Query mail messages with filters and pagination"
)
async def query_mail(
    request: MailQueryRequest,
    background_tasks: BackgroundTasks,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> MailQueryResponse:
    """Query mail messages."""
    try:
        result = await mail_usecases.query_mail(
            account_id=request.account_id,
            folder_id=request.folder_id,
            date_from=request.date_from,
            date_to=request.date_to,
            sender_email=request.sender_email,
            is_read=request.is_read,
            importance=request.importance,
            search=request.search,
            top=request.top,
            skip=request.skip
        )
        
        # Convert messages to response format
        message_responses = []
        for message in result.messages:
            recipients = [
                RecipientInfo(email=r.email, name=r.name)
                for r in message.recipients
            ]
            cc_recipients = [
                RecipientInfo(email=r.email, name=r.name)
                for r in (message.cc_recipients or [])
            ]
            bcc_recipients = [
                RecipientInfo(email=r.email, name=r.name)
                for r in (message.bcc_recipients or [])
            ]
            
            message_responses.append(MailMessageResponse(
                message_id=message.message_id,
                internet_message_id=message.internet_message_id,
                account_id=message.account_id,
                subject=message.subject,
                sender_email=message.sender_email,
                sender_name=message.sender_name,
                recipients=recipients,
                cc_recipients=cc_recipients if cc_recipients else None,
                bcc_recipients=bcc_recipients if bcc_recipients else None,
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
            ))
        
        # Process new messages in background if any
        if result.new_messages > 0:
            background_tasks.add_task(
                mail_usecases.process_new_messages,
                [msg for msg in result.messages if msg.message_id not in result.existing_message_ids]
            )
        
        return MailQueryResponse(
            messages=message_responses,
            total_found=result.total_found,
            new_messages=result.new_messages,
            has_more=result.has_more,
            next_skip=result.next_skip
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to query mail", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query mail"
        )


@router.post(
    "/send",
    response_model=SendMailResponse,
    summary="Send mail message",
    description="Send a mail message"
)
async def send_mail(
    request: SendMailRequest,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> SendMailResponse:
    """Send mail message."""
    try:
        result = await mail_usecases.send_mail(
            account_id=request.account_id,
            to_recipients=request.to_recipients,
            subject=request.subject,
            body=request.body,
            body_type=request.body_type,
            cc_recipients=request.cc_recipients,
            bcc_recipients=request.bcc_recipients,
            save_to_sent_items=request.save_to_sent_items
        )
        
        return SendMailResponse(
            message_id=result.message_id,
            sent_at=result.sent_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to send mail", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send mail"
        )


@router.post(
    "/delta-sync",
    response_model=DeltaSyncResponse,
    summary="Perform delta sync",
    description="Perform incremental mail synchronization using delta links"
)
async def delta_sync(
    request: DeltaSyncRequest,
    background_tasks: BackgroundTasks,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> DeltaSyncResponse:
    """Perform delta sync."""
    try:
        result = await mail_usecases.delta_sync(
            account_id=request.account_id,
            folder_id=request.folder_id
        )
        
        # Convert messages to response format
        message_responses = []
        for message in result.messages:
            recipients = [
                RecipientInfo(email=r.email, name=r.name)
                for r in message.recipients
            ]
            cc_recipients = [
                RecipientInfo(email=r.email, name=r.name)
                for r in (message.cc_recipients or [])
            ]
            bcc_recipients = [
                RecipientInfo(email=r.email, name=r.name)
                for r in (message.bcc_recipients or [])
            ]
            
            message_responses.append(MailMessageResponse(
                message_id=message.message_id,
                internet_message_id=message.internet_message_id,
                account_id=message.account_id,
                subject=message.subject,
                sender_email=message.sender_email,
                sender_name=message.sender_name,
                recipients=recipients,
                cc_recipients=cc_recipients if cc_recipients else None,
                bcc_recipients=bcc_recipients if bcc_recipients else None,
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
            ))
        
        # Process new messages in background if any
        if result.new_messages > 0:
            background_tasks.add_task(
                mail_usecases.process_new_messages,
                [msg for msg in result.messages if msg.is_new]
            )
        
        return DeltaSyncResponse(
            messages=message_responses,
            new_messages=result.new_messages,
            updated_messages=result.updated_messages,
            deleted_messages=result.deleted_messages,
            delta_token=result.delta_token,
            next_sync_available=result.next_sync_available
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to perform delta sync", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform delta sync"
        )


@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create webhook subscription",
    description="Create a webhook subscription for mail notifications"
)
async def create_webhook(
    request: CreateWebhookRequest,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> WebhookResponse:
    """Create webhook subscription."""
    try:
        webhook = await mail_usecases.create_webhook_subscription(
            account_id=request.account_id,
            resource=request.resource,
            change_types=request.change_types,
            notification_url=request.notification_url,
            expiration_hours=request.expiration_hours
        )
        
        return WebhookResponse(
            subscription_id=webhook.subscription_id,
            account_id=webhook.account_id,
            resource=webhook.resource,
            change_types=webhook.change_types,
            notification_url=webhook.notification_url,
            expires_datetime=webhook.expires_datetime,
            is_active=webhook.is_active,
            created_at=webhook.created_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to create webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create webhook"
        )


@router.post(
    "/webhooks/notifications",
    summary="Handle webhook notification",
    description="Handle incoming webhook notifications from Microsoft Graph"
)
async def handle_webhook_notification(
    notification: WebhookNotification,
    background_tasks: BackgroundTasks,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
):
    """Handle webhook notification."""
    try:
        # Validate webhook notification
        is_valid = await mail_usecases.validate_webhook_notification(
            subscription_id=notification.subscription_id,
            client_state=notification.client_state
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook notification"
            )
        
        # Process notification in background
        background_tasks.add_task(
            mail_usecases.process_webhook_notification,
            notification.subscription_id,
            notification.change_type,
            notification.resource,
            notification.resource_data
        )
        
        return {"status": "accepted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to handle webhook notification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to handle webhook notification"
        )


@router.get(
    "/webhooks/validate",
    summary="Validate webhook subscription",
    description="Validate webhook subscription during creation"
)
async def validate_webhook(
    validationToken: str
):
    """Validate webhook subscription."""
    # Microsoft Graph sends validation token as query parameter
    # We need to return it as plain text response
    return validationToken


@router.get(
    "/webhooks/{account_id}",
    response_model=List[WebhookResponse],
    summary="List webhooks",
    description="List webhook subscriptions for an account"
)
async def list_webhooks(
    account_id: str,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> List[WebhookResponse]:
    """List webhook subscriptions."""
    try:
        webhooks = await mail_usecases.get_webhook_subscriptions(account_id)
        
        return [
            WebhookResponse(
                subscription_id=webhook.subscription_id,
                account_id=webhook.account_id,
                resource=webhook.resource,
                change_types=webhook.change_types,
                notification_url=webhook.notification_url,
                expires_datetime=webhook.expires_datetime,
                is_active=webhook.is_active,
                created_at=webhook.created_at
            )
            for webhook in webhooks
        ]
        
    except Exception as e:
        logger.error("Failed to list webhooks", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list webhooks"
        )


@router.delete(
    "/webhooks/{subscription_id}",
    response_model=BaseResponse,
    summary="Delete webhook subscription",
    description="Delete a webhook subscription"
)
async def delete_webhook(
    subscription_id: str,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> BaseResponse:
    """Delete webhook subscription."""
    try:
        success = await mail_usecases.delete_webhook_subscription(subscription_id)
        
        return BaseResponse(
            success=success,
            message="Webhook deleted successfully" if success else "Webhook not found"
        )
        
    except Exception as e:
        logger.error("Failed to delete webhook", subscription_id=subscription_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete webhook"
        )


@router.get(
    "/query-history",
    response_model=QueryHistoryListResponse,
    summary="Get query history",
    description="Get mail query history with optional filters"
)
async def get_query_history(
    account_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> QueryHistoryListResponse:
    """Get query history."""
    try:
        histories = await mail_usecases.get_query_history(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )
        
        history_responses = [
            {
                "account_id": history.account_id,
                "query_type": history.query_type,
                "query_parameters": history.query_parameters,
                "messages_found": history.messages_found,
                "new_messages": history.new_messages,
                "query_datetime": history.query_datetime,
                "execution_time_ms": history.execution_time_ms,
                "success": history.success,
                "error_message": history.error_message
            }
            for history in histories
        ]
        
        return QueryHistoryListResponse(
            histories=history_responses,
            total=len(history_responses)
        )
        
    except Exception as e:
        logger.error("Failed to get query history", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get query history"
        )


@router.get(
    "/external-api-calls",
    response_model=ExternalAPIListResponse,
    summary="Get external API calls",
    description="Get external API call history"
)
async def get_external_api_calls(
    account_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    success: Optional[bool] = None,
    limit: int = 100,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> ExternalAPIListResponse:
    """Get external API calls."""
    try:
        api_calls = await mail_usecases.get_external_api_calls(
            account_id=account_id,
            date_from=date_from,
            date_to=date_to,
            success=success,
            limit=limit
        )
        
        api_call_responses = [
            {
                "message_id": call.message_id,
                "endpoint_url": call.endpoint_url,
                "http_method": call.http_method,
                "request_payload": call.request_payload,
                "response_status": call.response_status,
                "response_body": call.response_body,
                "success": call.success,
                "retry_count": call.retry_count,
                "created_at": call.created_at,
                "completed_at": call.completed_at
            }
            for call in api_calls
        ]
        
        return ExternalAPIListResponse(
            api_calls=api_call_responses,
            total=len(api_call_responses)
        )
        
    except Exception as e:
        logger.error("Failed to get external API calls", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get external API calls"
        )


@router.post(
    "/process-new/{account_id}",
    response_model=BaseResponse,
    summary="Process new messages",
    description="Manually trigger processing of new messages for an account"
)
async def process_new_messages(
    account_id: str,
    background_tasks: BackgroundTasks,
    mail_usecases: MailUseCases = Depends(get_mail_usecases)
) -> BaseResponse:
    """Process new messages for an account."""
    try:
        # Start background task to process new messages
        background_tasks.add_task(
            mail_usecases.process_account_new_messages,
            account_id
        )
        
        return BaseResponse(
            message="Processing new messages started in background"
        )
        
    except Exception as e:
        logger.error("Failed to start processing new messages", account_id=account_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start processing new messages"
        )
