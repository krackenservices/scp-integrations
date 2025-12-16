# SCP Integrations - Monorepo

Unified tooling for the **System Capability Protocol** (SCP). This monorepo contains the core scanner/graph builder and integration plugins.

> **Note**: The [SCP specification](https://github.com/krackenservices/scp-definition) is maintained separately.

## Packages

### [constructor](./packages/constructor)
**Core tool for architecture definition and graph building**

Scan repositories for `scp.yaml` manifests, validate them, build dependency graphs, and export to various formats (JSON, Mermaid, Neo4j).

```bash
uv run scp-cli scan ./repos --export mermaid
```

## Quick Start

```bash
# Install all dependencies
make setup

# Scan repositories for scp.yaml files
make scan DIR=/path/to/repos

# Or use the CLI directly
uv run scp-cli scan /path/to/repos --export json -o graph.json
```

## Makefile Commands

Run `make help` to see all available commands

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
```

## What is SCP?

The **System Capability Protocol** provides a declarative manifest format (`scp.yaml`) that describes what a system *should* be, complementing OpenTelemetry's view of what *is happening*.

This enables:
- **LLM Reasoning**: Change impact analysis and migration planning
- **Architecture Discovery**: Auto-generate org-wide system maps
- **Theory vs Reality**: Diff declared dependencies against OTel traces
- **Smart Alerting**: Auto-enrich alerts with ownership and blast radius

See [scp-definition](https://github.com/krackenservices/scp-definition) for the complete specification.

## Development

This is a Python monorepo managed with `uv`. Each package can be developed independently:

```bash
# Work on constructor
cd packages/constructor
uv sync
uv run pytest
```

## License

MIT

