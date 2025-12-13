"""Tests for the export module."""

import json
import pytest

from scp_constructor.models import (
    SCPManifest,
    System,
    Classification,
    Capability,
    Dependency,
)
from scp_constructor.export import export_json, export_mermaid


@pytest.fixture
def sample_manifests():
    """Create sample manifests for testing."""
    order_service = SCPManifest(
        scp="0.1.0",
        system=System(
            urn="urn:scp:test:order-service",
            name="Order Service",
            classification=Classification(tier=1, domain="ordering"),
        ),
        provides=[
            Capability(capability="order-management", type="rest"),
        ],
        depends=[
            Dependency(
                system="urn:scp:test:user-service",
                capability="user-lookup",
                type="rest",
                criticality="required",
                failure_mode="fail-fast",
            ),
        ],
    )

    user_service = SCPManifest(
        scp="0.1.0",
        system=System(
            urn="urn:scp:test:user-service",
            name="User Service",
            classification=Classification(tier=2, domain="identity"),
        ),
        provides=[
            Capability(capability="user-lookup", type="rest"),
        ],
    )

    return [order_service, user_service]


class TestExportJson:
    """Tests for JSON export."""

    def test_export_structure(self, sample_manifests):
        """Test JSON export has correct structure."""
        result = export_json(sample_manifests)

        assert "nodes" in result
        assert "edges" in result
        assert "meta" in result

    def test_export_nodes(self, sample_manifests):
        """Test nodes are correctly created."""
        result = export_json(sample_manifests)

        system_nodes = [n for n in result["nodes"] if n["type"] == "System"]
        cap_nodes = [n for n in result["nodes"] if n["type"] == "Capability"]

        assert len(system_nodes) == 2
        assert len(cap_nodes) == 2

    def test_export_edges(self, sample_manifests):
        """Test edges are correctly created."""
        result = export_json(sample_manifests)

        dep_edges = [e for e in result["edges"] if e["type"] == "DEPENDS_ON"]
        provides_edges = [e for e in result["edges"] if e["type"] == "PROVIDES"]

        assert len(dep_edges) == 1
        assert dep_edges[0]["from"] == "urn:scp:test:order-service"
        assert dep_edges[0]["to"] == "urn:scp:test:user-service"
        assert len(provides_edges) == 2

    def test_export_meta(self, sample_manifests):
        """Test meta stats are correct."""
        result = export_json(sample_manifests)

        assert result["meta"]["systems_count"] == 2
        assert result["meta"]["capabilities_count"] == 2
        assert result["meta"]["dependencies_count"] == 1


class TestExportMermaid:
    """Tests for Mermaid export."""

    def test_export_header(self, sample_manifests):
        """Test Mermaid output has correct header."""
        result = export_mermaid(sample_manifests)

        assert result.startswith("flowchart LR")

    def test_export_direction(self, sample_manifests):
        """Test custom direction."""
        result = export_mermaid(sample_manifests, direction="TB")

        assert result.startswith("flowchart TB")

    def test_export_tier1_styling(self, sample_manifests):
        """Test tier 1 systems get critical styling."""
        result = export_mermaid(sample_manifests)

        # Tier 1 should have double brackets and red indicator
        assert '[[' in result
        assert '🔴' in result

    def test_export_tier2_styling(self, sample_manifests):
        """Test tier 2 systems get different styling."""
        result = export_mermaid(sample_manifests)

        # Tier 2 should have yellow indicator
        assert '🟡' in result

    def test_export_dependency_edge(self, sample_manifests):
        """Test dependency edges are rendered."""
        result = export_mermaid(sample_manifests)

        # Should have an edge with capability label
        assert "-->|user-lookup|" in result

    def test_export_critical_class(self, sample_manifests):
        """Test critical class is defined."""
        result = export_mermaid(sample_manifests)

        assert "classDef critical" in result
