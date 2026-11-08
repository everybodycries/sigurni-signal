-- LOCAL EPHEMERAL DATABASE ONLY. Synthetic capability credentials are not real keys.
begin;
insert into sigurni_signal_private.members(id,key_hash,nickname,city,role)values
('11111111-1111-4111-8111-111111111111',encode(sha256(convert_to(repeat('a',64),'UTF8')),'hex'),'Admin','Zagreb','admin');
set local role anon;
do $test$
declare a jsonb;b jsonb;c jsonb;result jsonb;delta jsonb;backup jsonb;mid uuid;cid uuid;denied boolean;n integer;
begin
 -- No direct private-data access even for an API role possessing a valid key.
 begin perform count(*)from sigurni_signal_private.members;raise exception 'direct read allowed';exception when insufficient_privilege then null;end;
 begin perform public.sigurni_signal_community(repeat('0',64),'login');raise exception 'unknown key accepted';exception when invalid_authorization_specification then null;end;
 begin perform public.sigurni_signal_community(null,'snapshot');raise exception 'anonymous access accepted';exception when invalid_authorization_specification then null;end;
 result:=public.sigurni_signal_community(repeat('a',64),'login');assert result#>>'{self,role}'='admin';
 perform public.sigurni_signal_community(repeat('a',64),'admin_invite',jsonb_build_object('invite_hash',encode(sha256(convert_to(repeat('1',64),'UTF8')),'hex'),'label','Test pozivnica'));
 a:=public.sigurni_signal_community(null,'join',jsonb_build_object('invite',repeat('1',64),'member_key',repeat('b',64),'nickname','Ana','city','Sarajevo'));
 assert a#>>'{self,role}'='member';
 begin perform public.sigurni_signal_community(null,'join',jsonb_build_object('invite',repeat('1',64),'member_key',repeat('f',64),'nickname','Replay','city','Zagreb'));raise exception 'invite replay allowed';exception when invalid_authorization_specification then null;end;
 begin perform public.sigurni_signal_community(repeat('b',64),'admin_snapshot');raise exception 'member became admin';exception when insufficient_privilege then null;end;
 perform public.sigurni_signal_community(repeat('a',64),'admin_invite',jsonb_build_object('invite_hash',encode(sha256(convert_to(repeat('2',64),'UTF8')),'hex'),'label','Druga pozivnica'));
 b:=public.sigurni_signal_community(null,'join',jsonb_build_object('invite',repeat('2',64),'member_key',repeat('c',64),'nickname','Boris','city','Beograd'));
 perform public.sigurni_signal_community(repeat('a',64),'admin_invite',jsonb_build_object('invite_hash',encode(sha256(convert_to(repeat('3',64),'UTF8')),'hex'),'label','Treća pozivnica'));
 c:=public.sigurni_signal_community(null,'join',jsonb_build_object('invite',repeat('3',64),'member_key',repeat('d',64),'nickname','Cecilija','city','Zagreb'));
 -- Group message and idempotent retransmission.
 result:=public.sigurni_signal_community(repeat('b',64),'send','{"request_id":"aaaaaaaa-1111-4111-8111-111111111111","body":"Pozdrav grupi","room":"general"}');mid:=(result->>'id')::uuid;
 assert public.sigurni_signal_community(repeat('b',64),'send','{"request_id":"aaaaaaaa-1111-4111-8111-111111111111","body":"Pozdrav grupi","room":"general"}')->>'id'=mid::text;
 begin perform public.sigurni_signal_community(repeat('b',64),'send','{"request_id":"aaaaaaaa-1111-4111-8111-111111111111","body":"Promijenjena poruka","room":"general"}');raise exception 'request ID changed meaning';exception when invalid_parameter_value then null;end;
 result:=public.sigurni_signal_community(repeat('c',64),'snapshot','{"room":"general"}');assert jsonb_array_length(result->'messages')=1;
 assert result#>>'{messages,0,body}'='Pozdrav grupi';
 delta:=public.sigurni_signal_community(repeat('c',64),'snapshot',jsonb_build_object('room','general','known_messages',result->>'messages_version','known_directory',result->>'directory_version'));
 assert delta->'messages'='null'::jsonb and delta->'directory'='null'::jsonb,'unchanged poll repeated payload';
 assert delta->>'messages_version'=result->>'messages_version' and delta->>'directory_version'=result->>'directory_version';
 delta:=public.sigurni_signal_community(repeat('c',64),'snapshot','{"room":"general","known_messages":"stale","known_directory":"stale"}');
 assert jsonb_array_length(delta->'messages')=1 and jsonb_array_length(delta->'directory')=4,'stale poll omitted needed payload';
 result:=public.sigurni_signal_community(repeat('b',64),'send',jsonb_build_object('request_id','aaaaaaaa-2222-4222-8222-222222222222','body','Privatno Ana Borisu','peer',b#>>'{self,id}'));
 mid:=(result->>'id')::uuid;
 result:=public.sigurni_signal_community(repeat('c',64),'snapshot',jsonb_build_object('peer',a#>>'{self,id}'));assert jsonb_array_length(result->'messages')=1;
 result:=public.sigurni_signal_community(repeat('d',64),'snapshot',jsonb_build_object('peer',a#>>'{self,id}'));assert jsonb_array_length(result->'messages')=0;
 result:=public.sigurni_signal_community(repeat('a',64),'snapshot',jsonb_build_object('peer',a#>>'{self,id}'));assert jsonb_array_length(result->'messages')=0,'unrelated admin read private DM';
 begin perform public.sigurni_signal_community(repeat('a',64),'admin_redact',jsonb_build_object('id',mid));raise exception 'admin redacted private DM';exception when insufficient_privilege then null;end;
 -- Profile edits cannot introduce role changes.
 result:=public.sigurni_signal_community(repeat('b',64),'profile','{"nickname":"Ana Nova","city":"Sarajevo","role":"admin"}');assert result#>>'{self,role}'='member';assert result#>>'{self,nickname}'='Ana Nova';
 -- Community-key encrypted backups always target actor.id, including for administrators.
 backup:='{"version":1,"cipher":"AES-256-GCM","kdf":"PBKDF2-SHA256","iterations":600000,"salt":"AAAAAAAAAAAAAAAAAAAAAA==","iv":"AAAAAAAAAAAAAAAA","ciphertext":"AAAAAAAAAAAAAAAAAAAAAA=="}'::jsonb;
 perform public.sigurni_signal_community(repeat('b',64),'backup_put',jsonb_build_object('envelope',backup,'member_id',b#>>'{self,id}'));
 result:=public.sigurni_signal_community(repeat('b',64),'backup_get','{}');assert result->'envelope'=backup and result->>'updated_at' is not null;
 begin perform public.sigurni_signal_community(repeat('c',64),'backup_get',jsonb_build_object('member_id',a#>>'{self,id}'));raise exception 'other member read backup';exception when invalid_parameter_value then null;end;
 begin perform public.sigurni_signal_community(repeat('a',64),'backup_get',jsonb_build_object('member_id',a#>>'{self,id}'));raise exception 'admin read another member backup';exception when invalid_parameter_value then null;end;
 begin perform public.sigurni_signal_community(repeat('b',64),'backup_put',jsonb_build_object('envelope',backup||'{"extra":true}'::jsonb));raise exception 'extra envelope field accepted';exception when invalid_parameter_value then null;end;
 begin perform public.sigurni_signal_community(repeat('b',64),'backup_put',jsonb_build_object('envelope',jsonb_set(backup,'{ciphertext}',to_jsonb(repeat('A',95000)))));raise exception 'oversize backup accepted';exception when invalid_parameter_value then null;end;
 assert public.sigurni_signal_community(repeat('b',64),'backup_get','{}')->'envelope'=backup,'invalid overwrite changed prior backup';
 perform public.sigurni_signal_community(repeat('c',64),'backup_delete',jsonb_build_object('member_id',a#>>'{self,id}'));
 assert public.sigurni_signal_community(repeat('b',64),'backup_get','{}')->'envelope'=backup,'other member deleted owner backup';
 backup:=jsonb_set(backup,'{ciphertext}','"BBBBBBBBBBBBBBBBBBBBBB=="');
 perform public.sigurni_signal_community(repeat('b',64),'backup_put',jsonb_build_object('envelope',backup));
 assert public.sigurni_signal_community(repeat('b',64),'backup_get','{}')->'envelope'=backup,'owner upsert failed';
 perform public.sigurni_signal_community(repeat('b',64),'backup_delete','{}');
 begin perform public.sigurni_signal_community(repeat('b',64),'backup_get','{}');raise exception 'deleted backup remained';exception when invalid_parameter_value then null;end;
 raise notice 'Community encrypted backup roundtrip, owner-only access, strict envelope/size validation, upsert and deletion passed';
 -- Real call authorization and SDP privacy.
 result:=public.sigurni_signal_community(repeat('b',64),'call_start',jsonb_build_object('peer',b#>>'{self,id}','offer',jsonb_build_object('type','offer','sdp',E'v=0\r\nsynthetic-offer')));cid:=(result#>>'{call,id}')::uuid;
 delta:=public.sigurni_signal_community(repeat('b',64),'snapshot',jsonb_build_object('known_call',cid::text||':ringing'));
 assert delta#>>'{calls,0,unchanged}'='true' and delta#>'{calls,0,offer}'='null'::jsonb and delta#>'{calls,0,answer}'='null'::jsonb,'unchanged call repeated SDP';
 begin perform public.sigurni_signal_community(repeat('d',64),'call_end',jsonb_build_object('id',cid,'reason','ended'));raise exception 'outsider ended call';exception when insufficient_privilege then null;end;
 begin perform public.sigurni_signal_community(repeat('b',64),'call_answer',jsonb_build_object('id',cid,'answer',jsonb_build_object('type','answer','sdp','wrong side')));raise exception 'caller answered own call';exception when insufficient_privilege then null;end;
 result:=public.sigurni_signal_community(repeat('d',64),'snapshot','{}');assert jsonb_array_length(result->'calls')=0,'outsider read SDP';
 result:=public.sigurni_signal_community(repeat('c',64),'call_answer',jsonb_build_object('id',cid,'answer',jsonb_build_object('type','answer','sdp',E'v=0\r\nsynthetic-answer')));assert result#>>'{call,state}'='accepted';
 result:=public.sigurni_signal_community(repeat('b',64),'snapshot',jsonb_build_object('known_call',cid::text||':ringing'));assert result#>>'{calls,0,answer,type}'='answer';assert result#>>'{calls,0,unchanged}'='false','changed call answer omitted';
 perform public.sigurni_signal_community(repeat('b',64),'call_end',jsonb_build_object('id',cid,'reason','ended'));
 result:=public.sigurni_signal_community(repeat('c',64),'snapshot','{}');assert result#>>'{calls,0,state}'='ended';assert result#>'{calls,0,offer}'='null'::jsonb;assert result#>'{calls,0,answer}'='null'::jsonb;
 -- Admin announcement, moderation, self-protection and live revocation.
 perform public.sigurni_signal_community(repeat('a',64),'admin_announcement','{"body":"Testna obavijest"}');
 result:=public.sigurni_signal_community(repeat('b',64),'snapshot','{}');assert result#>>'{announcements,0,body}'='Testna obavijest';
 mid:=(result#>>'{messages,0,id}')::uuid;
 perform public.sigurni_signal_community(repeat('a',64),'admin_redact',jsonb_build_object('id',mid));
 result:=public.sigurni_signal_community(repeat('b',64),'snapshot','{}');assert result#>>'{messages,0,redacted}'='true';assert result#>>'{messages,0,body}'='[Poruku je uklonio administrator]';
 begin perform public.sigurni_signal_community(repeat('a',64),'admin_member','{"id":"11111111-1111-4111-8111-111111111111","role":"member","active":true}');raise exception 'admin removed own role';exception when insufficient_privilege then null;end;
 perform public.sigurni_signal_community(repeat('a',64),'admin_member',jsonb_build_object('id',c#>>'{self,id}','role','member','active',false));
 begin perform public.sigurni_signal_community(repeat('d',64),'login');raise exception 'revoked key accepted';exception when invalid_authorization_specification then null;end;
 begin perform public.sigurni_signal_community(repeat('d',64),'snapshot',jsonb_build_object('known_messages',result->>'messages_version','known_directory',result->>'directory_version'));raise exception 'delta bypassed revoked key';exception when invalid_authorization_specification then null;end;
 result:=public.sigurni_signal_community(repeat('a',64),'admin_snapshot');assert jsonb_array_length(result->'members')=4;assert result#>>'{stats,members}'='3';assert jsonb_array_length(result->'audit')>=6;
 assert position('key_hash' in result::text)=0 and position('token_hash' in result::text)=0,'response exposed hashes';
 -- Strict JSON types and payload bounds.
 begin perform public.sigurni_signal_community(repeat('b',64),'send',jsonb_build_object('request_id',gen_random_uuid(),'body',jsonb_build_object('unexpected','object'),'room','general'));raise exception 'object body accepted';exception when invalid_parameter_value then null;end;
 begin perform public.sigurni_signal_community(repeat('b',64),'send',jsonb_build_object('request_id',gen_random_uuid(),'body',repeat('x',1501),'room','general'));raise exception 'oversize message accepted';exception when invalid_parameter_value then null;end;
 begin perform public.sigurni_signal_community(repeat('b',64),'profile','{"nickname":123,"city":"Zagreb"}');raise exception 'nonstring profile accepted';exception when invalid_parameter_value then null;end;
 begin perform public.sigurni_signal_community(repeat('b',64),'call_start',jsonb_build_object('peer',b#>>'{self,id}','offer',jsonb_build_object('type','offer','sdp','ok','extra',true)));raise exception 'extra signaling fields accepted';exception when invalid_parameter_value then null;end;
 begin perform public.sigurni_signal_community(repeat('b',64),'call_start',jsonb_build_object('peer',b#>>'{self,id}','offer',jsonb_build_object('type','offer','sdp',repeat('x',40001))));raise exception 'oversize SDP accepted';exception when invalid_parameter_value then null;end;
 -- Pending invites can be explicitly revoked before use.
 result:=public.sigurni_signal_community(repeat('a',64),'admin_invite',jsonb_build_object('invite_hash',encode(sha256(convert_to(repeat('4',64),'UTF8')),'hex'),'label','Revoke test'));
 perform public.sigurni_signal_community(repeat('a',64),'admin_revoke_invite',jsonb_build_object('id',result->>'id'));
 begin perform public.sigurni_signal_community(null,'join',jsonb_build_object('invite',repeat('4',64),'member_key',repeat('f',64),'nickname','Revoked Invite','city','Zagreb'));raise exception 'revoked invitation accepted';exception when invalid_authorization_specification then null;end;
 -- Deactivated/demoted administrators cannot leave redeemable old invitations behind.
 perform public.sigurni_signal_community(repeat('a',64),'admin_member',jsonb_build_object('id',b#>>'{self,id}','role','admin','active',true));
 perform public.sigurni_signal_community(repeat('c',64),'admin_invite',jsonb_build_object('invite_hash',encode(sha256(convert_to(repeat('5',64),'UTF8')),'hex'),'label','Creator demotion test'));
 perform public.sigurni_signal_community(repeat('a',64),'admin_member',jsonb_build_object('id',b#>>'{self,id}','role','member','active',true));
 begin perform public.sigurni_signal_community(null,'join',jsonb_build_object('invite',repeat('5',64),'member_key',repeat('f',64),'nickname','Demoted Creator Invite','city','Zagreb'));raise exception 'demoted creator invite accepted';exception when invalid_authorization_specification then null;end;
 perform public.sigurni_signal_community(repeat('a',64),'admin_member',jsonb_build_object('id',b#>>'{self,id}','role','admin','active',true));
 perform public.sigurni_signal_community(repeat('c',64),'admin_invite',jsonb_build_object('invite_hash',encode(sha256(convert_to(repeat('6',64),'UTF8')),'hex'),'label','Creator deactivation test'));
 perform public.sigurni_signal_community(repeat('a',64),'admin_member',jsonb_build_object('id',b#>>'{self,id}','role','admin','active',false));
 begin perform public.sigurni_signal_community(null,'join',jsonb_build_object('invite',repeat('6',64),'member_key',repeat('f',64),'nickname','Inactive Creator Invite','city','Zagreb'));raise exception 'inactive creator invite accepted';exception when invalid_authorization_specification then null;end;
 perform public.sigurni_signal_community(repeat('a',64),'admin_member',jsonb_build_object('id',b#>>'{self,id}','role','member','active',true));
 raise notice 'Invitations from demoted or inactive creators are rejected';
 -- Twenty messages per minute, but an identical safe retry remains idempotent.
 for n in 1..18 loop
  cid:=gen_random_uuid();result:=public.sigurni_signal_community(repeat('b',64),'send',jsonb_build_object('request_id',cid,'body','Quota test','room','general'));
 end loop;
 assert public.sigurni_signal_community(repeat('b',64),'send',jsonb_build_object('request_id',cid,'body','Quota test','room','general'))=result;
 begin perform public.sigurni_signal_community(repeat('b',64),'send',jsonb_build_object('request_id',gen_random_uuid(),'body','Too fast','room','general'));raise exception 'message quota absent';exception when program_limit_exceeded then null;end;
 for n in 1..12 loop
  result:=public.sigurni_signal_community(repeat('c',64),'call_start',jsonb_build_object('peer',a#>>'{self,id}','offer',jsonb_build_object('type','offer','sdp','Quota offer')));
  cid:=(result#>>'{call,id}')::uuid;
  begin perform public.sigurni_signal_community(repeat('b',64),'call_start',jsonb_build_object('peer',b#>>'{self,id}','offer',jsonb_build_object('type','offer','sdp','Busy offer')));raise exception 'busy callee accepted call';exception when object_not_in_prerequisite_state then null;end;
  perform public.sigurni_signal_community(repeat('c',64),'call_end',jsonb_build_object('id',cid,'reason','ended'));
 end loop;
 begin perform public.sigurni_signal_community(repeat('c',64),'call_start',jsonb_build_object('peer',a#>>'{self,id}','offer',jsonb_build_object('type','offer','sdp','Too many')));raise exception 'call quota absent';exception when program_limit_exceeded then null;end;
 raise notice 'Strict payload validation, invite revocation, 20/min messages, idempotent retries, busy peer and 12/hour call quotas passed';
 raise notice 'Community role, invitation, chat, DM, call, redaction, profile and revocation assertions passed';
end $test$;
reset role;
-- A verified active snapshot does the hourly, application-scoped retention sweep.
update sigurni_signal_private.housekeeping set last_cleanup=now()-interval '2 hours';
insert into sigurni_signal_private.messages(request_id,sender_id,room,body,created_at)values(gen_random_uuid(),'11111111-1111-4111-8111-111111111111','general','Old retention fixture',now()-interval '31 days');
insert into sigurni_signal_private.calls(caller_id,callee_id,state,offer,created_at,updated_at,expires_at)values('11111111-1111-4111-8111-111111111111',(select id from sigurni_signal_private.members where nickname='Ana Nova'),'ended','{"type":"offer","sdp":"expired retention fixture"}',now()-interval '3 days',now()-interval '3 days',now()-interval '2 days');
insert into sigurni_signal_private.announcements(author_id,body,created_at)values('11111111-1111-4111-8111-111111111111','Old retention fixture',now()-interval '31 days');
insert into sigurni_signal_private.audit(actor_id,action,created_at)values('11111111-1111-4111-8111-111111111111','Old retention fixture',now()-interval '100 days');
insert into sigurni_signal_private.invites(token_hash,label,creator_id,expires_at)values(repeat('0',64),'Old retention fixture','11111111-1111-4111-8111-111111111111',now()-interval '31 days');
set local role anon;
select public.sigurni_signal_community(repeat('a',64),'snapshot','{}')->>'messages_version' as retention_poll_version;
reset role;
do $retention$ begin
 assert not exists(select 1 from sigurni_signal_private.messages where created_at<now()-interval '30 days');
 assert not exists(select 1 from sigurni_signal_private.calls where expires_at<now()-interval '1 day');
 assert not exists(select 1 from sigurni_signal_private.announcements where created_at<now()-interval '30 days');
 assert not exists(select 1 from sigurni_signal_private.audit where created_at<now()-interval '90 days');
 assert not exists(select 1 from sigurni_signal_private.invites where expires_at<now()-interval '30 days');
 assert (select last_cleanup=now() from sigurni_signal_private.housekeeping where id);
 raise notice 'Snapshot delta payloads and active-app hourly retention passed';
end $retention$;
do $catalog$ begin
 assert not has_schema_privilege('anon','sigurni_signal_private','USAGE');
 assert not has_table_privilege('anon','sigurni_signal_private.messages','SELECT');
 assert not has_table_privilege('authenticated','sigurni_signal_private.members','SELECT');
 assert not has_table_privilege('anon','sigurni_signal_private.backups','SELECT');
 assert not has_table_privilege('authenticated','sigurni_signal_private.backups','SELECT');
 assert (select bool_and(relrowsecurity and relforcerowsecurity)from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='sigurni_signal_private' and relkind='r');
 assert has_function_privilege('anon','public.sigurni_signal_community(text,text,jsonb)','EXECUTE');
 assert not exists(select 1 from pg_proc p,aclexplode(p.proacl) acl where p.oid='public.sigurni_signal_community(text,text,jsonb)'::regprocedure and acl.grantee=0 and acl.privilege_type='EXECUTE');
end $catalog$;
rollback;
