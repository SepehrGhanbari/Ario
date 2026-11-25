import tempfile
import unittest
from pathlib import Path
from capture_gateway import CaptureGateway, LocalWitnessQuorum, ReferenceModel, GatewayError, InjectedCrash
from message_journal import MessageJournal


class ReviewTests(unittest.TestCase):
    def test_export_rejects_corrupt_meta(self):
        with tempfile.TemporaryDirectory() as d, MessageJournal(Path(d)/'j') as j:
            j.append('incoming', b'x')
            j.connection.execute("UPDATE journal_meta SET value=? WHERE key='history_commitment'", ('f'*64,))
            with self.assertRaises(ValueError):
                j.export_commitment_metadata()

    def test_nonextending_and_missing_proof(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with CaptureGateway(p/'a',model=ReferenceModel(lambda _:b'y')) as a, CaptureGateway(p/'b',model=ReferenceModel(lambda _:b'y')) as b, LocalWitnessQuorum(p/'w') as w:
                a.receive('r',b'first')
                self.assertEqual(w.commit_bundle(a.bundle())['status'],'HOLD_MISSING_MESSAGE_PROOF')
                self.assertEqual(w.commit_bundle(a.bundle(),records=a.journal.records())['status'],'QUORUM_FINALIZED')
                b.receive('r',b'different'); b.receive('s',b'next')
                self.assertEqual(w.commit_bundle(b.bundle(),records=b.journal.records())['status'],'HOLD_INVALID_MESSAGE_PROOF')
                self.assertEqual(w.read_status(a.bundle_digest()),'QUORUM_MATCH')
                a.receive('s',b'next')
                self.assertEqual(w.commit_bundle(a.bundle(),records=a.journal.records())['status'],'QUORUM_FINALIZED')

    def test_wrong_witness_identity(self):
        with tempfile.TemporaryDirectory() as d, LocalWitnessQuorum(d) as w:
            with self.assertRaises(GatewayError):
                w.set_available((*w.roster, 'outsider'))
            w.witnesses[w.roster[-1]].db.execute('UPDATE witness_state SET witness_id=? WHERE singleton=1',('outsider',))
            self.assertEqual(w.read_status('0'*64),'QUORUM_MISMATCH')

    def test_recovery_transaction_failure(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'g'; model=ReferenceModel(lambda _:b'y')
            with CaptureGateway(p,model=model) as g:
                g.receive('r',b'x')
                with self.assertRaises(InjectedCrash):
                    g.generate('r',b'x',crash_at='after_generation_before_commit')
                original=g._add_event
                def fail(*args,**kwargs):
                    result=original(*args,**kwargs)
                    if args[0]=='INTERRUPTED':
                        raise RuntimeError('injected recovery fault')
                    return result
                g._add_event=fail
                with self.assertRaises(RuntimeError):
                    g.recover()
            with CaptureGateway(p,model=model) as g:
                with self.assertRaises(GatewayError):
                    g.generate('r',b'x')
                self.assertEqual(g.recover(),['interrupted:r'])
                self.assertEqual(len(model.calls),1)

if __name__=='__main__': unittest.main()
