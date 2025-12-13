"""Local filesystem scanner for SCP files."""

from pathlib import Path


def scan_directory(root: Path, filename: str = "scp.yaml") -> list[Path]:
    """Recursively scan a directory for SCP manifest files.
    
    Args:
        root: Directory to scan
        filename: Name of manifest files to find (default: scp.yaml)
        
    Returns:
        List of paths to discovered SCP files
    """
    root = Path(root)
    
    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")
    
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")
    
    # Find all matching files recursively
    scp_files = list(root.rglob(filename))
    
    # Sort for consistent ordering
    return sorted(scp_files)


def scan_directories(roots: list[Path], filename: str = "scp.yaml") -> list[Path]:
    """Scan multiple directories for SCP manifest files.
    
    Args:
        roots: List of directories to scan
        filename: Name of manifest files to find
        
    Returns:
        Combined list of paths to discovered SCP files (deduplicated)
    """
    all_files: set[Path] = set()
    
    for root in roots:
        try:
            files = scan_directory(root, filename)
            all_files.update(files)
        except (FileNotFoundError, NotADirectoryError):
            # Skip invalid directories, let caller handle logging
            continue
    
    return sorted(all_files)
