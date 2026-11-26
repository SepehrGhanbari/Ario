#!/usr/bin/env python3
"""ARIA research-only GitHub release byte cross-check (no restore / execution).

Trust statement: this verifies a local file against the checksum registry at a
fixed release-publishing GitHub commit over validated HTTPS. It does NOT certify
the GitHub operator, the publisher's personal identity, the truth of file contents,
or the independence of a Zenodo/DOI record. Distribute this verifier separately
from the untrusted archive, or verify the verifier itself before relying on it.

Python >= 3.10; stdlib only.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import hmac
import http.client
import math
import json
import os
from pathlib import Path
import re
import ssl
import stat
import sys
import urllib.error
import urllib.request

REPO = "SepehrGhanbari/Ario"
OFFICIAL_REPO = f"https://github.com/{REPO}"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
MAX_REFERENCE_BYTES = 64 * 1024
MAX_LOCAL_BYTES = 384 * 1024 * 1024
BLOCK_SIZE = 1024 * 1024

# Project bibliographic links indexed in the official root README at
# main commit 4eeea66c83e3ee8b2cc901d9ae61df22140ff6b5.
# They are reference links only, NOT attestations of the 204-file archive.
PROJECT_DOIS = (
    "10.5281/zenodo.23259916", "10.5281/zenodo.23326995",
    "10.5281/zenodo.23375350", "10.5281/zenodo.23375401",
    "10.5281/zenodo.23376521", "10.5281/zenodo.23376577",
    "10.5281/zenodo.23441596", "10.5281/zenodo.23600820",
    "10.5281/zenodo.23651704", "10.5281/zenodo.23771218",
    "10.5281/zenodo.24041161", "10.5281/zenodo.24054535",
    "10.5281/zenodo.24136175", "10.5281/zenodo.24230572",
    "10.5281/zenodo.24343618",
)


@dataclass(frozen=True)
class Release:
    name: str
    publication_commit: str  # package + checksums.json first committed here
    source_commit: str       # earlier source-tree snapshot, not publishing commit
    source_tree: str
    checksums_path: str
    checksums_sha256: str     # independently pinned by this verifier's distribution
    assets: tuple[str, ...]


RELEASE = Release(
    name="ario-204-2026-11-11",
    publication_commit="4731c912ba4b34b302843dd37067822ffb699ba7",
    source_commit="05ba5c960aaea96fc6bb80504b53b4d47e7d42f5",
    source_tree="8a9429d396c09fe17682a61dd91cb43672d3cb79",
    checksums_path="releases/ai-readable-full-2026-11-11-05ba5c9/checksums.json",
    checksums_sha256="33df4395bffc0ab261af333d84e48b080fdff3d10852de2522bc61e19515ae6f",
    assets=("ario-full.zip", "ario-full.txt", "ario-manifest.json"),
)


class ReferenceUnknown(Exception):
    """External source could not be evaluated; never claim match or mismatch."""


class VerificationRejected(Exception):
    """Observed bytes or supplied inputs violate the pinned release contract."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def url_for(config: Release) -> str:
    # User input never selects an arbitrary host or remote path.
    if not isinstance(config.publication_commit, str) or not HEX40.fullmatch(config.publication_commit):
        raise VerificationRejected("invalid publication commit")
    path = config.checksums_path
    if (not isinstance(path, str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", path)
            or any(segment in (".", "..") for segment in path.split("/"))):
        raise VerificationRejected("invalid checksums path")
    return (
        f"https://raw.githubusercontent.com/{REPO}/"
        f"{config.publication_commit}/{config.checksums_path}"
    )


def reference_framing(headers) -> tuple[int | None, bool]:
    """Return a bounded length and whether a standard chunked body is present."""
    lengths = headers.get_all("Content-Length", [])
    encodings = headers.get_all("Transfer-Encoding", [])
    if encodings:
        if lengths or [value.strip().lower() for value in encodings] != ["chunked"]:
            raise ReferenceUnknown("unsupported or ambiguous HTTP framing")
        return None, True
    if not lengths:
        return None, False
    # RFC 9112 permits repeated decimal values only when they agree.
    values = [value.strip(" \t") for field in lengths for value in field.split(",")]
    if any(re.fullmatch(r"[0-9]+", value) is None for value in values):
        raise ReferenceUnknown("invalid HTTP Content-Length")
    normalized = {value.lstrip("0") or "0" for value in values}
    if len(normalized) != 1:
        raise ReferenceUnknown("conflicting HTTP Content-Length values")
    value = normalized.pop()
    if len(value) > len(str(MAX_REFERENCE_BYTES)) or int(value) > MAX_REFERENCE_BYTES:
        raise ReferenceUnknown("oversized official checksum response")
    return int(value), False


def _decoder_framing_state(response) -> tuple[bool | None, int | None]:
    """Inspect the *actual* stdlib HTTP decoder, not only normalized headers.

    urllib's addinfourl wraps an HTTPResponse in .fp. Tests that directly use
    HTTPResponse have .chunked on the top-level object instead. An unknown
    decoder state is not affirmative evidence of decoded chunked framing.
    """
    decoder = response
    if type(getattr(decoder, "chunked", None)) is not bool:
        decoder = getattr(response, "fp", None)
    flag = getattr(decoder, "chunked", None)
    length = getattr(decoder, "length", None)
    return (flag if type(flag) is bool else None,
            length if type(length) is int else None)


class _ReferenceHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, context):
        super().__init__(context=context)
        self.context = context
        self.validated_session = False

    def https_open(self, request):
        handler = self

        class ReferenceConnection(http.client.HTTPSConnection):
            def connect(self):
                super().connect()
                handler.validated_session = (
                    self.host == "raw.githubusercontent.com"
                    and handler.context.check_hostname
                    and handler.context.verify_mode == ssl.CERT_REQUIRED
                    and isinstance(self.sock, ssl.SSLSocket)
                    and bool(self.sock.getpeercert())
                )

        return self.do_open(ReferenceConnection, request, context=self.context)


