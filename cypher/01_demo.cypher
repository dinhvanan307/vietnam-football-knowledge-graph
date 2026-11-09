LOAD CSV WITH HEADERS FROM 'file:///example/entities.csv' AS row
MERGE (n:FixtureEntity {entity_id:row.entity_id}) SET n.name=row.canonical_name;
LOAD CSV WITH HEADERS FROM 'file:///example/facts.csv' AS row
MATCH (p:FixtureEntity {entity_id:row.src_id}), (c:FixtureEntity {entity_id:row.dst_id})
MERGE (p)-[r:GIA_HAN_VOI {fact_id:row.fact_id}]->(c)
SET r.evidence_id=row.evidence_id, r.method='fixture';
MATCH (n:FixtureEntity) RETURN count(n) AS fixture_nodes;
MATCH (:FixtureEntity)-[r]->(:FixtureEntity) RETURN count(r) AS fixture_edges;
