"""Independent W4-C adversarial negative checks; laboratory only."""
from dataclasses import replace
import pytest
import w4c_distributed_lab as w
import test_w4c_distributed_lab as fixture

GIANT = 10**5000


@pytest.mark.parametrize("bad", [[], {}, None, "PEER-" + "X"*250, "РEER-1", True])
def test_invalid_replica_identity_is_bounded_rejection(bad):
    p = fixture.replicas()
    altered = (replace(p[0], peer_id=bad),) + p[1:]
    out = w.assess(altered, fixture.reports(), fixture.request(), w.ReplayView(()))
    assert out.status == "REJECTED"
    assert out.reason == "W4C_REPLICA_SHAPE_INVALID"
    fixture.fail_closed(out)


@pytest.mark.parametrize("field", ["revision", "checked_at", "expires_at"])
def test_unbounded_snapshot_integer_rejected_without_crash(field):
    view = fixture.registry(**{field: GIANT})
    out = fixture.run(nodes=fixture.replicas(view))
    assert out.status == "REJECTED"
    assert out.reason == "W4C_INVALID_REGISTRY_SNAPSHOT"
    fixture.fail_closed(out)


def test_unbounded_revocation_integer_rejected_without_crash():
    view=fixture.registry(revocations=(w.Revocation(fixture.enrollment(0).key_id, GIANT,"COMPROMISED"),))
    out=fixture.run(nodes=fixture.replicas(view))
    assert out.status=="REJECTED" and out.reason=="W4C_INVALID_REGISTRY_SNAPSHOT"
    fixture.fail_closed(out)


@pytest.mark.parametrize("field", ["registry_revision", "mock_tick"])
def test_unbounded_request_integer_rejected_without_crash(field):
    out = fixture.run(scope=fixture.request(**{field: GIANT}))
    assert out.status=="REJECTED" and out.reason=="W4C_CONTEXT_TIME_OR_REVISION_INVALID"
    fixture.fail_closed(out)


def test_unbounded_recovery_time_remains_unknown():
    old=fixture.registry(frozen=True)
    new=fixture.registry(root_ref="INJECTED-ROOT-B",epoch="SYNTHETIC-02",revision=8,predecessor_digest=w._digest(old))
    case=w.RecoveryProposal(old,new,(("ENDORSER-A","GROUP-A"),("ENDORSER-B","GROUP-B")),True)
    out=w.examine_recovery(case,new.root_ref,GIANT)
    assert out.status=="UNKNOWN" and out.reason=="W4C_RECOVERY_TIME_UNAVAILABLE"
    fixture.fail_closed(out)
