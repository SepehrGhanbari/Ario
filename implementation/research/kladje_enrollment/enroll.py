"""Ario Kladje research enrollment only. No witness requests or production keys."""
import argparse
import base64
import getpass
import hashlib
import os
from pathlib import Path
import urllib.request
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ORIGIN = 'github.com/SepehrGhanbari/Ario/kladje-test-v1'
LIST_URL = 'https://testing.witness-network.org/log-list.1'
DEFAULT = Path.home() / 'Ario-Kladje-Research-v1'


def vkey(origin, public):
    if len(public) != 32 or not origin or any(c.isspace() or c == '+' for c in origin):
        raise ValueError('invalid origin/public key')
    payload = b'\x01' + public
    kid = hashlib.sha256(origin.encode('ascii') + b'\n' + payload).hexdigest()[:8]
    return origin + '+' + kid + '+' + base64.b64encode(payload).decode('ascii')


def public_vkey(key):
    return vkey(ORIGIN, key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def create_identity(path, password):
    if len(password) < 12:
        raise ValueError('passphrase must contain at least 12 bytes')
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.BestAvailableEncryption(password))
    with os.fdopen(os.open(path / 'research-log.private.pem', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f:
        f.write(pem)
        f.flush()
        os.fsync(f.fileno())
    return public_vkey(key)


def load_vkey(path, password):
    key = serialization.load_pem_private_key((path / 'research-log.private.pem').read_bytes(), password)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('wrong key type')
    return public_vkey(key)


def enrolled(raw, expected):
    lines = raw.decode('utf-8', errors='strict').splitlines()
    relevant = [x.strip() for x in lines if x.strip() and not x.lstrip().startswith('#')]
    if not relevant or relevant[0] != 'logs/v0':
        raise ValueError('unknown list format')
    candidates = [x[5:] for x in relevant[1:] if x.startswith('vkey ') and x[5:].split('+', 1)[0] == ORIGIN]
    return candidates == [expected]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect refused')


def fetch_list():
    req = urllib.request.Request(LIST_URL, headers={'Cache-Control': 'no-cache', 'User-Agent': 'Ario-research-enrollment/1'})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('list too large')
    return raw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['init', 'show', 'check'])
    p.add_argument('--state-dir', type=Path, default=DEFAULT)
    a = p.parse_args()
    try:
        if a.action == 'init' and a.state_dir.exists():
            raise ValueError('identity already exists; use show, never replace')
        pw = getpass.getpass('Research key passphrase (not sent or printed): ').encode('utf-8')
        if a.action == 'init':
            if pw != getpass.getpass('Confirm passphrase: ').encode('utf-8'):
                raise ValueError('passphrases differ')
            key = create_identity(a.state_dir, pw)
        else:
            key = load_vkey(a.state_dir, pw)
        if a.action == 'check':
            ok = enrolled(fetch_list(), key)
            print('ENROLLED' if ok else 'NOT_ENROLLED_OR_KEY_CONFLICT')
            return 0 if ok else 2
        print('origin:', ORIGIN)
        print('vkey:', key)
        print('qpd: 24\nlist: testing\nContact: choose a public project contact yourself.')
        print('No registration submitted. Keep the encrypted private PEM and its passphrase offline.')
        return 0
    except (OSError, ValueError, TypeError) as e:
        print('HOLD:', type(e).__name__, str(e))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
