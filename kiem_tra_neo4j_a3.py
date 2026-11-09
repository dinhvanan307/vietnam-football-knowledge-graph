"""Chụp toàn bộ nội dung logic của database để so sánh trước/sau, chỉ đọc."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from neo4j import GraphDatabase, READ_ACCESS
from ban_giao import enc


def fingerprint(session):
    digest = hashlib.sha256()
    count = Counter()
    relations = Counter()
    for key, query in (
        ("nodes", "MATCH (n) RETURN properties(n) AS props, labels(n) AS labels ORDER BY n.entity_id"),
        ("edges", """MATCH (s)-[r]->(d) RETURN s.entity_id AS s, type(r) AS t, d.entity_id AS d,
                     properties(r) AS props ORDER BY r.fact_id"""),
    ):
        for row in session.run(query):
            item = row.data()
            if key == "nodes":
                item["labels"].sort()
            else:
                relations[item["t"]] += 1
            digest.update((enc(item) + "\n").encode())
            count[key] += 1
    return dict(nodes=count["nodes"], edges=count["edges"], types=len(relations),
                relations=dict(sorted(relations.items())), graph_sha256=digest.hexdigest())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", choices=("A2", "A3"))
    args = parser.parse_args()
    port = {"A2": 7687, "A3": 7689}[args.version]
    pw = dict(s.split("=", 1) for s in Path(".env").read_text().splitlines() if "=" in s)["NEO4J_PASSWORD"]
    with GraphDatabase.driver(f"bolt://127.0.0.1:{port}", auth=("neo4j", pw)) as driver:
        with driver.session(database="neo4j", default_access_mode=READ_ACCESS) as session:
            print(json.dumps(fingerprint(session), ensure_ascii=False, sort_keys=True))
