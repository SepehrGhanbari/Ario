"""R63 read quorum experiment. Never authorizes a signature or a latest claim."""
from itertools import combinations
from pathlib import Path
from verify_witness import KEYS, note
from verify_direct import consistency
from cryptography.exceptions import InvalidSignature

REQUIRED = frozenset(('geomys', 'markovian'))
REVIEW = 'MATCH_READ_QUORUM_REVIEW_ONLY'
HOLD = 'HOLD_'


def decide(candidate, replies, proofs, now, max_age=3600, future_skew=60):
    """Fixed 2/2 research policy; `now` must come from a trusted clock in deployment.

    Candidate is only a proposed (size, root), not an authenticated log receipt.
    Every response is independently authenticated; a match is not freshness.
    Proofs indexed by (lower_size, higher_size); never skip a valid higher head.
    """
    if type(now) is not int or type(max_age) is not int or not 0 < max_age <= 3600 or type(future_skew) is not int or not 0 <= future_skew <= 60:
        return HOLD + 'CLOCK_POLICY'
    observed = {}
    try:
        for name, raw in replies:
            if name not in REQUIRED or name in observed:
                return HOLD + 'WITNESS_IDENTITY'
            if type(raw) is not bytes or not 0 < len(raw) <= 4096:
                return HOLD + 'INVALID_NOTE'
            size, root, ts = note(raw, KEYS[name])
            if not now-max_age <= ts <= now+future_skew:
                return HOLD + 'SIGNED_AGE'
            observed[name] = (size, root)
        if frozenset(observed) != REQUIRED:
            return HOLD + 'READ_QUORUM'
        low, high = sorted(observed.values())
        if low[0] == high[0]:
            if low[1] != high[1]:
                return HOLD + 'WITNESS_CONFLICT'
        else:
            path = proofs.get((low[0], high[0]))
            if type(path) not in (list, tuple) or not 1 <= len(path) <= 64 or any(type(x) is not bytes or len(x) != 32 for x in path):
                return HOLD + 'CONSISTENCY_UNAVAILABLE'
            try:
                consistency(low[0], high[0], low[1], high[1], list(path))
            except (ValueError, IndexError):
                return HOLD + 'CONSISTENCY_INVALID'
        if type(candidate) is not tuple or len(candidate) != 2 or type(candidate[0]) is not int or type(candidate[1]) is not bytes or len(candidate[1]) != 32:
            return HOLD + 'CANDIDATE_INVALID'
        if candidate[0] < high[0]:
            return HOLD + 'BELOW_OBSERVED_REFERENCE'
        if candidate != high:
            return HOLD + 'CANDIDATE_NOT_OBSERVED'
        return REVIEW
    except (ValueError, InvalidSignature, TypeError, KeyError, IndexError, AttributeError, OverflowError):
        return HOLD + 'INVALID_NOTE'


def run():
    p = Path(__file__).resolve().parent
    a, b = ((p / (n + '.note')).read_bytes() for n in ('markovian', 'geomys'))
    x, y = note(a, KEYS['markovian']), note(b, KEYS['geomys'])
    low, high = x[:2], y[:2]
    # Historical reference clock, NOT a live freshness measurement.
    now = max(x[2], y[2]) + 60
    proof = {(low[0], high[0]): [bytes.fromhex(s) for s in (p / '665-668.txt').read_text().splitlines()]}
    both = [('markovian', a), ('geomys', b)]
    broken = {k: v[:-1] for k, v in proof.items()}
    cases = [
        ('both_valid', high, both, proof, now, REVIEW),
        ('reorder', high, both[::-1], proof, now, REVIEW),
        ('old_candidate', low, both, proof, now, HOLD+'BELOW_OBSERVED_REFERENCE'),
        ('newer_witness_missing', low, both[:1], proof, now, HOLD+'READ_QUORUM'),
        ('older_witness_missing', high, both[1:], proof, now, HOLD+'READ_QUORUM'),
        ('none', low, [], proof, now, HOLD+'READ_QUORUM'),
        ('duplicate', low, [both[0], both[0]], proof, now, HOLD+'WITNESS_IDENTITY'),
        ('unknown', low, [('unknown', a), both[1]], proof, now, HOLD+'WITNESS_IDENTITY'),
        ('cross_identity', low, [('geomys', a), both[0]], proof, now, HOLD+'INVALID_NOTE'),
        ('tamper', high, [both[0], ('geomys', b.replace(b'281668', b'281669'))], proof, now, HOLD+'INVALID_NOTE'),
        ('missing_path', high, both, {}, now, HOLD+'CONSISTENCY_UNAVAILABLE'),
        ('short_path', high, both, broken, now, HOLD+'CONSISTENCY_INVALID'),
        ('wrong_root', (high[0], bytes(32)), both, proof, now, HOLD+'CANDIDATE_NOT_OBSERVED'),
        ('unobserved_higher', (high[0]+1, high[1]), both, proof, now, HOLD+'CANDIDATE_NOT_OBSERVED'),
        ('expired', high, both, proof, now+3600, HOLD+'SIGNED_AGE'),
        ('future', high, both, proof, min(x[2], y[2])-61, HOLD+'SIGNED_AGE'),
        ('bad_clock', high, both, proof, None, HOLD+'CLOCK_POLICY'),
        ('bool_candidate', (True, high[1]), both, proof, now, HOLD+'CANDIDATE_INVALID'),
        ('same_valid_notes_replayed_within_window_RED', high, both, proof, now+1, REVIEW),
    ]
    for label, candidate, replies, paths, clock, expected in cases:
        got = decide(candidate, replies, paths, clock)
        if got != expected: raise AssertionError((label, got, expected))
        print(label, got, 'PASS')
    # Combinatorial model only: high was durably retained by a write quorum.
    # Each honest intersection member returns at least its retained reference.
    members = set(range(4))
    quorums = list(map(set, combinations(members, 3)))
    faults = [set()] + [{i} for i in members]
    tested = 0
    for write in quorums:
        for read in quorums:
            for faulty in faults:
                if not (write & read) - faulty: raise AssertionError('no honest intersection')
                tested += 1
    print('3of4_read_write_intersection', tested, 'PASS_MODEL_ONLY')
    # Higher state held by just one unavailable witness can be invisible.
    omitted = {0}; responding = {1,2,3}
    if omitted & responding: raise AssertionError('bad negative control')
    print('higher_held_by_one_omitted_witness RED_MODEL_ONLY')
    print('19/19 expected fixture controls; 80/80 quorum intersection cases; 2 residual REDs; GENESIS NO_GO')

if __name__ == '__main__': run()
