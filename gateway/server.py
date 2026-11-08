"""Read-only static gateway. It never forwards radio, database or Supabase APIs.

Python3.9+, standard library only. GPL-3.0-only.
"""
import argparse
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import stat
from urllib.parse import unquote, urlsplit

PROJECT=Path(__file__).resolve().parents[1]
BLOCKED={'api','radio','station','gateway','tests','supabase','android','work','node_modules'}
TYPES={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8',
       '.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8',
       '.json':'application/json; charset=utf-8','.webmanifest':'application/manifest+json; charset=utf-8',
       '.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg',
       '.webp':'image/webp','.ico':'image/x-icon','.woff':'font/woff','.woff2':'font/woff2',
       '.pdf':'application/pdf','.csv':'text/csv; charset=utf-8','.geojson':'application/geo+json; charset=utf-8','.txt':'text/plain; charset=utf-8','.zip':'application/zip',
       '.apk':'application/vnd.android.package-archive'}
CSP="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' https://*.supabase.co; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"

class GatewayServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,root):
        root=Path(root).resolve(strict=True)
        if not root.is_dir():raise ValueError('Public root must be a directory.')
        if root==PROJECT or root in PROJECT.parents:
            raise ValueError('Serve only the public web directory, never the project/filesystem root.')
        if address[0] not in ('127.0.0.1','0.0.0.0'):raise ValueError('Use localhost or explicit LAN binding.')
        self.root=root
        self.root_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:super().__init__(address,Handler)
        except BaseException:
            if self.root_fd is not None:
                os.close(self.root_fd);self.root_fd=None
            raise
    def server_close(self):
        super().server_close()
        if self.root_fd is not None:
            os.close(self.root_fd);self.root_fd=None

class Handler(BaseHTTPRequestHandler):
    server_version='SigurniSignalGateway/0.2'
    sys_version=''
    def log_message(self,format,*args):pass
    def _headers(self,status,length,content_type='text/plain; charset=utf-8',modified=None):
        self.send_response(status)
        self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(length))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',CSP);self.send_header('X-Frame-Options','DENY')
        # Revalidation when online; the PWA's explicit service worker owns offline caching.
        self.send_header('Cache-Control','no-cache')
        if modified is not None:self.send_header('Last-Modified',formatdate(modified,usegmt=True))
        if status==405:self.send_header('Allow','GET, HEAD')
        self.end_headers()
    def _error(self,status):
        body=b'Not found.\n' if status==404 else b'Read-only gateway. Use GET or HEAD.\n'
        self._headers(status,len(body))
        if self.command!='HEAD':self.wfile.write(body)
    def _open(self):
        path=unquote(urlsplit(self.path).path,encoding='utf-8',errors='strict')
        if not path.startswith('/') or '\\' in path or '\x00' in path:raise ValueError('Invalid path')
        parts=path.split('/')[1:]
        if any(p in ('.','..') or p.startswith('.') for p in parts if p):raise ValueError('Hidden/traversal')
        if any(p.lower() in BLOCKED for p in parts):raise ValueError('Private directory')
        if not any(parts):parts=['index.html']
        elif not parts[-1]:parts.append('index.html')
        parts=[p for p in parts if p]
        if Path(parts[-1]).suffix.lower() not in TYPES:raise ValueError('Unsupported public asset')
        # Resolve check covers ordinary traversal; dirfd + O_NOFOLLOW also prevents
        # swapping a checked directory for a symlink between checking and opening.
        candidate=self.server.root.joinpath(*parts).resolve(strict=True)
        candidate.relative_to(self.server.root)
        directory=os.dup(self.server.root_fd)
        try:
            for part in parts[:-1]:
                following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
                os.close(directory);directory=following
            fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):os.close(fd);raise ValueError('Not a regular file')
            return fd,info,TYPES[Path(parts[-1]).suffix.lower()]
        finally:os.close(directory)
    def _serve(self):
        try:fd,info,mime=self._open()
        except (OSError,ValueError,UnicodeError,RuntimeError):self._error(404);return
        with os.fdopen(fd,'rb')as stream:
            self._headers(200,info.st_size,mime,info.st_mtime)
            if self.command=='HEAD':return
            try:
                while True:
                    block=stream.read(65536)
                    if not block:break
                    self.wfile.write(block)
            except (BrokenPipeError,ConnectionResetError):pass
    def do_GET(self):self._serve()
    def do_HEAD(self):self._serve()
    def do_POST(self):self._error(405)
    do_PUT=do_POST
    do_PATCH=do_POST
    do_DELETE=do_POST
    do_OPTIONS=do_POST
    do_TRACE=do_POST
    do_CONNECT=do_POST


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=PROJECT/'web',help='Only a public, sanitized web directory.')
    parser.add_argument('--port',type=int,default=8088)
    parser.add_argument('--lan',action='store_true',help='Explicitly listen on0.0.0.0 for the isolated LAN.')
    args=parser.parse_args()
    if not 0<=args.port<=65535:parser.error('Port must be between0and65535.')
    try:server=GatewayServer(('0.0.0.0' if args.lan else '127.0.0.1',args.port),args.root)
    except (OSError,ValueError) as exc:parser.error(str(exc))
    print(f'Sigurni Signal public-content gateway: http://127.0.0.1:{server.server_port}',flush=True)
    if args.lan:print('LAN MODE: public content only. No station administration, radio API or database is exposed. Check firewall/router access before use.',flush=True)
    print('HTTP on a non-localhost LAN origin is not a secure context: service-worker installation and cloud cryptography may be unavailable. Preinstall PWA from HTTPS before outage.',flush=True)
    try:server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
