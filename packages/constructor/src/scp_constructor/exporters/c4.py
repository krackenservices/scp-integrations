"""C4 PlantUML export for architecture diagrams.

Generates C4 Container diagrams using the C4-PlantUML library syntax.
See: https://github.com/plantuml-stdlib/C4-PlantUML
"""

from scp_sdk import SCPManifest


def export_c4(manifests: list[SCPManifest], title: str = "System Architecture") -> str:
    """Export manifests to a C4 PlantUML Container diagram.

    Generates a C4 Container-level diagram with:
    - Internal systems as Container elements
    - External systems (tier 4-5 or unscanned dependencies) as System_Ext
    - Dependencies as Rel relationships with capability labels

    Args:
        manifests: List of SCP manifests
        title: Diagram title

    Returns:
        PlantUML C4 diagram string (.puml format)
    """
    lines = [
        "@startuml",
        "!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml",
        "",
        f"title {title}",
        "",
    ]

    # Track all systems and their metadata
    systems: dict[str, dict] = {}
    # Track systems that are scanned (have full manifests)
    scanned_urns: set[str] = set()
    # Track dependencies
    dependencies: list[tuple[str, str, str, str]] = []  # (from, to, label, type)

    # First pass: collect all system info from manifests
    for manifest in manifests:
        urn = manifest.system.urn
        scanned_urns.add(urn)

        tier = (
            manifest.system.classification.tier
            if manifest.system.classification
            else None
        )
        domain = (
            manifest.system.classification.domain
            if manifest.system.classification
            else None
        )

        systems[urn] = {
            "name": manifest.system.name,
            "description": manifest.system.description or "",
            "tier": tier,
            "domain": domain,
            "is_external": tier is not None and tier >= 4,
        }

        # Collect dependencies
        if manifest.depends:
            for dep in manifest.depends:
                label = dep.capability or "uses"
                dep_type = dep.type or ""
                dependencies.append((urn, dep.system, label, dep_type))

                # Add stub for unknown dependencies
                if dep.system not in systems:
                    dep_name = dep.system.split(":")[-1].replace("-", " ").title()
                    systems[dep.system] = {
                        "name": dep_name,
                        "description": "External system",
                        "tier": None,
                        "domain": None,
                        "is_external": True,
                    }

    # Group systems by domain for boundaries
    domains: dict[str, list[str]] = {}
    no_domain: list[str] = []

    for urn, info in systems.items():
        if info["is_external"]:
            continue  # External systems go outside boundaries
        domain = info.get("domain")
        if domain:
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(urn)
        else:
            no_domain.append(urn)

    # Output external systems first
    external_urns = [urn for urn, info in systems.items() if info["is_external"]]
    if external_urns:
        lines.append("' External Systems")
        for urn in sorted(external_urns):
            info = systems[urn]
            alias = _urn_to_alias(urn)
            lines.append(f'System_Ext({alias}, "{info["name"]}", "{info["description"]}")')
        lines.append("")

    # Output internal systems grouped by domain
    if domains:
        for domain, urns in sorted(domains.items()):
            boundary_id = _sanitize_alias(domain)
            lines.append(f'System_Boundary({boundary_id}, "{domain.title()}") {{')
            for urn in sorted(urns):
                info = systems[urn]
                alias = _urn_to_alias(urn)
                tier_tag = f" [Tier {info['tier']}]" if info["tier"] else ""
                desc = info["description"] or f"Internal service{tier_tag}"
                lines.append(f'    Container({alias}, "{info["name"]}", "", "{desc}")')
            lines.append("}")
            lines.append("")

    # Output systems without domain
    if no_domain:
        lines.append("' Internal Systems (no domain)")
        for urn in sorted(no_domain):
            info = systems[urn]
            alias = _urn_to_alias(urn)
            tier_tag = f" [Tier {info['tier']}]" if info["tier"] else ""
            desc = info["description"] or f"Internal service{tier_tag}"
            lines.append(f'Container({alias}, "{info["name"]}", "", "{desc}")')
        lines.append("")

    # Output relationships
    if dependencies:
        lines.append("' Relationships")
        for from_urn, to_urn, label, dep_type in dependencies:
            from_alias = _urn_to_alias(from_urn)
            to_alias = _urn_to_alias(to_urn)
            tech = f", {dep_type}" if dep_type else ""
            lines.append(f'Rel({from_alias}, {to_alias}, "{label}"{tech})')
        lines.append("")

    lines.append("@enduml")
    return "\n".join(lines)


def _urn_to_alias(urn: str) -> str:
    """Convert a URN to a valid PlantUML alias."""
    # Extract the service name and sanitize
    parts = urn.split(":")
    name = parts[-1] if parts else urn
    return name.replace("-", "_")


def _sanitize_alias(text: str) -> str:
    """Convert text to a valid PlantUML alias."""
    return text.replace("-", "_").replace(" ", "_").replace(".", "_").lower()
