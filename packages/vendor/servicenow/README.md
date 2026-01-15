# ServiceNow CMDB Integration

Sync SCP unified model JSON to ServiceNow Configuration Management Database (CMDB).

## Installation

```bash
cd packages/vendor/servicenow
uv sync
```

## Quick Start

```bash
# Set credentials
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_USERNAME="admin"
export SERVICENOW_PASSWORD="password"

# Sync (uses sensible defaults)
scp-servicenow cmdb sync graph.json
```

**That's it!** The integration works out-of-the-box with sensible defaults. No configuration file needed.

---

## Commands

### `sync` - Sync SCP graph to ServiceNow

```bash
scp-servicenow cmdb sync graph.json [OPTIONS]
```

**Options**:

- `--instance, -i` - ServiceNow instance URL (overrides env var)
- `--ci-class, -c` - CI class to use (default: `cmdb_ci_service_discovered`)
- `--dry-run, -d` - Validate without making changes
- `--config` - Path to custom `cmdb.yaml` config file

**Examples**:

```bash
# Basic sync
scp-servicenow cmdb sync graph.json

# Dry-run
scp-servicenow cmdb sync graph.json --dry-run

# Custom config
scp-servicenow cmdb sync graph.json --config my-cmdb.yaml
```

### `validate` - Validate SCP graph mapping

```bash
scp-servicenow cmdb validate graph.json
```

Checks for mapping issues before syncing.

### `init` - Generate configuration template

```bash
scp-servicenow cmdb init [OPTIONS]
```

Generates a `cmdb.yaml` configuration file with defaults that you can customize.

**Options**:

- `--output, -o` - Output path (default: `cmdb.yaml`)
- `--force, -f` - Overwrite existing file

**Examples**:

```bash
# Generate config template
scp-servicenow cmdb init

# Custom path
scp-servicenow cmdb init --output config/prod-cmdb.yaml
```

---

## Default Field Mappings

**The integration works without configuration using these defaults:**

| SCP Field           | ServiceNow Field        | Notes                                    |
| ------------------- | ----------------------- | ---------------------------------------- |
| `node.id` (URN)     | `correlation_id`        | Unique identifier for idempotent upserts |
| `node.name`         | `name`                  | CI display name                          |
| `node.tier`         | `business_criticality`  | 1→Critical, 2→High, 3→Medium, 4→Low      |
| `node.team`         | `comments`              | Stored in metadata section               |
| `node.domain`       | `comments`              | Stored in metadata section               |
| `node.contacts[]`   | `owned_by` + `comments` | Email→User lookup, others in metadata    |
| `node.escalation[]` | `comments`              | Formatted escalation chain               |
| `edge.DEPENDS_ON`   | `cmdb_rel_ci`           | Relationship: "Depends on::Used by"      |

### Comments Field Format

By default, team, domain, contacts, and escalation are stored in the `comments` field:

```
SCP Metadata:
Team: checkout-team
Domain: payments

Contacts:
  - pagerduty: acmepay-checkout-critical
  - slack: #team-checkout

Escalation Chain:
checkout-team → payments-platform
```

---

## Configuration (Optional)

### When to Use Configuration

Configuration is **OPTIONAL**. Use `cmdb.yaml` if you need to:

- Map SCP fields to custom ServiceNow fields (e.g., `u_business_domain`)
- Customize the comments template format
- Change tier-to-criticality mappings
- Disable email-to-user resolution

### Generate Configuration Template

```bash
scp-servicenow cmdb init
```

This creates `cmdb.yaml` with all defaults. Edit to customize for your instance.

### Example: Using Custom Fields

If your ServiceNow instance has custom fields:

```yaml
# cmdb.yaml
field_mappings:
  name: name
  business_criticality: tier
  u_business_domain: domain # Custom field (must exist in ServiceNow)
  u_support_team: team # Custom field (must exist in ServiceNow)
  comments:
    - contacts
    - escalation
```

> **Note**: Custom fields (`u_*`) must be created in ServiceNow first. See [Creating Custom Fields](#creating-custom-fields).

### Configuration Options

```yaml
# Field mappings
field_mappings:
  name: name # Standard field
  business_criticality: tier # Via tier_mappings
  comments: [team, domain, ...] # List of fields to store in comments

# Tier to criticality mapping
tier_mappings:
  1: "1 - Critical"
  2: "2 - High"
  # ...

# Contact resolution
contact_resolution:
  resolve_email_to_owned_by: true # Try to map email→owned_by
  email_not_found: "warn" # warn, ignore, or error

# CI class
ci_class: "cmdb_ci_service_discovered"

# Comments template (Python format string)
comments_template: |
  SCP Metadata:
  Team: {team}
  Domain: {domain}
  ...
```

---

## Authentication

Set environment variables for ServiceNow credentials:

### Basic Auth (Recommended for Development)

```bash
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_USERNAME="admin"
export SERVICENOW_PASSWORD="password"
```

### OAuth Bearer Token

```bash
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_TOKEN="your-bearer-token"
```

### OAuth Client Credentials

```bash
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_CLIENT_ID="your-client-id"
export SERVICENOW_CLIENT_SECRET="your-client-secret"
```

---

## Creating Custom Fields

To use custom fields like `u_business_domain` or `u_support_team`:

1. Navigate to **System Definition > Tables** in ServiceNow
2. Find table: `cmdb_ci_service_discovered`
3. Add new fields:
   - Column: `u_business_domain`, Type: String, Length: 100
   - Column: `u_support_team`, Type: String, Length: 100
4. Update your `cmdb.yaml` to use these fields
5. Run sync

---

## Complete Example

```bash
# 1. Generate SCP JSON
cd packages/constructor
uv run scp-cli scan /path/to/repos --export json -o /tmp/graph.json

# 2. (Optional) Generate config template
cd ../vendor/servicenow
uv run scp-servicenow cmdb init

# 3. (Optional) Edit config to use custom fields
# vim cmdb.yaml

# 4. Set credentials
export SERVICENOW_INSTANCE="https://dev12345.service-now.com"
export SERVICENOW_USERNAME="admin"
export SERVICENOW_PASSWORD="password"

# 5. Dry-run to validate
uv run scp-servicenow cmdb sync /tmp/graph.json --dry-run

# 6. Sync to ServiceNow
uv run scp-servicenow cmdb sync /tmp/graph.json
```

---

## Troubleshooting

### No configuration file found (Warning)

**This is OK!** The integration works with defaults. Only create `cmdb.yaml` if you need custom mappings.

### Custom field not populated

Verify the field exists in ServiceNow:

1. Check `sys_dictionary` table for your field
2. Ensure field name matches exactly (case-sensitive)
3. Confirm you're using the correct CI table

### Email contact not resolving to owned_by

Check that:

1. Email address matches a ServiceNow user exactly
2. User exists in `sys_user` table
3. `contact_resolution.resolve_email_to_owned_by` is `true` (default)
