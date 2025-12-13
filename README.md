# SCP Integrations - Monorepo

Unified tooling for the **System Capability Protocol** (SCP). This monorepo contains the core scanner/graph builder and Grafana integration plugin.

> **Note**: The [SCP specification](../scp-definition) is maintained separately.

## Packages

### 📐 [constructor](./packages/constructor)
**Core tool for architecture definition and graph building**

Scan repositories for `scp.yaml` manifests, validate them, build dependency graphs, and export to various formats (JSON, Mermaid, Neo4j).

```bash
cd packages/constructor
uv run scp scan ./repos --export mermaid
```

### 🎯 [grafana](./packages/grafana)
**Grafana integration plugin**

Automatically create monitoring dashboards and alerts in Grafana from `scp.yaml` manifests.

```bash
cd packages/grafana
uv run scp-integrations sync ./repos
```

## Quick Start

```bash
# Install dependencies for both packages
cd packages/constructor && uv sync && cd ../..
cd packages/grafana && uv sync && cd ../..

# Scan repositories for scp.yaml files
cd packages/constructor
uv run scp scan /path/to/repos --export json -o graph.json

# Create Grafana dashboards and alerts
cd ../grafana
export GRAFANA_URL=http://localhost:3000
export GRAFANA_API_KEY=your-key
uv run scp-integrations sync /path/to/repos
```

## Architecture

```
SCP Ecosystem
│
├── scp-definition (separate repo)
│   └── Specification, schemas, examples
│
└── scp-integrations (this monorepo)
    │
    ├── constructor (scan → validate → graph)
    │   ├── Local scanner
    │   ├── GitHub scanner
    │   ├── Validator
    │   └── Exporters (JSON, Mermaid, Neo4j)
    │
    └── grafana (monitor → alert)
        ├── Dashboard builder
        ├── Alert generator
        └── Grafana API client
```

## What is SCP?

The **System Capability Protocol** provides a declarative manifest format (`scp.yaml`) that describes what a system *should* be, complementing OpenTelemetry's view of what *is happening*.

This enables:
- **LLM Reasoning**: Change impact analysis and migration planning
- **Architecture Discovery**: Auto-generate org-wide system maps
- **Theory vs Reality**: Diff declared dependencies against OTel traces
- **Smart Alerting**: Auto-enrich alerts with ownership and blast radius

See [scp-definition](../scp-definition) for the complete specification.

## Development

This is a Python monorepo managed with `uv`. Each package can be developed independently:

```bash
# Work on constructor
cd packages/constructor
uv sync
uv run pytest

# Work on grafana integration
cd packages/grafana
uv sync
uv run pytest
```

## License

MIT
