from pathlib import Path
import hashlib,json,sys
from bongda.a7.paths import RELEASE as B
from bongda.storage.nhap_neo4j_a3 import import_snapshot
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
if __name__=='__main__':
    snap=B/'snapshot'
    for name,h in json.loads((snap/'checksums.json').read_bytes()).items():
        if sha(snap/name)!=h:raise ValueError('Bad release checksum: '+name)
    stats=json.loads((snap/'stats.json').read_bytes())
    if stats['gate_sha256']!=sha(B/'nghiem_thu.json'):raise ValueError('Different evaluation')
    gate=json.loads((B/'nghiem_thu.json').read_bytes())['per_type']
    assert all(gate[rel]['pass_gate'] for rel in stats['import_actions']['new'])
    import_snapshot(snap,uri='bolt://127.0.0.1:7696',env_file=B/'.env',path=B/'import',project='d22_press_a7',report_dir=B)
