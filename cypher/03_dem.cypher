MATCH (n:Entity)-[r]-(m:Entity) WHERE r.status='accepted'
RETURN count(DISTINCT n.entity_id) AS connected_entities;
MATCH (:Entity)-[r]->(:Entity) WHERE r.status='accepted'
RETURN count(r) AS edge_rows, count(DISTINCT r.fact_id) AS facts, count(DISTINCT type(r)) AS types;
MATCH (:Entity)-[r]->(:Entity) WHERE r.status='accepted'
RETURN type(r) AS relation, count(*) AS rows, count(DISTINCT r.fact_id) AS facts ORDER BY facts DESC;
MATCH (:Entity)-[r]->(:Entity) WHERE r.status='accepted'
WITH r.fact_id AS f,count(*) AS n WHERE f IS NULL OR n<>1 RETURN f,n;
MATCH (:Entity)-[r]->(:Entity) WHERE r.status='accepted' AND (r.evidence_id IS NULL OR trim(r.evidence_id)='')
RETURN r.fact_id AS no_evidence_pointer;
