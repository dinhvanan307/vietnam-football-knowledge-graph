"""Contextual arrival extractor. Preserve the exact sentence for every returned edge."""

import re
from . import rules as v1
from ..clubs import key

PLAYER_TITLE = re.compile(
    r"(?:(?:Hậu vệ|Trung vệ|Thủ môn|Tiền vệ|Tiền đạo|Cầu thủ|Ngoại binh|Tuyển thủ|ĐTQG|ĐT|U\d+|Việt Nam|Brazil|Serbia|Nhật Bản|Hàn Quốc|Hà Lan|Thái Lan|Anh|Pháp)\s+)+"
)
LEAD = re.compile(
    r"^(?:trước đó|trước đây|mới đây|hiện tại|theo đó|hồi đầu|bên cạnh|trong đó|chủ tịch|ban lãnh đạo|đội bóng|câu lạc bộ|đội tuyển|sài gòn|hà nội|thành phố|v league|trong khi|ban huấn luyện|giải đấu|đội chủ|năm ngoái)\b",
    re.I,
)
PRO = re.compile(
    r"^(?:anh|anh ấy|cầu thủ này|chân sút này|cầu thủ sinh năm \d{4})\b", re.I
)
ACTOR_PASSIVE = re.compile(r"\bđược\s+(?:đội bóng\s+)?(?:CLB\s+)?$", re.I)
AGREED = re.compile(
    r"\b(?:đã (?:đạt (?:được )?(?:thỏa|thoả) thuận|hoàn tất (?:thương vụ|chiêu mộ))|vừa công bố|chính thức công bố|đã chính thức công bố|vừa ra mắt)\b",
    re.I,
)
INTRO = re.compile(r"\b(?:tân binh|bản hợp đồng(?: mới)?|cầu thủ mới)\b", re.I)
NEG_AFTER = re.compile(
    r"\b(?:nhiều khả năng|có thể sẽ|vẫn chưa|chưa hoàn tất|chưa chốt|vẫn đang đàm phán)\b",
    re.I,
)
RUMOUR = re.compile(
    r"\b(?:tin đồn|thỏa thuận sơ bộ|thoả thuận sơ bộ|sẽ ký|dự kiến ký|được cho là|rục rịch|dự định|chưa ký)\b",
    re.I,
)
RETAIN = re.compile(
    r"\b(?:gia hạn|thi đấu thêm|tiếp tục thi đấu|giữ chân|ở lại|tái ký)\b", re.I
)
STAFF = re.compile(
    r"\b(?:hlv|trợ lý|giám đốc|chủ tịch|thầy|ông|bà|trọng tài|huấn luyện viên)\s*$",
    re.I,
)
ROLE = v1.ROLE


def clean(label):
    label = PLAYER_TITLE.sub("", label, count=1) if PLAYER_TITLE.match(label) else label
    if (
        not label
        or label.isupper()
        or LEAD.search(label)
        or key(label) in v1.NOT_PERSON
        or v1.BLOCK_WORDS.intersection(key(label).split())
    ):
        return ""
    return label


def actors(text, date):
    clubs = v1.teams(text, date)
    out = []
    for m in v1.NAME.finditer(text):
        name = clean(m.group())
        if not name:
            continue
        start = m.end() - len(name)
        if any(start < b and m.end() > a for a, b, _ in clubs) or STAFF.search(
            text[:start]
        ):
            continue
        if len(name.split()) < 2 and not re.search(
            ROLE.pattern + r"\s*$", text[:start], re.I
        ):
            continue
        if re.search(r"(?:người|quốc tịch|ở|tại)\s*$", text[:start], re.I):
            continue
        out.append((start, m.end(), name))
    return out


