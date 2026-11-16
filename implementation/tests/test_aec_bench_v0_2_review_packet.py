from research.export_aec_bench_v0_2_review_packet import build_blinded_packet


def test_blinded_packet_contains_all_public_fixtures_without_oracle_fields():
    packet = build_blinded_packet()
    assert packet["case_count"] == 120
    assert packet["not_hidden"] is True
    assert packet["packet_kind"] == "PUBLIC_DEVELOPMENT_FIXTURES_BLINDED_TO_EXPECTED_LABELS"
    assert len(packet["cases"]) == 120
    for case in packet["cases"]:
        assert "expected" not in case
        assert "rationale" not in case
        assert {"case_id", "family", "variant", "input"}.issubset(case)


def test_blinded_packet_preserves_counterfactual_pair_identifiers():
    packet = build_blinded_packet()
    paired = [case for case in packet["cases"] if case["pair_group"]]
    assert len(paired) == 20
    assert len({case["pair_group"] for case in paired}) == 10
