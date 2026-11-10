"""A6: control factuality and resolve a list referenced by a past senior camp."""
import re
from collections import defaultdict

FORECAST = re.compile(r"được kỳ vọng|mối quan tâm của dư luận|dự kiến (?:sẽ )?(?:triệu tập|gọi)|nhiều khả năng|có khả năng|nên (?:được )?(?:gọi|triệu tập)|có thể sẽ được gọi|được tiến cử", re.I)
PENDING = re.compile(r"danh sách (?:triệu tập )?chính thức sẽ (?:được )?(?:công bố|chốt)|chưa (?:công bố|chốt) danh sách", re.I)
PAST_GROUP = re.compile(r"(?:những|các|nhóm) (?:gương mặt|cầu thủ)(?: (?:trẻ|kể trên|nói trên|này|đó))* (?:đều )?(?:đã|từng) (?:được (?:gọi|triệu tập)|góp mặt|có mặt|xuất hiện|tập trung|hội quân)[^.?!]{0,70}?(?:đội tuyển|tuyển|ĐT)(?: nam)? (?:Việt Nam|VN)\b", re.I)
CONFIRMED = re.compile(r"(?:đã|vừa|chính thức) (?:được )?(?:gọi|triệu tập|hội quân|có mặt)|(?:có tên|góp mặt) trong danh sách (?:chính thức|tập trung)|công bố danh sách", re.I)

def apply(article, base, registry, identify):
    parts=[s for s in article['clean_text'].splitlines() if s.strip()]
    result={}; rejected={}
    pending=bool(PENDING.search(article['clean_text']))
    for eid,p in base.items():
        named=[parts[n-1] for n in p['refs'] if 1<=n<=len(parts) and re.search(re.escape(p['name']),parts[n-1],re.I)]
        def tentative(s):
            mention=[c for c in re.split(r'(?<=[.!?])\s+',s) if p['name'].casefold() in c.casefold()]
            return bool(mention) and all((FORECAST.search(c) or (pending and ('tin liên quan' in c.lower() or 'danh sách sơ bộ' in c.lower()))) and not CONFIRMED.search(c) for c in mention)
        if named and all(tentative(x) for x in named):
            rejected[eid]='dự đoán trong mệnh đề nêu tên'; continue
        result[eid]=dict(p)
    # The later U-age prediction and the earlier confirmed senior camp refer to
    # different events. Resolve only the list antecedent of an explicit past verb.
    alias=sorted((k for k in registry.callups.aliases if len(k.split())>=2),key=lambda s:(-len(s),s))
    token=re.compile(r'(?<!\w)(?:'+'|'.join(re.escape(k) for k in alias)+r')(?!\w)',re.I)
    for n,s in enumerate(parts,1):
        for match in PAST_GROUP.finditer(s):
            left=s[:match.start()].strip()
            refs=[n]
            if not left and n>1:left=parts[n-2];refs=[n-1,n]
            # Only the immediate enumerated list may serve as the antecedent.
            left=re.split(r'[!?]|(?<=\.)\s+',left.rstrip('. '))[-1]
            if ',' not in left or not re.search(r'gồm|bao gồm|là|có |hậu vệ|tiền vệ|tiền đạo|thủ môn',left,re.I):continue
            for m in token.finditer(left):
                name=m.group();eid=identify(name,left,article['clean_text'],int(article['date'][:4]))
                if eid:
                    old=result.get(eid,{'name':name,'refs':[]})
                    result[eid]={**old,'refs':sorted(set(old['refs']+refs))}
    return result,rejected
