import base64,contextlib,hashlib,io,json,pathlib,tempfile,unittest
from unittest import mock
import RESTORE_FROM_TXT_HARDENED as hardened
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
  self.assertEqual(list(self.d.glob(".out.stage-*")),[])
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
 def test_payload_hash_tampering(self):
  data=snap([("a",b"x")]).replace(b'"sha256":"',b'"sha256":"f')
  self.bad(data)
 def test_noncanonical_dot_path(self):self.bad(snap([("./a",b"x")]))
 def test_repeated_separator(self):self.bad(snap([("a//b",b"x")]))
 def test_windows_console_device(self):self.bad(snap([("dir/CONIN$",b"x")]))
 def test_windows_superscript_device(self):self.bad(snap([("COM¹.txt",b"x")]))
 def test_windows_invalid_filename_characters(self):
  for name in ('a?b','a|b','a<b','a>b','a"b','a*b','a'+chr(1)+'b'):
   with self.subTest(path=repr(name)): self.bad(snap([(name,b"x")]))
 def test_success_does_not_claim_source_authenticity(self):
  self.src.write_bytes(snap([("safe.txt",b"x")]))
  captured=io.StringIO()
  with contextlib.redirect_stdout(captured): self.assertEqual(restore(self.src,self.dst),1)
  self.assertIn("RESTORE_STRUCTURAL_PASS_AUTHENTICITY_UNKNOWN",captured.getvalue())

 def test_oversized_preamble_line_rejected(self):
  data=snap([("a",b"x")]).replace(b"@@ARIO_BEGIN\n",b"X"*1048576+b"\n@@ARIO_BEGIN\n",1)
  self.bad(data)
 def test_oversized_record_json_field_rejected(self):
  data=snap([("a",b"x")]).replace(b'"path":"a"',b'"ignored":"'+b"X"*1048576+b'","path":"a"',1)
  self.bad(data)
 def test_terabyte_payload_declaration_rejected_before_read(self):
  data=snap([("a",b"x")]).replace(b'"payload_bytes":1',b'"payload_bytes":1099511627776',1)
  self.bad(data)
 def test_header_file_count_budget(self):
  self.bad(snap([("a",b"x")],hc=hardened.MAX_FILES+1))
 def test_header_total_bytes_budget(self):
  self.bad(snap([("a",b"x")],hb=hardened.MAX_TRACKED_BYTES+1))
 def test_record_payload_budget(self):
  data=snap([("a",b"x")]).replace(b'"payload_bytes":1',b'"payload_bytes":67108865',1)
  self.bad(data)
 def test_input_file_budget_without_huge_fixture(self):
  self.src.write_bytes(snap([("a",b"x")]))
  with mock.patch.object(hardened,"MAX_INPUT_BYTES",self.src.stat().st_size-1):
   with self.assertRaisesRegex(SnapshotError,"source type or size limit"): restore(self.src,self.dst)
  self.assertFalse(self.dst.exists())
 def test_record_count_budget_before_extra_record(self):
  data=snap([("a",b"x"),("b",b"y")],hc=1)
  self.src.write_bytes(data)
  with self.assertRaisesRegex(SnapshotError,"record count budget"): restore(self.src,self.dst)
  self.assertFalse(self.dst.exists())
 def test_header_line_budget_even_without_equals(self):
  data=snap([("a",b"x")]).replace(b"@@ARIO_BEGIN\n",b"X"*4097+b"\n@@ARIO_BEGIN\n",1)
  self.bad(data)
 def test_duplicate_record_path_rejected(self):
  data=snap([("valid.txt",b"x")]).replace(b'"path":"valid.txt"',b'"path":"../unsafe.txt","path":"valid.txt"',1)
  self.bad(data)
 def test_duplicate_record_hash_rejected(self):
  data=snap([("a",b"x")]).replace(b'"sha256":"',b'"sha256":"deadbeef","sha256":"',1)
  self.bad(data)
 def test_nested_duplicate_json_keys_rejected(self):
  data=snap([("a",b"x")]).replace(b'"path":"a"',b'"meta":{"flag":1,"flag":2},"path":"a"',1)
  self.bad(data)
 def test_nonfinite_json_constant_rejected(self):
  data=snap([("a",b"x")]).replace(b'"path":"a"',b'"meta":NaN,"path":"a"',1)
  self.bad(data)
 def test_dot_path_fails_before_write(self):
  self.bad(snap([(".",b"x")]))
 def test_invalid_surrogate_path(self):self.bad(snap([("\udcff",b"x")]))
 def test_header_count_mismatch(self):self.bad(snap([("a",b"x")],hc=2))
 def test_footer_manifest_mismatch(self):self.bad(snap([("a",b"x")],fm="d"*64))
 def test_partial_record_failure_cleans_stage(self):
  data=snap([("first",b"x"),("second",b"y")]).replace(hashlib.sha256(b"y").hexdigest().encode(),b"f"*64)
  self.bad(data)
 def test_trailing_dot_path(self):self.bad(snap([("file.",b"x")]))
 def test_unicode_nfc_collision_rejected(self):
  self.bad(snap([("é.txt",b"a"),("e\u0301.txt",b"b")]))
 def test_unicode_nfc_directory_component_collision_rejected(self):
  self.bad(snap([("dir/é/a",b"a"),("dir/e\u0301/b",b"b")]))
 def test_distinct_unicode_names_remain_representable(self):
  self.src.write_bytes(snap([("é.txt",b"a"),("ê.txt",b"b")]))
  self.assertEqual(restore(self.src,self.dst),2)
  self.assertEqual((self.dst/"ê.txt").read_bytes(),b"b")
 def test_case_colliding_directory_components(self):self.bad(snap([("Dir/a",b"x"),("dir/b",b"y")]))
 def test_file_directory_conflict_parent_first(self):self.bad(snap([("a",b"x"),("a/b",b"y")]))
 def test_file_directory_conflict_child_first(self):self.bad(snap([("a/b",b"y"),("a",b"x")]))
 def test_reserved_device_alias_with_space_before_extension(self):
  for name in ("CON .txt","COM1 .dat","AUX .log","dir/LPT2 .bin"):
   with self.subTest(path=name): self.bad(snap([(name,b"x")]))
 def test_path_component_byte_limit(self):
  self.bad(snap([("é"*128+".txt",b"x")]))
 def test_binary_payload_uses_separate_encoded_limit(self):
  raw=bytes([0])*10
  self.src.write_bytes(snap([("data.bin",raw)]))
  with mock.patch.object(hardened,"MAX_RECORD_RAW_BYTES",10), mock.patch.object(hardened,"MAX_RECORD_PAYLOAD_BYTES",20):
   self.assertEqual(restore(self.src,self.dst),1)
   self.assertEqual((self.dst/"data.bin").read_bytes(),raw)
if __name__=="__main__":unittest.main()
