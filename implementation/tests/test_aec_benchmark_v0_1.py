from research.aec_benchmark_v0_1 import METHODS, corpus, evaluate, score

def test_stable_unique_corpus():
    cases=corpus(); ids=[x.case_id for x in cases]
    assert len(ids)==len(set(ids))==12
    assert len({x.family for x in cases})>=8

def test_shared_root_not_counted_as_five_by_typed_policy():
    c=next(x for x in corpus() if x.case_id=="AEC01_SHARED_ROOT_5")
    assert evaluate(c,"raw_relay_count")["roots"]==5
    assert evaluate(c,"ario_typed_policy")["roots"]==1

def test_majority_does_not_erase_minority_conflict():
    c=next(x for x in corpus() if x.case_id=="AEC03_MINORITY_SUPPORTED")
    assert evaluate(c,"majority_vote")["claim_status"]=="UNSUPPORTED"
    assert evaluate(c,"ario_typed_policy")["claim_status"]=="UNKNOWN"

def test_missing_ancestry_stays_unknown():
    c=next(x for x in corpus() if x.case_id=="AEC04_MISSING_ANCESTRY")
    out=evaluate(c,"ario_typed_policy")
    assert out["roots"] is None and out["claim_status"]=="UNKNOWN"

def test_hash_is_not_authentication_or_truth():
    c=next(x for x in corpus() if x.case_id=="AEC08_HASH_WITHOUT_AUTH")
    out=evaluate(c,"hash_integrity_only")
    assert out["roots"] is None and out["claim_status"]=="UNKNOWN"

def test_schema_scope_and_digest_fail_closed():
    cases={x.case_id:x for x in corpus()}
    assert evaluate(cases["AEC06_SCHEMA_DOWNGRADE"],"ario_typed_policy")["claim_status"]=="REJECTED"
    assert evaluate(cases["AEC07_SCOPE_MISMATCH"],"ario_typed_policy")["scope_status"]=="OUT_OF_SCOPE"
    assert evaluate(cases["AEC09_INVALID_DIGEST"],"ario_typed_policy")["claim_status"]=="REJECTED"

def test_duplicate_sender_does_not_inflate_count():
    c=next(x for x in corpus() if x.case_id=="AEC10_REPLAYED_AGENT")
    assert evaluate(c,"raw_relay_count")["roots"]==2
    assert evaluate(c,"ario_typed_policy")["roots"]==1

def test_metrics_separate_and_complete():
    out=score()
    assert out["case_count"]==12 and set(out["methods"])==set(METHODS)
    for method in METHODS:
        assert 0<=out["methods"][method]["claim_disposition_accuracy"]<=1
        assert "unsupported_claim_promotions" in out["methods"][method]
