/* Generated app-shell-only cache. Auth/backups and large downloads never cached. */
const CACHE="sigurni-signal-web-1073fadfe04631";
const ASSETS=["/", "/index.html", "/style.css", "/app.mjs", "/config.json", "/manifest.webmanifest", "/guide.html", "/guide.css", "/data/guides.json", "/downloads/prirucnik-offline.html", "/downloads/offgrid-guide.html", "/assets/icon.svg", "/assets/icon-192.png", "/assets/icon-512.png", "/lib/cloud.mjs", "/lib/crypto.mjs", "/lib/model.mjs", "/lib/storage.mjs"];
const URLS=new Set(ASSETS);
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS))));
self.addEventListener('message',event=>{if(event.data?.type==='SKIP_WAITING')self.skipWaiting();});
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const key of await caches.keys())if(key.startsWith('sigurni-signal-web-')&&key!==CACHE)await caches.delete(key);await self.clients.claim();})()));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==self.location.origin||url.search||!URLS.has(url.pathname))return;
event.respondWith((async()=>{const cache=await caches.open(CACHE);const existing=await cache.match(url.pathname);if(existing)return existing;try{const response=await fetch(event.request);if(response.ok)await cache.put(url.pathname,response.clone());return response;}catch{return new Response('Sadržaj još nije spremljen. Otvori aplikaciju dok imaš mrežu.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});}})());});
