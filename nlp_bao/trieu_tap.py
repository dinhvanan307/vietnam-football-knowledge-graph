"""Nhận diện các thành viên của một đợt tập trung ĐT nam Việt Nam trong văn bản."""
import csv
import re
from collections import defaultdict
from pathlib import Path

REL = "DUOC_TRIEU_TAP_VAO"
TEAM = re.compile(r"(?:\b(?:đội\s+)?tuyển|\bĐT)\s+(?:quốc gia\s+|nam\s+)?(?:Việt Nam|VN)\b|ĐTQG",re.I)
YOUTH = re.compile(r"\bU[ .-]?\d{2}\b|tuyển nữ|futsal",re.I)
UNCERTAIN = re.compile(r"(?:chưa|không|có thể|đáng|nên|hy vọng|mong|khả năng)\s+(?:được\s+)?(?:gọi|triệu tập)|"
                       r"nếu\b|dự kiến|dự đoán|ứng viên|danh sách chờ|cơ hội (?:được )?(?:gọi|triệu tập)",re.I)
CAMP = re.compile(r"triệu tập|được gọi|gọi bổ sung|gọi lên|hội quân|tập trung|danh sách (?:chính thức|sơ bộ|các cầu thủ)|"
                  r"có mặt (?:trong|ở|tại).{0,55}buổi tập|(?:đang|hiện) có \d+ (?:thủ môn|hậu vệ|tiền vệ|tiền đạo)",re.I)
LIST = re.compile(r"danh sách tập trung ban đầu|danh sách (?:triệu tập|cầu thủ được gọi)|"
                  r"(?:đang|hiện) có \d+ (?:thủ môn|hậu vệ|tiền vệ|tiền đạo)\s*[:：]|"
                  r"(?:gọi|triệu tập).{0,32}(?:bao gồm|gồm có|gồm|là|sau đây)\s*[:：]?|"
                  r"(?:các |những )?(?:cầu thủ|cái tên) được gọi (?:lên )?(?:bổ sung|thay thế) (?:gồm|là)",re.I)
POSITION = re.compile(r"^\s*(?:[-–•]\s*)?(?:các |nhóm )?(?:thủ môn|hậu vệ|tiền vệ|tiền đạo)\s*[:：]",re.I)
TRANSITION = re.compile(r"\b(?:trong khi đó|tuy nhiên|trong khi|thay vì|ngoại trừ|trừ trường hợp)\b",re.I)
DIRECT = re.compile(r"\bđược (?:HLV [^,.;:]{1,42}?(?=\s+(?:triệu tập|gọi))\s+)?(?:triệu tập|gọi (?:lên|bổ sung))|"
                    r"\b(?:đã |vừa |quyết định )?(?:triệu tập|gọi bổ sung|gọi lên)\s+(?:bổ sung\s+)?|"
                    r"\b(?:có mặt (?:trong|ở|tại).{0,55}buổi tập|hội quân (?:cùng|với)|tập trung cùng)",re.I)
STOP_NAME = re.compile(r"(?i)\b(?:HLV|huấn luyện viên|trợ lý|bác sĩ|giám đốc)\s+$")


