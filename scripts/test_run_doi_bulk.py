import hashlib, io, tempfile, unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import run_doi_bulk as b
v=b.v
class TestBulk(unittest.TestCase):
    def execute(self, content=b'hello', second=b'hello', drift=False, unavailable=False):
        data=b'hello'; md5=hashlib.md5(data).hexdigest(); calls=[]; metadata=[]
        def get(host,path):
            if host=='api.github.com': raise v.Unknown('offline mapping')
            metadata.append(path)
            key='a.txt' if not drift or len(metadata)==1 else 'b.txt'
            return {'id':1,'doi':'10.5281/zenodo.1','files':[{'key':key,'size':len(data),'checksum':'md5:'+md5}]}
        @contextmanager
        def response(host,path,limit):
            calls.append(path)
            if unavailable: raise v.Unknown('offline')
            payload=content if len(calls)==1 else second
            yield io.BytesIO(payload),len(payload)
        with tempfile.TemporaryDirectory() as tmp, patch.object(v,'RECORDS',('1',)),patch.object(v,'get_json',get),patch.object(v,'response',response):
            result=b.run(tmp)
            return result,calls
    def test_two_reads(self):
        r,c=self.execute(); self.assertEqual(r['status'],'ALL_SELECTED_DOI_FILES_MATCH_ZENODO_HTTPS'); self.assertEqual(len(c),2); self.assertEqual(r['records'][0]['files'][0]['sha256'],hashlib.sha256(b'hello').hexdigest())
    def test_tampered_download(self):
        r,c=self.execute(content=b'HELLO'); self.assertEqual(r['status'],'UNKNOWN'); self.assertEqual(len(c),1)
    def test_second_response_mismatch(self):
        r,c=self.execute(second=b'HELLO'); self.assertEqual(r['status'],'UNKNOWN'); self.assertEqual(len(c),2)
    def test_metadata_drift(self):
        r,c=self.execute(drift=True); self.assertEqual(r['status'],'UNKNOWN')
    def test_unavailable(self):
        r,c=self.execute(unavailable=True); self.assertEqual(r['status'],'UNKNOWN')
if __name__=='__main__': unittest.main()
