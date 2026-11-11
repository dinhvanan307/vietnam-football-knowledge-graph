"""Structural measures from the locked A10 release. Requires networkx==3.5."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import networkx as nx

SEED = 22


def read_table(path, sep=","):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=sep))


def rank(scores, entities, limit=6):
    keys = sorted(scores, key=lambda k: (-scores[k], entities[k]["canonical_name"], k))
    return [
        {"id": k, "name": entities[k]["canonical_name"], "value": scores[k]}
        for k in keys[:limit]
    ]


def describe(graph, entities, unit_count, centrality=False, communities=False):
    """Use simple undirected topology. Only teammate community weights count distinct matches."""
    assert not nx.number_of_selfloops(graph)
    groups = sorted(nx.connected_components(graph), key=len, reverse=True)
    largest = graph.subgraph(groups[0]).copy()
    # One BFS per vertex gives the diameter and distance sum on the same component.
    distance_sum = diameter = 0
    for _, distances in nx.all_pairs_shortest_path_length(largest):
        diameter = max(diameter, max(distances.values()))
        distance_sum += sum(distances.values())
    size = len(largest)
    degrees = dict(graph.degree())
    output = {
        "nodes": len(graph),
        "edge_observations": unit_count,
        "distinct_pairs": graph.number_of_edges(),
        "mean_degree": sum(degrees.values()) / len(graph),
        "median_degree": median(degrees.values()),
        "degree_one_count": sum(v == 1 for v in degrees.values()),
        "density": nx.density(graph),
        "components": len(groups),
        "largest_component": size,
        "largest_component_share": size / len(graph),
        "mean_distance_largest_component": distance_sum / (size * (size - 1))
        if size > 1
        else 0,
        "diameter_largest_component": diameter,
        "mean_clustering": nx.average_clustering(graph),
        "transitivity": nx.transitivity(graph),
        "top_degree": rank(degrees, entities),
    }
    if centrality:
        values = nx.betweenness_centrality(graph, weight=None, normalized=True)
        output["top_betweenness"] = rank(values, entities)
    if communities:
        weight = "matches"
        partition = nx.community.louvain_communities(
            graph, weight=weight, seed=SEED, resolution=1
        )
        output["louvain"] = {
            "weight": weight,
            "seed": SEED,
            "resolution": 1,
            "count": len(partition),
            "sizes": sorted(map(len, partition), reverse=True),
            "modularity": nx.community.modularity(graph, partition, weight=weight),
        }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", type=Path, help="Extracted A10 submission directory")
    parser.add_argument("output", type=Path, help="JSON destination")
    args = parser.parse_args()
    release = json.loads((args.release / "graph/manifest.json").read_text())
    assert release["version"] == "A10"
    for name, signature in release["sha256"].items():
        assert (
            hashlib.sha256((args.release / "graph" / name).read_bytes()).hexdigest()
            == signature
        )
    entities = {
        r["entity_id"]: r for r in read_table(args.release / "graph/entities.csv")
    }
    facts = {r["fact_id"]: r for r in read_table(args.release / "graph/facts.csv")}
    folder = args.release / "phan_lop"
    full = nx.Graph()
    full.add_nodes_from(sorted(entities))
    layer_graphs = {}
    fact_ids = set()
    counts = {}
    for name in ("xa_hoi", "boi_canh"):
        g = nx.Graph()
        rows = read_table(folder / (name + ".tsv"), "\t")
        for r in rows:
            key = r["fact_id"]
            raw = facts[key]
            assert key not in fact_ids and (
                raw["src_id"],
                raw["dst_id"],
                raw["relation_type"],
            ) == (r["src_id"], r["dst_id"], r["relation"])
            fact_ids.add(key)
            g.add_edge(r["src_id"], r["dst_id"])
        layer_graphs[name] = g
        full.add_edges_from(g.edges)
        counts[name] = len(rows)
    assert fact_ids == facts.keys()
    pairs = read_table(folder / "dong_doi.tsv", "\t")
    witnesses = read_table(folder / "dong_doi_chung_cu.tsv", "\t")
    matches = defaultdict(set)
    for row in witnesses:
        for index in (1, 2):
            f = facts[row[f"fact{index}"]]
            assert (f["src_id"], f["dst_id"], f["club_id"], f["relation_type"]) == (
                row[f"player{index}"],
                row["match"],
                row["club"],
                "DA_CHINH_TRONG_TRAN",
            )
        matches[row["player1"], row["player2"]].add(row["match"])
    teammates = nx.Graph()
    for row in pairs:
        pair = (row["player1"], row["player2"])
        weight = int(row["matches"])
        assert weight == len(matches[pair]) and not teammates.has_edge(*pair)
        teammates.add_edge(*pair, matches=weight)
    assert len(matches) == len(pairs)
    layers = {
        name: describe(g, entities, counts[name], centrality=(name == "xa_hoi"))
        for name, g in layer_graphs.items()
    }
    data = {
        "version": release["version"],
        "networkx": nx.__version__,
        "input_sha256": release["sha256"],
        "full": describe(full, entities, len(facts)),
        **layers,
        "dong_doi": describe(
            teammates, entities, len(witnesses), centrality=True, communities=True
        ),
    }
    data["dong_doi"]["matches_with_verified_pairs"] = len(
        {r["match"] for r in witnesses}
    )
    data["dong_doi"]["unique_matches_in_full"] = sum(
        e["type"] == "Match" for e in entities.values()
    )
    weights = Counter(r["matches"] for r in pairs)
    data["dong_doi"]["pairs_seen_once"] = weights["1"]
    maximum = max(int(r["matches"]) for r in pairs)
    data["dong_doi"]["top_pairs"] = [r for r in pairs if int(r["matches"]) == maximum]
    data["dong_doi"]["highest_weighted_degree"] = rank(
        dict(teammates.degree(weight="matches")), entities
    )
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
