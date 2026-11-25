"""Local protocol checks, not network results. Uses exact R22 module at CI checkout."""
import unittest, copy
import transport as t
class Controls(unittest.TestCase):
    def setUp(self):
        self.boot={'start':10,'first_checksum':'1'*64}
        self.report={'disposition':'HOLD_OPAQUE_NEW_SIGNED_COMMITMENT','complete_sampled_suffix':True,'new_opaque_signed_commitments':2,'sampled_tree_size':20,'matching_signed_leaves':[{'index':10,'checksum':'1'*64},{'index':11,'checksum':'2'*64},{'index':15,'checksum':'3'*64}]}
    def test_order(self):self.assertEqual(len(t.verify_discovery(self.boot,self.report)),3)
    def test_incomplete(self):
        self.report['complete_sampled_suffix']=False
        with self.assertRaises(ValueError):t.verify_discovery(self.boot,self.report)
    def test_extra(self):
        self.report['matching_signed_leaves'].append({'index':16,'checksum':'4'*64})
        with self.assertRaises(ValueError):t.verify_discovery(self.boot,self.report)
    def test_duplicate(self):
        self.report['matching_signed_leaves'][2]['checksum']='2'*64
        with self.assertRaises(ValueError):t.verify_discovery(self.boot,self.report)
    def test_wrong_first(self):
        self.report['matching_signed_leaves'][0]['index']=9
        with self.assertRaises(ValueError):t.verify_discovery(self.boot,self.report)
    def test_reverse(self):
        self.report['matching_signed_leaves'][2]['index']=10
        with self.assertRaises(ValueError):t.verify_discovery(self.boot,self.report)
    def test_payload_relay_crypto(self):
        raw=b'PUBLIC SYNTHETIC TEST ONLY';target=t.sha(raw);event=t.make_event(raw,target)
        self.assertEqual(t.extract(event,target),raw)
        self.assertIsNone(t.extract(event,'0'*64))
        event['content']+='A'
        self.assertIsNone(t.extract(event,target))
    def test_payload_type(self):
        raw=b'{"domain":"wrong","kind":"RESERVE"}'
        with self.assertRaises(ValueError):t.payload(raw,1)
if __name__=='__main__':unittest.main()
