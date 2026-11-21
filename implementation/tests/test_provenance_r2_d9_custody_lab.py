"""Only a same-author LAB test suite. No remote custodian or real enrollment."""
import dataclasses
import json
import pathlib
import sys
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import provenance_r2_d9_custody_lab as d9


def pub(k):
    return k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def sign(k, body, domain, rot=None):
    return d9.Signed(body, k.sign(domain + body), rot)


class Fixture:
    def __init__(self):
        self.custodian, self.floor_signer, self.rotation = [Ed25519PrivateKey.generate() for _ in range(3)]
        self.pins = d9.LabPins(pub(self.custodian), pub(self.floor_signer), pub(self.rotation), "a" * 32)
        self.events = []
        self.append("STATE", "1" * 64)
        self.append("STATE", "1" * 64)
        self.floor = self.make_floor(1)
        self.head = self.make_head()

    def append(self, kind, pin, *, revtip=None, epoch=None, rot_sign=True, prev_override=None, seq=None):
        last = json.loads(self.events[-1].body) if self.events else None
        o = {"schema": "ARIO-R2-D9-EVENT-V1", "sequence": seq if seq is not None else len(self.events)+1,
             "prev": prev_override if prev_override is not None else d9.event_digest(self.events[-1]) if self.events else d9.ZERO,
             "kind": kind, "state_sha256": "2" * 64,
             "revocation_tip": revtip if revtip is not None else (last["revocation_tip"] if last else d9.ZERO),
             "observer_pin": pin, "epoch": epoch if epoch is not None else (last["epoch"] if last else 1)}
        body = d9.canonical(o)
        rsig = self.rotation.sign(d9.ROTATION+body) if rot_sign and kind == "OBSERVER_ROTATE" else None
        self.events.append(sign(self.custodian, body, d9.EVENT, rsig))
        self.head = self.make_head()
        return self.events[-1]

    def make_head(self, *, index=None, nonce=None, event_hash=None, revtip=None):
        if index is None:
            index = len(self.events)
        o = json.loads(self.events[index-1].body)
        return sign(self.custodian, d9.canonical({"schema": "ARIO-R2-D9-HEAD-V1", "sequence": index,
            "event_hash": event_hash or d9.event_digest(self.events[index-1]),
            "revocation_tip": revtip or o["revocation_tip"], "observer_pin": o["observer_pin"],
            "epoch": o["epoch"], "nonce": nonce or self.pins.fresh_nonce}), d9.HEAD)

    def make_floor(self, index, *, event_hash=None):
        o=json.loads(self.events[index-1].body)
        return sign(self.floor_signer, d9.canonical({"schema": "ARIO-R2-D9-FLOOR-V1", "sequence": index,
            "event_hash": event_hash or d9.event_digest(self.events[index-1]),
            "revocation_tip": o["revocation_tip"], "observer_pin": o["observer_pin"], "epoch": o["epoch"]}), d9.FLOOR)

    def run(self, **kw):
        return d9.evaluate(tuple(self.events), self.head, self.floor, self.pins, **kw)


