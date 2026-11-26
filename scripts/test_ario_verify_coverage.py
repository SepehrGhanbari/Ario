import contextlib
import hashlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import ario_verify_coverage as v

class Coverage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.data=b'abc'; self.blob=v.object_id('blob',self.data)
        self.sub=v.object_id('tree',b'100644 file\0'+bytes.fromhex(self.blob))
        self.tree=v.object_id('tree',b'40000 dir\0'+bytes.fromhex(self.sub))
        self.rows={'sha':self.tree,'truncated':False,'tree':[{'path':'dir','mode':'040000','type':'tree','sha':self.sub},{'path':'dir/file','mode':'100644','type':'blob','sha':self.blob,'size':3}]}
        (self.root/'dir').mkdir(); (self.root/'dir/file').write_bytes(self.data)
        self.record=v.RECORDS[0]; self.md5=hashlib.md5(self.data).hexdigest(); self.metadata={'id':int(self.record),'doi':f'10.5281/zenodo.{self.record}','files':[{'key':'file.pdf','size':3,'checksum':'md5:'+self.md5}]}
        (self.root/self.record).mkdir(); (self.root/self.record/'file.pdf').write_bytes(self.data)
    def treecheck(self):
        c='a'*40
        with patch.object(v,'get_json',side_effect=[{'sha':c,'tree':{'sha':self.tree}},self.rows]):
            return v.check_checkout(self.root,c)
    def clear_extra(self):
        (self.root/self.record/'file.pdf').unlink(); (self.root/self.record).rmdir()
    def doi(self,body=None,catalog=False):
        if body is None: body=self.data
        @contextlib.contextmanager
        def reply(host,path,limit):
            self.assertEqual(host,'zenodo.org'); self.assertEqual(path,f'/api/records/{self.record}/files/file.pdf/content'); self.assertEqual(limit,3)
            yield io.BytesIO(body),len(body)
        with patch.object(v,'get_json',return_value=self.metadata),patch.object(v,'response',reply):
            return v.check_doi(self.root,self.record,catalog)
    def test_git_tree_exact(self):
        self.clear_extra(); self.assertEqual(self.treecheck()['status'],'TRACKED_FILE_BYTES_MATCH_GITHUB_TREE')
    def test_git_compare_against_actual_git_object(self):
        try: r=subprocess.run(['git','hash-object','--stdin'],input=self.data,capture_output=True,check=True)
        except FileNotFoundError: self.skipTest('git unavailable')
        self.assertEqual(r.stdout.decode().strip(),self.blob)
    def test_modified_same_size(self):
        self.clear_extra(); (self.root/'dir/file').write_bytes(b'xyz'); self.assertEqual(self.treecheck()['status'],'REJECTED')
    def test_missing(self):
        self.clear_extra(); (self.root/'dir/file').unlink(); self.assertEqual(self.treecheck()['status'],'REJECTED')
    def test_untracked(self):
        self.assertEqual(self.treecheck()['status'],'REJECTED')
    def test_git_metadata_not_read(self):
        self.clear_extra(); (self.root/'.git').mkdir(); (self.root/'.git/config').write_text('untrusted'); self.assertEqual(self.treecheck()['status'],'TRACKED_FILE_BYTES_MATCH_GITHUB_TREE')
    def test_truncation(self):
        self.rows['truncated']=True
        with self.assertRaises(v.Unknown): self.treecheck()
    def test_tree_wrong_hash(self):
        self.rows['tree'][1]['sha']='f'*40
        with self.assertRaises(v.Unknown): self.treecheck()
    def test_tree_omitted_entry(self):
        self.rows['tree'].pop()
        with self.assertRaises(v.Unknown): self.treecheck()
    def test_case_collision(self):
        self.rows['tree'].append(dict(self.rows['tree'][1],path='dir/FILE'))
        with self.assertRaises(v.Unknown): self.treecheck()
    def test_unsafe_paths(self):
        for s in ['../x','/x','a\\b','dir/CON.txt','dir/.git/x','dir/a.','a:x']:
            with self.subTest(s=s),self.assertRaises(v.Unknown): v.parts(s)
    def test_symlink(self):
        self.clear_extra(); f=self.root/'dir/file'; f.unlink(); (self.root/'other').write_bytes(self.data)
        try: f.symlink_to(self.root/'other')
        except OSError: self.skipTest('symlink unavailable')
        self.assertEqual(self.treecheck()['status'],'REJECTED')
    def test_doi_live_path_mock_match(self):
        self.assertEqual(self.doi()['status'],'ALL_RECORD_FILES_MATCH_ZENODO_HTTPS')
    def test_doi_modified_same_size(self):
        (self.root/self.record/'file.pdf').write_bytes(b'xyz'); self.assertEqual(self.doi()['status'],'REJECTED')
    def test_doi_wrong_remote(self):
        self.assertEqual(self.doi(b'xyz')['status'],'UNKNOWN')
    def test_doi_short_remote(self):
        self.assertEqual(self.doi(b'ab')['status'],'UNKNOWN')
    def test_doi_catalog_not_match(self):
        self.assertEqual(self.doi(catalog=True)['status'],'METADATA_ONLY')
    def test_doi_concept_rejected(self):
        self.metadata['doi']='10.5281/zenodo.0000'
        with self.assertRaises(v.Unknown): self.doi()
    def test_doi_filename_traversal(self):
        self.metadata['files'][0]['key']='../file.pdf'
        with self.assertRaises(v.Unknown): self.doi()
    def test_doi_duplicate_file(self):
        self.metadata['files'].append(dict(self.metadata['files'][0],key='FILE.PDF'))
        with self.assertRaises(v.Unknown): self.doi()
    def test_doi_missing_local_file(self):
        (self.root/self.record/'file.pdf').unlink(); self.assertEqual(self.doi()['status'],'REJECTED')
    def test_doi_unavailable(self):
        with patch.object(v,'get_json',side_effect=v.Unknown('offline')),self.assertRaises(v.Unknown): v.check_doi(self.root,self.record)
    def test_duplicate_json(self):
        with self.assertRaises(v.Unknown): v.unique_pairs([('x',1),('x',2)])
    def test_blocks_oversize(self):
        with self.assertRaises(v.Unknown): list(v.blocks(io.BytesIO(b'abc'),None,2))
    def test_blocks_truncated(self):
        with self.assertRaises(v.Unknown): list(v.blocks(io.BytesIO(b'ab'),3,3))

if __name__=='__main__': unittest.main(verbosity=2)
