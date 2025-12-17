"""Tests for the export module."""

import pytest

from scp_constructor.models import (
    SCPManifest,
    System,
    Classification,
    Capability,
    Dependency,
    Ownership,
    SecurityExtension,
)
from scp_constructor.export import export_json, export_mermaid, export_openc2, import_json


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


@pytest.fixture
def security_manifest():
    """Create manifest with security extensions."""
    return SCPManifest(
        scp="0.1.0",
        system=System(
            urn="urn:scp:crowdstrike:falcon",
            name="CrowdStrike Falcon",
            classification=Classification(tier=1, domain="security"),
        ),
        ownership=Ownership(team="security-ops"),
        provides=[
            Capability(
                capability="host-containment",
                type="rest",
                x_security=SecurityExtension(
                    actuator_profile="edr",
                    actions=["contain", "allow", "query"],
                    targets=["hostname", "device_id"],
                ),
            ),
            Capability(
                capability="threat-intel",
                type="rest",
                x_security=SecurityExtension(
                    actuator_profile="edr",
                    actions=["query"],
                    targets=["ioc", "hash"],
                ),
            ),
        ],
    )


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

    def test_export_includes_security_extension(self, security_manifest):
        """Test security extension is included in capability nodes."""
        result = export_json([security_manifest])

        cap_nodes = [n for n in result["nodes"] if n["type"] == "Capability"]
        assert len(cap_nodes) == 2

        containment_node = next(n for n in cap_nodes if n["name"] == "host-containment")
        assert "x_security" in containment_node
        assert containment_node["x_security"]["actuator_profile"] == "edr"
        assert "contain" in containment_node["x_security"]["actions"]


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


class TestExportOpenc2:
    """Tests for OpenC2 export."""

    def test_export_structure(self, security_manifest):
        """Test OpenC2 export has correct structure."""
        result = export_openc2([security_manifest])

        assert "openc2_version" in result
        assert "actuators" in result
        assert "count" in result

    def test_export_actuator_count(self, security_manifest):
        """Test correct number of actuators."""
        result = export_openc2([security_manifest])

        assert result["count"] == 2
        assert len(result["actuators"]) == 2

    def test_export_actuator_fields(self, security_manifest):
        """Test actuator has all required fields."""
        result = export_openc2([security_manifest])

        actuator = result["actuators"][0]
        assert "actuator_id" in actuator
        assert "name" in actuator
        assert "capability" in actuator
        assert "profile" in actuator
        assert "actions" in actuator
        assert "targets" in actuator
        assert "api" in actuator
        assert "metadata" in actuator

    def test_export_actuator_values(self, security_manifest):
        """Test actuator has correct values."""
        result = export_openc2([security_manifest])

        containment = next(a for a in result["actuators"] if a["capability"] == "host-containment")
        assert containment["actuator_id"] == "urn:scp:crowdstrike:falcon"
        assert containment["name"] == "CrowdStrike Falcon"
        assert containment["profile"] == "edr"
        assert containment["actions"] == ["contain", "allow", "query"]
        assert containment["targets"] == ["hostname", "device_id"]
        assert containment["metadata"]["team"] == "security-ops"

    def test_export_skips_non_security_capabilities(self, sample_manifests):
        """Test capabilities without x-security are skipped."""
        result = export_openc2(sample_manifests)

        assert result["count"] == 0
        assert result["actuators"] == []


class TestImportJson:
    """Tests for JSON import."""

    def test_import_reconstructs_manifests(self, sample_manifests):
        """Test import reconstructs manifest list.
        
        Note: import_json only reconstructs systems that were fully defined,
        not stub nodes created from dependency references.
        """
        json_data = export_json(sample_manifests)
        imported = import_json(json_data)

        # Both systems are fully defined (not stubs) so both should be imported
        assert len(imported) == 2

    def test_import_preserves_system_info(self, sample_manifests):
        """Test system info is preserved."""
        json_data = export_json(sample_manifests)
        imported = import_json(json_data)

        urns = {m.system.urn for m in imported}
        # Both should be present since both are real systems (not stubs)
        assert "urn:scp:test:order-service" in urns
        assert "urn:scp:test:user-service" in urns

    def test_import_preserves_classification(self, sample_manifests):
        """Test classification is preserved."""
        json_data = export_json(sample_manifests)
        imported = import_json(json_data)

        order = next(m for m in imported if m.system.urn == "urn:scp:test:order-service")
        assert order.system.classification.tier == 1
        assert order.system.classification.domain == "ordering"

    def test_import_preserves_security_extension(self, security_manifest):
        """Test security extension survives round-trip."""
        json_data = export_json([security_manifest])
        imported = import_json(json_data)

        assert len(imported) == 1
        manifest = imported[0]

        # Check security extension is preserved
        containment = next(c for c in manifest.provides if c.capability == "host-containment")
        assert containment.x_security is not None
        assert containment.x_security.actuator_profile == "edr"
        assert containment.x_security.actions == ["contain", "allow", "query"]

    def test_roundtrip_openc2_export(self, security_manifest):
        """Test JSON -> import -> OpenC2 export produces same result."""
        # Direct export
        direct_openc2 = export_openc2([security_manifest])

        # Round-trip export
        json_data = export_json([security_manifest])
        imported = import_json(json_data)
        roundtrip_openc2 = export_openc2(imported)

        # Compare (ignoring contract which isn't stored in JSON)
        assert direct_openc2["count"] == roundtrip_openc2["count"]
        assert len(direct_openc2["actuators"]) == len(roundtrip_openc2["actuators"])

        for direct, roundtrip in zip(direct_openc2["actuators"], roundtrip_openc2["actuators"]):
            assert direct["actuator_id"] == roundtrip["actuator_id"]
            assert direct["capability"] == roundtrip["capability"]
            assert direct["actions"] == roundtrip["actions"]
            assert direct["targets"] == roundtrip["targets"]

