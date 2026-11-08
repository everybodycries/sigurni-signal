"""Loopback-only offline HTTP station. No unauthenticated LAN server.
SPDX-License-Identifier: GPL-3.0-only
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import secrets
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .core import Store, next_window, required_wh
from .radio import RadioWorker

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'station'/'static'

class StationServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,store,radio):
        if address[0]!='127.0.0.1': raise ValueError('Dopušteno je samo 127.0.0.1.')
        self.store=store; self.radio=radio; self.token=secrets.token_urlsafe(32)
        super().__init__(address,Handler)
        self.origin=f'http://127.0.0.1:{self.server_port}'

class Handler(BaseHTTPRequestHandler):
    server_version='SigurniSignal/0.1'
    def log_message(self,format,*args): pass  # Do not log content, tokens, or local identifiers.
    def _respond(self,status,data,content_type='application/json; charset=utf-8',filename=None):
        if isinstance(data,(dict,list)): data=json.dumps(data,ensure_ascii=False).encode()
        elif isinstance(data,str): data=data.encode()
        self.send_response(status)
        self.send_header('Content-Type',content_type); self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer'); self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers(); self.wfile.write(data)
    def _trusted(self):
        # Exact authority defeats DNS rebinding and hostile browser origins.
        if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':
            self._respond(403,{'error':'Neispravan Host.'}); return False
        origin=self.headers.get('Origin')
        if origin and origin!=self.server.origin:
            self._respond(403,{'error':'Vanjski Origin nije dopušten.'}); return False
        if self.headers.get('Sec-Fetch-Site')=='cross-site':
            self._respond(403,{'error':'Cross-site zahtjev je blokiran.'}); return False
        return True
    def do_GET(self):
        if not self._trusted(): return
        path=urlsplit(self.path).path
        try:
            if path=='/':
                self._respond(200,(STATIC/'index.html').read_text().replace('__CSRF_TOKEN__',self.server.token),'text/html; charset=utf-8')
            elif path in ('/app.js','/style.css'):
                file=STATIC/path[1:]; self._respond(200,file.read_bytes(),'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
            elif path=='/api/state':
                s=self.server.store
                self._respond(200,{'now':int(time.time()),'settings':s.settings(),'radio':self.server.radio.status(),
                    'messages':s.messages(),'radiograms':s.radiograms(),'readiness':s.readiness(),
                    'window':next_window(city=s.settings()['city']),'contacts':s.contacts(),'audit':s.audit()})
            elif path=='/api/guides':
                file=ROOT/'content'/'guides.json'
                self._respond(200,json.loads(file.read_text()) if file.exists() else {'guides':[],'review_status':'not_installed'})
            elif path=='/api/export/audit':
                # JSON avoids spreadsheet formula execution in untrusted radio text.
                self._respond(200,self.server.store.audit(export=True),filename='audit.json')
            elif path=='/api/export/messages':
                self._respond(200,self.server.store.messages(export=True),filename='messages.json')
            else: self._respond(404,{'error':'Nije pronađeno.'})
        except (ValueError,KeyError) as exc: self._respond(400,{'error':str(exc)})
    def do_POST(self):
        if not self._trusted(): return
        if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),self.server.token):
            self._respond(403,{'error':'Nedostaje valjan CSRF token.'}); return
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            self._respond(415,{'error':'Potreban je JSON.'}); return
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=65536: raise ValueError('Neispravna veličina zahtjeva.')
            data=json.loads(self.rfile.read(n)); s=self.server.store; path=urlsplit(self.path).path
            if not isinstance(data,dict): raise ValueError('Potreban je JSON objekt.')
            if path=='/api/messages': result=s.create_message(data['body'],data['destination'],data.get('kind','normal'))
            elif path=='/api/confirm': s.confirm_human(data['id'],data['actor'],data['note']); result={'ok':True}
            elif path=='/api/close': s.close_incident(data['id'],data['actor'],data['note']); result={'ok':True}
            elif path=='/api/radiograms': result=s.create_radiogram(data['body'],data['destination_city'],data['consent_text'],data['public_confirm'],data['consent_by'])
            elif path=='/api/radiograms/advance':
                s.advance_radiogram(data['id'],data['state'],data['actor'],data['note']); result={'ok':True}
            elif path=='/api/evidence':
                s.record_evidence(data['gate'],data['reference'],data['reviewer'],data['reviewed_at'],data['expires_at']); result={'ok':True}
            elif path=='/api/settings':
                s.configure(data['city'],data['radio_enabled'],data.get('local_profile_reference',''),data['actor']); result={'ok':True}
            elif path=='/api/contacts': s.save_contact(data['name'],data['node'],data['city']); result={'ok':True}
            elif path=='/api/power': result={'required_wh':required_wh(data['daily_wh'],data.get('days',3),data.get('efficiency',.85),data.get('temperature_factor',.9))}
            else: self._respond(404,{'error':'Nije pronađeno.'}); return
            s.secure_files(); self._respond(200,result)
        except (ValueError,KeyError,TypeError,OverflowError) as exc: self._respond(400,{'error':str(exc)})
        except Exception:
            self._respond(500,{'error':'Lokalna operacija nije dovršena. Provjerite dnevnik i disk; dostava nije potvrđena.'})

def main():
    parser=argparse.ArgumentParser(description='Sigurni Signal — lokalna bazna konzola, HF ostaje ručan.')
    parser.add_argument('--db',default='work/station-data.nosync/station.sqlite3'); parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--serial',help='Izričit USB put, primjer /dev/ttyACM0. Bez ovoga nema radijske veze.')
    args=parser.parse_args()
    import os
    os.umask(0o077)
    store=Store(args.db); radio=RadioWorker(store,args.serial)
    server=StationServer(('127.0.0.1',args.port),store,radio)
    radio.start()
    print(f'Sigurni Signal: {server.origin} — lokalno slanje početno isključeno; HF ručan i uvjetovan dokazima.',flush=True)
    try: server.serve_forever(poll_interval=.5)
    except KeyboardInterrupt: pass
    finally: server.server_close(); radio.stop(); store.close()

if __name__=='__main__': main()
