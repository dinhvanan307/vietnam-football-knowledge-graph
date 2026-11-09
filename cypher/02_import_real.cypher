CREATE CONSTRAINT d22_entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE;

LOAD CSV WITH HEADERS FROM 'file:///real/entities.csv' AS x
MERGE (n:Entity {entity_id:x.entity_id})
SET n.name=x.canonical_name, n.kind=x.type, n.role=x.role
SET n:$(x.type);

LOAD CSV WITH HEADERS FROM 'file:///real/facts.csv' AS f
WITH f WHERE f.status='accepted' AND f.relation_type IN ['THI_DAU_CHO', 'DAN_DAT', 'KY_HOP_DONG_VOI', 'GIA_HAN_VOI', 'THANH_LY_VOI', 'DUOC_CHO_MUON_DEN', 'DUOC_TRIEU_TAP_VAO', 'KY_LUAT', 'TAI_TRO', 'CHU_TICH_CUA', 'THAM_GIA_GIAI', 'TO_CHUC_GIAI', 'SU_DUNG_SAN_NHA', 'DANG_KY_THI_DAU_CHO', 'GHI_BAN_VAO_LUOI', 'NHAN_THE_VANG_KHI_GAP', 'DOI_DAU', 'DOI_TRUONG_CUA', 'THI_DAU_TAI_SAN']
MATCH (s:Entity {entity_id:f.src_id}), (o:Entity {entity_id:f.dst_id})
MERGE (s)-[r:$(f.relation_type) {fact_id:f.fact_id}]->(o)
SET r.status=f.status, r.period=f.period, r.event_key=f.event_key, r.method=f.method,
    r.evidence_id=f.evidence_id, r.article_id=f.article_id, r.article_url=f.article_url, r.quote=f.quote;
