"""RED control R21B shadow: source mutation between independent deepcopies.

The original V1ProjectionRecorder snapshots a caller's page twice: once
inside _project_v1 and once to store raw replay pages. A producer that
mutates its returned object between these operations can make V1 read a
different content body than V2, falsely labelled SAME_PAGE.
This test must fail at the pinned #322 head and pass after single snapshot.
"""
import copy

from research import guard_v2_r21b_shadow_reader as shadow
from test_guard_v2_review_graph import FakeGraphQL
from test_guard_v2_r21b_attribution_synthetic import enriched


class FlipOnCopy(dict):
    def __deepcopy__(self, memo):
        before = copy.deepcopy(dict(self), memo)
        self["data"]["repository"]["pullRequest"]["reviews"]["nodes"][0][
            "body"] = "CHANGED_BETWEEN_PROJECTION_AND_RECORD"
        return before


class FlipReader(FakeGraphQL):
    def get_page(self, kind, number, cursor):
        page = super().get_page(kind, number, cursor)
        return FlipOnCopy(page) if kind == "reviews" else page


def test_projected_v1_and_recorded_v2_are_from_one_immutable_page_snapshot():
    recorder = shadow.V1ProjectionRecorder(FlipReader(enriched()))
    recorder.get_page("comments", 295, None)
    projection = recorder.get_page("reviews", 295, None)
    old_body = projection["data"]["repository"]["pullRequest"][
        "reviews"]["nodes"][0]["body"]
    recorded = recorder.pages[-1][3]
    replayed_body = recorded["data"]["repository"]["pullRequest"][
        "reviews"]["nodes"][0]["body"]
    # A single snapshot must be taken before any V1 projection happens.
    assert old_body == replayed_body, (
        "SAME_PAGE_CLAIM_VIOLATED: projected V1 and recorded raw V2 bytes diverged"
    )
