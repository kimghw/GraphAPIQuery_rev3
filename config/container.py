"""Dependency injection container configuration."""

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject

from config.settings import Settings
from adapters.db.database import DatabaseAdapter
from adapters.db.repositories import (
    AccountRepository,
    TokenRepository,
    MailQueryLogRepository,
    WebhookSubscriptionRepository
)
from adapters.external.graph_client import GraphAPIClient
from adapters.external.oauth_client import OAuthClient
from core.usecases.auth_usecases import AuthenticationUseCases
from core.usecases.mail_usecases import MailUseCases


class Container(containers.DeclarativeContainer):
    """Application dependency injection container."""
    
    # Configuration
    config = providers.Configuration()
    
    # Settings
    settings = providers.Singleton(
        Settings
    )
    
    # Database
    database_adapter = providers.Singleton(
        DatabaseAdapter,
        settings=settings
    )
    
    # Repositories
    account_repository = providers.Factory(
        AccountRepository,
        session_factory=database_adapter.provided.session_scope
    )
    
    token_repository = providers.Factory(
        TokenRepository,
        session_factory=database_adapter.provided.session_scope
    )
    
    mail_query_log_repository = providers.Factory(
        MailQueryLogRepository,
        session_factory=database_adapter.provided.session_scope
    )
    
    webhook_subscription_repository = providers.Factory(
        WebhookSubscriptionRepository,
        session_factory=database_adapter.provided.session_scope
    )
    
    # External clients
    oauth_client = providers.Factory(
        OAuthClient,
        settings=settings
    )
    
    graph_api_client = providers.Factory(
        GraphAPIClient,
        settings=settings
    )
    
    # Use cases
    auth_usecases = providers.Factory(
        AuthenticationUseCases,
        account_repo=account_repository,
        token_repo=token_repository,
        oauth_client=oauth_client
    )
    
    mail_usecases = providers.Factory(
        MailUseCases,
        account_repo=account_repository,
        token_repo=token_repository,
        mail_query_log_repo=mail_query_log_repository,
        webhook_subscription_repo=webhook_subscription_repository,
        graph_client=graph_api_client,
        oauth_client=oauth_client
    )


def create_container() -> Container:
    """Create and configure the dependency injection container."""
    container = Container()
    
    # Wire the container to modules that need dependency injection
    container.wire(modules=[
        "adapters.api.auth_routes",
        "adapters.api.mail_routes",
        "adapters.api.dependencies",
        "adapters.cli.main",
        "main"
    ])
    
    return container


# Global container instance
container = create_container()
