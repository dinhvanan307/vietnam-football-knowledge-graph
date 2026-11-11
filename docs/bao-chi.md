# A8 · Quan hệ bóng đá từ báo chí trong nước

A8 dùng bằng chứng từ 147 bài đăng trên 10 tên miền báo chí. Mỗi cạnh có URL và trích đoạn gắn với văn bản đã lưu. CSDL có 468 nút, 858 cạnh và 13 loại. Còn thiếu 1.532 nút và 4.142 cạnh so với yêu cầu môn học.

## Chạy lại từ bộ dữ liệu local

Ở thư mục gốc của repo, kích hoạt môi trường Python có các thư viện trong `requirements.lock`. Bộ bàn giao local đặt cạnh repo gồm `../A7_Ban_nop/snapshot` (đầu vào lịch sử), `../A8_bao_chi/thu_bao` (URL hạt giống, manifest và HTML) và `../A8_bao_chi/snapshot` (bản đã đóng). Dùng thư mục mới để so sánh hai lần dựng.

```sh
python -m bongda.press.build ../A7_Ban_nop/snapshot ../A8_bao_chi/thu_bao ../A8_bao_chi/snapshot_rebuild
cmp ../A8_bao_chi/snapshot/facts.csv ../A8_bao_chi/snapshot_rebuild/facts.csv
cmp ../A8_bao_chi/snapshot/entities.csv ../A8_bao_chi/snapshot_rebuild/entities.csv
python -m bongda.press.audit ../A8_bao_chi/snapshot ../A8_bao_chi/mau_100_tao_lai.tsv
python -m bongda.press.visual ../A8_bao_chi/snapshot ../A8_bao_chi/Ban_do_bao_chi.html
```

Để thu lại tài liệu trực tuyến, sao chép `thu_bao/urls.txt` vào thư mục thu mới rồi chạy `python -m bongda.collect.doi_hinh_bao DUONG_DAN_THU_MOI --limit 120`. Các trang có thể thay đổi theo thời gian. Thư mục snapshot dùng bản HTML đã lưu để không phụ thuộc vào phiên bản trang hiện tại.

## Neo4j

Trong bộ bàn giao trên máy, `../A8_bao_chi/.env` đã có mật khẩu local. Khi chuyển sang máy khác, tự tạo tệp đó với một dòng `NEO4J_PASSWORD=mat-khau-rieng-cua-ban`. Giữ kín tệp cấu hình.

```sh
docker compose --env-file ../A8_bao_chi/.env -f compose.press.yaml up -d
python -m bongda.press.import_graph ../A8_bao_chi
```

Mở [Neo4j Browser](http://localhost:7484/browser/), kết nối `bolt://127.0.0.1:7697`, tài khoản `neo4j`. CSDL này có volume riêng. Trình nhập đối chiếu toàn bộ thuộc tính hai lần; lần thứ hai phải tạo 0 nút và 0 cạnh mới.

## Dữ liệu kiểm tra

- `snapshot/stats.json` và `sources_checked.tsv` trong snapshot chứa kết quả đếm và nhật ký 39 bài mới. 34 bài góp 485 cạnh đội hình. Có 571 lượt tên chuyển sang `needs_review.tsv`.
- `mau_100.tsv` được chọn ngẫu nhiên khỏi toàn bộ 858 cạnh với seed 20261111. `mau_100_da_ra.tsv` chứa từng kết luận cùng lý do. Một lượt đối chiếu xác nhận 91/100, còn 9 trường hợp chưa rõ. Khoảng Wilson 95% xấp xỉ 83,8–95,2%. Mẫu chỉ bao phủ 7/13 loại và không đo recall trên bài mới.
- Thư mục `results/press_only` của repo chứa thống kê, kết quả lấy mẫu và biên bản Neo4j dạng tổng hợp. HTML gốc, nội dung nguyên văn, bản đồ có trích dẫn và mật khẩu giữ ở bộ bàn giao local.
