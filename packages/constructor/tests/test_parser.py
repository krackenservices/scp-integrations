"""Tests for the SCP parser (SDK Manifest class)."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from scp_sdk import Manifest


# Path to example SCP files
EXAMPLES_DIR = Path(__file__).parent.parent.parent / "scp-definition" / "examples"


class TestLoadScp:
    """Tests for loading SCP files."""

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

        manifest = Manifest.from_file(scp_file)

        assert manifest.data.scp == "0.1.0"
        assert manifest.data.system.urn == "urn:scp:test:my-service"
        assert manifest.data.system.name == "My Service"

    def test_load_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            Manifest.from_file(tmp_path / "missing.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        """Test error on invalid YAML syntax."""
        scp_file = tmp_path / "scp.yaml"
        scp_file.write_text("{ invalid yaml: [")

        with pytest.raises(Exception):  # YAML parsing error
            Manifest.from_file(scp_file)

    def test_load_empty_file(self, tmp_path):
        """Test error on empty file."""
        scp_file = tmp_path / "scp.yaml"
        scp_file.write_text("")

        with pytest.raises(Exception):  # Will fail validation
            Manifest.from_file(scp_file)

    def test_load_missing_required_field(self, tmp_path):
        """Test validation error when required field missing."""
        scp_content = """
scp: "0.1.0"
system:
  name: "Missing URN Service"
"""
        scp_file = tmp_path / "scp.yaml"
        scp_file.write_text(scp_content)

        with pytest.raises(ValidationError):
            Manifest.from_file(scp_file)


class TestLoadScpFromContent:
    """Tests for loading from string content."""

    def test_load_valid_content(self):
        """Test loading from string content."""
        content = """
scp: "0.1.0"
system:
  urn: "urn:scp:test:string-service"
  name: "String Service"
"""
        manifest = Manifest.from_yaml(content)

        assert manifest.data.system.urn == "urn:scp:test:string-service"

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
        manifest = Manifest.from_yaml(content)

        assert len(manifest.data.depends) == 1
        assert manifest.data.depends[0].system == "urn:scp:test:other-service"
        assert manifest.data.depends[0].criticality == "required"

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
        manifest = Manifest.from_yaml(content)

        assert len(manifest.data.provides) == 1
        assert manifest.data.provides[0].capability == "user-lookup"
        assert manifest.data.provides[0].sla.availability == "99.9%"


class TestRealExamples:
    """Tests against the real SCP example files."""

    @pytest.mark.skipif(
        not EXAMPLES_DIR.exists(), reason="scp-definition examples not available"
    )
    def test_load_user_service(self):
        """Test loading the user-service example."""
        manifest = Manifest.from_file(EXAMPLES_DIR / "user-service" / "scp.yaml")

        assert manifest.data.system.urn == "urn:scp:acme:user-service"
        assert manifest.data.system.name == "User Service"
        assert manifest.data.system.classification.tier == 2
        assert manifest.data.ownership.team == "identity-platform"
        assert len(manifest.data.provides) == 2
        assert len(manifest.data.depends) == 3

    @pytest.mark.skipif(
        not EXAMPLES_DIR.exists(), reason="scp-definition examples not available"
    )
    def test_load_order_service(self):
        """Test loading the order-service example."""
        manifest = Manifest.from_file(EXAMPLES_DIR / "order-service" / "scp.yaml")

        assert manifest.data.system.urn == "urn:scp:acme:order-service"
        assert manifest.data.system.classification.tier == 1
        assert manifest.data.ownership.team == "ordering"
