#!/usr/bin/env python3
"""W9 hand-designed research controls: NO external holdout, no independent oracle."""
import copy
import json
import w9_bounded_receipt_contract as w

cases=[]
def check(name, assertion, expected, reason=None):
    actual=w.evaluate(*assertion)
    assert actual['declared_relation']==expected,(name,actual)
    if reason:
        assert actual['reason']==reason,(name,actual)
    assert actual['execution_authenticity']=='UNKNOWN' and actual['source_custody']=='NOT_ESTABLISHED'
    assert actual['assessment']=='NOT_ASSESSED' and actual['world_truth']=='UNKNOWN'
    assert actual['action_authority']=='NONE' and actual['memory_admitted'] is False
    cases.append({'id':name,'relation':actual['declared_relation'],'reason':actual['reason']})

def variant(**changes):
    r=w.receipt()
    r.update(changes)
    return r

check('P01_present_supported',(w.claim(),[w.receipt()]),'DECLARED_MATCH')
check('P02_absent_supported',(w.claim(False),[w.receipt(False)]),'DECLARED_MATCH')
check('N03_contradictory_stdout',(w.claim(),[w.receipt(False)]),'DECLARED_CONTRADICTION')
check('N04_cross_target',(w.claim(),[w.receipt(target='B')]),'UNKNOWN','SCOPE_TARGET_OR_TIME_MISMATCH')
check('N05_cross_principal',(w.claim(),[w.receipt(principal='OTHER')]),'UNKNOWN','SCOPE_TARGET_OR_TIME_MISMATCH')
check('N06_time_stale',(w.claim(),[w.receipt(at='2026-11-15T00:00:00Z')]),'UNKNOWN','SCOPE_TARGET_OR_TIME_MISMATCH')
check('N07_empty_stdout',(w.claim(),[w.receipt(stdout='')]),'UNKNOWN','EMPTY_OUTPUT')
check('N08_unparseable',(w.claim(),[w.receipt(stdout='{bad')]),'UNKNOWN','INVALID_OR_DUPLICATE_JSON')
check('N09_duplicate_json_keys',(w.claim(),[w.receipt(stdout='{"schema":"ario.lab.fs_presence.v0","target":"A","target":"B","principal":"LAB","at":"2026-11-16T00:00:00Z","present":true}')]),'UNKNOWN','INVALID_OR_DUPLICATE_JSON')
check('N10_wrong_present_type',(w.claim(),[w.receipt(stdout='{"schema":"ario.lab.fs_presence.v0","target":"A","principal":"LAB","at":"2026-11-16T00:00:00Z","present":"true"}')]),'UNKNOWN','BAD_PRESENT_TYPE')
check('N11_missing_schema',(w.claim(),[w.receipt(stdout='{}')]),'UNKNOWN','UNKNOWN_OBSERVATION_SCHEMA')
check('N12_nonzero_exit',(w.claim(),[w.receipt(exit_code=1)]),'UNKNOWN','REPORTED_TOOL_FAILURE')
check('N13_self_digest_tamper',(w.claim(),[variant(stdout_sha256='0'*64)]),'UNKNOWN','SELF_REPORTED_DIGEST_MISMATCH')
check('N14_bad_lock_digest',(w.claim(),[variant(lock_sha256='0'*64)]),'UNKNOWN','SELF_REPORTED_DIGEST_MISMATCH')
check('N15_multi_receipt_conflict',(w.claim(),[w.receipt(True,id='A1'),w.receipt(False,id='A2')]),'DECLARED_CONFLICT')
check('N16_duplicate_receipt_id',(w.claim(),[w.receipt(True,id='A1'),w.receipt(False,id='A1')]),'UNKNOWN','DUPLICATE_OR_INVALID_ID')
check('N17_same_receipt_twice',(w.claim(),[w.receipt(),w.receipt()]),'UNKNOWN','DUPLICATE_OR_INVALID_ID')
check('N18_unicode_exactness',(w.claim(target='caf\u00e9'),[w.receipt(target='cafe\u0301')]),'UNKNOWN','SCOPE_TARGET_OR_TIME_MISMATCH')
check('N19_unknown_predicate',({**w.claim(),'predicate':'GENERAL_TRUTH'},[w.receipt()]),'UNKNOWN','UNSUPPORTED_CLAIM')
check('N20_oversize',(w.claim(),[w.receipt(stdout='A'*4097)]),'UNKNOWN','RESOURCE_LIMIT')
check('N21_nonfinite_json',(w.claim(),[w.receipt(stdout='{"schema":"ario.lab.fs_presence.v0","target":"A","principal":"LAB","at":"2026-11-16T00:00:00Z","present":NaN}')]),'UNKNOWN','INVALID_OR_DUPLICATE_JSON')
check('N22_boolean_exit_code',(w.claim(),[variant(exit_code=True)]),'UNKNOWN','BAD_TOOL_OR_EXIT_TYPE')
check('N23_mismatched_tool',(w.claim(),[variant(tool='run_tests')]),'UNKNOWN','BAD_TOOL_OR_EXIT_TYPE')
check('N24_claim_missing_scope',(w.claim(principal=''),[w.receipt()]),'UNKNOWN','UNSUPPORTED_CLAIM')
check('P25_two_matching_declared_sources',(w.claim(),[w.receipt(id='A1'),w.receipt(id='A2')]),'DECLARED_MATCH')
check('N26_no_receipts',(w.claim(),[]),'UNKNOWN','RECEIPT_COUNT')

print(json.dumps({'status':'ALL_HAND_DESIGNED_EXPECTATIONS_MATCHED','case_count':len(cases),
'source_independence':'NOT_ESTABLISHED','all_memory_admissions':0,
'controls':cases},sort_keys=True,indent=2))
