#!/usr/bin/env python3
"""W8 / PR #210 source-monitoring research falsifiers; synthetic only.

Fetch exactly PR #210 implementation/core/source_monitoring.py at head
07068bdfa36abb29a3ce8e927077df3ffe02b0cf and save alongside this script
as source_monitoring_PR210_pinned.py. Runs in a disposable lab directory;
does not invoke actual Ario tools, touch memory ledgers, or authorize anything.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

PIN = "b3b500ebc8736aa5475d117f508a769a39b78d6d"
path = Path(__file__).with_name("source_monitoring_PR210_pinned.py")
raw = path.read_bytes()
actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()
if actual != PIN:
    raise SystemExit("HOLD: source Git blob mismatch: " + actual)
spec = importlib.util.spec_from_file_location("w8_source_monitoring_pinned", path)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

outcomes = []

def record(case_id, observed, assertion, kind):
    outcomes.append({"case_id": case_id, "observed": observed, "test_predicate": assertion,
                     "kind": kind})

def g():
    return m.SourceMonitoringGuard(allowlisted_tools={"inspect_directory", "run_tests", "check_file_hash"})

def evidence(guard, *, assertion="tool returned", target="target A", stdout="OK", code=0,
             hash_checks=True, id=None):
    kw = {}
    if hash_checks:
        kw["expected_execution_lock_sha256"] = hashlib.sha256(b"synthetic-lock").hexdigest()
        kw["expected_stdout_sha256"] = hashlib.sha256(stdout.encode()).hexdigest()
    return guard.record_empirical_observation(
        assertion=assertion, tool="inspect_directory", target=target,
        exit_code=code, stdout=stdout, execution_lock="synthetic-lock",
        attribution_id=id, **kw)

# B01 — unrelated success is already documented; retain as replication control.
x=g()
claim=x.create_hypothesis("Blue box belongs to user B")
obs=evidence(x,assertion="Directory A was enumerated",stdout="Directory A = empty")
yes=x.evaluate_claim_promotion(claim.attribution_id,[obs.attribution_id])
assert yes.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL
record("B01","PROMOTED", "Unrelated success promoted unrelated claim","known_reproduction")

# B02 — explicit conflicting factual stdout still permits claim promotion.
x=g()
claim=x.create_hypothesis("Target A exists on disk")
obs=evidence(x,assertion="Directory enumeration completed",stdout="NOT_FOUND: Target A")
yes=x.evaluate_claim_promotion(claim.attribution_id,[obs.attribution_id])
injected=x.filter_working_memory_candidates([yes.attribution_id],require_verified=True)
assert yes.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL and len(injected)==1
record("B02","PROMOTED_AND_FILTER_ADMITTED","Semantically contradictory stdout still reaches strict working-memory gate","new_falsifier")

# B03 — correct hashes for target A reused as support for target B.
x=g()
claim=x.create_hypothesis("Target B passed hash verification")
obs=evidence(x,assertion="Target A matched its expected hash",target="target A",stdout="Target A: MATCH")
yes=x.evaluate_claim_promotion(claim.attribution_id,[obs.attribution_id])
assert yes.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL
record("B03","PROMOTED","Different target scopes not compared","new_falsifier")

# B04 — zero-byte stdout and exit 0 are enough for empirical state/claim.
x=g()
claim=x.create_hypothesis("Unknown file was verified authentic")
obs=evidence(x,assertion="Tool process exited successfully",stdout="")
assert obs.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL
yes=x.evaluate_claim_promotion(claim.attribution_id,[obs.attribution_id])
assert yes.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL
record("B04","PROMOTED","No substantive observation bytes required","new_falsifier")

# B05 — caller supplies both output and success flag with no expected digests.
x=g()
claim=x.create_hypothesis("A signed external receipt exists")
obs=evidence(x,assertion="Receipt was found",stdout="invented response",hash_checks=False)
yes=x.evaluate_claim_promotion(claim.attribution_id,[obs.attribution_id])
assert yes.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL
record("B05","PROMOTED","No mandatory independent expected lock/stdout digest or actual tool runner","new_falsifier")

# B06 — missing lineage ancestor silently allowed through.
x=g()
claim=x.create_hypothesis("Claim with missing ancestor",parent_attribution_ids=["GHOST-SOURCE-ID"])
obs=evidence(x,assertion="Claim with missing ancestor",stdout="Claim with missing ancestor")
yes=x.evaluate_claim_promotion(claim.attribution_id,[obs.attribution_id])
assert yes.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL
assert "GHOST-SOURCE-ID" in yes.parent_attribution_ids
record("B06","PROMOTED_WITH_DANGLING_PARENT","Lineage completeness not validated","new_falsifier")

# B07 — external/veracity object deserializer accepts claimed VERIFIED with fake parent.
obj=m.SourceAttribution.from_dict({
    "attribution_id":"FORGED-UNREGISTERED", "source_type":"INTERNAL_HYPOTHESIS",
    "assertion":"A synthetic claim with an unresolved source",
    "veracity_state":"VERIFIED_EMPIRICAL", "parent_attribution_ids":["MISSING-EMPIRICAL-PARENT"]
})
assert obj.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL and obj.provenance is None
record("B07","DESERIALIZED_AS_VERIFIED","Raw SourceAttribution schema invariant accepts fake parent; does not establish registry insertion","new_schema_falsifier")

# B08 — explicit attribution_id may replace an existing node without warning.
x=g()
a=x.create_hypothesis("Original private unverified claim",attribution_id="REUSED-ID")
b=x.create_external_testimony("Different speaker's unrelated assertion",attribution_id="REUSED-ID")
assert a.assertion!=b.assertion
assert x.attributions["REUSED-ID"].assertion==b.assertion
record("B08","PRIOR_ATTRIBUTION_OVERWRITTEN","Registry ID immutability not enforced","new_falsifier")

# B09 — bool is an int in Python; True treated as successful zero? True != 0, so unsupported.
# This is the correct negative control; no false-positive assertion.
x=g()
obs=evidence(x,assertion="Boolean success sentinel",code=True,stdout="OK")
assert obs.veracity_state==m.VeracityState.UNSUPPORTED
record("B09","UNSUPPORTED","Bool True does not count as exit code 0, although its type is accepted","type_control")

# B10 — nonallowlisted tool correctly blocked.
x=g()
try:
    x.record_empirical_observation(assertion="bad",tool="unlisted",target="x",
        exit_code=0,stdout="OK",execution_lock="synthetic-lock")
except m.SourceMonitoringError:
    record("B10","BLOCKED","Nonallowlisted tool rejected","positive_control")
else:
    raise AssertionError("B10 nonallowlisted tool was accepted")

# B11 — false expected stdout hash correctly fails.
x=g()
try:
    x.record_empirical_observation(assertion="hash",tool="inspect_directory",target="x",
        exit_code=0,stdout="OK",execution_lock="synthetic-lock",
        expected_stdout_sha256=hashlib.sha256(b"different").hexdigest())
except m.AttributionMismatchError:
    record("B11","BLOCKED","Explicit mismatching expected digest rejected","positive_control")
else:
    raise AssertionError("B11 incorrect digest was accepted")

# B12 — nonzero exit correctly blocked for claim.
x=g()
h=x.create_hypothesis("Unrelated hypothesis")
o=evidence(x,assertion="Process failed",code=1,stdout="FAIL")
try:
    x.evaluate_claim_promotion(h.attribution_id,[o.attribution_id])
except m.SelfCitationError:
    record("B12","BLOCKED","Nonzero exit evidence cannot promote","positive_control")
else:
    raise AssertionError("B12 failed tool promoted")

# B13 — pure external testimony without tool correctly blocked.
x=g()
h=x.create_hypothesis("Unrelated hypothesis")
o=x.create_external_testimony("Another witness assertion")
try:
    x.evaluate_claim_promotion(h.attribution_id,[o.attribution_id])
except m.SelfCitationError:
    record("B13","BLOCKED","External testimony alone cannot promote","positive_control")
else:
    raise AssertionError("B13 testimony promoted")

# B14 — semantically related, success: does not block all positives.
x=g()
h=x.create_hypothesis("The synthetic check passed")
o=evidence(x,assertion="The synthetic check passed",stdout="The synthetic check passed")
p=x.evaluate_claim_promotion(h.attribution_id,[o.attribution_id])
assert p.veracity_state==m.VeracityState.VERIFIED_EMPIRICAL
record("B14","PROMOTED","Matching synthetic support is permitted; does NOT prove externally assessed truth","positive_control")

res={"schema":"ARIO-W8-SYNTHETIC-PR210-RESULTS-v1",
"source_pr_head":"07068bdfa36abb29a3ce8e927077df3ffe02b0cf",
"source_blob_sha1":PIN,"source_verified":True,
"case_count":len(outcomes),
"case_kinds":{key:sum(c["kind"]==key for c in outcomes) for key in sorted({x["kind"] for x in outcomes})},
"cases":outcomes,
"execution":"DIRECT_SOURCE_PINNED_CPYTHON_SYNTHETIC_ONLY",
"gold_author_independent":False,
"note":"An observed PROMOTED means this PR's current source-status contract emitted VERIFIED_EMPIRICAL for a supplied synthetic claim; it neither proves world truth nor production exploitability."}
assert len(outcomes)==14
print(json.dumps(res,indent=2,sort_keys=True))
