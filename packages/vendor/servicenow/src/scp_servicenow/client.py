"""ServiceNow REST API client for CMDB operations."""

from typing import Any, Literal
import httpx
from pydantic import BaseModel


__all__ = ["ServiceNowAuth", "ServiceNowClient"]


class ServiceNowAuth(BaseModel):
    """ServiceNow authentication configuration."""

    instance_url: str
    username: str | None = None
    password: str | None = None
    token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None

    def get_auth(self) -> tuple[str, str] | None:
        """Get basic auth tuple if username/password provided."""
        if self.username and self.password:
            return (self.username, self.password)
        return None

    def get_headers(self) -> dict[str, str]:
        """Get authorization headers."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.client_id and self.client_secret:
            # For client credentials, we'd need to fetch token first
            # For now, assume token is already provided
            raise ValueError(
                "Client credentials flow requires token exchange - please provide SERVICENOW_TOKEN"
            )

        return headers


class ServiceNowClient:
    """ServiceNow CMDB API client."""

    def __init__(self, auth: ServiceNowAuth, timeout: int = 30):
        """Initialize client.

        Args:
            auth: Authentication configuration
            timeout: Request timeout in seconds
        """
        self.auth = auth
        self.base_url = auth.instance_url.rstrip("/")
        self.timeout = timeout

        # Prepare auth for httpx
        self._httpx_auth = auth.get_auth()
        self._headers = auth.get_headers()

        # Cache for relationship type sys_id to avoid repeated lookups
        self._rel_type_cache: dict[str, str] = {}

    def _request(
        self,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make authenticated request to ServiceNow.

        Args:
            method: HTTP method
            path: API path (without base URL)
            **kwargs: Additional arguments for httpx.request

        Returns:
            Response JSON data

        Raises:
            httpx.HTTPStatusError: On HTTP error responses
        """
        url = f"{self.base_url}/{path.lstrip('/')}"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(
                method=method,
                url=url,
                auth=self._httpx_auth,
                headers=self._headers,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

    def upsert_ci(
        self, ci_class: str, correlation_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create or update a Configuration Item.

        Uses correlation_id to determine if CI exists, then creates or updates.

        Args:
            ci_class: CI class name (e.g., 'cmdb_ci_service_discovered')
            correlation_id: Unique identifier (SCP URN)
            data: CI field data

        Returns:
            Created or updated CI record
        """
        # Query for existing CI by correlation_id
        query_params = {
            "sysparm_query": f"correlation_id={correlation_id}",
            "sysparm_limit": 1,
        }

        existing = self._request(
            "GET", f"/api/now/table/{ci_class}", params=query_params
        )

        if existing.get("result"):
            # Update existing CI
            ci_sys_id = existing["result"][0]["sys_id"]
            result = self._request(
                "PUT", f"/api/now/table/{ci_class}/{ci_sys_id}", json=data
            )
            return result.get("result", {})
        else:
            # Create new CI
            data["correlation_id"] = correlation_id
            result = self._request("POST", f"/api/now/table/{ci_class}", json=data)
            return result.get("result", {})

    def create_relationship(
        self, parent_sys_id: str, child_sys_id: str, type_sys_id: str | None = None
    ) -> dict[str, Any]:
        """Create a CI relationship.

        Args:
            parent_sys_id: Parent CI sys_id
            child_sys_id: Child CI sys_id
            type_sys_id: Relationship type sys_id (defaults to "Depends on::Used by")

        Returns:
            Created relationship record
        """
        # Check if relationship already exists
        query_params = {
            "sysparm_query": f"parent={parent_sys_id}^child={child_sys_id}",
            "sysparm_limit": 1,
        }

        existing = self._request(
            "GET", "/api/now/table/cmdb_rel_ci", params=query_params
        )

        if existing.get("result"):
            # Relationship already exists
            return existing["result"][0]

        # Create new relationship
        rel_data: dict[str, Any] = {
            "parent": parent_sys_id,
            "child": child_sys_id,
        }

        if type_sys_id:
            rel_data["type"] = type_sys_id
        else:
            # Get "Depends on::Used by" relationship type (with caching)
            cache_key = "Depends on::Used by"
            if cache_key in self._rel_type_cache:
                rel_data["type"] = self._rel_type_cache[cache_key]
            else:
                # Query for the relationship type
                type_query = {
                    "sysparm_query": "parent_descriptor=Depends on^child_descriptor=Used by",
                    "sysparm_limit": 1,
                }
                type_result = self._request(
                    "GET", "/api/now/table/cmdb_rel_type", params=type_query
                )

                if type_result.get("result"):
                    type_sys_id = type_result["result"][0]["sys_id"]
                    self._rel_type_cache[cache_key] = type_sys_id
                    rel_data["type"] = type_sys_id

        result = self._request("POST", "/api/now/table/cmdb_rel_ci", json=rel_data)
        return result.get("result", {})

    def get_ci_by_correlation_id(
        self, ci_class: str, correlation_id: str
    ) -> dict[str, Any] | None:
        """Get CI by correlation_id.

        Args:
            ci_class: CI class name
            correlation_id: Unique identifier

        Returns:
            CI record or None if not found
        """
        query_params = {
            "sysparm_query": f"correlation_id={correlation_id}",
            "sysparm_limit": 1,
        }

        result = self._request("GET", f"/api/now/table/{ci_class}", params=query_params)

        if result.get("result"):
            return result["result"][0]
        return None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get ServiceNow user by email.

        Args:
            email: Email address

        Returns:
            User record or None if not found
        """
        query_params = {
            "sysparm_query": f"email={email}",
            "sysparm_limit": 1,
            "sysparm_fields": "sys_id,name,email,user_name",
        }

        result = self._request("GET", "/api/now/table/sys_user", params=query_params)

        if result.get("result"):
            return result["result"][0]
        return None
