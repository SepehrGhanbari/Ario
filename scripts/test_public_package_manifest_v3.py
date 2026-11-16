import hashlib, json, pathlib, subprocess, sys, tempfile, unittest
SCRIPT = pathlib.Path(__file__).with_name("build_public_package_manifest_v3.py")
def run(*args):
    return subprocess.check_output([sys.executable, str(SCRIPT), *map(str,args)], text=True)
class ManifestV3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.repo=pathlib.Path(self.tmp.name)
        subprocess.check_call(["git","init","-q",str(self.repo)])
        subprocess.check_call(["git","-C",str(self.repo),"config","user.email","test@example.invalid"])
        subprocess.check_call(["git","-C",str(self.repo),"config","user.name","Manifest Test"])
        self.pkg=self.repo/"package"; (self.pkg/"docs").mkdir(parents=True)
        raw=b"line one\nline two\n"
        (self.pkg/"docs"/"sample.md").write_bytes(raw)
        crlf=raw.replace(b"\n",b"\r\n")
        v2={"format":"PUBLIC_PACKAGE_FILE_MANIFEST_V2","file_count_excluding_self":1,"files":{"docs/sample.md":{"bytes":len(crlf),"sha256":hashlib.sha256(crlf).hexdigest()}},"source":"test"}
        self.v2=self.pkg/"PUBLIC_PACKAGE_FILE_MANIFEST.json"; self.v2.write_text(json.dumps(v2),encoding="utf-8")
        subprocess.check_call(["git","-C",str(self.repo),"add","."])
        subprocess.check_call(["git","-C",str(self.repo),"commit","-qm","fixture"])
        self.out=self.pkg/"PUBLIC_PACKAGE_FILE_MANIFEST_V3.json"
    def tearDown(self): self.tmp.cleanup()
    def test_git_blob_basis_and_crlf_correction(self):
        run("--repo",self.repo,"--manifest-v2",self.v2,"--ref","HEAD","--output",self.out)
        result=json.loads(self.out.read_text(encoding="utf-8"))
        raw=(self.pkg/"docs"/"sample.md").read_bytes()
        self.assertEqual(result["files"]["docs/sample.md"]["bytes"],len(raw))
        self.assertEqual(result["files"]["docs/sample.md"]["sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(result["correction_log"]),1)
        self.assertEqual(result["correction_log"][0]["diagnosis"],"V2_HASH_MATCHED_LF_TO_CRLF_CONVERSION")
    def test_deterministic_output(self):
        run("--repo",self.repo,"--manifest-v2",self.v2,"--ref","HEAD","--output",self.out)
        first=self.out.read_bytes()
        run("--repo",self.repo,"--manifest-v2",self.v2,"--ref","HEAD","--output",self.out)
        self.assertEqual(first,self.out.read_bytes())
    def test_requires_explicit_ref(self):
        p=subprocess.run([sys.executable,str(SCRIPT),"--repo",str(self.repo),"--manifest-v2",str(self.v2),"--output",str(self.out)],capture_output=True)
        self.assertNotEqual(p.returncode,0)
if __name__=="__main__": unittest.main()
