"""OpenC2 actuator profile export for SOAR integration."""

from typing import Any

from scp_sdk import SCPManifest


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

            actuators.append(
                {
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
                        "tier": manifest.system.classification.tier
                        if manifest.system.classification
                        else None,
                        "domain": manifest.system.classification.domain
                        if manifest.system.classification
                        else None,
                    },
                }
            )

    return {
        "openc2_version": "1.0",
        "actuators": actuators,
        "count": len(actuators),
    }
