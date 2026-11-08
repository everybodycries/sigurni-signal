-- Fix forward: invitation creators must remain active administrators at redemption.
-- Existing schema, member keys and Supabase Auth are unchanged.
create or replace function public.sigurni_signal_community(p_key text,p_action text,p_data jsonb default '{}'::jsonb)
returns jsonb
language plpgsql security definer set search_path=''
as $fn$
declare
 actor sigurni_signal_private.members%rowtype;
 invitation sigurni_signal_private.invites%rowtype;
 target_member sigurni_signal_private.members%rowtype;
 current_call sigurni_signal_private.calls%rowtype;
 existing sigurni_signal_private.messages%rowtype;
 v_peer uuid;
 v_id uuid;
 v_request uuid;
 v_room text;
 v_body text;
 v_name text;
 v_city text;
 v_hash text;
 v_role text;
 v_active boolean;
 v_json jsonb;
 v_messages jsonb;
 v_calls jsonb;
 v_self jsonb;
 v_directory jsonb;
 v_messages_version text;
 v_directory_version text;
begin
 if p_action is null or length(p_action)>40 or p_data is null or jsonb_typeof(p_data)<>'object' or octet_length(p_data::text)>100000 then
  raise exception using errcode='22023',message='Neispravan zahtjev.';
 end if;
 if p_action='join' then
  if coalesce(p_data->>'invite','') !~ '^[0-9a-f]{64}$' or coalesce(p_data->>'member_key','') !~ '^[0-9a-f]{64}$' then
   raise exception using errcode='28000',message='Pozivnica ili pristupni ključ nisu valjani.';
  end if;
  v_name:=btrim(p_data->>'nickname'); v_city:=p_data->>'city';
  if jsonb_typeof(p_data->'nickname') is distinct from 'string' or jsonb_typeof(p_data->'city') is distinct from 'string' or v_name is null or length(v_name) not between 2 and 40 or octet_length(v_name)>160 or v_name ~ '[[:cntrl:]]' or v_city is null or v_city not in('Zagreb','Sarajevo','Beograd') then
   raise exception using errcode='22023',message='Provjeri nadimak i grad.';
  end if;
  perform pg_advisory_xact_lock(633104,1);
  select * into invitation from sigurni_signal_private.invites
   where token_hash=encode(sha256(convert_to(p_data->>'invite','UTF8')),'hex') and used_at is null and expires_at>now()
   and exists(select 1 from sigurni_signal_private.members creator
    where creator.id=sigurni_signal_private.invites.creator_id and creator.active and creator.role='admin')
   for update;
  if not found then raise exception using errcode='28000',message='Pozivnica je istekla ili je već iskorištena.';end if;
  if (select count(*) from sigurni_signal_private.members where active)>=50 or (select count(*) from sigurni_signal_private.members)>=200 then raise exception using errcode='54000',message='Dosegnut je pilot limit od 50 članova.';end if;
  v_hash:=encode(sha256(convert_to(p_data->>'member_key','UTF8')),'hex');
  begin
   insert into sigurni_signal_private.members(key_hash,nickname,city) values(v_hash,v_name,v_city) returning * into actor;
  exception when unique_violation then raise exception using errcode='22023',message='Nadimak ili ključ je već upotrijebljen.';end;
  update sigurni_signal_private.invites set used_at=now(),used_by=actor.id where id=invitation.id;
  insert into sigurni_signal_private.audit(actor_id,action,target)values(actor.id,'member_joined',actor.id::text);
  return jsonb_build_object('self',jsonb_build_object('id',actor.id,'nickname',actor.nickname,'city',actor.city,'role',actor.role));
 end if;
 if p_key is null or p_key !~ '^[0-9a-f]{64}$' then raise exception using errcode='28000',message='Prijavi se pristupnim ključem.';end if;
 perform pg_advisory_xact_lock(633104,1);
 select * into actor from sigurni_signal_private.members where key_hash=encode(sha256(convert_to(p_key,'UTF8')),'hex') and active;
 if not found then raise exception using errcode='28000',message='Pristupni ključ nije valjan ili je pristup zaustavljen.';end if;
 v_self:=jsonb_build_object('id',actor.id,'nickname',actor.nickname,'city',actor.city,'role',actor.role);
 if p_action='login' then return jsonb_build_object('self',v_self);end if;
 if p_action='profile' then
  v_name:=btrim(p_data->>'nickname');v_city:=p_data->>'city';
  if jsonb_typeof(p_data->'nickname') is distinct from 'string' or jsonb_typeof(p_data->'city') is distinct from 'string' or v_name is null or length(v_name) not between 2 and 40 or octet_length(v_name)>160 or v_name ~ '[[:cntrl:]]' or v_city is null or v_city not in('Zagreb','Sarajevo','Beograd') then raise exception using errcode='22023',message='Provjeri nadimak i grad.';end if;
  begin update sigurni_signal_private.members set nickname=v_name,city=v_city where id=actor.id returning * into actor;
  exception when unique_violation then raise exception using errcode='22023',message='Taj je nadimak već zauzet.';end;
  return jsonb_build_object('self',jsonb_build_object('id',actor.id,'nickname',actor.nickname,'city',actor.city,'role',actor.role));
 end if;
 if p_action in('snapshot','send') then
  begin v_peer:=nullif(p_data->>'peer','')::uuid;exception when invalid_text_representation then raise exception using errcode='22023',message='Neispravan primatelj.';end;
  v_room:=coalesce(p_data->>'room','general');
  if v_peer is not null then
   if v_peer=actor.id or not exists(select 1 from sigurni_signal_private.members where id=v_peer and active) then raise exception using errcode='22023',message='Odabrani sugovornik nije dostupan.';end if;
   v_room:=null;
  elsif v_room not in('general','Zagreb','Sarajevo','Beograd') then raise exception using errcode='22023',message='Nepoznata soba.';
  end if;
 end if;
 if p_action='snapshot' then
  -- Retention advances only while an authorized application is active; no external cron.
  -- The existing application lock serializes this hourly timestamp and its bounded deletes.
  if (select last_cleanup from sigurni_signal_private.housekeeping where id)<now()-interval '1 hour' then
   delete from sigurni_signal_private.messages where created_at<now()-interval '30 days';
   delete from sigurni_signal_private.calls where expires_at<now()-interval '1 day';
   delete from sigurni_signal_private.announcements where created_at<now()-interval '30 days';
   delete from sigurni_signal_private.audit where created_at<now()-interval '90 days';
   delete from sigurni_signal_private.invites where expires_at<now()-interval '30 days';
   update sigurni_signal_private.housekeeping set last_cleanup=now() where id;
  end if;
  -- Expired signaling is never retained as a live call. SDP disappears on end/expiry.
  update sigurni_signal_private.calls set state=case when state='ringing' then 'missed' else 'ended' end,offer=null,answer=null,updated_at=now()
   where expires_at<=now() and (state in('ringing','accepted') or offer is not null or answer is not null);
  select coalesce(jsonb_agg(x order by x.created_at,x.id),'[]'::jsonb) into v_messages from (
   select m.id,m.request_id,m.sender_id,a.nickname as sender_name,m.recipient_id,m.room,m.body,m.redacted,m.created_at
   from sigurni_signal_private.messages m join sigurni_signal_private.members a on a.id=m.sender_id
   where m.created_at>now()-interval '30 days' and
    ((v_peer is null and m.recipient_id is null and m.room=v_room) or (v_peer is not null and ((m.sender_id=actor.id and m.recipient_id=v_peer)or(m.sender_id=v_peer and m.recipient_id=actor.id))))
   order by m.created_at desc,m.id desc limit 50
  )x;
  select coalesce(jsonb_agg(x),'[]'::jsonb) into v_calls from (
   select c.id,c.caller_id,c.callee_id,c.state,
    case when p_data->>'known_call'=c.id::text||':'||c.state then null else c.offer end as offer,
    case when p_data->>'known_call'=c.id::text||':'||c.state then null else c.answer end as answer,
    coalesce(p_data->>'known_call'=c.id::text||':'||c.state,false) as unchanged,
    c.created_at,c.expires_at
   from sigurni_signal_private.calls c where (c.caller_id=actor.id or c.callee_id=actor.id)
   and ((c.state in('ringing','accepted') and c.expires_at>now()) or c.updated_at>now()-interval '2 minutes')
   order by (c.state in('ringing','accepted')) desc,c.created_at desc,c.id desc limit 1
  )x;
  select coalesce(jsonb_agg(jsonb_build_object('id',m.id,'nickname',m.nickname,'city',m.city) order by m.nickname),'[]'::jsonb) into v_directory from sigurni_signal_private.members m where m.active;
  v_messages_version:=md5(v_messages::text);v_directory_version:=md5(v_directory::text);
  return jsonb_build_object('self',v_self,'server_time',now(),
   'messages',case when p_data->>'known_messages'=v_messages_version then null else v_messages end,
   'messages_version',v_messages_version,'calls',v_calls,
   'directory',case when p_data->>'known_directory'=v_directory_version then null else v_directory end,
   'directory_version',v_directory_version,
   'announcements',(select coalesce(jsonb_agg(x),'[]'::jsonb) from(select a.id,a.body,a.created_at,m.nickname as author from sigurni_signal_private.announcements a join sigurni_signal_private.members m on m.id=a.author_id order by a.created_at desc,a.id desc limit 10)x));
 end if;
 if p_action='send' then
  begin v_request:=(p_data->>'request_id')::uuid;exception when invalid_text_representation then raise exception using errcode='22023',message='Nedostaje valjana oznaka poruke.';end;
  v_body:=btrim(p_data->>'body');
  if jsonb_typeof(p_data->'body') is distinct from 'string' or v_request is null or v_body is null or length(v_body) not between 1 and 1500 or octet_length(v_body)>6000 or translate(v_body,chr(9)||chr(10)||chr(13),'') ~ '[[:cntrl:]]' then
   raise exception using errcode='22023',message='Poruka mora imati 1–1500 znakova bez kontrolnih znakova.';
  end if;
  perform pg_advisory_xact_lock(633104,hashtext(actor.id::text));
  select * into existing from sigurni_signal_private.messages where sender_id=actor.id and request_id=v_request;
  if found then
   if existing.body=v_body and existing.room is not distinct from v_room and existing.recipient_id is not distinct from v_peer then return jsonb_build_object('id',existing.id);end if;
   raise exception using errcode='22023',message='Oznaka već pripada drugoj poruci.';
  end if;
  if (select count(*) from sigurni_signal_private.messages where sender_id=actor.id and created_at>now()-interval '1 minute')>=20
    or (select count(*) from sigurni_signal_private.messages where sender_id=actor.id and created_at>now()-interval '1 day')>=300 then
   raise exception using errcode='54000',message='Dosegnut je limit slanja. Pričekaj prije nove poruke.';
  end if;
  -- Shared cap makes the pilot's storage bounded even under many members.
  perform pg_advisory_xact_lock(633104,2);
  if (select count(*) from sigurni_signal_private.messages)>=20000 then raise exception using errcode='54000',message='Pilot arhiva je puna; administrator treba pregledati pohranu.';end if;
  insert into sigurni_signal_private.messages(request_id,sender_id,recipient_id,room,body)values(v_request,actor.id,v_peer,v_room,v_body) returning id into v_id;
  return jsonb_build_object('id',v_id);
 end if;
 if p_action='call_start' then
  begin v_peer:=(p_data->>'peer')::uuid;exception when invalid_text_representation then raise exception using errcode='22023',message='Neispravan sugovornik.';end;
  v_json:=p_data->'offer';
  if v_peer is null or v_peer=actor.id or not exists(select 1 from sigurni_signal_private.members where id=v_peer and active) then raise exception using errcode='22023',message='Odaberi aktivnog sugovornika.';end if;
  if v_json is null or jsonb_typeof(v_json)<>'object' or v_json-array['type','sdp']<>'{}'::jsonb or v_json->>'type' is distinct from 'offer' or jsonb_typeof(v_json->'sdp') is distinct from 'string' or length(v_json->>'sdp') not between 1 and 40000 or octet_length(v_json::text)>50000 then raise exception using errcode='22023',message='Neispravni podaci poziva.';end if;
  perform pg_advisory_xact_lock(633104,3);
  if exists(select 1 from sigurni_signal_private.calls where state in('ringing','accepted') and expires_at>now() and (caller_id in(actor.id,v_peer)or callee_id in(actor.id,v_peer))) then raise exception using errcode='55000',message='Sugovornik ili ti već imate aktivan poziv.';end if;
  if (select count(*) from sigurni_signal_private.calls where caller_id=actor.id and created_at>now()-interval '1 hour')>=12 then raise exception using errcode='54000',message='Dosegnut je satni limit poziva.';end if;
  delete from sigurni_signal_private.calls where expires_at<now()-interval '1 day';
  update sigurni_signal_private.calls set state=case when state='ringing' then 'missed' else 'ended' end,offer=null,answer=null,updated_at=now() where expires_at<=now() and (offer is not null or answer is not null or state in('ringing','accepted'));
  if (select count(*) from sigurni_signal_private.calls)>=3000 then raise exception using errcode='54000',message='Arhiva poziva je puna.';end if;
  insert into sigurni_signal_private.calls(caller_id,callee_id,offer)values(actor.id,v_peer,v_json) returning * into current_call;
  return jsonb_build_object('call',jsonb_build_object('id',current_call.id,'caller_id',current_call.caller_id,'callee_id',current_call.callee_id,'state',current_call.state,'offer',current_call.offer,'answer',current_call.answer,'created_at',current_call.created_at,'expires_at',current_call.expires_at));
 end if;
 if p_action in('call_answer','call_end') then
  begin v_id:=(p_data->>'id')::uuid;exception when invalid_text_representation then raise exception using errcode='22023',message='Neispravna oznaka poziva.';end;
  select * into current_call from sigurni_signal_private.calls where id=v_id and (caller_id=actor.id or callee_id=actor.id) for update;
  if not found then raise exception using errcode='42501',message='Poziv nije dostupan ovom članu.';end if;
  if p_action='call_end' then
   if p_data->>'reason' not in('ended','declined') or p_data->>'reason' is null then raise exception using errcode='22023',message='Neispravna završna radnja.';end if;
   if p_data->>'reason'='declined' and (current_call.callee_id<>actor.id or current_call.state<>'ringing') then raise exception using errcode='42501',message='Samo primatelj može odbiti dolazni poziv.';end if;
   update sigurni_signal_private.calls set state=p_data->>'reason',offer=null,answer=null,updated_at=now(),expires_at=least(expires_at,now()) where id=v_id;
   return jsonb_build_object('ok',true);
  end if;
  if current_call.callee_id<>actor.id or current_call.state<>'ringing' or current_call.expires_at<=now() or not exists(select 1 from sigurni_signal_private.members where id=current_call.caller_id and active) then raise exception using errcode='42501',message='Poziv više nije dostupan za prihvat.';end if;
  v_json:=p_data->'answer';
  if v_json is null or jsonb_typeof(v_json)<>'object' or v_json-array['type','sdp']<>'{}'::jsonb or v_json->>'type' is distinct from 'answer' or jsonb_typeof(v_json->'sdp') is distinct from 'string' or length(v_json->>'sdp') not between 1 and 40000 or octet_length(v_json::text)>50000 then raise exception using errcode='22023',message='Neispravan odgovor poziva.';end if;
  update sigurni_signal_private.calls set answer=v_json,state='accepted',updated_at=now(),expires_at=now()+interval '60 minutes' where id=v_id returning * into current_call;
  return jsonb_build_object('call',jsonb_build_object('id',current_call.id,'caller_id',current_call.caller_id,'callee_id',current_call.callee_id,'state',current_call.state,'offer',current_call.offer,'answer',current_call.answer,'created_at',current_call.created_at,'expires_at',current_call.expires_at));
 end if;
 if p_action like 'admin_%' then
  if actor.role<>'admin' then raise exception using errcode='42501',message='Ova radnja traži administratora.';end if;
  perform pg_advisory_xact_lock(633104,1);
  -- Retention only affects this application's data and never other project tables.
  delete from sigurni_signal_private.messages where created_at<now()-interval '30 days';
  delete from sigurni_signal_private.calls where expires_at<now()-interval '1 day';
  delete from sigurni_signal_private.announcements where created_at<now()-interval '30 days';
  delete from sigurni_signal_private.audit where created_at<now()-interval '90 days';
  delete from sigurni_signal_private.invites where expires_at<now()-interval '30 days';
  if p_action<>'admin_snapshot' and (select count(*) from sigurni_signal_private.audit where actor_id=actor.id and created_at>now()-interval '1 minute')>=60 then raise exception using errcode='54000',message='Previše administratorskih promjena; pričekaj jednu minutu.';end if;
  if p_action='admin_snapshot' then
   return jsonb_build_object('members',(select coalesce(jsonb_agg(jsonb_build_object('id',m.id,'nickname',m.nickname,'city',m.city,'role',m.role,'active',m.active,'created_at',m.created_at) order by m.created_at),'[]'::jsonb) from sigurni_signal_private.members m),
    'invites',(select coalesce(jsonb_agg(x),'[]'::jsonb) from(select i.id,i.label,i.expires_at,i.used_at from sigurni_signal_private.invites i order by i.created_at desc limit 50)x),
    'audit',(select coalesce(jsonb_agg(x),'[]'::jsonb) from(select a.id,a.action,m.nickname as actor_name,a.target,a.created_at from sigurni_signal_private.audit a join sigurni_signal_private.members m on m.id=a.actor_id order by a.created_at desc,a.id desc limit 50)x),
    'stats',jsonb_build_object('members',(select count(*) from sigurni_signal_private.members where active),'messages',(select count(*) from sigurni_signal_private.messages),'calls',(select count(*) from sigurni_signal_private.calls)));
  elsif p_action='admin_revoke_invite' then
   begin v_id:=(p_data->>'id')::uuid;exception when invalid_text_representation then raise exception using errcode='22023',message='Neispravna pozivnica.';end;
   update sigurni_signal_private.invites set expires_at=least(expires_at,now()) where id=v_id and used_at is null;
   if not found then raise exception using errcode='22023',message='Neiskorištena pozivnica nije pronađena.';end if;
   insert into sigurni_signal_private.audit(actor_id,action,target)values(actor.id,'invite_revoked',v_id::text);
   return jsonb_build_object('ok',true);
  elsif p_action='admin_invite' then
   v_hash:=p_data->>'invite_hash';v_name:=btrim(p_data->>'label');
   if jsonb_typeof(p_data->'label') is distinct from 'string' or v_hash is null or v_hash !~ '^[0-9a-f]{64}$' or v_name is null or length(v_name) not between 1 and 80 or v_name ~ '[[:cntrl:]]' then raise exception using errcode='22023',message='Provjeri naziv i ključ pozivnice.';end if;
   if (select count(*) from sigurni_signal_private.invites where created_at>now()-interval '1 hour')>=20 or (select count(*) from sigurni_signal_private.invites where used_at is null and expires_at>now())>=50 then raise exception using errcode='54000',message='Dosegnut je limit pozivnica.';end if;
   insert into sigurni_signal_private.invites(token_hash,label,creator_id)values(v_hash,v_name,actor.id) returning id into v_id;
   insert into sigurni_signal_private.audit(actor_id,action,target)values(actor.id,'invite_created',v_id::text);
   return jsonb_build_object('id',v_id,'expires_at',now()+interval '7 days');
  elsif p_action='admin_member' then
   begin v_id:=(p_data->>'id')::uuid;exception when invalid_text_representation then raise exception using errcode='22023',message='Neispravan član.';end;
   v_role:=p_data->>'role';
   if v_role is null or v_role not in('admin','member') or jsonb_typeof(p_data->'active') is distinct from 'boolean' then raise exception using errcode='22023',message='Provjeri ulogu i pristup člana.';end if;
   v_active:=(p_data->>'active')::boolean;
   select * into target_member from sigurni_signal_private.members where id=v_id for update;
   if not found then raise exception using errcode='22023',message='Član nije pronađen.';end if;
   if v_id=actor.id and (not v_active or v_role<>'admin') then raise exception using errcode='42501',message='Ne možeš sam sebi oduzeti administratorski pristup.';end if;
   if target_member.active and target_member.role='admin' and (not v_active or v_role<>'admin') and (select count(*) from sigurni_signal_private.members where active and role='admin')<=1 then raise exception using errcode='42501',message='Mora ostati najmanje jedan aktivni administrator.';end if;
   if v_active and not target_member.active and (select count(*) from sigurni_signal_private.members where active)>=50 then raise exception using errcode='54000',message='Dosegnut je pilot limit od 50 aktivnih članova.';end if;
   update sigurni_signal_private.members set active=v_active,role=v_role where id=v_id;
   if not v_active then update sigurni_signal_private.calls set state='ended',offer=null,answer=null,updated_at=now(),expires_at=least(expires_at,now()) where state in('ringing','accepted') and(caller_id=v_id or callee_id=v_id);end if;
   insert into sigurni_signal_private.audit(actor_id,action,target)values(actor.id,'member_access_changed',v_id::text||':'||v_role||':'||v_active::text);
   return jsonb_build_object('ok',true);
  elsif p_action='admin_announcement' then
   v_body:=btrim(p_data->>'body');
   if jsonb_typeof(p_data->'body') is distinct from 'string' or v_body is null or length(v_body) not between 1 and 1500 or octet_length(v_body)>6000 or translate(v_body,chr(9)||chr(10)||chr(13),'') ~ '[[:cntrl:]]' then raise exception using errcode='22023',message='Obavijest mora imati 1–1500 znakova.';end if;
   if (select count(*) from sigurni_signal_private.announcements)>=1000 or (select count(*) from sigurni_signal_private.announcements where created_at>now()-interval '1 hour')>=20 then raise exception using errcode='54000',message='Dosegnut je limit obavijesti.';end if;
   insert into sigurni_signal_private.announcements(author_id,body)values(actor.id,v_body) returning id into v_id;
   insert into sigurni_signal_private.audit(actor_id,action,target)values(actor.id,'announcement_posted',v_id::text);
   return jsonb_build_object('id',v_id);
  elsif p_action='admin_redact' then
   begin v_id:=(p_data->>'id')::uuid;exception when invalid_text_representation then raise exception using errcode='22023',message='Neispravna poruka.';end;
   update sigurni_signal_private.messages set body='[Poruku je uklonio administrator]',redacted=true where id=v_id and recipient_id is null and not redacted;
   if not found then raise exception using errcode='42501',message='Samo se grupna poruka može moderirati.';end if;
   insert into sigurni_signal_private.audit(actor_id,action,target)values(actor.id,'group_message_redacted',v_id::text);
   return jsonb_build_object('ok',true);
  end if;
 end if;
 raise exception using errcode='22023',message='Nepoznata radnja.';
end;
$fn$;
revoke all on function public.sigurni_signal_community(text,text,jsonb) from public;
grant execute on function public.sigurni_signal_community(text,text,jsonb) to anon,authenticated;
comment on function public.sigurni_signal_community(text,text,jsonb) is
 'Sigurni Signal isolated capability-auth RPC. 256-bit keys in POST bodies, hashes only at rest. Private chat is server-stored, not end-to-end encrypted. No access to other applications or auth.users.';
