"""Build A9 only from the frozen A8 press evidence and locally archived newspapers."""
import argparse,json,tempfile
from pathlib import Path
from bongda.press_final.network import Graph
from bongda.press_final.tables import result_tables,transfers_and_squads
from bongda.press_final.profiles import club_cards,add_club_cards
from bongda.press_final.editorial import add_text
from bongda.press_final.youth import add_youth

from bongda.press_final.fixtures import games,apply_games

def build(parent,root,dest,version="A9"):
    if dest.exists(): raise FileExistsError("Use a new directory: "+str(dest))
    g=Graph(parent/"snapshot",parent/"mau_100_da_ra.tsv",version)
    result_tables(g,root/"thu_lam_dong")
    cards=list(club_cards(root/"ho_so_bao"))
    for *_,rows in cards:
        for pid,name,q in rows:g.register_person_names(pid,name)
    historic=list(games(root/"phieu_tran"))
    for *_,rows in historic:
        for pid,name,*_ in rows:g.register_person_names(pid,name)
    transfers_and_squads(g,root/"thu_vnexpress")
    apply_games(g,historic)
    add_club_cards(g,cards)
    add_youth(g,root/"doi_tre")
    add_text(g,root)
    with tempfile.TemporaryDirectory(dir=dest.parent) as work:
        snap=Path(work)/"snapshot"; stats=g.dump(snap);snap.rename(dest)
    return stats
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("parent","root","output"):p.add_argument(n,type=Path)
    p.add_argument("--version",choices=["A9","A9.1"],default="A9")
    a=p.parse_args();print(json.dumps(build(a.parent,a.root,a.output,a.version),ensure_ascii=False,indent=2))
