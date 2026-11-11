"""High-precision extraction of completed player arrivals at Vietnamese clubs."""

import re
import unicodedata

from ..clubs import identify, key
from ..editorial import TEAM_TOK, latin

UPPER = "".join(
    chr(i)
    for i in range(65, 0x1F00)
    if chr(i).isupper() and "LATIN" in unicodedata.name(chr(i), "")
)
WORD = f"[{UPPER}][^\\W\\d_]*(?:[-’'][^\\W\\d_]+)*"
NAME = re.compile(
    r"(?<![\w])"
    + WORD
    + r"(?:(?:\s+(?:da|do|dos|de|van|von|del|di))?\s+"
    + WORD
    + r"){0,4}"
)
ROLE = re.compile(
    r"(?:thủ môn|trung vệ|hậu vệ|tiền vệ|tiền đạo|ngoại binh|cầu thủ|chân sút|tuyển thủ|tân binh)",
    re.I,
)
STAFF = re.compile(
    r"\b(?:hlv|trợ lý|ông|bà|giám đốc|chủ tịch|huấn luyện viên)\s*$", re.I
)
# Use complete cues. An isolated word "hợp đồng" also occurs in renewals and rumours.
SIGN = re.compile(
    r"\b(?:k[ýí] (?:kết |vào )?(?:(?:bản|một|một bản) )?hợp đồng|đặt bút ký|chiêu mộ(?: thành công)?|tuyển mộ|gia nhập|đầu quân cho|cập bến|mua đứt|công bố (?:bản hợp đồng|tân binh)|chính thức ra mắt)\b",
    re.I,
)
NEG = re.compile(
    r"\b(?:muốn|mong|sẽ|có thể|sắp|dự kiến|dự định|nhiều khả năng|tin đồn|chưa|không|từ chối|đề nghị|đàm phán|nhằm|quan tâm|nhắm|tìm cách|nếu|chờ|hy vọng|hi vọng|mục tiêu|được cho là|nỗ lực|thuyết phục)\b",
    re.I,
)
NON_NEW = re.compile(
    r"\b(?:gia hạn|tái ký|ở lại|giữ chân|cho mượn|dạng mượn|mượn từ|hợp đồng đào tạo|hợp đồng tài trợ|lò đào tạo)\b",
    re.I,
)
OFF_SCOPE = re.compile(
    r"sân 7|bóng đá 7 người|bóng đá nữ|giải (?:bóng đá )?nữ|futsal|bóng chuyền|phủi|bóng rổ|hạng ba quốc gia",
    re.I,
)
NOT_PERSON = {
    "brazil",
    "serbia",
    "nga",
    "phap",
    "viet nam",
    "thai lan",
    "na uy",
    "nhat ban",
    "han quoc",
    "thuy dien",
    "indonesia",
    "dong nam a",
    "viet kieu",
    "quoc gia",
    "world cup",
    "v league",
    "vleague",
    "chau au",
    "chau a",
    "doi tuyen",
    "bo dao nha",
    "argentina",
    "nigeria",
    "ha lan",
    "viettel",
}
BLOCK_WORDS = set("clb fc hlv cup u fifa afc vff vpf tto fifa futsal vck hagl".split())
SEPARATE = re.compile(
    r'(?<=[.!?])\s+(?=[A-ZÀ-ỸĐ“"«(0-9])|(?<=[.!?][”"])\s+(?=[A-ZÀ-ỸĐ0-9])'
)


def teams(s, date):
    return [
        (m.start(), m.end(), cid)
        for m in TEAM_TOK.finditer(latin(s))
        if (cid := identify(m.group(), date))
    ]


def names(s, clubs):
    mentions = []
    for m in NAME.finditer(s):
        start, end = m.span()
        # Punctuation separates typographic lead-ins and locations from player names.
        if any(start < b and end > a for a, b, _ in clubs):
            continue
        if STAFF.search(s[:start]):
            continue
        label = m.group()
        if (
            label.isupper()
            or key(label) in NOT_PERSON
            or BLOCK_WORDS.intersection(key(label).split())
        ):
            continue
        if len(label.split()) == 1 and not re.search(
            ROLE.pattern + r"\s*$", s[:start], re.I
        ):
            continue
        if re.search(r"(?:người|quốc tịch|lựa chọn của|sinh tại)\s*$", s[:start], re.I):
            continue
        mentions.append((start, end, label))
    return mentions


