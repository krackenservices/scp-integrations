"""Tests for the SCP models module."""

import pytest
from pydantic import ValidationError

from scp_constructor.models import (
    SCPManifest,
    System,
    Classification,
    Ownership,
    Capability,
    Dependency,
    SLA,
)


class TestSystem:
    """Tests for System model."""

    def test_minimal_system(self):
        """Test creating a system with only required fields."""
        system = System(urn="urn:scp:test:my-service", name="My Service")

        assert system.urn == "urn:scp:test:my-service"
        assert system.name == "My Service"
        assert system.description is None
        assert system.classification is None

    def test_system_with_classification(self):
        """Test system with classification."""
        system = System(
            urn="urn:scp:test:critical-service",
            name="Critical Service",
            classification=Classification(tier=1, domain="payments"),
        )

        assert system.classification.tier == 1
        assert system.classification.domain == "payments"

    def test_tier_validation(self):
        """Test tier must be 1-5."""
        with pytest.raises(ValidationError):
            Classification(tier=0)

        with pytest.raises(ValidationError):
            Classification(tier=6)


class TestCapability:
    """Tests for Capability model."""

    def test_rest_capability(self):
        """Test creating a REST capability."""
        cap = Capability(
            capability="user-lookup",
            type="rest",
            sla=SLA(availability="99.9%", latency_p99_ms=100),
        )

        assert cap.capability == "user-lookup"
        assert cap.type == "rest"
        assert cap.sla.availability == "99.9%"

    def test_event_capability(self):
        """Test creating an event capability with topics."""
        cap = Capability(
            capability="order-events",
            type="event",
            topics=["orders.created", "orders.updated"],
        )

        assert cap.type == "event"
        assert len(cap.topics) == 2


class TestDependency:
    """Tests for Dependency model."""

    def test_required_dependency(self):
        """Test creating a required dependency."""
        dep = Dependency(
            system="urn:scp:test:other-service",
            type="rest",
            criticality="required",
            failure_mode="fail-fast",
        )

        assert dep.criticality == "required"
        assert dep.failure_mode == "fail-fast"

    def test_degraded_dependency(self):
        """Test creating a degraded dependency."""
        dep = Dependency(
            system="urn:scp:test:cache",
            type="data",
            criticality="degraded",
            failure_mode="fallback",
        )

        assert dep.criticality == "degraded"


class TestSCPManifest:
    """Tests for the root SCPManifest model."""

    def test_minimal_manifest(self):
        """Test creating a minimal manifest."""
        manifest = SCPManifest(
            scp="0.1.0",
            system=System(urn="urn:scp:test:service", name="Service"),
        )

        assert manifest.scp == "0.1.0"
        assert manifest.urn == "urn:scp:test:service"
        assert manifest.ownership is None
        assert manifest.provides is None
        assert manifest.depends is None

    def test_full_manifest(self):
        """Test creating a full manifest."""
        manifest = SCPManifest(
            scp="0.1.0",
            system=System(
                urn="urn:scp:test:full-service",
                name="Full Service",
                classification=Classification(tier=1, domain="core"),
            ),
            ownership=Ownership(team="platform"),
            provides=[
                Capability(capability="api", type="rest"),
            ],
            depends=[
                Dependency(
                    system="urn:scp:test:db",
                    type="data",
                    criticality="required",
                ),
            ],
        )

        assert manifest.ownership.team == "platform"
        assert len(manifest.provides) == 1
        assert len(manifest.depends) == 1

    def test_otel_service_name_property(self):
        """Test the otel_service_name convenience property."""
        from scp_constructor.models import Runtime, Environment

        manifest = SCPManifest(
            scp="0.1.0",
            system=System(urn="urn:scp:test:service", name="Service"),
            runtime=Runtime(
                environments={
                    "production": Environment(otel_service_name="my-service-prod"),
                }
            ),
        )

        assert manifest.otel_service_name == "my-service-prod"
