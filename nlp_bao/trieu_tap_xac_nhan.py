"""High precision extractor for senior men's call-ups. No data or labels from test files."""
import re,unicodedata
from collections import defaultdict
def n(s):return unicodedata.normalize('NFC',s).casefold()
senior=r'(?:đội\s+tuyển|đtqg|tuyển)\s+(?:quốc gia(?:\s+(?:việt nam|vn))?|việt nam|vn)\b'
other=r'\bu[\s.‐-]*(?:1[6789]|2[0123])\b|tuyển nữ|đội nữ|futsal'
uncertain=r'khả năng|dự đoán|dự kiến|chưa (?:công bố|chốt|quyết định)|có thể|danh sách sơ bộ|đề xuất|tầm ngắm|sẽ (?:được )?(?:quyết định|gọi|triệu tập)|nếu |cân nhắc|định gọi'
negative=r'không (?:được |có |gọi|triệu tập)|bị loại|bị gạch|vắng mặt|lỡ hẹn|bỏ qua'
action=r'(?:triệu tập(?: bổ sung)?|gọi (?:bổ sung|trở lại|thêm|lên tuyển)|điền tên|đã gọi|quyết định gọi)'
official=r'công bố|chốt danh sách|triệu tập|đã gọi|quyết định gọi|đã chọn|đệ trình|được gọi bổ sung'
positions=r'(?:các )?(?:thủ môn|hậu vệ|tiền vệ|tiền đạo|trung vệ)'
def prepare(rows):
 names=defaultdict(set)
 for r in rows:
  if 'Player' not in r['role']:continue
  name=n(re.sub(r'\s*\([^()]*\)\s*$','',r['canonical_name']))
  if len(name.split())>=2:
   names[name].add(r['entity_id']);names[' '.join(name.split()[-2:])].add(r['entity_id'])
 return names
def extract(article,names):
 blocks=unicodedata.normalize('NFC',article['clean_text']).split('\n\n');title=n(article['title']);lead=n(' '.join(blocks[:2]))
 if not re.search(senior,title+' '+lead) or re.search(other,title) and not re.search(senior,title):return {}
 valid=any(re.search(official,s) and not re.search(uncertain,s) for s in (title,lead))
 if not valid:return {}
 # Competing youth/team lists and proposed calls cannot establish a positive scope.
 if re.search(uncertain,title+' '+n(blocks[0])):return {}
 found={};scope=False
 for i,para in enumerate(blocks,1):
  p=n(para)
  if re.search(other,p) or re.search(r'dự kiến|danh sách sơ bộ|đội hình ra sân',p):scope=False
  if re.search(r'danh sách (?:cụ thể|triệu tập|tập trung|cầu thủ|đội tuyển)|thành phần đội tuyển',p) and not re.search(other+'|'+uncertain,p):scope=True
  for sent in re.split(r'(?<=[.!?])\s+',para):
   t=n(sent);regions=[]
   if re.search(other+'|'+uncertain+'|'+negative,t):continue
   if re.match(r'^\W*'+positions+r'\s*[:(]',t) and (scope or re.search(official,lead)):regions=[t]
   else:
    for m in re.finditer(action,t):
     # Agent names preceding the verb must not become called players.
     aft=t[m.end():]
     aft=re.split(r'\b(?:thay (?:cho|thế)|trám (?:vào )?chỗ|ngoại trừ|ngoài ra|bởi vì|để thay|nhưng|trong khi|thay vì|lên (?:đội )?tuyển|vào (?:đội )?tuyển)\b',aft,maxsplit=1)[0]
     if not t[:m.start()].rstrip().endswith('được'):regions.append(aft)
     before=t[:m.start()]
     if before.rstrip().endswith('được'):
      # Accept only the immediate grammatical subject before the passive.
      match=re.search(r'((?:\w+[ -]){1,5}\w+)\s+(?:(?:vừa|lần đầu|chính thức|đã)\s+)*được\s*$',before)
      if match:regions.append(match[1])
   for region in regions:
    hits=[]
    for alias,ids in names.items():
     if len(ids)!=1:continue
     for m in re.finditer(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',region):
      hits.append((m.start(),m.end(),alias,next(iter(ids))))
    occupied=set()
    for a,b,alias,eid in sorted(hits,key=lambda h:-(h[1]-h[0])):
     if occupied.intersection(range(a,b)):continue
     occupied.update(range(a,b))
     # Short, context-dependent nicknames are restricted to a formal positional list.
     if len(alias.split())<3 and not re.match(r'^\W*'+positions+r'\s*[:(]',t):continue
     item=found.setdefault(eid,{'name':alias,'refs':[]})
     if i not in item['refs']:item['refs'].append(i)
 return found