def _retrieve_reference(config: Release) -> tuple[bytes, bool]:
    url = url_for(config)
    # Disable environment proxy reliance and all HTTP redirects. The standard
    # HTTPS stack still validates the certificate chain/hostname.
    try:
        https = _ReferenceHTTPSHandler(ssl.create_default_context())
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            https,
            NoRedirect(),
        )
        # The registry pin covers the identity representation. Do not hash
        # compressed wire bytes as though they were the registry itself.
        request = urllib.request.Request(url, headers={
            "User-Agent": "ario-byte-crosscheck/0.1", "Accept-Encoding": "identity",
        })
        with opener.open(request, timeout=15) as response:
            if response.status != 200 or response.geturl() != url:
                raise ReferenceUnknown("unexpected GitHub response or redirect")
            codings = response.headers.get_all("Content-Encoding", [])
            if codings and [value.strip(" \t").lower() for value in codings] != ["identity"]:
                raise ReferenceUnknown("unsupported HTTP Content-Encoding; identity required")
            declared, chunked = reference_framing(response.headers)
            decoder_chunked, decoder_length = _decoder_framing_state(response)
            # The HTTP library may parse optional trailing whitespace differently
            # from header normalization. Never hash a wire-encoded chunk body as
            # though it were the decoded checksum registry.
            if chunked and decoder_chunked is not True:
                raise ReferenceUnknown("HTTP chunked decoder/header disagreement")
            if decoder_chunked is True and not chunked:
                raise ReferenceUnknown("HTTP decoder/header framing disagreement")
            if declared is not None and decoder_length is not None and decoder_length != declared:
                raise ReferenceUnknown("HTTP Content-Length decoder/header disagreement")
            # A validated fixed-length message ends at its declared boundary,
            # not at connection EOF. CPython may leave .length unset for a
            # comma-list of identical lengths; reading past that boundary can
            # otherwise block on a persistent connection. Keep the bounded
            # max+1 probe only for chunked or close-delimited bodies.
            data = response.read(declared if declared is not None else MAX_REFERENCE_BYTES + 1)
            if len(data) > MAX_REFERENCE_BYTES:
                raise ReferenceUnknown("oversized official checksum response")
            # CPython HTTPResponse.read(n) may return normally after premature
            # EOF while its declared Content-Length still has outstanding bytes.
            # The incomplete remote response is UNKNOWN, not evidence of an
            # incorrect local file or a changed pinned GitHub registry.
            outstanding = getattr(response, "length", None)
            if type(outstanding) is int and outstanding > 0:
                raise ReferenceUnknown("truncated GitHub reference HTTP body")
            if declared is not None and len(data) != declared:
                raise ReferenceUnknown("truncated GitHub reference HTTP body")
            if declared is None and not chunked and hashlib.sha256(data).hexdigest() != config.checksums_sha256:
                raise ReferenceUnknown("cannot establish completeness of close-delimited registry")
            return data, https.validated_session
    except (OSError, urllib.error.URLError, http.client.HTTPException, ValueError) as exc:
        raise ReferenceUnknown("GitHub reference unavailable over validated HTTPS") from exc


