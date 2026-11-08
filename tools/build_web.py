"""Prepare static, free-hostable assets; private app data is never published."""
from pathlib import Path
import hashlib,json,re,shutil,struct,zlib,math
ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'web'
def png_icon(size):
 # Raster companion to the original SVG brandmark; no external image dependency.
 bg=(21,60,50);fg=(217,237,182);rows=[]
 for y in range(size):
  row=bytearray()
  for x in range(size):
   a=(x+.5)*192/size;b=(y+.5)*192/size;dx=a-96;dy=b-96;dist=math.hypot(dx,dy)
   ink=abs(dist-53)<4 or (b<=96 and (abs(dist-38)<4 or abs(dist-19)<4)) or dist<8 or (abs(dx)<4 and 119<=b<=145)
   # Rounded-square background plus generous maskable icon safe zone.
   corner=math.hypot(max(abs(dx)-52,0),max(abs(dy)-52,0))
   row.extend((*((fg if ink else bg)),255 if corner<=44 else 0))
  rows.append(b'\0'+row)
 data=zlib.compress(b''.join(rows),9)
 def chunk(t,b):return struct.pack('!I',len(b))+t+b+struct.pack('!I',zlib.crc32(t+b)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',data)+chunk(b'IEND',b'')
def main():
 (WEB/'data').mkdir(exist_ok=True);(WEB/'downloads').mkdir(exist_ok=True)
 shutil.copy2(ROOT/'content/guides.json',WEB/'data/guides.json')
 handbook=(ROOT/'docs/prirucnik-offline.html').read_text()
 css=re.search(r'<style>(.*?)</style>',handbook,re.S).group(1)
 (WEB/'guide.css').write_text(css+'\npre{white-space:pre-wrap;overflow-wrap:anywhere}\n')
 (WEB/'guide.html').write_text(re.sub(r'<style>.*?</style>','<link rel="stylesheet" href="/guide.css">',handbook,flags=re.S))
 (WEB/'downloads/prirucnik-offline.html').write_text(handbook)
 offgrid=(ROOT/'docs/offgrid-deployment.md').read_text()
 import html
 (WEB/'downloads/offgrid-guide.html').write_text('<!doctype html><html lang="hr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vlastita lokalna mreža</title><link rel="stylesheet" href="/guide.css"><main><h1>Vlastita lokalna mreža</h1><pre>'+html.escape(offgrid)+'</pre></main></html>')
 for size in (192,512):(WEB/f'assets/icon-{size}.png').write_bytes(png_icon(size))
 config=json.loads((WEB/'config.json').read_text());
 if (ROOT/'sigurni-signal-pilot.apk').exists():config['nativeSha256']=hashlib.sha256((ROOT/'sigurni-signal-pilot.apk').read_bytes()).hexdigest()
 elif not re.fullmatch(r'[a-f0-9]{64}',config.get('nativeSha256','')):raise ValueError('Supply verified APK or configured nativeSha256')
 (WEB/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
 cache_files=['/','/index.html','/style.css','/app.mjs','/config.json','/manifest.webmanifest','/guide.html','/guide.css','/data/guides.json','/downloads/prirucnik-offline.html','/downloads/offgrid-guide.html','/assets/icon.svg','/assets/icon-192.png','/assets/icon-512.png']+[f'/lib/{p.name}' for p in sorted((WEB/'lib').glob('*.mjs'))]
 digest=hashlib.sha256(b'worker-v2-normalized-pages'+b''.join((WEB/f.lstrip('/')).read_bytes() for f in cache_files if f!='/')).hexdigest()[:14]
 sw="""/* Generated app-shell-only cache. Auth/backups and large downloads never cached. */
const CACHE=__CACHE__;
const ASSETS=__ASSETS__;
const ALIASES=Object.fromEntries(ASSETS.filter(p=>p.endsWith('.html')).map(p=>[p==='/index.html'?'/':p.slice(0,-5),p]));
const URLS=new Set([...ASSETS,...Object.keys(ALIASES)]);
const clean=response=>new Response(response.body,{status:response.status,statusText:response.statusText,headers:response.headers});
self.addEventListener('install',event=>event.waitUntil((async()=>{const cache=await caches.open(CACHE);await Promise.all(ASSETS.map(async path=>{const response=await fetch(path,{cache:'reload'});if(!response.ok)throw new Error('Offline asset unavailable');await cache.put(path,clean(response));}));})()));
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')self.skipWaiting();});
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const key of await caches.keys())if(key.startsWith('sigurni-signal-web-')&&key!==CACHE)await caches.delete(key);await self.clients.claim();})()));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==self.location.origin||url.search||!URLS.has(url.pathname))return;
event.respondWith((async()=>{const cache=await caches.open(CACHE);const key=ALIASES[url.pathname]||url.pathname;const existing=await cache.match(key);if(existing)return clean(existing);try{const response=await fetch(event.request);if(response.ok)await cache.put(key,clean(response.clone()));return response;}catch{return new Response('Sadržaj još nije spremljen. Otvori aplikaciju dok imaš mrežu.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});}})());});
""".replace('__CACHE__',json.dumps('sigurni-signal-web-'+digest)).replace('__ASSETS__',json.dumps(cache_files))
 (WEB/'sw.js').write_text(sw)
 headers="""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; connect-src 'self' https://*.supabase.co; worker-src 'self'; manifest-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'
/sw.js
  Cache-Control: no-cache
/config.json
  Cache-Control: no-cache
/downloads/prirucnik-offline.html
  Content-Disposition: attachment; filename="sigurni-signal-prirucnik.html"
"""
 (WEB/'_headers').write_text(headers)
 (WEB/'robots.txt').write_text('User-agent: *\nAllow: /\n')
 for p in WEB.rglob('*'):
  if p.is_file() and p.stat().st_size>25*1024*1024:raise ValueError('Pages asset limit exceeded:'+str(p))
 print('Public static assets prepared. Shell cache:',digest,'No credentials or private station files published.')
if __name__=='__main__':main()
