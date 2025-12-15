# SCP Constructor

Build architecture graphs from `scp.yaml` files. Scan local directories or GitHub organizations, validate manifests, sync to Neo4j, and export to JSON or Mermaid diagrams.

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
```

### Scan GitHub Organization

```bash
export GITHUB_TOKEN=ghp_xxx
uv run scp-cli scan-github myorg --export mermaid
```

### Sync to Neo4j

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password

uv run scp-cli scan ./repos
```

## Commands

| Command | Description |
|---------|-------------|
| `scp validate <path>` | Validate SCP files |
| `scp scan <path>` | Scan local directory |
| `scp scan-github <org>` | Scan GitHub org |
| `scp version` | Show version |

## Export Formats

- **JSON**: Graph with nodes/edges arrays
- **Mermaid**: Flowchart diagram with tier styling

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub PAT for org scanning |
| `NEO4J_URI` | Neo4j connection URI |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
