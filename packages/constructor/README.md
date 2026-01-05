# SCP Constructor

Build architecture graphs from `scp.yaml` files. Scan local directories or GitHub organizations, validate manifests, sync to Neo4j, and export to JSON, Mermaid, or OpenC2 actuator profiles.

## Installation

```bash
uv sync
```

## Usage

### Validate SCP Files

```bash
uv run scp-cli validate ./examples
```

### Scan Local Directory

```bash
# Scan and export to Mermaid
uv run scp-cli scan ./path/to/repos --export mermaid

# Scan and export to JSON
uv run scp-cli scan ./path/to/repos --export json -o graph.json

# Scan and export OpenC2 actuator profile (for SOAR)
uv run scp-cli scan ./path/to/repos --export openc2 -o actuators.json
```

### Transform JSON to Other Formats

```bash
# Scan once, transform many
uv run scp-cli scan ./repos --export json -o graph.json
uv run scp-cli transform graph.json --export mermaid -o diagram.mmd
uv run scp-cli transform graph.json --export openc2 -o actuators.json
```

### Scan GitHub Organization

```bash
export GITHUB_TOKEN=ghp_xxx
uv run scp-cli scan-github myorg --export mermaid
```

### Sync to Neo4j

```bash
# Export directly to Neo4j
uv run scp-cli scan ./repos --export neo4j --neo4j-uri bolt://localhost:7687

# Or use environment variables
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password

uv run scp-cli scan ./repos --export neo4j
```

## Commands

| Command | Description |
|---------|-------------|
| `scp-cli validate <path>` | Validate SCP files |
| `scp-cli scan <path>` | Scan local directory |
| `scp-cli scan-github <org>` | Scan GitHub org |
| `scp-cli transform <json>` | Transform JSON to other formats |
| `scp-cli version` | Show version |

## Export Formats

- **JSON**: Graph with nodes/edges arrays
- **Mermaid**: Flowchart diagram with tier styling
- **OpenC2**: Actuator profile for SOAR integration
- **Neo4j**: Direct sync to Neo4j graph database

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub PAT for org scanning |
| `NEO4J_URI` | Neo4j connection URI |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |

