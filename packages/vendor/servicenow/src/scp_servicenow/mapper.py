"""Transform SCP unified JSON to ServiceNow CMDB model."""

from enum import Enum
from typing import Any

from scp_sdk import Graph, SystemNode

from .config import CMDBConfig


class IssueSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"


__all__ = [
    "map_node_to_ci",
    "validate_mapping",
    "IssueSeverity",
    "DEFAULT_TIER_TO_CRITICALITY",
]


# Default tier mapping (used if config doesn't specify)
DEFAULT_TIER_TO_CRITICALITY = {
    1: "1 - Critical",
    2: "2 - High",
    3: "3 - Medium",
    4: "4 - Low",
    5: "5 - Planning",
}


def map_node_to_ci(
    node: SystemNode, config: CMDBConfig | None = None
) -> dict[str, Any]:
    """Map SCP node to ServiceNow CI payload.

    Args:
        node: SCP system node
        config: Optional CMDBConfig for custom mappings

    Returns:
        ServiceNow CI data payload
    """
    if config is None:
        config = CMDBConfig()

    ci_data: dict[str, Any] = {
        "name": node.name,
    }

    # Map tier to business_criticality using config
    if node.tier is not None:
        ci_data["business_criticality"] = config.get_tier_criticality(node.tier)

    # Check if config wants to use custom fields
    field_mappings = config.field_mappings or {}

    # Map domain if configured
    if "u_business_domain" in field_mappings:
        if node.domain:
            ci_data["u_business_domain"] = node.domain

    # Map team if configured
    if "u_support_team" in field_mappings:
        if node.team:
            ci_data["u_support_team"] = node.team

    # Map contacts (email) to owned_by/managed_by
    # We return the email address here, and sync.py will resolve it to a sys_user
    contacts = node.contacts or []
    for contact in contacts:
        if (
            contact.type == "email"
            and config.contact_resolution.resolve_email_to_owned_by
        ):
            # Store temporarily as _support_email to be resolved by sync
            ci_data["_support_email"] = contact.ref
            break

    # Format comments field if configured
    comments_fields = field_mappings.get("comments", [])
    if comments_fields:
        comments = config.format_comments(
            team=node.team,
            domain=node.domain,
            contacts=contacts,
            escalation=node.escalation or [],
        )
        if comments:
            ci_data["comments"] = comments

    return ci_data


def validate_mapping(graph: Graph) -> list[dict[str, Any]]:
    """Validate SCP graph can be mapped to ServiceNow.

    Checks for common issues that might prevent successful mapping:
    - Systems missing required 'name' field
    - Invalid tier values (must be 1-5)
    - Dependencies with missing source or target systems

    Args:
        graph: SCP unified graph to validate

    Returns:
        List of validation issues. Each issue is a dict with:
            - severity: IssueSeverity.ERROR | IssueSeverity.WARNING
            - node_id: str (URN of the problematic node)
            - edge: DependencyEdge (for dependency issues)
            - message: str (human-readable description)

        Returns empty list if no issues found.
    """
    issues: list[dict[str, Any]] = []

    # Check for nodes without names
    for system in graph.systems():
        if not system.name:
            issues.append(
                {
                    "severity": IssueSeverity.ERROR,
                    "node_id": system.urn,
                    "message": "System node missing 'name' field",
                }
            )

        # Warn about invalid tier values
        if system.tier is not None and system.tier not in DEFAULT_TIER_TO_CRITICALITY:
            issues.append(
                {
                    "severity": IssueSeverity.WARNING,
                    "node_id": system.urn,
                    "message": f"Invalid tier value {system.tier}, expected 1-5",
                }
            )

    # Check for dependency edges without valid targets
    for edge in graph.dependencies():
        # Source must exist (Graph guarantees this usually, but good to check)
        if not graph.find_system(edge.from_urn):
            issues.append(
                {
                    "severity": IssueSeverity.ERROR,
                    "edge": edge,
                    "message": f"Dependency source '{edge.from_urn}' not found in systems",
                }
            )

        # Target might be external or missing
        if not graph.find_system(edge.to_urn):
            issues.append(
                {
                    "severity": IssueSeverity.WARNING,
                    "edge": edge,
                    "message": f"Dependency target '{edge.to_urn}' not found in systems (might be external)",
                }
            )

    return issues
