"""Durable radio queue and deliberately manual public-radiogram workflow.

No HF transmitter is controlled by this module. Evidence entries are local
operator attestations, not legal opinions or machine validation of reports.
SPDX-License-Identifier: GPL-3.0-only
"""
from __future__ import annotations
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

CITIES = {'Kragujevac': 'Europe/Belgrade', 'Zagreb': 'Europe/Zagreb', 'Sarajevo': 'Europe/Sarajevo', 'Beograd': 'Europe/Belgrade'}
GATES = {
    'legal_HR': 'Hrvatska: važeća pravila i dopušten prijenos',
    'legal_BA': 'BiH: važeća pravila i dopušten prijenos',
    'legal_RS': 'Srbija: važeća pravila i dopušten prijenos',
    'operators_HR': 'Zagreb: dva osposobljena operatera i raspored',
    'operators_BA': 'Sarajevo: dva osposobljena operatera i raspored',
    'operators_RS': 'Beograd: dva osposobljena operatera i raspored',
    'site_HR': 'Zagreb: odobrena lokacija i sigurna instalacija',
    'site_BA': 'Sarajevo: odobrena lokacija i sigurna instalacija',
    'site_RS': 'Beograd: odobrena lokacija i sigurna instalacija',
    'operators_KG': 'Kragujevac: dva osposobljena operatera i raspored',
    'site_KG': 'Kragujevac: odobrena lokacija i bezbedna instalacija',
    'link_KG_ZG': 'Kragujevac–Zagreb: terenski dokaz veze',
    'link_ZG_SA': 'Zagreb–Sarajevo: terenski dokaz veze',
    'link_ZG_BG': 'Zagreb–Beograd: terenski dokaz veze',
    'link_SA_BG': 'Sarajevo–Beograd: terenski dokaz veze',
}
ID_RE = re.compile(r'^[A-Z2-9]{8}$')
DEST_RE = re.compile(r'^![0-9a-fA-F]{8}$')

def clean(value, label='Tekst', maximum=4096):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{label}: obvezan tekst, najviše {maximum} znakova.')
    # Text messages are single-line for predictable printable interoperability.
    if any(ord(c)<32 or ord(c)==127 for c in value):
        raise ValueError(f'{label}: kontrolni znakovi nisu dopušteni.')
    return value.strip()

def encode_wire(message_id, body):
    if not ID_RE.fullmatch(message_id): raise ValueError('Neispravna oznaka poruke.')
    body=clean(body)
    wire=f'[{message_id}] {body}'
    if len(wire.encode('utf-8')) > 200: raise ValueError('Poruka s oznakom prelazi 200 UTF-8 bajtova.')
    return wire

def parse_wire(text):
    if not isinstance(text,str): raise ValueError('Tekst nije niz znakova.')
    m=re.fullmatch(r'POTVRDA ([A-Z2-9]{8})',text.strip())
    if m: return {'type':'receipt_claim','wire_id':m[1],'body':text}
    m=re.fullmatch(r'\[([A-Z2-9]{8})\] (.+)',text)
    if m: return {'type':'message','wire_id':m[1],'body':m[2]}
    return {'type':'plain','wire_id':None,'body':text}

def required_wh(daily_wh,days=3,efficiency=.85,temperature_factor=.9):
    values=(daily_wh,days,efficiency,temperature_factor)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
        raise ValueError('Vrijednosti moraju biti konačni brojevi.')
    if daily_wh<=0 or days<=0 or not 0<efficiency<=1 or not 0<temperature_factor<=1:
        raise ValueError('Potrošnja/dani >0; učinkovitost i temperaturni faktor između 0 i 1.')
    return daily_wh*days*1.3/(efficiency*temperature_factor)

def next_window(now=None,city='Kragujevac'):
    now=int(time.time() if now is None else now)
    if city not in CITIES: raise ValueError('Nepoznat grad.')
    zone=ZoneInfo(CITIES[city]); local=datetime.fromtimestamp(now,zone)
    for day in (0,1):
        date=local.date()+timedelta(days=day)
        for hour in (8,14,20):
            start=datetime(date.year,date.month,date.day,hour,tzinfo=zone)
            end=start+timedelta(minutes=30)
            if now<int(end.timestamp()):
                return {'city':city,'local':start.isoformat(),'utc':start.astimezone(timezone.utc).isoformat(),
                        'start_epoch':int(start.timestamp()),'end_epoch':int(end.timestamp()),
                        'duration_minutes':30,'active':int(start.timestamp())<=now<int(end.timestamp()),
                        'notice':'Planirani prozor; prisutnost operatera i dostava nisu zajamčeni.'}
    raise RuntimeError('Nedostaje idući prozor.')

