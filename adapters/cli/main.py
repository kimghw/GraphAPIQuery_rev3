"""CLI main application."""

import asyncio
import json
from datetime import datetime
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
import structlog

from config.settings import get_settings
from adapters.db.database import get_database_adapter, migrate_database_sync
from adapters.db.repositories import DatabaseRepositoryAdapter
from adapters.external.graph_client import GraphAPIClientAdapter
from adapters.external.oauth_client import OAuthClientAdapter
from core.usecases.auth_usecases import AuthenticationUseCases
from core.usecases.mail_usecases import MailUseCases
from core.domain.entities import AuthenticationFlow, AccountStatus, Account

# Configure logging for CLI
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
console = Console()

app = typer.Typer(
    name="graphapi-cli",
    help="Microsoft Graph API Mail Collection System CLI",
    add_completion=False
)

# Sub-commands
auth_app = typer.Typer(name="auth", help="Authentication commands")
mail_app = typer.Typer(name="mail", help="Mail commands")
app.add_typer(auth_app)
app.add_typer(mail_app)


def get_usecases():
    """Get use cases instances."""
    settings = get_settings()
    
    # Initialize adapters
    db_adapter = get_database_adapter(settings)
    repo_adapter = DatabaseRepositoryAdapter(db_adapter)
    graph_adapter = GraphAPIClientAdapter(settings)
    oauth_adapter = OAuthClientAdapter(settings)
    
    # Initialize use cases
    auth_usecases = AuthenticationUseCases(
        account_repo=repo_adapter,
        token_repo=repo_adapter,
        auth_log_repo=repo_adapter,
        auth_flow_repo=repo_adapter,
        oauth_client=oauth_adapter,
        config=settings
    )
    
    mail_usecases = MailUseCases(
        account_repo=repo_adapter,
        token_repo=repo_adapter,
        mail_repo=repo_adapter,
        query_history_repo=repo_adapter,
        webhook_repo=repo_adapter,
        external_api_repo=repo_adapter,
        delta_link_repo=repo_adapter,
        external_api_client=graph_adapter,  # Using graph_adapter as external API client
        graph_client=graph_adapter,
        config=settings
    )
    
    return auth_usecases, mail_usecases


@app.command()
def init():
    """Initialize the database."""
    console.print("[bold blue]Initializing Microsoft Graph API Mail Collection System...[/bold blue]")
    
    try:
        settings = get_settings()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Migrating database...", total=None)
            migrate_database_sync(settings)
            progress.update(task, description="Database migration completed")
        
        console.print("[bold green]✓ System initialized successfully![/bold green]")
        console.print(f"Database: {settings.DATABASE_URL}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Initialization failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def status():
    """Show system status."""
    console.print("[bold blue]System Status[/bold blue]")
    
    try:
        settings = get_settings()
        
        # Create status table
        table = Table(title="Microsoft Graph API Mail Collection System")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")
        
        # Check database
        try:
            db_adapter = get_database_adapter(settings)
            with db_adapter.session_scope() as session:
                session.execute("SELECT 1")
            table.add_row("Database", "✓ Connected", settings.DATABASE_URL)
        except Exception as e:
            table.add_row("Database", "✗ Error", str(e))
        
        # System info
        table.add_row("Environment", "✓ Active", settings.ENVIRONMENT)
        table.add_row("Version", "✓ Running", "1.0.0")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]✗ Status check failed: {e}[/bold red]")
        raise typer.Exit(1)


# Authentication commands
@auth_app.command("create")
def create_account(
    email: str = typer.Option(..., help="User email address"),
    tenant_id: str = typer.Option(..., help="Azure AD tenant ID"),
    client_id: str = typer.Option(..., help="Application client ID"),
    flow: str = typer.Option("authorization_code", help="Authentication flow (authorization_code|device_code)"),
    client_secret: Optional[str] = typer.Option(None, help="Client secret (for authorization_code flow)"),
    redirect_uri: Optional[str] = typer.Option(None, help="Redirect URI (for authorization_code flow)"),
):
    """Create a new account."""
    try:
        auth_usecases, _ = get_usecases()
        
        # Validate flow
        if flow not in ["authorization_code", "device_code"]:
            console.print("[bold red]✗ Invalid flow. Use 'authorization_code' or 'device_code'[/bold red]")
            raise typer.Exit(1)
        
        auth_flow = AuthenticationFlow.AUTHORIZATION_CODE if flow == "authorization_code" else AuthenticationFlow.DEVICE_CODE
        
        # Validate required parameters
        if auth_flow == AuthenticationFlow.AUTHORIZATION_CODE:
            if not client_secret:
                client_secret = Prompt.ask("Client secret", password=True)
            if not redirect_uri:
                redirect_uri = Prompt.ask("Redirect URI", default="http://localhost:8000/auth/callback")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating account...", total=None)
            
            result = asyncio.run(auth_usecases.register_account(
                email=email,
                user_id=email,  # Use email as user_id for simplicity
                authentication_flow=auth_flow,
                scopes=["offline_access", "User.Read", "Mail.Read", "Mail.ReadWrite", "Mail.Send"]
            ))
            
            progress.update(task, description="Account created successfully")
        
        console.print(f"[bold green]✓ Account created successfully![/bold green]")
        console.print(f"Account ID: {result['account_id']}")
        console.print(f"Message: {result['message']}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to create account: {e}[/bold red]")
        raise typer.Exit(1)


