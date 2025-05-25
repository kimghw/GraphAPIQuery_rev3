"""Main FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

from config.settings import get_settings
from adapters.db.database import get_database_adapter, migrate_database
from adapters.api.auth_routes import router as auth_router
from adapters.api.mail_routes import router as mail_router
from adapters.api.schemas import HealthCheckResponse, ErrorResponse


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Microsoft Graph API Mail Collection System")
    
    try:
        # Initialize database
        settings = get_settings()
        logger.info("Initializing database", database_url=settings.DATABASE_URL)
        
        await migrate_database(settings)
        logger.info("Database migration completed")
        
        # Test database connection
        db_adapter = get_database_adapter(settings)
        async with db_adapter.session_scope() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down Microsoft Graph API Mail Collection System")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Microsoft Graph API Mail Collection System",
        description="""
        A comprehensive system for collecting and managing Microsoft 365 email data 
        using Microsoft Graph API with OAuth 2.0 authentication.
        
        ## Features
        
        * **Multi-user Authentication**: Support for Authorization Code Flow and Device Code Flow
        * **Mail Operations**: Query, send, and manage email messages
        * **Delta Synchronization**: Incremental mail sync using delta links
        * **Webhook Support**: Real-time notifications for new messages
        * **Query History**: Track and audit all mail queries
        * **External API Integration**: Forward new messages to external systems
        
        ## Authentication Flows
        
        ### Authorization Code Flow
        1. Create account with `client_secret` and `redirect_uri`
        2. Call `/auth/authenticate` to get authorization URL
        3. User visits URL and grants permissions
        4. System receives callback and exchanges code for tokens
        
        ### Device Code Flow
        1. Create account with `authentication_flow: "device_code"`
        2. Call `/auth/device-code` to get user code
        3. User visits verification URI and enters code
        4. Poll `/auth/device-code/poll/{account_id}` until complete
        
        ## Mail Operations
        
        * **Query**: Filter messages by date, sender, read status, importance
        * **Send**: Send emails with HTML or text content
        * **Delta Sync**: Get only new/updated messages since last sync
        * **Webhooks**: Receive real-time notifications for new messages
        
        ## Security
        
        * OAuth 2.0 with PKCE for secure authentication
        * Token refresh and validation
        * Webhook signature verification
        * Structured logging for audit trails
        """,
        version="1.0.0",
        contact={
            "name": "Microsoft Graph API Mail Collection System",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add routers
    app.include_router(auth_router)
    app.include_router(mail_router)
    
    return app


app = create_app()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=f"HTTP_{exc.status_code}",
            error_message=exc.detail
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception occurred",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            error_message="An internal server error occurred"
        ).dict()
    )


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(
        "HTTP request started",
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    # Log response
    logger.info(
        "HTTP request completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=duration
    )
    
    return response


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "message": "Microsoft Graph API Mail Collection System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check system health and status"
)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    settings = get_settings()
    services = {}
    
    # Check database
    try:
        db_adapter = get_database_adapter(settings)
        async with db_adapter.session_scope() as session:
            await session.execute(text("SELECT 1"))
        services["database"] = "healthy"
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        services["database"] = "unhealthy"
    
    # Check external services (could add Graph API ping here)
    services["graph_api"] = "not_checked"
    
    # Determine overall status
    overall_status = "healthy" if all(
        status in ["healthy", "not_checked"] 
        for status in services.values()
    ) else "unhealthy"
    
    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        database=services["database"],
        services=services
    )


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """Get OpenAPI schema."""
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


if __name__ == "__main__":
    settings = get_settings()
    
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_config=log_config,
        access_log=True
    )
