"""Neo4j graph builder for SCP architecture data."""

from dataclasses import dataclass

from neo4j import GraphDatabase

from .models import SCPManifest


@dataclass
class GraphStats:
    """Statistics from a graph sync operation."""
    
    systems_created: int = 0
    systems_updated: int = 0
    capabilities_created: int = 0
    teams_created: int = 0
    dependencies_created: int = 0
    provides_edges: int = 0
    owns_edges: int = 0


class Neo4jGraph:
    """Neo4j graph builder for SCP architecture data.
    
    Creates and maintains a graph database with:
    - System nodes
    - Capability nodes  
    - Team nodes
    - DEPENDS_ON, PROVIDES, OWNS relationships
    """
    
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """Initialize the Neo4j connection.
        
        Args:
            uri: Neo4j connection URI (e.g., bolt://localhost:7687)
            user: Database username
            password: Database password
            database: Database name (default: neo4j)
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
    
    def close(self):
        """Close the database connection."""
        self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def setup_constraints(self):
        """Create database constraints and indexes."""
        queries = [
            "CREATE CONSTRAINT system_urn IF NOT EXISTS FOR (s:System) REQUIRE s.urn IS UNIQUE",
            "CREATE CONSTRAINT capability_id IF NOT EXISTS FOR (c:Capability) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT team_id IF NOT EXISTS FOR (t:Team) REQUIRE t.id IS UNIQUE",
            "CREATE INDEX otel_idx IF NOT EXISTS FOR (s:System) ON (s.otel_service_name)",
        ]
        
        with self.driver.session(database=self.database) as session:
            for query in queries:
                session.run(query)
    
    def sync_manifest(self, manifest: SCPManifest, source: str | None = None) -> GraphStats:
        """Sync an SCP manifest to the graph database.
        
        Uses MERGE operations for idempotent updates.
        
        Args:
            manifest: The SCP manifest to sync
            source: Optional source identifier (repo path, file path)
            
        Returns:
            Statistics about the sync operation
        """
        stats = GraphStats()
        
        with self.driver.session(database=self.database) as session:
            # Create/update the system node
            result = session.run("""
                MERGE (s:System {urn: $urn})
                ON CREATE SET
                    s.name = $name,
                    s.description = $description,
                    s.version = $version,
                    s.tier = $tier,
                    s.domain = $domain,
                    s.otel_service_name = $otel_service_name,
                    s.source = $source,
                    s.created_at = datetime(),
                    s.updated_at = datetime()
                ON MATCH SET
                    s.name = $name,
                    s.description = $description,
                    s.version = $version,
                    s.tier = $tier,
                    s.domain = $domain,
                    s.otel_service_name = $otel_service_name,
                    s.source = $source,
                    s.updated_at = datetime()
                RETURN s.urn AS urn, 
                       CASE WHEN s.created_at = s.updated_at THEN 'created' ELSE 'updated' END AS action
            """, {
                "urn": manifest.system.urn,
                "name": manifest.system.name,
                "description": manifest.system.description,
                "version": manifest.system.version,
                "tier": manifest.system.classification.tier if manifest.system.classification else None,
                "domain": manifest.system.classification.domain if manifest.system.classification else None,
                "otel_service_name": manifest.otel_service_name,
                "source": source,
            })
            
            record = result.single()
            if record["action"] == "created":
                stats.systems_created += 1
            else:
                stats.systems_updated += 1
            
            # Create team and OWNS relationship
            if manifest.ownership:
                session.run("""
                    MERGE (t:Team {id: $team_id})
                    ON CREATE SET t.name = $team_id
                    WITH t
                    MATCH (s:System {urn: $system_urn})
                    MERGE (t)-[r:OWNS]->(s)
                    ON CREATE SET r.created_at = datetime()
                """, {
                    "team_id": manifest.ownership.team,
                    "system_urn": manifest.system.urn,
                })
                stats.teams_created += 1  # May be existing, but we count attempts
                stats.owns_edges += 1
            
            # Create capabilities and PROVIDES relationships
            if manifest.provides:
                for cap in manifest.provides:
                    cap_id = f"{manifest.system.urn}:{cap.capability}"
                    
                    session.run("""
                        MERGE (c:Capability {id: $cap_id})
                        ON CREATE SET
                            c.name = $name,
                            c.type = $type,
                            c.availability = $availability,
                            c.latency_p99_ms = $latency_p99
                        WITH c
                        MATCH (s:System {urn: $system_urn})
                        MERGE (s)-[r:PROVIDES]->(c)
                        ON CREATE SET
                            r.sla_availability = $availability,
                            r.sla_latency_p99_ms = $latency_p99
                    """, {
                        "cap_id": cap_id,
                        "name": cap.capability,
                        "type": cap.type,
                        "availability": cap.sla.availability if cap.sla else None,
                        "latency_p99": cap.sla.latency_p99_ms if cap.sla else None,
                        "system_urn": manifest.system.urn,
                    })
                    stats.capabilities_created += 1
                    stats.provides_edges += 1
            
            # Create DEPENDS_ON relationships
            if manifest.depends:
                for dep in manifest.depends:
                    # Ensure target system exists as a stub
                    session.run("""
                        MERGE (target:System {urn: $target_urn})
                        ON CREATE SET target.name = $target_urn
                    """, {"target_urn": dep.system})
                    
                    # Create dependency edge
                    session.run("""
                        MATCH (from:System {urn: $from_urn})
                        MATCH (to:System {urn: $to_urn})
                        MERGE (from)-[r:DEPENDS_ON]->(to)
                        ON CREATE SET
                            r.capability = $capability,
                            r.type = $type,
                            r.criticality = $criticality,
                            r.failure_mode = $failure_mode,
                            r.timeout_ms = $timeout_ms,
                            r.declared = true,
                            r.created_at = datetime()
                        ON MATCH SET
                            r.capability = $capability,
                            r.type = $type,
                            r.criticality = $criticality,
                            r.failure_mode = $failure_mode,
                            r.timeout_ms = $timeout_ms,
                            r.declared = true,
                            r.updated_at = datetime()
                    """, {
                        "from_urn": manifest.system.urn,
                        "to_urn": dep.system,
                        "capability": dep.capability,
                        "type": dep.type,
                        "criticality": dep.criticality,
                        "failure_mode": dep.failure_mode,
                        "timeout_ms": dep.timeout_ms,
                    })
                    stats.dependencies_created += 1
        
        return stats
    
    def sync_manifests(self, manifests: list[tuple[SCPManifest, str | None]]) -> GraphStats:
        """Sync multiple manifests to the graph.
        
        Args:
            manifests: List of (manifest, source) tuples
            
        Returns:
            Combined statistics
        """
        total_stats = GraphStats()
        
        for manifest, source in manifests:
            stats = self.sync_manifest(manifest, source)
            total_stats.systems_created += stats.systems_created
            total_stats.systems_updated += stats.systems_updated
            total_stats.capabilities_created += stats.capabilities_created
            total_stats.teams_created += stats.teams_created
            total_stats.dependencies_created += stats.dependencies_created
            total_stats.provides_edges += stats.provides_edges
            total_stats.owns_edges += stats.owns_edges
        
        return total_stats
    
    def get_all_systems(self) -> list[dict]:
        """Get all systems from the graph."""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (s:System)
                OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep:System)
                RETURN s.urn AS urn, s.name AS name, s.tier AS tier, 
                       s.domain AS domain, collect(dep.urn) AS dependencies
                ORDER BY s.tier, s.name
            """)
            return [dict(record) for record in result]
    
    def get_blast_radius(self, system_urn: str, depth: int = 3) -> list[dict]:
        """Get systems that depend on the given system (blast radius).
        
        Args:
            system_urn: URN of the system to analyze
            depth: Maximum traversal depth
            
        Returns:
            List of dependent systems
        """
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                MATCH (s:System {urn: $urn})<-[:DEPENDS_ON*1..$depth]-(dependent:System)
                RETURN DISTINCT dependent.urn AS urn, dependent.name AS name, 
                       dependent.tier AS tier, dependent.domain AS domain
                ORDER BY dependent.tier
            """, {"urn": system_urn, "depth": depth})
            return [dict(record) for record in result]
