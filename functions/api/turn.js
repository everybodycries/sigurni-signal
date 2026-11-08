/* GPL-3.0-only. Cloudflare Pages Function; no provider secrets in public bundles. */
const AUTH_URL='https://idgjvhuctieesmkyiwfl.supabase.co/rest/v1/rpc/sigurni_signal_community';
const PUBLIC_KEY='sb_publishable_L3D3232C5sZIVI8QDjn_4A_PBNKBIQt';
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function answer(status,data,extra={}){return new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','Pragma':'no-cache','X-Content-Type-Options':'nosniff',...extra}});}
async function boundedText(message,limit){
 const declared=message.headers.get('Content-Length');
 if(declared!==null&&(!/^\d+$/.test(declared)||Number(declared)>limit))throw new Error('body limit');
 if(!message.body)return '';
 const reader=message.body.getReader(),parts=[];let size=0;
 try{for(;;){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>limit)throw new Error('body limit');parts.push(value);}}
 catch(error){try{await reader.cancel();}catch{}throw error;}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.byteLength;}
 return new TextDecoder('utf-8',{fatal:true}).decode(bytes);
}
async function fetchJson(url,options,limit){
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),8000);
 try{const response=await fetch(url,{...options,signal:controller.signal,redirect:'manual',cache:'no-store',credentials:'omit'});
  if(!response.ok){try{await response.body?.cancel();}catch{}return{ok:false,status:response.status,data:null};}
  return{ok:true,status:response.status,data:JSON.parse(await boundedText(response,limit))};
 }finally{clearTimeout(timeout);}
}
function providerUrl(value){
 if(typeof value!=='string')return null;
 try{const u=new URL(value);return u.protocol==='https:'&&/^[a-z0-9-]+\.metered\.live$/.test(u.hostname)&&!u.port&&!u.username&&!u.password&&!u.search&&!u.hash&&u.pathname==='/api/v1/turn/credentials'?u:null;}catch{return null;}
}
function iceServers(data,apiKey){
 if(!Array.isArray(data)||data.length<2||data.length>10)throw new Error('invalid ICE list');
 let hasTurn=false;
 const result=data.map(server=>{
  if(!server||typeof server!=='object'||Array.isArray(server))throw new Error('invalid ICE server');
  const urls=typeof server.urls==='string'?[server.urls]:server.urls;
  if(!Array.isArray(urls)||urls.length<1||urls.length>10)throw new Error('invalid ICE URLs');
  let needsCredential=false;
  for(const url of urls){
   if(typeof url!=='string'||url.length>512||url.includes(apiKey)||!/^(stun|stuns|turn|turns):(?:\[[0-9a-f:.]+\]|[a-z0-9.-]+)(?::\d{1,5})?(?:\?transport=(udp|tcp))?$/i.test(url))throw new Error('invalid ICE URL');
   if(/^turns?:/i.test(url)){needsCredential=true;hasTurn=true;}
  }
  const clean={urls:typeof server.urls==='string'?server.urls:[...urls]};
  for(const key of ['username','credential'])if(server[key]!==undefined){if(typeof server[key]!=='string'||server[key].length<1||server[key].length>512||server[key].includes(apiKey))throw new Error('invalid ICE credential');clean[key]=server[key];}
  if(needsCredential&&(!clean.username||!clean.credential))throw new Error('missing TURN credential');
  return clean;
 });
 if(!hasTurn)throw new Error('relay server absent');
 return result;
}
export async function onRequest({request,env={}}){
 if(request.method!=='POST')return answer(405,{message:'Koristi POST zahtjev.'},{Allow:'POST'});
 const origin=request.headers.get('Origin');
 if(origin&&origin!==new URL(request.url).origin)return answer(403,{message:'Zahtjev s druge stranice nije dopušten.'});
 if(!/^application\/json(?:\s*;|$)/i.test(request.headers.get('Content-Type')||''))return answer(400,{message:'Zahtjev mora biti JSON.'});
 let input;
 try{input=JSON.parse(await boundedText(request,1024));if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).length!==1||typeof input.key!=='string'||!/^[0-9a-f]{64}$/.test(input.key))throw new Error('invalid key');}
 catch{return answer(400,{message:'Provjeri pristupni ključ i veličinu zahtjeva.'});}
 // Authenticate before even reporting provider configuration; a revoked key cannot obtain ICE.
 let auth;
 try{auth=await fetchJson(AUTH_URL,{method:'POST',headers:{apikey:PUBLIC_KEY,'Content-Type':'application/json'},body:JSON.stringify({p_key:input.key,p_action:'login',p_data:{}})},4096);}
 catch{return answer(503,{message:'Provjera pristupa trenutačno nije dostupna. Pokušaj ponovno.'});}
 if(!auth.ok){if(auth.status>=500||auth.status===429)return answer(503,{message:'Provjera pristupa trenutačno nije dostupna. Pokušaj ponovno.'});return answer(401,{message:'Pristupni ključ nije valjan ili je pristup zaustavljen.'});}
 if(!UUID.test(auth.data?.self?.id||''))return answer(401,{message:'Pristup nije potvrđen.'});
 const provider=providerUrl(env.TURN_API_URL),apiKey=typeof env.TURN_API_KEY==='string'?env.TURN_API_KEY.trim():'';
 if(!provider||!apiKey||apiKey.length>4096)return answer(503,{configured:false,message:'TURN relay još nije povezan. Izravni poziv može raditi samo ako ga mreža dopušta.'});
 provider.searchParams.set('apiKey',apiKey);
 let upstream;
 try{upstream=await fetchJson(provider.toString(),{method:'GET',headers:{Accept:'application/json'}},65536);}
 catch{return answer(503,{configured:true,message:'Relay trenutačno nije dostupan. Pokušaj kasnije.'});}
 if(!upstream.ok){if(upstream.status===429)return answer(429,{configured:true,message:'Relay je ograničio broj zahtjeva. Pokušaj kasnije.'});return answer(502,{configured:true,message:'Relay trenutačno nije dostupan. Pokušaj kasnije.'});}
 try{return answer(200,{configured:true,iceServers:iceServers(upstream.data,apiKey)});}
 catch{return answer(502,{configured:true,message:'Relay nije vratio valjanu konfiguraciju. Pokušaj kasnije.'});}
}
