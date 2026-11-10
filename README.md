# Mạng cầu thủ, huấn luyện viên và CLB bóng đá Việt Nam

Đề tài 22 xây dựng đồ thị có hướng từ tin thể thao trong nước và Wikipedia tiếng Việt. Mỗi cạnh ghi nhận một quan hệ bóng đá và liên kết về bằng chứng trong nguồn. Dự án dùng Python 3.13 để thu thập, trích xuất, đánh giá và dùng Neo4j để lưu đồ thị.

| Kết quả của đồ thị A3 | Giá trị |
|---|---:|
| Nút có kết nối | 2.061 |
| Cạnh có bằng chứng | 18.156 |
| Loại quan hệ | 17 |
| Cạnh từ luật NLP trên báo đã duyệt | 30 |
| Cạnh từ dữ liệu có cấu trúc của Wikipedia | 18.126 |
| Precision ước lượng từ 300 cạnh / cận dưới một phía 95% | 96,39% / 92,65% |

Chi tiết số đếm và mẫu đánh giá nằm trong [kết quả A3](results/a3/). Các nhãn đánh giá do Codex đối chiếu nguồn; nhóm chưa hoàn tất hai lượt chấm độc lập của A/B.

## Kiểm tra ngay sau khi clone

Hai lệnh kiểm tra bên dưới chỉ dùng thư viện chuẩn của Python 3.13. Chạy từ gốc repository.

```sh
git clone https://github.com/dinhvanan307/vietnam-football-knowledge-graph.git
cd vietnam-football-knowledge-graph
python3.13 -m bongda verify
python3.13 -m bongda bundle check examples/graph --graph --demo
```

Lệnh đầu kiểm tra lại hai mẫu và tính precision của A3. Lệnh sau kiểm tra ví dụ gồm 2 nút và 1 cạnh. Xem `python3.13 -m bongda --help` để liệt kê các lệnh chính. Các kiểm thử hồi quy có thể chạy bằng `python3.13 -m unittest discover -s tests`. Các bước khôi phục ZIP, dựng lại đồ thị, nhập Neo4j hai lần và chấm kết quả từ phản hồi Gemini đã lưu có trong [hướng dẫn chạy local](docs/chay-local.md).

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

## Kết quả NLP trên báo chí

- Trên 18 bài với 53 quan hệ thuộc năm loại, lượt Gemini trước sửa đạt precision 66,67%, recall 49,06%. Khi chấm lại cùng phản hồi sau sửa, hai giá trị đạt 84,44% và 71,70%. [Kết quả và đối chiếu từng cạnh](results/press/)
- Riêng quan hệ triệu tập lên tuyển, trên 14 bài mới với 139 quan hệ tham chiếu, precision đạt 83,70% và recall đạt 81,29%, tăng 2,88 điểm phần trăm recall so với bản trước trên đúng lô đó. [Thiết kế và kết quả kiểm tra](results/callups/README.md)
