"""Comprehensive validation tests for mapper module."""

from scp_sdk import SystemNode, Graph, DependencyEdge
from scp_servicenow.mapper import (
    map_node_to_ci,
    validate_mapping,
    DEFAULT_TIER_TO_CRITICALITY,
    IssueSeverity,
)
from scp_servicenow.config import CMDBConfig
from unittest.mock import MagicMock


class TestMapNodeToCi:
    """Tests for map_node_to_ci function."""

    def test_basic_mapping(self):
        """Test basic node to CI mapping."""
        node = SystemNode(
            urn="urn:scp:test:order-service",
            name="Order Service",
        )

        ci_data = map_node_to_ci(node)

        assert ci_data["name"] == "Order Service"

    def test_tier_mapping(self):
        """Test tier to business_criticality mapping."""
        node = SystemNode(
            urn="urn:scp:test:critical-service",
            name="Critical Service",
            tier=1,
        )

        ci_data = map_node_to_ci(node)

        assert ci_data["business_criticality"] == "1 - Critical"

    def test_all_tiers(self):
        """Test all tier values map correctly."""
        for tier, expected_criticality in DEFAULT_TIER_TO_CRITICALITY.items():
            node = SystemNode(
                urn=f"urn:scp:test:tier-{tier}",
                name=f"Tier {tier} Service",
                tier=tier,
            )

            ci_data = map_node_to_ci(node)
            assert ci_data["business_criticality"] == expected_criticality

    def test_domain_mapping(self):
        """Test domain to u_business_domain mapping."""
        node = SystemNode(
            urn="urn:scp:test:service",
            name="Service",
            domain="payments",
        )

        config = CMDBConfig(
            field_mappings={
                "u_business_domain": "domain",
                "name": "name",
                "business_criticality": "tier",
            }
        )

        ci_data = map_node_to_ci(node, config)

        assert ci_data["u_business_domain"] == "payments"

    def test_team_mapping(self):
        """Test team to u_support_team mapping."""
        node = SystemNode(
            urn="urn:scp:test:service",
            name="Service",
            team="platform-team",
        )

        config = CMDBConfig(
            field_mappings={
                "u_support_team": "team",
                "name": "name",
                "business_criticality": "tier",
            }
        )

        ci_data = map_node_to_ci(node, config)

        assert ci_data["u_support_team"] == "platform-team"

    def test_missing_optional_fields(self):
        """Test mapping with missing optional fields."""
        node = SystemNode(
            urn="urn:scp:test:basic",
            name="Basic Service",
        )

        ci_data = map_node_to_ci(node)

        assert ci_data["name"] == "Basic Service"
        assert "business_criticality" not in ci_data
        assert "u_business_domain" not in ci_data
        assert "u_support_team" not in ci_data


class TestValidateMapping:
    """Tests for validate_mapping function."""

    def test_valid_graph_no_issues(self):
        """Test validation passes for valid graph."""
        # Create mock graph with valid systems
        graph = MagicMock(spec=Graph)

        node_a = SystemNode(urn="urn:scp:test:service-a", name="Service A", tier=1)
        node_b = SystemNode(urn="urn:scp:test:service-b", name="Service B", tier=2)

        graph.systems.return_value = [node_a, node_b]

        edge = DependencyEdge(
            from_urn="urn:scp:test:service-a", to_urn="urn:scp:test:service-b"
        )
        graph.dependencies.return_value = [edge]

        # Mock find_system to return nodes when they exist
        def mock_find_system(urn):
            if urn == "urn:scp:test:service-a":
                return node_a
            elif urn == "urn:scp:test:service-b":
                return node_b
            return None

        graph.find_system.side_effect = mock_find_system

        issues = validate_mapping(graph)

        assert len(issues) == 0

    def test_missing_name_error(self):
        """Test validation catches missing name."""
        graph = MagicMock(spec=Graph)

        # Create node with no name (empty string)
        node = SystemNode(urn="urn:scp:test:no-name", name="")

        graph.systems.return_value = [node]
        graph.dependencies.return_value = []

        issues = validate_mapping(graph)

        assert len(issues) == 1
        assert issues[0]["severity"] == IssueSeverity.ERROR
        assert "name" in issues[0]["message"].lower()
        assert issues[0]["node_id"] == "urn:scp:test:no-name"

    def test_invalid_tier_warning(self):
        """Test validation warns about invalid tier."""
        graph = MagicMock(spec=Graph)

        # Create node with invalid tier
        node = SystemNode(urn="urn:scp:test:bad-tier", name="Bad Tier", tier=99)

        graph.systems.return_value = [node]
        graph.dependencies.return_value = []

        issues = validate_mapping(graph)

        assert len(issues) == 1
        assert issues[0]["severity"] == IssueSeverity.WARNING
        assert "tier" in issues[0]["message"].lower()
        assert "99" in issues[0]["message"]

    def test_missing_dependency_source_error(self):
        """Test validation catches missing dependency source."""
        graph = MagicMock(spec=Graph)

        node_b = SystemNode(urn="urn:scp:test:service-b", name="Service B")

        graph.systems.return_value = [node_b]

        edge = DependencyEdge(
            from_urn="urn:scp:test:service-a", to_urn="urn:scp:test:service-b"
        )
        graph.dependencies.return_value = [edge]

        # Mock find_system - only service-b exists
        def mock_find_system(urn):
            if urn == "urn:scp:test:service-b":
                return node_b
            return None

        graph.find_system.side_effect = mock_find_system

        issues = validate_mapping(graph)

        # Should have error for missing source
        errors = [i for i in issues if i["severity"] == IssueSeverity.ERROR]
        assert len(errors) == 1
        assert "service-a" in errors[0]["message"]
        assert "not found" in errors[0]["message"].lower()

    def test_missing_dependency_target_warning(self):
        """Test validation warns about missing external dependency target."""
        graph = MagicMock(spec=Graph)

        node_a = SystemNode(urn="urn:scp:test:service-a", name="Service A")

        graph.systems.return_value = [node_a]

        edge = DependencyEdge(
            from_urn="urn:scp:test:service-a", to_urn="urn:scp:test:external"
        )
        graph.dependencies.return_value = [edge]

        # Mock find_system - only service-a exists
        def mock_find_system(urn):
            if urn == "urn:scp:test:service-a":
                return node_a
            return None

        graph.find_system.side_effect = mock_find_system

        issues = validate_mapping(graph)

        # Should have warning for missing target (might be external)
        warnings = [i for i in issues if i["severity"] == IssueSeverity.WARNING]
        assert len(warnings) == 1
        assert "external" in warnings[0]["message"]
        assert "might be external" in warnings[0]["message"].lower()

    def test_multiple_issues(self):
        """Test validation catches multiple issues."""
        graph = MagicMock(spec=Graph)

        # Node with no name
        node_a = SystemNode(urn="urn:scp:test:no-name", name="")
        # Node with invalid tier
        node_b = SystemNode(urn="urn:scp:test:bad-tier", name="Bad Tier", tier=999)

        graph.systems.return_value = [node_a, node_b]
        graph.dependencies.return_value = []

        issues = validate_mapping(graph)

        assert len(issues) == 2
        errors = [i for i in issues if i["severity"] == IssueSeverity.ERROR]
        warnings = [i for i in issues if i["severity"] == IssueSeverity.WARNING]

        assert len(errors) == 1  # Missing name
        assert len(warnings) == 1  # Invalid tier
