# Đánh giá trích xuất thương vụ cầu thủ

Mỗi quan sát là một cầu thủ đến một CLB trong một đợt được bài báo xác nhận. Tên cầu thủ, đội tiếp nhận và câu làm bằng chứng phải khớp. Nhóm giữ riêng bằng chứng ký hợp đồng, thông báo của CLB, thỏa thuận đã chốt và thông tin cầu thủ gia nhập đội.

| Bài chưa dùng | Phương pháp | TP / FP / FN | Precision | Recall | F1 |
|---|---|---:|---:|---:|---:|
| Lô đầu · 20 bài | Luật nền | 5 / 1 / 3 | 83,33% | 62,50% | 71,43% |
| Lô đầu · 20 bài | Đọc từng ứng viên | 7 / 0 / 1 | 100% | 87,50% | 93,33% |
| Lô giữa · 16 bài | Luật nền | 1 / 4 / 8 | 20,00% | 11,11% | 14,29% |
| Lô giữa · 16 bài | Luật K1 | 1 / 1 / 8 | 50,00% | 11,11% | 18,18% |
| Lô cuối · 24 bài | Luật K1 | 3 / 4 / 9 | 42,86% | 25,00% | 31,58% |
| Lô cuối · 24 bài | Luật K2 | 3 / 4 / 9 | 42,86% | 25,00% | 31,58% |
| Lô cuối · 24 bài | Đọc từng ứng viên | 11 / 1 / 1 | 91,67% | 91,67% | 91,67% |
| Lô đầu và lô cuối · 44 bài | Đọc từng ứng viên | **18 / 1 / 2** | **94,74%** | **90,00%** | **92,31%** |

Chọn 66 URL từ Bóng Đá, Thanh Niên và Tuổi Trẻ theo tiêu đề, có cả tin đồn, gia hạn và chia tay. Loại bốn bản in trùng và hai trang không đủ điều kiện, còn 60 bài. Lô cuối dùng tên CLB trong tiêu đề để chọn mẫu. Đơn vị đánh giá là thương vụ trong từng bài. Một bài có thể đóng góp nhiều quan sát. Các bài âm tính được giữ trong mẫu.

K1/K2 là hai phiên bản luật tự động. Trong lượt đọc từng ứng viên, chương trình chọn câu và ngữ cảnh, sau đó trợ lý đọc và quyết định từng cạnh. Dự đoán được khóa trước khi cùng trợ lý đọc lại toàn bài để lập nhãn. Nhãn hiện có một người chấm theo quy trình, chưa có lượt chấm chéo độc lập. Khoảng Wilson 95% tham khảo cho precision gộp là 75,36–99,06%. Mẫu hạn chế theo tòa soạn và có các cạnh cùng bài.

Trong 29 thương vụ tham chiếu, 4 có câu xác nhận đã ký, 1 có thông báo hợp đồng của CLB, 2 nêu thỏa thuận đã chốt và 22 xác nhận gia nhập hoặc tư cách tân binh. Riêng 44 bài của lượt đọc có 2 trường hợp ký hoặc công bố hợp đồng, cả hai đều tìm đúng trong phép lọc hậu kiểm. Kết quả NLP được lưu riêng với 12.781 cạnh của A10.

## Tái lập điểm

Chạy từ thư mục gốc của repo bằng Python 3.13. Lệnh đọc các phiếu công khai và kiểm tra lại TP, FP, FN, ba thước đo và phạm vi bài trong từng lô.

```sh
python3.13 -m bongda.evaluate.verify_contracts
```

[Danh sách bài và trạng thái](articles.tsv) · [Phiếu chấm từng dự đoán](reviews.tsv) · [Thương vụ và vị trí câu trong bài](events.tsv) · [Số liệu đầy đủ](metrics.json).

## Chạy bộ trích trên văn bản riêng

Cài thư viện bằng `python3.13 -m pip install -r requirements.lock`. Tệp UTF-8 đầu vào có dạng sau. Ví dụ dùng tên giả.

```json
{"title":"CLB Thanh Hóa công bố tân binh","day":"2026-07-01","paragraphs":["CLB Thanh Hóa đã chiêu mộ thành công tiền đạo Nguyễn Minh Sơn."]}
```

```sh
python3.13 -m bongda.press_final.contracts bai.json --mode k2
python3.13 -m bongda.press_final.contracts bai.json --mode review
```

Chọn `k1` để chạy luật trước đó. Đầu ra K2 giữ tên, mã CLB, câu bằng chứng và vị trí đoạn.câu. Chế độ `review` trả về các câu gợi ý để rà từng cầu thủ. Các phiếu công khai giữ URL và vị trí câu. Văn bản bài báo được lưu local.
