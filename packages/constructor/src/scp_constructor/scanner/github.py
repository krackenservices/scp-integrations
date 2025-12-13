"""GitHub API scanner for SCP files across an organization."""

import base64
from dataclasses import dataclass

import httpx

from ..models import SCPManifest
from ..parser import load_scp_from_content, SCPParseError


@dataclass
class SCPFile:
    """Represents an SCP file found in a GitHub repository."""
    
    manifest: SCPManifest
    repo: str
    path: str
    sha: str


class GitHubScanner:
    """Scanner for finding SCP files across a GitHub organization."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str):
        """Initialize with a GitHub personal access token.
        
        Args:
            token: GitHub PAT with repo read access
        """
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def list_org_repos(self, org: str) -> list[dict]:
        """List all repositories in an organization.
        
        Args:
            org: GitHub organization name
            
        Returns:
            List of repository metadata dicts
        """
        repos = []
        page = 1
        
        while True:
            resp = self.client.get(
                f"/orgs/{org}/repos",
                params={"per_page": 100, "page": page, "type": "all"},
            )
            resp.raise_for_status()
            
            data = resp.json()
            if not data:
                break
            
            repos.extend(data)
            page += 1
        
        return repos
    
    def search_code(self, org: str, filename: str = "scp.yaml") -> list[dict]:
        """Search for SCP files across an organization using code search.
        
        Args:
            org: GitHub organization name
            filename: Filename to search for
            
        Returns:
            List of search result items
        """
        results = []
        page = 1
        
        while True:
            resp = self.client.get(
                "/search/code",
                params={
                    "q": f"filename:{filename} org:{org}",
                    "per_page": 100,
                    "page": page,
                },
            )
            resp.raise_for_status()
            
            data = resp.json()
            results.extend(data.get("items", []))
            
            # Check if there are more pages
            if len(results) >= data.get("total_count", 0):
                break
            page += 1
        
        return results
    
    def get_file_content(self, owner: str, repo: str, path: str) -> tuple[str, str]:
        """Get the content of a file from a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Path to file in repo
            
        Returns:
            Tuple of (decoded content, sha)
        """
        resp = self.client.get(f"/repos/{owner}/{repo}/contents/{path}")
        resp.raise_for_status()
        
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]
    
    def scan_org(self, org: str, filename: str = "scp.yaml") -> list[SCPFile]:
        """Scan an entire GitHub organization for SCP files.
        
        Args:
            org: GitHub organization name
            filename: Name of SCP files to find
            
        Returns:
            List of SCPFile objects with parsed manifests
        """
        scp_files = []
        
        # Use code search to find files
        search_results = self.search_code(org, filename)
        
        for item in search_results:
            repo_full_name = item["repository"]["full_name"]
            owner, repo = repo_full_name.split("/")
            path = item["path"]
            
            try:
                content, sha = self.get_file_content(owner, repo, path)
                manifest = load_scp_from_content(content, f"{repo_full_name}/{path}")
                
                scp_files.append(SCPFile(
                    manifest=manifest,
                    repo=repo_full_name,
                    path=path,
                    sha=sha,
                ))
            except (httpx.HTTPError, SCPParseError):
                # Skip files that can't be fetched or parsed
                continue
        
        return scp_files


def scan_github_org(org: str, token: str, filename: str = "scp.yaml") -> list[SCPFile]:
    """Convenience function to scan a GitHub organization.
    
    Args:
        org: GitHub organization name
        token: GitHub personal access token
        filename: Name of SCP files to find
        
    Returns:
        List of SCPFile objects
    """
    with GitHubScanner(token) as scanner:
        return scanner.scan_org(org, filename)
