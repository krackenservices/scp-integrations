"""CLI for ServiceNow CMDB integration."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from scp_sdk import Graph

from .client import ServiceNowAuth, ServiceNowClient
from .mapper import validate_mapping, IssueSeverity
from .sync import sync_to_servicenow, print_sync_results
from .config import CMDBConfig


app = typer.Typer(help="ServiceNow CMDB integration for SCP unified model")
cmdb_app = typer.Typer(help="CMDB operations")
app.add_typer(cmdb_app, name="cmdb")
console = Console()


def get_auth_from_env() -> ServiceNowAuth:
    """Get ServiceNow authentication from environment variables.

    Returns:
        ServiceNowAuth configuration

    Raises:
        typer.Exit: If required env vars are missing
    """
    instance = os.getenv("SERVICENOW_INSTANCE")

    if not instance:
        console.print(
            "[red]Error: SERVICENOW_INSTANCE environment variable not set[/red]"
        )
        raise typer.Exit(1)

    return ServiceNowAuth(
        instance_url=instance,
        username=os.getenv("SERVICENOW_USERNAME"),
        password=os.getenv("SERVICENOW_PASSWORD"),
        token=os.getenv("SERVICENOW_TOKEN"),
        client_id=os.getenv("SERVICENOW_CLIENT_ID"),
        client_secret=os.getenv("SERVICENOW_CLIENT_SECRET"),
    )


@cmdb_app.command()
def sync(
    graph_file: Path = typer.Argument(..., help="Path to SCP unified JSON graph"),
    instance: Optional[str] = typer.Option(
        None, "--instance", "-i", help="ServiceNow instance URL (overrides env var)"
    ),
    servicenow_ci_class: str = typer.Option(
        "cmdb_ci_service_discovered",
        "--ci-class",
        "-c",
        help="ServiceNow CI class to use",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Validate without making changes"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", help="Path to cmdb.yaml config file"
    ),
):
    """Sync SCP graph to ServiceNow CMDB.

    Example:
        scp-servicenow sync graph.json --instance https://dev12345.service-now.com
    """
    # Load graph
    if not graph_file.exists():
        console.print(f"[red]Error: File not found: {graph_file}[/red]")
        raise typer.Exit(1)

    try:
        graph = Graph.from_file(graph_file)
    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {graph_file}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error: Invalid graph format: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error loading graph: {e}[/red]")
        raise typer.Exit(1)

    # Load configuration
    try:
        config = CMDBConfig.load(config_file)
    except Exception as e:
        console.print(
            f"[yellow]Warning: Could not load config, using defaults: {e}[/yellow]"
        )
        config = CMDBConfig()

    # Get authentication
    auth = get_auth_from_env()

    # Override instance URL if provided
    if instance:
        auth.instance_url = instance

    # Validate authentication
    if not auth.get_auth() and not auth.token:
        console.print(
            "[red]Error: No authentication provided. Set SERVICENOW_USERNAME/PASSWORD or SERVICENOW_TOKEN[/red]"
        )
        raise typer.Exit(1)

    console.print(f"[bold]ServiceNow Instance:[/bold] {auth.instance_url}")
    console.print(f"[bold]CI Class:[/bold] {servicenow_ci_class}")
    console.print(f"[bold]Systems:[/bold] {len(graph)}")
    console.print(f"[bold]Dependencies:[/bold] {len(list(graph.dependencies()))}")

    # Create client
    client = ServiceNowClient(auth)

    # Sync
    try:
        result = sync_to_servicenow(
            graph, client, servicenow_ci_class, dry_run, config=config
        )
        print_sync_results(result, dry_run)

        if result.failed:
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Sync cancelled[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[red]Sync failed: {e}[/red]")
        raise typer.Exit(1)


@cmdb_app.command()
def init(
    output: Path = typer.Option(
        Path("cmdb.yaml"), "--output", "-o", help="Output path for config file"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing file"),
):
    """Generate a cmdb.yaml configuration file with defaults.

    This creates a configuration template that you can customize for your
    ServiceNow instance. The integration works with sensible defaults, so
    this file is OPTIONAL and only needed to override default behavior.

    Example:
        scp-servicenow cmdb init
        scp-servicenow cmdb init --output my-config.yaml
    """
    if output.exists() and not force:
        console.print(
            f"[yellow]Warning: {output} already exists. Use --force to overwrite.[/yellow]"
        )
        raise typer.Exit(1)

    # Generate default config
    config = CMDBConfig()

    # Add helpful comments
    yaml_content = f"""# ServiceNow CMDB Integration Configuration
#
# This file is OPTIONAL. The integration works with sensible defaults.
# Use this to customize field mappings for your ServiceNow instance.
#
# Default behavior (no config file):
#   - Maps tier to business_criticality
#   - Stores team, domain, contacts, escalation in comments field
#   - Resolves email contacts to owned_by field
#
# To use custom ServiceNow fields:
#   - Uncomment the u_* fields below
#   - Ensure those fields exist in your ServiceNow instance

{config.to_yaml()}

# Example: Using custom fields (requires creating them in ServiceNow)
# field_mappings:
#   name: name
#   business_criticality: tier
#   u_business_domain: domain        # Custom field for domain
#   u_support_team: team              # Custom field for team
#   comments:
#     - contacts
#     - escalation
"""

    try:
        output.write_text(yaml_content)
        console.print(f"[green]✓ Created configuration template: {output}[/green]")
        console.print(
            "\n[dim]Edit this file to customize field mappings for your instance.[/dim]"
        )
    except Exception as e:
        console.print(f"[red]Error writing config file: {e}[/red]")
        raise typer.Exit(1)


@cmdb_app.command()
def validate(
    graph_file: Path = typer.Argument(..., help="Path to SCP unified JSON graph"),
):
    """Validate SCP graph can be mapped to ServiceNow.

    Example:
        scp-servicenow validate graph.json
    """
    # Load graph
    if not graph_file.exists():
        console.print(f"[red]Error: File not found: {graph_file}[/red]")
        raise typer.Exit(1)

    try:
        graph = Graph.from_file(graph_file)
    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {graph_file}[/red]")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error: Invalid graph format: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error loading graph: {e}[/red]")
        raise typer.Exit(1)

    # Validate
    console.print(f"[bold]Validating {graph_file}...[/bold]\n")

    issues = validate_mapping(graph)

    if not issues:
        console.print("[green]✓ Validation passed - no issues found[/green]")
        return

    # Group by severity
    errors = [i for i in issues if i.get("severity") == IssueSeverity.ERROR]
    warnings = [i for i in issues if i.get("severity") == IssueSeverity.WARNING]

    if errors:
        console.print(f"[red]✗ {len(errors)} error(s) found:[/red]")
        for error in errors:
            console.print(f"  • {error.get('message')}")

    if warnings:
        console.print(f"\n[yellow]⚠ {len(warnings)} warning(s) found:[/yellow]")
        for warning in warnings:
            console.print(f"  • {warning.get('message')}")

    if errors:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
