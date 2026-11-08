/* SPDX-License-Identifier: GPL-3.0-only */
export const VERSION='0.3.0';
export const CITIES=['Zagreb','Sarajevo','Beograd'];
export const CHECKS=[['radio','Radio konfiguriran za lokalno dopušten profil'],['keys','Privatni kanal i kontakti provjereni osobno'],['charge','Radio i rezervne baterije napunjeni'],['bank','Powerbank i kabeli provjereni'],['offline','Priručnik spremljen i otvoren bez mreže'],['shelter','Veza ispitana iz dogovorenog unutarnjeg prostora'],['contacts','Papirnata kopija kontakata spremljena'],['family','Obiteljski postupak i mjesto dogovoreni'],['water','Zaliha vode i hrane pripremljena'],['medicine','Osobni lijekovi pripremljeni prema uputama liječnika'],['receiver','Baterijski prijamnik i svjetiljka provjereni'],['co','Generator i CO alarm pripremljeni prema uputama']];
export const byteLength=s=>new TextEncoder().encode(s).length;
function text(value,max,empty=true,multiline=false){if(typeof value!=='string'||value.length>max||(!empty&&!value.trim())||(multiline?/[\x00-\x09\x0b-\x1f\x7f]/:/[\x00-\x1f\x7f]/).test(value))throw new Error('Neispravan tekst ili kontrolni znak.');return value;}
export function wireMessage(id,body){if(!/^[A-Z2-9]{8}$/.test(id))throw new Error('Neispravna oznaka poruke.');body=text(body,200,false).trim();const wire=`[${id}] ${body}`;if(byteLength(wire)>200)throw new Error('Najviše 200 UTF-8 bajtova, uključujući oznaku.');return wire;}
export function newId(){const values=crypto.getRandomValues(new Uint8Array(8));return [...values].map(n=>'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'[n%32]).join('');}
export function freshState(){return {version:1,city:'Zagreb',contacts:[],drafts:[],checklist:CHECKS.map(([id,label])=>({id,label,done:false})),plan:{contact:'',meeting:'',notes:''}};}
export function validateState(s){
 if(!s||s.version!==1||!CITIES.includes(s.city)||!Array.isArray(s.contacts)||s.contacts.length>100||!Array.isArray(s.drafts)||s.drafts.length>500||!Array.isArray(s.checklist)||s.checklist.length!==CHECKS.length||!s.plan||typeof s.plan!=='object')throw new Error('Nepodržana ili prevelika sigurnosna kopija.');
 const contacts=s.contacts.map(c=>{const id=text(c.id,80,false),name=text(c.name,80,false),node=text(c.node,20,false);if(!/^![0-9a-fA-F]{8}$/.test(node))throw new Error('Neispravna oznaka radijskog čvora.');return{id,name,node:node.toLowerCase()};});
 if(new Set(contacts.map(c=>c.id)).size!==contacts.length||new Set(contacts.map(c=>c.node)).size!==contacts.length)throw new Error('Duplicirane oznake kontakata.');
 const drafts=s.drafts.map(d=>{const id=text(d.id,8,false);wireMessage(id,d.body);if(!Number.isSafeInteger(d.createdAt)||d.createdAt<=0||!['normal','ok','help'].includes(d.kind)||!['all',...contacts.map(c=>c.node)].includes(d.destination))throw new Error('Neispravan nacrt.');return{id,body:d.body,destination:d.destination,createdAt:d.createdAt,kind:d.kind};});
 if(new Set(drafts.map(d=>d.id)).size!==drafts.length)throw new Error('Duplicirane oznake nacrta.');
 const checklist=CHECKS.map(([id,label])=>{const c=s.checklist.find(c=>c.id===id);if(!c||typeof c.done!=='boolean')throw new Error('Neispravan popis pripreme.');return{id,label,done:c.done};});
 return{version:1,city:s.city,contacts,drafts,checklist,plan:{contact:text(s.plan.contact,200),meeting:text(s.plan.meeting,300),notes:text(s.plan.notes,2000,true,true)}};
}
export function backupState(state){const valid=validateState(state);return{...valid,drafts:[]};}
export function powerBudget(daily,days=3,eff=.85,usable=.9){if([daily,days,eff,usable].some(n=>typeof n!=='number'||!Number.isFinite(n))||daily<=0||days<=0||eff<=0||eff>1||usable<=0||usable>1)throw new Error('Unesi pozitivne vrijednosti; faktori moraju biti između 0 i 1.');return daily*days*1.3/(eff*usable);}
export function nextWatch(now=new Date()){
 if(!Number.isFinite(now.getTime()))throw new Error('Neispravno vrijeme.');
 const fmt=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Zagreb',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 const parts=date=>Object.fromEntries(fmt.formatToParts(date).map(x=>[x.type,x.value]));
 const offsetAt=date=>{const p=parts(date);return Date.UTC(+p.year,+p.month-1,+p.day,+p.hour,+p.minute,+p.second)-Math.floor(date.getTime()/1000)*1000;};
 const p=parts(now);
 for(let day=0;day<2;day++)for(const h of [8,14,20]){
  const base=Date.UTC(+p.year,+p.month-1,+p.day+day,h);let at=new Date(base-offsetAt(new Date(base)));at=new Date(base-offsetAt(at));
  if(now.getTime()<at.getTime()+1800000)return{at,local:String(h).padStart(2,'0')+':00',active:now>=at,staffed:false};
 }
 throw new Error('Termin nije dostupan.');
}

/** The native pilot generates a fresh wire ID; the official client sends plain text. */
export function radioCopy(draft,client){const wire=wireMessage(draft.id,draft.body);if(client==='android')return draft.body.trim();if(client==='official')return wire;throw new Error('Odaberi radijski klijent.');}
