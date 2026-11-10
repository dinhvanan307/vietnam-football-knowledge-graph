"""Loại thực thể và chiều quan hệ thống nhất cho dữ liệu thật lẫn fixture."""
P, C, N, O, G, S = "Person","Club","NationalTeam","Organization","Competition","Stadium"
ENDS = {
    "THI_DAU_CHO": ({P},{C}), "DAN_DAT": ({P},{C,N}), "KY_HOP_DONG_VOI": ({P},{C}),
    "GIA_HAN_VOI": ({P},{C}), "THANH_LY_VOI": ({P},{C}), "DUOC_CHO_MUON_DEN": ({P},{C}),
    "DUOC_TRIEU_TAP_VAO": ({P},{N}), "KY_LUAT": ({O},{P,C}), "TAI_TRO": ({O},{C,N,G}),
    "CHU_TICH_CUA": ({P},{C,O}), "THAM_GIA_GIAI": ({C,N},{G}), "TO_CHUC_GIAI": ({O},{G}),
    "SU_DUNG_SAN_NHA": ({C},{S}),
    "DANG_KY_THI_DAU_CHO": ({P},{C}),
    "GHI_BAN_VAO_LUOI": ({P},{C}),
    "NHAN_THE_VANG_KHI_GAP": ({P},{C}),
    "DOI_DAU": ({C},{C}),
    "DOI_TRUONG_CUA": ({P},{C}),
    "THI_DAU_TAI_SAN": ({C},{S}),
}
ENTITY = {P,C,N,O,G,S}
