# Mạng cầu thủ, huấn luyện viên và CLB bóng đá Việt Nam

Đề tài 22 dùng tin thể thao trong nước và Wikipedia để nối thực thể bằng các quan hệ có hướng. Mỗi cạnh được chấp nhận có mã `fact_id`, hai đầu mút, loại quan hệ, khóa sự kiện và bằng chứng truy về phiên bản nguồn. Ví dụ, cầu thủ đăng ký cho một CLB theo mùa và cầu thủ ghi bàn vào lưới đối thủ trong một trận là hai loại cạnh khác nhau.

| Kết quả A3 | Giá trị |
|---|---:|
| Nút có kết nối | 2.061 |
| Cạnh có bằng chứng | 18.156 |
| Loại quan hệ | 17 |
| Cạnh từ luật NLP trên tin báo đã rà soát | 30 |
| Cạnh từ đội hình, biên bản trận và bảng nhân sự Wikipedia | 18.126 |
| Precision toàn mạng ước lượng từ 300 cạnh | 96,39% |
| Cận dưới một phía 95% | 92,65% |

Phân bố theo loại nút, quan hệ và phương pháp nằm trong [thống kê A3](ket_qua/thong_ke_a3.json). Các số liệu mô tả tập nguồn nhóm đã thu.

## 1. Kiểm tra nhanh sau khi clone

Các lệnh dưới đây dùng shell trên macOS hoặc Linux. Phần kiểm tra nhanh chỉ cần Git và Python 3.13. Từ thư mục cha nơi bạn muốn lưu repo, chạy:

```sh
git clone https://github.com/dinhvanan307/vietnam-football-knowledge-graph.git
cd vietnam-football-knowledge-graph
python3.13 danh_gia_toan_bo_a3/kiem_tra_cong_khai.py
python3.13 ban_giao.py check example --graph --demo
```

Lệnh đầu sau khi vào repo dựng lại mẫu từ 18.156 mã cạnh rồi tính lại precision. Lệnh cuối kiểm tra bộ ví dụ giả lập gồm 2 nút và 1 cạnh. Các kết quả kỳ vọng của phép đánh giá:

| Tầng lấy mẫu | Số cạnh trong tầng | Cạnh đúng trong mẫu |
|---|---:|---:|
| Mẫu mới giữ lại sau sửa A3 | 16.782 | 193/200 |
| Phần ngoài khung mẫu trên | 1.374 | 95/100 |

Có tổng cộng 288 nhãn đúng, 8 sai và 4 chưa rõ. Mỗi nhãn sai hoặc chưa rõ tính 0. Ước lượng toàn mạng lấy precision mỗi tầng nhân với tỷ trọng cạnh của tầng. Cận dưới dùng phân phối siêu bội khi lấy mẫu không hoàn lại, với hiệu chỉnh Bonferroni cho hai tầng. Cận dưới 92,65% vượt ngưỡng yêu cầu 90%. Các nhãn do Codex đối chiếu nguồn. Nhóm chưa có lượt chấm độc lập của hai người. Phép đo áp dụng cho precision của cạnh đã trích xuất, chưa đo recall hoặc F1.

- [Phiếu 300 cạnh](ket_qua/nhan_300.tsv) có chủ thể, quan hệ, đối tượng, thời gian, nhãn và URL để giảng viên tự xem nguồn.
- [Khung lấy mẫu](ket_qua/khung_a3.tsv) chứa mã cạnh và tầng. Hai seed theo thứ tự bảng là `2026110803` và `2026110804`.
- [Kết quả đánh giá](ket_qua/precision_a3.json) ghi số đếm, ước lượng, cận dưới và checksum mẫu.

## 2. Chuẩn bị dữ liệu và môi trường cho bản đầy đủ

