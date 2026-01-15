"""Tests for the sync module."""

from unittest.mock import MagicMock

import pytest
from pytest_httpx import HTTPXMock
from scp_sdk import SystemNode, DependencyEdge

from scp_servicenow.client import ServiceNowAuth, ServiceNowClient
from scp_servicenow.sync import sync_to_servicenow


@pytest.fixture
def mock_graph():
    """Create a mock Graph object."""
    graph = MagicMock()

    node_a = SystemNode(
        urn="urn:scp:test:service-a",
        name="Service A",
        tier=1,
        domain="core",
        team="platform",
    )
    node_b = SystemNode(
        urn="urn:scp:test:service-b",
        name="Service B",
        tier=2,
    )

    edge = DependencyEdge(
        from_urn="urn:scp:test:service-a",
        to_urn="urn:scp:test:service-b",
        type="DEPENDS_ON",
    )

    graph.systems.return_value = [node_a, node_b]
    graph.dependencies.return_value = [edge]

    # Also support len() if used in CLI
    graph.__len__.return_value = 2

    return graph


@pytest.fixture
def mock_auth():
    """Create mock ServiceNow auth."""
    return ServiceNowAuth(
        instance_url="https://test.service-now.com",
        username="admin",
        password="password",
    )


class TestSyncToServiceNow:
    """Tests for sync_to_servicenow function."""

    def test_dry_run_mode(self, mock_graph, mock_auth, httpx_mock: HTTPXMock):
        """Test dry run mode doesn't make API calls."""
        client = ServiceNowClient(mock_auth)

        # Dry run should not make any HTTP requests
        result = sync_to_servicenow(mock_graph, client, dry_run=True)

        assert len(result.created_cis) == 0  # Dry run doesn't track creates
        assert len(result.failed) == 0

    def test_sync_creates_cis(self, mock_graph, mock_auth, httpx_mock: HTTPXMock):
        """Test sync creates CIs."""
        client = ServiceNowClient(mock_auth)

        # Mock API responses for CI upserts
        # First check if CI exists (empty result = doesn't exist)
        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_ci_service_discovered?sysparm_query=correlation_id=urn:scp:test:service-a&sysparm_limit=1",
            json={"result": []},
        )

        # Then create the CI
        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_ci_service_discovered",
            method="POST",
            json={
                "result": {
                    "sys_id": "test-sys-id-a",
                    "name": "Service A",
                    "correlation_id": "urn:scp:test:service-a",
                }
            },
        )

        # Same for service-b
        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_ci_service_discovered?sysparm_query=correlation_id=urn:scp:test:service-b&sysparm_limit=1",
            json={"result": []},
        )

        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_ci_service_discovered",
            method="POST",
            json={
                "result": {
                    "sys_id": "test-sys-id-b",
                    "name": "Service B",
                    "correlation_id": "urn:scp:test:service-b",
                }
            },
        )

        # Mock relationship type lookup
        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_rel_type?sysparm_query=parent_descriptor=Depends on^child_descriptor=Used by&sysparm_limit=1",
            json={"result": [{"sys_id": "rel-type-id"}]},
        )

        # Mock relationship check (doesn't exist)
        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_rel_ci?sysparm_query=parent=test-sys-id-a^child=test-sys-id-b&sysparm_limit=1",
            json={"result": []},
        )

        # Mock relationship creation
        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_rel_ci",
            method="POST",
            json={
                "result": {
                    "sys_id": "rel-sys-id",
                    "parent": "test-sys-id-a",
                    "child": "test-sys-id-b",
                }
            },
        )

        result = sync_to_servicenow(mock_graph, client, dry_run=False)

        assert len(result.created_cis) == 2
        assert len(result.created_relationships) == 1
        assert len(result.failed) == 0

    def test_sync_handles_existing_ci(self, mock_auth, httpx_mock: HTTPXMock):
        """Test sync updates existing CI."""
        # Create a simpler graph for this test
        graph = MagicMock()
        node = SystemNode(
            urn="urn:scp:test:existing",
            name="Existing Service",
        )
        graph.systems.return_value = [node]
        graph.dependencies.return_value = []

        client = ServiceNowClient(mock_auth)

        # Mock CI already exists
        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_ci_service_discovered?sysparm_query=correlation_id=urn:scp:test:existing&sysparm_limit=1",
            json={
                "result": [
                    {
                        "sys_id": "existing-sys-id",
                        "name": "Existing Service",
                        "correlation_id": "urn:scp:test:existing",
                    }
                ]
            },
        )

        # Mock update
        httpx_mock.add_response(
            url="https://test.service-now.com/api/now/table/cmdb_ci_service_discovered/existing-sys-id",
            method="PUT",
            json={
                "result": {
                    "sys_id": "existing-sys-id",
                    "name": "Existing Service",
                }
            },
        )

        result = sync_to_servicenow(graph, client, dry_run=False)

        assert len(result.created_cis) == 1  # Updated CI counted as created
        assert len(result.failed) == 0
