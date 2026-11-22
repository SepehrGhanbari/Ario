"""G7 CNG-checkpoint integration: no keys in unit tests, deliberately no authority."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import g7_preflight as g7

G6=g7.G6
class G7(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig1,cls.orig2,cls.new1,cls.new2,cls.pin_path,cls.src = g7.paths(G6)
        cls.a=cls.orig1.read_bytes()
        cls.b=cls.orig2.read_bytes()
        cls.c=cls.new1.read_bytes()
        cls.d=cls.new2.read_bytes()
        cls.pin=json.loads(cls.pin_path.read_text())
    def make(self,**kw):
        z=dict(base_v1=self.a,base_v2=self.b,candidate_v1=self.c,
               candidate_v2=self.d,pin=self.pin,source=self.src)
        z.update(kw)
        return g7.build(**z)
    def test_01_valid_exact_extension(self):
        pay,body=self.make()
        self.assertEqual(body['candidate']['seq'],4)
        self.assertEqual(body['candidate']['head'],g7.SEQ4_HEAD)
        self.assertTrue(pay.startswith(g7.DOMAIN))
    def test_02_candidate_does_not_advance_phone(self):
        _,body=self.make()
        self.assertIs(body['phone_floor_advanced'],False)
        self.assertEqual(body['external_latest'],'NOT_ESTABLISHED')
    def test_03_not_an_approval(self):
        _,body=self.make()
        self.assertEqual(body['signing_purpose'],g7.NO_AUTHORITY)
        self.assertEqual(body['native_v9_signer'],'NOT_EXECUTED')
    def test_04_frozen_source_pin(self):
        self.assertEqual(g7.sha(self.src.read_bytes()),g7.g6.FROZEN_V9_SHA)
    def test_05_invalid_seq2_phone_pin(self):
        with self.assertRaisesRegex(g7.Hold,'HOLD_PIN_REBOUND'):
            self.make(pin={**self.pin,'seq':2})
    def test_06_invalid_seq4_phone_pin(self):
        with self.assertRaisesRegex(g7.Hold,'HOLD_PIN_REBOUND'):
            self.make(pin={**self.pin,'seq':4})
    def test_07_invalid_head_phone_pin(self):
        with self.assertRaisesRegex(g7.Hold,'HOLD_PIN_REBOUND'):
            self.make(pin={**self.pin,'head':'f'*64})
    def test_08_noninteger_pin(self):
        with self.assertRaisesRegex(g7.Hold,'HOLD_PIN_REBOUND'):
            self.make(pin={**self.pin,'seq':3.0})
    def test_09_changed_base_v1(self):
        with self.assertRaisesRegex(g7.Hold,'HOLD_G4_PREFIX_CHANGED'):
            self.make(base_v1=self.a+b'[]\n')
    def test_10_changed_base_v2(self):
        with self.assertRaisesRegex(g7.Hold,'HOLD_G4_PREFIX_CHANGED'):
            self.make(base_v2=self.b+b'[]\n')
    def test_11_changed_candidate_v1(self):
        with self.assertRaises(g7.Hold):
            self.make(candidate_v1=self.c.replace(b'44444',b'55555'))
    def test_12_changed_candidate_v2(self):
        with self.assertRaises(g7.Hold):
            self.make(candidate_v2=self.d[:-2]+b'X\n')
    def test_13_rollback_to_seq3(self):
        with self.assertRaisesRegex(g7.Hold,'HOLD_ROLLBACK_OR_FORK'):
            self.make(candidate_v1=self.a,candidate_v2=self.b)
    def test_14_forked_seq4_valid_local_chain(self):
        mod=g7.g6.frozen_module(self.src)
        alt,status=mod.append(self.b,'e'*64,'5'*64)
        self.assertEqual(status,'NEW_NEEDS_DURABLE_APPEND')
        alt1=self.a+mod.canonical(['e'*64,'5'*64])+b'\n'
        with self.assertRaises(g7.Hold):
            self.make(candidate_v1=alt1,candidate_v2=alt)
    def test_15_distinct_payload_digest(self):
        pay,_=self.make()
        self.assertEqual(len(g7.sha(pay)),64)
        self.assertNotEqual(g7.sha(pay),g7.sha(self.d))
    def test_16_prepare_then_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            self.assertIn('NO_AUTHORITY',g7.run('prepare',G6,root))
            self.assertIn('PUBLIC_SIGNATURE_STILL_SEPARATE',g7.run('verify',G6,root))
    def test_17_existing_evidence_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run'
            g7.run('prepare',G6,root)
            with self.assertRaisesRegex(g7.Hold,'HOLD_REFUSE_EXISTING_OUTPUT'):
                g7.run('prepare',G6,root)
    def test_18_saved_payload_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';g7.run('prepare',G6,root)
            (root/'payload.bin').write_bytes(b'forgery')
            with self.assertRaisesRegex(g7.Hold,'HOLD_CHANGED_JOURNAL_AFTER_SIGN'):
                g7.run('verify',G6,root)
    def test_19_saved_metadata_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';g7.run('prepare',G6,root)
            (root/'candidate-metadata.json').write_text('{}')
            with self.assertRaisesRegex(g7.Hold,'HOLD_CHANGED_JOURNAL_AFTER_SIGN'):
                g7.run('verify',G6,root)
    def test_20_postsign_altered_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';g7.run('prepare',G6,root)
            bad=Path(tmp)/'altered_v2.jsonl';bad.write_bytes(self.d+b'\n')
            with self.assertRaises(g7.Hold):
                g7.run('verify',G6,root,candidate_v2_override=bad)
    def test_21_deleted_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';g7.run('prepare',G6,root)
            (root/'payload.bin').unlink()
            with self.assertRaisesRegex(g7.Hold,'HOLD_SIGNED_PAYLOAD_UNAVAILABLE'):
                g7.run('verify',G6,root)
    def test_22_missing_phone_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake=Path(tmp)
            (fake/'g4_source_v1.jsonl').write_bytes(self.a)
            with self.assertRaises(g7.Hold):
                g7.run('prepare',fake,Path(tmp)/'new')
if __name__=='__main__':
    unittest.main(verbosity=2)
