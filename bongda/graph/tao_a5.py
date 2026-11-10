"""Dựng A5 từ A4 đã khóa, đưa thẻ của cán bộ ra khỏi tập sự kiện cầu thủ."""

import argparse
import csv
import json
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import mwparserfromhell as mw

from bongda.core.ban_giao import enc, idx, jlines, sha, table, verify
from bongda.extract.doc_bien_ban import BOX_NAMES, STAFF_TITLE, date_vi, has_staff_title, param

A4_CHECKSUM = "410ddb522516fdca02b759e9b7f0b158b28959aa72b14790ff793d2135dd1396"
YELLOW = "NHAN_THE_VANG_KHI_GAP"


def write_table(path, rows, delimiter=","):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys(), delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def check_card(node, fact, evidence, article, raw, clubs):
    """Đối chiếu người, đội, ngày, phút thẻ và vị trí dòng ghi thẻ trong bản wiki."""
    revision = raw["revisions"][0]
    if (str(raw["pageid"]), str(revision["revid"])) != (article["pageid"], article["revid"]):
        raise ValueError("Sai bản sửa đổi Wikipedia")
    original = revision["slots"]["main"]["content"]
    box_text = original[evidence["start"] : evidence["end"]]
    if box_text != evidence["quote"] or article["clean_text"] != original:
        raise ValueError("Đoạn biên bản không khớp bản gốc: " + fact["fact_id"])
    boxes = [
        t
        for t in mw.parse(box_text).filter_templates(recursive=False)
        if str(t.name).strip().casefold() in BOX_NAMES
    ]
    if len(boxes) != 1:
        raise ValueError("Thiếu hoặc trùng biên bản: " + fact["fact_id"])
    box = boxes[0]
    day, home, away = fact["event_key"].split(":")
    if date_vi(param(box, "date", "ngày"), article["title"]) != day or day != fact["period"]:
        raise ValueError("Sai ngày trận")
    name = node["canonical_name"]
    marker = re.compile(
        r"(?P<actor>[^{}]+?)\s*\{\{\s*(?:yel|thẻ vàng)\s*\|\s*(?P<minute>\d+(?:\+\d+)?)\s*\}\}", re.I
    )
    matches = []
    for side, own, opponent in ((1, home, away), (2, away, home)):
        fragment = param(
            box, f"goals{side}", f"bàn thắng {side}", f"bàn thắng{side}", f"bàn thắng cho đội {side}"
        )
        for line in re.split(r"(?i)<br\s*/?>|\n", fragment):
            line = line.strip().lstrip("*:").strip()
            hit = marker.match(line)
            if not hit or not has_staff_title(hit["actor"]):
                continue
            actor = mw.parse(hit["actor"])
            visible = actor.strip_code().strip()
            names = {visible, STAFF_TITLE.sub("", visible).strip()}
            names.update(str(link.title).strip() for link in actor.filter_wikilinks())
            if name not in names:
                continue
            if opponent != fact["dst_id"]:
                raise ValueError("Đội đối phương không khớp " + fact["fact_id"])
            matches.append((own, opponent, hit, visible))
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("Có nhiều thẻ khớp người và đội: " + fact["fact_id"])
    own, opponent, hit, visible = matches[0]
    excerpt = hit.group()
    if box_text.count(excerpt) != 1:
        raise ValueError("Chưa định vị được chính xác dòng nhận thẻ")
    start = evidence["start"] + box_text.index(excerpt)
    report = re.search(r"https?://(?:www\.)?vpf\.vn/[^\s\]<>|]+", param(box, "report"))
    return dict(
        fact_id=fact["fact_id"],
        entity_id=node["entity_id"],
        name_in_source=visible,
        old_node_name=name,
        old_role=node["role"],
        old_relation=fact["relation_type"],
        event_key=fact["event_key"],
        match_date=day,
        minute=hit["minute"],
        team_id=own,
        opponent_id=opponent,
        team_in_graph=clubs[own]["canonical_name"],
        opponent_in_graph=clubs[opponent]["canonical_name"],
        evidence_id=evidence["evidence_id"],
        article_id=article["article_id"],
        revid=article["revid"],
        source_url=article["canonical_url"],
        match_report_url=report[0] if report else "",
        start=start,
        end=start + len(excerpt),
        source_line=excerpt,
        decision="exclude_from_player_graph",
        reason="Biên bản ghi chức danh cán bộ trước tên người nhận thẻ.",
    )


