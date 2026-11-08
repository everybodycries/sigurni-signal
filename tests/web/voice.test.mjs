import test from 'node:test';
import assert from 'node:assert/strict';
import {VoiceCalls} from '../../web/lib/voice.mjs';

const A='10000000-0000-4000-8000-000000000001',B='10000000-0000-4000-8000-000000000002',C='10000000-0000-4000-8000-000000000003',ID='20000000-0000-4000-8000-000000000001';
const offer={type:'offer',sdp:'v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n'},answer={type:'answer',sdp:'v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n'};
const call=(overrides={})=>({id:ID,caller_id:A,callee_id:B,state:'ringing',offer,answer:null,created_at:new Date().toISOString(),expires_at:new Date(Date.now()+45000).toISOString(),...overrides});
function media(){const track={kind:'audio',enabled:true,stopped:false,stop(){this.stopped=true;}};return {track,getTracks:()=>[track],getAudioTracks:()=>[track]};}
class FakePC extends EventTarget{
 static instances=[];
 constructor(config){super();this.config=config;this.connectionState='new';this.iceGatheringState='complete';this.localDescription=null;this.remoteDescription=null;this.closed=false;this.added=[];this.remoteSets=0;FakePC.instances.push(this);}
 addTrack(track,stream){this.added.push({track,stream});}
 async createOffer(){return offer;}
 async createAnswer(){return answer;}
 async setLocalDescription(d){this.localDescription=d;}
 async setRemoteDescription(d){this.remoteDescription=d;this.remoteSets++;}
 close(){this.closed=true;this.connectionState='closed';this.onconnectionstatechange?.();}
 connect(){this.connectionState='connected';this.onconnectionstatechange?.();}
}
function fixture(selfId=A,extra={}){const requests=[],states=[],errors=[],streams=[],captured=[];const rpc=async(action,data)=>{requests.push({action,data});if(action==='call_start')return{call:call({caller_id:selfId,callee_id:data.peer,offer:data.offer})};if(action==='call_answer')return{call:call({state:'accepted',answer:data.answer,expires_at:new Date(Date.now()+3600000).toISOString()})};return{ok:true};};const voice=new VoiceCalls({selfId,rpc,onState:s=>states.push(s),onError:e=>errors.push(e),onRemoteStream:s=>streams.push(s),mediaDevices:{getUserMedia:async c=>{assert.deepEqual(c,{audio:true,video:false});const stream=media();captured.push(stream);return stream;}},PeerConnection:FakePC,...extra});return{voice,requests,states,errors,streams,captured};}