def fetch_official_reference(config: Release) -> bytes:
    """Fetch bytes via the checked TLS path; parsing/pin comparison is separate."""
    data, validated = _retrieve_reference(config)
    if not validated:
        raise ReferenceUnknown("validated GitHub TLS session was not observed")
    return data


def unique_object(pairs):
    out = {}
    for key, val in pairs:
        if key in out:
            raise VerificationRejected("duplicate checksum JSON field")
        out[key] = val
    return out


def parse_reference(raw: bytes, config: Release, asset: str) -> tuple[int, str]:
    if asset not in config.assets:
        raise VerificationRejected("asset name is not in the trusted release allowlist")
    if type(raw) is not bytes:
        raise VerificationRejected("checksum reference must be bytes")
    if len(raw) > MAX_REFERENCE_BYTES:
        raise VerificationRejected("official checksum response exceeds limit")
    if (type(config.checksums_sha256) is not str
            or HEX64.fullmatch(config.checksums_sha256) is None):
        raise VerificationRejected("invalid expected checksum registry pin")
    digest = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(digest, config.checksums_sha256):
        raise VerificationRejected("OFFICIAL_REFERENCE_PIN_MISMATCH")
    def no_nonstandard(_):
        raise VerificationRejected("nonstandard JSON number")
    def bounded_int(v):
        if len(v) > 16:
            raise VerificationRejected("oversized numeric JSON literal")
        return int(v)
    def finite_float(v):
        if len(v) > 64:
            raise VerificationRejected("oversized floating-point JSON literal")
        value = float(v)
        if not math.isfinite(value):
            raise VerificationRejected("non-finite JSON number")
        return value
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                         parse_constant=no_nonstandard, parse_int=bounded_int,
                         parse_float=finite_float)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise VerificationRejected("invalid checksum JSON") from exc
    if not isinstance(doc, dict) or doc.get("commit") != config.source_commit:
        raise VerificationRejected("source commit mismatch")
    if (doc.get("git_tree") != config.source_tree
            or type(doc.get("tracked_files")) is not int or doc["tracked_files"] != 204):
        raise VerificationRejected("source tree or file count mismatch")
    item = doc.get(asset)
    if not isinstance(item, dict):
        raise VerificationRejected("asset checksum record missing")
    expected_bytes, expected_hash = item.get("bytes"), item.get("sha256")
    if type(expected_bytes) is not int or not 0 <= expected_bytes <= MAX_LOCAL_BYTES:
        raise VerificationRejected("invalid expected byte count")
    if not isinstance(expected_hash, str) or not HEX64.fullmatch(expected_hash):
        raise VerificationRejected("invalid expected SHA-256")
    return expected_bytes, expected_hash


