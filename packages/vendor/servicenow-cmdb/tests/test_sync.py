"""Tests for the sync module."""

import json

import pytest
from pytest_httpx import HTTPXMock

from scp_servicenow.client import ServiceNowAuth, ServiceNowClient
from scp_servicenow.sync import load_graph_json, sync_to_servicenow


@pytest.fixture
def sample_graph_file(tmp_path):
    """Create a sample graph JSON file."""
    graph_data = {
        "nodes": [
            {
                "id": "urn:scp:test:service-a",
                "type": "System",
                "name": "Service A",
                "tier": 1,
                "domain": "core",
                "team": "platform",
            },
            {
                "id": "urn:scp:test:service-b",
                "type": "System",
                "name": "Service B",
                "tier": 2,
            },
        ],
        "edges": [
            {
                "from": "urn:scp:test:service-a",
                "to": "urn:scp:test:service-b",
                "type": "DEPENDS_ON",
            }
        ],
    }

    graph_file = tmp_path / "test_graph.json"
    graph_file.write_text(json.dumps(graph_data))
    return graph_file


@pytest.fixture
def mock_auth():
    """Create mock ServiceNow auth."""
    return ServiceNowAuth(
        instance_url="https://test.service-now.com",
        username="admin",
        password="password",
    )


class TestLoadGraphJson:
    """Tests for load_graph_json function."""

    def test_load_valid_json(self, sample_graph_file):
        """Test loading valid JSON file."""
        graph_data = load_graph_json(sample_graph_file)

        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert len(graph_data["nodes"]) == 2
        assert len(graph_data["edges"]) == 1

    def test_load_missing_file(self, tmp_path):
        """Test loading missing file raises error."""
        missing_file = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            load_graph_json(missing_file)


class TestSyncToServiceNow:
    """Tests for sync_to_servicenow function."""

    def test_dry_run_mode(self, sample_graph_file, mock_auth, httpx_mock: HTTPXMock):
        """Test dry run mode doesn't make API calls."""
        graph_data = load_graph_json(sample_graph_file)
        client = ServiceNowClient(mock_auth)

        # Dry run should not make any HTTP requests
        result = sync_to_servicenow(graph_data, client, dry_run=True)

        assert len(result.created_cis) == 0  # Dry run doesn't track creates
        assert len(result.failed) == 0

    def test_sync_creates_cis(
        self, sample_graph_file, mock_auth, httpx_mock: HTTPXMock
    ):
        """Test sync creates CIs."""
        graph_data = load_graph_json(sample_graph_file)
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

        result = sync_to_servicenow(graph_data, client, dry_run=False)

        assert len(result.created_cis) == 2
        assert len(result.created_relationships) == 1
        assert len(result.failed) == 0

    def test_sync_handles_existing_ci(self, mock_auth, httpx_mock: HTTPXMock):
        """Test sync updates existing CI."""
        graph_data = {
            "nodes": [
                {
                    "id": "urn:scp:test:existing",
                    "type": "System",
                    "name": "Existing Service",
                }
            ],
            "edges": [],
        }

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

        result = sync_to_servicenow(graph_data, client, dry_run=False)

        assert len(result.created_cis) == 1  # Updated CI counted as created
        assert len(result.failed) == 0
