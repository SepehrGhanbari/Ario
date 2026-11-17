import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_SOURCE = pathlib.Path(__file__).with_name("make_export.py")


class ExportPathPolicyTests(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX fixture uses names Windows cannot create")
    def test_generator_rejects_windows_invalid_path_characters(self):
        invalid_names = ('bad?name', 'bad*name', 'bad|name', 'bad<name', 'bad>name', 'bad"name', 'bad\x01name')
        for invalid_name in invalid_names:
            with self.subTest(path=repr(invalid_name)), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                release = root / "release"
                source = release / "source"
                source.mkdir(parents=True)
                script = release / "make_export.py"
                shutil.copyfile(SCRIPT_SOURCE, script)

                subprocess.check_call(["git", "init", "-q", str(source)])
                subprocess.check_call(["git", "-C", str(source), "config", "user.email", "test@example.invalid"])
                subprocess.check_call(["git", "-C", str(source), "config", "user.name", "Export Path Test"])
                (source / invalid_name).write_bytes(b"x")
                subprocess.check_call(["git", "-C", str(source), "add", "--all"])
                subprocess.check_call(["git", "-C", str(source), "commit", "-qm", "invalid path fixture"])

                result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, repr(invalid_name))
                self.assertFalse((release / "artifacts" / "ario-full.txt").exists())

    def test_generator_rejects_oversized_source_blob_before_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = pathlib.Path(tmp) / "release"
            source = release / "source"
            source.mkdir(parents=True)
            script = release / "make_export.py"
            shutil.copyfile(SCRIPT_SOURCE, script)
            source_text = script.read_text(encoding="utf-8")
            source_text = source_text.replace(
                "MAX_RECORD_RAW_BYTES=64*1024*1024",
                "MAX_RECORD_RAW_BYTES=4",
            )
            script.write_text(source_text, encoding="utf-8")
            subprocess.check_call(["git", "init", "-q", str(source)])
            subprocess.check_call(["git", "-C", str(source), "config", "user.email", "test@example.invalid"])
            subprocess.check_call(["git", "-C", str(source), "config", "user.name", "Export Path Test"])
            (source / "too-large.bin").write_bytes(b"12345")
            subprocess.check_call(["git", "-C", str(source), "add", "--all"])
            subprocess.check_call(["git", "-C", str(source), "commit", "-qm", "oversized blob fixture"])
            result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tracked byte/resource limit", result.stderr)
            self.assertFalse((release / "artifacts" / "ario-full.txt").exists())

    @unittest.skipIf(os.name == "nt", "Unicode normalization fixture is POSIX-only in this harness")
    def test_generator_rejects_unicode_nfc_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = pathlib.Path(tmp) / "release"
            source = release / "source"
            source.mkdir(parents=True)
            shutil.copyfile(SCRIPT_SOURCE, release / "make_export.py")
            subprocess.check_call(["git", "init", "-q", str(source)])
            subprocess.check_call(["git", "-C", str(source), "config", "user.email", "test@example.invalid"])
            subprocess.check_call(["git", "-C", str(source), "config", "user.name", "Export Path Test"])
            (source / "é.txt").write_bytes(b"a")
            (source / "e\u0301.txt").write_bytes(b"b")
            subprocess.check_call(["git", "-C", str(source), "add", "--all"])
            subprocess.check_call(["git", "-C", str(source), "commit", "-qm", "unicode alias fixture"])
            result = subprocess.run([sys.executable, str(release / "make_export.py")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((release / "artifacts" / "ario-full.txt").exists())

if __name__ == "__main__":
    unittest.main()