Để dựng A3, kiểm tra đoạn bằng chứng và nhập toàn mạng, cần Python 3.13, các gói bàn giao riêng của nhóm và Docker có Compose v2. Repo công khai có mã, dữ liệu ví dụ, khung mẫu và kết quả. Các gói riêng giữ HTML, wikitext, đoạn bằng chứng và phiếu chi tiết.

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip check
```

Trên máy mới, tập hợp năm ZIP bên dưới vào một thư mục. Đặt `DATA_DIR` thành đường dẫn đến thư mục đó rồi chạy từ gốc repo. Trong bàn giao gốc của nhóm, `Danh_gia_precision_A2.zip` nằm trong thư mục con `Mau_ban_giao_A/`; cũng có thể truyền trực tiếp đường dẫn đó làm đối số.

```sh
DATA_DIR="/duong/dan/den/nam-goi-ban-giao"
python khoi_phuc_goi.py \
  "$DATA_DIR/Ban_giao_A2_2026-11-08.zip" \
  "$DATA_DIR/Ban_giao_A3_2026-11-08.zip" \
  "$DATA_DIR/Danh_gia_precision_A2.zip" \
  "$DATA_DIR/Danh_gia_precision_A3.zip" \
  "$DATA_DIR/Danh_gia_toan_bo_A3.zip"
```

Công cụ xác thực SHA-256 của từng ZIP, khôi phục đúng các file đầu vào cần dùng và báo lỗi nếu một file local có nội dung khác. Riêng bước nhập Neo4j ở mục 4 chỉ cần gói `Ban_giao_A3_2026-11-08.zip`.

## 3. Dựng lại và đối chiếu A3

```sh
python tao_a3.py work/a3_rebuild
python kiem_tra_delta_a3.py work/a3_rebuild
python kiem_tra_a2.py work/a3_rebuild --require-target
cmp work/a3_rebuild/entities.csv work/a3_final/entities.csv
cmp work/a3_rebuild/facts.csv work/a3_final/facts.csv
cmp work/a3_rebuild/evidence.jsonl work/a3_final/evidence.jsonl
```

`tao_a3.py` đọc snapshot A2 đã khóa, áp dụng các quy tắc sửa cùng loại lỗi và ghi sang một thư mục đích mới. Chọn tên đích khác cho lần dựng tiếp theo. Kiểm tra delta truy nguyên bốn cạnh sai ban đầu cùng các cạnh liên quan. Lệnh kiểm tra tiếp theo đối chiếu bằng chứng, đếm thực thể, cạnh và loại quan hệ. Các lệnh `cmp` trả mã 0 và không in gì khi kết quả trùng khớp.

Để tái lập cả **bước mở rộng A2** từ dữ liệu nguồn lưu local, chạy thêm:

```sh
python khoi_phuc_nguon_a2.py
python doc_bien_ban.py
python mo_rong_a.py work/a2_rebuild
python kiem_tra_a2.py work/a2_rebuild --require-target
cmp work/a2_rebuild/facts.csv work/a2_final/facts.csv
```

## 4. Nhập Neo4j hai lần

Ở lần cài đầu, tạo mật khẩu riêng bằng lệnh dưới đây. Lệnh tạo mới `.env` đúng một lần. Giữ file này cùng volume Neo4j để có thể kết nối ở những lần chạy sau.

```sh
(umask 077 && python -c 'from pathlib import Path; import secrets; f = Path(".env").open("x"); f.write("NEO4J_PASSWORD=" + secrets.token_hex(24) + "\n"); f.close()')
mkdir -p work/a3_import
docker compose -f compose.a3.yaml up -d --wait
python nhap_neo4j_a3.py work/a3_final
python kiem_tra_neo4j_a3.py A3
```

Script nhập hai lượt bằng `MERGE`, kiểm từng nút, cạnh và thuộc tính, rồi tính SHA-256 của nội dung Neo4j. Trên cơ sở dữ liệu trống, lượt đầu tạo 2.061 nút và 18.156 cạnh. Lượt hai tạo thêm 0 nút và 0 cạnh. Cả hai lượt có 17 loại quan hệ và cùng SHA-256 `79750950cfd4bcb95775c6dbf025ee541873fb0cbd38d6d41319978ee7a65794`. Kết quả chạy lại nằm trong `work/a3_final/neo4j_recheck.json` khi thư mục đã có biên bản gốc.

Mở Neo4j Browser ở [localhost:7476](http://localhost:7476), kết nối Bolt tại `bolt://127.0.0.1:7689`, tên đăng nhập `neo4j`, mật khẩu trong `.env`. Dùng truy vấn sau để xem một cầu thủ, CLB và nguồn đăng ký thi đấu theo mùa:

