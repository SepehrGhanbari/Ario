import hashlib
from pathlib import Path
import pytest
from research.w36_pinned_sigsum_v0_1 import (
    verify_bytes, evaluate_floor, EXPECTED_SCOPE, may_use_from_receipt,
    PINNED_PROOF_SHA256, PINNED_CHECKPOINT_SHA256,
    PINNED_PUBKEY_SHA256, PINNED_POLICY_SHA256,
)
F=Path(__file__).resolve().parent/'fixtures'/'w37_w35_public'

def valid_receipt():
    blobs=[(F/s).read_bytes() for s in ['checkpoint.PUBLIC_SYNTHETIC.json', 'checkpoint.PUBLIC_SYNTHETIC.json.proof',
                                        'w35-lab-submitter.pub', 'sigsum-test1-2025.policy']]
    # Windows may have CRLF checkout; require pinned LF hashes after normalization.
    pins=[PINNED_CHECKPOINT_SHA256,PINNED_PROOF_SHA256,PINNED_PUBKEY_SHA256,PINNED_POLICY_SHA256]
    blobs=[b.replace(b'\r\n',b'\n') for b in blobs]
    assert [hashlib.sha256(b).hexdigest() for b in blobs] == pins
    receipt, data=verify_bytes(*blobs)
    assert receipt.receipt_status=='VERIFIED_SYNTHETIC_INCLUSION'
    assert not may_use_from_receipt(receipt)
    return receipt,data

@pytest.mark.parametrize('size',["280277",None,{},280277.0,True,False,-1,0,2**64,1.0,[],(280277,),complex(2,3),b'280277'])
def test_malformed_floor_sizes_fail_closed(size):
    e,d=valid_receipt()
    f={'independently_retained':True,'scope':EXPECTED_SCOPE,'size':size,'root':d['tree_root']}
    assert evaluate_floor(e,d,f)=='UNKNOWN_MALFORMED_FLOOR_SIZE'
    assert not may_use_from_receipt(e)

@pytest.mark.parametrize('shape',[[],42,'text',True])
def test_malformed_floor_shapes_fail_closed(shape):
    e,d=valid_receipt()
    assert evaluate_floor(e,d,shape)=='UNKNOWN_MALFORMED_FLOOR'

@pytest.mark.parametrize('flag',[1,'yes',True,False,None])
def test_retention_flag_not_truthy(flag):
    e,d=valid_receipt()
    f={'independently_retained':flag,'scope':EXPECTED_SCOPE,'size':d['tree_size'],'root':d['tree_root']}
    assert evaluate_floor(e,d,f)==('MOCK_FLOOR_MATCH' if flag is True else 'UNKNOWN_SELF_REPORTED_FLOOR')

@pytest.mark.parametrize('delta,expected',[(0,'MOCK_FLOOR_MATCH'),(1,'UNKNOWN_STALE_PROOF_RELATIVE_TO_FLOOR'),(-1,'UNKNOWN_NEWER_HEAD_REQUIRES_CONSISTENCY_PROOF')])
def test_legitimate_integer_floor_distinctions(delta,expected):
    e,d=valid_receipt()
    f={'independently_retained':True,'scope':EXPECTED_SCOPE,'size':d['tree_size']+delta,'root':d['tree_root']}
    assert evaluate_floor(e,d,f)==expected
    assert not may_use_from_receipt(e)


def test_missing_floor_and_bad_signed_status():
    e,d=valid_receipt()
    assert evaluate_floor(e,d,None)=='NOT_CHECKED_NO_EXTERNAL_FLOOR'
    assert evaluate_floor(type(e)('INVALID_OR_UNVERIFIED_RECEIPT','BAD'),d,{'independently_retained':True})=='UNKNOWN_INVALID_PROOF'

def test_same_size_wrong_root_no_match():
    e,d=valid_receipt()
    f={'independently_retained':True,'scope':EXPECTED_SCOPE,'size':d['tree_size'],'root':'x'*64}
    assert evaluate_floor(e,d,f)=='UNKNOWN_SAME_SIZE_ROOT_CONFLICT'
