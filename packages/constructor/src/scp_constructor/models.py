"""Pydantic models for SCP (System Capability Protocol) manifests.

These models match the SCP v0.1.0 schema specification.
"""

from typing import Literal
from pydantic import BaseModel, Field


# ============================================================================
# Nested Types
# ============================================================================


class Contact(BaseModel):
    """Contact channel for a team."""

    type: Literal["oncall", "slack", "email", "teams", "pagerduty", "opsgenie"]
    ref: str


class Contract(BaseModel):
    """API contract specification reference."""

    type: Literal["openapi", "asyncapi", "protobuf", "graphql", "avro", "jsonschema"] | None = None
    ref: str | None = None


class SLA(BaseModel):
    """Service level agreement targets."""

    availability: str | None = None  # e.g., "99.95%"
    latency_p50_ms: int | None = None
    latency_p99_ms: int | None = None
    throughput_rps: int | None = None


class RetryConfig(BaseModel):
    """Retry configuration for dependencies."""

    max_attempts: int | None = None
    backoff: Literal["none", "linear", "exponential"] | None = None


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int | None = None
    reset_timeout_ms: int | None = None


class SecurityConstraints(BaseModel):
    """Security-related constraints."""

    authentication: list[str] | None = None
    data_classification: str | None = None
    encryption: dict[str, bool] | None = None  # at_rest, in_transit


class ComplianceConstraints(BaseModel):
    """Compliance-related constraints."""

    frameworks: list[str] | None = None
    data_residency: list[str] | None = None
    retention_days: int | None = None


class OperationalConstraints(BaseModel):
    """Operational constraints."""

    max_replicas: int | None = None
    min_replicas: int | None = None
    deployment_windows: list[str] | None = None


class KubernetesRuntime(BaseModel):
    """Kubernetes deployment info."""

    namespace: str | None = None
    deployment: str | None = None
    service: str | None = None


class AWSRuntime(BaseModel):
    """AWS deployment info."""

    account_id: str | None = None
    region: str | None = None
    arn: str | None = None


class Environment(BaseModel):
    """Runtime environment configuration."""

    otel_service_name: str | None = None
    endpoints: list[str] | None = None
    kubernetes: KubernetesRuntime | None = None
    aws: AWSRuntime | None = None


class FailureModeThresholds(BaseModel):
    """Thresholds for failure mode detection."""

    warning_ms: int | None = None
    critical_ms: int | None = None


class SecurityExtension(BaseModel):
    """OpenC2-inspired security capability metadata.
    
    Used to describe what actions a security tool supports,
    enabling SOAR autodiscovery of security controls.
    """

    actuator_profile: str | None = None  # e.g., "edr", "siem", "slpf"
    actions: list[str] = []              # e.g., "query", "contain", "deny"
    targets: list[str] = []              # e.g., "device", "ipv4_net", "file"


# ============================================================================
# Top-Level Types
# ============================================================================


class Classification(BaseModel):
    """System classification metadata."""

    tier: int | None = Field(None, ge=1, le=5)
    domain: str | None = None
    tags: list[str] | None = None


class System(BaseModel):
    """Core system identification."""

    urn: str = Field(..., pattern=r"^urn:scp:[a-z0-9-]+(:[a-z0-9-]+)?$")
    name: str
    description: str | None = None
    version: str | None = None
    classification: Classification | None = None


class Ownership(BaseModel):
    """Team ownership and contact information."""

    team: str
    contacts: list[Contact] | None = None
    escalation: list[str] | None = None


class Capability(BaseModel):
    """A capability provided by the system."""
    
    model_config = {"populate_by_name": True}

    capability: str
    type: Literal["rest", "grpc", "graphql", "event", "data", "stream"]
    contract: Contract | None = None
    sla: SLA | None = None
    topics: list[str] | None = None  # For event types
    x_security: SecurityExtension | None = Field(None, alias="x-security")


class Dependency(BaseModel):
    """A dependency on another system."""

    system: str = Field(..., pattern=r"^urn:scp:[a-z0-9-]+(:[a-z0-9-]+)?$")
    capability: str | None = None
    type: Literal["rest", "grpc", "graphql", "event", "data", "stream"]
    criticality: Literal["required", "degraded", "optional"]
    failure_mode: Literal["fail-fast", "circuit-break", "fallback", "queue-buffer", "retry"] | None = None
    timeout_ms: int | None = None
    retry: RetryConfig | None = None
    circuit_breaker: CircuitBreakerConfig | None = None
    topics: list[str] | None = None
    access: Literal["read", "write", "read-write"] | None = None


class Constraints(BaseModel):
    """System constraints."""

    security: SecurityConstraints | None = None
    compliance: ComplianceConstraints | None = None
    operational: OperationalConstraints | None = None


class Runtime(BaseModel):
    """Runtime environment configurations."""

    environments: dict[str, Environment] | None = None


class FailureMode(BaseModel):
    """Known failure mode and its characteristics."""

    mode: str
    impact: Literal["total-outage", "partial-outage", "degraded-experience", "data-inconsistency", "silent-failure"]
    detection: str | None = None
    recovery: str | None = None
    degraded_behavior: str | None = None
    mttr_target_minutes: int | None = None
    thresholds: FailureModeThresholds | None = None


# ============================================================================
# Root Model
# ============================================================================


class SCPManifest(BaseModel):
    """Root SCP manifest model.
    
    This represents a complete scp.yaml file.
    """

    scp: str  # Version, e.g., "0.1.0"
    system: System
    ownership: Ownership | None = None
    provides: list[Capability] | None = None
    depends: list[Dependency] | None = None
    constraints: Constraints | None = None
    runtime: Runtime | None = None
    failure_modes: list[FailureMode] | None = None

    @property
    def urn(self) -> str:
        """Convenience accessor for system URN."""
        return self.system.urn

    @property
    def otel_service_name(self) -> str | None:
        """Get the production OTel service name if defined."""
        if self.runtime and self.runtime.environments:
            prod = self.runtime.environments.get("production")
            if prod:
                return prod.otel_service_name
        return None
