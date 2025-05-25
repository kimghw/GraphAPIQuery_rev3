"""Configuration management CLI commands."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from typing import Dict, Any
import json

from config.settings import validate_settings, get_settings
from config.validation import validate_environment_file, check_security_configuration, get_config_summary

app = typer.Typer(help="Configuration management commands")
console = Console()


@app.command("validate")
def validate_config():
    """
    Validate the current configuration.
    
    Checks environment file, settings validation, and security configuration.
    """
    console.print("\n🔍 [bold blue]Configuration Validation[/bold blue]\n")
    
    try:
        # Validate settings
        validation_results = validate_settings()
        
        # Display overall status
        if validation_results["valid"]:
            console.print("✅ [bold green]Configuration is valid[/bold green]\n")
        else:
            console.print("❌ [bold red]Configuration has errors[/bold red]\n")
        
        # Display errors
        if validation_results["errors"]:
            error_table = Table(title="❌ Configuration Errors", show_header=False)
            error_table.add_column("Error", style="red")
            
            for error in validation_results["errors"]:
                error_table.add_row(f"• {error}")
            
            console.print(error_table)
            console.print()
        
        # Display warnings
        if validation_results["warnings"]:
            warning_table = Table(title="⚠️  Configuration Warnings", show_header=False)
            warning_table.add_column("Warning", style="yellow")
            
            for warning in validation_results["warnings"]:
                warning_table.add_row(f"• {warning}")
            
            console.print(warning_table)
            console.print()
        
        # Display environment file check
        env_check = validation_results.get("env_file_check", {})
        if env_check:
            _display_env_file_check(env_check)
        
        # Display configuration summary
        summary = validation_results.get("summary", {})
        if summary:
            _display_config_summary(summary)
        
        # Exit with appropriate code
        if not validation_results["valid"]:
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ [bold red]Validation failed: {str(e)}[/bold red]")
        raise typer.Exit(1)


@app.command("summary")
def config_summary():
    """
    Display a summary of the current configuration.
    """
    console.print("\n📋 [bold blue]Configuration Summary[/bold blue]\n")
    
    try:
        settings = get_settings()
        summary = get_config_summary(settings)
        
        _display_config_summary(summary)
        
    except Exception as e:
        console.print(f"❌ [bold red]Failed to get configuration summary: {str(e)}[/bold red]")
        raise typer.Exit(1)


@app.command("security-check")
def security_check():
    """
    Check security configuration and display warnings.
    """
    console.print("\n🔒 [bold blue]Security Configuration Check[/bold blue]\n")
    
    try:
        settings = get_settings()
        warnings = check_security_configuration(settings)
        
        if not warnings:
            console.print("✅ [bold green]No security issues found[/bold green]")
        else:
            warning_table = Table(title="🔒 Security Warnings", show_header=False)
            warning_table.add_column("Warning", style="yellow")
            
            for warning in warnings:
                warning_table.add_row(f"• {warning}")
            
            console.print(warning_table)
            
            if settings.is_production():
                console.print("\n⚠️  [bold yellow]Production environment detected - please address these warnings[/bold yellow]")
        
    except Exception as e:
        console.print(f"❌ [bold red]Security check failed: {str(e)}[/bold red]")
        raise typer.Exit(1)


@app.command("env-check")
def env_file_check():
    """
    Check the .env file for required variables and common issues.
    """
    console.print("\n📄 [bold blue]Environment File Check[/bold blue]\n")
    
    try:
        env_check = validate_environment_file()
        _display_env_file_check(env_check)
        
        if env_check["errors"]:
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"❌ [bold red]Environment file check failed: {str(e)}[/bold red]")
        raise typer.Exit(1)


@app.command("export")
def export_config(
    output_file: str = typer.Option("config_export.json", help="Output file path"),
    include_secrets: bool = typer.Option(False, help="Include sensitive configuration")
):
    """
    Export current configuration to a JSON file.
    """
    console.print(f"\n📤 [bold blue]Exporting Configuration to {output_file}[/bold blue]\n")
    
    try:
        settings = get_settings()
        
        # Get configuration data
        config_data = {
            "environment": settings.ENVIRONMENT,
            "app_info": {
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION
            },
            "server": {
                "host": settings.HOST,
                "port": settings.PORT
            },
            "database": {
                "url": settings.DATABASE_URL if include_secrets else "***HIDDEN***",
                "echo": settings.DATABASE_ECHO
            },
            "graph_api": {
                "endpoint": settings.GRAPH_API_ENDPOINT,
                "client_id": settings.CLIENT_ID if include_secrets else "***HIDDEN***",
                "tenant_id": settings.TENANT_ID if include_secrets else "***HIDDEN***",
                "redirect_uri": settings.REDIRECT_URI
            },
            "features": {
                "cache_enabled": bool(getattr(settings, 'REDIS_URL', None)),
                "metrics_enabled": getattr(settings, 'METRICS_ENABLED', True),
                "rate_limit_enabled": getattr(settings, 'RATE_LIMIT_ENABLED', False),
                "background_tasks_enabled": getattr(settings, 'BACKGROUND_TASKS_ENABLED', True)
            },
            "cors_origins": settings.CORS_ORIGINS,
            "log_level": settings.LOG_LEVEL
        }
        
        # Add validation results
        validation_results = validate_settings()
        config_data["validation"] = {
            "valid": validation_results["valid"],
            "error_count": len(validation_results["errors"]),
            "warning_count": len(validation_results["warnings"])
        }
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
        
        console.print(f"✅ [bold green]Configuration exported to {output_file}[/bold green]")
        
        if not include_secrets:
            console.print("ℹ️  [dim]Sensitive data was hidden. Use --include-secrets to export all data.[/dim]")
        
    except Exception as e:
        console.print(f"❌ [bold red]Export failed: {str(e)}[/bold red]")
        raise typer.Exit(1)


def _display_env_file_check(env_check: Dict[str, Any]):
    """Display environment file check results."""
    
    # File existence
    if env_check["file_exists"]:
        console.print("✅ [green].env file found[/green]")
    else:
        console.print("❌ [red].env file not found[/red]")
        return
    
    # Required variables
    if env_check["required_vars_present"]:
        present_table = Table(title="✅ Required Variables Present", show_header=False)
        present_table.add_column("Variable", style="green")
        
        for var in env_check["required_vars_present"]:
            present_table.add_row(f"• {var}")
        
        console.print(present_table)
        console.print()
    
    # Missing variables
    if env_check["missing_vars"]:
        missing_table = Table(title="❌ Missing Required Variables", show_header=False)
        missing_table.add_column("Variable", style="red")
        
        for var in env_check["missing_vars"]:
            missing_table.add_row(f"• {var}")
        
        console.print(missing_table)
        console.print()
    
    # Warnings
    if env_check["warnings"]:
        warning_table = Table(title="⚠️  Environment File Warnings", show_header=False)
        warning_table.add_column("Warning", style="yellow")
        
        for warning in env_check["warnings"]:
            warning_table.add_row(f"• {warning}")
        
        console.print(warning_table)
        console.print()
    
    # Errors
    if env_check["errors"]:
        error_table = Table(title="❌ Environment File Errors", show_header=False)
        error_table.add_column("Error", style="red")
        
        for error in env_check["errors"]:
            error_table.add_row(f"• {error}")
        
        console.print(error_table)
        console.print()


def _display_config_summary(summary: Dict[str, Any]):
    """Display configuration summary."""
    
    # Create summary table
    summary_table = Table(title="📋 Configuration Summary")
    summary_table.add_column("Setting", style="cyan")
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("Environment", summary.get("environment", "unknown"))
    summary_table.add_row("Debug Mode", "✅ Enabled" if summary.get("debug_mode") else "❌ Disabled")
    summary_table.add_row("Database Type", summary.get("database_type", "unknown"))
    summary_table.add_row("Cache", "✅ Enabled" if summary.get("cache_enabled") else "❌ Disabled")
    summary_table.add_row("External API", "✅ Configured" if summary.get("external_api_configured") else "❌ Not configured")
    summary_table.add_row("Encryption", "✅ Enabled" if summary.get("encryption_enabled") else "❌ Disabled")
    summary_table.add_row("Monitoring", "✅ Enabled" if summary.get("monitoring_enabled") else "❌ Disabled")
    summary_table.add_row("CORS Origins", str(summary.get("cors_origins_count", 0)))
    summary_table.add_row("Log Level", summary.get("log_level", "unknown"))
    
    # Server config
    server_config = summary.get("server_config", {})
    summary_table.add_row("Server", f"{server_config.get('host', 'unknown')}:{server_config.get('port', 'unknown')}")
    
    console.print(summary_table)
    console.print()


if __name__ == "__main__":
    app()
