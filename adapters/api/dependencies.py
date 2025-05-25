"""FastAPI dependencies."""

from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings, Settings
from adapters.db.database import get_database_adapter, DatabaseAdapter
from adapters.db.repositories import (
    AccountRepository, AuthFlowRepository, TokenRepository,
    MailRepository, MailQueryHistoryRepository, DeltaLinkRepository,
    WebhookRepository, ExternalAPIRepository, AuthenticationLogRepository
)
from adapters.external.oauth_client import OAuthClientAdapter
from adapters.external.graph_client import GraphAPIClientAdapter
from core.usecases.auth_usecases import AuthenticationUseCases
from core.usecases.mail_usecases import MailUseCases


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    settings = get_settings()
    db_adapter = get_database_adapter(settings)
    
    async with db_adapter.session_scope() as session:
        yield session


async def get_account_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AccountRepository:
    """Get account repository."""
    return AccountRepository(session)


async def get_auth_flow_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AuthFlowRepository:
    """Get auth flow repository."""
    return AuthFlowRepository(session)


async def get_token_repository(
    session: AsyncSession = Depends(get_db_session)
) -> TokenRepository:
    """Get token repository."""
    return TokenRepository(session)


async def get_mail_repository(
    session: AsyncSession = Depends(get_db_session)
) -> MailRepository:
    """Get mail repository."""
    return MailRepository(session)


async def get_mail_query_history_repository(
    session: AsyncSession = Depends(get_db_session)
) -> MailQueryHistoryRepository:
    """Get mail query history repository."""
    return MailQueryHistoryRepository(session)


async def get_delta_link_repository(
    session: AsyncSession = Depends(get_db_session)
) -> DeltaLinkRepository:
    """Get delta link repository."""
    return DeltaLinkRepository(session)


async def get_webhook_repository(
    session: AsyncSession = Depends(get_db_session)
) -> WebhookRepository:
    """Get webhook repository."""
    return WebhookRepository(session)


async def get_external_api_repository(
    session: AsyncSession = Depends(get_db_session)
) -> ExternalAPIRepository:
    """Get external API repository."""
    return ExternalAPIRepository(session)


async def get_auth_log_repository(
    session: AsyncSession = Depends(get_db_session)
) -> AuthenticationLogRepository:
    """Get authentication log repository."""
    return AuthenticationLogRepository(session)


async def get_oauth_client() -> OAuthClientAdapter:
    """Get OAuth client."""
    settings = get_settings()
    return OAuthClientAdapter(settings)


async def get_graph_client() -> GraphAPIClientAdapter:
    """Get Graph API client."""
    settings = get_settings()
    return GraphAPIClientAdapter(settings)


async def get_auth_usecases(
    account_repo: AccountRepository = Depends(get_account_repository),
    auth_flow_repo: AuthFlowRepository = Depends(get_auth_flow_repository),
    token_repo: TokenRepository = Depends(get_token_repository),
    auth_log_repo: AuthenticationLogRepository = Depends(get_auth_log_repository),
    oauth_client: OAuthClientAdapter = Depends(get_oauth_client),
    graph_client: GraphAPIClientAdapter = Depends(get_graph_client)
) -> AuthenticationUseCases:
    """Get authentication use cases."""
    return AuthenticationUseCases(
        account_repository=account_repo,
        auth_flow_repository=auth_flow_repo,
        token_repository=token_repo,
        auth_log_repository=auth_log_repo,
        oauth_client=oauth_client,
        graph_client=graph_client
    )


async def get_mail_usecases(
    account_repo: AccountRepository = Depends(get_account_repository),
    token_repo: TokenRepository = Depends(get_token_repository),
    mail_repo: MailRepository = Depends(get_mail_repository),
    mail_query_repo: MailQueryHistoryRepository = Depends(get_mail_query_history_repository),
    delta_link_repo: DeltaLinkRepository = Depends(get_delta_link_repository),
    webhook_repo: WebhookRepository = Depends(get_webhook_repository),
    external_api_repo: ExternalAPIRepository = Depends(get_external_api_repository),
    graph_client: GraphAPIClientAdapter = Depends(get_graph_client)
) -> MailUseCases:
    """Get mail use cases."""
    return MailUseCases(
        account_repository=account_repo,
        token_repository=token_repo,
        mail_repository=mail_repo,
        mail_query_history_repository=mail_query_repo,
        delta_link_repository=delta_link_repo,
        webhook_repository=webhook_repo,
        external_api_repository=external_api_repo,
        graph_client=graph_client
    )