test('incoming polling never opens microphone, autoanswers or duplicates state',async()=>{let captures=0;const f=fixture(B,{mediaDevices:{getUserMedia:async()=>{captures++;return media();}}});await f.voice.observe([call()]);await f.voice.observe([call()]);assert.equal(captures,0);assert.equal(f.requests.length,0);assert.equal(f.states.filter(s=>s.phase==='incoming').length,1);f.voice.dispose();});
test('outgoing remains ringing until answer and real connection, mute and hangup stop capture',async()=>{const f=fixture();await f.voice.start(B);const pc=FakePC.instances.at(-1);assert.equal(f.states.at(-1).phase,'ringing');assert.equal(f.states.some(s=>s.phase==='connected'),false);await f.voice.observe([call({state:'accepted',answer})]);await f.voice.observe([call({state:'accepted',answer})]);assert.equal(pc.remoteSets,1);assert.equal(f.states.at(-1).phase,'connecting');pc.connect();assert.equal(f.states.at(-1).phase,'connected');f.voice.setMuted(true);assert.equal(f.captured[0].track.enabled,false);await f.voice.hangup();assert.equal(f.captured[0].track.stopped,true);assert.equal(pc.closed,true);assert.equal(f.requests.at(-1).action,'call_end');assert.equal(f.states.at(-1).phase,'ended');f.voice.dispose();});
test('cancelling during pending microphone permission stops late stream and never signals',async()=>{let resolve;const pending=new Promise(r=>resolve=r);const f=fixture(A,{mediaDevices:{getUserMedia:()=>pending}});const started=f.voice.start(B);for(let i=0;i<4;i++)await Promise.resolve();await f.voice.hangup();const stream=media();resolve(stream);await started;assert.equal(stream.track.stopped,true);assert.equal(f.requests.length,0);assert.equal(f.states.at(-1).phase,'ended');f.voice.dispose();});
test('late call creation after local hangup is ended on server',async()=>{let finish;const pending=new Promise(r=>finish=r);const requests=[];const f=fixture(A,{rpc:async(a,d)=>{requests.push({a,d});return a==='call_start'?pending:{ok:true};}});const started=f.voice.start(B);for(let i=0;i<6;i++)await Promise.resolve();await f.voice.hangup();finish({call:call()});await started;assert.equal(f.captured[0].track.stopped,true);assert.equal(requests.at(-1).a,'call_end');assert.equal(requests.at(-1).d.id,ID);f.voice.dispose();});
test('only intended callee can accept and malformed or expired invitations do not capture',async()=>{const f=fixture(C);assert.equal(await f.voice.accept(call()),false);assert.equal(await f.voice.accept(call({callee_id:C,offer:{type:'answer',sdp:'invalid'}})),false);assert.equal(await f.voice.accept(call({callee_id:C,expires_at:new Date(Date.now()-1).toISOString()})),false);assert.equal(f.captured.length,0);assert.equal(f.requests.length,0);f.voice.dispose();});
test('accept supplies answer, incoming end and dispose stop microphone and remote audio',async()=>{const f=fixture(B);await f.voice.observe([call()]);assert.equal(await f.voice.accept(call()),true);const pc=FakePC.instances.at(-1);assert.deepEqual(pc.remoteDescription,offer);assert.equal(f.requests.at(-1).action,'call_answer');assert.equal(f.states.at(-1).phase,'connecting');const remote={};pc.ontrack({streams:[remote]});assert.equal(f.streams.at(-1),remote);await f.voice.observe([call({state:'ended'})]);assert.equal(pc.closed,true);assert.equal(f.captured[0].track.stopped,true);assert.equal(f.streams.at(-1),null);f.voice.dispose();});
test('server rejection releases microphone and reports failure',async()=>{const f=fixture(A,{rpc:async()=>{throw new Error('Peer is busy');}});assert.equal(await f.voice.start(B),false);assert.equal(f.captured[0].track.stopped,true);assert.equal(FakePC.instances.at(-1).closed,true);assert.equal(f.states.at(-1).phase,'failed');assert.equal(f.errors.length,1);f.voice.dispose();});
test('dispose during permission request prevents late access and later actions',async()=>{let resolve;const pending=new Promise(r=>resolve=r);const f=fixture(A,{mediaDevices:{getUserMedia:()=>pending}});const operation=f.voice.start(B);for(let i=0;i<4;i++)await Promise.resolve();f.voice.dispose();const stream=media();resolve(stream);await operation;assert.equal(stream.track.stopped,true);assert.equal(await f.voice.start(B),false);assert.equal(f.requests.length,0);});
test('unrelated or oversize signaling is ignored without disrupting a valid incoming call',async()=>{const f=fixture(B);await f.voice.observe([call()]);await f.voice.observe([call({caller_id:C,callee_id:C}),call({offer:{type:'offer',sdp:'x'.repeat(40001)}})]);assert.equal(f.captured.length,0);assert.equal(f.states.at(-1).phase,'incoming');f.voice.dispose();});

test('microphone refusal is reported clearly without signaling or retrying capture',async()=>{let attempts=0;const f=fixture(A,{mediaDevices:{getUserMedia:async()=>{attempts++;throw new DOMException('Permission denied','NotAllowedError');}}});assert.equal(await f.voice.start(B),false);assert.equal(attempts,1);assert.equal(f.requests.length,0);assert.match(f.states.at(-1).message,/Mikrofon nije odobren/);f.voice.dispose();});
test('decline does not capture and an unrelated member cannot terminate an invitation',async()=>{const f=fixture(B);await f.voice.observe([call()]);assert.equal(await f.voice.decline(call()),true);assert.equal(f.captured.length,0);assert.deepEqual(f.requests.at(-1),{action:'call_end',data:{id:ID,reason:'declined'}});f.voice.dispose();const outsider=fixture(C);assert.equal(await outsider.voice.decline(call()),false);assert.equal(outsider.requests.length,0);outsider.voice.dispose();});

test('missed terminal server record stops capture with a localized result',async()=>{const f=fixture();await f.voice.start(B);await f.voice.observe([call({state:'missed',offer:null,answer:null,expires_at:new Date(Date.now()-1000).toISOString()})]);assert.equal(f.states.at(-1).phase,'ended');assert.match(f.states.at(-1).message,/nije prihvaćen/);assert.equal(f.captured[0].track.stopped,true);assert.equal(FakePC.instances.at(-1).closed,true);f.voice.dispose();});

