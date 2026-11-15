"""Task-scoped comparative policy baselines for AEC-Bench v0.2.

The typed candidate is benchmark-side code, not an Ario runtime invocation.
Simple baselines are deliberately applicable only to the task lanes they model.
No overall/composite score is calculated.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from research.aec_benchmark_v0_2 import FAMILIES, _evaluate, corpus

METHODS = (
    "raw_relay_count",
    "majority_vote",
    "hash_integrity_only",
    "ario_typed_policy_candidate",
)
TARGET_FIELDS = {
    "lineage_dependence": "root_count",
    "relay_replay_identity": "unique_senders",
    "claim_disposition": "status",
    "scope": "scope",
    "schema_version": "schema",
    "integrity_authenticity": "integrity",
    "temporal_provenance": "temporal",
    "revision_history": "history",
    "composition_dependencies": "composition",
    "uncertainty_abstention": "status",
}
APPLICABLE = {
    "raw_relay_count": {"lineage_dependence", "relay_replay_identity"},
    "majority_vote": {"claim_disposition"},
    "hash_integrity_only": {"integrity_authenticity"},
    "ario_typed_policy_candidate": set(FAMILIES),
}


def _raw_relay(fixture: Any) -> dict[str, Any]:
    d = fixture.input
    if fixture.family == "lineage_dependence":
        # Deliberately naive: each reporting source is counted as independent.
        return {"root_count": len(d["sources"])}
    if fixture.family == "relay_replay_identity":
        # Deliberately naive: every received record is counted as a distinct sender.
        return {"unique_senders": len(d["records"])}
    raise ValueError("raw relay baseline is not applicable to this family")


def _majority_vote(fixture: Any) -> dict[str, str]:
    labels = fixture.input["labels"]
    if not labels:
        return {"status": "UNKNOWN"}
    counts = Counter(labels)
    winner, count = counts.most_common(1)[0]
    if count <= len(labels) / 2:
        return {"status": "UNKNOWN"}
    mapping = {
        "SUPPORTS": "SUPPORTED",
        "CONTRADICTS": "CONTRADICTED",
        "REFUTES": "CONTRADICTED",
        "UNSUPPORTED": "REJECTED",
        "UNKNOWN": "UNKNOWN",
    }
    return {"status": mapping.get(winner, "UNKNOWN")}


def _hash_integrity_only(fixture: Any) -> dict[str, str]:
    d = fixture.input
    if d.get("algorithm_unsupported") or d["digest"] is None:
        integrity = "UNKNOWN"
    elif d["digest"] in {"invalid", "altered"}:
        integrity = "INVALID"
    elif d["digest"] == "valid":
        integrity = "VALID"
    else:
        integrity = "UNKNOWN"
    # This baseline intentionally does not inspect or infer authentication.
    return {"integrity": integrity, "authentication": "NOT_CHECKED"}


def evaluate_method(fixture: Any, method: str) -> dict[str, Any]:
    if method not in METHODS:
        raise ValueError(f"unknown method: {method}")
    if fixture.family not in APPLICABLE[method]:
        raise ValueError(f"{method} is not applicable to {fixture.family}")
    if method == "raw_relay_count":
        return _raw_relay(fixture)
    if method == "majority_vote":
        return _majority_vote(fixture)
    if method == "hash_integrity_only":
        return _hash_integrity_only(fixture)
    return _evaluate(fixture)


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _confusion(expected: list[str], observed: list[str], labels: tuple[str, ...]) -> dict[str, Any]:
    matrix = {actual: {predicted: 0 for predicted in labels} for actual in labels}
    for actual, predicted in zip(expected, observed):
        if actual in matrix and predicted in matrix[actual]:
            matrix[actual][predicted] += 1
    per_class = {}
    f1_values = []
    for label in labels:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in labels if other != label)
        fn = sum(matrix[label][other] for other in labels if other != label)
        precision = _ratio(tp, tp + fp)
        recall = _ratio(tp, tp + fn)
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall > 0
            else (0.0 if precision == 0 or recall == 0 else None)
        )
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1}
        if f1 is not None:
            f1_values.append(f1)
    return {
        "labels": list(labels),
        "confusion_matrix_actual_by_predicted": matrix,
        "per_class": per_class,
        "macro_f1": _ratio(sum(f1_values), len(f1_values)),
    }


def _observations(fixtures: tuple[Any, ...], method: str) -> list[dict[str, Any]]:
    rows = []
    for f in fixtures:
        if f.family not in APPLICABLE[method]:
            continue
        observed = evaluate_method(f, method)
        target = TARGET_FIELDS[f.family]
        rows.append({
            "case_id": f.case_id,
            "family": f.family,
            "variant": f.variant,
            "pair_group": f.pair_group,
            "target_field": target,
            "expected": f.expected.get(target),
            "observed": observed.get(target),
            "match": observed.get(target) == f.expected.get(target),
            "full_expected": f.expected,
            "full_observed": observed,
        })
    return rows


def _metric_lanes(fixtures: tuple[Any, ...], method: str) -> dict[str, Any]:
    rows = _observations(fixtures, method)
    by_family = {}
    for family in sorted(APPLICABLE[method]):
        group = [r for r in rows if r["family"] == family]
        by_family[family] = {
            "target_field": TARGET_FIELDS[family],
            "cases": len(group),
            "matches": sum(r["match"] for r in group),
            "target_field_accuracy": _ratio(sum(r["match"] for r in group), len(group)),
        }

    metrics: dict[str, Any] = {"by_family_target_field": by_family}
    if "lineage_dependence" in APPLICABLE[method]:
        group = [f for f in fixtures if f.family == "lineage_dependence"]
        known = [f for f in group if f.expected["root_count"] is not None]
        predictions = {f.case_id: evaluate_method(f, method)["root_count"] for f in known}
        metrics["root_count_accuracy"] = _ratio(
            sum(predictions[f.case_id] == f.expected["root_count"] for f in known), len(known)
        )
        inflated = [
            f for f in known
            if isinstance(predictions[f.case_id], int)
            and predictions[f.case_id] > f.expected["root_count"]
        ]
        metrics["false_independence_inflations"] = {
            "count": len(inflated), "denominator": len(known), "rate": _ratio(len(inflated), len(known))
        }
        incomplete = [f for f in group if f.expected["root_count"] is None]
        missing_predictions = {
            f.case_id: evaluate_method(f, method).get("root_count") for f in incomplete
        }
        metrics["missing_ancestry_preservation"] = {
            "correct_unknown_count": sum(value is None for value in missing_predictions.values()),
            "denominator": len(incomplete),
            "rate": _ratio(sum(value is None for value in missing_predictions.values()), len(incomplete)),
        }
    if method in {"majority_vote", "ario_typed_policy_candidate"}:
        group = [f for f in fixtures if f.family == "claim_disposition"]
        expected = [f.expected["status"] for f in group]
        observed = [evaluate_method(f, method)["status"] for f in group]
        labels = ("SUPPORTED", "CONTRADICTED", "CONTESTED", "UNKNOWN", "REJECTED")
        metrics["claim_disposition"] = {
            "accuracy": _ratio(sum(a == b for a, b in zip(expected, observed)), len(group)),
            **_confusion(expected, observed, labels),
        }
        eligible_for_promotion = [
            (a, b) for a, b in zip(expected, observed)
            if a in {"UNKNOWN", "CONTESTED", "REJECTED"}
        ]
        promotions = sum(b in {"SUPPORTED", "CONTRADICTED"} for _, b in eligible_for_promotion)
        metrics["unsupported_claim_promotions"] = {
            "count": promotions,
            "denominator": len(eligible_for_promotion),
            "rate": _ratio(promotions, len(eligible_for_promotion)),
        }
    if "integrity_authenticity" in APPLICABLE[method]:
        group = [f for f in fixtures if f.family == "integrity_authenticity"]
        expected = [f.expected["integrity"] for f in group]
        observed = [evaluate_method(f, method)["integrity"] for f in group]
        labels = ("VALID", "INVALID", "UNKNOWN")
        metrics["integrity_state"] = {
            "accuracy": _ratio(sum(a == b for a, b in zip(expected, observed)), len(group)),
            **_confusion(expected, observed, labels),
        }
        if method == "ario_typed_policy_candidate":
            auth_expected = [f.expected["auth"] for f in group]
            auth_observed = [evaluate_method(f, method)["auth"] for f in group]
            auth_labels = ("VERIFIED", "UNVERIFIED", "FAILED", "NOT_APPLICABLE")
            metrics["authentication_state"] = {
                "accuracy": _ratio(sum(a == b for a, b in zip(auth_expected, auth_observed)), len(group)),
                **_confusion(auth_expected, auth_observed, auth_labels),
            }
        else:
            metrics["authentication_state"] = "NOT_COMPARABLE: hash baseline does not inspect authentication"
    if method == "ario_typed_policy_candidate":
        group = [f for f in fixtures if f.family == "scope"]
        violations = [f for f in group if f.expected["scope"] == "OUT_OF_SCOPE"]
        in_scope = [f for f in group if f.expected["scope"] == "IN_SCOPE"]
        predictions = {f.case_id: evaluate_method(f, method)["scope"] for f in group}
        tp = sum(predictions[f.case_id] == "OUT_OF_SCOPE" for f in violations)
        fp = sum(predictions[f.case_id] == "OUT_OF_SCOPE" for f in in_scope)
        metrics["scope_violation_detection"] = {
            "recall": _ratio(tp, len(violations)),
            "false_positive_rate": _ratio(fp, len(in_scope)),
            "violations": len(violations),
            "in_scope_controls": len(in_scope),
        }
        for family, key, metric_name in (
            ("schema_version", "schema", "schema_acceptance_accuracy"),
            ("revision_history", "history", "revision_history_accuracy"),
            ("composition_dependencies", "composition", "composition_state_accuracy"),
        ):
            subset = [f for f in fixtures if f.family == family]
            metrics[metric_name] = {
                "accuracy": _ratio(
                    sum(evaluate_method(f, method).get(key) == f.expected[key] for f in subset),
                    len(subset),
                ),
                "cases": len(subset),
            }
        composition = [f for f in fixtures if f.family == "composition_dependencies"]
        invalid = [f for f in composition if f.expected["composition"] == "INVALID"]
        valid_controls = [f for f in composition if f.expected["composition"] != "INVALID"]
        predicted = {f.case_id: evaluate_method(f, method)["composition"] for f in composition}
        metrics["composition_invalid_detection"] = {
            "recall": _ratio(
                sum(predicted[f.case_id] == "INVALID" for f in invalid), len(invalid)
            ),
            "false_positive_rate": _ratio(
                sum(predicted[f.case_id] == "INVALID" for f in valid_controls), len(valid_controls)
            ),
            "invalid_cases": len(invalid),
            "valid_or_incomplete_controls": len(valid_controls),
        }
        temporal = [f for f in fixtures if f.family == "temporal_provenance"]
        strict = [
            f for f in temporal
            if f.expected["temporal"] not in {"UNKNOWN", "UNCERTAIN", "PARTIAL", "SUPERSEDED"}
        ]
        metrics["temporal_ordering_accuracy"] = {
            "accuracy": _ratio(
                sum(evaluate_method(f, method)["temporal"] == f.expected["temporal"] for f in strict),
                len(strict),
            ),
            "cases": len(strict),
            "excluded_uncertain_or_partial": len(temporal) - len(strict),
        }
        status_rows = []
        for f in fixtures:
            if "status" in f.expected:
                predicted = evaluate_method(f, method).get("status")
                if predicted is not None:
                    status_rows.append((f.expected["status"], predicted))
        labels = ("UNKNOWN", "SUPPORTED", "CONTRADICTED", "CONTESTED", "REJECTED")
        status_confusion = _confusion(
            [a for a, _ in status_rows], [b for _, b in status_rows], labels
        )
        unknown_tp = status_confusion["confusion_matrix_actual_by_predicted"]["UNKNOWN"]["UNKNOWN"]
        unknown_fp = sum(
            status_confusion["confusion_matrix_actual_by_predicted"][actual]["UNKNOWN"]
            for actual in labels if actual != "UNKNOWN"
        )
        unknown_fn = sum(
            status_confusion["confusion_matrix_actual_by_predicted"]["UNKNOWN"][predicted]
            for predicted in labels if predicted != "UNKNOWN"
        )
        metrics["unknown_abstention"] = {
            "precision": _ratio(unknown_tp, unknown_tp + unknown_fp),
            "recall": _ratio(unknown_tp, unknown_tp + unknown_fn),
            "abstention_count": unknown_tp + unknown_fp,
            "status_decisions": len(status_rows),
        }
    return metrics


def build_report() -> dict[str, Any]:
    fixtures = corpus()
    methods = {}
    case_outputs = []
    for method in METHODS:
        rows = _observations(fixtures, method)
        methods[method] = {
            "policy_identity": (
                "BENCHMARK_SIDE_TYPED_CANDIDATE_NOT_ARIO_RUNTIME"
                if method == "ario_typed_policy_candidate"
                else "DELIBERATELY_SIMPLE_TASK_SCOPED_BASELINE"
            ),
            "applicable_families": sorted(APPLICABLE[method]),
            "applicable_cases": len(rows),
            "not_comparable_cases": len(fixtures) - len(rows),
            "metrics": _metric_lanes(fixtures, method),
            "cases": rows,
        }
        case_outputs.extend({"method": method, **row} for row in rows)
    return {
        "benchmark": "AEC-Bench-0.2-policy-comparison-preview",
        "corpus_kind": "SYNTHETIC_DETERMINISTIC_PUBLIC_DEVELOPMENT",
        "case_count": len(fixtures),
        "method_count": len(METHODS),
        "methods": methods,
        "cases": case_outputs,
        "non_claims": [
            "The Ario typed policy here is benchmark-side candidate code, not a call to the Ario runtime or current AEC adapter.",
            "Raw relay, majority vote and hash integrity are intentionally simple baselines, not full competing systems.",
            "Only applicable task lanes are scored; NOT_COMPARABLE is not counted as a failure.",
            "All fixtures and oracle labels are synthetic and author-authored.",
            "No aggregate/composite leaderboard score is produced.",
            "No real-world truth, source authenticity, privacy, security, model behavior or architectural superiority is established.",
            "PROV and LTMS adapters are separate, bounded integrations and are not treated as end-to-end policy comparators.",
        ],
    }


def main() -> None:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(build_report(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
