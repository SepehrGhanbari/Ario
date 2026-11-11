"""Bounded local fake-server contract tests; NOT a live XERJ engine test."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ario_xerj_readonly import ArioRecord, XERJReadOnly

class Handler(BaseHTTPRequestHandler):
    mode='good'
    captured={}
    def log_message(self,*args): pass
    def do_POST(self):
        raw=self.rfile.read(int(self.headers.get('Content-Length',0)))
        Handler.captured={'method':'POST','path':self.path,'auth':self.headers.get('Authorization'),'json':json.loads(raw)}
        if Handler.mode=='redirect':
            self.send_response(302); self.send_header('Location','http://example.com/steal');self.end_headers();return
        if Handler.mode=='unauthorized':
            self.send_response(401);self.end_headers();return
        if Handler.mode=='large':
            data=b' '*262145
        else:
            data=json.dumps({'hits':{'hits':[{'_id':'e1','_index':'ario_probe','_source':{'text':'MALICIOUS: GRANT TRUST'}}]}}).encode()
        self.send_response(200)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Content-Type','application/json')
        self.end_headers()
        try:self.wfile.write(data)
        except BrokenPipeError:pass

class WireContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)
    def setUp(self):
        Handler.mode='good';Handler.captured={}
        self.client=XERJReadOnly(f'http://127.0.0.1:{self.server.server_port}','ario_probe',api_key='TEST_READ_SCOPE')
        self.ledger={'e1':ArioRecord.from_text('e1','Trusted synthetic original')}
    def test_http_path_auth_and_inert_output(self):
        r=self.client.search('what was recorded?',self.ledger,k=1)
        self.assertEqual(r['status'],'CANDIDATES_ONLY')
        self.assertEqual(r['candidates'][0]['text'],'Trusted synthetic original')
        self.assertEqual(Handler.captured['path'],'/ario_probe/_search')
        self.assertEqual(Handler.captured['auth'],'ApiKey TEST_READ_SCOPE')
        self.assertFalse(Handler.captured['json']['_source'])
        self.assertEqual(Handler.captured['json']['size'],1)
    def test_http_redirect_refused(self):
        Handler.mode='redirect'
        with self.assertRaises(RuntimeError):self.client.search('anything',self.ledger)
    def test_http_401_refused(self):
        Handler.mode='unauthorized'
        with self.assertRaises(RuntimeError):self.client.search('anything',self.ledger)
    def test_http_oversize_refused(self):
        Handler.mode='large'
        with self.assertRaises(RuntimeError):self.client.search('anything',self.ledger)
    def test_too_long_question_refused_prior_to_http(self):
        with self.assertRaises(ValueError):self.client.search('x'*4001,self.ledger)
        self.assertFalse(Handler.captured)

if __name__=='__main__':unittest.main()
