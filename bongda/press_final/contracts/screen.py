"""Select evidence for reading while preserving paragraph and sentence IDs."""

import re

CUE = re.compile(
    r"hợp đồng|bản ký kết|đặt bút|k[ýí] (?:kết|với|mới|chính thức)|bom tấn|tân binh|thương vụ|chuyển nhượng|chiêu mộ|tuyển mộ|gia nhập|đầu quân|cập bến|mua đứt|tậu |trao đổi|chuyển (?:đến|sang|tới|về|từ)|đưa (?:về|vào|vào biên chế)|đem về|mang về|lót tay|bổ sung|tăng cường|đón (?:thêm|chào)|chào (?:đón|mừng)|ra mắt|khoác áo|chính thức (?:là|trở thành)|thu nạp|quân số|tân binh|thanh lý|giữ chân|cho mượn|chấm dứt|chia tay",
    re.I,
)


def sentences(paragraphs):
    out = {}
    for i, p in enumerate(paragraphs, 1):
        # A stop followed by a space is important for initials such as TP.HCM.
        parts = re.split(
            r'(?<=[.!?])\s+(?=[A-ZÀ-ỸĐ“"«(0-9])|(?<=[.!?][”"])\s+(?=[A-ZÀ-ỸĐ0-9])', p
        )
        for j, s in enumerate(parts, 1):
            out[f"{i}.{j}"] = s
    return out


def packets(a):
    ss = sentences(a["paragraphs"])
    keys = list(ss)
    picked = set()
    for i, k in enumerate(keys):
        if CUE.search(ss[k]):
            picked.update(keys[max(0, i - 1) : i + 2])
    return {k: v for k, v in ss.items() if k in picked}
