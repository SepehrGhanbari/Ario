#!/usr/bin/env python3
"""Pinned, read-only TB-003 evaluator. Accepts unlabeled challenge cases only.
No labels/oracle are imported. Not author-blind; real independent steward required.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types
import urllib.request

PINNED_COMMIT = "972a4199e5c52e1bdab559be623949c7d7a24b69"
URL = "https://raw.githubusercontent.com/SepehrGhanbari/Ario/" + PINNED_COMMIT + "/implementation/witness_provenance_experiment.py"
SHA256 = "71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567"
BLOB_SHA1 = "4faf010d73219af63c254097e9c135da68d60078"


# Proposed H_S research input schema. No claim about historical authenticity.
SCHEMA = "ARIO-TB003-SNAPSHOT-CHALLENGE-0.1"
ROOT_KEYS = {"schema", "kind", "cases"}
CASE_KEYS = {
    "case_id", "snapshot_sequence", "complete_transfer_surface",
    "capture", "declared_holder", "transfers", "compromised_custodians",
    "other_witness_custodians", "complete_control_surface",
    "complete_source_surface", "common_control", "shared_storage", "common_source"
}
BOOL_KEYS = {
    "complete_transfer_surface", "complete_control_surface",
    "complete_source_surface", "common_control", "shared_storage", "common_source"
}
RESERVED_GRAPH_IDS = {"A", "B", "CAPA", "CAPB", "DA", "DB", "SA", "SB", "CTRL"}
CAPTURE_KEYS = {"custodian", "sequence"}
TRANSFER_KEYS = {"from", "to", "origin", "sequence"}


def _ascii_id(value):
    return (type(value) is str and 0 < len(value) <= 128
            and all(32 <= ord(ch) <= 126 for ch in value))


def _custodian_id(value):
    return _ascii_id(value) and value not in RESERVED_GRAPH_IDS


def _sequence(value):
    return type(value) is int and 0 <= value <= 1_000_000


def _reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY:" + key)
        result[key] = value
    return result


def validate_case(item):
    """Reject unexpected fields, malformed values and graph-ID collisions."""
    if type(item) is not dict or set(item) != CASE_KEYS:
        raise ValueError("CASE_UNEXPECTED_OR_GOLD_FIELDS")
    if not _ascii_id(item["case_id"]):
        raise ValueError("INVALID_CASE_ID")
    for key in BOOL_KEYS:
        if type(item[key]) is not bool:
            raise ValueError("FLAG_NOT_BOOLEAN:" + key)
    if not _sequence(item["snapshot_sequence"]):
        raise ValueError("INVALID_SNAPSHOT_SEQUENCE")
    if not _custodian_id(item["declared_holder"]):
        raise ValueError("INVALID_OR_RESERVED_DECLARED_HOLDER")
    if (type(item["other_witness_custodians"]) is not list
            or item["other_witness_custodians"] != ["P2"]):
        raise ValueError("UNSUPPORTED_WITNESS_B_CONFIGURATION")
    cap = item["capture"]
    if type(cap) is not dict or set(cap) != CAPTURE_KEYS:
        raise ValueError("INVALID_CAPTURE_SHAPE")
    if not _custodian_id(cap["custodian"]) or not _sequence(cap["sequence"]):
        raise ValueError("INVALID_CAPTURE_VALUE")
    moves = item["transfers"]
    # 8 fixed base edges, up to two common-controller edges; MAX_EDGES=128.
    if type(moves) is not list or len(moves) > 118:
        raise ValueError("INVALID_TRANSFER_LIST")
    custodians = {"P1", "P2", "P3", "P4", "P5", cap["custodian"], item["declared_holder"]}
    for move in moves:
        if type(move) is not dict or set(move) != TRANSFER_KEYS:
            raise ValueError("TRANSFER_UNEXPECTED_OR_GOLD_FIELDS")
        if not (_custodian_id(move["from"]) and _custodian_id(move["to"])
                and _sequence(move["sequence"])
                and type(move["origin"]) is str
                and move["origin"] in ("LAB", "SELF")):
            raise ValueError("INVALID_TRANSFER_VALUE")
        custodians.update((move["from"], move["to"]))
    compromised = item["compromised_custodians"]
    if (type(compromised) is not list or len(compromised) > 64
            or any(not _custodian_id(name) for name in compromised)):
        raise ValueError("INVALID_COMPROMISE_LIST")
    if len(set(compromised)) != len(compromised):
        raise ValueError("DUPLICATE_COMPROMISED_CUSTODIAN")
    custodians.update(compromised)
    if len(custodians) > 12:
        raise ValueError("TOO_MANY_CUSTODIANS")


def parse_unlabeled_dataset(raw):
    """Fail closed on duplicated keys, unexpected keys and illegal types."""
    if type(raw) is not bytes or not 0 < len(raw) <= 4_000_000:
        raise ValueError("INVALID_DATASET_SIZE_OR_TYPE")
    try:
        dataset = json.loads(raw.decode("utf-8"),
                             object_pairs_hook=_reject_duplicate_json_keys)
    except UnicodeDecodeError as error:
        raise ValueError("INVALID_UTF8") from error
    if (type(dataset) is not dict
            or set(dataset) not in ({"schema", "cases"}, ROOT_KEYS)):
        raise ValueError("DATASET_UNEXPECTED_OR_GOLD_FIELDS")
    if dataset["schema"] != SCHEMA:
        raise ValueError("UNSUPPORTED_DATASET_SCHEMA")
    if ("kind" in dataset and
            (type(dataset["kind"]) is not str or dataset["kind"] not in
             ("PUBLIC_DEVELOPMENT_ONLY", "UNLABELED_HOLDOUT", "EXPLORATORY_TEST"))):
        raise ValueError("UNSUPPORTED_DATASET_KIND")
    items = dataset["cases"]
    if type(items) is not list or not 1 <= len(items) <= 240:
        raise ValueError("INVALID_CASE_IDS_OR_COUNT")
    ids = set()
    for item in items:
        validate_case(item)
        if item["case_id"] in ids:
            raise ValueError("DUPLICATE_CASE_ID")
        ids.add(item["case_id"])
    return dataset


def load_pinned(path: str | None):
    if path:
        raw = Path(path).read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=15) as response:
            raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()
    if digest != SHA256 or blob != BLOB_SHA1:
        raise RuntimeError("PINNED_SOURCE_HASH_MISMATCH")
    module = types.ModuleType("ario_tb003_blind_evaluator")
    sys.modules[module.__name__] = module
    exec(compile(raw.decode("utf-8"), URL if not path else path, "exec"), module.__dict__)
    return module

def make_case(p, item):
    lab, scope = p.LAB, "SNAPSHOT-RESEARCH-ONLY"
    def n(id_, kind, **kw):
        return p.Node(id_, kind, scope, lab, "challenge-steward", **kw)
    def e(id_, src, dst, kind, origin=lab, **kw):
        return p.Edge(id_, src, dst, kind, origin, "challenge-steward", **kw)
    people = {"P1", "P2", "P3", "P4", "P5", item["capture"]["custodian"], item["declared_holder"]}
    people.update(item.get("compromised_custodians", []))
    for move in item["transfers"]:
        people.add(move["from"])
        people.add(move["to"])
    if len(people) > 12:
        raise ValueError("TOO_MANY_CUSTODIANS")
    nodes = [
        n("A", "ARTIFACT"), n("B", "ARTIFACT"),
        n("CAPA", "CAPTURE", capture_sequence=item["capture"]["sequence"],
          capture_custodian=item["capture"]["custodian"]),
        n("CAPB", "CAPTURE", capture_sequence=0, capture_custodian="P2"),
        n("DA", "STORAGE_DOMAIN", object_identity="disk-a"),
        n("DB", "STORAGE_DOMAIN",
          object_identity="disk-a" if item["shared_storage"] else "disk-b"),
        n("SA", "SOURCE", object_identity="source-a"),
        n("SB", "SOURCE",
          object_identity="source-a" if item["common_source"] else "source-b"),
        n("CTRL", "CONTROL_PRINCIPAL")
    ]
    nodes.extend(n(x, "CUSTODIAN") for x in sorted(people))
    edges = [
        e("capture-A", "A", "CAPA", "CAPTURED_FROM"),
        e("capture-B", "B", "CAPB", "CAPTURED_FROM"),
        e("held-A", "A", item["declared_holder"], "HELD_BY"),
        e("held-B", "B", "P2", "HELD_BY"),
        e("stored-A", "A", "DA", "STORED_AT"),
        e("stored-B", "B", "DB", "STORED_AT"),
        e("source-A", "CAPA", "SA", "DERIVED_FROM"),
        e("source-B", "CAPB", "SB", "DERIVED_FROM")
    ]
    for i, move in enumerate(item["transfers"]):
        origin = lab if move["origin"] == "LAB" else p.SELF
        edges.append(e("transfer-" + str(i), move["from"], move["to"], "TRANSFERRED_TO",
                       origin=origin, subject_artifact_ref="A", sequence=move["sequence"]))
    if item["common_control"]:
        edges.extend([e("ctrl-A", "CTRL", "DA", "CAN_WRITE"),
                      e("ctrl-B", "CTRL", "DB", "CAN_WRITE")])
    return p.ProvenanceCase(
        p.ControlGraph(tuple(nodes), tuple(edges)), scope, ("A", "B"),
        item["complete_control_surface"], item["complete_source_surface"], lab,
        mutation_sequence=item["snapshot_sequence"],
        compromised_node_ids=tuple(item.get("compromised_custodians", []))
    )

def run(dataset_path, source_file=None):
    raw = Path(dataset_path).read_bytes()
    dataset = parse_unlabeled_dataset(raw)
    p = load_pinned(source_file)
    results = []
    for item in dataset["cases"]:
        r = p.evaluate_provenance(make_case(p, item))
        results.append({
            "case_id": item["case_id"],
            "custody_A": r.per_witness_custody[0].status,
            "admin": r.administrative_separation.status,
            "source": r.source_independence.status,
            "capture_order": r.capture_order.status,
            "evidence_admission": r.evidence_admission,
            "historical_event_truth": r.historical_event_truth
        })
    return {
        "mode": "BLIND_TO_EXTERNAL_LABELS_NOT_AUTHOR_BLIND",
        "source_commit": PINNED_COMMIT,
        "source_sha256": SHA256,
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "num_cases": len(results),
        "predictions": results
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", help="Unlabeled JSON challenge dataset")
    parser.add_argument("--source-file", help="Pinned evaluator file for offline use")
    parser.add_argument("--output", help="Optional NEW output JSON file; no overwrite")
    args = parser.parse_args()
    result = run(args.dataset, args.source_file)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with Path(args.output).open("x", encoding="utf-8") as out:
            out.write(output)
    else:
        print(output, end="")

if __name__ == "__main__":
    main()
