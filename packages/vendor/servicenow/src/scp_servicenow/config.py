"""Configuration loader for ServiceNow CMDB integration."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


__all__ = ["CMDBConfig", "ContactResolutionConfig"]


# Default configuration constants
DEFAULT_TIER_MAPPINGS = {
    1: "1 - Critical",
    2: "2 - High",
    3: "3 - Medium",
    4: "4 - Low",
    5: "5 - Planning",
}

DEFAULT_COMMENTS_TEMPLATE = """SCP Metadata:
Team: {team}
Domain: {domain}

Contacts:
{contacts}

Escalation Chain:
{escalation}"""


class ContactResolutionConfig(BaseModel):
    """Contact resolution configuration."""

    resolve_email_to_owned_by: bool = True
    email_not_found: str = "warn"  # warn, ignore, error


class CMDBConfig(BaseModel):
    """ServiceNow CMDB integration configuration."""

    field_mappings: dict[str, Any] = Field(
        default_factory=lambda: {
            "name": "name",
            "business_criticality": "tier",
            "comments": ["contacts", "escalation", "team", "domain"],
        }
    )
    tier_mappings: dict[int, str] = Field(
        default_factory=lambda: DEFAULT_TIER_MAPPINGS.copy()
    )
    contact_resolution: ContactResolutionConfig = Field(
        default_factory=ContactResolutionConfig
    )
    ci_class: str = "cmdb_ci_service_discovered"
    comments_template: str = DEFAULT_COMMENTS_TEMPLATE

    @classmethod
    def load(cls, config_path: Path | None = None) -> "CMDBConfig":
        """Load configuration from YAML file.

        Args:
            config_path: Path to cmdb.yaml config file. If None, looks for cmdb.yaml
                        in current directory. If not found, uses defaults.

        Returns:
            CMDBConfig instance
        """
        if config_path is None:
            # Look for cmdb.yaml in current directory only
            cwd_config = Path.cwd() / "cmdb.yaml"
            if cwd_config.exists():
                config_path = cwd_config
            else:
                # Return defaults - no config file required
                return cls()

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}

        return cls(**config_data)

    def to_yaml(self) -> str:
        """Generate YAML representation of current config.

        Returns:
            YAML string
        """
        return yaml.dump(
            {
                "field_mappings": self.field_mappings,
                "tier_mappings": self.tier_mappings,
                "contact_resolution": {
                    "resolve_email_to_owned_by": self.contact_resolution.resolve_email_to_owned_by,
                    "email_not_found": self.contact_resolution.email_not_found,
                },
                "ci_class": self.ci_class,
                "comments_template": self.comments_template,
            },
            default_flow_style=False,
            sort_keys=False,
        )

    def get_tier_criticality(self, tier: int | None) -> str:
        """Get ServiceNow criticality from SCP tier.

        Args:
            tier: SCP tier (1-5)

        Returns:
            ServiceNow criticality string
        """
        if tier is None:
            return "3 - Medium"
        return self.tier_mappings.get(tier, "3 - Medium")

    def format_comments(
        self,
        team: str | None = None,
        domain: str | None = None,
        contacts: list[dict] | None = None,
        escalation: list[str] | None = None,
    ) -> str:
        """Format comments field using template.

        Args:
            team: Team name
            domain: Business domain
            contacts: List of contact dicts with type and ref
            escalation: Escalation chain

        Returns:
            Formatted comments string
        """
        if not self.comments_template:
            return ""

        # Format contacts
        contacts_str = ""
        if contacts:
            contacts_str = "\n".join([f"  - {c.type}: {c.ref}" for c in contacts])

        # Format escalation
        escalation_str = ""
        if escalation:
            escalation_str = " → ".join(escalation)

        return self.comments_template.format(
            team=team or "Not specified",
            domain=domain or "Not specified",
            contacts=contacts_str or "None",
            escalation=escalation_str or "None",
        )
