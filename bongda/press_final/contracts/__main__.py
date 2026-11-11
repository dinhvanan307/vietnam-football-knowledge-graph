"""Read one UTF-8 JSON article and emit either rule predictions or a review packet."""

import argparse
import json
from pathlib import Path

from . import context, rules, screen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "article", type=Path, help="JSON object with title, day and paragraphs"
    )
    parser.add_argument("--mode", choices=("k1", "k2", "review"), default="k2")
    args = parser.parse_args()
    article = json.loads(args.article.read_text(encoding="utf-8"))
    if not isinstance(article, dict) or not isinstance(article.get("paragraphs"), list):
        parser.error("expected an object with a paragraphs array")
    if not all(isinstance(p, str) for p in article["paragraphs"]):
        parser.error("each paragraph must be a string")
    if not all(isinstance(article.get(k), str) for k in ("title", "day")):
        parser.error("title and day must be strings")
    if args.mode == "review":
        result = screen.packets(article)
    else:
        extractor = rules.extract if args.mode == "k1" else context.extract
        result = extractor(article["title"], article["day"], article["paragraphs"])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
