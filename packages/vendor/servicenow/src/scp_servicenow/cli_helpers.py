"""Helper functions for CLI operations."""

from pathlib import Path
from typing import Optional

from rich.console import Console
from scp_sdk import Graph

from .config import CMDBConfig

console = Console()


def load_graph_file(graph_file: Path) -> Graph:
    """Load and validate graph file.

    Args:
        graph_file: Path to graph JSON file

    Returns:
        Loaded Graph object

    Raises:
        SystemExit: If file cannot be loaded
    """
    if not graph_file.exists():
        console.print(f"[red]Error: File not found: {graph_file}[/red]")
        raise SystemExit(1)

    try:
        return Graph.from_file(graph_file)
    except FileNotFoundError:
        console.print(f"[red]Error: File not found: {graph_file}[/red]")
        raise SystemExit(1)
    except ValueError as e:
        console.print(f"[red]Error: Invalid graph format: {e}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Error loading graph: {e}[/red]")
        raise SystemExit(1)


def load_config_file(config_file: Optional[Path] = None) -> CMDBConfig:
    """Load configuration file with fallback to defaults.

    Args:
        config_file: Optional path to config file

    Returns:
        Loaded or default CMDBConfig
    """
    try:
        return CMDBConfig.load(config_file)
    except Exception as e:
        console.print(
            f"[yellow]Warning: Could not load config, using defaults: {e}[/yellow]"
        )
        return CMDBConfig()
