"""CLI for ServiceNow CMDB integration."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .client import ServiceNowAuth, ServiceNowClient
from .mapper import validate_mapping
from .sync import load_graph_json, sync_to_servicenow, print_sync_results


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
    ci_class: str = typer.Option(
        "cmdb_ci_service_discovered",
        "--ci-class",
        "-c",
        help="ServiceNow CI class to use",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Validate without making changes"
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
        graph_data = load_graph_json(graph_file)
    except Exception as e:
        console.print(f"[red]Error loading JSON: {e}[/red]")
        raise typer.Exit(1)

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
    console.print(f"[bold]CI Class:[/bold] {ci_class}")
    console.print(
        f"[bold]Systems:[/bold] {len([n for n in graph_data.get('nodes', []) if n.get('type') == 'System'])}"
    )
    console.print(
        f"[bold]Dependencies:[/bold] {len([e for e in graph_data.get('edges', []) if e.get('type') == 'DEPENDS_ON'])}"
    )

    # Create client
    client = ServiceNowClient(auth)

    # Sync
    try:
        result = sync_to_servicenow(graph_data, client, ci_class, dry_run)
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
        graph_data = load_graph_json(graph_file)
    except Exception as e:
        console.print(f"[red]Error loading JSON: {e}[/red]")
        raise typer.Exit(1)

    # Validate
    console.print(f"[bold]Validating {graph_file}...[/bold]\n")

    issues = validate_mapping(graph_data)

    if not issues:
        console.print("[green]✓ Validation passed - no issues found[/green]")
        return

    # Group by severity
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

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
