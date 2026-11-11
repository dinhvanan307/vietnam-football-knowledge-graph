"""Resolve only named Vietnamese professional clubs; keep historical identities apart."""
import re,unicodedata

def key(s):
    s=unicodedata.normalize("NFD",s.casefold().replace("đ","d"))
    return " ".join(re.findall(r"[a-z0-9]+","".join(c for c in s if not unicodedata.combining(c))))

# Display names in the first column are taken from the published football sources.
ROWS = """
c-bd|CLB Bình Dương|Bình Dương;B.Bình Dương;B.BD;Becamex Bình Dương;Becamex TP HCM;Becamex TP.HCM;Becamex Thành phố Hồ Chí Minh;Bình Dương FC
c-binhdinh|CLB Bình Định|Bình Định;Topenland Bình Định;MerryLand Quy Nhơn Bình Định;Quy Nhơn Bình Định;MQ.Bình Định;Quy Nhon United
c-cahn|CLB Công an Hà Nội|Công an Hà Nội;CAHN;CA Hà Nội;Cong An Nhan Dan
c-dn|CLB Đà Nẵng|Đà Nẵng;SHB Đà Nẵng;SHB.ĐN;SHB.Đà Nẵng
c-hagl|Hoàng Anh Gia Lai|HAGL;HA.GL;H.A.G.L;H.A Gia Lai;Hoàng Anh Gia Lai;LPBank HAGL;LPBank Hoàng Anh Gia Lai
c-hcm|CLB TP.HCM|TPHCM;TP.HCM;Hồ Chí Minh;TP Hồ Chí Minh;Thành phố Hồ Chí Minh;Công an TP.HCM;CA TP.HCM;CA TPHCM;Công an TP Hồ Chí Minh;Công an TPHCM
c-hn|CLB Hà Nội|Hà Nội;Hà Nội FC;Hà Nội T&T;HN.T&T;Hà Nội T T
c-hp|CLB Hải Phòng|Hải Phòng;Vicem Hải Phòng;XM Hải Phòng;XM.Hải Phòng
c-ht|CLB Hồng Lĩnh Hà Tĩnh|Hà Tĩnh;Hồng Lĩnh Hà Tĩnh;HL Hà Tĩnh;HL.Hà Tĩnh
c-nd|CLB Nam Định|Nam Định;Dược Nam Hà Nam Định;Thép Xanh Nam Định;TX Nam Định
c-ph|CLB Phố Hiến|Phố Hiến;PVF-CAND;PVF Công An Nhân Dân
c-qn|CLB Quảng Nam|Quảng Nam;QNK Quảng Nam
c-slna|Sông Lam Nghệ An|SLNA;Sông Lam Nghệ An
c-tc|Thể Công Viettel|Viettel;Thể Công;Thể Công Viettel;Thể Công – Viettel
c-th|CLB Thanh Hóa|Thanh Hóa;FLC Thanh Hóa;Đông Á Thanh Hóa;Lam Sơn Thanh Hóa
club-press-khanhhoa-2023|CLB Khánh Hòa|Khánh Hòa;Khánh Hoà;Sanna Khánh Hòa BVN;S.Khánh Hòa;Sanna Khánh Hòa
club-press-ninhbinh-2025|CLB Ninh Bình (2025/26)|Ninh Bình;Phù Đổng;Phù Đổng Ninh Bình
club-historic-vissai|Vissai Ninh Bình|Vissai Ninh Bình;The Vissai Ninh Bình
club-w14899593|CLB Bắc Ninh|Bắc Ninh;Bắc Ninh FC
club-w3176765|CLB Đồng Nai|Đồng Nai;Đồng Nai Berjaya
club-w445434|CLB Sài Gòn|Sài Gòn;Sài Gòn FC
c9-qnin|Than Quảng Ninh|Than Quảng Ninh;T.Quảng Ninh;Quảng Ninh
c9-bp|CLB Bình Phước|Bình Phước;Trường Tươi Bình Phước;Trường Tươi Đồng Nai
c9-la|CLB Long An|Long An;Đồng Tâm Long An;ĐTLA;ĐT.Long An
c9-ct|CLB Cần Thơ|Cần Thơ;XSKT Cần Thơ;XSKT.Cần Thơ
c9-dt|CLB Đồng Tháp|Đồng Tháp;TĐCS Đồng Tháp;CS Đồng Tháp
c9-brvt|CLB Bà Rịa – Vũng Tàu|Bà Rịa Vũng Tàu;BR-VT;Bà Rịa Vũng Tàu FC
c9-hue|CLB Huế|Huế;Bóng đá Huế;Huda Huế
c9-ag|CLB An Giang|An Giang;Hùng Vương An Giang
c9-tn|CLB Tây Ninh|Tây Ninh;XM Fico Tây Ninh;Tây Ninh FC
c9-pt|CLB Phú Thọ|Phú Thọ
c9-hb|CLB Hòa Bình|Hòa Bình;Hòa Bình FC
c9-dl|CLB Đắk Lắk|Đắk Lắk;Đắc Lắc;Đắk Lăk
c9-bt|CLB Bình Thuận|Bình Thuận
c9-kg|CLB Kiên Giang|Kiên Giang;Kienlongbank Kiên Giang
c9-hcm2|CLB TP.HCM II|Hồ Chí Minh II;TP Hồ Chí Minh II;TP.HCM II;Trẻ TP.HCM
""".strip()
NAMES={};ALIASES={}
for row in ROWS.splitlines():
    ident,name,variants=row.split("|");NAMES[ident]=name
    for alias in [name,*variants.split(";")]:ALIASES[key(alias)]=ident
def identify(label,date="",provider_id=None):
    k=re.sub(r"^(?:clb|fc) ","",key(label))
    ident=ALIASES.get(k)
    if k=="cong an nhan dan":return None  # historical names require the original competition context
    if ident=="club-press-ninhbinh-2025" and k=="ninh binh" and date and date<"2015":return "club-historic-vissai"
    if ident=="club-press-khanhhoa-2023" and date and date<"2013":return None
    if ident=="club-w3176765" and k=="dong nai" and date>="2025-08" and provider_id==9161:return "c9-bp"
    if ident=="club-w3176765" and k=="dong nai" and date>="2025-08" and not provider_id:return None
    if ident=="c-hn" and k=="ha noi" and date and date<"2017":return None  # two Hà Nội teams shared the city name
    if ident=="club-w445434" and date and date<"2016":return None
    return ident
LEAGUES={"v league":("g-vl1","V.League 1"),"v league 1":("g-vl1","V.League 1"),
    "hang nhat quoc gia":("g9-vl2","Giải hạng Nhất quốc gia"),"cup quoc gia":("g9-cup","Cúp Quốc gia Việt Nam")}
