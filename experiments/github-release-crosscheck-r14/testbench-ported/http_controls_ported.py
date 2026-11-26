"""Offline HTTP conformance controls. The opener and HTTP parser are genuine.
Only HTTPSConnection.connect is replaced with an in-memory response. No network or TLS."""
import http.client
import io
import os
import ssl
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / sys.argv[1]))
import ario_github_crosscheck_v0_2 as v


class MemorySocket:
    def __init__(self, record):
        self.record = record

    def makefile(self, *args, **kwargs):
        return io.BytesIO(self.record)

    def sendall(self, data):
        pass

    def close(self):
        pass


def record(status='200 OK', headers=(), body=b'abc'):
    start = ('HTTP/1.1 ' + status).encode() + b'\r\n'
    lines = b''.join(s.encode() + b'\r\n' for s in headers)
    return start + lines + b'\r\n' + body


def check(name, packet, expected):
    attempts = []

    def connect(conn):
        attempts.append((conn.host, conn.port, conn._context.check_hostname,
                         conn._context.verify_mode))
        if len(attempts) != 1:
            raise AssertionError('unexpected extra connection')
        conn.sock = MemorySocket(packet)

    env = {'https_proxy': 'http://proxy.invalid:9999', 'HTTPS_PROXY': 'http://proxy.invalid:9999',
           'no_proxy': '', 'NO_PROXY': ''}
    with patch.dict(os.environ, env), patch.object(http.client.HTTPSConnection, 'connect', connect):
        try:
            raw, validated_tls = v._retrieve_reference(v.RELEASE)
            assert validated_tls is False  # Offline socket transport was synthetic.
            result = 'BODY ' + str(len(raw))
        except v.ReferenceUnknown:
            result = 'UNKNOWN'
    assert attempts == [('raw.githubusercontent.com', 443, True, ssl.CERT_REQUIRED)]
    print(f'{name:28} {result:10} expected {expected:10} {"PASS" if expected == result else "FAIL"}')
    return expected == result


cases = [('fixed length', record(headers=['Content-Length: 3']), 'BODY 3'),
         ('valid chunked', record(headers=['Transfer-Encoding: chunked'],body=b'3\r\nabc\r\n0\r\n\r\n'), 'BODY 3'),
         ('chunked trailing SP',record(headers=['Transfer-Encoding: chunked '],body=b'3\r\nabc\r\n0\r\n\r\n'), 'UNKNOWN'),
         ('chunked trailing HTAB',record(headers=['Transfer-Encoding: chunked\t'],body=b'3\r\nabc\r\n0\r\n\r\n'),'UNKNOWN'),
         ('early EOF declared', record(headers=['Content-Length: 8']), 'UNKNOWN'),
         ('bad status line', b'bad status\r\n\r\n','UNKNOWN'),
         ('invalid chunk size', record(headers=['Transfer-Encoding: chunked'],body=b'x\r\n'), 'UNKNOWN'),
         ('EOF within chunk', record(headers=['Transfer-Encoding: chunked'],body=b'8\r\nabc'), 'UNKNOWN'),
         ('conflicting lengths', record(headers=['Content-Length: 3','Content-Length: 4']), 'UNKNOWN'),
         ('invalid length', record(headers=['Content-Length: invalid']), 'UNKNOWN'),
         ('both framing headers', record(headers=['Content-Length: 3','Transfer-Encoding: chunked'],body=b'3\r\nabc\r\n0\r\n\r\n'), 'UNKNOWN'),
         ('close delimited unpinned', record(), 'UNKNOWN')]
for status in (301,302,303,307,308,404,500):
    cases.append((str(status), record(str(status)+' status',['Location: https://second.invalid/','Content-Length: 0'],b''),'UNKNOWN'))
for n in (65535,65536,65537):
    cases.append(('size '+str(n), record(headers=['Content-Length: '+str(n)],body=b'.'*n),
                  'UNKNOWN' if n>65536 else 'BODY '+str(n)))
with_no_length=(Path(__file__).parent/'input'/'research_reference_checksums.json').read_bytes()
cases.append(('close delimited pinned',record(body=with_no_length),'BODY 962'))
results=[check(*case) for case in cases]
with patch.object(v.ssl,'create_default_context',side_effect=OSError('trust store unavailable')):
    try: v.fetch_official_reference(v.RELEASE)
    except Exception as exc: result=type(exc).__name__
print('TLS setup exception',result,'expected ReferenceUnknown')
results.append(result=='ReferenceUnknown')
print('Conformance checks',sum(results),'/',len(results))
raise SystemExit(0 if all(results) else 1)
