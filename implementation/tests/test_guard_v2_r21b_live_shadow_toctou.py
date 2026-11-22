"""R21B live shadow TOCTOU negative control, no network, no real credentials.

A stable GraphQL pair sampled with a REST pin read *before* GraphQL cannot
exclude a PR head/base revision changing immediately AFTER those samples.
The bounded live diagnostic must do a final read-only REST recheck before
reporting TWO_COMPLETE_NONATTESTED. Not an atomic snapshot proof.
"""
import json

from research import guard_v2_r21b_live_shadow_probe as live

BASE = "b" * 40
HEAD = "a" * 40


class ChangingFinalRest:
    def __init__(self, token):
        self.number_reads = {}

    def get_json(self, url):
        if url == live.rest.API:
            return {"id": 1401709791}
        number = int(url.rsplit("/", 1)[-1])
        seen = self.number_reads.get(number, 0)
        self.number_reads[number] = seen + 1
        return {
            "id": 5402535550 + number,
            "number": number,
            "head": {"sha": HEAD if seen == 0 else "f" * 40},
            "base": {"sha": BASE},
        }


def synthetic_stable_shadow(pin, reader):
    return {
        "schema": "synthetic-only",
        "reason": "SHADOW_DUAL_CAPTURE_HOLD",
        "recorded_page_count": 6,
        "v1": {
            "sample_status": "SAMPLED_STABLE_UNATTESTED",
            "reason": "TWO_COMPLETE_GRAPH_SAMPLES_MATCH",
            "first_digest": "1" * 64, "second_digest": "1" * 64,
        },
        "v2": {
            "reason": "B_SAMPLES_EQUAL_NONATTESTED",
            "first_attribution_digest": "2" * 64,
            "second_attribution_digest": "2" * 64,
        },
    }


def test_post_sample_rest_revision_change_cannot_admit_complete_observation(
        monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", live.REPO)
    monkeypatch.setenv(
        "GITHUB_REF", "refs/heads/research/r21b-shadow-reader-v1-v2-20261122")
    monkeypatch.setenv("GITHUB_TOKEN", "SYNTHETIC_NEVER_SENT")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    monkeypatch.setattr(live.rest, "GitHubReadOnly", ChangingFinalRest)
    monkeypatch.setattr(live.shadow, "ReadOnlyGraphQLB", lambda token: object())
    monkeypatch.setattr(live.shadow, "compare_shadow", synthetic_stable_shadow)
    code = live.main()
    line = capsys.readouterr().out
    summary = json.loads(line.split("ARIO_R21B_LIVE_SHADOW ", 1)[1])
    assert code == 2, "STALE_HEAD_PRESENTED_AS_COMPLETE_AFTER_CHANGE"
    assert summary["research_observation"] == "INCOMPLETE_OR_CHANGED_HOLD"
    assert all(x.get("final_rest_scope_check") == "CHANGED_HOLD"
               for x in summary["results"])
