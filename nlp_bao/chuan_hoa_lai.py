"""Chuẩn hóa lại phản hồi Gemini đã lưu sau khi sửa cách liên kết thực thể."""
import argparse
import json
import re
from pathlib import Path
import tempfile

import trich_xuat as tx


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("articles", "entities", "predictions", "output"):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    if args.output.resolve() == args.predictions.resolve():
        cli.error("Dùng thư mục đầu ra mới để lưu được cả hai phiên bản.")
    registry = tx.Registry(args.entities)
    args.output.mkdir(parents=True, exist_ok=True)
    graph_hash = tx.digest(args.entities.read_bytes())
    facts_hash = tx.digest(args.entities.with_name("facts.csv").read_bytes())
    for line in args.articles.read_text().splitlines():
        a = json.loads(line)
        aid = a["article_id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+",aid):
            raise ValueError(aid)
        old = json.loads((args.predictions / (aid+".json")).read_bytes())
        meta = dict(old["input"])
        if meta["article_id"] != aid or meta["canonical_url"] != a["canonical_url"] or meta["text_sha256"] != tx.digest(a["clean_text"].encode()):
            raise ValueError("Sai phiên bản " + aid)
        if meta["graph_sha256"] != graph_hash or meta["facts_sha256"] != facts_hash:
            raise ValueError("Sai snapshot A3")
        records = old.get("api_edges")
        if records is None:
            records = [dict(src=e["src"], rel=e["relation_type"], dst=e["dst"],
                            paragraphs=[p["paragraph"] for p in e["evidence"]]) for e in old["edges"]]
            records += [e["raw"] for e in old["rejected"]]
        edges, rejected = tx.normalize_records(records, a, registry)
        meta["inference_code_sha256"] = meta.get("inference_code_sha256", meta["code_sha256"])
        meta["code_sha256"] = tx.digest(Path(tx.__file__).read_bytes())
        meta["aliases_sha256"] = tx.digest(Path(tx.__file__).with_name("ten_clb.tsv").read_bytes())
        for field, filename in (("callup_code_sha256","trieu_tap.py"),("callup_names_sha256","ten_tuyen_thu.tsv")):
            meta[field] = tx.digest(Path(tx.__file__).with_name(filename).read_bytes())
        result = dict(old, input=meta, edges=edges, rejected=rejected)
        with tempfile.NamedTemporaryFile(dir=args.output,mode="w",encoding="utf-8",delete=False) as stream:
            json.dump(result,stream,ensure_ascii=False)
            staged = Path(stream.name)
        staged.replace(args.output / (aid+".json"))


if __name__ == "__main__":
    main()