@auth_app.command("list")
def list_accounts():
    """List all accounts."""
    try:
        auth_usecases, _ = get_usecases()
        
        accounts = asyncio.run(auth_usecases.get_all_accounts())
        
        if not accounts:
            console.print("[yellow]No accounts found[/yellow]")
            return
        
        table = Table(title="Accounts")
        table.add_column("ID", style="cyan")
        table.add_column("Email", style="green")
        table.add_column("Flow", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Last Auth")
        
        for account_data in accounts:
            account = account_data["account"]
            last_auth = account.get("last_authenticated_at")
            last_auth_str = last_auth.strftime("%Y-%m-%d %H:%M") if last_auth else "Never"
            table.add_row(
                account["id"][:8] + "...",
                account["email"],
                account["authentication_flow"],
                account["status"],
                last_auth_str
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to list accounts: {e}[/bold red]")
        raise typer.Exit(1)


@auth_app.command("authenticate")
def authenticate_account(
    account_id: Optional[str] = typer.Option(None, help="Account ID"),
    email: Optional[str] = typer.Option(None, help="Account email"),
):
    """Authenticate an account."""
    if not account_id and not email:
        console.print("[bold red]✗ Either account_id or email must be provided[/bold red]")
        raise typer.Exit(1)
    
    try:
        auth_usecases, _ = get_usecases()
        
        # Get account
        if account_id:
            account_info = asyncio.run(auth_usecases.get_account_info(account_id, by_email=False))
        else:
            account_info = asyncio.run(auth_usecases.get_account_info(email, by_email=True))
        
        if not account_info:
            console.print("[bold red]✗ Account not found[/bold red]")
            raise typer.Exit(1)
        
        account = Account(**account_info["account"])
        
        console.print(f"[bold blue]Authenticating account: {account.email}[/bold blue]")
        
        # Start authentication process
        result = asyncio.run(auth_usecases.authenticate_account(account.id))
        
        if result.get("requires_user_action"):
            if account.authentication_flow == AuthenticationFlow.AUTHORIZATION_CODE:
                # Authorization code flow
                console.print(Panel(
                    f"[bold green]Please visit the following URL to authenticate:[/bold green]\n\n{result['authorization_url']}",
                    title="Authorization Required",
                    border_style="green"
                ))
                console.print("[yellow]After authentication, the system will automatically receive the callback.[/yellow]")
                
            else:
                # Device code flow
                console.print(Panel(
                    f"[bold green]Go to:[/bold green] {result['verification_uri']}\n"
                    f"[bold green]Enter code:[/bold green] {result['user_code']}",
                    title="Device Authentication",
                    border_style="green"
                ))
                console.print("[yellow]Complete the authentication in your browser, then run the command again to check status.[/yellow]")
        else:
            console.print("[bold green]✓ Authentication completed successfully![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Authentication failed: {e}[/bold red]")
        raise typer.Exit(1)


@auth_app.command("tokens")
def show_tokens(
    account_id: Optional[str] = typer.Option(None, help="Account ID (show all if not specified)")
):
    """Show token status."""
    try:
        auth_usecases, _ = get_usecases()
        
        if account_id:
            token = asyncio.run(auth_usecases.get_token_status(account_id))
            tokens = [token] if token else []
        else:
            tokens = asyncio.run(auth_usecases.get_all_token_status())
        
        if not tokens:
            console.print("[yellow]No tokens found[/yellow]")
            return
        
        table = Table(title="Token Status")
        table.add_column("Account ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Expires", style="red")
        table.add_column("Scopes")
        
        for token in tokens:
            expires = token.expires_at.strftime("%Y-%m-%d %H:%M") if token.expires_at else "Never"
            scopes = ", ".join(token.scopes[:3]) + ("..." if len(token.scopes) > 3 else "")
            
            table.add_row(
                token.account_id[:8] + "...",
                token.token_type,
                token.status.value,
                expires,
                scopes
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to show tokens: {e}[/bold red]")
        raise typer.Exit(1)


# Mail commands
@mail_app.command("query")
def query_mail(
    account_id: Optional[str] = typer.Option(None, help="Account ID (query all accounts if not specified)"),
    folder: str = typer.Option("inbox", help="Folder to query"),
    days: int = typer.Option(7, help="Number of days to look back"),
    limit: int = typer.Option(10, help="Maximum number of messages to return"),
    sender: Optional[str] = typer.Option(None, help="Filter by sender email"),
    unread_only: bool = typer.Option(False, help="Show only unread messages"),
    output_format: str = typer.Option("table", help="Output format (table|json)"),
):
    """Query mail messages."""
    try:
        _, mail_usecases = get_usecases()
        
        # Calculate date range
        date_from = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        date_from = date_from.replace(day=date_from.day - days)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Querying mail...", total=None)
            
            result = asyncio.run(mail_usecases.query_mail(
                account_id=account_id,
                folder_id=folder,
                date_from=date_from,
                sender_email=sender,
                is_read=False if unread_only else None,
                top=limit
            ))
            
            progress.update(task, description="Query completed")
        
        if output_format == "json":
            # JSON output
            messages_data = []
            for msg in result.messages:
                messages_data.append({
                    "message_id": msg.message_id,
                    "subject": msg.subject,
                    "sender_email": msg.sender_email,
                    "sender_name": msg.sender_name,
                    "received_datetime": msg.received_datetime.isoformat(),
                    "is_read": msg.is_read,
                    "importance": msg.importance.value,
                    "has_attachments": msg.has_attachments
                })
            
            console.print(json.dumps({
                "total_found": result.total_found,
                "new_messages": result.new_messages,
                "messages": messages_data
            }, indent=2))
        
        else:
            # Table output
            if not result.messages:
                console.print("[yellow]No messages found[/yellow]")
                return
            
            table = Table(title=f"Mail Messages ({result.total_found} found, {result.new_messages} new)")
            table.add_column("Subject", style="cyan", max_width=40)
            table.add_column("From", style="green", max_width=30)
            table.add_column("Date", style="blue")
            table.add_column("Status", style="yellow")
            table.add_column("Importance", style="red")
            
            for msg in result.messages:
                status = "📧" if msg.is_read else "📩"
                importance = {"low": "🔽", "normal": "➖", "high": "🔺"}.get(msg.importance.value, "➖")
                date_str = msg.received_datetime.strftime("%m-%d %H:%M")
                
                table.add_row(
                    msg.subject or "(No subject)",
                    f"{msg.sender_name or msg.sender_email or 'Unknown'}",
                    date_str,
                    status,
                    importance
                )
            
            console.print(table)
            
            if result.new_messages > 0:
                console.print(f"[bold green]✓ {result.new_messages} new messages processed[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to query mail: {e}[/bold red]")
        raise typer.Exit(1)


@mail_app.command("send")
def send_mail(
    account_id: Optional[str] = typer.Option(None, help="Account ID"),
    to: str = typer.Option(..., help="Recipient email address"),
    subject: str = typer.Option(..., help="Email subject"),
    body: str = typer.Option(..., help="Email body"),
    body_type: str = typer.Option("text", help="Body type (text|html)"),
):
    """Send a mail message."""
    try:
        _, mail_usecases = get_usecases()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Sending mail...", total=None)
            
            result = asyncio.run(mail_usecases.send_mail(
                account_id=account_id,
                to_recipients=[to],
                subject=subject,
                body=body,
                body_type=body_type
            ))
            
            progress.update(task, description="Mail sent successfully")
        
        console.print(f"[bold green]✓ Mail sent successfully![/bold green]")
        if result.message_id:
            console.print(f"Message ID: {result.message_id}")
        console.print(f"Sent at: {result.sent_at}")
        
    except Exception as e:
        console.print(f"[bold red]✗ Failed to send mail: {e}[/bold red]")
        raise typer.Exit(1)


@mail_app.command("sync")
def delta_sync(
    account_id: Optional[str] = typer.Option(None, help="Account ID (sync all accounts if not specified)"),
    folder: str = typer.Option("inbox", help="Folder to sync"),
):
    """Perform delta synchronization."""
    try:
        _, mail_usecases = get_usecases()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Performing delta sync...", total=None)
            
            result = asyncio.run(mail_usecases.delta_sync(
                account_id=account_id,
                folder_id=folder
            ))
            
            progress.update(task, description="Delta sync completed")
        
        console.print(f"[bold green]✓ Delta sync completed![/bold green]")
        console.print(f"New messages: {result.new_messages}")
        console.print(f"Updated messages: {result.updated_messages}")
        console.print(f"Deleted messages: {result.deleted_messages}")
        
        if result.new_messages > 0:
            console.print(f"[bold blue]Processing {result.new_messages} new messages...[/bold blue]")
        
    except Exception as e:
        console.print(f"[bold red]✗ Delta sync failed: {e}[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
