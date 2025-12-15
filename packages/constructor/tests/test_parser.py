"""Tests for the SCP parser module."""

import pytest
from pathlib import Path

from scp_constructor.parser import load_scp, load_scp_from_content, SCPParseError


# Path to example SCP files
EXAMPLES_DIR = Path(__file__).parent.parent.parent / "scp-definition" / "examples"


class TestLoadScp:
    """Tests for load_scp function."""

    def test_load_valid_file(self, tmp_path):
        """Test loading a valid SCP file."""
        scp_content = """
scp: "0.1.0"
system:
  urn: "urn:scp:test:my-service"
  name: "My Service"
"""
        scp_file = tmp_path / "scp.yaml"
        scp_file.write_text(scp_content)

        manifest = load_scp(scp_file)

        assert manifest.scp == "0.1.0"
        assert manifest.system.urn == "urn:scp:test:my-service"
        assert manifest.system.name == "My Service"

    def test_load_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        with pytest.raises(SCPParseError) as exc:
            load_scp(tmp_path / "missing.yaml")

        assert "File not found" in str(exc.value)

    def test_load_invalid_yaml(self, tmp_path):
        """Test error on invalid YAML syntax."""
        scp_file = tmp_path / "scp.yaml"
        scp_file.write_text("{ invalid yaml: [")

        with pytest.raises(SCPParseError) as exc:
            load_scp(scp_file)

        assert "Invalid YAML" in str(exc.value)

    def test_load_empty_file(self, tmp_path):
        """Test error on empty file."""
        scp_file = tmp_path / "scp.yaml"
        scp_file.write_text("")

        with pytest.raises(SCPParseError) as exc:
            load_scp(scp_file)

        assert "Empty file" in str(exc.value)

    def test_load_missing_required_field(self, tmp_path):
        """Test validation error when required field missing."""
        scp_content = """
scp: "0.1.0"
system:
  name: "Missing URN Service"
"""
        scp_file = tmp_path / "scp.yaml"
        scp_file.write_text(scp_content)

        with pytest.raises(SCPParseError) as exc:
            load_scp(scp_file)

        assert "validation failed" in str(exc.value)


class TestLoadScpFromContent:
    """Tests for load_scp_from_content function."""

    def test_load_valid_content(self):
        """Test loading from string content."""
        content = """
scp: "0.1.0"
system:
  urn: "urn:scp:test:string-service"
  name: "String Service"
"""
        manifest = load_scp_from_content(content)

        assert manifest.system.urn == "urn:scp:test:string-service"

    def test_load_with_dependencies(self):
        """Test loading manifest with dependencies."""
        content = """
scp: "0.1.0"
system:
  urn: "urn:scp:test:dependent-service"
  name: "Dependent Service"
depends:
  - system: "urn:scp:test:other-service"
    type: "rest"
    criticality: "required"
"""
        manifest = load_scp_from_content(content)

        assert len(manifest.depends) == 1
        assert manifest.depends[0].system == "urn:scp:test:other-service"
        assert manifest.depends[0].criticality == "required"

    def test_load_with_capabilities(self):
        """Test loading manifest with provided capabilities."""
        content = """
scp: "0.1.0"
system:
  urn: "urn:scp:test:provider-service"
  name: "Provider Service"
provides:
  - capability: "user-lookup"
    type: "rest"
    sla:
      availability: "99.9%"
      latency_p99_ms: 100
"""
        manifest = load_scp_from_content(content)

        assert len(manifest.provides) == 1
        assert manifest.provides[0].capability == "user-lookup"
        assert manifest.provides[0].sla.availability == "99.9%"


class TestRealExamples:
    """Tests against the real SCP example files."""

    @pytest.mark.skipif(
        not EXAMPLES_DIR.exists(),
        reason="scp-definition examples not available"
    )
    def test_load_user_service(self):
        """Test loading the user-service example."""
        manifest = load_scp(EXAMPLES_DIR / "user-service" / "scp.yaml")

        assert manifest.system.urn == "urn:scp:acme:user-service"
        assert manifest.system.name == "User Service"
        assert manifest.system.classification.tier == 2
        assert manifest.ownership.team == "identity-platform"
        assert len(manifest.provides) == 2
        assert len(manifest.depends) == 3

    @pytest.mark.skipif(
        not EXAMPLES_DIR.exists(),
        reason="scp-definition examples not available"
    )
    def test_load_order_service(self):
        """Test loading the order-service example."""
        manifest = load_scp(EXAMPLES_DIR / "order-service" / "scp.yaml")

        assert manifest.system.urn == "urn:scp:acme:order-service"
        assert manifest.system.classification.tier == 1
        assert manifest.ownership.team == "ordering"
