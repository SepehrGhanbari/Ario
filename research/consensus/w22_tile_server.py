#!/usr/bin/env python3
"""W22 LOOPBACK ONLY: C2SP signed-note /checkpoint and tiny tlog-tiles subset.

Offers only size 3/8 partial level-0 tiles for a fixed synthetic dataset.
Does NOT offer a production C2SP full tile service, witness API or new writes.
"""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from pathlib import Path
import argparse
import hashlib
import json
import struct


def entry_bytes(e):
    return json.dumps(e,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()


def tile_bytes(events):
    return b''.join(hashlib.sha256(b'\x00' + entry_bytes(e)).digest() for e in events)


def bundle_bytes(events):
    raw = [entry_bytes(e) for e in events]
    if any(len(v) >= 65536 for v in raw):
        raise ValueError('entry bundle too big')
    return b''.join(struct.pack('>H',len(v))+v for v in raw)


def content_for(fixture, mode, path):
    size = 3 if mode == 'stale' else 8
    current = fixture['events'][:size]
    if mode in ('fork','coordinated-data-tamper'):
        current = fixture['fork_events']
    if path == '/checkpoint':
        note = fixture['previous_checkpoint'] if mode == 'stale' else (
            fixture['same_signer_fork_checkpoint'] if mode == 'fork' else fixture['current_checkpoint'])
        if mode == 'bad-signature':
            note = note[:-3] + 'A' + note[-2:]
        if mode == 'bad-size':
            note = note.replace('\n8\n','\n08\n',1)
        return 200, 'text/plain; charset=utf-8', note.encode()
    if path == f'/tile/0/0.p/{size}':
        tile = tile_bytes(current)
        if mode == 'bad-tile':
            tile = bytes([tile[0] ^ 1]) + tile[1:]
        return 200, 'application/octet-stream', tile
    if path == f'/tile/entries/0.p/{size}':
        b=bundle_bytes(current)
        if mode == 'bad-entry':
            b=b[:-1] + bytes([b[-1] ^ 1])
        if mode == 'short-entry':
            b=b[:-1]
        return 200, 'application/octet-stream', b
    if path == '/w22/consistency/3/8' and mode not in ('stale',):
        # NOT a C2SP-standard endpoint. This is a bounded W22 extension only.
        path_nodes=fixture['_local_path']
        if mode == 'bad-consistency':
            path_nodes=list(path_nodes)
            path_nodes[0]='0'*64
        return 200, 'application/json', json.dumps({'schema':'ARIO_W22_LOCAL_COMPACT_PATH_V1',
            'old_size':3,'new_size':8,'nodes':path_nodes},sort_keys=True).encode()
    return 404, 'text/plain; charset=utf-8', b'not found\n'


def make_server(fixture, mode, host='127.0.0.1', port=0):
    assert host == '127.0.0.1'
    assert mode in ('normal','stale','fork','bad-signature','bad-size','bad-tile','bad-entry','short-entry','redirect','coordinated-data-tamper','bad-consistency')
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('//') or self.path != urlsplit(self.path).path or '?' in self.path:
                self.send_error(400)
                return
            if mode == 'redirect' and self.path == '/checkpoint':
                self.send_response(302)
                self.send_header('Location', fixture.get('_redirect_target','http://127.0.0.2:1/checkpoint'))
                self.end_headers()
                return
            status,typ,data=content_for(fixture,mode,self.path)
            self.send_response(status)
            self.send_header('Content-Type',typ)
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_POST(self):
            self.send_error(405,'read-only')
        def log_message(self,*args):
            pass
    return ThreadingHTTPServer((host,port),Handler)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--fixture',required=True)
    ap.add_argument('--w20-fixture',required=True)
    ap.add_argument('--mode',choices=['normal','stale','fork','bad-signature','bad-size','bad-tile','bad-entry','short-entry','redirect','coordinated-data-tamper','bad-consistency'],default='normal')
    ap.add_argument('--port',type=int,default=0)
    args=ap.parse_args()
    fixture=json.loads(Path(args.fixture).read_text('utf8'))
    w20=json.loads(Path(args.w20_fixture).read_text('utf8'))
    fixture['_local_path']=w20['consistency_proof']
    s=make_server(fixture,args.mode,port=args.port)
    print('W22_LOOPBACK_READY http://127.0.0.1:'+str(s.server_port),flush=True)
    try:s.serve_forever()
    finally:s.server_close()

if __name__ == '__main__':
    main()
