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
    system_nodes: dict[str, dict] = {}  # Track by URN for stub replacement
    
    for manifest in manifests:
        urn = manifest.system.urn
        
        # Add or update system node (replaces stub if exists)
        system_nodes[urn] = {
            "id": urn,
            "type": "System",
            "name": manifest.system.name,
            "tier": manifest.system.classification.tier if manifest.system.classification else None,
            "domain": manifest.system.classification.domain if manifest.system.classification else None,
            "team": manifest.ownership.team if manifest.ownership else None,
        }
        
        # Add dependency edges (create stub only if not already known)
        if manifest.depends:
            for dep in manifest.depends:
                # Create stub node for dependency target if not seen
                if dep.system not in system_nodes:
                    system_nodes[dep.system] = {
                        "id": dep.system,
                        "type": "System",
                        "name": dep.system.split(":")[-1],  # Extract name from URN
                        "stub": True,
                    }
                
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
                cap_node: dict[str, Any] = {
                    "id": cap_id,
                    "type": "Capability",
                    "name": cap.capability,
                    "capability_type": cap.type,
                }
                # Include security extension if present
                if cap.x_security:
                    cap_node["x_security"] = {
                        "actuator_profile": cap.x_security.actuator_profile,
                        "actions": cap.x_security.actions,
                        "targets": cap.x_security.targets,
                    }
                nodes.append(cap_node)
                edges.append({
                    "from": urn,
                    "to": cap_id,
                    "type": "PROVIDES",
                })
    
    # Combine system nodes (from dict) with capability nodes (from list)
    all_nodes = list(system_nodes.values()) + nodes
    
    return {
        "nodes": all_nodes,
        "edges": edges,
        "meta": {
            "systems_count": len(system_nodes),
            "capabilities_count": len(nodes),
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
        lines.append("    classDef critical fill:#ff6b6b,stroke:#333,stroke-width:2px")
        lines.append(f"    class {','.join(tier1_ids)} critical")
    
    return "\n".join(lines)


def _urn_to_id(urn: str) -> str:
    """Convert a URN to a valid Mermaid node ID."""
    # Extract the service name and sanitize
    parts = urn.split(":")
    name = parts[-1] if parts else urn
    # Replace hyphens and make alphanumeric
    return name.replace("-", "_")


def export_openc2(manifests: list[SCPManifest]) -> dict[str, Any]:
    """Export OpenC2 actuator profile for SOAR discovery.
    
    Extracts security capabilities from manifests and formats them
    as an OpenC2-compatible actuator inventory.
    
    Args:
        manifests: List of SCP manifests
        
    Returns:
        Dictionary with actuators list for SOAR consumption
    """
    actuators: list[dict] = []
    
    for manifest in manifests:
        if not manifest.provides:
            continue
            
        for cap in manifest.provides:
            if not cap.x_security:
                continue
                
            actuators.append({
                "actuator_id": manifest.system.urn,
                "name": manifest.system.name,
                "capability": cap.capability,
                "profile": cap.x_security.actuator_profile,
                "actions": cap.x_security.actions,
                "targets": cap.x_security.targets,
                "api": {
                    "type": cap.type,
                    "contract": cap.contract.ref if cap.contract else None,
                },
                "metadata": {
                    "team": manifest.ownership.team if manifest.ownership else None,
                    "tier": manifest.system.classification.tier if manifest.system.classification else None,
                    "domain": manifest.system.classification.domain if manifest.system.classification else None,
                },
            })
    
    return {
        "openc2_version": "1.0",
        "actuators": actuators,
        "count": len(actuators),
    }


def import_json(data: dict[str, Any]) -> list[SCPManifest]:
    """Import manifests from a previously exported JSON graph.
    
    Reconstructs SCPManifest objects from the JSON export format,
    allowing transformation to other formats without re-scanning.
    
    Args:
        data: Dictionary from export_json() output
        
    Returns:
        List of reconstructed SCP manifests
    """
    from .models import (
        System, Classification, Ownership, Capability, 
        Dependency, SecurityExtension
    )
    
    manifests: list[SCPManifest] = []
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    
    # Build lookup maps
    system_nodes = {n["id"]: n for n in nodes if n.get("type") == "System" and not n.get("stub")}
    capability_nodes = {n["id"]: n for n in nodes if n.get("type") == "Capability"}
    
    # Group edges by source system
    provides_by_system: dict[str, list[dict]] = {}
    depends_by_system: dict[str, list[dict]] = {}
    
    for edge in edges:
        if edge["type"] == "PROVIDES":
            provides_by_system.setdefault(edge["from"], []).append(edge)
        elif edge["type"] == "DEPENDS_ON":
            depends_by_system.setdefault(edge["from"], []).append(edge)
    
    # Reconstruct manifests
    for urn, node in system_nodes.items():
        # Build classification
        classification = None
        if node.get("tier") or node.get("domain"):
            classification = Classification(
                tier=node.get("tier"),
                domain=node.get("domain"),
            )
        
        # Build ownership
        ownership = None
        if node.get("team"):
            ownership = Ownership(team=node["team"])
        
        # Build capabilities
        provides = []
        for edge in provides_by_system.get(urn, []):
            cap_node = capability_nodes.get(edge["to"])
            if cap_node:
                # Check for security extension in capability node
                x_security = None
                if cap_node.get("x_security"):
                    sec = cap_node["x_security"]
                    x_security = SecurityExtension(
                        actuator_profile=sec.get("actuator_profile"),
                        actions=sec.get("actions", []),
                        targets=sec.get("targets", []),
                    )
                
                provides.append(Capability(
                    capability=cap_node["name"],
                    type=cap_node.get("capability_type", "rest"),
                    x_security=x_security,
                ))
        
        # Build dependencies
        depends = []
        for edge in depends_by_system.get(urn, []):
            depends.append(Dependency(
                system=edge["to"],
                capability=edge.get("capability"),
                type="rest",  # Default, as type isn't stored in edge
                criticality=edge.get("criticality", "required"),
                failure_mode=edge.get("failure_mode"),
            ))
        
        manifest = SCPManifest(
            scp="0.1.0",
            system=System(
                urn=urn,
                name=node["name"],
                classification=classification,
            ),
            ownership=ownership,
            provides=provides if provides else None,
            depends=depends if depends else None,
        )
        manifests.append(manifest)
    
    return manifests

