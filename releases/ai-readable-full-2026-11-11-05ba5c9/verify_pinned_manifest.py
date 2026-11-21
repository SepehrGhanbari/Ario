#!/usr/bin/env python3
"""Read-only, independently parsed TXT-to-manifest verification with an EXTERNAL pin.

The expected SHA-256 MUST come from a trusted channel outside the files being
checked. A match alone does not establish who published that pin.
"""
import argparse
import base64
import binascii
import hashlib
import json
import os
import pathlib
import re
import stat

FMT = b"ARIO_FULL_TEXT_EXPORT_V1\n"
HEADER_LINE_LIMIT = 4096
HEADER_TOTAL_LIMIT = 16384
RECORD_LINE_LIMIT = 65536
MANIFEST_LIMIT = 8 * 1024 * 1024
INPUT_LIMIT = 384 * 1024 * 1024
PER_RECORD_RAW_LIMIT = 64 * 1024 * 1024
PER_RECORD_PAYLOAD_LIMIT = 90 * 1024 * 1024
PATH_LIMIT = 4096
PATH_COMPONENT_LIMIT = 255
PATH_DEPTH_LIMIT = 128
PATH_INDEX_ENTRY_LIMIT = 100000
PATH_INDEX_BYTE_LIMIT = 8 * 1024 * 1024
COUNT_LIMIT = 10000
TOTAL_LIMIT = 256 * 1024 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
FOOT = re.compile(rb"@@ARIO_COMPLETE files=(\d+) commit=([0-9a-f]{40}) tree=([0-9a-f]{40}) tracked_bytes=(\d+) manifest_sha256=([0-9a-f]{64})\n")

RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
            "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10))}


def portable_key(value):
    import unicodedata
    return unicodedata.normalize("NFC", value.casefold())


def validate_manifest_path(value):
    require(isinstance(value, str) and bool(value), "invalid manifest path")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise VerificationError("invalid manifest path encoding") from exc
    require(len(encoded) <= PATH_LIMIT and chr(92) not in value and chr(0) not in value,
            "manifest path length or separator")
    posix = pathlib.PurePosixPath(value)
    windows = pathlib.PureWindowsPath(value)
    require(len(posix.parts) <= PATH_DEPTH_LIMIT, "manifest path depth limit")
    require(bool(posix.parts) and posix.as_posix() == value
            and not posix.is_absolute() and not windows.drive
            and not windows.root and not windows.is_absolute()
            and ".." not in posix.parts, "unsafe or non-canonical manifest path")
    for part in posix.parts:
        require(len(part.encode("utf-8")) <= PATH_COMPONENT_LIMIT,
                "manifest path component byte limit")
        device_base = part.split(".", 1)[0].rstrip(" ").upper()
        require(part not in ("", ".", "..") and not part.endswith((".", " "))
                and ":" not in part
                and not any(ord(ch) < 32 or ch in '<>\"|?*' for ch in part)
                and device_base not in RESERVED,
                "non-portable manifest path")
    return posix


class VerificationError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise VerificationError(reason)


def unique_object(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, "duplicate JSON key")
        result[k] = v
    return result


def compact_base64(payload):
    """Remove only ASCII Base64 whitespace without per-token allocations."""
    return payload.translate(None, b" \t\r\n\v\f")


def reject_constant(_token):
    raise VerificationError("non-standard JSON number")


