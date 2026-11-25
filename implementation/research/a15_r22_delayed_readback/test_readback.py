import unittest
from readback import verify_retained_discovery,replace_once,ROOT,SIZE,FLOOR_ROOT,FLOOR_SIZE
class TestReadback(unittest.TestCase):
    def boot(self): return {'start':281650,'first_checksum':'1'*64}
    def base(self):
        return dict(retained_tree_size=SIZE,retained_tree_root=ROOT,retained_consistency='PASS',complete_retained_range=True,scan_end_exclusive=SIZE,sampled_tree_size=FLOOR_SIZE+100000,scan_start=281650,verified_leaf_count=3,global_latest_scope='NOT_ESTABLISHED',complete_sampled_suffix=False,floor_size=FLOOR_SIZE,floor_root=FLOOR_ROOT,floor_consistency='PASS',disposition='HOLD_OPAQUE_NEW_SIGNED_COMMITMENT',new_opaque_signed_commitments=2,matching_signed_leaves=[{'index':281650+i,'checksum':str(i+1)*64} for i in range(3)])
    def test_grown_log(self):
        r=self.base(); self.assertEqual(len(verify_retained_discovery(self.boot(),r)),3);self.assertFalse(r['complete_sampled_suffix'])
    def test_exact_head(self):
        r=self.base();r['sampled_tree_size']=FLOOR_SIZE;r['sampled_tree_root']=FLOOR_ROOT;self.assertEqual(len(verify_retained_discovery(self.boot(),r)),3)
    def test_same_size_conflict(self):
        r=self.base();r['sampled_tree_size']=FLOOR_SIZE;r['sampled_tree_root']='0'*64
        with self.assertRaisesRegex(ValueError,'HOLD_RETAINED_HEAD_CONFLICT'):verify_retained_discovery(self.boot(),r)
    def test_bad_report(self):
        for k,v in [('retained_tree_size',SIZE-1),('retained_tree_root','0'*64),('retained_consistency','FAIL'),('complete_retained_range',False),('scan_end_exclusive',SIZE-1),('sampled_tree_size',SIZE),('sampled_tree_size',True),('scan_start',281651),('verified_leaf_count',2),('global_latest_scope','ESTABLISHED'),('floor_size',SIZE),('floor_root','0'*64),('floor_consistency','FAIL')]:
            with self.subTest(k=k):
                r=self.base();r[k]=v
                with self.assertRaisesRegex(ValueError,'HOLD_RETAINED_RANGE_REPORT'):verify_retained_discovery(self.boot(),r)
    def test_missing_match(self):
        r=self.base();r['matching_signed_leaves'].pop()
        with self.assertRaisesRegex(ValueError,'HOLD_MATCH_COUNT'):verify_retained_discovery(self.boot(),r)
    def test_duplicate_match(self):
        r=self.base();r['matching_signed_leaves'][2]['checksum']='2'*64
        with self.assertRaisesRegex(ValueError,'HOLD_MATCH_ORDER'):verify_retained_discovery(self.boot(),r)
    def test_wrong_boot(self):
        with self.assertRaisesRegex(ValueError,'HOLD_MATCH_COUNT'):verify_retained_discovery({'start':281650,'first_checksum':'9'*64},self.base())
    def test_patch_anchor(self):
        self.assertEqual(replace_once('a b','b','c'),'a c')
        for text in ('a','b b'):
            with self.assertRaises(ValueError):replace_once(text,'b','c')
if __name__=='__main__':unittest.main()