def extract(title, day, paragraphs):
    lines = [
        (f"{i}.{j}", s)
        for i, p in enumerate(paragraphs, 1)
        for j, s in enumerate(v1.SEPARATE.split(p), 1)
    ]
    if v1.OFF_SCOPE.search(" ".join([title, *paragraphs[:2]])):
        return []
    text = dict(lines)
    out = {}

    def add(name, cid, anchor, support=""):
        name = clean(name)
        if not name or not cid:
            return
        s = text[anchor]
        if RUMOUR.search(s) or NONPLAYER.search(s):
            return
        if re.search(r"\bhợp đồng mới\b", s, re.I) and RETAIN.search(
            " ".join([title, *paragraphs[:4]])
        ):
            return
        # The article may qualify just one name from an earlier group as still uncertain.
        if any(
            NEG_AFTER.search(q)
            and (
                name in q
                or (len(name.split()) >= 3 and " ".join(name.split()[-2:]) in q)
            )
            for _, q in lines
        ):
            return
        out.setdefault(
            (name, cid, anchor),
            dict(name=name, club=cid, anchor=anchor, context=support, evidence=s),
        )

    for r in v1.extract(title, day, paragraphs):
        add(r["name"], r["club"], r["anchor"], r["context"])
    focus = v1.teams(title, day)
    for i, (anchor, s) in enumerate(lines):
        if (
            RUMOUR.search(s)
            or RETAIN.search(s)
            or NONPLAYER.search(s)
            or v1.OFF_SCOPE.search(s)
        ):
            continue
        teams = v1.teams(s, day)
        persons = actors(s, day)
        # "A được CLB B chiêu mộ" and "Anh được B chiêu mộ". For a pronoun, use
        # a unique player in the two previous sentences; abstain if ambiguous.
        for a, b, cid in teams:
            if not ACTOR_PASSIVE.search(s[:a]) or not re.match(
                r"\s+(?:chính thức |thành công )?(?:chiêu mộ|tuyển mộ|ký hợp đồng)\b",
                s[b:],
                re.I,
            ):
                continue
            if v1.NEG.search(s[:a]):
                continue
            prior = [p for p in persons if p[1] < a]
            if prior:
                add(prior[-1][2], cid, anchor)
            elif PRO.match(s):
                for prev, q in reversed(lines[max(0, i - 2) : i]):
                    labels = actors(q, day)
                    if len(labels) == 1:
                        add(labels[0][2], cid, anchor, prev)
                        break
                    if labels:
                        break
        # A domestic club confirms a completed agreement with one or several players.
        for m in AGREED.finditer(s):
            source = [t for t in teams if t[1] <= m.start()]
            if not source or v1.NEG.search(s[: m.start()]):
                continue
            if not INTRO.search(s[m.end() :]) and "chiêu mộ" not in m.group().lower():
                continue
            for a, b, name in persons:
                if a < m.end() or a - m.end() > 220 or STAFF.search(s[:a]):
                    continue
                if re.search(
                    r"\b(?:trợ lý|HLV|của đội|nhà tài trợ)\b", s[m.end() : a], re.I
                ):
                    break
                if len(name.split()) >= 2:
                    add(name, source[-1][2], anchor)
        # "Hồ ... đặt bút ký ... có thời hạn ... với CLB B."
        for m in re.finditer(r"\b(?:đặt bút ký|đã ký|chính thức ký)\b", s, re.I):
            left = [p for p in persons if p[1] <= m.start()]
            if not left or v1.NEG.search(re.split("[,;:]", s[: m.start()])[-1]):
                continue
            right = [
                t
                for t in teams
                if t[0] > m.end()
                and re.search(r"\bvới\s+(?:CLB\s+)?$", s[m.end() : t[0]], re.I)
            ]
            if len(right) == 1 and len(s[m.end() : right[0][0]]) < 85:
                add(left[-1][2], right[0][2], anchor)
        # Completed acquisition with an anaphoric club. Require a unique named
        # club in the headline and one of the immediately preceding sentences.
        if (
            not teams
            and re.search(r"\b(?:đã|vừa|mới đây đã) chiêu mộ thành công\b", s, re.I)
            and re.search(r"\b(?:đội bóng|CLB)\b", s, re.I)
            and len({c[2] for c in focus}) == 1
        ):
            cid = focus[0][2]
            supports = [
                k
                for k, q in lines[max(0, i - 3) : i]
                if {t[2] for t in v1.teams(q, day)} == {cid}
            ]
            cue = s.lower().index("chiêu mộ")
            after = [p for p in persons if p[0] > cue]
            if supports and len(after) == 1:
                add(after[0][2], cid, anchor, supports[-1])
    return list(out.values())


NONPLAYER = re.compile(
    r"hợp đồng tài trợ|nhà tài trợ|tài trợ trang phục|hợp đồng huấn luyện|cho mượn|dưới dạng mượn",
    re.I,
)
