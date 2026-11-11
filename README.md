# Mạng cầu thủ, huấn luyện viên và CLB bóng đá Việt Nam

**Bản hiện tại: [A10 – mạng phân lớp](docs/phan-lop-a10.md).** Toàn đồ thị: 3.585 nút, 12.781 cạnh, 24 loại. Mạng xã hội trực tiếp: 1.103 tác nhân, 2.654 cạnh. [Kết quả A10](results/a10/) · [Cypher](cypher/phan_lop_a10.cypher).

**Bản nền A9.1 (11/11/2026)** sử dụng báo chí thể thao trong nước: **3.566 nút, 12.749 cạnh, 22 loại quan hệ, 1.180 URL**, đã nhập Neo4j hai lần. Có **1.199 người, 2.300 trận, 67 thực thể khác**. Nguồn gồm bài biên tập và bảng dữ liệu do báo đăng. Không dùng Wikipedia làm bằng chứng trong bản nộp. Mẫu 200 cạnh xác nhận **192 đúng (96%), 8 chưa rõ**.

**[Chạy local, mở bản đồ và kiểm tra A9.1](docs/bao-chi-a91.md)** · [Kết quả kiểm tra](results/a91/) · [Truy vấn Neo4j](cypher/phan_tich_bao_chi.cypher). Trên lô thử mới, mô-đun NLP nối trận tìm đúng 13/25 trận, so với 7/25 ở luật cũ. Đây là phép đo riêng.

## Phiên bản lịch sử — không dùng làm số liệu bản nộp

[A8: bản chỉ báo quy mô nhỏ](docs/bao-chi.md). Nội dung sau mô tả bản A7 kết hợp hai loại nguồn và được giữ để tái lập kết quả cũ.

Mỗi cạnh ghi nhận một quan hệ bóng đá và liên kết về bằng chứng trong nguồn. Dự án dùng Python 3.13 để thu thập, trích xuất, đánh giá và dùng Neo4j để lưu đồ thị.

**Bản A7 đạt kiểm tra** trên bốn loại quan hệ trích từ báo thể thao trong nước. Đồ thị có **2.068 nút, 18.261 cạnh và 18 loại quan hệ**. So với A6.3, A7 có thêm 144 cạnh từ 73 bài báo. Trong toàn đồ thị, báo chí là nguồn chính của 371 cạnh và Wikipedia là nguồn chính của 17.890 cạnh.

| Quan hệ trên báo | Đúng / dự đoán | Precision | Recall | Cạnh mới đã nhập |
|---|---:|---:|---:|---:|
| Ký hợp đồng | 12/13 | 92,31% | 52,17% | 33 |
| Triệu tập vào tuyển nam Việt Nam | 41/42 | 97,62% | 83,67% | 50 |
| VFF kỷ luật cầu thủ | 12/12 | 100% | 85,71% | 31 |
| Doanh nghiệp tài trợ CLB | 20/22 | 90,91% | 74,07% | 30 |

Trên các lô nghiệm thu, 85 trong 89 dự đoán đúng, với 28 quan hệ bỏ sót. Ngưỡng áp dụng riêng cho từng loại là precision quan sát trên 90%, ít nhất 5 dự đoán từ ít nhất 3 bài. Mẫu chọn theo chủ đề và được đối chiếu nguồn một lượt. [Kết quả và phiếu A7](results/a7/) · [Hướng dẫn chạy A7](docs/a7.md)

## Kiểm tra ngay sau khi clone

Các lệnh kiểm tra bên dưới chỉ dùng thư viện chuẩn của Python 3.13. Chạy từ gốc repository.

```sh
git clone https://github.com/dinhvanan307/vietnam-football-knowledge-graph.git
cd vietnam-football-knowledge-graph
python3.13 -m bongda verify-a7
python3.13 -m bongda verify
python3.13 -m bongda bundle check examples/graph --graph --demo
```

Lệnh `verify-a7` tính lại kết quả từ phiếu chấm công khai và đối chiếu biên bản nhập Neo4j hai lượt. Lệnh `verify` tái lập kết quả A3. Lệnh `bundle check` kiểm tra ví dụ gồm 2 nút và 1 cạnh. Xem `python3.13 -m bongda --help` để liệt kê các lệnh chính. Các kiểm thử hồi quy có thể chạy bằng `python3.13 -m unittest discover -s tests`. Các bước khôi phục ZIP, dựng lại đồ thị, nhập Neo4j hai lần và chấm kết quả từ phản hồi Gemini đã lưu có trong [hướng dẫn chạy local](docs/chay-local.md).

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| [bongda/core](bongda/core/) | Lược đồ nút và cạnh, hợp đồng dữ liệu và bộ luật NLP pilot |
| [bongda/collect](bongda/collect/) | Spider báo chí, lấy phiên bản Wikipedia, đối chiếu định danh |
| [bongda/extract](bongda/extract/) | Bảng đội hình và nhân sự, biên bản trận, gom bài theo sự kiện |
| [bongda/data](bongda/data/) | Đóng gói pilot, khôi phục snapshot và nguồn từ gói bàn giao |
| [bongda/graph](bongda/graph/) | Mở rộng A2, dựng A3, kiểm tra quy mô và truy nguyên thay đổi |
| [bongda/storage](bongda/storage/) · [cypher](cypher/) | Nhập Neo4j, đối chiếu toàn đồ thị và truy vấn phân tích |
| [bongda/evaluate](bongda/evaluate/) | Lấy mẫu, đọc bằng chứng, tính precision cho A2 và A3 |
| [nlp_bao](nlp_bao/) | Trích và chuẩn hóa quan hệ báo chí qua Gemini API, chấm theo từng bộ ba |
| [templates](templates/) · [examples](examples/) | Bảng đầu vào và dữ liệu giả lập để chạy thử |
| [results](results/) | Số liệu công khai, nhãn và dấu kiểm của từng thí nghiệm |
| `work/` | Snapshot thật, văn bản nguồn, phản hồi API và kết quả chạy trên máy nhóm |

Các đường dẫn `ban_giao.py`, `ontology.py` và `trich_quan_he.py` ở gốc trỏ đến mã trong `bongda/core/`. Các thí nghiệm đã khóa dùng những đường dẫn này để kiểm tra SHA-256 và nạp lại đúng bộ luật pilot.

## Các lượt đánh giá trước A7

- Trên 18 bài với 53 quan hệ thuộc năm loại, lượt Gemini trước sửa đạt precision 66,67%, recall 49,06%. Khi chấm lại cùng phản hồi sau sửa, hai giá trị đạt 84,44% và 71,70%. [Kết quả và đối chiếu từng cạnh](results/press/)
- Riêng quan hệ triệu tập lên tuyển, trên 14 bài mới với 139 quan hệ tham chiếu, precision đạt 83,70% và recall đạt 81,29%, tăng 2,88 điểm phần trăm recall so với bản trước trên đúng lô đó. [Thiết kế và kết quả kiểm tra](results/callups/README.md)
