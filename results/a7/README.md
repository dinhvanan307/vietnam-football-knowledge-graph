# Nghiệm thu A7

**Đạt kiểm tra** về precision quan sát trên mẫu cho cả bốn loại quan hệ. Kết quả gộp là 85 dự đoán đúng, 4 sai và 28 bỏ sót. Trong 22 dự đoán tài trợ, có 20 đúng khi sử dụng tên tương đương của doanh nghiệp đã khóa trước lúc chấm. Nếu so nguyên chuỗi ID tạm thì có 19 đúng. Một bài về danh sách tuyển đóng góp 36 kết quả triệu tập đúng.

- [Phiếu đối chiếu theo bài và loại quan hệ](doi_chieu.tsv)
- [Precision, recall và F1 trên mẫu nghiệm thu](nghiem_thu.json)
- [Số nút, cạnh, loại quan hệ và nguồn chính](thong_ke.json)
- [Đối chiếu 188 đoạn bằng chứng từ 73 bài báo](kiem_doi_nguon.json)
- [Biên bản hai lần nhập Neo4j](neo4j_check.json)

Chạy `python3.13 -m bongda verify-a7` từ gốc repo để tái lập các số liệu kiểm tra. [Hướng dẫn](../../docs/a7.md)
