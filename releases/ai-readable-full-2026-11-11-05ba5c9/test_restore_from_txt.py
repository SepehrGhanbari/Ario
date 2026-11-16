import base64,hashlib,json,pathlib,tempfile,unittest
from RESTORE_FROM_TXT_HARDENED import restore,SnapshotError
def sha(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def snap(rows,**bad):
 c="a"*40;t="b"*40;m="c"*64;size=sum(len(b) for _,b in rows)
 hc=bad.get("hc",len(rows));hb=bad.get("hb",size);fc=bad.get("fc",len(rows));fcom=bad.get("fcom",c);ft=bad.get("ft",t);fb=bad.get("fb",size);fm=bad.get("fm",m)
 o=bytearray(f"ARIO_FULL_TEXT_EXPORT_V1\nrepo=https://example.invalid\ncommit={c}\ntree={t}\ntracked_files={hc}\ntracked_bytes={hb}\nmanifest_sha256={m}\n@@ARIO_BEGIN\n".encode())
 for path,b in rows:
  enc="raw-utf8"
  try:b.decode("utf-8")
  except UnicodeDecodeError:enc="base64"
  payload=b if enc=="raw-utf8" else base64.encodebytes(b)
  e={"path":path,"mode":"100644","git_blob_sha1":sha(b),"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b),"encoding":enc,"payload_bytes":len(payload)}
  o+=b"@@ARIO_FILE "+json.dumps(e,separators=(",",":")).encode()+b"\n"+payload+b"\n@@ARIO_END\n"
 o+=f"@@ARIO_COMPLETE files={fc} commit={fcom} tree={ft} tracked_bytes={fb} manifest_sha256={fm}\n".encode()
 if "tail" in bad:o+=bad["tail"]
 return bytes(o)
class Tests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.d=pathlib.Path(self.tmp.name);self.src=self.d/"x.txt";self.dst=self.d/"out"
 def tearDown(self):self.tmp.cleanup()
 def bad(self,data):
  self.src.write_bytes(data)
  with self.assertRaises(SnapshotError):restore(self.src,self.dst)
  self.assertFalse(self.dst.exists())
 def test_valid_text_and_binary(self):
  self.src.write_bytes(snap([("a",b"hello"),("b/c",b"\0\xff")]))
  self.assertEqual(restore(self.src,self.dst),2);self.assertEqual((self.dst/"b/c").read_bytes(),b"\0\xff")
 def test_windows_drive(self):self.bad(snap([(r"C:\Users\A\x",b"x")]))
 def test_unc(self):self.bad(snap([(r"\\server\share\x",b"x")]))
 def test_parent(self):self.bad(snap([("../x",b"x")]))
 def test_backslash(self):self.bad(snap([(r"a\..\x",b"x")]))
 def test_reserved_name(self):self.bad(snap([("dir/CON.txt",b"x")]))
 def test_case_collision(self):self.bad(snap([("A",b"x"),("a",b"y")]))
 def test_footer_count(self):self.bad(snap([("a",b"x")],fc=2))
 def test_footer_commit(self):self.bad(snap([("a",b"x")],fcom="d"*40))
 def test_footer_tree(self):self.bad(snap([("a",b"x")],ft="d"*40))
 def test_footer_bytes(self):self.bad(snap([("a",b"x")],fb=2))
 def test_trailing(self):self.bad(snap([("a",b"x")],tail=b"bad"))
 def test_missing_footer(self):self.bad(snap([("a",b"x")]).replace(b"@@ARIO_COMPLETE",b"@@ARIO_MISSING"))
 def test_existing_destination(self):
  self.dst.mkdir();(self.dst/"keep").write_text("safe");self.src.write_bytes(snap([("a",b"x")]))
  with self.assertRaises(SnapshotError):restore(self.src,self.dst)
  self.assertEqual((self.dst/"keep").read_text(),"safe")
if __name__=="__main__":unittest.main()
