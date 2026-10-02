import re
from neo4j import GraphDatabase

# Regex patterns for parsing edge string and extracting blackboard parameter
EDGE_PATTERN = re.compile(r"^edge\(\s*([^,\s]+)\s*,\s*([^,\s]+)\s*,\s*(.+)\s*\)$")
BLACKBOARD_PATTERN = re.compile(r"^blackboard\(([^)]+)\)$")


def parse_prolog_connections(raw_edges):
    parsed_connections = []

    for item in raw_edges:
        match = EDGE_PATTERN.match(item.strip())
        if match:
            from_service, to_service, edge_type_raw = match.groups()

            bb_match = BLACKBOARD_PATTERN.match(edge_type_raw)
            if bb_match:
                rel_type = "BLACKBOARD"
                param = bb_match.group(1)
            else:
                rel_type = edge_type_raw.upper()  # Standard Neo4j uppercase convention
                param = None

            parsed_connections.append(
                {
                    "from_service": from_service,
                    "to_service": to_service,
                    "rel_type": rel_type,
                    "param": param,
                }
            )

    return parsed_connections


def upload_to_neo4j(prolog_connections, uri, auth):
    connections = parse_prolog_connections(prolog_connections)
    driver = GraphDatabase.driver(uri, auth=auth)

    with driver.session() as session:
        # Create unique constraint on Service name if it doesn't exist
        session.run("MATCH (s1:Service)-[r]-(s2:Service) DETACH DELETE s1, s2")
        session.run(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE"
        )

        for conn in connections:
            # Dynamic relationship types in Cypher require string formatting;
            # service names and parameters are safely passed via parameters.
            cypher = f"""
            MERGE (a:Service {{name: $from_service}})
            MERGE (b:Service {{name: $to_service}})
            MERGE (a)-[r:{conn['rel_type']}]->(b)
            SET r.parameter = $param
            """
            session.run(
                cypher,
                from_service=conn["from_service"],
                to_service=conn["to_service"],
                param=conn["param"],
            )

    driver.close()


# Example usage:
# upload_to_neo4j(parsed_connections, "bolt://localhost:7687", ("neo4j", "your_password"))
