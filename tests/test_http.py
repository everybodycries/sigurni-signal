import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from station.core import Store
from station.radio import RadioWorker
from station.server import StationServer

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Store(Path(self.tmp.name)/'db')
        self.radio=RadioWorker(self.db);self.server=StationServer(('127.0.0.1',0),self.db,self.radio)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.db.close();self.tmp.cleanup()
    def req(self,path='/',data=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        h={'Host':f'127.0.0.1:{self.server.server_port}'}
        if data is not None: h.update({'Content-Type':'application/json','X-CSRF-Token':self.server.token})
        h.update(headers or {})
        c.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,h)
        r=c.getresponse(); status=r.status; body=r.read(); response_headers=dict(r.getheaders());c.close()
        return status,body,response_headers
    def test_loopback_only(self):
        with self.assertRaises(ValueError): StationServer(('0.0.0.0',0),self.db,self.radio)
    def test_rebinding_host_rejected(self):
        self.assertEqual(self.req('/api/state',headers={'Host':'hostile.example'})[0],403)
    def test_foreign_origin_rejected(self):
        self.assertEqual(self.req('/api/messages',{'body':'hi','destination':'all'}, {'Origin':'https://evil.example'})[0],403)
    def test_missing_token_rejected(self):
        self.assertEqual(self.req('/api/messages',{'body':'hi','destination':'all'}, {'X-CSRF-Token':''})[0],403)
    def test_create_restart_and_export(self):
        status,body,_=self.req('/api/messages',{'body':'DOBRO SAM','destination':'all','kind':'ok'})
        self.assertEqual(status,200);m=json.loads(body);self.assertEqual(m['status'],'saved')
        self.assertEqual(self.req('/api/state')[0],200)
        status,body,headers=self.req('/api/export/messages');self.assertEqual(status,200)
        self.assertEqual(json.loads(body)[0]['body'],'DOBRO SAM');self.assertIn('attachment',headers['Content-Disposition'])
    def test_no_radio_no_fake_success(self):
        s=json.loads(self.req('/api/state')[1]);self.assertFalse(s['radio']['connected']);self.assertFalse(s['readiness']['hf_ready'])
    def test_html_csp_and_no_external_scripts(self):
        status,body,headers=self.req('/');self.assertEqual(status,200)
        self.assertIn(self.server.token.encode(),body);self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertNotIn(b'<script src="http',body)
    def test_json_type_error_is_bad_request(self):
        self.assertEqual(self.req('/api/messages',{'body':42,'destination':'all'})[0],400)
    def test_content_is_served_offline(self):
        status,body,_=self.req('/api/guides');self.assertEqual(status,200);self.assertGreaterEqual(len(json.loads(body)['guides']),1)
    def test_no_path_traversal(self):
        self.assertEqual(self.req('/../station/core.py')[0],404)
    def test_public_consent_and_hf_gate(self):
        data={'body':'Javni tekst','destination_city':'Sarajevo','consent_text':'Javni tekst','public_confirm':True,'consent_by':'Ana'}
        status,body,_=self.req('/api/radiograms',data);self.assertEqual(status,200)
        id=json.loads(body)['id']
        self.assertEqual(self.req('/api/radiograms/advance',{'id':id,'state':'approved','actor':'Op','note':'review'})[0],400)

if __name__=='__main__':unittest.main()
