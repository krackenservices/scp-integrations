"""CLI for SCP Constructor."""

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from . import __version__
from .parser import load_scp, SCPParseError
from .scanner.local import scan_directory
from .scanner.github import scan_github_org
from .graph import Neo4jGraph
from .export import export_json, export_mermaid

app = typer.Typer(
    name="scp",
    help="SCP Constructor - Build architecture graphs from scp.yaml files",
    no_args_is_help=True,
)
console = Console()


@app.command()
def scan(
    path: Path = typer.Argument(..., help="Directory to scan for scp.yaml files"),
    neo4j_uri: Optional[str] = typer.Option(None, "--neo4j-uri", envvar="NEO4J_URI", help="Neo4j URI"),
    neo4j_user: Optional[str] = typer.Option(None, "--neo4j-user", envvar="NEO4J_USER", help="Neo4j username"),
    neo4j_password: Optional[str] = typer.Option(None, "--neo4j-password", envvar="NEO4J_PASSWORD", help="Neo4j password"),
    export_format: Optional[str] = typer.Option(None, "--export", "-e", help="Export format: json, mermaid"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file (stdout if not specified)"),
):
    """Scan a local directory for SCP files and build the architecture graph."""
    
    console.print(f"[bold blue]Scanning[/] {path}")
    
    # Find SCP files
    try:
        scp_files = scan_directory(path)
    except (FileNotFoundError, NotADirectoryError) as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(1)
    
    if not scp_files:
        console.print("[yellow]No scp.yaml files found[/]")
        raise typer.Exit(0)
    
    console.print(f"Found [green]{len(scp_files)}[/] SCP files\n")
    
    # Parse all files
    manifests = []
    errors = []
    
    for scp_file in scp_files:
        try:
            manifest = load_scp(scp_file)
            manifests.append((manifest, str(scp_file)))
            console.print(f"  ✓ [green]{manifest.system.name}[/] ({manifest.system.urn})")
        except SCPParseError as e:
            errors.append(e)
            console.print(f"  ✗ [red]{scp_file}[/]: {e}")
    
    if errors:
        console.print(f"\n[yellow]Warning:[/] {len(errors)} files failed to parse")
    
    # Sync to Neo4j if configured
    if neo4j_uri and neo4j_user and neo4j_password:
        console.print(f"\n[bold blue]Syncing to Neo4j[/] {neo4j_uri}")
        
        try:
            with Neo4jGraph(neo4j_uri, neo4j_user, neo4j_password) as graph:
                graph.setup_constraints()
                stats = graph.sync_manifests(manifests)
                
                console.print(Panel(
                    f"Systems: {stats.systems_created} created, {stats.systems_updated} updated\n"
                    f"Capabilities: {stats.capabilities_created}\n"
                    f"Dependencies: {stats.dependencies_created}",
                    title="Graph Stats",
                    border_style="green",
                ))
        except Exception as e:
            console.print(f"[red]Neo4j Error:[/] {e}")
            raise typer.Exit(1)
    
    # Export if requested
    if export_format:
        manifest_list = [m for m, _ in manifests]
        
        if export_format == "json":
            data = export_json(manifest_list)
            content = json.dumps(data, indent=2)
        elif export_format == "mermaid":
            content = export_mermaid(manifest_list)
        else:
            console.print(f"[red]Unknown export format:[/] {export_format}")
            raise typer.Exit(1)
        
        if output:
            output.write_text(content)
            console.print(f"\n[green]Exported to[/] {output}")
        else:
            console.print()
            if export_format == "mermaid":
                console.print(Syntax(content, "text", theme="monokai"))
            else:
                console.print(Syntax(content, "json", theme="monokai"))


@app.command("scan-github")
def scan_github(
    org: str = typer.Argument(..., help="GitHub organization to scan"),
    token: Optional[str] = typer.Option(None, "--token", envvar="GITHUB_TOKEN", help="GitHub personal access token"),
    neo4j_uri: Optional[str] = typer.Option(None, "--neo4j-uri", envvar="NEO4J_URI", help="Neo4j URI"),
    neo4j_user: Optional[str] = typer.Option(None, "--neo4j-user", envvar="NEO4J_USER", help="Neo4j username"),
    neo4j_password: Optional[str] = typer.Option(None, "--neo4j-password", envvar="NEO4J_PASSWORD", help="Neo4j password"),
    export_format: Optional[str] = typer.Option(None, "--export", "-e", help="Export format: json, mermaid"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Scan a GitHub organization for SCP files."""
    
    if not token:
        console.print("[red]Error:[/] GitHub token required (--token or GITHUB_TOKEN env var)")
        raise typer.Exit(1)
    
    console.print(f"[bold blue]Scanning GitHub org[/] {org}")
    
    try:
        scp_files = scan_github_org(org, token)
    except Exception as e:
        console.print(f"[red]GitHub API Error:[/] {e}")
        raise typer.Exit(1)
    
    if not scp_files:
        console.print("[yellow]No scp.yaml files found[/]")
        raise typer.Exit(0)
    
    console.print(f"Found [green]{len(scp_files)}[/] SCP files\n")
    
    for scp_file in scp_files:
        console.print(f"  ✓ [green]{scp_file.manifest.system.name}[/] ({scp_file.repo})")
    
    manifests = [(f.manifest, f.repo) for f in scp_files]
    
    # Sync to Neo4j if configured
    if neo4j_uri and neo4j_user and neo4j_password:
        console.print(f"\n[bold blue]Syncing to Neo4j[/] {neo4j_uri}")
        
        try:
            with Neo4jGraph(neo4j_uri, neo4j_user, neo4j_password) as graph:
                graph.setup_constraints()
                stats = graph.sync_manifests(manifests)
                
                console.print(Panel(
                    f"Systems: {stats.systems_created} created, {stats.systems_updated} updated\n"
                    f"Capabilities: {stats.capabilities_created}\n"
                    f"Dependencies: {stats.dependencies_created}",
                    title="Graph Stats",
                    border_style="green",
                ))
        except Exception as e:
            console.print(f"[red]Neo4j Error:[/] {e}")
            raise typer.Exit(1)
    
    # Export if requested
    if export_format:
        manifest_list = [m for m, _ in manifests]
        
        if export_format == "json":
            data = export_json(manifest_list)
            content = json.dumps(data, indent=2)
        elif export_format == "mermaid":
            content = export_mermaid(manifest_list)
        else:
            console.print(f"[red]Unknown export format:[/] {export_format}")
            raise typer.Exit(1)
        
        if output:
            output.write_text(content)
            console.print(f"\n[green]Exported to[/] {output}")
        else:
            console.print()
            if export_format == "mermaid":
                console.print(Syntax(content, "text", theme="monokai"))
            else:
                console.print(Syntax(content, "json", theme="monokai"))


@app.command()
def validate(
    path: Path = typer.Argument(..., help="Path to scp.yaml file or directory"),
):
    """Validate SCP files without syncing to a graph."""
    
    if path.is_file():
        files = [path]
    else:
        files = scan_directory(path)
    
    if not files:
        console.print("[yellow]No SCP files found[/]")
        raise typer.Exit(0)
    
    errors = 0
    
    for scp_file in files:
        try:
            manifest = load_scp(scp_file)
            console.print(f"✓ [green]{scp_file}[/]")
            console.print(f"  System: {manifest.system.name} ({manifest.system.urn})")
            
            if manifest.depends:
                console.print(f"  Dependencies: {len(manifest.depends)}")
            if manifest.provides:
                console.print(f"  Capabilities: {len(manifest.provides)}")
                
        except SCPParseError as e:
            errors += 1
            console.print(f"✗ [red]{scp_file}[/]")
            console.print(f"  Error: {e}")
            for err in e.errors[:5]:  # Show first 5 errors
                loc = ".".join(str(l) for l in err.get("loc", []))
                console.print(f"    - {loc}: {err.get('msg', 'Unknown error')}")
    
    if errors:
        console.print(f"\n[red]{errors} file(s) failed validation[/]")
        raise typer.Exit(1)
    else:
        console.print(f"\n[green]All {len(files)} file(s) valid[/]")


@app.command()
def version():
    """Show version information."""
    console.print(f"scp-constructor v{__version__}")


if __name__ == "__main__":
    app()
