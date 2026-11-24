import unittest
from unittest.mock import patch
import recovery as r

class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.a = dict(profile=r.PROFILE, scope="a"*48, record_count=2,
                      previous_checksum="GENESIS", floor_commitment_sha256="b"*64,
                      synthetic_nonce="c"*64, synthetic=True, authoritative=False,
                      historical_event_truth="UNKNOWN", trust_activation="NO_GO", production="NO_GO")
        self.first = r.canonical(self.a)
        self.pin = r.checksum(self.first)
        self.b = dict(self.a, record_count=4, previous_checksum=self.pin,
                      floor_commitment_sha256="d"*64, synthetic_nonce="e"*64)
        self.second = r.canonical(self.b)
        self.target = r.checksum(self.second)

    def verify(self, raw, target=None, pin=None):
        return r.validate(self.first, raw, self.target if target is None else target,
                          self.pin if pin is None else pin)

    def altered(self, **kw):
        raw = r.canonical(dict(self.b, **kw))
        return self.verify(raw, r.checksum(raw))

    def test_valid(self):
        self.assertEqual(self.verify(self.second), "RECOVERED_LINKED_SYNTHETIC_ENVELOPE_ONLY")
    def test_missing(self):
        self.assertEqual(self.verify(None), "HOLD_CONTENT_UNAVAILABLE")
    def test_tamper(self):
        self.assertEqual(self.verify(self.second+b" "), "HOLD_CONTENT_HASH_MISMATCH")
    def test_replay(self):
        self.assertEqual(self.verify(self.first), "HOLD_CONTENT_HASH_MISMATCH")
    def test_bootstrap(self):
        self.assertEqual(self.verify(self.second,pin="0"*64), "HOLD_BOOTSTRAP_MISMATCH")
    def test_wrong_scope_even_with_matching_hash(self):
        self.assertEqual(self.altered(scope="f"*48), "HOLD_WRONG_SCOPE")
    def test_wrong_previous_even_with_matching_hash(self):
        self.assertEqual(self.altered(previous_checksum="f"*64), "HOLD_PREDECESSOR")
    def test_old_count_even_with_matching_hash(self):
        self.assertEqual(self.altered(record_count=2), "HOLD_NON_ADVANCING_COUNT")
    def test_same_floor(self):
        self.assertEqual(self.altered(floor_commitment_sha256="b"*64), "HOLD_UNCHANGED_FLOOR_COMMITMENT")
    def test_authority(self):
        self.assertEqual(self.altered(authoritative=True), "HOLD_CONTENT_SCHEMA")
    def test_bool_count(self):
        self.assertEqual(self.altered(record_count=True), "HOLD_CONTENT_SCHEMA")
    def test_duplicate_field(self):
        raw = self.second.replace(b'"record_count":4', b'"record_count":4,"record_count":4')
        self.assertEqual(self.verify(raw,r.checksum(raw)), "HOLD_CONTENT_SCHEMA")
    def test_noncanonical(self):
        raw = self.second+b" "
        self.assertEqual(self.verify(raw,r.checksum(raw)), "HOLD_CONTENT_SCHEMA")
    def test_invalid_discovery(self):
        self.assertEqual(self.verify(self.second,"bad"), "HOLD_INVALID_DISCOVERY")
    def test_valid_relay_event_and_replay_rejection(self):
        event = r.event_for(self.second)
        self.assertEqual(r.extract(event,self.target),self.second)
        self.assertIsNone(r.extract(event,self.pin))
        self.assertIsNone(r.extract(dict(event,content=event["content"]+"x"),self.target))
    def test_discovery_report(self):
        boot = {"start":10,"first_checksum":self.pin}
        report = {"disposition":"HOLD_OPAQUE_NEW_SIGNED_COMMITMENT","complete_sampled_suffix":True,
                  "new_opaque_signed_commitments":1,"sampled_tree_size":12,
                  "matching_signed_leaves":[{"index":10,"checksum":self.pin},{"index":11,"checksum":self.target}]}
        self.assertEqual(r.discover_target(report,boot),self.target)
        for change in ({"complete_sampled_suffix":False},{"new_opaque_signed_commitments":2},
                       {"matching_signed_leaves":[{"index":10,"checksum":self.pin}]}):
            with self.assertRaises(ValueError):
                r.discover_target(dict(report,**change),boot)

if __name__ == "__main__":
    unittest.main()
