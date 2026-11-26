#!/usr/bin/env python3
"""Explicit, read-only verification or verified download of the pinned Ario release.

Run only from a trusted copy of this launcher and R1.4. No archive is executed,
extracted or restored. This checks release assets, not an entire Git checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
VERIFIER = ROOT / 'experiments/github-release-crosscheck-r14/candidate/ario_github_crosscheck_v0_4.py'
VERIFIER_SHA = 'fac354c46e8fc8ce68edf6202980aa974ab3f0319cfe0e8272b5c688330b432b'
PUBLICATION = '4731c912ba4b34b302843dd37067822ffb699ba7'
SOURCE = '05ba5c960aaea96fc6bb80504b53b4d47e7d42f5'
PIN = '33df4395bffc0ab261af333d84e48b080fdff3d10852de2522bc61e19515ae6f'
RELEASE = 'releases/ai-readable-full-2026-11-11-05ba5c9'
HOST = 'raw.githubusercontent.com'
ASSETS = {
    'ario-full.zip': (6524694, 'd11269dc593f9cbb70e7d622a8acc31d0fe36d292a935225aca6b8f98d5c5d51'),
    'ario-full.txt': (17751878, '86aafca0e20fb356bdee14c05815d017b3212ef68afed8757fa16f1a1b746af6'),
    'ario-manifest.json': (63205, 'f86fb10ef3eb71dd6e3c348b3f0c9b42c88b3837ae889918c33d8f5d62fe11d8'),
}


class Unknown(Exception):
    pass


class Rejected(Exception):
    pass


def pinned_verifier() -> bytes:
    try:
        with VERIFIER.open('rb') as f:
            data = f.read(65537)
    except OSError as exc:
        raise Unknown('R1.4 verifier unavailable') from exc
    if len(data) > 65536 or hashlib.sha256(data).hexdigest() != VERIFIER_SHA:
        raise Rejected('R1.4 verifier bytes differ from reviewed pin')
    return data


def download_asset(asset: str, path: Path) -> None:
    """Download an allowlisted asset only; success here is NOT verification."""
    size, _ = ASSETS[asset]
    target = f'/SepehrGhanbari/Ario/{PUBLICATION}/{RELEASE}/{asset}'
    try:
        conn = http.client.HTTPSConnection(HOST, timeout=20, context=ssl.create_default_context())
        try:
            conn.request('GET', target, headers={'Accept-Encoding': 'identity', 'Connection': 'close', 'User-Agent': 'ario-verified-release/0.1'})
            with conn.getresponse() as response:
                if response.status != 200:
                    raise Unknown(f'download HTTP {response.status}')
                codings = response.headers.get_all('Content-Encoding', [])
                if codings and [v.strip(' \t').lower() for v in codings] != ['identity']:
                    raise Unknown('unsupported download content coding')
                lengths = response.headers.get_all('Content-Length', [])
                encodings = response.headers.get_all('Transfer-Encoding', [])
                if lengths:
                    # Narrowly support one canonical decimal length; do not guess
                    # about ambiguous framing or rely on connection EOF.
                    val = lengths[0].strip(' \t')
                    if (len(lengths) != 1 or encodings or len(val) > 12 or
                            re.fullmatch(r'[0-9]+', val) is None or int(val) != size or
                            response.chunked or response.length != size):
                        raise Unknown('unexpected download length/framing')
                elif ([v.strip(' \t').lower() for v in encodings] != ['chunked'] or
                      response.chunked is not True):
                    raise Unknown('unsupported download framing')
                with path.open('xb') as out:
                    remaining = size
                    while remaining:
                        block = response.read(min(1024 * 1024, remaining))
                        if not block or len(block) > remaining:
                            raise Unknown('incomplete download')
                        out.write(block)
                        remaining -= len(block)
                    if response.chunked and response.read(1):
                        raise Unknown('oversized download')
                    if not response.chunked and response.length not in (0,):
                        raise Unknown('incomplete fixed-length download')
        finally:
            conn.close()
    except (OSError, http.client.HTTPException, ValueError) as exc:
        raise Unknown('download unavailable over HTTPS') from exc


def verify_asset(verifier: Path, asset: str, path: Path) -> dict:
    try:
        proc = subprocess.run([sys.executable, '-I', '-B', str(verifier), '--file', str(path), '--asset', asset], capture_output=True, timeout=90, check=False)
        result = json.loads(proc.stdout)
        if not isinstance(result, dict):
            raise ValueError('not a JSON object')
    except (OSError, subprocess.TimeoutExpired, ValueError, UnicodeError) as exc:
        raise Unknown('R1.4 did not return a usable result') from exc
    if proc.returncode == 2 and result.get('exit_code') == 2 and result.get('status') == 'REJECTED':
        raise Rejected(str(result.get('reason', 'R1.4 rejected')))
    if proc.returncode == 3 and result.get('exit_code') == 3 and result.get('status') == 'UNKNOWN':
        raise Unknown(str(result.get('reason', 'R1.4 unknown')))
    size, sha = ASSETS[asset]
    required = {'status': 'GITHUB_RELEASE_BYTES_MATCH', 'reference_transport': 'HTTPS_GITHUB', 'exit_code': 0,
                'repository': 'https://github.com/SepehrGhanbari/Ario', 'publication_commit': PUBLICATION,
                'source_commit': SOURCE, 'checksums_sha256': PIN, 'asset': asset, 'size_bytes': size, 'sha256': sha}
    if proc.returncode != 0 or any(result.get(k) != v for k, v in required.items()):
        raise Unknown('R1.4 result does not establish the required exact live match')
    return result


def run(mode: str, directory: Path, selected: tuple[str, ...]) -> tuple[int, dict]:
    report = {'status': 'UNKNOWN', 'mode': mode, 'results': [], 'scope': 'PINNED_204_FILE_RELEASE_ASSETS_ONLY',
              'qualification': 'Not whole-clone verification, independent publisher identity, DOI equivalence, or permission to execute. Results describe the bytes read.'}
    created = None
    accepted = False
    try:
        source = pinned_verifier()
        if mode == 'download':
            # A fresh directory, never overwrite existing user files. It is only
            # advertised as accepted when every selected asset passes R1.4.
            created = Path(tempfile.mkdtemp(prefix='ario-release-', dir=directory))
            directory = created
        with tempfile.TemporaryDirectory(prefix='ario-r14-pinned-') as scratch:
            verifier = Path(scratch) / 'verifier.py'
            verifier.write_bytes(source)
            for asset in selected:
                try:
                    path = directory / asset
                    if mode == 'download':
                        download_asset(asset, path)
                    result = verify_asset(verifier, asset, path)
                    report['results'].append({'asset': asset, 'status': result['status'], 'sha256': result['sha256'], 'reference_transport': result['reference_transport']})
                except (Rejected, Unknown) as exc:
                    report['results'].append({'asset': asset, 'status': 'REJECTED' if isinstance(exc, Rejected) else 'UNKNOWN', 'reason': str(exc)})
                    if mode == 'download':
                        break
        states = [r['status'] for r in report['results']]
        if 'REJECTED' in states:
            report['status'] = 'REJECTED'
            return 2, report
        if len(states) != len(selected) or any(s != 'GITHUB_RELEASE_BYTES_MATCH' for s in states):
            return 3, report
        accepted = True
        report['status'] = 'ALL_SELECTED_RELEASE_ASSETS_MATCH'
        report['directory'] = str(directory)
        return 0, report
    except Rejected as exc:
        report.update(status='REJECTED', reason=str(exc))
        return 2, report
    except (Unknown, OSError) as exc:
        report['reason'] = str(exc)
        return 3, report
    finally:
        if created is not None and not accepted:
            # Only the fresh directory created by this invocation is disposable.
            try:
                shutil.rmtree(created)
            except OSError:
                report['unaccepted_directory'] = str(created)
                report['cleanup'] = 'FAILED; do not use these files'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', nargs='?', choices=['check', 'download'], default='check')
    parser.add_argument('--directory', type=Path, help='Existing directory of assets (check) or existing output parent (download)')
    parser.add_argument('--asset', choices=tuple(ASSETS), action='append', help='Repeat to select assets; default checks all three')
    args = parser.parse_args(argv)
    selected = tuple(dict.fromkeys(args.asset or ASSETS))
    directory = (args.directory if args.directory is not None else (ROOT / RELEASE if args.mode == 'check' else Path.cwd())).resolve()
    code, report = run(args.mode, directory, selected)
    report['exit_code'] = code
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
