"""Quyết định theo tên hiển thị, giải và mùa tại từng vị trí bằng chứng."""
import re

import mwparserfromhell as mw

OLD_KH = "club-khatoco-khanh-hoa-cu"
OLD_AG = "club-hung-vuong-an-giang-cu"
HISTORICAL = {
    OLD_KH: ("Khatoco Khánh Hòa (đội một đến 2012)", "https://vpf.vn/team/clb-khatoco-khanh-hoa/"),
    OLD_AG: ("Hùng Vương An Giang (đội một đến 2014)",
             "https://thethaovanhoa.vn/chum-anh-bong-da-an-giang-nhung-ngay-khong-nu-cuoi-20141027144022743.htm"),
}
SOURCES = {
    "viettel_clb": "https://vpf.vn/tin-tuc/hoat-dong-vpf/doan-khao-sat-cong-ty-vpf-lam-viec-voi-trung-tam-the-thao-viettel/",
    "khatoco_cu": HISTORICAL[OLD_KH][1],
    "an_giang_cu": HISTORICAL[OLD_AG][1],
    "ha_noi_hang_nhat": "https://vpf.vn/team/xskt-lam-dong/",
    "ha_noi_b": "https://vpf.vn/team/hong-linh-ha-tinh/?sid=154439",
    "tdc_binh_duong": "https://vpf.vn/hang-nhat-tai-lieu/hang-nhat-thong-bao/thong-bao-so-9-giai-bong-da-hang-nhat-quoc-gia-eximbank-2013/",
}


def club_decision(old_id, label, season, league):
    name = " ".join(label.casefold().split())
    if old_id == "club-w591109":
        if name == "viettel":
            return "c-tc", "viettel_clb"
        return None, "chua_ro_doi_cua_to_chuc"
    if old_id == "club-w2452083" and season == "2012" and name == "khatoco khánh hòa":
        return OLD_KH, "khatoco_cu"
    if old_id == "club-w421642" and season in {"2012", "2013", "2014"}:
        if "an giang" in name:
            return OLD_AG, "an_giang_cu"
        return None, "chua_ro_doi_an_giang"
    if old_id == "c-hn" and league == "VL2":
        if season == "2012" and name == "hà nội":
            return "club-w445434", "ha_noi_hang_nhat"
        if season == "2018" and name == "hà nội b":
            return "c-ht", "ha_noi_b"
        return None, "chua_ro_doi_ha_noi_hang_nhat"
    return old_id, ""


def roster_decision(fact, article, evidence):
    context = article["clean_text"][evidence["context_start"]:evidence["context_end"]]
    period = fact["period"]
    target = fact["dst_id"]
    if not article["title"].casefold().startswith("câu lạc bộ"):
        # Trang giải có tiêu đề theo mùa, và đề mục là tên đội.
        label = mw.parse(context).strip_code().strip("= \n")
        _, league, season = article["story_group"].split(":")
        return club_decision(target, label, season, league)

    lead = re.split(r"<ref\b", context, maxsplit=1, flags=re.I)[0]
    visible = mw.parse(lead).strip_code().casefold()
    if re.search(r"hạng (hai|nhì|ba)|hạng [23](?!\d)", visible):
        return None, "doi_hinh_ngoai_pham_vi"
    if "đang cập nhật" in visible:
        return None, "doi_hinh_dang_cap_nhat"
    if re.search(r"đội hình (2|b|trẻ)\b", visible):
        if target == "c-bd" and "TDC Bình Dương" in lead and f"Hạng Nhất {period}" in lead:
            return "club-w502739", "tdc_binh_duong"
        return None, "doi_hinh_phu_chua_ro"
    # Năm của bảng phải hiển thị cho người đọc. Năm trong bài nguồn,
    # URL chú thích hoặc ngày lấy dữ liệu không thể thay cho nhãn mùa.
    if not re.search(r"(?<!\d)" + re.escape(period).replace("–", "[–/-]") + r"(?!\d)", visible):
        return None, "sai_mua_hien_thi"
    titles = re.findall(r"(?:title|tiêu đề)\s*=\s*([^|}]+)", context, re.I)
    for title in titles:
        years = set(re.findall(r"\b20\d{2}\b", title))
        if years and period[:4] not in years:
            return None, "mau_thuan_mua_trich_nguon"
    return club_decision(target, article["title"], period, article["story_group"].split(":")[1])
