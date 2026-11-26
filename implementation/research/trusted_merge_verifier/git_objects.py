"""Read-only Git object access for the trusted merge verifier.

The verifier derives diffs, blob identities and file contents from the
candidate repository's objects. It never executes candidate code, never runs
candidate hooks, and disables replace objects, external diff drivers and user
configuration. This is still same-user process separation, not custody.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

GIT_TIMEOUT = 30
MAX_BLOB_BYTES = 8 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{40}\Z")
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,200}\Z")


class GitObjectError(RuntimeError):
    """The candidate repository cannot provide trustworthy object data."""


@dataclass(frozen=True)
class Commit:
    sha: str
    tree: str
    parents: tuple[str, ...]


@dataclass(frozen=True)
class DiffEntry:
    status: str  # A, M, D, R, T
    old_path: str | None
    new_path: str | None
    old_mode: str
    new_mode: str
    old_blob: str | None
    new_blob: str | None
    score: int | None

    @property
    def path(self) -> str:
        return self.new_path if self.new_path is not None else self.old_path or ""


def _env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_PAGER": "cat",
        "LC_ALL": "C",
        "LANG": "C",
    })
    return env


class GitRepo:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        if not self.path.is_dir():
            raise GitObjectError("candidate path is not a directory")
        probe = self._run("rev-parse", "--git-dir", check=False)
        if probe.returncode != 0:
            raise GitObjectError("candidate path is not a Git repository")

    def _run(self, *args: str, check: bool = True, cap: int = 0) -> subprocess.CompletedProcess:
        cmd = [
            "git", "--no-replace-objects", "-C", str(self.path),
            "-c", "core.hooksPath=" + os.devnull,
            "-c", "core.fsmonitor=false",
            "-c", "core.pager=cat",
            "-c", "diff.external=",
            *args,
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=_env(), timeout=GIT_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            raise GitObjectError(f"git invocation failed: {type(exc).__name__}") from exc
        if check and result.returncode != 0:
            raise GitObjectError(f"git {args[0]} failed")
        if cap and len(result.stdout) > cap:
            raise GitObjectError("git output exceeds research cap")
        return result

    def resolve_ref(self, ref: str) -> str | None:
        if not isinstance(ref, str) or REF.fullmatch(ref) is None or ".." in ref or ref.endswith(".lock"):
            return None
        result = self._run("rev-parse", "--verify", "--quiet", f"refs/heads/{ref}^{{commit}}", check=False)
        if result.returncode != 0:
            return None
        sha = result.stdout.decode("ascii", "strict").strip()
        return sha if SHA.fullmatch(sha) else None

    def commit(self, rev: str) -> Commit:
        if not isinstance(rev, str) or SHA.fullmatch(rev) is None:
            raise GitObjectError("commit revision is not a full SHA")
        result = self._run("rev-list", "--parents", "-n", "1", rev, check=False)
        if result.returncode != 0:
            raise GitObjectError("commit is not present in the candidate repository")
        fields = result.stdout.decode("ascii", "strict").split()
        if not fields or fields[0] != rev:
            raise GitObjectError("commit identity mismatch")
        parents = tuple(fields[1:])
        if not all(SHA.fullmatch(parent) for parent in parents):
            raise GitObjectError("commit parent identity is invalid")
        tree = self._run("rev-parse", f"{rev}^{{tree}}").stdout.decode("ascii", "strict").strip()
        if SHA.fullmatch(tree) is None:
            raise GitObjectError("commit tree identity is invalid")
        return Commit(sha=rev, tree=tree, parents=parents)

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        result = self._run("merge-base", "--is-ancestor", ancestor, descendant, check=False)
        if result.returncode not in (0, 1):
            raise GitObjectError("ancestry check failed")
        return result.returncode == 0

    def merge_base(self, left: str, right: str) -> str | None:
        result = self._run("merge-base", left, right, check=False)
        if result.returncode != 0:
            return None
        sha = result.stdout.decode("ascii", "strict").strip()
        return sha if SHA.fullmatch(sha) else None

    def diff(self, base: str, head: str) -> list[DiffEntry]:
        raw = self._run("diff-tree", "-r", "-z", "-M", "--raw", "--no-commit-id",
                        "--no-abbrev", "--no-ext-diff", "--no-textconv",
                        base, head).stdout
        entries: list[DiffEntry] = []
        tokens = raw.split(b"\0")
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if not token.strip():
                index += 1
                continue
            token = token.lstrip(b"\r\n")
            if not token.startswith(b":"):
                raise GitObjectError("unexpected diff record")
            try:
                old_mode, new_mode, old_blob, new_blob, status = token[1:].decode("ascii").split(" ")
            except ValueError as exc:
                raise GitObjectError("malformed diff header") from exc
            code = status[0]
            score = int(status[1:]) if len(status) > 1 and status[1:].isdigit() else None
            index += 1
            if index > len(tokens):
                raise GitObjectError("truncated diff record")
            if code in ("R", "C"):
                if index + 1 >= len(tokens):
                    raise GitObjectError("truncated rename record")
                old_path = tokens[index].decode("utf-8", "strict")
                new_path = tokens[index + 1].decode("utf-8", "strict")
                index += 2
            else:
                path = tokens[index].decode("utf-8", "strict")
                index += 1
                if code == "D":
                    old_path, new_path = path, None
                else:
                    old_path, new_path = None, path
            if code not in ("A", "M", "D", "R", "C", "T", "U"):
                raise GitObjectError("unsupported diff status")
            entries.append(DiffEntry(
                status=code, old_path=old_path if code != "A" else None,
                new_path=new_path if code != "D" else None,
                old_mode=old_mode, new_mode=new_mode,
                old_blob=None if old_blob.startswith("000000") else old_blob,
                new_blob=None if new_blob.startswith("000000") else new_blob,
                score=score,
            ))
        return sorted(entries, key=lambda e: (e.path, e.status))

    def blob_id(self, commit: str, path: str) -> str | None:
        """Return the regular-file blob at ``path`` in ``commit``, else None.

        Uses a literal pathspec so a path containing revision syntax characters
        cannot be reinterpreted as a revision expression.
        """
        if not isinstance(path, str) or not path or path.startswith("/") or "\0" in path:
            raise GitObjectError("invalid repository path")
        result = self._run("ls-tree", "-z", "--full-tree", commit, "--",
                           f":(literal){path}", check=False)
        if result.returncode != 0:
            return None
        records = [record for record in result.stdout.split(b"\0") if record.strip()]
        if len(records) != 1:
            return None
        try:
            header, observed = records[0].split(b"\t", 1)
            mode, kind, sha = header.decode("ascii").split(" ")
            observed_path = observed.decode("utf-8", "strict")
        except (ValueError, UnicodeError) as exc:
            raise GitObjectError("malformed tree record") from exc
        if observed_path != path or kind != "blob" or not mode.startswith("100"):
            return None
        return sha if SHA.fullmatch(sha) else None

    def blob_bytes(self, blob: str) -> bytes:
        if not isinstance(blob, str) or SHA.fullmatch(blob) is None:
            raise GitObjectError("blob identity is invalid")
        result = self._run("cat-file", "blob", blob, cap=MAX_BLOB_BYTES)
        return result.stdout

    def blob_sha256(self, blob: str | None) -> tuple[str | None, int | None]:
        if blob is None:
            return None, None
        data = self.blob_bytes(blob)
        return hashlib.sha256(data).hexdigest(), len(data)
