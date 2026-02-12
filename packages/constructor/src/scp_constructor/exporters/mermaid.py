"""Mermaid diagram export for architecture graph data."""

from scp_sdk import SCPManifest


def export_mermaid(manifests: list[SCPManifest], direction: str = "LR") -> str:
    """Export manifests to a Mermaid flowchart diagram with capability grouping.

    Args:
        manifests: List of SCP manifests
        direction: Graph direction (TB, BT, LR, RL)

    Returns:
        Mermaid diagram string
    """
    lines = [f"flowchart {direction}"]

    # Track systems and their properties
    systems: dict[str, dict] = {}

    # Track dependencies grouped by consumer and capability
    # Structure: {consumer_urn: {capability_name: [(target_urn, type), ...]}}
    consumer_deps: dict[str, dict[str, list[tuple[str, str]]]] = {}

    for manifest in manifests:
        urn = manifest.system.urn
        short_id = _urn_to_id(urn)

        systems[urn] = {
            "id": short_id,
            "name": manifest.system.name,
            "tier": manifest.system.classification.tier
            if manifest.system.classification
            else None,
        }

        if manifest.depends:
            if urn not in consumer_deps:
                consumer_deps[urn] = {}

            for dep in manifest.depends:
                capability = dep.capability or "unknown"
                dep_type = dep.type

                if capability not in consumer_deps[urn]:
                    consumer_deps[urn][capability] = []

                consumer_deps[urn][capability].append((dep.system, dep_type))

                # Add stub for unknown dependencies
                if dep.system not in systems:
                    dep_id = _urn_to_id(dep.system)
                    dep_name = dep.system.split(":")[-1].replace("-", " ").title()
                    systems[dep.system] = {
                        "id": dep_id,
                        "name": dep_name,
                        "tier": None,
                    }

    # Determine which capabilities should be grouped
    # A capability gets grouped if a consumer depends on 2+ systems for it
    capability_groups: dict[
        str, list[dict]
    ] = {}  # {group_id: {consumer, capability, targets: [(urn, type)], ...}}
    direct_edges: list[tuple[str, str, str]] = []  # [(from_urn, to_urn, capability)]

    group_counter = 1

    for consumer_urn, capabilities in consumer_deps.items():
        for capability_name, targets in capabilities.items():
            if len(targets) >= 2:
                # Create a group
                group_id = f"{_sanitize_id(capability_name)}_{group_counter}"
                group_counter += 1

                capability_groups[group_id] = {
                    "consumer": consumer_urn,
                    "capability": capability_name,
                    "targets": targets,
                }
            else:
                # Direct edge (only 1 provider)
                target_urn, _ = targets[0]
                direct_edges.append((consumer_urn, target_urn, capability_name))

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

    # Output capability groups as subgraphs
    if capability_groups:
        lines.append("")
        lines.append("    %% Capability Groups")

        for group_id, group_info in capability_groups.items():
            consumer_id = systems[group_info["consumer"]]["id"]
            capability_name = group_info["capability"]
            targets = group_info["targets"]

            # Draw edge from consumer to group
            lines.append(f"    {consumer_id} --> {group_id}")
            lines.append("")

            # Check if we have mixed types
            types_in_group = set(dep_type for _, dep_type in targets)

            if len(types_in_group) > 1:
                # Mixed types - use nested subgraphs
                lines.append(f'    subgraph {group_id}["{capability_name}"]')

                # Group targets by type
                targets_by_type: dict[str, list[str]] = {}
                for target_urn, dep_type in targets:
                    if dep_type not in targets_by_type:
                        targets_by_type[dep_type] = []
                    targets_by_type[dep_type].append(target_urn)

                # Create nested subgraph for each type
                type_counter = 1
                for dep_type, type_targets in sorted(targets_by_type.items()):
                    type_subgraph_id = f"{dep_type}_{type_counter}"
                    type_counter += 1
                    lines.append(f'        subgraph {type_subgraph_id}["{dep_type}"]')
                    for target_urn in type_targets:
                        target_id = systems[target_urn]["id"]
                        lines.append(f"            {target_id}")
                    lines.append("        end")

                lines.append("    end")
            else:
                # Single type - simple subgraph
                lines.append(f'    subgraph {group_id}["{capability_name}"]')
                for target_urn, _ in targets:
                    target_id = systems[target_urn]["id"]
                    lines.append(f"        {target_id}")
                lines.append("    end")

            lines.append("")

    # Output direct dependency edges
    if direct_edges:
        lines.append("")
        lines.append("    %% Direct Dependencies")
        for from_urn, to_urn, capability in direct_edges:
            from_id = systems[from_urn]["id"]
            to_id = systems[to_urn]["id"]
            lines.append(f"    {from_id} -->|{capability}| {to_id}")

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


def _sanitize_id(text: str) -> str:
    """Convert text to a valid Mermaid ID (alphanumeric + underscore)."""
    # Replace hyphens and spaces with underscores, remove other special chars
    return text.replace("-", "_").replace(" ", "_").replace(".", "_").lower()