```cypher
MATCH (p:Person)-[r:DANG_KY_THI_DAU_CHO]->(c:Club)
RETURN p.name AS cau_thu, c.name AS clb, r.period AS mua,
       r.article_url AS nguon, r.quote AS bang_chung
ORDER BY cau_thu, mua LIMIT 10;
```

Có thêm [truy vấn đếm và kiểm tra trùng cạnh](cypher/03_dem.cypher) và [truy vấn degree người–CLB](cypher/04_degree.cypher). Để dừng dịch vụ và giữ dữ liệu, chạy `docker compose -f compose.a3.yaml down`.

## 5. Tái lập đánh giá từ bằng chứng gốc

Sau khi khôi phục các gói ở mục 2, chạy theo thứ tự:

```sh
python danh_gia_precision/chuan_bi_doi_chieu.py
python danh_gia_precision_a3/chuan_bi.py
python danh_gia_precision_a3/tinh_ket_qua.py
python danh_gia_toan_bo_a3/chuan_bi_ngoai.py
python danh_gia_toan_bo_a3/tinh_toan_bo.py
cmp danh_gia_toan_bo_a3/ket_qua_toan_bo.json ket_qua/precision_a3.json
```

Bước A2 xác định các cạnh đã xem trước khi sửa. Bước A3 dựng lại khung lấy mẫu, kiểm phiên bản nguồn, vị trí đoạn trích và ghép đúng nhãn đã khóa cho từng mã cạnh. File `danh_gia_toan_bo_a3/doi_chieu_300_canh.tsv` chứa đủ bằng chứng và lý do chấm để hai thành viên có thể rà lại.

## 6. Mã xử lý và thu thập

| Công đoạn | Mã chính |
|---|---|
| Lấy báo Thanh Niên, Tuổi Trẻ từ danh sách URL, lưu HTML và văn bản sạch | [thu_bao_mau.py](thu_bao_mau.py), [templates/](templates/) |
| Lấy hồ sơ và trang mùa giải Wikipedia, giữ pageid và revid | [thu_wiki.py](thu_wiki.py), [thu_mua_giai.py](thu_mua_giai.py), [doi_hinh_lich_su.py](doi_hinh_lich_su.py) |
| Gom tin theo sự kiện, nhận diện thực thể bằng từ điển/bí danh, đề xuất quan hệ bằng luật theo hướng và lọc qua phiếu rà | [gom_su_kien.py](gom_su_kien.py), [dong_goi_pilot.py](dong_goi_pilot.py), [trich_quan_he.py](trich_quan_he.py) |
| Đọc bảng đội hình, nhân sự và biên bản trận, hợp nhất thực thể, tạo cạnh và định vị bằng chứng | [doc_bien_ban.py](doc_bien_ban.py), [nhan_su_mua_giai.py](nhan_su_mua_giai.py), [mo_rong_a.py](mo_rong_a.py) |
| Sửa theo lớp lỗi A2 và truy nguyên thay đổi | [quy_tac_a3.py](quy_tac_a3.py), [tao_a3.py](tao_a3.py), [kiem_tra_delta_a3.py](kiem_tra_delta_a3.py) |
| Nhập idempotent và xác minh toàn bộ thuộc tính | [nhap_neo4j_a3.py](nhap_neo4j_a3.py), [Cypher nhập](cypher/02_import_real.cypher) |

Ví dụ thu một lô tin mới từ URL công khai:

```sh
scrapy runspider thu_bao_mau.py -a seeds=templates/seeds_pilot.tsv -a out=work/bao_moi
```

Spider kiểm tra `robots.txt`, lưu kết quả vào thư mục mới và ghi URL lỗi vào `errors.tsv`. Nội dung trên web có thể thay đổi theo thời gian. Các mục 3–5 dùng bản nguồn đã khóa của nhóm để tái lập số liệu trong báo cáo.
