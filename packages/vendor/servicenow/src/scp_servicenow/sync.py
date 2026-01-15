"""Sync orchestration for SCP to ServiceNow CMDB."""

from typing import Any

from scp_sdk import Graph
from rich.console import Console
from rich.table import Table

from .client import ServiceNowClient
from .mapper import map_node_to_ci
from .config import CMDBConfig


__all__ = ["sync_to_servicenow", "print_sync_results", "SyncResult"]


console = Console()


class SyncResult(dict):
    """Results from a sync operation."""

    created_cis: list[dict[str, Any]]
    updated_cis: list[dict[str, Any]]
    created_relationships: list[dict[str, Any]]
    failed: list[dict[str, Any]]

    def __init__(self):
        super().__init__()
        self.created_cis = []
        self.updated_cis = []
        self.created_relationships = []
        self.failed = []


def sync_to_servicenow(
    graph: Graph,
    client: ServiceNowClient,
    ci_class: str = "cmdb_ci_service_discovered",
    dry_run: bool = False,
    config: CMDBConfig | None = None,
) -> SyncResult:
    """Sync SCP graph to ServiceNow CMDB.

    Args:
        graph: SCP unified graph
        client: ServiceNow API client
        ci_class: CI class to create (default: cmdb_ci_service_discovered)
        dry_run: If True, validate but don't make changes
        config: Optional CMDBConfig for custom field mappings

    Returns:
        Sync results
    """
    result = SyncResult()

    system_nodes = list(graph.systems())

    console.print(
        f"\n[bold]Syncing {len(system_nodes)} systems to ServiceNow...[/bold]"
    )

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]\n")

    # Track correlation_id -> sys_id mapping for relationships
    ci_mapping: dict[str, str] = {}

    # Step 1: Upsert CIs
    with console.status("[bold green]Syncing CIs...") as status:
        for i, node in enumerate(system_nodes, 1):
            node_id = node.urn
            node_name = node.name or "Unknown"

            status.update(
                f"[bold green]Syncing CI {i}/{len(system_nodes)}: {node_name}"
            )

            try:
                ci_data = map_node_to_ci(node, config=config)

                # Resolve support email to user
                support_email = ci_data.pop("_support_email", None)
                if not dry_run and support_email:
                    user = client.get_user_by_email(support_email)
                    if user:
                        ci_data["owned_by"] = user["sys_id"]
                    else:
                        console.print(
                            f"  [yellow]Warning: User not found for email {support_email}[/yellow]"
                        )
                elif dry_run and support_email:
                    console.print(f"  [dim]Would look up user: {support_email}[/dim]")

                if dry_run:
                    console.print(f"  [dim]Would sync: {node_name} ({node_id})[/dim]")
                    ci_mapping[node_id] = "dry-run-sys-id"
                else:
                    # Upsert the CI
                    created_ci = client.upsert_ci(ci_class, node_id, ci_data)

                    # Track sys_id for relationships
                    sys_id = created_ci.get("sys_id")
                    if sys_id:
                        ci_mapping[node_id] = sys_id

                    # Check if it was a create or update based on response
                    # ServiceNow returns the CI record either way
                    result.created_cis.append(
                        {"urn": node_id, "name": node_name, "sys_id": sys_id}
                    )

            except Exception as e:
                console.print(f"  [red]Failed: {node_name} - {e}[/red]")
                result.failed.append(
                    {"urn": node_id, "name": node_name, "error": str(e)}
                )

    # Step 2: Sync relationships
    dependency_edges = list(graph.dependencies())

    if dependency_edges:
        console.print(
            f"\n[bold]Syncing {len(dependency_edges)} relationships...[/bold]"
        )

        with console.status("[bold green]Syncing relationships...") as status:
            for i, edge in enumerate(dependency_edges, 1):
                from_id = edge.from_urn
                to_id = edge.to_urn

                status.update(
                    f"[bold green]Syncing relationship {i}/{len(dependency_edges)}"
                )

                # Only sync if both CIs exist in our mapping
                if from_id not in ci_mapping or to_id not in ci_mapping:
                    console.print(
                        f"  [dim]Skipping relationship: {from_id} -> {to_id} (missing CI)[/dim]"
                    )
                    continue

                try:
                    if dry_run:
                        console.print(
                            f"  [dim]Would create: {from_id} -> {to_id}[/dim]"
                        )
                    else:
                        parent_sys_id = ci_mapping[from_id]
                        child_sys_id = ci_mapping[to_id]

                        rel = client.create_relationship(parent_sys_id, child_sys_id)

                        result.created_relationships.append(
                            {
                                "from": from_id,
                                "to": to_id,
                                "rel_sys_id": rel.get("sys_id"),
                            }
                        )

                except Exception as e:
                    console.print(
                        f"  [red]Failed relationship: {from_id} -> {to_id} - {e}[/red]"
                    )
                    result.failed.append(
                        {"from": from_id, "to": to_id, "error": str(e)}
                    )

    return result


def print_sync_results(result: SyncResult, dry_run: bool = False):
    """Print formatted sync results.

    Args:
        result: Sync results
        dry_run: Whether this was a dry run
    """
    console.print("\n[bold]Sync Results[/bold]")

    # Create summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Count", justify="right")

    table.add_row(
        "CIs Created/Updated" if not dry_run else "CIs (Dry Run)",
        str(len(result.created_cis)),
    )
    table.add_row(
        "Relationships Created" if not dry_run else "Relationships (Dry Run)",
        str(len(result.created_relationships)),
    )
    table.add_row(
        "Failed", str(len(result.failed)), style="red" if result.failed else None
    )

    console.print(table)

    # Show failures if any
    if result.failed:
        console.print("\n[bold red]Failures:[/bold red]")
        for failure in result.failed:
            console.print(f"  • {failure}")
