# ServiceNow CMDB Integration

Sync SCP unified model JSON to ServiceNow Configuration Management Database (CMDB).

## Installation

```bash
cd packages/vendor/servicenow-cmdb
uv sync
```

## Usage

### Sync SCP graph to ServiceNow

```bash
scp-servicenow cmdb sync graph.json --instance https://dev12345.service-now.com
```

### Dry-run (validate without making changes)

```bash
scp-servicenow cmdb sync graph.json --instance https://dev12345.service-now.com --dry-run
```

### Validate mapping

```bash
scp-servicenow cmdb validate graph.json
```

## Authentication

Set environment variables for ServiceNow authentication:

```bash
# Basic Auth
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_USERNAME="admin"
export SERVICENOW_PASSWORD="password"

# OAuth Bearer Token
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_TOKEN="your-bearer-token"

# OAuth Client Credentials
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_CLIENT_ID="your-client-id"
export SERVICENOW_CLIENT_SECRET="your-client-secret"
```

## Field Mapping

| SCP Field         | ServiceNow Field       | Notes                                |
| ----------------- | ---------------------- | ------------------------------------ |
| `node.id` (URN)   | `correlation_id`       | Unique identifier for upsert         |
| `node.name`       | `name`                 | CI display name                      |
| `node.tier`       | `business_criticality` | 1→critical, 2→high, 3→medium, 4→low  |
| `node.domain`     | `u_business_domain`    | Custom field (requires setup)        |
| `node.team`       | `support_group`        | Assignment group reference           |
| `node.contacts`   | `owned_by`             | First `email` contact mapped to User |
| `edge.DEPENDS_ON` | `cmdb_rel_ci`          | Relationship: "Depends on::Used by"  |

## CI Class

By default, systems are created as `cmdb_ci_service_discovered` (Application Service) CIs.

## Example

```bash
# Generate SCP JSON from repository scan
cd ../constructor
uv run scp-cli scan /path/to/repos --export json -o /tmp/graph.json

# Sync to ServiceNow
cd ../vendor/servicenow-cmdb
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_USERNAME="admin"
export SERVICENOW_PASSWORD="password"
uv run scp-servicenow cmdb sync /tmp/graph.json
```
