import http.client
from pathlib import Path
import tempfile
import threading
import unittest
from gateway.server import GatewayServer

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'web';self.root.mkdir()
        (self.root/'index.html').write_text('<!doctype html><title>Public guide</title>')
        (self.root/'app.mjs').write_text('export const ready = true;')
        (self.root/'manifest.webmanifest').write_text('{"name":"Signal"}')
        (self.root/'.env').write_text('secret')
        (self.root/'private.sqlite3').write_bytes(b'private')
        (self.root/'api').mkdir();(self.root/'api/state').write_text('private')
        (self.root/'station').mkdir();(self.root/'station/secrets.txt').write_text('private')
        (self.root/'empty').mkdir()
        self.secret=Path(self.temp.name)/'secret.txt';self.secret.write_text('outside root')
        (self.root/'link.txt').symlink_to(self.secret)
        (self.root/'loop.txt').symlink_to(self.root/'loop.txt')
        self.server=GatewayServer(('127.0.0.1',0),self.root)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path='/',method='GET'):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        c.request(method,path)
        response=c.getresponse();result=response.status,response.read(),dict(response.getheaders());c.close();return result
    def test_index_and_head(self):
        status,body,headers=self.request();self.assertEqual(status,200);self.assertIn(b'Public guide',body)
        status,body,head=self.request(method='HEAD');self.assertEqual(status,200);self.assertEqual(body,b'');self.assertEqual(head['Content-Length'],headers['Content-Length'])
    def test_busy_port_preserves_bind_error(self):
        with self.assertRaises(OSError): GatewayServer(('127.0.0.1',self.server.server_port),self.root)
    def test_static_mime_types(self):
        self.assertEqual(self.request('/app.mjs')[2]['Content-Type'],'text/javascript; charset=utf-8')
        self.assertEqual(self.request('/manifest.webmanifest')[2]['Content-Type'],'application/manifest+json; charset=utf-8')
    def test_only_get_and_head(self):
        for method in ('POST','PUT','PATCH','DELETE','OPTIONS','TRACE','CONNECT'):
            self.assertEqual(self.request('/',method)[0],405)
    def test_traversal_and_symlink_are_blocked(self):
        for path in ('/../secret.txt','/%2e%2e/secret.txt','/%2E%2E%2Fsecret.txt','/folder/%2e%2e/index.html','/link.txt','/loop.txt','/..%5csecret.txt'):
            self.assertEqual(self.request(path)[0],404,path)
    def test_hidden_and_private_files_are_blocked(self):
        for path in ('/.env','/%2eenv','/private.sqlite3','/api/state','/station/secrets.txt'):
            self.assertEqual(self.request(path)[0],404,path)
    def test_no_directory_listing(self):
        for path in ('/empty','/empty/'):
            self.assertEqual(self.request(path)[0],404)
    def test_no_cloud_or_radio_proxy(self):
        for path in ('/api/messages','/api/export/messages','/radio/send','/supabase/secret.txt'):
            self.assertEqual(self.request(path)[0],404)
    def test_security_headers(self):
        _,_,h=self.request();self.assertEqual(h['X-Content-Type-Options'],'nosniff')
        self.assertEqual(h['Referrer-Policy'],'no-referrer');self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin',h)
    def test_root_cannot_be_project_or_filesystem_ancestor(self):
        from gateway.server import PROJECT
        for root in (PROJECT,PROJECT.parent,Path('/')):
            with self.assertRaises(ValueError): GatewayServer(('127.0.0.1',0),root)

if __name__=='__main__':unittest.main()
