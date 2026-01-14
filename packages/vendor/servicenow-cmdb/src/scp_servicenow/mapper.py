"""Transform SCP unified JSON to ServiceNow CMDB model."""

from typing import Any


TIER_TO_CRITICALITY = {
    1: "1 - Critical",
    2: "2 - High",
    3: "3 - Medium",
    4: "4 - Low",
    5: "5 - Planning",
}


def map_node_to_ci(node: dict[str, Any]) -> dict[str, Any]:
    """Map SCP node to ServiceNow CI payload.

    Args:
        node: SCP graph node

    Returns:
        ServiceNow CI data payload
    """
    ci_data: dict[str, Any] = {
        "name": node.get("name", ""),
    }

    # Map tier to business_criticality
    tier = node.get("tier")
    if tier is not None:
        ci_data["business_criticality"] = TIER_TO_CRITICALITY.get(tier, "3 - Medium")

    # Map domain to custom field (u_business_domain)
    domain = node.get("domain")
    if domain:
        ci_data["u_business_domain"] = domain

    # Map team to support_group
    # Note: This requires the team name to match an existing assignment group
    # In production, you might want to lookup the sys_id of the group
    team = node.get("team")
    if team:
        ci_data["u_support_team"] = team  # Using custom field for simplicity

    # Map contacts (email) to owned_by/managed_by
    # We return the email address here, and sync.py will resolve it to a sys_user
    contacts = node.get("contacts", [])
    for contact in contacts:
        if contact.get("type") == "email":
            # Store temporarily as _support_email to be resolved by sync
            ci_data["_support_email"] = contact.get("ref")
            break

    return ci_data


def validate_mapping(graph_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate SCP JSON can be mapped to ServiceNow.

    Args:
        graph_data: SCP unified JSON graph

    Returns:
        List of validation warnings/errors
    """
    issues: list[dict[str, Any]] = []

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    # Check for nodes without names
    for node in nodes:
        if node.get("type") == "System" and not node.get("name"):
            issues.append(
                {
                    "severity": "error",
                    "node_id": node.get("id"),
                    "message": "System node missing 'name' field",
                }
            )

        # Warn about invalid tier values
        tier = node.get("tier")
        if tier is not None and tier not in TIER_TO_CRITICALITY:
            issues.append(
                {
                    "severity": "warning",
                    "node_id": node.get("id"),
                    "message": f"Invalid tier value {tier}, expected 1-5",
                }
            )

    # Check for dependency edges without valid targets
    system_ids = {n["id"] for n in nodes if n.get("type") == "System"}

    for edge in edges:
        if edge.get("type") == "DEPENDS_ON":
            if edge.get("from") not in system_ids:
                issues.append(
                    {
                        "severity": "error",
                        "edge": edge,
                        "message": f"Dependency source '{edge.get('from')}' not found in nodes",
                    }
                )

            if edge.get("to") not in system_ids:
                issues.append(
                    {
                        "severity": "warning",
                        "edge": edge,
                        "message": f"Dependency target '{edge.get('to')}' not found in nodes (might be external)",
                    }
                )

    return issues
