// Chạy từng câu. Chọn tên mới cho từng snapshot.
// Mỗi cặp người–CLB có bằng chứng đăng ký đội hình mùa giải hoặc thi đấu được tính một lần.
MATCH (p:Entity:Person)-[r:THI_DAU_CHO|DANG_KY_THI_DAU_CHO]->(c:Entity:Club)
WHERE r.status='accepted'
WITH DISTINCT p,c
WITH gds.graph.project('d22_aff_rc01',p,c,{sourceNodeLabels:'Person',targetNodeLabels:'Club',relationshipType:'AFFILIATED'},{undirectedRelationshipTypes:['*']}) AS g
RETURN g.graphName AS graph, g.nodeCount AS nodes, g.relationshipCount AS projected_relationships;
CALL gds.degree.stream('d22_aff_rc01') YIELD nodeId,score
WITH gds.util.asNode(nodeId) AS c,score WHERE c:Club
RETURN c.entity_id AS id,c.name AS club,score ORDER BY score DESC,id;
MATCH (p:Entity:Person)-[r:THI_DAU_CHO|DANG_KY_THI_DAU_CHO]->(c:Entity:Club)
WHERE r.status='accepted'
RETURN c.entity_id AS id,c.name AS club,count(DISTINCT p.entity_id) AS degree_check
ORDER BY degree_check DESC,id;
