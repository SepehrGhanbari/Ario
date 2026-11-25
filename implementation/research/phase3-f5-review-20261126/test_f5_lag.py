import tempfile, unittest
from pathlib import Path
from capture_gateway import CaptureGateway, ReferenceModel, LocalWitnessQuorum

class LagTests(unittest.TestCase):
    def run_case(self,n):
        roster=tuple(f'w{i}@g{i}' for i in range(n)); q=2*((n-1)//3)+1
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with CaptureGateway(p/'g.sqlite',model=ReferenceModel(lambda _:b'y')) as g, LocalWitnessQuorum(p/'w',roster=roster) as w:
                g.receive('r',b'x'); self.assertEqual(w.commit_bundle(g.bundle(), records=g.journal.records())['status'],'QUORUM_FINALIZED')
                old=g.bundle_digest()
                w.set_available(roster[:q]); g.generate('r',b'x'); self.assertEqual(w.commit_bundle(g.bundle(), records=g.journal.records())['status'],'QUORUM_FINALIZED')
                new=g.bundle_digest()
                w.set_available(roster)
                self.assertEqual(w.read_status(new),'QUORUM_MATCH')
                self.assertEqual(w.read_status(old),'QUORUM_MISMATCH')
                w.set_available(roster[q:]); self.assertEqual(w.read_status(old),'UNAVAILABLE')
                w.set_available(roster)
                self.assertEqual(w.catch_up(),n-q)
                self.assertTrue(all(x.status()['sequence']==2 for x in w.witnesses.values()))
                g.receive('next',b'z'); self.assertEqual(w.commit_bundle(g.bundle(), records=g.journal.records())['status'],'QUORUM_FINALIZED')
                self.assertEqual(w.read_status(g.bundle_digest()),'QUORUM_MATCH')
    def test_four(self): self.run_case(4)
    def test_ten(self): self.run_case(10)
    def test_hundred(self): self.run_case(100)
    def test_unknown_and_reset(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with CaptureGateway(p/'g.sqlite',model=ReferenceModel(lambda _:b'y')) as g, LocalWitnessQuorum(p/'w') as w:
                g.receive('r',b'x'); w.commit_bundle(g.bundle(), records=g.journal.records()); head=g.bundle_digest()
                x=w.witnesses[w.roster[-1]]
                x.db.execute('UPDATE witness_state SET sequence=99 WHERE singleton=1')
                self.assertEqual(w.read_status(head),'QUORUM_MISMATCH')
                x.db.execute('UPDATE witness_state SET sequence=0,head_digest=?,cumulative_message_count=0,history_commitment=? WHERE singleton=1',('0'*64,'0'*64))
                self.assertEqual(w.read_status(head),'QUORUM_MISMATCH')
                self.assertEqual(w.catch_up(),0)
    def test_restart_holds(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with CaptureGateway(p/'g.sqlite',model=ReferenceModel(lambda _:b'y')) as g:
                g.receive('r',b'x')
                with LocalWitnessQuorum(p/'w') as w:
                    w.commit_bundle(g.bundle(), records=g.journal.records()); head=g.bundle_digest()
                with LocalWitnessQuorum(p/'w') as w:
                    self.assertEqual(w.read_status(head),'UNAVAILABLE')
                    self.assertEqual(w.commit_bundle(g.bundle(), records=g.journal.records())['status'],'UNAVAILABLE')
    def test_conflicting_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with CaptureGateway(p/'g.sqlite',model=ReferenceModel(lambda _:b'y')) as g, LocalWitnessQuorum(p/'w') as w:
                g.receive('r',b'x'); w.commit_bundle(g.bundle(), records=g.journal.records()); head=g.bundle_digest()
                w.witnesses[w.roster[-1]].db.execute('UPDATE witness_state SET head_digest=? WHERE singleton=1',('f'*64,))
                self.assertEqual(w.read_status(head),'QUORUM_MISMATCH')
                self.assertEqual(w.catch_up(),0)
    def test_duplicate_roster(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): LocalWitnessQuorum(d,roster=('x',)*4)
if __name__=='__main__': unittest.main()
