"""Export public AEC-Bench fixtures without expected labels or oracle rationales.

The output is a reviewer-facing input packet. It is not a hidden test set.
Run from the implementation directory:
    python -m research.export_aec_bench_v0_2_review_packet --output research/review_packet
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from research.aec_benchmark_v0_2 import corpus, VERSION


def build_blinded_packet() -> dict:
    fixtures = corpus()
    rows = []
    for fixture in fixtures:
        rows.append({
            "case_id": fixture.case_id,
            "family": fixture.family,
            "variant": fixture.variant,
            "pair_group": fixture.pair_group or None,
            "input": fixture.input,
        })
    return {
        "packet": "AEC-Bench-v0.2-independent-public-fixture-review",
        "benchmark_version": VERSION,
        "packet_kind": "PUBLIC_DEVELOPMENT_FIXTURES_BLINDED_TO_EXPECTED_LABELS",
        "case_count": len(rows),
        "review_instruction": (
            "Reviewers must independently assign dispositions from the protocol. "
            "This packet intentionally excludes expected labels and oracle rationales."
        ),
        "cases": rows,
        "not_hidden": True,
        "warning": (
            "These public development fixtures are not a hidden test set. "
            "Do not describe this packet as independent validation or hidden evaluation."
        ),
    }


def write_packet(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    packet = build_blinded_packet()
    json_path = output_dir / "aec_bench_v0_2_blinded_public_fixtures.json"
    csv_path = output_dir / "aec_bench_v0_2_adjudication_template.csv"
    json_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "case_id", "family", "variant", "pair_group",
            "reviewer_disposition", "reviewer_scope", "reviewer_confidence",
            "rationale", "ambiguity_or_missing_information", "reviewer_id",
        ])
        writer.writeheader()
        for case in packet["cases"]:
            writer.writerow({
                "case_id": case["case_id"],
                "family": case["family"],
                "variant": case["variant"],
                "pair_group": case["pair_group"] or "",
                "reviewer_disposition": "",
                "reviewer_scope": "",
                "reviewer_confidence": "",
                "rationale": "",
                "ambiguity_or_missing_information": "",
                "reviewer_id": "",
            })
    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("research/review_packet"))
    args = parser.parse_args()
    json_path, csv_path = write_packet(args.output)
    print(f"wrote {json_path}")
    print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
