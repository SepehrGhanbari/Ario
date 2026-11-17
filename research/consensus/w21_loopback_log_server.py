#!/usr/bin/env python3
"""W21 LOOPBACK ONLY synthetic HTTP log facade, NOT C2SP/production.

Serves existing public W20 signed checkpoints, compact consistency proof and
all provided synthetic event inclusion proofs. Never signs or appends events.
There is NO authentic third-party witness, registry or external deployment.
"""
from __future__ import annotations
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from w20_merkle_producer import canon, inclusion_path

DIR = Path(__file__).resolve().parent
FIXTURE = DIR / 'W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json'
MODES = ('normal','stale','tampered-event','tampered-checkpoint','partial','oversize','bad-json')


def make_view(fixture: dict, mode: str) -> tuple[dict, dict, list[str]]:
    events = fixture['events']
    if mode == 'stale':
        old_events = events[:3]
        raw = [canon(x) for x in old_events]
        return fixture['old_checkpoint'], {'events':old_events,
            'inclusions':[{'index':i,'proof':[v.hex() for v in inclusion_path(raw,i)]}
                          for i in range(len(raw))]}, []
    head = json.loads(json.dumps(fixture['new_checkpoint']))
    supplied = {'events':json.loads(json.dumps(events)),
                'inclusions':json.loads(json.dumps(fixture['inclusions']))}
    if mode == 'tampered-event':
        supplied['events'][4]['payload_sha256'] = '0'*64
    if mode == 'tampered-checkpoint':
        head['body']['root_sha256'] = 'f'*64  # signature now invalid
    if mode == 'partial':
        supplied['events'] = supplied['events'][:7]
        supplied['inclusions'] = supplied['inclusions'][:7]
    return head, supplied, fixture['consistency_proof']


class Handler(BaseHTTPRequestHandler):
    server_version = 'W21-Research-Loopback/1'
    def log_message(self, *args):
        pass
    def do_POST(self):
        self.send_error(405, 'W21 read-only')
    def do_PUT(self):
        self.send_error(405, 'W21 read-only')
    def do_DELETE(self):
        self.send_error(405, 'W21 read-only')
    def do_GET(self):
        uri = urlsplit(self.path)
        if uri.fragment or uri.username or uri.password or uri.query and uri.path != '/v0/consistency':
            return self.send_error(400)
        mode = self.server.view_mode
        if uri.path not in ('/v0/checkpoint','/v0/events','/v0/consistency'):
            return self.send_error(404)
        head, supplied, path = make_view(self.server.fixture, mode)
        if uri.path == '/v0/checkpoint':
            obj = {'schema':'ARIO_W21_SYNTHETIC_HTTP_CHECKPOINT_V1','checkpoint':head}
        elif uri.path == '/v0/events':
            obj = {'schema':'ARIO_W21_SYNTHETIC_HTTP_EVENTS_V1',**supplied}
        else:
            params = parse_qs(uri.query, strict_parsing=True, max_num_fields=2)
            try:
                if set(params) != {'old','new'} or len(params['old'])!=1 or len(params['new'])!=1:
                    return self.send_error(400)
                old,new = int(params['old'][0]),int(params['new'][0])
                if old!=3 or new!=head['body']['size']:
                    return self.send_error(404)
            except (ValueError,KeyError,OverflowError):
                return self.send_error(400)
            obj = {'schema':'ARIO_W21_SYNTHETIC_HTTP_CONSISTENCY_V1','old':old,'new':new,'proof':path}
        data = json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
        if mode == 'oversize' and uri.path=='/v0/events':
            data += b' '*100000
        if mode == 'bad-json' and uri.path=='/v0/checkpoint':
            data = b'{"schema":"a","schema":"b"}'
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=MODES,default='normal')
    parser.add_argument('--host',default='127.0.0.1',choices=['127.0.0.1'])
    parser.add_argument('--port',type=int,default=0)
    args=parser.parse_args()
    f=json.loads(FIXTURE.read_text('utf8'))
    with ThreadingHTTPServer((args.host,args.port),Handler) as server:
        server.fixture=f
        server.view_mode=args.mode
        print(f'W21_READY_PORT={server.server_address[1]}',flush=True)
        server.serve_forever(poll_interval=0.1)

if __name__=='__main__': main()
