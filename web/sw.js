/* Generated app-shell-only cache. Auth/backups and large downloads never cached. */
const CACHE="sigurni-signal-web-a7d90dfdcfe2ea";
const ASSETS=["/", "/index.html", "/style.css", "/app.mjs", "/community.mjs", "/config.json", "/manifest.webmanifest", "/guide.html", "/guide.css", "/data/guides.json", "/downloads/prirucnik-offline.html", "/downloads/offgrid-guide.html", "/assets/icon.svg", "/assets/icon-192.png", "/assets/icon-512.png", "/lib/cloud.mjs", "/lib/community.mjs", "/lib/crypto.mjs", "/lib/model.mjs", "/lib/storage.mjs", "/lib/voice.mjs"];
const ALIASES=Object.fromEntries(ASSETS.filter(p=>p.endsWith('.html')).map(p=>[p==='/index.html'?'/':p.slice(0,-5),p]));
const URLS=new Set([...ASSETS,...Object.keys(ALIASES)]);
const clean=response=>new Response(response.body,{status:response.status,statusText:response.statusText,headers:response.headers});
self.addEventListener('install',event=>event.waitUntil((async()=>{const cache=await caches.open(CACHE);await Promise.all(ASSETS.map(async path=>{const response=await fetch(path,{cache:'reload'});if(!response.ok)throw new Error('Offline asset unavailable');await cache.put(path,clean(response));}));})()));
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')self.skipWaiting();});
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const key of await caches.keys())if(key.startsWith('sigurni-signal-web-')&&key!==CACHE)await caches.delete(key);await self.clients.claim();})()));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==self.location.origin||url.search||!URLS.has(url.pathname))return;
event.respondWith((async()=>{const cache=await caches.open(CACHE);const key=ALIASES[url.pathname]||url.pathname;const existing=await cache.match(key);if(existing)return clean(existing);try{const response=await fetch(event.request);if(response.ok)await cache.put(key,clean(response.clone()));return response;}catch{return new Response('Sadržaj još nije spremljen. Otvori aplikaciju dok imaš mrežu.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});}})());});
