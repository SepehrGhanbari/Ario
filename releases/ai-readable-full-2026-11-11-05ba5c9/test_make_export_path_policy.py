import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_SOURCE = pathlib.Path(__file__).with_name("make_export.py")


@unittest.skipIf(os.name == "nt", "POSIX fixture uses names Windows cannot create")
class ExportPathPolicyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
