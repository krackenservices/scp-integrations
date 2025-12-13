"""Export functions for architecture graph data."""

from typing import Any

from .models import SCPManifest


def export_json(manifests: list[SCPManifest]) -> dict[str, Any]:
    """Export manifests to a JSON-serializable graph structure.
    
    Args:
        manifests: List of SCP manifests
        
    Returns:
        Dictionary with nodes and edges lists
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    seen_urns: set[str] = set()
    
    for manifest in manifests:
        urn = manifest.system.urn
        
        # Add system node
        if urn not in seen_urns:
            nodes.append({
                "id": urn,
                "type": "System",
                "name": manifest.system.name,
                "tier": manifest.system.classification.tier if manifest.system.classification else None,
                "domain": manifest.system.classification.domain if manifest.system.classification else None,
                "team": manifest.ownership.team if manifest.ownership else None,
            })
            seen_urns.add(urn)
        
        # Add dependency nodes and edges
        if manifest.depends:
            for dep in manifest.depends:
                # Stub node for dependency target if not seen
                if dep.system not in seen_urns:
                    nodes.append({
                        "id": dep.system,
                        "type": "System",
                        "name": dep.system.split(":")[-1],  # Extract name from URN
                        "stub": True,
                    })
                    seen_urns.add(dep.system)
                
                edges.append({
                    "from": urn,
                    "to": dep.system,
                    "type": "DEPENDS_ON",
                    "capability": dep.capability,
                    "criticality": dep.criticality,
                    "failure_mode": dep.failure_mode,
                })
        
        # Add capability nodes and PROVIDES edges
        if manifest.provides:
            for cap in manifest.provides:
                cap_id = f"{urn}:{cap.capability}"
                nodes.append({
                    "id": cap_id,
                    "type": "Capability",
                    "name": cap.capability,
                    "capability_type": cap.type,
                })
                edges.append({
                    "from": urn,
                    "to": cap_id,
                    "type": "PROVIDES",
                })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "systems_count": len([n for n in nodes if n["type"] == "System"]),
            "capabilities_count": len([n for n in nodes if n["type"] == "Capability"]),
            "dependencies_count": len([e for e in edges if e["type"] == "DEPENDS_ON"]),
        },
    }


def export_mermaid(manifests: list[SCPManifest], direction: str = "LR") -> str:
    """Export manifests to a Mermaid flowchart diagram.
    
    Args:
        manifests: List of SCP manifests  
        direction: Graph direction (TB, BT, LR, RL)
        
    Returns:
        Mermaid diagram string
    """
    lines = [f"flowchart {direction}"]
    
    # Track systems and their properties
    systems: dict[str, dict] = {}
    dependencies: list[tuple[str, str, str | None]] = []
    
    for manifest in manifests:
        urn = manifest.system.urn
        short_id = _urn_to_id(urn)
        
        systems[urn] = {
            "id": short_id,
            "name": manifest.system.name,
            "tier": manifest.system.classification.tier if manifest.system.classification else None,
        }
        
        if manifest.depends:
            for dep in manifest.depends:
                dependencies.append((urn, dep.system, dep.capability))
                
                # Add stub for unknown dependencies
                if dep.system not in systems:
                    dep_id = _urn_to_id(dep.system)
                    dep_name = dep.system.split(":")[-1].replace("-", " ").title()
                    systems[dep.system] = {
                        "id": dep_id,
                        "name": dep_name,
                        "tier": None,
                    }
    
    # Output system nodes with styling
    lines.append("")
    lines.append("    %% Systems")
    for urn, info in systems.items():
        tier = info["tier"]
        name = info["name"]
        node_id = info["id"]
        
        if tier == 1:
            # Critical systems - double border
            lines.append(f'    {node_id}[["🔴 {name}"]]')
        elif tier == 2:
            lines.append(f'    {node_id}["🟡 {name}"]')
        else:
            lines.append(f'    {node_id}["{name}"]')
    
    # Output dependency edges
    lines.append("")
    lines.append("    %% Dependencies")
    for from_urn, to_urn, capability in dependencies:
        from_id = systems[from_urn]["id"]
        to_id = systems[to_urn]["id"]
        
        if capability:
            lines.append(f"    {from_id} -->|{capability}| {to_id}")
        else:
            lines.append(f"    {from_id} --> {to_id}")
    
    # Add styling
    lines.append("")
    lines.append("    %% Styling")
    
    tier1_ids = [info["id"] for info in systems.values() if info["tier"] == 1]
    if tier1_ids:
        lines.append(f"    classDef critical fill:#ff6b6b,stroke:#333,stroke-width:2px")
        lines.append(f"    class {','.join(tier1_ids)} critical")
    
    return "\n".join(lines)


def _urn_to_id(urn: str) -> str:
    """Convert a URN to a valid Mermaid node ID."""
    # Extract the service name and sanitize
    parts = urn.split(":")
    name = parts[-1] if parts else urn
    # Replace hyphens and make alphanumeric
    return name.replace("-", "_")
