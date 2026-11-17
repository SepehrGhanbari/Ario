#!/usr/bin/env python3
"""W14 — disposable Linux-UID custody lab, NO Ario keys, no real effects.

Four distinct unprivileged numeric UIDs hold grant, revocation, anchor and
verification roles. A root-only orchestration process creates the disposable
folder and drops child privileges before key generation; it is deliberately
out of the trust model. Because a common root CAN still alter everything,
this is DAC separation, NOT independent administrators or HSM isolation.

Use only in an already-isolated, disposable Linux root container.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ROLE_UIDS = {"grant": 31801, "revoker": 31802, "anchor": 31803, "verifier": 31804}
DOMAINS = {"grant": "W14-LAB-GRANT-V1", "revoker": "W14-LAB-REV-HEAD-V1", "anchor": "W14-LAB-ANCHOR-V1"}


def raw_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write_file(path, content, mode=0o644):
    """Atomic publication, not durable transaction proof after power failure."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp-" + str(os.getpid()))
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def load_key(path):
    raw = Path(path).read_bytes()
    if len(raw) != 32:
        raise ValueError("not a raw Ed25519 private key")
    return Ed25519PrivateKey.from_private_bytes(raw)


def make_key(role_dir, pub_dir):
    private = role_dir / "private.key"
    public = pub_dir / "public.hex"
    if private.exists() or public.exists():
        raise ValueError("key already exists")
    sk = Ed25519PrivateKey.generate()
    sk_bytes = sk.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                serialization.NoEncryption())
    fd = os.open(str(private), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(sk_bytes)
        f.flush()
        os.fsync(f.fileno())
    write_file(public, sk.public_key().public_bytes(serialization.Encoding.Raw,
                                                    serialization.PublicFormat.Raw).hex().encode("ascii") + b"\n")
    return {"uid": os.geteuid(), "public_sha256": sha(bytes.fromhex(public.read_text().strip()))}


def sign(sk, domain, body):
    token = {"domain": domain, "body": body}
    signature = sk.sign(raw_json(token)).hex()
    return {**token, "signature": signature}


def verify(public_hex, expected_domain, signed):
    if (type(signed) is not dict or set(signed) != {"domain", "body", "signature"} or
            signed["domain"] != expected_domain or type(signed["body"]) is not dict or
            type(signed["signature"]) is not str or len(signed["signature"]) != 128):
        return None
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(
            bytes.fromhex(signed["signature"]),
            raw_json({"domain": signed["domain"], "body": signed["body"]}))
    except (ValueError, InvalidSignature, TypeError):
        return None
    return signed["body"]


def output(obj):
    sys.stdout.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")


def read_json(path):
    return json.loads(Path(path).read_text("utf8"))


def role_command(args):
    d = Path(args.root)
    role = args.role
    if os.geteuid() != ROLE_UIDS[role]:
        raise PermissionError("role must use its unique unprivileged UID")
    private = d / role / "private"
    public = d / role / "public"
    key_file = private / "private.key"
    if args.cmd == "generate":
        output({"cmd": "generate", "role": role, **make_key(private, public)})
    elif args.cmd == "probe":
        other = d / args.other / "private" / "private.key"
        try:
            with open(other, "rb") as f:
                f.read(1)  # never print secrets
        except PermissionError:
            output({"cmd": "probe", "uid": os.geteuid(), "other": args.other, "access": "DENIED"})
        else:
            output({"cmd": "probe", "uid": os.geteuid(), "other": args.other, "access": "EXPOSED"})
    elif args.cmd == "grant":
        if role != "grant":
            raise ValueError("wrong role for grant")
        body = {"version": 1, "grant_id": args.grant_id, "principal": "TEST_USER",
                "operation": "SEND", "resource": "report-1", "destination": args.destination,
                "not_before": 100, "expires": 200}
        packet = sign(load_key(key_file), DOMAINS[role], body)
        dest = public / ("grant_" + args.grant_id + ".json")
        write_file(dest, raw_json(packet) + b"\n")
        output({"cmd": "grant", "uid": os.geteuid(), "grant_id": args.grant_id,
                "destination": body["destination"], "packet_sha256": sha(raw_json(packet))})
    elif args.cmd == "head":
        if role != "revoker":
            raise ValueError("wrong role for revocation head")
        state_file = private / "state.json"
        state = read_json(state_file) if state_file.exists() else {"epoch": -1, "revoked": [], "prior_head": None}
        if args.revoke:
            if state["epoch"] < 0:
                raise ValueError("must issue genesis head before revocation")
            if args.revoke in state["revoked"]:
                raise ValueError("already revoked")
            state["revoked"].append(args.revoke)
        new_epoch = state["epoch"] + 1
        body = {"version": 1, "epoch": new_epoch, "revoked": sorted(state["revoked"]),
                "previous_head_sha256": state["prior_head"]}
        packet = sign(load_key(key_file), DOMAINS[role], body)
        write_file(public / "head.json", raw_json(packet) + b"\n")
        write_file(state_file, raw_json({"epoch": new_epoch, "revoked": state["revoked"],
                                         "prior_head": sha(raw_json(packet))}) + b"\n", mode=0o600)
        output({"cmd": "head", "uid": os.geteuid(), "epoch": new_epoch,
                "revoked_count": len(body["revoked"])})
    elif args.cmd == "verify":
        if role != "verifier":
            raise ValueError("wrong role for read-only verifier")
        trust = read_json(d / "trusted_public.json")
        result = check_packets(
            trust, read_json(d / args.grant_packet), read_json(d / args.head_packet),
            read_json(d / args.anchor_packet),
            {"principal": "TEST_USER", "operation": "SEND", "resource": "report-1",
             "destination": args.destination}, now=args.now)
        output({"uid": os.geteuid(), **result})
    elif args.cmd == "anchor":
        if role != "anchor":
            raise ValueError("wrong role for anchor")
        trust = read_json(d / "trusted_public.json")
        head_packet = read_json(d / "revoker" / "public" / "head.json")
        head = verify(trust["revoker"], DOMAINS["revoker"], head_packet)
        if head is None:
            raise ValueError("revoker signature failed")
        state_file = private / "state.json"
        previous = read_json(state_file) if state_file.exists() else {"epoch": -1, "head_hash": None}
        if (head.get("epoch") != previous["epoch"] + 1 or
                head.get("previous_head_sha256") != previous["head_hash"]):
            raise ValueError("STALE_OR_FORKED_REVOCATION_HEAD")
        body = {"version": 1, "epoch": head["epoch"], "head_sha256": sha(raw_json(head_packet)),
                "prev_anchor_epoch": previous["epoch"]}
        packet = sign(load_key(key_file), DOMAINS["anchor"], body)
        write_file(public / "anchor.json", raw_json(packet) + b"\n")
        write_file(state_file, raw_json({"epoch": head["epoch"],
                                         "head_hash": sha(raw_json(head_packet))}) + b"\n", mode=0o600)
        output({"cmd": "anchor", "uid": os.geteuid(), "epoch": head["epoch"]})
    else:
        raise ValueError("unknown role command")


def check_packets(trust, grant_packet, head_packet, anchor_packet, candidate, now=150):
    """No real authorization: positive only means ready for a *separate* gate."""
    base = {"authority": "NOT_ESTABLISHED", "real_effects": 0,
            "true_user_approval": "NOT_ESTABLISHED", "independent_admin_custody": False}
    def verdict(status, why):
        return {**base, "verdict": status, "reason": why}
    grant = verify(trust["grant"], DOMAINS["grant"], grant_packet)
    head = verify(trust["revoker"], DOMAINS["revoker"], head_packet)
    anchor = verify(trust["anchor"], DOMAINS["anchor"], anchor_packet)
    if grant is None: return verdict("DENY", "GRANT_SIGNATURE_OR_DOMAIN")
    if head is None: return verdict("DENY", "REVOCATION_SIGNATURE_OR_DOMAIN")
    if anchor is None: return verdict("DENY", "ANCHOR_SIGNATURE_OR_DOMAIN")
    if (set(grant) != {"version", "grant_id", "principal", "operation", "resource",
                       "destination", "not_before", "expires"} or
        set(head) != {"version", "epoch", "revoked", "previous_head_sha256"} or
        set(anchor) != {"version", "epoch", "head_sha256", "prev_anchor_epoch"} or
        grant["version"] != 1 or head["version"] != 1 or anchor["version"] != 1 or
        type(head["epoch"]) is not int or type(anchor["epoch"]) is not int or
        type(head["revoked"]) is not list or not all(type(x) is str for x in head["revoked"])):
        return verdict("UNKNOWN", "INVALID_BODY_SCHEMA")
    if (anchor["epoch"] != head["epoch"] or anchor["head_sha256"] != sha(raw_json(head_packet))):
        return verdict("DENY", "STALE_OR_UNANCHORED_HEAD")
    if type(now) is not int or type(grant["not_before"]) is not int or type(grant["expires"]) is not int:
        return verdict("UNKNOWN", "CLOCK_UNTRUSTED_OR_WRONG_TYPE")
    if not grant["not_before"] <= now < grant["expires"]:
        return verdict("DENY", "GRANT_EXPIRED_OR_NOT_YET")
    if grant["grant_id"] in head["revoked"]:
        return verdict("DENY", "GRANT_REVOKED")
    if any(grant[k] != candidate.get(k) for k in ("principal", "operation", "resource", "destination")):
        return verdict("DENY", "GRANT_NOT_BOUND_TO_PROPOSED_SCOPE")
    return verdict("ELIGIBLE_FOR_SEPARATE_GATE", "SIGNED_PACKET_AND_ANCHORED_SCOPE_MATCH_NOT_AUTHORITY")


def drop(uid):
    os.setgroups([])
    os.setgid(uid)
    os.setuid(uid)


def run_role(base, role, cmd, *args):
    argv = [sys.executable, os.path.abspath(__file__), "--mode", "role", "--root", str(base),
            "--role", role, "--cmd", cmd] + [str(a) for a in args]
    launcher=["setpriv", "--reuid", str(ROLE_UIDS[role]), "--regid", str(ROLE_UIDS[role]),
              "--clear-groups", "--"]
    child = subprocess.run(launcher+argv, capture_output=True, text=True, timeout=10)
    if child.returncode:
        raise AssertionError(f"{role}/{cmd} returned {child.returncode}: {child.stderr.strip()[-400:]}")
    return json.loads(child.stdout.strip())


def prepare(base):
    os.chmod(base, 0o755)
    for role, uid in ROLE_UIDS.items():
        root = base / role
        root.mkdir(mode=0o755)
        (root / "private").mkdir(mode=0o700)
        (root / "public").mkdir(mode=0o755)
        for path, mode in ((root,0o755),(root / "private",0o700),(root / "public",0o755)):
            os.chown(path, uid, uid)
            os.chmod(path, mode)
    for role in ("grant", "revoker", "anchor"):
        data=run_role(base, role, "generate")
        assert data["uid"] == ROLE_UIDS[role]
    trusted={role:(base / role / "public" / "public.hex").read_text().strip() for role in ("grant", "revoker", "anchor")}
    write_file(base / "trusted_public.json", raw_json(trusted) + b"\n", 0o444)
    os.chmod(base / "trusted_public.json",0o444)
    return trusted


def orchestrate():
    if sys.platform != "linux" or os.geteuid()!=0:
        raise RuntimeError("W14 native UID test REQUIRES a disposable Linux root container; no simulated success fallback")
    results=[]
    def check(case, condition, observed, interpretation):
        assert condition, f"{case}: {observed}"
        results.append({"id": case, "observed": observed, "scope": interpretation})
    with tempfile.TemporaryDirectory(prefix="ario_w14_disposable_linux_uids_") as tmp:
        base = Path(tmp)
        trust=prepare(base)
        for actor, target in (("grant","revoker"),("revoker","grant"),("grant","anchor"),
                              ("anchor","revoker"),("verifier","grant"),("verifier","revoker")):
            p=run_role(base,actor,"probe","--other",target)
            check(f"UID_{actor}_CANNOT_READ_{target}_PRIVATE",p["access"]=="DENIED",
                  p["access"], "actual OS kernel DAC for two distinct unprivileged UIDs")
        check("KEYS_ARE_DISTINCT",len(set(trust.values()))==3,
              "THREE_DIFFERENT_PUBLIC_KEYS", "distinct public keys, common root still has every privilege")
        for actor in ("grant", "verifier"):
            attempted=subprocess.run(["setpriv","--reuid",str(ROLE_UIDS[actor]),
                        "--regid",str(ROLE_UIDS[actor]),"--clear-groups","--",
                        sys.executable,"-c",
                        "import os,sys;sys.exit(0 if os.access(sys.argv[1],os.W_OK) else 7)",
                        str(base/"trusted_public.json")],capture_output=True,timeout=5)
            check(f"TRUST_REGISTRY_NOT_WRITABLE_BY_{actor}",attempted.returncode==7,
                  "DENIED", "public key registry is root-owned; not modifiable by unprivileged roles")
        # Negative custody finding: test *root* can access all three synthetic private keys.
        root_reads=all(len((base / role / "private" / "private.key").read_bytes())==32
                       for role in ("grant", "revoker", "anchor"))
        check("SAME_ROOT_CAN_READ_ALL_PRIVATE_KEYS",root_reads,"EXPOSED_TO_COMMON_ROOT",
              "same-root control defeats administrative independence even when DAC works")
        run_role(base,"grant","grant","--grant-id","G-1","--destination","review@example.invalid")
        run_role(base,"revoker","head")
        run_role(base,"anchor","anchor")
        read=lambda path:read_json(base / path)
        # The verification itself runs as a FOURTH, distinct non-root OS identity.
        # Public trust config is root-owned 0444, not mutable by this verifier.
        def check_as_verifier(g="grant/public/grant_G-1.json",h="revoker/public/head.json",
                              a="anchor/public/anchor.json",destination="review@example.invalid",
                              now=150):
            return run_role(base,"verifier","verify","--grant-packet",g,
                            "--head-packet",h,"--anchor-packet",a,"--destination",destination,
                            "--now",str(now))
        grant=read("grant/public/grant_G-1.json")
        h0=read("revoker/public/head.json")
        a0=read("anchor/public/anchor.json")
        # Archive genuine prior signed snapshots in read-only scratch fixtures.
        fixtures=base/"fixtures"
        fixtures.mkdir(mode=0o755)
        write_file(fixtures/"head0.json",raw_json(h0)+b"\n",0o444)
        write_file(fixtures/"anchor0.json",raw_json(a0)+b"\n",0o444)
        v0=check_as_verifier()
        check("VERIFY_PROCESS_ACTUALLY_DIFFERENT_UID",v0["uid"]==ROLE_UIDS["verifier"],
              v0["uid"],"positive UID proof for read-only verification process")
        check("INITIAL_UNREVOKED_MATCH",v0["verdict"]=="ELIGIBLE_FOR_SEPARATE_GATE",
              v0["verdict"], "synthetic grant and signed epoch 0 anchor, zero external authority")
        check("VERIFIER_NO_REAL_EFFECT",v0["real_effects"]==0 and v0["authority"]=="NOT_ESTABLISHED",
              "NO_EFFECT_OR_AUTHORITY", "a source/permission signature is NOT permission to execute")
        bad_dest=check_as_verifier(destination="attacker@example.invalid")
        check("GRANT_TARGET_MISMATCH",bad_dest["reason"]=="GRANT_NOT_BOUND_TO_PROPOSED_SCOPE",
              bad_dest["reason"],"signed token does not permit substituting the target")
        expired=check_as_verifier(now=201)
        check("GRANT_EXPIRED",expired["reason"]=="GRANT_EXPIRED_OR_NOT_YET",
              expired["reason"],"toy verifier rejects token past declared expiry")
        future=check_as_verifier(now=99)
        check("GRANT_NOT_YET_ACTIVE",future["reason"]=="GRANT_EXPIRED_OR_NOT_YET",
              future["reason"],"toy verifier rejects token before start time")
        # Cross-role signed bytes used in the grant field must be refused.
        cross=check_as_verifier("fixtures/head0.json")
        check("REVOKER_SIGNATURE_NOT_A_GRANT",cross["reason"]=="GRANT_SIGNATURE_OR_DOMAIN",
              cross["reason"], "domain/key mismatch blocks cross-role substitution")
        # A tampered signed head or anchor is rejected (never accepted on a malformed source).
        forged_head=json.loads(raw_json(h0))
        forged_head["body"]["epoch"] += 1
        write_file(fixtures/"tampered_head.json",raw_json(forged_head)+b"\n",0o444)
        t_head=check_as_verifier(h="fixtures/tampered_head.json")
        check("WITNESS_SIGNATURE_TAMPER",t_head["reason"]=="REVOCATION_SIGNATURE_OR_DOMAIN",
              t_head["reason"],"changing signed head bytes invalidates witness signature")
        forged_anchor=json.loads(raw_json(a0))
        forged_anchor["body"]["epoch"] += 1
        write_file(fixtures/"tampered_anchor.json",raw_json(forged_anchor)+b"\n",0o444)
        t_anchor=check_as_verifier(a="fixtures/tampered_anchor.json")
        check("ANCHOR_SIGNATURE_TAMPER",t_anchor["reason"]=="ANCHOR_SIGNATURE_OR_DOMAIN",
              t_anchor["reason"],"changing signed anchor bytes invalidates anchor signature")
        run_role(base,"revoker","head","--revoke","G-1")
        h1=read("revoker/public/head.json")
        # New revocation head exists but independent anchor has not yet advanced.
        lag=check_as_verifier(a="fixtures/anchor0.json")
        check("UNANCHORED_REVOCATION_HEAD",lag["reason"]=="STALE_OR_UNANCHORED_HEAD",
              lag["reason"], "unanchored epoch mismatch is HOLD/DENY, not accepted")
        run_role(base,"anchor","anchor")
        a1=read("anchor/public/anchor.json")
        now=check_as_verifier()
        check("REVOKED_GRANT_REFUSED",now["reason"]=="GRANT_REVOKED",
              now["reason"], "fresh witness anchor and revocation head")
        stalehead=check_as_verifier(h="fixtures/head0.json")
        check("STALE_REVOCATION_WITH_FRESH_ANCHOR",stalehead["reason"]=="STALE_OR_UNANCHORED_HEAD",
              stalehead["reason"], "anchor comparison reveals stale presented witness head")
        offline=check_as_verifier(h="fixtures/head0.json",a="fixtures/anchor0.json")
        check("OFFLINE_VERIFIER_BOTH_STALE_STILL_ELIGIBLE",offline["verdict"]=="ELIGIBLE_FOR_SEPARATE_GATE",
              offline["verdict"], "negative: stale signed revocation and stale signed anchor still agree")
        # Test that each domain cannot change another's public snapshot files (DAC).
        for actor, target in (("grant", "revoker/public/head.json"),
                              ("revoker","anchor/public/anchor.json"),
                              ("anchor","grant/public/grant_G-1.json")):
            path=base / target
            # Signed public files are mode 0644, owner-write only.
            # This probes modification of a different role's published signed packet.
            check(f"CROSS_{actor}_CANNOT_MODIFY_{target.replace('/','_')}",
                  not bool(subprocess.run(["setpriv","--reuid",str(ROLE_UIDS[actor]),
                        "--regid",str(ROLE_UIDS[actor]),"--clear-groups","--",
                        sys.executable,"-c","import os,sys;sys.exit(0 if os.access(sys.argv[1],os.W_OK) else 7)",str(path)],
                       capture_output=True,timeout=5).returncode==0),
                  "DENIED", "kernel DAC prevents unprivileged cross-domain overwrite")
        # Actual root orchestration can nevertheless rewind both signed *public* views.
        # Only disposable test fixture, without rewriting private state/keys.
        write_file(base/"revoker"/"public"/"head.json", raw_json(h0)+b"\n")
        write_file(base/"anchor"/"public"/"anchor.json", raw_json(a0)+b"\n")
        restored=check_as_verifier()
        check("COMMON_ROOT_ROLLBACK_BOTH_VIEWS",restored["verdict"]=="ELIGIBLE_FOR_SEPARATE_GATE",
              restored["verdict"],"negative: shared root can revert both signed public views and fool a stale-only verifier")
        write_file(fixtures/"anchor1.json",raw_json(a1)+b"\n",0o444)
        freshexternal=check_as_verifier(a="fixtures/anchor1.json")
        check("EXTERNALLY_RETAINED_ANCHOR_DETECTS_ROLLBACK",freshexternal["reason"]=="STALE_OR_UNANCHORED_HEAD",
              freshexternal["reason"],"conditional: if an untampered latest anchor is available")
        # Even though a common root rolled the public head back, the untouched
        # anchor-private high-water file (under a different UID) refuses epoch 0.
        try:
            run_role(base,"anchor","anchor")
        except AssertionError as exc:
            anchor_rejected="STALE_OR_FORKED_REVOCATION_HEAD" in str(exc)
        else:
            anchor_rejected=False
        check("ANCHOR_PRIVATE_HIGHWATER_REJECTS_OLD_HEAD",anchor_rejected,
              "STALE_OR_FORKED_REVOCATION_HEAD" if anchor_rejected else "WRONGLY_ACCEPTED",
              "different UID with surviving private high-water can reject stale issuer state")
        # The signature signer itself can issue a synthetic "malicious" grant. This lab
        # never authenticates the human intention, only signature/role/shape.
        run_role(base,"grant","grant","--grant-id","G-EVIL","--destination","attacker@example.invalid")
        # A correctly signed, but illicitly requested grant passes syntactic checks.
        ev=check_as_verifier(g="grant/public/grant_G-EVIL.json",
                             destination="attacker@example.invalid")
        check("COMPROMISED_ACTUAL_ISSUER_NOT_DETECTABLE",ev["verdict"]=="ELIGIBLE_FOR_SEPARATE_GATE",
              ev["verdict"],"negative: genuine role key can sign unauthorized scope; no human-approval proof")
        # Even an intact latest witness/anchor would not reject a new (unrevoked)
        # grant signed by a compromised *actual* grant issuer. The witness has
        # no evidence of the legitimate user's intent.
        write_file(fixtures/"head1.json",raw_json(h1)+b"\n",0o444)
        ev_fresh=check_as_verifier(g="grant/public/grant_G-EVIL.json",
                    h="fixtures/head1.json",a="fixtures/anchor1.json",
                    destination="attacker@example.invalid")
        check("FRESH_ANCHOR_CANNOT_FIX_COMPROMISED_GRANT_ISSUER",
              ev_fresh["verdict"]=="ELIGIBLE_FOR_SEPARATE_GATE",ev_fresh["verdict"],
              "negative: fresh witness still has no authenticated user-consent input")
    return {"schema":"ARIO_W14_NATIVE_UID_CUSTODY_V1", "environment":"DISPOSABLE_LINUX_ROOT_CONTAINER",
            "python":sys.version.split()[0],"cases":len(results),"results":results,
            "os_identity_uids":ROLE_UIDS,"private_keys_exported_to_results":False,
            "trusted_key_registry_root_owned":True,"independent_admin_domains":False,
            "root_can_read_any_key":True,"signed_head_rollback_resistance_without_external_copy":False,
            "real_user_consent_proven":False,"production_execution":False,"effects":0,
            "report":"kernel_DAC_separation_reproduced;common_root_rollback_and_stale_verifier_failures_reproduced"}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("role","run"),default="run")
    p.add_argument("--root")
    p.add_argument("--role",choices=list(ROLE_UIDS))
    p.add_argument("--cmd",choices=("generate","probe","grant","head","anchor","verify"))
    p.add_argument("--grant-id",default="G-1")
    p.add_argument("--destination",default="review@example.invalid")
    p.add_argument("--revoke",default=None)
    p.add_argument("--grant-packet")
    p.add_argument("--head-packet")
    p.add_argument("--anchor-packet")
    p.add_argument("--other",choices=list(ROLE_UIDS))
    p.add_argument("--now",type=int,default=150)
    args=p.parse_args()
    if args.mode=="role":
        if not args.root or not args.role or not args.cmd:
            raise ValueError("role invocation incomplete")
        role_command(args)
    else:
        output(orchestrate())

if __name__=="__main__":
    main()
