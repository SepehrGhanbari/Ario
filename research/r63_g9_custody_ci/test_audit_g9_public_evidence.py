"""G9 public-signature verifier mutation regression (no signer, no keys)."""
import copy,json,sys,unittest,io,zipfile,warnings
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import audit_g9_public_evidence as a

class TestG9PublicEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=Path(sys.argv[1])
        if source.is_dir():outer={x.name:x.read_bytes() for x in source.iterdir() if x.is_file()}
        else:outer=a.members(source.read_bytes())
        cls.r=json.loads(next(raw for name,raw in outer.items() if name.startswith('r63-g9-native-report-')))
        cls.d=a.members(next(raw for name,raw in outer.items() if name.startswith('r63-g9-native-evidence-')))
    def bad(self,fn):
        r=copy.deepcopy(self.r);d=dict(self.d)
        fn(r,d)
        with self.assertRaises((ValueError,KeyError)):a.audit_data(r,d)
    def test_00_valid(self):
        self.assertEqual(a.audit_data(self.r,self.d)['status'],'PASS_PUBLIC_BYTES_AND_ECDSA')
    def test_01_alter_first_receipt(self):
        self.bad(lambda r,d:d.__setitem__('observer/first-receipt-public.txt',d['observer/first-receipt-public.txt'][:-4]+b'AAAA'))
    def test_02_alter_second_receipt(self):
        self.bad(lambda r,d:d.__setitem__('normal/receipt-public.txt',d['normal/receipt-public.txt'][:-4]+b'AAAA'))
    def test_03_missing_old_receipt(self):
        self.bad(lambda r,d:d.pop('observer/first-receipt-public.txt'))
    def test_04_missing_new_receipt(self):
        self.bad(lambda r,d:d.pop('normal/receipt-public.txt'))
    def test_05_payload_mutated(self):
        self.bad(lambda r,d:d.__setitem__('payload.bin',d['payload.bin']+b'forgery'))
    def test_06_duplicate_actor_key(self):
        self.bad(lambda r,d:d.__setitem__('founder.pub',d['ario.pub']))
    def test_07_forged_actor_approval(self):
        def flip(r,d):
            req=d['normal/request.txt'].split(b' ')
            req[5]=req[6]
            d['normal/request.txt']=b' '.join(req)
        self.bad(flip)
    def test_08_missing_spent_marker(self):
        self.bad(lambda r,d:d.pop(next(k for k in d if k.endswith('.used'))))
    def test_09_modified_spent_marker(self):
        def mod(r,d):
            k=next(k for k in d if k.endswith('.used'))
            d[k]+=b'forgery'
        self.bad(mod)
    def test_10_false_independence_claim(self):
        self.bad(lambda r,d:r.__setitem__('independent_admin','ESTABLISHED'))
    def test_11_claim_common_admin_is_protected(self):
        self.bad(lambda r,d:r['results']['SHARED_ADMIN_RED'].__setitem__('decision','PASS_PROTECTED'))
    def test_12_missing_native_entry(self):
        self.bad(lambda r,d:d.pop('normal/native-enter.txt'))
    def test_13_missing_custody_trace(self):
        self.bad(lambda r,d:r.__setitem__('custody_trace',''))
    def test_14_mislabeled_rollback(self):
        self.bad(lambda r,d:r['results']['OS_SEPARATE_FLOOR'].__setitem__('retry','SIGNED_RECEIPT'))
    def test_15_corrupt_native_public_pin(self):
        self.bad(lambda r,d:d.__setitem__('normal/public-pin.sha256',b'0'*64+b'\n'))
    def test_16_duplicate_zip_paths(self):
        b=io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(b,'w') as z:
                z.writestr('x','1');z.writestr('x','2')
        with self.assertRaises(ValueError):a.members(b.getvalue())
if __name__=='__main__':
    src=sys.argv[1] if len(sys.argv)==2 else None
    if src is None:raise SystemExit('usage: python test_audit_g9_public_evidence.py ARTIFACT_DIR')
    unittest.main(argv=[sys.argv[0]],verbosity=2)
