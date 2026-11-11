# Đề tài 22 · Bản A10
Mở `Mo_ban_do.html` trong gói nộp, chọn một quan hệ rồi mở nguồn. Mặc định là mạng xã hội. Có thể tìm người, lọc theo nghiệp vụ và tách bài biên tập khỏi bảng dữ liệu. Mạng không lấy cạnh từ Wikipedia, bóng đá sinh viên hoặc phong trào.

| Phần | Dùng để trả lời | Quy mô |
|---|---|---|
| Xã hội trực tiếp | Ai ký, gia hạn, chuyển đến, được gọi, bị phạt, huấn luyện hoặc tài trợ cho ai? | 1.103 tác nhân, 2.654 cạnh, 16 loại |
| Bối cảnh | Ai có mặt hoặc đá chính trong trận nào, thuộc giải nào? | 2.976 nút gồm cả tác nhân, 10.127 cạnh, 9 loại |
| Nguồn | Tòa soạn nào xác nhận quan hệ ở đoạn hoặc dòng nào? | 1.181 URL, 16.187 đoạn bằng chứng; không cộng vào nút xã hội |
| Đồng đội suy ra | Hai người đã cùng đá chính cho cùng CLB ở bao nhiêu trận? | 2.718 cặp, 5.796 lượt cặp–trận; không cộng vào số cạnh gốc |

Có 494 nút chung giữa hai lớp. Quan hệ tài trợ cho CLB và tài trợ cho giải nằm ở hai lớp khác nhau nên số loại toàn mạng là 24, không phải 25. Có 2.300 nút trận. Toàn đồ thị đạt ngưỡng quy mô 3.585 nút và 12.781 cạnh. Riêng mạng tác nhân còn thiếu 897 nút và 2.346 cạnh so với hai ngưỡng đề bài. Tách chuyển nhượng, danh sách đội và ký hợp đồng: mỗi loại khẳng định một sự việc khác nhau.

29 cạnh mới ghi nhận HLV trưởng ở thời điểm bài giới thiệu mùa được đăng; 5 lượt tên chưa định danh được giữ ngoài đồ thị. 3 cạnh VPF tổ chức giải năm 2023 có nguồn [VnExpress](https://vnexpress.net/vpf-dong-y-voi-de-xuat-cua-hagl-4564430.html). Trong lớp xã hội có 1.101 cạnh từ bài biên tập và 1.553 từ bảng báo đăng. Trong mẫu ngẫu nhiên 80 cạnh xã hội có 73 xác nhận, 7 chưa rõ, precision bảo thủ 91,25% (Wilson 95%: 83,02–95,70%). Chưa đủ để kết luận vượt 90% với độ tin cậy 95%. Đây là đối chiếu một lượt. Không phải phép đo riêng NLP, recall hoặc precision toàn A10.

## Khôi phục từ gói nộp
Tại gốc kho mã, sau khi cài Python 3.13, Docker và các thư viện bằng `python -m pip install -r requirements.lock`, đặt biến `PACK` thành đường dẫn tuyệt đối tới thư mục đã giải nén. Tạo mật khẩu trong tệp local chỉ người dùng đọc được.
```sh
python -c "import pathlib,secrets; p=pathlib.Path('.env.a10'); f=p.open('x'); p.chmod(0o600); f.write('NEO4J_PASSWORD='+secrets.token_urlsafe(24)+'\n'); f.close()"
docker compose --env-file .env.a10 -f compose.layers.yaml up -d
python -m bongda.press_final.compact check "$PACK/graph"
python -m bongda.press_final.compact restore "$PACK/graph" --env .env.a10 --uri bolt://127.0.0.1:7701
```
Chờ Neo4j khởi động xong trước khi restore. Mở http://localhost:7488/browser/ rồi chạy `cypher/phan_lop_a10.cypher`. Thông tin trên máy nhóm: hai lần nhập cùng mã băm, lần hai tạo 0 nút và 0 cạnh. Dữ liệu gốc có bản quyền được giữ local. Các lần chạy lịch sử A3–A9.1 trong repo không thay thế số liệu A10.

## Tái tạo trên máy có kho dữ liệu nguồn
Gọi từ gốc repo, thay các biến đường dẫn bằng vị trí tương ứng. Thư mục OUT mới chứa thư mục con nguon_moi với một bài đã lưu; PARENT là thư mục A9.1 chứa snapshot/.
```sh
python -m bongda.collect.to_chuc_giai_bao "$OUT/nguon_moi"
python -m bongda.press_final.layers "$PARENT" "$OUT"
python -m bongda.press_final.quality_layers "$OUT"
python -m bongda.press_final.view_layers "$OUT"
```
Trong gói nộp, `phan_lop/` chứa bảng từng lớp và liên kết bằng chứng; `kiem_tra/` chứa bản chấm từng cạnh; `graph/` dùng để nạp Neo4j. [Kho mã GitHub](https://github.com/dinhvanan307/vietnam-football-knowledge-graph).
