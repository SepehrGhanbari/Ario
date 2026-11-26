"""Pinned trust boundary for the research verifier.

The trust root is supplied by the operator from outside the candidate tree. It
pins the exact verifier source bytes and the policy bytes. This detects
candidate-side edits to a copied checker/policy, but it is NOT independent
custody: the same OS administrator can rewrite both the candidate and the pin.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

TRUST_SCHEMA = "ARIO-TRUST-ROOT-RESEARCH-0.1"
POLICY_SCHEMA = "ARIO-TRUSTED-MERGE-POLICY-RESEARCH-0.1"
MAX_TRUST_BYTES = 256 * 1024
MAX_POLICY_BYTES = 256 * 1024


class TrustError(ValueError):
    """The pinned trust boundary or policy is missing, malformed or changed."""


def _strict_json(raw: bytes, cap: int, label: str) -> dict:
    if len(raw) > cap:
        raise TrustError(f"{label} exceeds byte cap")

    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise TrustError(f"{label} has a duplicate JSON member")
            obj[key] = value
        return obj

    def bad_constant(_):
        raise TrustError(f"{label} has a nonstandard JSON constant")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                           parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, TrustError):
            raise
        raise TrustError(f"{label} is malformed JSON") from exc
    if not isinstance(value, dict):
        raise TrustError(f"{label} must be a JSON object")
    return value


def _read(path: Path, cap: int, label: str) -> bytes:
    if path.is_symlink():
        raise TrustError(f"{label} must not be a symlink")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise TrustError(f"{label} is not a regular file")
    return resolved.read_bytes()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _positive(value) -> bool:
    return type(value) is int and value > 0


def load_trust_root(path: str | Path) -> dict:
    try:
        root = _strict_json(_read(Path(path), MAX_TRUST_BYTES, "trust root"),
                            MAX_TRUST_BYTES, "trust root")
    except OSError as exc:
        raise TrustError("trust root is unreadable") from exc
    fields = {"schema", "policy_file", "policy_sha256", "verifier_sha256", "pinned_at"}
    if set(root) != fields or root["schema"] != TRUST_SCHEMA:
        raise TrustError("trust root fields or schema are unsupported")
    if not isinstance(root["policy_file"], str) or not root["policy_file"] or "/" in root["policy_file"]:
        raise TrustError("trust root policy_file is invalid")
    if not isinstance(root["policy_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", root["policy_sha256"]):
        raise TrustError("trust root policy digest is invalid")
    if not isinstance(root["pinned_at"], str) or not root["pinned_at"].strip():
        raise TrustError("trust root pinned_at is invalid")
    hashes = root["verifier_sha256"]
    if not isinstance(hashes, dict) or not hashes:
        raise TrustError("trust root verifier_sha256 is invalid")
    for name, digest in hashes.items():
        if (not isinstance(name, str) or not name or "/" in name or "\\" in name
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise TrustError("trust root verifier entry is invalid")
    return root


def verify_trust(verifier_dir: str | Path, trust_root: dict) -> dict:
    directory = Path(verifier_dir)
    if directory.is_symlink():
        raise TrustError("verifier directory must not be a symlink")
    directory = directory.resolve(strict=True)
    if not directory.is_dir():
        raise TrustError("verifier directory is not a directory")
    code_files = {path.name for path in directory.glob("*.py") if path.is_file()}
    policy_name = trust_root["policy_file"]
    expected = set(trust_root["verifier_sha256"]) | {policy_name}
    if code_files | {policy_name} != expected:
        raise TrustError("verifier directory does not match the pinned file set")
    observed = {}
    for name in sorted(expected):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise TrustError(f"pinned file is missing or a symlink: {name}")
        data = path.read_bytes()
        digest = _sha256(data)
        if digest != trust_root["verifier_sha256"].get(name, trust_root["policy_sha256"]):
            raise TrustError(f"pinned file bytes changed: {name}")
        observed[name] = digest
    policy_bytes = (directory / policy_name).read_bytes()
    if _sha256(policy_bytes) != trust_root["policy_sha256"]:
        raise TrustError("policy bytes changed")
    return {
        "policy_sha256": trust_root["policy_sha256"],
        "verifier_sha256": {name: observed[name] for name in sorted(observed) if name != policy_name},
        "pinned_at": trust_root["pinned_at"],
    }


def load_policy(verifier_dir: str | Path, trust_root: dict) -> dict:
    path = Path(verifier_dir) / trust_root["policy_file"]
    try:
        policy = _strict_json(_read(path, MAX_POLICY_BYTES, "policy"),
                              MAX_POLICY_BYTES, "policy")
    except OSError as exc:
        raise TrustError("policy is unreadable") from exc
    fields = {
        "schema", "scope", "repository", "required_approvals", "required_check",
        "allowed_merge_methods", "require_log_append", "log_path",
        "require_explicit_pr_association", "bypass_actor_ids", "protected_paths",
    }
    if set(policy) != fields or policy["schema"] != POLICY_SCHEMA:
        raise TrustError("policy fields or schema are unsupported")
    if policy["scope"] != "SYNTHETIC_TWO_ROLE_LAB_ONLY":
        raise TrustError("policy scope is not the synthetic two-role lab")
    repo = policy["repository"]
    if not isinstance(repo, dict) or set(repo) != {"id", "full_name"}:
        raise TrustError("policy repository is invalid")
    if not _positive(repo["id"]) or not isinstance(repo["full_name"], str) or not repo["full_name"]:
        raise TrustError("policy repository identity is invalid")
    if type(policy["required_approvals"]) is not int or not 1 <= policy["required_approvals"] <= 20:
        raise TrustError("policy required_approvals is invalid")
    check = policy["required_check"]
    if not isinstance(check, dict) or set(check) != {"name", "app_id", "workflow_id", "workflow_path"}:
        raise TrustError("policy required_check is invalid")
    if not all(isinstance(check[key], str) and check[key] for key in ("name", "workflow_path")):
        raise TrustError("policy check name/path is invalid")
    if not _positive(check["app_id"]) or not _positive(check["workflow_id"]):
        raise TrustError("policy app/workflow identity is invalid")
    methods = policy["allowed_merge_methods"]
    if not isinstance(methods, list) or not methods or len(methods) > 5 \
            or not all(method in {"merge", "squash", "rebase"} for method in methods):
        raise TrustError("policy allowed_merge_methods is invalid")
    if type(policy["require_log_append"]) is not bool \
            or type(policy["require_explicit_pr_association"]) is not bool:
        raise TrustError("policy booleans are invalid")
    if not isinstance(policy["log_path"], str) or not policy["log_path"] or policy["log_path"].startswith("/"):
        raise TrustError("policy log_path is invalid")
    bypass = policy["bypass_actor_ids"]
    if not isinstance(bypass, list) or len(bypass) > 100 or not all(_positive(x) for x in bypass):
        raise TrustError("policy bypass_actor_ids is invalid")
    protected = policy["protected_paths"]
    if not isinstance(protected, dict) or set(protected) != {"basenames", "prefixes", "name_pattern"}:
        raise TrustError("policy protected_paths is invalid")
    if (not isinstance(protected["basenames"], list) or not isinstance(protected["prefixes"], list)
            or not isinstance(protected["name_pattern"], str)):
        raise TrustError("policy protected path lists are invalid")
    try:
        re.compile(protected["name_pattern"])
    except re.error as exc:
        raise TrustError("policy protected name_pattern is invalid") from exc
    if not all(isinstance(x, str) and x for x in protected["basenames"] + protected["prefixes"]):
        raise TrustError("policy protected path entry is invalid")
    return policy
