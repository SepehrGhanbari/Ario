"""Synthetic split-read payload substitution: same bytes must be checked and interpreted."""
from dataclasses import replace
from hashlib import sha256

from test_w2_lab_verifier import PAYLOAD, baseline, with_oracle
from w2_lab_verifier import inspect, mock_candidate_digest


def test_w2_n15_no_unverified_second_payload_read_may_hide_conflicting_report():
    request, oracle = baseline()
    a = request.sources[0]
    verified_b = PAYLOAD.replace(b'COMPLETED', b'FAILED')
    attack_b = PAYLOAD
    b = replace(a, label='MOCK-WITNESS-B', locator='blob-B',
                claimed_digest=sha256(verified_b).hexdigest(),
                root='ROOT-B', parents=('ORIGIN-B',), custodian='CUSTODIAN-B')
    binding_b = replace(oracle.authenticated_sources['blob-A'],
                        actual_digest=b.claimed_digest, root=b.root,
                        parents=b.parents, custodian=b.custodian)
    joint = replace(request, sources=(a, b))
    grant = replace(oracle.review_grants['GRANT-A'],
                    bound_candidate_digest=mock_candidate_digest(joint))

    class SwitchingStore(dict):
        def get(self, key, default=None):
            return super().get(key, default)   # verified bytes checked here
        def __getitem__(self, key):
            if key == 'blob-B':
                return attack_b                  # same locator, different raw bytes
            return super().__getitem__(key)

    normal = with_oracle(oracle,
        payload_store={'blob-A': PAYLOAD, 'blob-B': verified_b},
        authenticated_sources={'blob-A': oracle.authenticated_sources['blob-A'], 'blob-B': binding_b},
        externally_enrolled_roots=frozenset({'ROOT-A', 'ROOT-B'}),
        review_grants={'GRANT-A': grant})
    control = inspect(joint, normal)
    assert (control.status, control.reason) == ('UNKNOWN', 'CONFLICTING_REPORTED_STATUSES')

    switched = inspect(joint, replace(normal, payload_store=SwitchingStore(normal.payload_store)))
    # The security-relevant parsing must operate on the SAME retrieved bytes
    # whose SHA-256 was checked; no second unverified read may hide a conflict.
    assert (switched.status, switched.reason) == ('UNKNOWN', 'CONFLICTING_REPORTED_STATUSES')


def test_w2_n16_repeated_locator_is_read_only_once_per_audit():
    req, o = baseline()
    a = req.sources[0]
    b = replace(a, label='DIFFERENT-CALLER-LABEL')
    joint = replace(req, sources=(a, b))

    class CountingStore(dict):
        count = 0
        def get(self, key, default=None):
            self.count += 1
            return super().get(key, default)

    store = CountingStore(o.payload_store)
    outcome = inspect(joint, with_oracle(o, payload_store=store))
    assert outcome.status == 'UNKNOWN'
    assert outcome.reason == 'SHARED_ANCESTRY_NOT_INDEPENDENT'
    assert store.count == 1, 'reusing the same locator must not trigger a second read'


def test_w2_n17_malformed_provenance_parent_list_not_treated_as_a_verified_graph():
    req, o = baseline()
    source = replace(req.sources[0], parents='ORIGIN-A')
    joint = replace(req, sources=(source,))
    # Even a lab oracle declaration must not certify malformed ancestry types.
    binding = replace(o.authenticated_sources['blob-A'], parents='ORIGIN-A')
    grant = replace(o.review_grants['GRANT-A'],
                    bound_candidate_digest=mock_candidate_digest(joint))
    oracle = with_oracle(o, authenticated_sources={'blob-A': binding},
                         review_grants={'GRANT-A': grant})
    outcome = inspect(joint, oracle)
    assert outcome.status in {'UNKNOWN', 'REJECTED'}
    assert outcome.admission_decision == 'NOT_EVALUATED'


def test_w2_n18_malformed_mock_oracle_parent_list_cannot_grant_reviewability():
    req, o = baseline()
    binding = replace(o.authenticated_sources['blob-A'], parents=['ORIGIN-A'])
    outcome = inspect(req, with_oracle(o, authenticated_sources={'blob-A': binding}))
    assert outcome.status == 'UNKNOWN'
    assert outcome.reason == 'SOURCE_ANCESTRY_UNVERIFIABLE'