class D9Tests(unittest.TestCase):
    def setUp(self):
        self.x=Fixture()

    def assertRejected(self, result):
        self.assertEqual(result["status"],"UNKNOWN")
        self.assertEqual(result["lab_diagnostic"],"NONE")

    def test_lab_positive(self):
        self.assertEqual(self.x.run()["lab_diagnostic"],"LAB_CONSISTENT_ONLY")

    def test_positive_never_grants_trust(self):
        r=self.x.run()
        for name, value in {"status":"UNKNOWN", "evidence_admission":"NOT_EVALUATED",
                            "real_world_custody":"NOT_ESTABLISHED", "remote_freshness":"NOT_ESTABLISHED",
                            "actual_remote_read":"NOT_RUN", "original_github_execution":"NOT_ESTABLISHED"}.items():
            self.assertEqual(r[name],value)

    def test_same_admin_can_create_three_valid_keys(self):
        self.assertEqual(self.x.run()["lab_diagnostic"],"LAB_CONSISTENT_ONLY")
        self.assertEqual(self.x.run()["real_world_custody"],"NOT_ESTABLISHED")

    def test_nonce_mismatch(self):
        self.x.head=self.x.make_head(nonce="b"*32)
        self.assertRejected(self.x.run())

    def test_floor_rollback_below_seq(self):
        self.x.floor=self.x.make_floor(2)
        self.x.events=self.x.events[:1]
        self.x.head=self.x.make_head()
        self.assertEqual(self.x.run()["reason"],"ROLLBACK_BELOW_PROTECTED_FLOOR")

    def test_equal_seq_wrong_floor_hash(self):
        self.x.floor=self.x.make_floor(1,event_hash="f"*64)
        self.assertEqual(self.x.run()["history_diagnostic"],"FORK_VS_FLOOR")

    def test_floor_none(self):
        self.assertRejected(d9.evaluate(tuple(self.x.events),self.x.head,None,self.x.pins))

    def test_floor_signature_wrong(self):
        self.x.floor=dataclasses.replace(self.x.floor,signature=b"0"*64)
        self.assertRejected(self.x.run())

    def test_head_signature_wrong(self):
        self.x.head=dataclasses.replace(self.x.head,signature=b"0"*64)
        self.assertRejected(self.x.run())

    def test_event_signature_wrong(self):
        self.x.events[0]=dataclasses.replace(self.x.events[0],signature=b"0"*64)
        self.assertEqual(self.x.run()["reason"],"EVENT_SIGNATURE_INVALID")

    def test_noncanonical_payload(self):
        raw=json.dumps(json.loads(self.x.events[0].body),indent=2).encode()
        self.x.events[0]=sign(self.x.custodian,raw,d9.EVENT)
        self.assertRejected(self.x.run())

    def test_duplicate_keys(self):
        s=self.x.events[0].body.decode()
        raw=s.replace('"epoch":1', '"epoch":1,"epoch":1')
        self.x.events[0]=sign(self.x.custodian,raw.encode(),d9.EVENT)
        self.assertRejected(self.x.run())

    def test_boolean_sequence_invalid(self):
        o=json.loads(self.x.events[0].body);o["sequence"]=True
        self.x.events[0]=sign(self.x.custodian,d9.canonical(o),d9.EVENT)
        self.assertRejected(self.x.run())

    def test_unexpected_keys_in_event(self):
        o=json.loads(self.x.events[0].body);o["trust_root"]="claimant"
        self.x.events[0]=sign(self.x.custodian,d9.canonical(o),d9.EVENT)
        self.assertRejected(self.x.run())

    def test_wrong_chain_prev(self):
        o=json.loads(self.x.events[1].body);o["prev"]="f"*64
        self.x.events[1]=sign(self.x.custodian,d9.canonical(o),d9.EVENT)
        self.assertRejected(self.x.run())

    def test_sequence_gap(self):
        o=json.loads(self.x.events[1].body);o["sequence"]=3
        self.x.events[1]=sign(self.x.custodian,d9.canonical(o),d9.EVENT)
        self.assertRejected(self.x.run())

    def test_snapshot_head_mismatch(self):
        self.x.head=self.x.make_head(event_hash="f"*64)
        self.assertRejected(self.x.run())

    def test_head_revocation_mismatch(self):
        self.x.head=self.x.make_head(revtip="f"*64)
        self.assertRejected(self.x.run())

    def test_revoke_advances_tip(self):
        self.x.append("REVOKE","1"*64,revtip="a"*64)
        self.x.floor=self.x.make_floor(3)
        self.assertEqual(self.x.run()["lab_diagnostic"],"LAB_CONSISTENT_ONLY")

    def test_revocation_not_advancing(self):
        self.x.append("REVOKE","1"*64,revtip=d9.ZERO)
        self.assertRejected(self.x.run())

    def test_revocation_omitted_vs_floor(self):
        self.x.append("REVOKE","1"*64,revtip="a"*64)
        self.x.floor=self.x.make_floor(3)
        self.x.events=self.x.events[:2]
        self.x.head=self.x.make_head()
        self.assertRejected(self.x.run())

    def test_silent_revocation(self):
        self.x.append("STATE","1"*64,revtip="a"*64)
        self.assertRejected(self.x.run())

    def test_authorized_observer_rotate_only_in_lab(self):
        self.x.append("OBSERVER_ROTATE","f"*64,epoch=2)
        self.assertEqual(self.x.run()["lab_diagnostic"],"LAB_CONSISTENT_ONLY")
        self.assertEqual(self.x.run()["external_enrollment"],"NOT_ESTABLISHED")

    def test_unauthorized_observer_rotation(self):
        self.x.append("OBSERVER_ROTATE","f"*64,epoch=2,rot_sign=False)
        self.assertEqual(self.x.run()["reason"],"UNAUTHORIZED_OBSERVER_ROTATION")

    def test_rotation_does_not_advance_epoch(self):
        self.x.append("OBSERVER_ROTATE","f"*64,epoch=1)
        self.assertRejected(self.x.run())

    def test_silent_observer_key_change(self):
        self.x.append("STATE","f"*64)
        self.assertRejected(self.x.run())

    def test_root_rotation_not_authorized(self):
        self.x.append("ROOT_ROTATE","1"*64)
        self.assertRejected(self.x.run())

    def test_visible_same_seq_fork(self):
        o=json.loads(self.x.events[0].body);o["state_sha256"]="a"*64
        alternate=sign(self.x.custodian,d9.canonical(o),d9.EVENT)
        fork_head=self.x.make_head(index=1,event_hash=d9.event_digest(alternate))
        self.assertEqual(self.x.run(alternative_head=fork_head)["reason"],"VISIBLE_SIGNED_EQUIVOCATION")

    def test_newer_signed_view_detected(self):
        self.x.append("STATE","1"*64)
        newer=self.x.make_head()
        self.x.events=self.x.events[:2];self.x.head=self.x.make_head()
        self.assertEqual(self.x.run(alternative_head=newer)["reason"],"NEWER_SIGNED_VIEW_WAS_WITHHELD")

    def test_old_consistent_alt_allowed_as_lab(self):
        self.assertEqual(self.x.run(alternative_head=self.x.make_head(index=1))["lab_diagnostic"],"LAB_CONSISTENT_ONLY")

    def test_fake_alt_signature_rejected(self):
        alt=dataclasses.replace(self.x.make_head(index=1),signature=b"b"*64)
        self.assertRejected(self.x.run(alternative_head=alt))

    def test_signed_head_cannot_carry_extra_rotation_signature(self):
        self.x.head=dataclasses.replace(self.x.head, rotation_signature=b"x"*64)
        self.assertRejected(self.x.run())

    def test_signed_floor_cannot_carry_extra_rotation_signature(self):
        self.x.floor=dataclasses.replace(self.x.floor, rotation_signature=b"x"*64)
        self.assertRejected(self.x.run())

    def test_signed_alternate_cannot_carry_extra_rotation_signature(self):
        alt=dataclasses.replace(self.x.make_head(index=1),rotation_signature=b"x"*64)
        self.assertRejected(self.x.run(alternative_head=alt))

    def test_key_replacement_fails_against_preloaded_pin(self):
        attacker=Ed25519PrivateKey.generate()
        self.x.head=sign(attacker,self.x.head.body,d9.HEAD)
        self.assertRejected(self.x.run())

    def test_caller_replaces_own_pins_and_records_still_only_lab(self):
        # Demonstrates why the pin must be obtained outside the claimant.
        self.assertEqual(self.x.run()["lab_diagnostic"],"LAB_CONSISTENT_ONLY")
        self.assertEqual(self.x.run()["independently_retained_floor"],"NOT_ESTABLISHED")

    def test_invalid_pin_channel(self):
        self.x.pins=dataclasses.replace(self.x.pins,source_basis="OOB_AUTHENTICATED")
        self.assertRejected(self.x.run())

    def test_identical_keys_cannot_pretend_separate(self):
        self.x.pins=dataclasses.replace(self.x.pins,floor_key=self.x.pins.custodian_key)
        self.assertRejected(self.x.run())

    def test_nonce_too_short(self):
        self.x.pins=dataclasses.replace(self.x.pins,fresh_nonce="a")
        self.assertRejected(self.x.run())

    def test_oversized_event(self):
        self.x.events[0]=sign(self.x.custodian,self.x.events[0].body + b" "*2000,d9.EVENT)
        self.assertRejected(self.x.run())

    def test_unbounded_history(self):
        self.assertRejected(d9.evaluate(tuple(self.x.events)*80,self.x.head,self.x.floor,self.x.pins))

    def test_missing_history(self):
        self.assertRejected(d9.evaluate(tuple(),self.x.head,self.x.floor,self.x.pins))

    def test_hidden_fork_is_unobservable(self):
        # Two fixture-worlds with different hidden reality but *identical* inputs.
        worlds = ({"hidden_later_fork": False}, {"hidden_later_fork": True})
        observed_results = [self.x.run() for _world in worlds]
        self.assertEqual(observed_results[0], observed_results[1])
        self.assertEqual(observed_results[0]["undisclosed_fork_absence"],"NOT_ESTABLISHED")

    def test_hidden_revocation_is_unobservable(self):
        worlds=({"hidden_revocation": False},{"hidden_revocation": True})
        observed_results=[self.x.run() for _world in worlds]
        self.assertEqual(observed_results[0],observed_results[1])
        self.assertEqual(observed_results[0]["unobserved_revocation_absence"],"NOT_ESTABLISHED")

    def test_no_network_or_file_io_in_evaluator(self):
        import inspect
        src=inspect.getsource(d9.evaluate)
        for banned in ("requests.","urllib.","open(","socket.","os.system"):
            self.assertNotIn(banned,src)


if __name__ == "__main__":
    unittest.main()
