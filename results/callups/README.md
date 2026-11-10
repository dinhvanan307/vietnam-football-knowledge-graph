# Kiểm tra quan hệ triệu tập lên đội tuyển nam Việt Nam

Ngày 10/11/2026, bản sửa đạt **precision 83,70%** và **recall 81,29%** trên 14 bài mới. So sánh hai phiên bản trên cùng phản hồi Gemini cho thấy recall tăng **2,88 điểm phần trăm**. Precision quan sát được còn dưới 90%.

| Phiên bản | Đúng | Đề xuất sai | Bỏ sót | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Trước sửa | 109 | 25 | 30 | 81,34% | 78,42% | 79,85% |
| Sau sửa | 113 | 22 | 26 | 83,70% | 81,29% | 82,48% |

**Lô phát triển.** Trong 31 quan hệ triệu tập trên lô 18 bài cũ, bản trước sửa tìm đúng 17 và bỏ sót 14. Bản sửa khôi phục được 13 trong 14 ca, gồm các thủ môn đã hội quân, cầu thủ trong danh sách ban đầu và một ca triệu tập được nhắc lại trong bài về chuyển nhượng. Ca còn sót là tên viết ngắn “Văn Vũ”. [14 ca đã rà](ra_14_canh_cu.tsv)

**Lô kiểm tra mới.** Lấy 14 bài từ Tuổi Trẻ và Thanh Niên, kiểm trùng URL và văn bản với corpus A3, lô 16 bài và lô 18 bài. Giá trị Jaccard 5 từ cao nhất là 0,011 khi so với các văn bản trước và các bài đã chọn cùng lô. Chọn 10 bài về đội nam và 4 bài đối chứng về tuyển trẻ, tuyển nữ hoặc tuyển nước ngoài. Codex đọc 137 đoạn sạch và gán 139 quan hệ theo bộ (bài, ID cầu thủ, triệu tập, ID đội tuyển). C01–C03 và C06 có các danh sách dài, chiếm 102/139 nhãn. Đây là mẫu chọn theo chủ đề và được một lượt chấm. Kết quả mô tả tập thử; chưa có hai bộ nhãn độc lập của A/B. [Danh sách bài](mau.tsv) · [Nhãn khóa trước khi chạy API](nhan.tsv)

**So sánh theo cặp.** Mã sửa được khóa trước khi chọn lô mới. Mỗi bài được xử lý qua Gemini API bằng prompt và bộ luật của commit `2f873fb`. Cả 14 phản hồi đều do `gemini-3.1-flash-lite` trả về. Bản cũ lấy cạnh từ đầu ra đã lưu; bản mới đọc đúng danh sách `api_edges` của lần gọi đó, bổ sung tên trong các đoạn xác nhận triệu tập, rồi đối chiếu ID. Hai bảng VFF từ năm 2019 và 2022 chỉ hỗ trợ giải nghĩa tên viết ngắn. Mỗi cạnh bổ sung còn phải có tên và vị trí bằng chứng trong bài đang xét. Các loại quan hệ khác được đối chiếu để đảm bảo kết quả giống bản gốc. [Khóa mã](khoa_ma.json) · [Khóa mẫu](khoa_mau.json) · [Số liệu](diem.json)

**Các thay đổi quan sát được.** Bản mới tìm thêm Trần Nguyên Mạnh ở C01 và Nguyễn Văn Toản, Phan Tuấn Tài, Hồ Tấn Tài ở C06; giữ cả 109 quan hệ đúng cũ. Bản sửa loại 8 đề xuất sai cũ nhưng phát sinh 5 đề xuất sai mới, nên số sai ròng giảm từ 25 xuống 22. Cả hai phiên bản đều cho 0 cạnh ở 4 bài đối chứng. [Điểm theo bài](theo_bai.tsv) · [Đối chiếu từng ID và đoạn](doi_chieu.tsv)

Một lỗi mới ở C01 là gán “Thanh Bình”, thủ môn SHB Đà Nẵng năm 2014, cho ID trung vệ Nguyễn Thanh Bình sinh năm 2000. C06 gọi “Văn Đức” của Hà Tĩnh nhưng bản sửa gán cho Phan Văn Đức. Đội bóng, vị trí và thời điểm triệu tập là các dữ kiện cần đối chiếu khi tên ngắn có nhiều cách hiểu. [Bài C01](https://tuoitre.vn/hlv-miura-chon-24-tuyen-thu-cho-doi-tuyen-vn-803964.htm) · [Bài C06](https://thanhnien.vn/tan-binh-nao-sang-cua-da-chinh-o-doi-tuyen-viet-nam-185230903091414705.htm)

Để tái tính từ bản lưu riêng trên máy nhóm, chạy từ gốc repo:

```sh
python3.13 nlp_bao/so_sanh_trieu_tap.py \
  ../Kiem_thu_trieu_tap/lot_moi.jsonl results/callups/nhan.tsv \
  ../Mau_ban_giao_A/work/a3_final/entities.csv ../Kiem_thu_trieu_tap/api work/kiem_tra_trieu_tap
```

Trên GitHub có thể kiểm lại phép tính từ `doi_chieu.tsv`. Với mỗi cột `truoc` hoặc `sau`, TP là số dòng cả dự đoán và `nhan` bằng 1, FP là số dòng chỉ dự đoán bằng 1, và FN là số dòng chỉ `nhan` bằng 1.
