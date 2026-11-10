"""Chốt tầng ngoài theo khung đã lưu; đọc lại raw để lập phiếu chưa có nhãn."""
import json
import random
import unicodedata
from collections import Counter, defaultdict

from lxml import html
from mwparserfromhell import parse

from bongda.paths import evaluation_dir
from bongda.evaluate.a3.chuan_bi import A3, lines, digest, tsv, put_tsv, verify_inputs
from bongda.evaluate.a2.chuan_bi_doi_chieu import flat

HERE = evaluation_dir("overall")
FIRST = evaluation_dir("a3")
SEED = 2026110804
SIZE = 100
FIRST_SHA = {
    "phieu_cham.tsv": "cee13579ea761956bca90cb12f5dc9f73826819a097384f378216e9154efc07d",
    "mau_khoa.txt": "a8b02fdcb9b3bab73814b2d2604803711150841e2239394974be8e38124d6d47",
    "canh_loai_khoi_khung.tsv": "d12723df18af1c1e6561492186764738f901efa568772e994f7f0ace85a7324e",
    "doi_chieu_200_canh.tsv": "c9ba1a278fe9334286c4a8b4ced47d506293849cb9592320ea6d3df08e1b30c5",
}


def lock_sample():
    HERE.mkdir(parents=True, exist_ok=True)
    verify_inputs()
    for path, expected in FIRST_SHA.items():
        accepted = {expected}
        if path == "doi_chieu_200_canh.tsv":
            # Cùng 200 dòng dữ liệu với tiêu đề cột đã chuẩn hóa.
            accepted.add("786857f1597f1880265c6a109f03cdec46633d6c5353bc9b4db4c9d0ff97ce89")
        if digest((FIRST/path).read_bytes()) not in accepted:
            raise ValueError(f"Thay đổi đầu vào đã khóa: {path}")
    facts = {r["fact_id"]: r for r in tsv(A3/"facts.csv", ",")}
    manifest = json.loads((FIRST/"khung_mau.json").read_text())
    assert digest((A3/"facts.csv").read_bytes()) == manifest["snapshot_facts_sha256"]
    rows = tsv(FIRST/"canh_loai_khoi_khung.tsv")
    outside = sorted(r["fact_id"] for r in rows)
    inside = sorted(set(facts) - set(outside))
    assert len(rows) == len(set(outside)) == 1374 and len(inside) == 16782
    assert set(outside) <= set(facts) and len(facts) == 18156
    assert digest(("\n".join(inside)+"\n").encode()) == manifest["eligible_sha256"]
    old_sample = (FIRST/"mau_khoa.txt").read_text().splitlines()
    assert random.Random(manifest["seed"]).sample(inside, 200) == old_sample
    sample = random.Random(SEED).sample(outside, SIZE)
    ids = "\n".join(sample)+"\n"
    path = HERE/"mau_khoa_ngoai.txt"
    if path.exists() and path.read_text() != ids:
        raise ValueError("Mẫu ngoài thay đổi.")
    path.write_text(ids)
    assert len(set(sample)) == SIZE and not set(sample).intersection(old_sample)
    return facts, sample


def original_text(article):
    raw = (A3/"raw"/article["raw_sha256"]).read_bytes()
    assert digest(raw) == article["raw_sha256"]
    if article["source_kind"] == "press":
        return html.fromstring(raw.decode("utf-8")).text_content()
    page = next(p for p in json.loads(raw)["query"]["pages"] if str(p["pageid"]) == article["pageid"])
    rv = next(r for r in page["revisions"] if str(r["revid"]) == article["revid"])
    return unicodedata.normalize("NFC", rv["slots"]["main"]["content"])


def main():
    facts, sample = lock_sample()
    selected = set(sample)
    articles = {r["article_id"]: r for r in lines(A3/"articles.jsonl")}
    nodes = {r["entity_id"]: r["canonical_name"] for r in tsv(A3/"entities.csv", ",")}
    attrs = {r["fact_id"]: r for r in lines(A3/"event_attributes.jsonl")}
    cached = {}
    supports = defaultdict(list)
    for e in lines(A3/"evidence.jsonl"):
        if e["fact_id"] not in selected:
            continue
        aid = e["article_id"]
        a = articles[aid]
        if aid not in cached:
            cached[aid] = original_text(a)
        raw = cached[aid]
        text = a["clean_text"]
        assert text[e["start"]:e["end"]] == e["quote"] and digest(text.encode()) == a["clean_sha256"]
        context = text[e["context_start"]:e["context_end"]] if "context_start" in e else ""
        if a["source_kind"] == "wiki" and a["story_group"].startswith("season:"):
            assert raw == text
        else:
            original = parse(raw).strip_code() if a["source_kind"] == "wiki" else raw
            assert flat(e["quote"]) in flat(original) and flat(context) in flat(original)
        supports[e["fact_id"]].append(dict(**e, title=a["title"], revid=a["revid"], url=a["canonical_url"],
                                           source=a["source"], source_kind=a["source_kind"],
                                           published_at=a["published_at"], context=context))
    packets = []
    for i, fid in enumerate(sample, 1):
        f = facts[fid]
        support = sorted(supports[fid], key=lambda e:(e["evidence_id"]!=f["evidence_id"], e["evidence_id"]))
        assert support and support[0]["evidence_id"] == f["evidence_id"]
        packets.append(dict(no=f"N{i:03}", **{k:f[k] for k in ("fact_id","src_id","dst_id","event_key","period","method","relation_type")},
                            src=nodes[f["src_id"]], dst=nodes[f["dst_id"]], attributes=attrs.get(fid,{}), support=support))
    (HERE/"ho_so_ngoai.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in packets))
    print(Counter(p["method"] for p in packets), "support", sum(map(len,supports.values())), "documents", len(cached))


if __name__ == "__main__":
    main()
