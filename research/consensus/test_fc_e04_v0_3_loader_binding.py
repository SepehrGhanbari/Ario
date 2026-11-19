#!/usr/bin/env python3
"""FC-E04 v0.3 bounded, byte-bound loader negatives; scratch only."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fc_e04_readonly_comparator_v0_3 as fc

ROOT = Path(__file__).resolve().parent


class LoaderBindingTests(unittest.TestCase):
    def _temp_module(self, source):
        directory = tempfile.TemporaryDirectory()
        folder = Path(directory.name)
        (folder / source.name).write_bytes(source.read_bytes())
        (folder / 'w9_bounded_receipt_contract.py').write_bytes((ROOT/'w9_bounded_receipt_contract.py').read_bytes())
        spec = importlib.util.spec_from_file_location('temporary_research_module', folder / source.name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return directory, module, folder/'w9_bounded_receipt_contract.py'

    def test_01_post_hash_loader_path_swap_has_no_effect(self):
        """Any loader call after verification would enable second-read substitution."""
        temporary, module, w9path = self._temp_module(ROOT / 'fc_e04_readonly_comparator_v0_3.py')
        with temporary:
            genuine = w9path.read_bytes()
            original = importlib.util.spec_from_file_location
            triggered = []

            def adversarial_loader(*args, **kwargs):
                triggered.append('post_verify_loader_open')
                w9path.write_bytes(genuine + b'\nFC_E04_CHANGED_AFTER_CHECK = True\n')
                return original(*args, **kwargs)

            with patch.object(importlib.util, 'spec_from_file_location', side_effect=adversarial_loader):
                out = module._load_w9()
            self.assertFalse(triggered, 'Expected no second path-based import after hash check')
            self.assertFalse(hasattr(out, 'FC_E04_CHANGED_AFTER_CHECK'))
            self.assertEqual(w9path.read_bytes(), genuine)
            self.assertEqual(out.evaluate(out.claim(), [out.receipt()])['declared_relation'], 'DECLARED_MATCH')

    def test_02_pinned_sha256_and_gitblob_both_match(self):
        raw = (ROOT/'w9_bounded_receipt_contract.py').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), fc.W9_SHA256)
        self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(), fc.W9_BLOB_SHA1)

    def test_03_modified_w9_source_refused_before_execution(self):
        temporary, module, path = self._temp_module(ROOT/'fc_e04_readonly_comparator_v0_3.py')
        with temporary:
            path.write_bytes(path.read_bytes() + b'\nFC_E04_UNTRUSTED_MARKER = True\n')
            with self.assertRaisesRegex(ValueError, 'W9_SOURCE_BLOB_MISMATCH'):
                module._load_w9()

    def test_04_oversized_w9_refused_before_execution(self):
        temporary, module, path = self._temp_module(ROOT/'fc_e04_readonly_comparator_v0_3.py')
        with temporary:
            path.write_bytes(b'#'*(fc.MAX_W9_SOURCE_BYTES + 1))
            with self.assertRaisesRegex(ValueError, 'W9_SOURCE_BYTE_LIMIT'):
                module._load_w9()

    def test_05_no_import_cache_file_write(self):
        temporary, module, path = self._temp_module(ROOT/'fc_e04_readonly_comparator_v0_3.py')
        with temporary:
            before = sorted(p.name for p in path.parent.iterdir())
            m = module._load_w9()
            self.assertTrue(hasattr(m, 'evaluate'))
            after = sorted(p.name for p in path.parent.iterdir())
            self.assertEqual(after, before)

    def test_06_immutable_input_across_split_stage(self):
        w9 = fc._load_w9()
        image = fc.make_image(w9.claim(), [w9.receipt()], [
            {'receipt_id':'R1','root_id':'SOURCE_1','parents':[]}
        ])
        before = image[:]
        rec = fc.recognize_image(image)
        out = fc.adjudicate_image(image, rec)
        self.assertEqual(image, before)
        self.assertEqual(out['final']['status'], 'DECLARED_ROOT_PARTITION_ONLY')
        self.assertEqual(out['source_custody'], 'NOT_ESTABLISHED')
        self.assertEqual(out['world_truth'], 'UNKNOWN')
        self.assertFalse(out['memory_admitted'])

if __name__ == '__main__':
    unittest.main()
