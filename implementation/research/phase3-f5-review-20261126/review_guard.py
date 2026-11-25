"""Local research guards. No authenticated network or external custody claim."""
from dataclasses import asdict
from message_journal import ZERO_HASH, _canonical, _hash


def verified_head(records, floor=(0, ZERO_HASH)):
    count, digest = floor
    if type(count) is not int or not 0 <= count <= len(records):
        raise ValueError('invalid or regressed floor')
    previous = history = ZERO_HASH
    if count == 0 and digest != history:
        raise ValueError('invalid genesis floor')
    for i, record in enumerate(records, 1):
        body = asdict(record)
        commitment = body.pop('cumulative_history_commitment')
        record_hash = body.pop('record_hash')
        if (body['message_sequence'] != i or body['cumulative_message_count'] != i
                or body['previous_record_hash'] != previous
                or body['previous_history_commitment'] != history
                or body['direction'] not in ('incoming', 'outgoing')):
            raise ValueError('nonconsecutive message proof')
        content_hash = body['content_hash']
        if len(content_hash) != 64 or len(bytes.fromhex(content_hash)) != 32:
            raise ValueError('invalid content hash')
        history = _hash(bytes.fromhex(history) + _canonical(body))
        previous = _hash(_canonical({**body, 'cumulative_history_commitment': history}))
        if (history, previous) != (commitment, record_hash):
            raise ValueError('message proof hash mismatch')
        if i == count and history != digest:
            raise ValueError('message proof does not extend retained floor')
    return len(records), history


def verified_export(journal, expected=None):
    """Verify and reconstruct from one read snapshot; never return metadata alone."""
    db = journal.connection
    db.execute('SAVEPOINT review_export')
    try:
        records = journal.records()
        head = verified_head(records)
        ok, detail = journal.verify(expected_checkpoint=expected)
        if not ok:
            raise ValueError(detail)
        if expected is not None and head != expected:
            raise ValueError('external checkpoint mismatch')
        return {'cumulative_message_count': head[0], 'cumulative_history_commitment': head[1]}
    finally:
        db.execute('RELEASE review_export')
