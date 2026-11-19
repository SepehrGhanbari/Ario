import hashlib
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

    @unittest.skipIf(os.name == "nt", "POSIX symlink fixture")
    def test_zip_materializes_git_symlink_as_regular_file(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            release = pathlib.Path(tmp) / "release"
            source = release / "source"
            source.mkdir(parents=True)
            shutil.copyfile(SCRIPT_SOURCE, release / "make_export.py")
            shutil.copyfile(pathlib.Path(__file__).with_name("RESTORE_FROM_TXT_HARDENED.py"),
                            release / "RESTORE_FROM_TXT_HARDENED.py")
            shutil.copyfile(pathlib.Path(__file__).with_name("verify_pinned_manifest.py"),
                            release / "verify_pinned_manifest.py")
            subprocess.check_call(["git", "init", "-q", str(source)])
            subprocess.check_call(["git", "-C", str(source), "config", "core.symlinks", "true"])
            subprocess.check_call(["git", "-C", str(source), "config", "user.email", "test@example.invalid"])
            subprocess.check_call(["git", "-C", str(source), "config", "user.name", "Export Path Test"])
            (source / "target.txt").write_bytes(b"target")
            (source / "link").symlink_to("target.txt")
            subprocess.check_call(["git", "-C", str(source), "add", "--all"])
            subprocess.check_call(["git", "-C", str(source), "commit", "-qm", "symlink fixture"])

            result = subprocess.run([sys.executable, str(release / "make_export.py")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            archive = release / "artifacts" / "ario-full.zip"
            with zipfile.ZipFile(archive) as z:
                entry = z.getinfo("ARIO_SOURCE/link")
                mode = (entry.external_attr >> 16) & 0xFFFF
                self.assertEqual(mode & 0o170000, 0o100000)
                self.assertEqual(z.read("ARIO_SOURCE/link"), b"target.txt")
            self.assertFalse((release / "artifacts" / "restored-from-txt").exists())

    def test_generator_is_repeatable_without_stale_restore_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = pathlib.Path(tmp) / "release"
            source = release / "source"
            source.mkdir(parents=True)
            shutil.copyfile(SCRIPT_SOURCE, release / "make_export.py")
            shutil.copyfile(pathlib.Path(__file__).with_name("RESTORE_FROM_TXT_HARDENED.py"),
                            release / "RESTORE_FROM_TXT_HARDENED.py")
            shutil.copyfile(pathlib.Path(__file__).with_name("verify_pinned_manifest.py"),
                            release / "verify_pinned_manifest.py")
            subprocess.check_call(["git", "init", "-q", str(source)])
            subprocess.check_call(["git", "-C", str(source), "config", "user.email", "test@example.invalid"])
            subprocess.check_call(["git", "-C", str(source), "config", "user.name", "Repeatability Test"])
            (source / "hello.txt").write_bytes(b"hello")
            subprocess.check_call(["git", "-C", str(source), "add", "--all"])
            subprocess.check_call(["git", "-C", str(source), "commit", "-qm", "repeatable export fixture"])

            script = release / "make_export.py"
            first = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            archive = release / "artifacts" / "ario-full.zip"
            first_hash = hashlib.sha256(archive.read_bytes()).hexdigest()

            second = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), first_hash)
            self.assertFalse((release / "artifacts" / "restored-from-txt").exists())

    def test_failed_rebuild_preserves_previous_complete_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = pathlib.Path(tmp) / "release"
            source = release / "source"
            source.mkdir(parents=True)
            shutil.copyfile(SCRIPT_SOURCE, release / "make_export.py")
            shutil.copyfile(pathlib.Path(__file__).with_name("RESTORE_FROM_TXT_HARDENED.py"),
                            release / "RESTORE_FROM_TXT_HARDENED.py")
            shutil.copyfile(pathlib.Path(__file__).with_name("verify_pinned_manifest.py"),
                            release / "verify_pinned_manifest.py")
            subprocess.check_call(["git", "init", "-q", str(source)])
            subprocess.check_call(["git", "-C", str(source), "config", "user.email", "test@example.invalid"])
            subprocess.check_call(["git", "-C", str(source), "config", "user.name", "Atomic Export Test"])
            (source / "first.txt").write_bytes(b"first")
            subprocess.check_call(["git", "-C", str(source), "add", "--all"])
            subprocess.check_call(["git", "-C", str(source), "commit", "-qm", "valid export fixture"])

            script = release / "make_export.py"
            first = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            archive = release / "artifacts" / "ario-full.zip"
            txt = release / "artifacts" / "ario-full.txt"
            old_archive = archive.read_bytes()
            old_txt = txt.read_bytes()

            source_text = script.read_text(encoding="utf-8")
            source_text = source_text.replace("MAX_INPUT_BYTES=384*1024*1024", "MAX_INPUT_BYTES=1")
            script.write_text(source_text, encoding="utf-8")
            second = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("TXT input byte limit", second.stderr)
            self.assertEqual(archive.read_bytes(), old_archive)
            self.assertEqual(txt.read_bytes(), old_txt)
            self.assertEqual(list(release.glob(".artifacts-stage-*")), [])
            self.assertEqual(list(release.glob(".artifacts-backup-*")), [])

    @unittest.skipIf(os.name == "nt", "POSIX fixture for distinct Unicode normalization paths")
    def test_generator_rejects_file_parent_unicode_and_casefold_aliases(self):
        cases = (
            ("e" + chr(0x301), "é"),
            ("Parent", "parent"),
        )
        for file_name, child_dir in cases:
            with self.subTest(file_name=file_name, child_dir=child_dir), tempfile.TemporaryDirectory() as tmp:
                release = pathlib.Path(tmp) / "release"
                source = release / "source"
                source.mkdir(parents=True)
                script = release / "make_export.py"
                shutil.copyfile(SCRIPT_SOURCE, script)
                (source / file_name).write_bytes(b"parent-is-file")
                child = source / child_dir
                child.mkdir()
                (child / "child.txt").write_bytes(b"child")
                subprocess.check_call(["git", "init", "-q", str(source)])
                subprocess.check_call(["git", "-C", str(source), "config", "user.email", "test@example.invalid"])
                subprocess.check_call(["git", "-C", str(source), "config", "user.name", "Parent Alias Test"])
                subprocess.check_call(["git", "-C", str(source), "add", "--all"])
                subprocess.check_call(["git", "-C", str(source), "commit", "-qm", "file parent alias fixture"])
                result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("file/directory path conflict", result.stderr)
                self.assertFalse((release / "artifacts" / "ario-full.txt").exists())

    def test_generator_rejects_path_depth_and_index_budget(self):
        for patch_text, filename, expected in (
            ("MAX_PATH_DEPTH=128", "a/b.txt", "path depth limit"),
            ("MAX_PATH_INDEX_ENTRIES=100000", "a/b.txt", "path index resource limit"),
            ("MAX_PATH_INDEX_BYTES=8*1024*1024", "a.txt", "path index resource limit"),
        ):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as tmp:
                release = pathlib.Path(tmp) / "release"
                source = release / "source"
                (source / "a").mkdir(parents=True)
                script = release / "make_export.py"
                shutil.copyfile(SCRIPT_SOURCE, script)
                source_text = script.read_text(encoding="utf-8")
                replacement = patch_text.split("=")[0] + ("=1" if "ENTRIES" in patch_text else "=1")
                script.write_text(source_text.replace(patch_text, replacement), encoding="utf-8")
                subprocess.check_call(["git", "init", "-q", str(source)])
                subprocess.check_call(["git", "-C", str(source), "config", "user.email", "test@example.invalid"])
                subprocess.check_call(["git", "-C", str(source), "config", "user.name", "Export Path Test"])
                (source / filename).write_bytes(b"x")
                subprocess.check_call(["git", "-C", str(source), "add", "--all"])
                subprocess.check_call(["git", "-C", str(source), "commit", "-qm", "path-index fixture"])
                result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assertFalse((release / "artifacts" / "ario-full.txt").exists())

if __name__ == "__main__":
    unittest.main()
