#!/usr/bin/env python3
"""W20: independently implemented compact-proof verifier against a generator.

All data are synthetic. Passing tests never establish operator independence.
"""
import copy
import hashlib
import json
import random
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import w20_merkle_producer as prod
import w20_independent_monitor as mon


class W20Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = prod.make_fixture()
        self.pinned_key = self.fixture['public_key_hex']  # Test-only, not actual OOB verification.

    def test_root_external_independent_flat_fold_and_vectors(self):
        # Compute an independent root by grouping powers-of-two subtrees bottom-up.
        # This reference does NOT call the producer's root method.
        def alt_root(events):
            if not events:
                return hashlib.sha256(b'').digest()
            forest=[]
            for event in events:
                leaf=hashlib.sha256(b'\x00'+event).digest()
                count=1
                while forest and forest[-1][0]==count:
                    old_count,old_hash=forest.pop()
                    leaf=hashlib.sha256(b'\x01'+old_hash+leaf).digest()
                    count+=old_count
                forest.append((count,leaf))
            acc=forest.pop()[1]
            while forest:
                older=forest.pop()[1]
                acc=hashlib.sha256(b'\x01'+older+acc).digest()
            return acc
        rng=random.Random(20261117)
        data=[rng.randbytes(rng.randrange(0,70)) for _ in range(64)]
        for n in range(65):
            with self.subTest(n=n):
                self.assertEqual(prod.root(data[:n]),alt_root(data[:n]))
        self.assertEqual(prod.root([]).hex(),hashlib.sha256(b'').hexdigest())
        self.assertEqual(prod.root([b'']).hex(),hashlib.sha256(b'\x00').hexdigest())

    def test_compact_inclusion_all_prefixes(self):
        rng=random.Random(917)
        arr=[rng.randbytes(rng.randrange(0,65)) for _ in range(48)]
        count=0
        for size in range(1,49):
            expected=prod.root(arr[:size]).hex()
            for ix in range(size):
                path=[x.hex() for x in prod.inclusion_path(arr[:size],ix)]
                self.assertTrue(mon.verify_inclusion(arr[ix],ix,size,expected,path),(ix,size))
                # Each leaf record is in-order, not any alias entry or index.
                self.assertFalse(mon.verify_inclusion(arr[ix]+b'!',ix,size,expected,path))
                if path:
                    fake=path.copy();fake[0]='0'*64
                    self.assertFalse(mon.verify_inclusion(arr[ix],ix,size,expected,fake))
                count+=1
        self.assertEqual(count,1176)

    def test_compact_consistency_all_prefix_pairs(self):
        rng=random.Random(918)
        arr=[rng.randbytes(rng.randrange(0,70)) for _ in range(48)]
        count=0
        for new_size in range(2,49):
            for old_size in range(1,new_size):
                path=[v.hex() for v in prod.consistency_path(arr[:new_size],old_size)]
                old_root=prod.root(arr[:old_size]).hex()
                new_root=prod.root(arr[:new_size]).hex()
                self.assertTrue(mon.verify_consistency(old_size,new_size,old_root,new_root,path), (old_size,new_size))
                self.assertFalse(mon.verify_consistency(old_size,new_size,'f'*64,new_root,path))
                if path:
                    bad=path.copy();bad[-1]='0'*64
                    self.assertFalse(mon.verify_consistency(old_size,new_size,old_root,new_root,bad))
                count+=1
        self.assertEqual(count,1128)

    def test_fixture_and_monitor_policy_boundaries(self):
        f=self.fixture
        good=mon.evaluate_bundle(f,self.pinned_key,known_prior=f['old_checkpoint'])
        self.assertEqual(good['verdict'],'HISTORICAL_CONSISTENT')
        self.assertEqual(good['source_truth'],'UNKNOWN')
        self.assertEqual(good['operational_authority'],'NONE')
        self.assertEqual(good['external_effects'],0)
        self.assertEqual(good['real_ario_log_witnessed'],'NOT_ESTABLISHED')
        self.assertEqual(mon.evaluate_bundle(f,None,known_prior=f['old_checkpoint'])['reason'],'NO_OUT_OF_BAND_KEY_PIN')
        self.assertEqual(mon.evaluate_bundle(f,self.pinned_key)['reason'],'NO_RETAINED_PRIOR_CHECKPOINT')
        wrong_prior=copy.deepcopy(f['old_checkpoint'])
        wrong_prior['body']['root_sha256']='0'*64
        self.assertEqual(mon.evaluate_bundle(f,self.pinned_key,known_prior=wrong_prior)['reason'],
                         'DECLARED_OLD_HEAD_DIFFERS_FROM_TRUSTED')
        old,new=f['old_checkpoint'],f['new_checkpoint']
        self.assertEqual(mon.evaluate(old,new,self.pinned_key,None)['reason'],'MISSING_COMPACT_CONSISTENCY_PROOF')
        self.assertEqual(mon.evaluate(new,old,self.pinned_key,f['consistency_proof'])['reason'],'LOCAL_TREE_SIZE_ROLLBACK')
        self.assertEqual(mon.evaluate(old,old,self.pinned_key,[])['reason'],'SAME_SIGNED_HEAD_NOT_FRESHNESS')
        # A second non-approved key signed different head cannot alter pinned truth.
        attacker=Ed25519PrivateKey.generate()
        forged=copy.deepcopy(new)
        forged['body']['root_sha256']='a'*64
        signed=prod.canon({'domain':prod.DOMAIN,'body':forged['body']})
        forged['signature']=attacker.sign(signed).hex()
        self.assertEqual(mon.evaluate(old,forged,self.pinned_key,f['consistency_proof'])['reason'],
                         'CHECKPOINT_SIGNATURE_OR_SCHEMA_INVALID')
        forged_origin=copy.deepcopy(new)
        forged_origin['body']['origin']='other.test.invalid/competing-origin'
        self.assertEqual(mon.evaluate(old,forged_origin,self.pinned_key,f['consistency_proof'])['reason'],
                         'CHECKPOINT_SIGNATURE_OR_SCHEMA_INVALID')
        mismatch=copy.deepcopy(f)
        mismatch['events'][3]['payload_sha256']='0'*64
        self.assertEqual(mon.evaluate_bundle(mismatch,self.pinned_key,known_prior=f['old_checkpoint'])['reason'],'EVENT_INCLUSION_INVALID')
        # A previously unproved leaf used to pass the selective-proof version;
        # the verifier now requires proofs for ALL events and detects its tamper.
        mismatch=copy.deepcopy(f)
        mismatch['events'][1]['payload_sha256']='0'*64
        self.assertEqual(mon.evaluate_bundle(mismatch,self.pinned_key,known_prior=f['old_checkpoint'])['reason'],'EVENT_INCLUSION_INVALID')
        mismatch=copy.deepcopy(f)
        mismatch['inclusions']=mismatch['inclusions'][:-1]
        self.assertEqual(mon.evaluate_bundle(mismatch,self.pinned_key,known_prior=f['old_checkpoint'])['reason'],'INCOMPLETE_FULL_HISTORY_EVIDENCE')
        mismatch=copy.deepcopy(f)
        mismatch['inclusions'][1]['index']=0
        self.assertEqual(mon.evaluate_bundle(mismatch,self.pinned_key,known_prior=f['old_checkpoint'])['reason'],'DUPLICATE_OR_MISSING_INCLUSION')
        mismatch=copy.deepcopy(f)
        mismatch['events'][2]['payload']='private user memory text'
        self.assertEqual(mon.evaluate_bundle(mismatch,self.pinned_key,known_prior=f['old_checkpoint'])['reason'],'NOT_A_PUBLIC_SYNTHETIC_EVENT')
        mismatch=copy.deepcopy(f)
        mismatch['events'][2]['declared_origin']='USER_VERIFIED'
        self.assertEqual(mon.evaluate_bundle(mismatch,self.pinned_key,known_prior=f['old_checkpoint'])['reason'],'NOT_A_PUBLIC_SYNTHETIC_EVENT')
        mismatch=copy.deepcopy(f)
        mismatch['consistency_proof']=['0'*64]
        self.assertEqual(mon.evaluate_bundle(mismatch,self.pinned_key,known_prior=f['old_checkpoint'])['reason'],'COMPACT_CONSISTENCY_PROOF_INVALID')
        # A valid test signer can intentionally lie; consent and world truth stay UNKNOWN.
        self.assertEqual(mon.evaluate_bundle(f,self.pinned_key,known_prior=f['old_checkpoint'])['human_approval'],'NOT_ESTABLISHED')

    def test_same_issuer_signed_fork_and_signed_wrong_origin(self):
        signer=Ed25519PrivateKey.generate()
        key=signer.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
        def signed(size,root,origin=mon.ORIGIN):
            body={'schema':'ARIO_W20_SYNTHETIC_CHECKPOINT_V1','origin':origin,
                  'size':size,'root_sha256':root,'version':1}
            sig=signer.sign(prod.canon({'domain':prod.DOMAIN,'body':body})).hex()
            return {'body':body,'domain':prod.DOMAIN,'signature':sig}
        left=signed(3,prod.root([b'a',b'b',b'c']).hex())
        same=signed(3,prod.root([b'a',b'b',b'd']).hex())
        self.assertEqual(mon.evaluate(left,same,key,[])['reason'],'EQUIVOCATION_SAME_SIZE')
        larger=signed(4,prod.root([b'a',b'b',b'd',b'e']).hex())
        false_proof=[v.hex() for v in prod.consistency_path([b'a',b'b',b'd',b'e'],3)]
        self.assertEqual(mon.evaluate(left,larger,key,false_proof)['reason'],
                         'COMPACT_CONSISTENCY_PROOF_INVALID')
        wrong_origin=signed(3,left['body']['root_sha256'],'attacker.test.invalid/other')
        self.assertEqual(mon.evaluate(left,wrong_origin,key,[])['reason'],
                         'CHECKPOINT_SIGNATURE_OR_SCHEMA_INVALID')
        # A historical old+old view is internally consistent even after another
        # newer valid checkpoint exists. No external freshness is proven.
        self.assertEqual(mon.evaluate(left,left,key,[])['reason'],'SAME_SIGNED_HEAD_NOT_FRESHNESS')

    def test_negative_type_and_boundary_controls(self):
        data=b'public event'
        r=prod.root([data]).hex()
        candidates=[
            (data,True,1,r,[]), (data,0,True,r,[]), (data,0,0,r,[]),
            (data,0,65,r,[]), (data,0,1,'F'*64,[]),
            (data,0,1,r,['0'*64]), (data,0,1,r,0),
            (data,0,1,r,['0'*64]*20)
        ]
        for args in candidates:
            self.assertFalse(mon.verify_inclusion(*args))
        for args in [(True,2,r,r,[]), (1,True,r,r,[]), (0,2,r,r,[]),
                     (3,2,r,r,[]), (1,65,r,r,[]), (1,1,r,'0'*64,[]),
                     (1,2,r,r,[]), (1,2,r,r,['0'*64]*20)]:
            self.assertFalse(mon.verify_consistency(*args))
        self.assertTrue(mon.verify_consistency(1,1,r,r,[]))
        # No live A/B readback; advertised *simulated* high-water is not trusted.

if __name__ == '__main__':
    unittest.main(verbosity=2)
