"""G8 independent public cryptography verifier negative controls (no signer use)."""
from __future__ import annotations
import io,json,sys,tempfile,unittest,warnings,zipfile
from pathlib import Path
import audit_g8_public_evidence as a

class TestG8PublicForensics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.target=getattr(cls,'target',None)
        if cls.target is None or not cls.target.exists():raise RuntimeError('Provide Actions G8 artifact ZIP or its extracted folder')
        if cls.target.is_dir():
            cls.entries={p.name:p.read_bytes() for p in cls.target.iterdir() if p.is_file()}
        else:
            with zipfile.ZipFile(cls.target) as z:cls.entries=a.verify_members(z)
        cls.inner_name=next(n for n in cls.entries if n.endswith('.zip') and n.startswith('r63-g8-native-evidence-'))
        cls.report_name=next(n for n in cls.entries if n.endswith('.json') and n.startswith('r63-g8-native-report-'))
        with zipfile.ZipFile(io.BytesIO(cls.entries[cls.inner_name])) as z:cls.inner=a.verify_members(z)
    def tamper(self,inner_edits=None,outer_edits=None,dupe=None):
        inner=dict(self.inner)
        if inner_edits:inner_edits(inner)
        with io.BytesIO() as buf:
            with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:
                for n,v in inner.items():z.writestr(n,v)
                if dupe:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore',UserWarning)
                        z.writestr(dupe,inner[dupe])
            nested=buf.getvalue()
        outer=dict(self.entries);outer[self.inner_name]=nested
        if outer_edits:outer_edits(outer)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        for n,v in outer.items():(Path(tmp.name)/n).write_bytes(v)
        return Path(tmp.name)
    def test_01_positive_full_artifact(self):
        self.assertEqual(a.audit(self.target)['result'],'PASS_CROSS_IMPLEMENTATION_BYTES_ONLY')
    def test_02_modified_public_native_signature_rejected(self):
        def change(inner):
            p='normal/receipt-public.txt';v=inner[p];
            self.assertIn(b'sig=',v)
            before,after=v.split(b'sig=',1)
            # SignHash raw P1363 signature starts after the ASCII 'sig=' marker.
            inner[p]=before+b'sig='+bytes([ord('A') if after[0]!=ord('A') else ord('B')])+after[1:]
        with self.assertRaises(ValueError):a.audit(self.tamper(change))
    def test_03_founder_claim_mutated_rejected(self):
        def change(inner):
            p='normal/request.txt';v=inner[p].split(b' ');v[5]=v[5][:-4]+b'AAAA';inner[p]=b' '.join(v)
        with self.assertRaises(ValueError):a.audit(self.tamper(change))
    def test_04_public_pin_swapped(self):
        with self.assertRaises(ValueError):a.audit(self.tamper(lambda x:x.__setitem__('receipt/public-pin.sha256',b'0'*64+b'\n')))
    def test_05_native_return_marker_changed(self):
        with self.assertRaises(ValueError):a.audit(self.tamper(lambda x:x.__setitem__('after/native-return.txt',b'NCryptSignHash RETURN 2\n')))
    def test_06_missing_intent_rejected(self):
        with self.assertRaises(ValueError):a.audit(self.tamper(lambda x:x.pop('after/use-intent.txt')))
    def test_07_same_admin_report_fabrication_rejected(self):
        def change(outer):
            report=json.loads(outer[self.report_name]);report['results']['after']['after']['native_enter']=False
            outer[self.report_name]=json.dumps(report).encode()
        with self.assertRaises(ValueError):a.audit(self.tamper(outer_edits=change))
    def test_08_forged_source_hash_rejected(self):
        def change(outer):
            report=json.loads(outer[self.report_name]);report['source_sha256']='f'*64
            outer[self.report_name]=json.dumps(report).encode()
        with self.assertRaises(ValueError):a.audit(self.tamper(outer_edits=change))
    def test_09_duplicate_archive_member_rejected(self):
        with self.assertRaises(ValueError):a.audit(self.tamper(dupe='normal/receipt-public.txt'))
    def test_10_changed_source_bound_seq4_payload_rejected(self):
        with self.assertRaises(ValueError):a.audit(self.tamper(lambda x:x.__setitem__('payload.bin',b'forged')))

if __name__=='__main__':
    argv=sys.argv[:];sys.argv=[sys.argv[0]]
    TestG8PublicForensics.target=Path(argv[1]).resolve() if len(argv)>1 else None
    unittest.main(verbosity=2)
