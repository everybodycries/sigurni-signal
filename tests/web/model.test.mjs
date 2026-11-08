import test from 'node:test';
import assert from 'node:assert/strict';
import {freshState,validateState,wireMessage,byteLength,powerBudget,nextWatch} from '../../web/lib/model.mjs';
import {seal,unseal,validateEnvelope} from '../../web/lib/crypto.mjs';
test('fresh planner starts empty and has no fabricated measurements',()=>{const s=freshState();assert.equal(s.contacts.length,0);assert.equal(s.drafts.length,0);assert.equal(s.city,'Zagreb');assert.ok(s.checklist.length>=10);assert.ok(s.checklist.every(x=>!x.done));});
test('wire limits include ID and Croatian characters',()=>{assert.equal(wireMessage('A7K42P9Q','DOBRO SAM'),'[A7K42P9Q] DOBRO SAM');assert.equal(byteLength(wireMessage('AAAAAAAA','ć'.repeat(94)+'a')),200);assert.throws(()=>wireMessage('AAAAAAAA','ć'.repeat(95)));assert.throws(()=>wireMessage('AAAAAAAA','a\nb'));});
test('imports are bounded and cannot contain unvalidated nested values',()=>{assert.throws(()=>validateState({}));const s=freshState();s.contacts=[{id:'a',name:'x',node:'javascript:evil'}];assert.throws(()=>validateState(s));const d=freshState();d.drafts=Array(501).fill({});assert.throws(()=>validateState(d));});
test('power calculator accounts for losses, zero and NaN',()=>{assert.ok(Math.abs(powerBudget(100,3,.8,.9)-541.6666667)<.0001);for(const n of [0,-1,NaN,Infinity])assert.throws(()=>powerBudget(n));});
test('watch windows do not imply active operators',()=>{const r=nextWatch(new Date('2026-11-08T06:00:00Z'));assert.equal(r.local,'08:00');assert.equal(r.at.toISOString(),'2026-11-08T07:00:00.000Z');assert.equal(r.staffed,false);});
test('backup encrypts, roundtrips, rejects wrong phrase and tampering',async()=>{const state=freshState();state.plan.notes='private test only';const e=await seal(state,'long private passphrase');assert.equal(e.cipher,'AES-256-GCM');assert.equal(e.iterations,600000);assert.ok(!JSON.stringify(e).includes('private test only'));assert.deepEqual(await unseal(e,'long private passphrase'),state);await assert.rejects(unseal(e,'another wrong passphrase'));const altered={...e,ciphertext:e.ciphertext.slice(0,-4)+'AAAA'};await assert.rejects(unseal(altered,'long private passphrase'));});
test('envelope bounds defend KDF/size abuse and short phrases',async()=>{await assert.rejects(seal(freshState(),'short'));assert.throws(()=>validateEnvelope({version:1,iterations:999999999}));const e=await seal(freshState(),'long private passphrase');assert.throws(()=>validateEnvelope({...e,iterations:1}));assert.throws(()=>validateEnvelope({...e,extra:'field'}));});

test('next watch handles DST offset on the following day',()=>{assert.equal(nextWatch(new Date('2026-03-28T21:00:00Z')).at.toISOString(),'2026-03-29T06:00:00.000Z');assert.equal(nextWatch(new Date('2026-10-24T21:00:00Z')).at.toISOString(),'2026-10-25T07:00:00.000Z');});

test('copy respects native-generated IDs and official text interoperability',async()=>{
 const {radioCopy}=await import('../../web/lib/model.mjs');
 const draft={id:'ABCDEFGH',body:'Dobro sam · čujemo se'};
 assert.equal(radioCopy(draft,'android'),'Dobro sam · čujemo se');
 assert.equal(radioCopy(draft,'official'),'[ABCDEFGH] Dobro sam · čujemo se');
 assert.throws(()=>radioCopy(draft,'unknown'));
});
