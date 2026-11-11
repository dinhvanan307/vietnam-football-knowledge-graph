// Lớp xã hội: cả hai đầu là cá nhân hoặc tổ chức
MATCH (a)-[r]->(b)
WHERE a.kind IN ['Person','Club','Organization','NationalTeam'] AND b.kind IN ['Person','Club','Organization','NationalTeam']
RETURN count(r) AS canh, count(DISTINCT type(r)) AS loai, size(reduce(s=[], x IN collect(DISTINCT a.entity_id) + collect(DISTINCT b.entity_id) | CASE WHEN x IN s THEN s ELSE s + x END)) AS tac_nhan;

// Bối cảnh: ít nhất một đầu là trận, giải hoặc sân
MATCH (a)-[r]->(b)
WHERE a.kind IN ['Match','Competition','Stadium'] OR b.kind IN ['Match','Competition','Stadium']
RETURN count(r) AS canh, count(DISTINCT type(r)) AS loai;

// Các sự kiện cụ thể và nguồn cho bản đồ trong Neo4j Browser
MATCH p=(a)-[r:GIA_HAN_VOI]->(b) RETURN p LIMIT 20;

// Đồng đội suy từ hai vị trí đá chính: cùng đội, cùng trận; đối chiếu danh sách đã xử lý mâu thuẫn trong dong_doi_chung_cu.tsv
MATCH (a:Person)-[r:DA_CHINH_TRONG_TRAN]->(m:Match)<-[s:DA_CHINH_TRONG_TRAN]-(b:Person)
WHERE a.entity_id < b.entity_id AND r.club_id = s.club_id
RETURN a.name AS cau_thu, b.name AS dong_doi, m.name AS tran, r.fact_id AS canh_1, s.fact_id AS canh_2 LIMIT 20;
