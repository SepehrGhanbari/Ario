"""W1 research-only: latent-graph challenge protocol scaffold v0.1 (PROPOSAL).

This is a *protocol scaffold*, not an independent benchmark and not a claim of
independent authorship. It exists to make the observation-equivalence trade-off
explicit and reproducible, and to replace the "16/16 development matches"
framing with per-variant reporting.

Protocol
--------
  G*  latent complete graph = the truth of what actually happened (here
      AUTHOR-DECLARED metadata, NOT externally adjudicated).
  O   a documented masking operator that emits an *observed* ProvenanceCase.
  For every G* the generator emits MATCHED variants that share the same latent
  truth but differ in what is disclosed:
      HONEST               observed graph discloses the true dependency graph;
      DECLARED_INCOMPLETE  observed graph also discloses it, but the completeness
                           flags are set False (honest abstention);
      UNDISCLOSED_OMISSION the true dependency is hidden (the observed graph is
                           the separate graph) while completeness flags stay True.

The oracle is the latent truth of G* by construction and is NEVER passed to any
rule under test. Rules see only the observed ProvenanceCase (no label leakage).

Limits (unchanged from the W1 review): truth here is author-declared; a real
protocol requires a separately authored generator and a frozen, independently
held oracle, neither of which is established here.
"""
from __future__ import annotations

import unittest

import w1_adversarial_input_sensitivity_v1 as w

HONEST = "HONEST"
DECLARED_INCOMPLETE = "DECLARED_INCOMPLETE"
UNDISCLOSED_OMISSION = "UNDISCLOSED_OMISSION"
VARIANTS = (HONEST, DECLARED_INCOMPLETE, UNDISCLOSED_OMISSION)

LATENT = (
    {"name": "G-sep", "shared_source": False, "shared_admin": False},
    {"name": "G-src", "shared_source": True, "shared_admin": False},
    {"name": "G-admin", "shared_source": False, "shared_admin": True},
    {"name": "G-both", "shared_source": True, "shared_admin": True},
)


def latent_dependent(spec):
    return bool(spec["shared_source"] or spec["shared_admin"])


def latent_relation(spec):
    if spec["shared_source"] and spec["shared_admin"]:
        return "SHARED_SOURCE_AND_ADMIN"
    if spec["shared_source"]:
        return "SHARED_SOURCE"
    if spec["shared_admin"]:
        return "SHARED_ADMIN"
    return "SEPARATE_MODELED"


def build_observed(engine, spec, variant):
    disclose = variant in (HONEST, DECLARED_INCOMPLETE)
    case = w.build_case(engine,
                        shared_source=(spec["shared_source"] and disclose),
                        shared_admin=(spec["shared_admin"] and disclose))
    complete = variant != DECLARED_INCOMPLETE
    return w.replace(case, complete_source_surface=complete, complete_control_surface=complete)


def development_expectation(spec, variant):
    """CO-DESIGNED development oracle (author policy), for self-consistency only."""
    if variant == DECLARED_INCOMPLETE:
        return "UNKNOWN"
    if variant == UNDISCLOSED_OMISSION:
        return "CONDITIONAL"          # the known non-detection, declared as "match"
    return "DEPENDENT" if latent_dependent(spec) else "CONDITIONAL"


def pinned_rule(engine):
    return lambda case: w.classify(engine, case)["classification"]


def never_promote_rule(engine):
    det = ("COMMON_CONTROL_DETECTED", "COMMON_SOURCE_DETECTED", "SAME_STORAGE_OBJECT")

    def rule(case):
        r = engine.evaluate_provenance(case)
        if (r.administrative_separation.status in det or
                r.source_independence.status in det or
                r.storage_separation.status == "SAME_STORAGE_OBJECT"):
            return "DEPENDENT"
        return "UNKNOWN"
    return rule


def score(engine, rule):
    rows = []
    for spec in LATENT:
        for variant in VARIANTS:
            case = build_observed(engine, spec, variant)
            v = rule(case)
            rows.append({
                "latent": spec["name"], "relation": latent_relation(spec), "variant": variant,
                "verdict": v, "dev_expected": development_expectation(spec, variant),
                "false_endorsement": v == "CONDITIONAL" and latent_dependent(spec),
                "missed_positive": (v != "CONDITIONAL" and not latent_dependent(spec)
                                    and variant != DECLARED_INCOMPLETE),
                "abstain": v == "UNKNOWN",
            })
    return rows


def summarize(rows):
    out = {}
    for variant in VARIANTS:
        sub = [r for r in rows if r["variant"] == variant]
        out[variant] = {
            "n": len(sub),
            "dev_matches": sum(r["verdict"] == r["dev_expected"] for r in sub),
            "false_endorsements": sum(r["false_endorsement"] for r in sub),
            "missed_positives": sum(r["missed_positive"] for r in sub),
            "abstain": sum(r["abstain"] for r in sub),
        }
    return out


class TestLatentGraphChallengeScaffold(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = w.load_pinned_engine()

    def test_no_latent_label_leaks_into_observed_input(self):
        for spec in LATENT:
            for variant in VARIANTS:
                blob = w.serialize_case(build_observed(self.e, spec, variant))
                for token in ("latent", "expected", "mechanism", "shared_source", "passes_dev"):
                    self.assertNotIn('"%s"' % token, blob)

    def test_omission_is_observation_identical_to_honest_separate(self):
        honest_sep = w.serialize_case(build_observed(self.e, LATENT[0], HONEST))
        for spec in LATENT[1:]:
            omitted = w.serialize_case(build_observed(self.e, spec, UNDISCLOSED_OMISSION))
            self.assertEqual(omitted, honest_sep)

    def test_variant_summary_is_matched_and_reports_false_endorsements(self):
        s = summarize(score(self.e, pinned_rule(self.e)))
        self.assertEqual(set(s), set(VARIANTS))
        self.assertGreater(s[UNDISCLOSED_OMISSION]["false_endorsements"], 0)
        self.assertEqual(s[HONEST]["false_endorsements"], 0)

    def test_never_promote_never_false_endorses(self):
        s = summarize(score(self.e, never_promote_rule(self.e)))
        total_false_endorsements = sum(v["false_endorsements"] for v in s.values())
        self.assertEqual(total_false_endorsements, 0)


if __name__ == "__main__":
    eng = w.load_pinned_engine()
    for label, rule in (("pinned", pinned_rule(eng)), ("never-promote", never_promote_rule(eng))):
        print("==", label, "==")
        for variant, s in summarize(score(eng, rule)).items():
            print("  %-20s n=%d dev=%d falseEnd=%d missPos=%d abstain=%d" %
                  (variant, s["n"], s["dev_matches"], s["false_endorsements"],
                   s["missed_positives"], s["abstain"]))
