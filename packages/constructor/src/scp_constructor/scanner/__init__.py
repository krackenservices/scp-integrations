"""Scanner modules for locating SCP files."""

from .local import scan_directory
from .github import scan_github_org

__all__ = ["scan_directory", "scan_github_org"]
