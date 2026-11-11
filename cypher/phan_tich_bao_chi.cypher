// 1. Số nút theo loại.
MATCH (n:Entity) RETURN n.kind AS loai, count(*) AS so_nut ORDER BY so_nut DESC;
// 2. Cơ cấu cạnh.
MATCH ()-[r]->() RETURN type(r) AS quan_he, count(*) AS so_canh ORDER BY so_canh DESC;
// 3. Mở 12 quan hệ và bằng chứng của Văn Quyết.
MATCH p=(n:Person {entity_id:'p-vq'})-[r]-(x)
RETURN p, r.period AS thoi_gian, r.article_url AS bao LIMIT 12;
// 4. Đếm cặp đá chính cho cùng CLB trong cùng trận; hai đối thủ không phải đồng đội.
MATCH (a:Person)-[r:DA_CHINH_TRONG_TRAN]->(m:Match)<-[s:DA_CHINH_TRONG_TRAN]-(b:Person)
WHERE a.entity_id < b.entity_id AND r.club_id = s.club_id
RETURN a.name AS cau_thu_1,b.name AS cau_thu_2,count(DISTINCT m) AS so_tran
ORDER BY so_tran DESC,cau_thu_1,cau_thu_2 LIMIT 10;
// 5. Báo nào xác nhận quan hệ tài trợ?
MATCH (s:Organization)-[r:TAI_TRO]->(c:Club)
RETURN s.name AS doanh_nghiep,c.name AS clb,r.period AS thoi_gian,r.article_url AS nguon LIMIT 10;