test('ICE timeout can signal already-gathered LAN candidates while remaining unconnected',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});
 class LanPC extends FakePC{constructor(c){super(c);this.iceGatheringState='gathering';}async setLocalDescription(d){this.localDescription={...d,sdp:d.sdp+'a=candidate:123 1 udp 2122260223 127.0.0.1 50000 typ host\r\n'};}}
 const f=fixture(A,{PeerConnection:LanPC});const started=f.voice.start(B);for(let i=0;i<8;i++)await Promise.resolve();assert.equal(f.requests.length,0);t.mock.timers.tick(8000);assert.equal(await started,true);assert.equal(f.requests[0].action,'call_start');assert.match(f.requests[0].data.offer.sdp,/127\.0\.0\.1/);assert.equal(f.states.at(-1).phase,'ringing');assert.equal(f.states.some(s=>s.phase==='connected'),false);f.voice.dispose();
});
test('ICE timeout with no candidate still fails and releases microphone',async t=>{
 t.mock.timers.enable({apis:['setTimeout']});class EmptyPC extends FakePC{constructor(c){super(c);this.iceGatheringState='gathering';}}
 const f=fixture(A,{PeerConnection:EmptyPC});const started=f.voice.start(B);for(let i=0;i<8;i++)await Promise.resolve();t.mock.timers.tick(8000);assert.equal(await started,false);assert.equal(f.requests.length,0);assert.equal(f.captured[0].track.stopped,true);assert.equal(f.states.at(-1).phase,'failed');f.voice.dispose();
});

test('dynamic ICE provider resolves before capture and supplies the actual connection config',async()=>{
 const order=[],servers=[{urls:['turns:relay.example.invalid:443?transport=tcp'],username:'temporary-user',credential:'test-ephemeral-secret'}];
 const f=fixture(A,{iceServers:async()=>{order.push('provider');return servers;},mediaDevices:{getUserMedia:async()=>{order.push('microphone');return media();}}});
 assert.equal(await f.voice.start(B),true);assert.deepEqual(order,['provider','microphone']);assert.deepEqual(FakePC.instances.at(-1).config.iceServers,servers);await f.voice.hangup();assert.equal(await f.voice.start(B),true);assert.deepEqual(order,['provider','microphone','provider','microphone']);f.voice.dispose();
});
test('cancel during dynamic ICE resolution never requests microphone',async()=>{
 let resolve;const provider=new Promise(r=>resolve=r);const f=fixture(A,{iceServers:()=>provider});const started=f.voice.start(B);await f.voice.hangup();resolve([{urls:'stun:stun.example.invalid:3478'}]);assert.equal(await started,false);assert.equal(f.captured.length,0);assert.equal(f.requests.length,0);f.voice.dispose();
});
test('ICE provider errors or invalid credentials fail before capture',async()=>{
 for(const iceServers of [async()=>{throw new Error('TURN service unavailable');},async()=>[{urls:'https://not-a-turn.example'}],async()=>Array.from({length:11},()=>({urls:'stun:stun.example.invalid'})),async()=>[{urls:'turn:relay.example.invalid:70000',credential:'x'}],async()=>[{urls:'turn:relay.example.invalid:3478',credential:'x'.repeat(513)}]]){
  const f=fixture(A,{iceServers});assert.equal(await f.voice.start(B),false);assert.equal(f.captured.length,0);assert.equal(f.requests.length,0);assert.equal(f.states.at(-1).phase,'failed');f.voice.dispose();
 }
});
test('accept also resolves fresh ICE credentials before opening microphone',async()=>{
 const order=[],servers=[{urls:'turn:relay.example.invalid:3478?transport=udp',username:'u',credential:'p'}];const f=fixture(B,{iceServers:async()=>{order.push('provider');return servers;},mediaDevices:{getUserMedia:async()=>{order.push('microphone');return media();}}});
 assert.equal(await f.voice.accept(call()),true);assert.deepEqual(order,['provider','microphone']);assert.deepEqual(FakePC.instances.at(-1).config.iceServers,servers);f.voice.dispose();
});

test('immediate cancel before resolved configuration continuation never opens microphone',async()=>{const f=fixture(A,{iceServers:async()=>[{urls:'stun:stun.example.invalid'}]});const started=f.voice.start(B);await f.voice.hangup();assert.equal(await started,false);assert.equal(f.captured.length,0);assert.equal(f.requests.length,0);f.voice.dispose();});
