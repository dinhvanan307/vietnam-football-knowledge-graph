# A9.1 — Bóng đá chuyên nghiệp Việt Nam trên báo chí trong nước

Mỗi quan hệ gắn với một sự kiện có nguồn. A9.1 có 3.566 nút (1.199 người, 2.300 trận, 67 nút loại khác), 12.749 cạnh, 22 loại, 1.180 URL. Không dùng Wikipedia làm nguồn cho cạnh. Các giải trận đấu là V.League 1, Hạng Nhất, Cúp Quốc gia. Tin ĐTQG nam được giữ; danh sách đội trẻ chỉ tạo quan hệ cầu thủ–CLB khi nguồn cho biết đơn vị chuyên nghiệp. Không lấy tên tỉnh làm bằng chứng về lò đào tạo.

**Cách đọc số liệu:** 2.917 cạnh có bằng chứng trong bài biên tập, 10.834 có bằng chứng từ bảng báo đăng, 1.002 có cả hai. Tức 1.915 chỉ có bài, 9.832 chỉ có bảng. Bảng chuyển nhượng không đồng nghĩa với ký hợp đồng mới. Cầu thủ dự bị không đồng nghĩa đã vào sân. Mốc 2.000 nút có tính trận. Cặp đồng đội là kết quả phân tích riêng, không cộng thêm vào tổng.

## Demo nhanh

Giải nén gói nộp của nhóm rồi mở `Ban_do_bao_chi.html` bằng trình duyệt. Tìm “Nguyễn Văn Quyết”, chọn loại quan hệ và mở URL bằng chứng. Không cần cài đặt. Repo này công bố mã và kết quả tổng hợp; các tệp nhập nằm trong thư mục `graph` của gói nộp kèm báo cáo.

## Khôi phục graph trên máy khác từ gói nộp

Cần Python 3.13, Docker Compose và cổng 7487/7700 trống. Từ gốc repo:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m bongda.press_final.compact check /duong/dan/goi_nop/graph
python -c "import pathlib,secrets; p=pathlib.Path('.env.a91'); f=p.open('x'); p.chmod(0o600); f.write('NEO4J_PASSWORD='+secrets.token_urlsafe(24)+'\n'); f.close()"
docker compose --env-file .env.a91 -f compose.submission.yaml up -d
python -m bongda.press_final.compact restore /duong/dan/goi_nop/graph --env .env.a91
```

Mở [Neo4j Browser](http://localhost:7487/browser/), kết nối `bolt://localhost:7700`, người dùng `neo4j`; dùng mật khẩu trong tệp cấu hình local. Có thể chạy lại lệnh restore. Bản di động bảo toàn nút, cạnh, mốc thời gian, URL, mã bằng chứng và CLB đá chính; bản đầy đủ trên máy nhóm còn có toàn văn sạch, file gốc, trích đoạn và tất cả bằng chứng. Cả hai dùng cùng mã cạnh. [Truy vấn mẫu](../cypher/phan_tich_bao_chi.cypher).

## Dựng và kiểm tra trên kho nguồn đã lưu

Các lệnh sau dành cho máy có bộ dữ liệu local, từ gốc repo. Đầu vào A8 chỉ chứa nguồn báo. `inputs` là bản sao dữ liệu đầu vào đã khóa bằng SQLite backup và bản HTML/JSON; khi thu lại từ web, nội dung có thể thay đổi. Thư mục đích của lệnh build phải mới.

```sh
python -m bongda.press_final.build ../A8_bao_chi ../A9_1_Ban_nop/inputs ../A9_1_Ban_nop/snapshot_thu --version A9.1
python -m bongda.press_final.verify ../A9_1_Ban_nop/snapshot_thu
python -m bongda.press_final.release check ../A9_1_Ban_nop
python -m bongda.press_final.release projection ../A9_1_Ban_nop
python -m bongda.press_final.release explore ../A9_1_Ban_nop
python -m bongda.press_final.analysis ../A9_1_Ban_nop
docker compose --env-file ../A9_1_Ban_nop/.env -f compose.submission.yaml up -d
python -m bongda.press_final.release neo4j ../A9_1_Ban_nop
```

Các module trong `bongda/collect` thu mục lục và tải bài/trang CLB; `bongda/press_final` xử lý nguồn, tên, vai trò, ngày, phiếu đội hình và đối chiếu trích đoạn. Lệnh Neo4j nhập bằng MERGE hai lần và so sánh từng thuộc tính. Trình kiểm tra từ chối CSDL khác; không xóa dữ liệu sẵn có.

## Hai phép đo khác nhau

- **Đồ thị:** [phiếu tổng hợp](../results/a91/precision_graph.json). Lấy đều 200 ID không hoàn lại (seed 17741463); 192 đúng, 8 chưa rõ, 0 bị bác bỏ. Precision bảo thủ 96,00%, Wilson 95% xấp xỉ 92,31–97,96%. Trong 200 ID, 2 từng xuất hiện ở mẫu trước, đều đúng và không dùng để sửa. 198 ID mới xác nhận 190. Một lượt đối chiếu nguồn, chưa có hai người chấm độc lập. Không đảm bảo mỗi loại đạt 90%.
- **NLP nối trận:** lô SGGP thứ hai gồm 36 URL chưa đọc, chấm 35 (25 trận chính, 10 bài âm tính, 1 bài nhiều tâm điểm ngoài đơn vị chấm). So trên cùng lô: luật [cũ](../results/a91/doi_chung_v1.json) tìm 7/25, luật [mới](../results/a91/doi_chung_v2.json) tìm 13/25; cả hai chưa có dương tính giả trên mẫu nhỏ. Mỗi trận cho hai quan hệ CLB→trận. Luật mới là đánh giá tách riêng sau khi đóng A9.1; không nhập lô test vào graph. Chưa có điểm recall chung cho 22 loại.
- Kiểm tra lại: `python -m bongda.press_final.sample ../A9_1_Ban_nop --size 200 --seed 17741463`; `python -m bongda.press_final.score_review ../A9_1_Ban_nop`. Tái lập đối chứng bằng `python -m bongda.press_final.test_articles ../A9_1_Ban_nop/snapshot ../A9_1_Ban_nop/lo_xac_nhan ../A9_1_Ban_nop/qa/xac_nhan --v2` (bỏ `--v2` để chạy bản cũ).

## Bằng chứng và giới hạn

[Thống kê](../results/a91/stats.json) · [Kiểm tra nguồn](../results/a91/integrity.json) · [Hai lượt nhập](../results/a91/neo4j_check.json) · [Dựng lại](../results/a91/rebuild_check.json) · [Đồng đội đá chính](../results/a91/projection.json). Giữ riêng các phiên bản lịch sử: [A8 chỉ báo](bao-chi.md), [A7 báo + Wikipedia](a7.md). Một số trang dùng tên CLB hiện tại cho trận cũ; cầu thủ trùng tên, cách viết tên không dấu, mã nhà cung cấp và nguồn thống kê chung vẫn có thể gây lỗi.
