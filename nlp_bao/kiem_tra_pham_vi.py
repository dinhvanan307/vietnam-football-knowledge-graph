"""Sàng quan hệ theo sự kiện; dự đoán và danh sách thủ tục không phải lệnh tập trung."""
import re
from ngu_canh_trieu_tap import apply as previous
from trieu_tap import TEAM,STOP_NAME

administrative=re.compile(r'tiêm (?:phòng|vắc[\s-]*xin|vaccine)|xét nghiệm|thủ tục (?:visa|thị thực)|đăng ký sơ bộ|danh sách dự kiến|danh sách (?:chính thức )?sẽ được công bố|chưa (?:chốt|công bố) danh sách',re.I)
projected=re.compile(r'được kỳ vọng|mối quan tâm của dư luận|có thể (?:sẽ )?(?:được gọi|thay)|muốn (?:gọi|bổ sung)|nhiều khả năng|có khả năng|dự kiến sẽ (?:gọi|triệu tập)|ứng (?:cử )?viên|phương án [AB]|tiêm (?:phòng|vắc|vaccine)|đề cử|tiến cử|danh sách (?:sơ bộ|dự phòng)',re.I)
strong=re.compile(r'(?:đã|vừa|chính thức) (?:được |có |gọi |cho )?(?:.{0,25}?)?(?:triệu tập|gọi (?:lên|bổ sung)|hội quân|tập trung)|tân binh.{0,45}đợt tập trung|đợt tập trung.{0,60}(?:có mặt|góp mặt)|(?:được gọi|triệu tập).{0,22}(?:tham gia|tập trung|bổ sung)|có tên trong danh sách (?:triệu tập|tập trung)|có mặt ở buổi tập',re.I)
roster=re.compile(r'(?:hiện có|có (?:đến|tới))\s+\d+\s+(?:thủ môn|hậu vệ|tiền vệ|tiền đạo)\s*(?:[:：]|là)|(?:đã|thường|vừa) triệu tập (?:thêm |bổ sung )?(?:(?:bộ đôi|bộ ba|\d+)\s+[^.;]{0,65}?\s+(?:là|gồm)|(?:hậu vệ|trung vệ|thủ môn|tiền đạo|tiền vệ))|(?:danh sách|nhóm).{0,28}(?:được (?:gọi|triệu tập)|hội quân).{0,60}(?:gồm|là|như)|^(?:các )?(?:thủ môn|hậu vệ|tiền vệ|tiền đạo)[:：]',re.I)
confirmed_camp=re.compile(r'công bố danh sách|danh sách tập trung ban đầu|đã (?:hội quân|triệu tập)|(?:được gọi|triệu tập) (?:bổ sung|lên|tập trung)',re.I)
def sentences(s):
    return re.split(r'(?<=[!?])\s+|(?<!\.)(?<=\.)\s+(?=[A-ZÀ-Ỹ])',s.replace('...','…'))
def apply(article,base,registry,identify):
    result,refused=previous(article,base,registry,identify)
    parts=[s for s in article['clean_text'].splitlines() if s.strip()]
    tentative_article=bool(administrative.search(' '.join(parts[:3])) or re.search(r'danh sách chính thức sẽ được công bố',article['clean_text'],re.I))
    for eid,p in list(result.items()):
        named=[c for n in p['refs'] for c in sentences(parts[n-1]) if p['name'].casefold() in c.casefold()]
        if named and not any(strong.search(c) and not re.search(r'chưa|không được|muốn bổ sung|sẽ được công bố',c,re.I) for c in named) and (tentative_article or all(projected.search(c) for c in named)):
            # Actual, announced training lists can also be called preliminary.
            real=any(re.search(r'danh sách.{0,35}(?:đã công bố|được gọi trong đợt tập trung)|(?:đã triệu tập|được gọi trong đợt tập trung)',c,re.I) for c in named)
            if not real:result.pop(eid);refused[eid]='không có quyết định trong phạm vi nêu tên'
    for i,s in enumerate(parts):
        context=' '.join(parts[max(0,i-2):i+1])
        for c in sentences(s):
            m=roster.search(c)
            if not m or not TEAM.search(context) or projected.search(c):continue
            if re.search(r'(?:lên|cho|tới|của|tuyển|gồm)\s+(?:đội\s+)?U[ .-]?\d+|đội tuyển nữ|futsal',c,re.I):continue
            if not TEAM.search(c) and (not confirmed_camp.search(context) or re.search(r'tuyển (?:nữ|U[ .-]?\d+)|futsal',context,re.I)):continue
            segment=re.split(r'\b(?:thay (?:thế|cho)|không được|trong khi|ngoại trừ)\b',c[m.end():],maxsplit=1,flags=re.I)[0]
            for hit in registry.callups.matcher.finditer(segment):
                name=hit.group()
                if STOP_NAME.search(segment[:hit.start()]) or not name[:1].isupper():continue
                eid=identify(name,c,article['clean_text'],int(article['date'][:4]))
                if eid and eid not in refused:
                    old=result.get(eid,dict(name=name,refs=[]));result[eid]=dict(name=old['name'],refs=sorted(set(old['refs']+[i+1])))
    return result,refused
