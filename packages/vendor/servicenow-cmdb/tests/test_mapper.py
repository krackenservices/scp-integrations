"""Tests for the mapper module."""

from scp_servicenow.mapper import map_node_to_ci, validate_mapping, TIER_TO_CRITICALITY


class TestMapNodeToCi:
    """Tests for map_node_to_ci function."""

    def test_basic_mapping(self):
        """Test basic node to CI mapping."""
        node = {
            "id": "urn:scp:test:order-service",
            "type": "System",
            "name": "Order Service",
        }

        ci_data = map_node_to_ci(node)

        assert ci_data["name"] == "Order Service"

    def test_tier_mapping(self):
        """Test tier to business_criticality mapping."""
        node = {
            "id": "urn:scp:test:critical-service",
            "type": "System",
            "name": "Critical Service",
            "tier": 1,
        }

        ci_data = map_node_to_ci(node)

        assert ci_data["business_criticality"] == "1 - Critical"

    def test_all_tiers(self):
        """Test all tier values map correctly."""
        for tier, expected_criticality in TIER_TO_CRITICALITY.items():
            node = {
                "id": f"urn:scp:test:tier-{tier}",
                "type": "System",
                "name": f"Tier {tier} Service",
                "tier": tier,
            }

            ci_data = map_node_to_ci(node)
            assert ci_data["business_criticality"] == expected_criticality

    def test_domain_mapping(self):
        """Test domain to u_business_domain mapping."""
        node = {
            "id": "urn:scp:test:service",
            "type": "System",
            "name": "Service",
            "domain": "payments",
        }

        ci_data = map_node_to_ci(node)

        assert ci_data["u_business_domain"] == "payments"

    def test_team_mapping(self):
        """Test team to u_support_team mapping."""
        node = {
            "id": "urn:scp:test:service",
            "type": "System",
            "name": "Service",
            "team": "platform-team",
        }

        ci_data = map_node_to_ci(node)

        assert ci_data["u_support_team"] == "platform-team"

    def test_missing_optional_fields(self):
        """Test mapping with missing optional fields."""
        node = {
            "id": "urn:scp:test:basic",
            "type": "System",
            "name": "Basic Service",
        }

        ci_data = map_node_to_ci(node)

        assert ci_data["name"] == "Basic Service"
        assert "business_criticality" not in ci_data
        assert "u_business_domain" not in ci_data
        assert "u_support_team" not in ci_data


class TestValidateMapping:
    """Tests for validate_mapping function."""

    def test_valid_graph(self):
        """Test validation passes for valid graph."""
        graph_data = {
            "nodes": [
                {
                    "id": "urn:scp:test:service-a",
                    "type": "System",
                    "name": "Service A",
                    "tier": 1,
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

        issues = validate_mapping(graph_data)

        assert len(issues) == 0

    def test_missing_name(self):
        """Test validation catches missing name."""
        graph_data = {
            "nodes": [
                {
                    "id": "urn:scp:test:no-name",
                    "type": "System",
                }
            ],
            "edges": [],
        }

        issues = validate_mapping(graph_data)

        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert "name" in issues[0]["message"].lower()

    def test_invalid_tier(self):
        """Test validation warns about invalid tier."""
        graph_data = {
            "nodes": [
                {
                    "id": "urn:scp:test:bad-tier",
                    "type": "System",
                    "name": "Bad Tier",
                    "tier": 99,
                }
            ],
            "edges": [],
        }

        issues = validate_mapping(graph_data)

        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert "tier" in issues[0]["message"].lower()

    def test_missing_dependency_source(self):
        """Test validation catches missing dependency source."""
        graph_data = {
            "nodes": [
                {
                    "id": "urn:scp:test:service-b",
                    "type": "System",
                    "name": "Service B",
                }
            ],
            "edges": [
                {
                    "from": "urn:scp:test:service-a",
                    "to": "urn:scp:test:service-b",
                    "type": "DEPENDS_ON",
                }
            ],
        }

        issues = validate_mapping(graph_data)

        assert len(issues) == 1
        assert issues[0]["severity"] == "error"

    def test_missing_dependency_target(self):
        """Test validation warns about missing external dependency target."""
        graph_data = {
            "nodes": [
                {
                    "id": "urn:scp:test:service-a",
                    "type": "System",
                    "name": "Service A",
                }
            ],
            "edges": [
                {
                    "from": "urn:scp:test:service-a",
                    "to": "urn:scp:test:external",
                    "type": "DEPENDS_ON",
                }
            ],
        }

        issues = validate_mapping(graph_data)

        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