class Store:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        # New files are private before SQLite first opens them (including WAL).
        self.path.touch(mode=0o600,exist_ok=True); os.chmod(self.path,0o600)
        self.lock=threading.RLock()
        self.db=sqlite3.connect(self.path,check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        with self.lock,self.db:
            self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA foreign_keys=ON')
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY, wire_id TEXT NOT NULL, body TEXT NOT NULL, wire TEXT NOT NULL,
              destination TEXT NOT NULL, sender TEXT NOT NULL, direction TEXT NOT NULL,
              kind TEXT NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
              status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, next_attempt_at INTEGER NOT NULL,
              packet_id INTEGER, human_confirmed_at INTEGER, incident TEXT NOT NULL,
              last_error TEXT NOT NULL DEFAULT '', updated_at INTEGER NOT NULL,
              dedup_key TEXT UNIQUE, sensitivity TEXT NOT NULL DEFAULT 'private');
            CREATE TABLE IF NOT EXISTS audit (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, at INTEGER NOT NULL, actor TEXT NOT NULL,
              subject TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS evidence (
              gate TEXT PRIMARY KEY, reference TEXT NOT NULL, reviewer TEXT NOT NULL,
              reviewed_at INTEGER NOT NULL, expires_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS radiograms (
              id TEXT PRIMARY KEY, body TEXT NOT NULL, destination_city TEXT NOT NULL,
              consent_digest TEXT NOT NULL, consent_by TEXT NOT NULL, consent_at INTEGER NOT NULL,
              state TEXT NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS contacts (id TEXT PRIMARY KEY,name TEXT NOT NULL,node TEXT NOT NULL,city TEXT NOT NULL);
            ''')
            for row in self.db.execute("SELECT id FROM messages WHERE status='submitting'").fetchall():
                self.db.execute("UPDATE messages SET status='needs_review',last_error='Prekid tijekom slanja; provjerite prije novog zahtjeva.' WHERE id=?",(row['id'],))
                self._audit('system',row['id'],'restart_uncertain_send',{},int(time.time()))
        self.secure_files()
    def secure_files(self):
        for suffix in ('','-wal','-shm'):
            p=Path(str(self.path)+suffix)
            if p.exists(): os.chmod(p,0o600)
    def close(self):
        with self.lock: self.db.close()
    def _audit(self,actor,subject,action,detail,now):
        self.db.execute('INSERT INTO audit(at,actor,subject,action,detail) VALUES (?,?,?,?,?)',
                        (now,actor,subject,action,json.dumps(detail,ensure_ascii=False,sort_keys=True)))
    def message(self,id):
        with self.lock:
            row=self.db.execute('SELECT * FROM messages WHERE id=?',(id,)).fetchone()
            if row is None: raise ValueError('Poruka nije pronađena.')
            return dict(row)
    def messages(self,export=False):
        # Unresolved help must remain visible regardless of newer routine traffic.
        query='SELECT * FROM messages'
        if not export:
            query+=" WHERE incident='open' OR id IN (SELECT id FROM messages ORDER BY created_at DESC,id LIMIT 500)"
        query+=' ORDER BY created_at DESC,id'
        with self.lock: return [dict(r) for r in self.db.execute(query)]
    def create_message(self,body,destination,kind='normal',now=None):
        now=int(time.time() if now is None else now)
        if kind not in ('normal','help','ok'): raise ValueError('Nepoznata vrsta poruke.')
        if destination!='all' and not DEST_RE.fullmatch(destination): raise ValueError('Odredište mora biti all ili ! i 8 heksadekadskih znamenki.')
        with self.lock,self.db:
            # Bounded storage/queue; do not silently evict unresolved help.
            n=self.db.execute("SELECT count(*) FROM messages WHERE direction='out' AND status IN ('saved','submitted','submitting') AND human_confirmed_at IS NULL AND incident!='closed' AND attempts<3 AND expires_at>?",(now,)).fetchone()[0]
            if n>=100: raise ValueError('Red ima 100 aktivnih poruka. Potreban je pregled prije novih slanja.')
            for _ in range(10):
                id=base64.b32encode(secrets.token_bytes(5)).decode()
                if not self.db.execute('SELECT 1 FROM messages WHERE id=?',(id,)).fetchone(): break
            else: raise RuntimeError('Nije moguće dodijeliti oznaku poruke.')
            wire=encode_wire(id,body); body=clean(body)
            ttl=3600 if kind=='help' else 86400
            self.db.execute('''INSERT INTO messages(id,wire_id,body,wire,destination,sender,direction,kind,
              created_at,expires_at,status,next_attempt_at,incident,updated_at)
              VALUES (?,?,?,?,?,?,'out',?,?,?,'saved',?,?,?)''',
              (id,id,body,wire,destination,'local',kind,now,now+ttl,now,'open' if kind=='help' else 'none',now))
            self._audit('local',id,'saved',{'bytes':len(wire.encode()),'kind':kind},now)
        return self.message(id)
    def reserve_next(self,now=None):
        now=int(time.time() if now is None else now)
        with self.lock,self.db:
            # A backwards wall-clock step pauses sending instead of extending lifetimes.
            last=self.db.execute("SELECT value FROM settings WHERE key='last_scheduler_at'").fetchone()
            if last and now<int(last[0]): return None
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('last_scheduler_at',?)",(str(now),))
            self.db.execute("UPDATE messages SET status='expired',last_error='Rok slanja istekao; zahtjev nije time riješen.',updated_at=? WHERE direction='out' AND expires_at<=? AND status IN ('saved','submitted')",(now,now))
            # Never allow future-created messages through a clock rollback.
            last_send=self.db.execute("SELECT value FROM settings WHERE key='last_send_at'").fetchone()
            if last_send and now-int(last_send[0])<30: return None
            row=self.db.execute("""SELECT * FROM messages WHERE direction='out' AND status IN ('saved','submitted')
              AND attempts<3 AND next_attempt_at<=? AND expires_at>? AND created_at<=?
              AND human_confirmed_at IS NULL AND incident!='closed' ORDER BY CASE kind WHEN 'help' THEN 0 ELSE 1 END,created_at,id LIMIT 1""",(now,now,now)).fetchone()
            if row is None: return None
            attempts=row['attempts']+1
            self.db.execute("UPDATE messages SET status='submitting',attempts=?,updated_at=? WHERE id=?",(attempts,now,row['id']))
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('last_send_at',?)",(str(now),))
            self._audit('system',row['id'],'attempt_reserved',{'attempt':attempts},now)
            return self.message(row['id'])
    def mark_submitted(self,id,packet_id,now=None):
        now=int(time.time() if now is None else now)
        with self.lock,self.db:
            m=self.message(id)
            if m['status']!='submitting': raise ValueError('Poruka nije u postupku predaje radiju.')
            wait=120 if m['attempts']==1 else 600
            self.db.execute("UPDATE messages SET status='submitted',packet_id=?,next_attempt_at=?,updated_at=? WHERE id=?",(int(packet_id),now+wait,now,id))
            self._audit('radio',id,'submitted',{'packet_id':int(packet_id)},now)
    def mark_uncertain(self,id,error,now=None):
        now=int(time.time() if now is None else now)
        with self.lock,self.db:
            self.db.execute("UPDATE messages SET status='needs_review',last_error=?,updated_at=? WHERE id=?",(str(error)[:300],now,id))
            self._audit('radio',id,'needs_review',{'reason':str(error)[:300]},now)
    def radio_ack(self,packet_id,error='NONE',now=None):
        now=int(time.time() if now is None else now)
        with self.lock,self.db:
            rows=self.db.execute("SELECT id FROM messages WHERE packet_id=? AND status='submitted'",(int(packet_id),)).fetchall()
            for r in rows:
                state='radio_acked' if error in ('NONE',0,'0') else 'needs_review'
                self.db.execute('UPDATE messages SET status=?,last_error=?,updated_at=? WHERE id=?',(state,'' if state=='radio_acked' else str(error),now,r['id']))
                self._audit('radio',r['id'],'radio_ack_claim',{'error':error,'human_confirmed':False},now)
    def receive(self,text,sender,packet_id,now=None):
        now=int(time.time() if now is None else now)
        text=clean(text,maximum=1024)
        if len(text.encode())>233: raise ValueError('Dolazni tekst prelazi podržanu veličinu.')
        sender=clean(sender,'Pošiljatelj',64)
        info=parse_wire(text); dedup=f'{sender}:wire:{info["wire_id"]}' if info['wire_id'] else f'{sender}:packet:{int(packet_id)}'
        id='rx-'+hashlib.sha256(dedup.encode()).hexdigest()[:24]
        with self.lock,self.db:
            existing=self.db.execute('SELECT * FROM messages WHERE dedup_key=?',(dedup,)).fetchone()
            if existing:
                if existing['wire']!=text:
                    self.db.execute("UPDATE messages SET last_error='Sukob oznake: isti pošiljatelj i oznaka, drukčiji tekst. Potreban pregled.' WHERE id=?",(existing['id'],))
                    self._audit(sender,existing['id'],'wire_id_collision',{'sha256_new':hashlib.sha256(text.encode()).hexdigest()},now)
                return self.message(existing['id'])
            incoming_help=info['type']=='message' and info['body'].upper().startswith(('TREBAM POMOĆ','TREBAM POMOC'))
            incoming_kind='help' if incoming_help else info['type']
            self.db.execute('''INSERT INTO messages(id,wire_id,body,wire,destination,sender,direction,kind,
              created_at,expires_at,status,next_attempt_at,incident,updated_at,dedup_key)
              VALUES (?,?,?,?,?,?,'in',?,?,?,'received',?,?,?,?)''',
              (id,info['wire_id'] or '',info['body'],text,'local',sender,incoming_kind,now,now+86400,now,'open' if incoming_help else 'none',now,dedup))
            self._audit(sender,id,'received_unverified',{'type':info['type'],'wire_id':info['wire_id']},now)
        return self.message(id)
    def confirm_human(self,id,actor,note,now=None):
        now=int(time.time() if now is None else now); actor=clean(actor,'Potvrdio',80); note=clean(note,'Način provjere',400)
        with self.lock,self.db:
            self.message(id)
            self.db.execute('UPDATE messages SET human_confirmed_at=?,updated_at=? WHERE id=?',(now,now,id))
            self._audit(actor,id,'human_receipt_manually_verified',{'note':note},now)
    def close_incident(self,id,actor,note,now=None):
        now=int(time.time() if now is None else now); actor=clean(actor,'Operater',80); note=clean(note,'Obrazloženje',400)
        with self.lock,self.db:
            m=self.message(id)
            if m['incident']!='open': raise ValueError('Zahtjev nije otvoren.')
            self.db.execute("UPDATE messages SET incident='closed',updated_at=? WHERE id=?",(now,id))
            self._audit(actor,id,'incident_closed',{'note':note},now)
    def create_radiogram(self,body,destination_city,consent_text,public_confirm,consent_by,now=None):
        now=int(time.time() if now is None else now); body=clean(body,'Javni tekst',200); consent_by=clean(consent_by,'Suglasnost dao',80)
        if len(body.encode())>200: raise ValueError('Javni tekst smije imati najviše 200 UTF-8 bajtova.')
        if destination_city not in CITIES: raise ValueError('Nepoznat grad.')
        if public_confirm is not True or consent_text!=body: raise ValueError('Potrebna je izričita suglasnost za točan javni tekst.')
        id=secrets.token_hex(8); digest=hashlib.sha256(body.encode()).hexdigest()
        with self.lock,self.db:
            self.db.execute("INSERT INTO radiograms VALUES (?,?,?,?,?,?,'pending',?)",(id,body,destination_city,digest,consent_by,now,now))
            self._audit(consent_by,id,'public_consent',{'sha256':digest,'destination_city':destination_city,'exact_text':body},now)
        return next(r for r in self.radiograms() if r['id']==id)
    def radiograms(self):
        with self.lock: return [dict(r) for r in self.db.execute('SELECT * FROM radiograms ORDER BY consent_at DESC,id')]
    def advance_radiogram(self,id,state,actor,note,now=None):
        now=int(time.time() if now is None else now); actor=clean(actor,'Operater',80); note=clean(note,'Dokaz provjere',400)
        with self.lock,self.db:
            row=self.db.execute('SELECT * FROM radiograms WHERE id=?',(id,)).fetchone()
            if row is None: raise ValueError('Radiogram nije pronađen.')
            expected={'pending':'approved','approved':'transmitted','transmitted':'destination_base','destination_base':'human_confirmed'}
            if state=='rejected' and row['state'] in ('pending','approved'): pass
            elif expected.get(row['state'])!=state: raise ValueError('Nedopušten redoslijed potvrda.')
            if state in ('approved','transmitted') and not self.readiness(now)['hf_ready']:
                raise ValueError('HF sloj je zaključan: nedostaju aktualni dokazi o pravilima, operaterima, lokacijama ili vezama.')
            if row['consent_digest']!=hashlib.sha256(row['body'].encode()).hexdigest(): raise ValueError('Tekst više ne odgovara suglasnosti.')
            self.db.execute('UPDATE radiograms SET state=?,updated_at=? WHERE id=?',(state,now,id))
            self._audit(actor,id,'radiogram_'+state,{'note':note,'sha256':row['consent_digest']},now)
    def record_evidence(self,gate,reference,reviewer,reviewed_at,expires_at,now=None):
        now=int(time.time() if now is None else now)
        if gate not in GATES: raise ValueError('Nepoznat uvjet aktivacije.')
        reference=clean(reference,'Dokaz',400); reviewer=clean(reviewer,'Pregledao',80)
        reviewed_at=int(reviewed_at); expires_at=int(expires_at)
        if not 0<reviewed_at<=now<expires_at: raise ValueError('Dokaz mora biti već pregledan i imati budući rok ponovne provjere.')
        with self.lock,self.db:
            self.db.execute('INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?)',(gate,reference,reviewer,reviewed_at,expires_at))
            self._audit(reviewer,gate,'evidence_recorded',{'reference':reference,'reviewed_at':reviewed_at,'expires_at':expires_at},now)
    def readiness(self,now=None):
        now=int(time.time() if now is None else now)
        with self.lock:
            entries={r['gate']:dict(r) for r in self.db.execute('SELECT * FROM evidence')}
            gates=[]
            for key,title in GATES.items():
                e=entries.get(key); current=bool(e and e['reviewed_at']<=now<e['expires_at'])
                gates.append({'key':key,'title':title,'current':current,'evidence':e})
            return {'hf_ready':all(g['current'] for g in gates),'gates':gates,
                    'notice':'Evidencija operatera nije automatska pravna potvrda. HF prijenos ostaje ručan.'}
    def audit(self,export=False):
        query='SELECT * FROM audit ORDER BY seq DESC'+('' if export else ' LIMIT 500')
        with self.lock: return [dict(r) for r in self.db.execute(query)]
    def settings(self):
        with self.lock:
            d={r['key']:r['value'] for r in self.db.execute('SELECT * FROM settings')}
            return {'city':d.get('city','Kragujevac'),'radio_enabled':d.get('radio_enabled','false')=='true','local_profile_reference':d.get('local_profile_reference','')}
    def configure(self,city,radio_enabled,local_profile_reference,actor):
        if city not in CITIES: raise ValueError('Nepoznat grad.')
        actor=clean(actor,'Operater',80)
        if not isinstance(radio_enabled,bool): raise ValueError('radio_enabled mora biti boolean.')
        if radio_enabled: local_profile_reference=clean(local_profile_reference,'Dokaz lokalnog radijskog profila',400)
        with self.lock,self.db:
            for k,v in {'city':city,'radio_enabled':str(radio_enabled).lower(),'local_profile_reference':local_profile_reference}.items():
                self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(k,v))
            self._audit(actor,'settings','configured',{'city':city,'radio_enabled':radio_enabled,'reference':local_profile_reference},int(time.time()))
    def contacts(self):
        with self.lock: return [dict(r) for r in self.db.execute('SELECT * FROM contacts ORDER BY name')]
    def save_contact(self,name,node,city):
        name=clean(name,'Ime',80)
        if not DEST_RE.fullmatch(node): raise ValueError('Čvor mora biti ! i osam heksadekadskih znamenki.')
        if city not in CITIES: raise ValueError('Nepoznat grad.')
        node=node.lower()
        with self.lock,self.db:
            self.db.execute('INSERT OR REPLACE INTO contacts VALUES (?,?,?,?)',(node,name,node,city))
