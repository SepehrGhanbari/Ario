#!/usr/bin/env python3
"""W21 same-author local subprocess/HTTP red and green controls (NO remote witness)."""
import copy
import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from urllib.error import HTTPError
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.request import Request,urlopen
from w21_http_observer import observe

ROOT=Path(__file__).parent
fixture=json.loads((ROOT/'W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json').read_text())
KEY=(ROOT/'W20_EPHEMERAL_PUBLIC_LOG_KEY_2026-11-17.txt').read_text().strip()
PRIOR=json.loads((ROOT/'W20_PRIOR_CHECKPOINT_SIMULATED_PIN_2026-11-17.json').read_text())
HW=fixture['new_checkpoint']

class WebLab(unittest.TestCase):
    def run_view(self,mode,*,key=KEY,prior=PRIOR,highwater=HW):
        cmd=[sys.executable,'-B',str(ROOT/'w21_loopback_log_server.py'),'--mode',mode]
        p=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            ready=p.stdout.readline().strip()
            self.assertTrue(ready.startswith('W21_READY_PORT='),(ready,p.stderr.read() if p.poll() is not None else ''))
            url='http://127.0.0.1:'+ready.split('=')[1]
            return observe(url,pinned_key=key,prior=prior,highwater=highwater)
        finally:
            p.terminate()
            try:p.communicate(timeout=2)
            except subprocess.TimeoutExpired:p.kill();p.communicate(timeout=2)

    def test_http_end_to_end_cases(self):
        cases=[
            ('W21-01_VALID_SYNTHETIC_HTTP_HEAD_AND_ALL_LEAVES','normal',KEY,PRIOR,HW,'HISTORICAL_CONSISTENT','HTTP_RESPONSES_MATCH_SYNTHETIC_RETAINED_HIGHWATER_NOT_WORLD_FRESHNESS'),
            ('W21-02_OLD_HEAD_VS_RETAINED_NEW_HIGHWATER_DENIED','stale',KEY,PRIOR,HW,'DENY','HTTP_ROLLBACK_BELOW_PINNED_HIGHWATER'),
            ('W21-03_OLD_OLD_WITH_OLD_HIGHWATER_STILL_LOOKS_VALID','stale',KEY,PRIOR,PRIOR,'HISTORICAL_CONSISTENT','HTTP_RESPONSES_MATCH_SYNTHETIC_RETAINED_HIGHWATER_NOT_WORLD_FRESHNESS'),
            ('W21-04_NO_HIGHWATER_HOLD','normal',KEY,PRIOR,None,'HOLD_UNCERTAIN','NO_SEPARATELY_RETAINED_HIGHWATER'),
            ('W21-05_NO_OOB_KEY_HOLD','normal',None,PRIOR,HW,'HOLD_UNCERTAIN','NO_OUT_OF_BAND_KEY_PIN'),
            ('W21-06_NO_PRIOR_HOLD','normal',KEY,None,HW,'HOLD_UNCERTAIN','NO_RETAINED_PRIOR_CHECKPOINT'),
            ('W21-07_CORRUPT_EVENT_DENIED','tampered-event',KEY,PRIOR,HW,'DENY','EVENT_INCLUSION_INVALID'),
            ('W21-08_CORRUPT_CHECKPOINT_DENIED','tampered-checkpoint',KEY,PRIOR,HW,'DENY','HTTP_HEAD_SIGNATURE_INVALID'),
            ('W21-09_PARTIAL_HISTORY_HOLD','partial',KEY,PRIOR,HW,'HOLD_UNCERTAIN','INCOMPLETE_FULL_HISTORY_EVIDENCE'),
            ('W21-10_OVERSIZE_RESPONSE_HOLD','oversize',KEY,PRIOR,HW,'HOLD_UNCERTAIN','REMOTE_LOOKUP_INVALID_OR_UNAVAILABLE'),
            ('W21-11_DUPLICATE_KEY_JSON_HOLD','bad-json',KEY,PRIOR,HW,'HOLD_UNCERTAIN','REMOTE_LOOKUP_INVALID_OR_UNAVAILABLE'),
            ('W21-12_WRONG_PINNED_KEY_DENIED','normal','0'*64,PRIOR,HW,'HOLD_UNCERTAIN','UNTRUSTED_PRIOR_INVALID'),
            ('W21-13_ALTERED_HIGHWATER_HOLD','normal',KEY,PRIOR,{**HW,'signature':'0'*128},'HOLD_UNCERTAIN','HIGHWATER_INVALID_OR_UNTRUSTED'),
        ]
        for cid,mode,key,prior,highwater,expected,reason in cases:
            with self.subTest(cid):
                res=self.run_view(mode,key=key,prior=prior,highwater=highwater)
                self.assertEqual((res['verdict'],res['reason']),(expected,reason))
                self.assertEqual(res['operational_authority'],'NONE')
                self.assertEqual(res['real_ario_log_witnessed'],'NOT_ESTABLISHED')
                self.assertFalse(res['memory_admitted'])

    def test_network_unavailability_and_nonlocal_url(self):
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        z=observe(f'http://127.0.0.1:{port}',pinned_key=KEY,prior=PRIOR,highwater=HW)
        self.assertEqual((z['verdict'],z['reason']),('HOLD_UNCERTAIN','REMOTE_LOOKUP_INVALID_OR_UNAVAILABLE'))
        for url in ['https://example.com','http://192.0.2.1:80','http://localhost:1234','http://127.0.0.1:1/other','http://127.0.0.1:not-a-port','http://127.0.0.1:99999']:
            z=observe(url,pinned_key=KEY,prior=PRIOR,highwater=HW)
            self.assertEqual((z['verdict'],z['reason']),('HOLD_UNCERTAIN','NON_LOOPBACK_OR_INVALID_URL'))

    def test_redirect_cannot_escape_single_allowed_origin(self):
        # Deliberately use a second loopback server as a harmless canary:
        # following even this redirect would break the strict origin boundary.
        contacted=[]
        class Canary(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_GET(self):
                contacted.append(self.path)
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.end_headers()
                self.wfile.write(b'{}')
        with HTTPServer(('127.0.0.1',0),Canary) as canary:
            canary_thread=Thread(target=canary.serve_forever,daemon=True)
            canary_thread.start()
            dest=f'http://127.0.0.1:{canary.server_address[1]}/redirected'
            class Redirect(BaseHTTPRequestHandler):
                def log_message(self,*_): pass
                def do_GET(self):
                    self.send_response(302)
                    self.send_header('Location',dest)
                    self.end_headers()
            with HTTPServer(('127.0.0.1',0),Redirect) as redirector:
                redirect_thread=Thread(target=redirector.serve_forever,daemon=True)
                redirect_thread.start()
                try:
                    z=observe(f'http://127.0.0.1:{redirector.server_address[1]}',
                              pinned_key=KEY,prior=PRIOR,highwater=HW)
                    self.assertEqual((z['verdict'],z['reason']),
                                     ('HOLD_UNCERTAIN','REMOTE_LOOKUP_INVALID_OR_UNAVAILABLE'))
                    self.assertEqual(contacted,[], 'HTTP redirect must not reach another origin')
                finally:
                    redirector.shutdown();redirect_thread.join(timeout=2)
            canary.shutdown();canary_thread.join(timeout=2)

    def test_server_rejects_mutating_request(self):
        p=subprocess.Popen([sys.executable,'-B',str(ROOT/'w21_loopback_log_server.py')],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            ready=p.stdout.readline().strip()
            port=int(ready.split('=')[1]);base=f'http://127.0.0.1:{port}/v0/checkpoint'
            for method in ['POST','PUT','DELETE']:
                with self.subTest(method):
                    try:
                        urlopen(Request(base,method=method,data=b'{}'),timeout=2)
                        self.fail('mutating method unexpectedly accepted')
                    except HTTPError as e:
                        self.assertEqual(e.code,405)
        finally:
            p.terminate();p.communicate(timeout=2)

if __name__=='__main__':unittest.main(verbosity=2)