def local_sha256(file_path: Path, expected_size: int) -> str:
    # No extraction, execution, file creation, or modifications.
    try:
        before_path = file_path.lstat()
        if not stat.S_ISREG(before_path.st_mode):
            raise VerificationRejected("refuse symlink, directory or non-regular input")
        if os.name == "nt":
            stream = file_path.open("rb")
        else:
            # O_NONBLOCK prevents an lstat-to-open FIFO swap from hanging.
            # O_NOFOLLOW prevents following a swapped leaf symlink. The opened
            # descriptor is still checked before any content is read.
            flags = (os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
                     | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
            fd = os.open(file_path, flags)
            try:
                stream = os.fdopen(fd, "rb", closefd=True)
            except BaseException:
                os.close(fd)
                raise
        with stream:
            initial = os.fstat(stream.fileno())
            if not stat.S_ISREG(initial.st_mode):
                raise VerificationRejected("input is not a regular file")
            if (initial.st_size != expected_size or initial.st_size > MAX_LOCAL_BYTES
                    or (initial.st_dev, initial.st_ino) != (before_path.st_dev, before_path.st_ino)):
                raise VerificationRejected("FILE_SIZE_OR_ID_MISMATCH")
            hashed = hashlib.sha256()
            remaining = expected_size
            while remaining:
                block = stream.read(min(BLOCK_SIZE, remaining))
                if not block:
                    raise VerificationRejected("truncated input while hashing")
                hashed.update(block)
                remaining -= len(block)
            if stream.read(1):
                raise VerificationRejected("file grew during hashing")
            final = os.fstat(stream.fileno())
            after_path = file_path.lstat()
            fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
            if any(getattr(initial, k) != getattr(final, k) for k in fields):
                raise ReferenceUnknown("input changed during hashing")
            # Windows path and handle queries can assign different meanings to ctime.
            # Keep full checks within each API; compare shared fields across the APIs.
            if any(getattr(before_path, k) != getattr(after_path, k) for k in fields):
                raise ReferenceUnknown("input path changed during hashing")
            shared = fields[:-1] if os.name == "nt" else fields
            if any(getattr(final, k) != getattr(after_path, k) for k in shared):
                raise ReferenceUnknown("input path changed during hashing")
            return hashed.hexdigest()
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError) as exc:
        raise ReferenceUnknown("local file unreadable or changed") from exc


def verify_file(path: Path, asset: str, config: Release = RELEASE,
                fetcher=None) -> dict:
    if asset not in config.assets:
        raise VerificationRejected("unrecognized release asset")
    # Ensure data at the official release's exact immutable Git reference is
    # selected without trusting metadata supplied by the downloaded file.
    live_github_fetch = fetcher is None
    if live_github_fetch and config != RELEASE:
        raise VerificationRejected("custom releases require an explicit reference provider")
    if live_github_fetch:
        ref, validated = _retrieve_reference(config)
        if not validated:
            raise ReferenceUnknown("validated GitHub TLS session was not observed")
    else:
        # A caller-supplied provider might be offline, or might fetch live HTTPS.
        # We observe only its bytes, not its transport; never assert either.
        try:
            ref = fetcher(config)
        except ReferenceUnknown:
            raise
        except Exception as exc:
            raise ReferenceUnknown("caller-supplied reference provider failed") from exc
    size, sha = parse_reference(ref, config, asset)
    observed = local_sha256(path, size)
    if not hmac.compare_digest(observed, sha):
        raise VerificationRejected("FILE_SHA256_MISMATCH")
    return {
        "status": ("GITHUB_RELEASE_BYTES_MATCH" if live_github_fetch
                   else "PINNED_REFERENCE_BYTES_MATCH_ORIGIN_UNVERIFIED"),
        "reference_transport": ("HTTPS_GITHUB" if live_github_fetch
                                else "CALLER_SUPPLIED_TRANSPORT_UNVERIFIED"),
        "repository": OFFICIAL_REPO,
        "publication_commit": config.publication_commit,
        "source_commit": config.source_commit,
        "asset": asset,
        "size_bytes": size,
        "sha256": sha,
        "checksums_sha256": config.checksums_sha256,
        "project_doi_reference_index": ["https://doi.org/" + doi for doi in PROJECT_DOIS],
        "doi_reference_scope": "PROJECT_BIBLIOGRAPHY_ONLY_NOT_SAME_FILE_ATTESTATION",
        "qualification": (
            "Exact local bytes match the verifier's pinned checksum registry. "
            + ("The registry was retrieved from fixed GitHub HTTPS. " if live_github_fetch
               else "Reference bytes were caller-supplied; whether GitHub was queried is unverified. ")
            + "Publisher identity beyond trusted GitHub origin, source independence, "
            "and truth of content are NOT established."
        ),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, required=True, help="untrusted local file (read-only)")
    ap.add_argument("--asset", choices=RELEASE.assets, required=True,
                    help="declared asset identity; local file may be renamed")
    args = ap.parse_args(argv)
    try:
        result = verify_file(args.file, args.asset)
        result["exit_code"] = 0
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except VerificationRejected as exc:
        print(json.dumps({"status": "REJECTED", "reason": str(exc), "exit_code": 2},
                         sort_keys=True))
        return 2
    except ReferenceUnknown as exc:
        print(json.dumps({"status": "UNKNOWN", "reason": str(exc), "exit_code": 3},
                         sort_keys=True))
        return 3


if __name__ == "__main__":
    sys.exit(main())