class Callups:
    def __init__(self, registry):
        self.aliases = defaultdict(set)
        self.senior = defaultdict(set)
        self.positions = defaultdict(set)
        for eid,name in registry.names.items():
            if "Player" not in registry.roles[eid]:
                continue
            bare = re.sub(r"\s*\([^()]*\)\s*$","",name).strip().casefold()
            if len(bare.split()) >= 2:
                self.aliases[bare].add(eid)
                self.aliases[" ".join(bare.split()[-2:])].add(eid)
        with Path(__file__).with_name("ten_tuyen_thu.tsv").open(encoding="utf-8") as f:
            for row in csv.DictReader(f,delimiter="\t"):
                eid=row["entity_id"]
                if eid not in registry.names:
                    continue
                self.positions[eid].add(row["vi_tri"].casefold())
                full=row["ten"].casefold()
                for alias in {full, " ".join(full.split()[-2:])}:
                    self.senior[alias].add(eid)
        names=sorted(self.aliases,key=lambda n:(-len(n),n))
        self.matcher=re.compile(r"(?<!\w)(?:"+"|".join(map(re.escape,names))+r")(?!\w)",re.I)

    def resolve(self, registry, name, context, article):
        name=" ".join(name.split())
        alias=name.casefold()
        possible=self.aliases.get(alias,set())
        # Nếu bài đã giải thích tên ngắn bằng đúng một họ tên đầy đủ thì dùng chính ngữ cảnh đó.
        longer={eid for eid in possible
                if len((full:=registry.names[eid].split("(")[0].strip()).split())>len(name.split())
                and re.search(r"(?<!\w)"+re.escape(full)+r"(?!\w)",article,re.I)}
        if len(longer)==1:
            return next(iter(longer))
        result=registry.resolve(name,"Person",context=context)
        if not result.startswith(("new:","ambiguous:")):
            return result
        known=self.senior.get(alias,set()) & possible
        positions=re.findall(r"(thủ môn|hậu vệ|tiền vệ|tiền đạo|trung vệ)\s+"+re.escape(name)+r"\b",context,re.I)
        if positions:
            roles={"hậu vệ" if t.casefold()=="trung vệ" else t.casefold() for t in positions}
            known={i for i in known if roles & self.positions[i]}
        return next(iter(known)) if len(known)==1 else result

    def supplements(self, article, registry):
        text=article["clean_text"]
        if not TEAM.search(text):
            return []
        blocks=[m.group() for m in re.finditer(r"[^\n]+",text)]
        additions=[]
        last_list=None
        for i,line in enumerate(blocks):
            # Không gán cả câu về đội trẻ chỉ vì bài cũng nhắc tuyển quốc gia.
            prior=blocks[max(0,i-2):i]
            senior_context=TEAM.search(line) or any(TEAM.search(t) and not YOUTH.search(t) for t in prior)
            carry=last_list is not None and i==last_list+1 and POSITION.search(line)
            last_list=None
            if not senior_context and not carry:
                continue
            intro=LIST.search(line)
            if YOUTH.search(line) or UNCERTAIN.search(line):
                intro=None
                carry=False
            if intro or carry:
                last_list=i
                if intro and "danh sách tập trung ban đầu" in intro.group().casefold():
                    start=intro.end()
                else:
                    start=intro.end() if intro else 0
                spans=[(line[start:], [i+1] if not carry else [i,i+1])]
            else:
                spans=[]
                for sentence in re.split(r"(?<=[.!?])\s+|;\s*",line):
                    for part in TRANSITION.split(sentence):
                        cue=DIRECT.search(part)
                        if not cue or YOUTH.search(part) or UNCERTAIN.search(part):
                            continue
                        # Tránh gán người thay thế, đối thủ hoặc người gọi ở phía bên kia động từ.
                        if cue.group().casefold().startswith(("được","hội quân","tập trung","có mặt")):
                            segment=part[:cue.start()]
                        else:
                            segment=part[cue.end():]
                        segment=re.split(r"\b(?:thay (?:thế |cho )?|để|nhằm|gặp|đối đầu|ở vòng loại)\b",segment,maxsplit=1,flags=re.I)[0]
                        spans.append((segment,[i+1]))
            for passage,refs in spans:
                for hit in self.matcher.finditer(passage):
                    if STOP_NAME.search(passage[:hit.start()]):
                        continue
                    name=hit.group()
                    eid=self.resolve(registry,name,line,text)
                    if eid.startswith(("new:","ambiguous:")):
                        continue
                    evidence=refs.copy()
                    if not TEAM.search(line):
                        evidence.extend(j+1 for j in range(max(0,i-2),i) if TEAM.search(blocks[j]))
                    additions.append(dict(src=name,dst="đội tuyển Việt Nam",rel=REL,paragraphs=sorted(set(evidence))))
        return additions