def extract(title, day, paragraphs):
    """Return one evidence row per mention. The caller may merge mentions of one transfer."""
    if OFF_SCOPE.search(" ".join([title, *paragraphs[:2]])):
        return []
    result = []
    history = []
    for pi, p in enumerate(paragraphs, 1):
        for si, s in enumerate(SEPARATE.split(p), 1):
            anchor = f"{pi}.{si}"
            clubs = teams(s, day)
            people = names(s, clubs)
            for cue in SIGN.finditer(s):
                before = s[: cue.start()]
                after = s[cue.end() :]
                # Denials and renewals in the same clause take precedence over the headline.
                left = re.split(r"[;:!?]", before)[-1]
                if NEG.search(left) or NON_NEW.search(s) or OFF_SCOPE.search(s):
                    continue
                if re.search(
                    r"(?:điều kiện|kế hoạch|trong việc|để|cần)\s*$", left, re.I
                ):
                    continue
                if re.match(
                    r"\s*(?:với\s+)?(?:HLV|nhà tài trợ|ban huấn luyện)\b", after, re.I
                ):
                    continue
                prev_teams = [c for c in clubs if c[1] <= cue.start()]
                next_teams = [c for c in clubs if c[0] >= cue.end()]
                prev_people = [m for m in people if m[1] <= cue.start()]
                next_people = [m for m in people if m[0] >= cue.end()]
                context = ""
                chosen = []
                moving = cue.group().casefold() in {
                    "gia nhập",
                    "đầu quân cho",
                    "cập bến",
                    "chính thức ra mắt",
                }
                if next_teams:
                    dest = next_teams[0]
                    gap = s[cue.end() : dest[0]].strip()
                    if not re.fullmatch(
                        r"(?:(?:chính thức|với|cho|cùng|tại|câu lạc bộ|clb|đội bóng|đội|bến đỗ mới)\s*)*",
                        gap,
                        re.I,
                    ):
                        dest = None
                else:
                    dest = None
                if (
                    dest
                    and prev_people
                    and (
                        moving
                        or not prev_teams
                        or prev_people[-1][1] > prev_teams[-1][1]
                        or re.search(
                            r"\([^)]*\)\s*(?:đã|vừa|chính thức)?\s*$", before, re.I
                        )
                    )
                ):
                    actor = prev_people[-1]
                    if len(before[actor[1] :]) > 100:
                        continue
                    chosen = [actor]
                    cid = dest[2]
                elif not moving and next_people:
                    dest = prev_teams[-1] if prev_teams else None
                    if dest is None:
                        if (
                            not re.match(r"^(?:đội bóng|clb|họ)\b", s, re.I)
                            or not history
                        ):
                            continue
                        pc = history[-1][1]
                        if len({c[2] for c in pc}) != 1:
                            continue
                        dest = pc[0]
                        context = history[-1][0]
                    gap = s[cue.end() : next_people[0][0]]
                    if next_teams and next_teams[0][0] < next_people[0][0]:
                        continue
                    if (
                        len(gap) > 82
                        or STAFF.search(gap)
                        or re.search(r"\b(?:để|nếu|từ|khi|giám đốc)\b", gap, re.I)
                    ):
                        continue
                    chosen = [next_people[0]]
                    cid = dest[2]
                    for nxt in next_people[1:]:
                        bridge = ROLE.sub("", s[chosen[-1][1] : nxt[0]])
                        if not re.fullmatch(
                            r"(?:[\s,:…]+|\([^)]{1,65}\)|\bvà\b|\bcùng\b)+",
                            bridge,
                            re.I,
                        ):
                            break
                        chosen.append(nxt)
                for _, _, player in chosen:
                    result.append(
                        dict(
                            name=player,
                            club=cid,
                            anchor=anchor,
                            context=context,
                            evidence=s,
                        )
                    )
            history.append((anchor, clubs))
    return result
