"""Read-only source-pinned falsification probe for PR #210. Synthetic only."""
import importlib.util, pathlib, sys, json
p = pathlib.Path(__file__).parent / "source_monitoring_PR210_pinned.py"
spec = importlib.util.spec_from_file_location("ario_pr210_source_monitoring_pinned", p)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
guard = module.SourceMonitoringGuard(allowlisted_tools={"test_tool"})
claim = guard.create_hypothesis("An unrelated factual assertion about a blue box.")
good = guard.record_empirical_observation(
    assertion="Synthetic test tool exited normally.",
    tool="test_tool", target="synthetic", exit_code=0,
    stdout="OK", execution_lock="synthetic-lock")
result = guard.evaluate_claim_promotion(claim.attribution_id, [good.attribution_id])
assert result.veracity_state == module.VeracityState.VERIFIED_EMPIRICAL
assert "blue box" in result.assertion
control = module.SourceMonitoringGuard(allowlisted_tools={"test_tool"})
claim2 = control.create_hypothesis("An unrelated factual assertion about a red box.")
bad = control.record_empirical_observation(
    assertion="Synthetic tool did not complete", tool="test_tool",
    target="synthetic", exit_code=1,
    stdout="FAIL", execution_lock="synthetic-lock")
try:
    control.evaluate_claim_promotion(claim2.attribution_id, [bad.attribution_id])
    raise AssertionError("Expected unsupported control to be blocked")
except module.SelfCitationError:
    pass
print(json.dumps({
  "case": "SOURCE_PREDICATE_MISSING",
  "unrelated_claim_promoted": result.veracity_state.value,
  "unrelated_claim_text": result.assertion,
  "successful_tool_assertion": good.assertion,
  "failed_tool_control": "BLOCKED",
  "conclusion": "A verified exit code and local hashes are not semantic evidence for an arbitrary unrelated claim; this pinned draft does not enforce support entailment.",
  "production_state_changed": False,
}, sort_keys=True))