def build(parent, dest):
    manifest = parent / "checksums.json"
    if sha(manifest.read_bytes()) != A4_CHECKSUM:
        raise ValueError("Snapshot nguồn không khớp A4 đã bàn giao.")
    for name, digest in json.loads(manifest.read_bytes()).items():
        if sha((parent / name).read_bytes()) != digest:
            raise ValueError("Tệp A4 sai SHA-256: " + name)
    verify(parent, False, True)
    nodes = idx(table(parent / "entities.csv"), "entity_id")
    facts = table(parent / "facts.csv")
    articles = idx(jlines(parent / "articles.jsonl"), "article_id")
    evidence = jlines(parent / "evidence.jsonl")
    support = defaultdict(list)
    for row in evidence:
        support[row["fact_id"]].append(row)
    staff_ids = {
        nid
        for nid, n in nodes.items()
        if n["type"] == "Person"
        and "Player" in n["role"].split("|")
        and has_staff_title(n["canonical_name"])
    }
    kept, removed, audit, raw_pages = [], set(), [], {}
    for f in facts:
        tagged_node = f["src_id"] in staff_ids or f["dst_id"] in staff_ids
        if f["relation_type"] != YELLOW or f["method"] != "wiki_match_event":
            if tagged_node:
                raise ValueError("Cần rà riêng quan hệ khác thẻ vàng: " + f["fact_id"])
            kept.append(f)
            continue
        hits = []
        for ev in support[f["fact_id"]]:
            if not has_staff_title(ev["quote"]):
                continue
            a = articles[ev["article_id"]]
            if a["article_id"] not in raw_pages:
                raw_pages[a["article_id"]] = json.loads((parent / "raw" / a["raw_sha256"]).read_bytes())[
                    "query"
                ]["pages"][0]
            audited = check_card(nodes[f["src_id"]], f, ev, a, raw_pages[a["article_id"]], nodes)
            if audited:
                hits.append(audited)
        if not hits and not tagged_node:
            kept.append(f)
            continue
        if not hits or len(hits) != len(support[f["fact_id"]]):
            raise ValueError("Bằng chứng vai trò thiếu hoặc bất đồng: " + f["fact_id"])
        audit.extend(hits)
        removed.add(f["fact_id"])
    if (
        not staff_ids.issubset({r["entity_id"] for r in audit})
        or {r["fact_id"] for r in audit} != removed
    ):
        raise ValueError("Chưa đối chiếu toàn bộ nút hoặc cạnh bị ảnh hưởng")
    if not any(r["fact_id"] == "f_5d26c9fccdf48f724e3c" for r in audit):
        raise ValueError("Chưa sửa ca N034")
    unaffected = [n for i, n in nodes.items() if i not in staff_ids]
    if {f[k] for f in kept for k in ("src_id", "dst_id")} != {n["entity_id"] for n in unaffected}:
        raise ValueError("Sửa lỗi làm phát sinh nút cô lập ngoài dự kiến.")
    for name in ("articles.jsonl", "manifest.json", "canh_bao_da_duyet.tsv", "quyet_dinh.tsv"):
        shutil.copyfile(parent / name, dest / name)
    shutil.copytree(parent / "raw", dest / "raw")
    write_table(dest / "staff_cards.tsv", audit, "\t")
    write_table(dest / "entities.csv", unaffected)
    write_table(dest / "facts.csv", kept)
    for name, rows in (
        ("evidence.jsonl", evidence),
        ("event_attributes.jsonl", jlines(parent / "event_attributes.jsonl")),
    ):
        with (dest / name).open("w") as stream:
            for row in rows:
                if row["fact_id"] not in removed:
                    stream.write(enc(row) + "\n")
    verify(dest, False, True)
    parent_stats = json.loads((parent / "stats.json").read_text())
    stats = {
        k: parent_stats[k]
        for k in ("article_count", "article_sources", "press_edges", "press_primary_articles")
    }
    stats.update(
        version="A5",
        parent="A4",
        parent_checksums_sha256=A4_CHECKSUM,
        nodes=len(unaffected),
        edges=len(kept),
        relations=Counter(f["relation_type"] for f in kept),
        node_types=Counter(n["type"] for n in unaffected),
        methods=Counter(f["method"] for f in kept),
        evidence_count=len(evidence) - len(audit),
        removed_player_nodes=len(staff_ids),
        removed_player_cards=len(removed),
        reviewed_spans=len(audit),
        reviewed_revisions=len({r["revid"] for r in audit}),
        semantic_precision="not_measured_on_A5",
    )
    (dest / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    sums = {p.name: sha(p.read_bytes()) for p in sorted(dest.iterdir()) if p.is_file()}
    (dest / "checksums.json").write_text(json.dumps(sums, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", type=Path)
    parser.add_argument("dest", type=Path)
    args = parser.parse_args()
    parent, dest = args.parent.resolve(), args.dest.resolve()
    if dest.exists() or dest.is_relative_to(parent):
        raise SystemExit("Chọn thư mục đích mới bên ngoài snapshot A4.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        stage = Path(tmp) / "snapshot"
        stage.mkdir()
        build(parent, stage)
        stage.rename(dest)


if __name__ == "__main__":
    main()
