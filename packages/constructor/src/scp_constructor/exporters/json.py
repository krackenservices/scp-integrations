"""JSON export and import for architecture graph data."""

from typing import Any

from scp_sdk import (
    SCPManifest,
    export_graph_json,
    import_graph_json,
)


def export_json(manifests: list[SCPManifest]) -> dict[str, Any]:
    """Export manifests to a JSON-serializable graph structure.

    This is a wrapper around scp_sdk.export_graph_json() for backward compatibility.

    Args:
        manifests: List of SCP manifests

    Returns:
        Dictionary with nodes and edges lists
    """
    return export_graph_json(manifests)


def import_json(data: dict[str, Any]) -> list[SCPManifest]:
    """Import manifests from a previously exported JSON graph.

    This is a wrapper around scp_sdk.import_graph_json() for backward compatibility.

    Reconstructs SCPManifest objects from the JSON export format,
    allowing transformation to other formats without re-scanning.

    Args:
        data: Dictionary from export_json() output

    Returns:
        List of reconstructed SCP manifests
    """
    return import_graph_json(data)