def strict_json(data):
    try:
        return json.loads(data, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise VerificationError("invalid JSON") from exc


def bounded_int(value, max_value, name):
    require(type(value) is int and 0 <= value <= max_value, "invalid " + name)
    return value


def decimal_header(value, max_value, name):
    require(isinstance(value, str) and len(value) <= len(str(max_value))
            and bool(re.fullmatch(r"[0-9]+", value)), "invalid " + name)
    number = int(value)
    return bounded_int(number, max_value, name)


def read_manifest(path, expected_sha256):
    require(isinstance(expected_sha256, str) and bool(HEX64.fullmatch(expected_sha256)),
            "explicit external SHA-256 pin required")
    with open(path, "rb") as f:
        require(stat.S_ISREG(os.fstat(f.fileno()).st_mode), "manifest must be a regular file")
        raw = f.read(MANIFEST_LIMIT + 1)
    require(len(raw) <= MANIFEST_LIMIT, "manifest byte limit")
    actual = hashlib.sha256(raw).hexdigest()
    require(actual == expected_sha256, "EXTERNAL_MANIFEST_PIN_MISMATCH")
    try:
        manifest_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError("manifest is not valid UTF-8") from exc
    manifest = strict_json(manifest_text)
    require(isinstance(manifest, dict), "manifest object expected")
    require(manifest.get("format") == "ARIO_FULL_SNAPSHOT_v1", "manifest format mismatch")
    require(isinstance(manifest.get("source_repo"), str) and manifest["source_repo"].startswith("https://"), "manifest source_repo")
    require(isinstance(manifest.get("commit"), str) and HEX40.fullmatch(manifest["commit"]), "manifest commit")
    require(isinstance(manifest.get("tree"), str) and HEX40.fullmatch(manifest["tree"]), "manifest tree")
    items = manifest.get("files")
    require(isinstance(items, list) and len(items) <= COUNT_LIMIT, "invalid manifest file list")
    count = bounded_int(manifest.get("tracked_files"), COUNT_LIMIT, "tracked_files")
    total = bounded_int(manifest.get("tracked_bytes"), TOTAL_LIMIT, "tracked_bytes")
    require(len(items) == count, "manifest record count mismatch")
    require(sum(bounded_int(x.get("bytes") if isinstance(x, dict) else None,
                            PER_RECORD_RAW_LIMIT, "manifest file bytes") for x in items) == total,
            "manifest byte sum mismatch")
    seen = set()
    all_parents = set()
    folded_components = {}
    path_index_entries = 0
    path_index_bytes = 0
    for item in items:
        path_value = item.get("path")
        path_obj = validate_manifest_path(path_value)
        key = portable_key(path_value)
        require(key not in seen and key not in all_parents,
                "duplicate, case-colliding, or file/directory-conflicting manifest path")
        parts = path_obj.parts
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            folded = portable_key(prefix)
            if index < len(parts):
                require(folded not in seen, "file/directory-conflicting manifest path")
            previous = folded_components.get(folded)
            if previous is None:
                added = len(folded.encode("utf-8")) + len(prefix.encode("utf-8"))
                require(path_index_entries < PATH_INDEX_ENTRY_LIMIT
                        and path_index_bytes + added <= PATH_INDEX_BYTE_LIMIT,
                        "manifest path index resource limit")
                folded_components[folded] = prefix
                path_index_entries += 1
                path_index_bytes += added
            else:
                require(previous == prefix, "case/Unicode-colliding manifest path component")
            if index < len(parts):
                all_parents.add(folded)
        seen.add(key)
        require(item.get("mode") in ("100644", "100755", "120000"),
                "invalid manifest mode")
        require(item.get("encoding") in ("raw-utf8", "base64"), "invalid manifest encoding")
        require(isinstance(item.get("sha256"), str) and HEX64.fullmatch(item["sha256"]),
                "invalid manifest SHA-256")
        require(isinstance(item.get("git_blob_sha1"), str) and HEX40.fullmatch(item["git_blob_sha1"]),
                "invalid manifest Git blob hash")
    require(manifest.get("text_files") is None or
            bounded_int(manifest["text_files"], COUNT_LIMIT, "text_files") == sum(x["encoding"] == "raw-utf8" for x in items),
            "manifest text count mismatch")
    require(manifest.get("binary_files") is None or
            bounded_int(manifest["binary_files"], COUNT_LIMIT, "binary_files") == sum(x["encoding"] == "base64" for x in items),
            "manifest binary count mismatch")
    return manifest, actual


def read_headers(f):
    require(f.readline(HEADER_LINE_LIMIT + 1) == FMT, "invalid format line")
    h = {}
    nbytes = len(FMT)
    while True:
        line = f.readline(HEADER_LINE_LIMIT + 1)
        nbytes += len(line)
        require(line and len(line) <= HEADER_LINE_LIMIT and nbytes <= HEADER_TOTAL_LIMIT,
                "oversized or missing header")
        if line == b"@@ARIO_BEGIN\n":
            break
        try:
            text = line.decode("ascii").rstrip("\r\n")
        except UnicodeDecodeError as exc:
            raise VerificationError("non-ASCII header") from exc
        if "=" in text:
            key, val = text.split("=", 1)
            require(key not in h, "duplicate header key")
            h[key] = val
    return h


def verify(txt_path, manifest_path, expected_manifest_sha256):
    manifest, pinned_hash = read_manifest(manifest_path, expected_manifest_sha256)
    with open(txt_path, "rb") as f:
        info = os.fstat(f.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= INPUT_LIMIT,
                "TXT type or byte limit")
        hdr = read_headers(f)
        require(hdr.get("repo") == manifest.get("source_repo"), "TXT repo/manifest mismatch")
        require(hdr.get("manifest_sha256") == pinned_hash,
                "TXT_MANIFEST_PIN_MISMATCH")
        require(hdr.get("commit") == manifest["commit"]
                and hdr.get("tree") == manifest["tree"], "TXT source identity mismatch")
        count = decimal_header(hdr.get("tracked_files"), COUNT_LIMIT, "TXT file count")
        total = decimal_header(hdr.get("tracked_bytes"), TOTAL_LIMIT, "TXT byte count")
        require(count == manifest["tracked_files"] and total == manifest["tracked_bytes"],
                "TXT header/manifest count mismatch")
        consumed = 0
        for item in manifest["files"]:
            line = f.readline(RECORD_LINE_LIMIT + 1)
            require(line.startswith(b"@@ARIO_FILE ") and len(line) <= RECORD_LINE_LIMIT,
                    "invalid record boundary/size")
            try:
                record_text = line[len(b"@@ARIO_FILE "):].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise VerificationError("record JSON is not valid UTF-8") from exc
            record = strict_json(record_text)
            require(isinstance(record, dict), "record object expected")
            for field in ("path", "mode", "git_blob_sha1", "sha256", "bytes", "encoding"):
                require(record.get(field) == item[field], "TXT record/manifest metadata mismatch: " + field)
            bounded_int(record.get("bytes"), PER_RECORD_RAW_LIMIT, "record raw bytes")
            length = bounded_int(record.get("payload_bytes"), PER_RECORD_PAYLOAD_LIMIT, "payload_bytes")
            require(f.tell() + length <= info.st_size, "truncated payload boundary")
            payload = f.read(length)
            require(len(payload) == length, "truncated payload")
            require(f.readline(2) == b"\n" and f.readline(64) == b"@@ARIO_END\n",
                    "invalid record terminator")
            if record["encoding"] == "raw-utf8":
                try:
                    payload.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise VerificationError("invalid raw UTF-8") from exc
                raw = payload
            else:
                try:
                    raw = base64.b64decode(compact_base64(payload), validate=True)
                except (ValueError, binascii.Error) as exc:
                    raise VerificationError("invalid Base64") from exc
            require(len(raw) == item["bytes"], "record length mismatch")
            require(hashlib.sha256(raw).hexdigest() == item["sha256"],
                    "record SHA-256 mismatch")
            git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            require(git_blob == item["git_blob_sha1"], "record Git blob mismatch")
            consumed += len(raw)
        foot = f.readline(513)
        match = FOOT.fullmatch(foot)
        require(match is not None, "missing or malformed footer")
        fcount, fcommit, ftree, fbytes, fhash = match.groups()
        require(int(fcount) == count and fcommit.decode() == manifest["commit"]
                and ftree.decode() == manifest["tree"] and int(fbytes) == consumed == total
                and fhash.decode() == pinned_hash, "footer/manifest mismatch")
        require(not f.read(1), "trailing TXT bytes")
    return {"files": count, "bytes": consumed, "manifest_sha256": pinned_hash,
            "scope": "PINNED_MANIFEST_AND_SOURCE_BYTES_MATCH; PIN_CUSTODY_NOT_VERIFIED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--txt", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True,
                        help="An independently obtained trusted pin, NEVER copied from the untrusted input")
    args = parser.parse_args()
    try:
        result = verify(args.txt, args.manifest, args.expected_manifest_sha256)
    except (VerificationError, OSError) as exc:
        parser.exit(2, "PINNED_MANIFEST_REJECTED: " + str(exc) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
