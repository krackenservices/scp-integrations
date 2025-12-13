"""YAML parser for SCP manifest files."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import SCPManifest


class SCPParseError(Exception):
    """Raised when an SCP file cannot be parsed or validated."""

    def __init__(self, path: Path, message: str, errors: list[dict] | None = None):
        self.path = path
        self.errors = errors or []
        super().__init__(f"{path}: {message}")


def load_scp(path: Path) -> SCPManifest:
    """Load and validate an SCP manifest from a YAML file.
    
    Args:
        path: Path to the scp.yaml file
        
    Returns:
        Validated SCPManifest object
        
    Raises:
        SCPParseError: If file cannot be read or fails validation
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise SCPParseError(path, "File not found")
    except yaml.YAMLError as e:
        raise SCPParseError(path, f"Invalid YAML: {e}")

    if not data:
        raise SCPParseError(path, "Empty file")

    try:
        return SCPManifest.model_validate(data)
    except ValidationError as e:
        raise SCPParseError(
            path,
            f"Schema validation failed with {len(e.errors())} errors",
            errors=[err for err in e.errors()],
        )


def load_scp_from_content(content: str, source: str = "<string>") -> SCPManifest:
    """Load and validate an SCP manifest from YAML string content.
    
    Args:
        content: YAML string content
        source: Source identifier for error messages
        
    Returns:
        Validated SCPManifest object
    """
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise SCPParseError(Path(source), f"Invalid YAML: {e}")

    if not data:
        raise SCPParseError(Path(source), "Empty content")

    try:
        return SCPManifest.model_validate(data)
    except ValidationError as e:
        raise SCPParseError(
            Path(source),
            f"Schema validation failed with {len(e.errors())} errors",
            errors=[err for err in e.errors()],
        )
