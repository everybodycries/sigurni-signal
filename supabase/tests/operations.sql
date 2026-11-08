-- LOCAL ONLY, rollback leaves no fixture rows.
begin;
insert into sigurni_signal_private.members(id,key_hash,nickname,city,role) values
('11111111-1111-4111-8111-111111111111',encode(sha256(convert_to(repeat('a',64),'UTF8')),'hex'),'Ops Admin','Kragujevac','admin'),
('22222222-2222-4222-8222-222222222222',encode(sha256(convert_to(repeat('b',64),'UTF8')),'hex'),'Ops Member','Zagreb','member'),
('33333333-3333-4333-8333-333333333333',encode(sha256(convert_to(repeat('c',64),'UTF8')),'hex'),'Ops Other','Kragujevac','member');
set local role anon;
do $test$
declare snap jsonb; payload jsonb;
begin
 begin perform public.sigurni_signal_community(repeat('0',64),'ops_snapshot');raise exception 'invalid member admitted';exception when invalid_authorization_specification then null;end;
 begin perform count(*)from sigurni_signal_private.tasks;raise exception 'private table exposed';exception when insufficient_privilege then null;end;
 begin perform sigurni_signal_private.operations('11111111-1111-4111-8111-111111111111','ops_snapshot','{}');raise exception 'private function exposed';exception when insufficient_privilege then null;end;
 perform public.sigurni_signal_community(repeat('b',64),'profile','{"nickname":"Ops Member","city":"Kragujevac"}');
 perform public.sigurni_signal_community(repeat('b',64),'send','{"request_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","body":"Kragujevac test","room":"Kragujevac"}');
 snap:=public.sigurni_signal_community(repeat('a',64),'snapshot','{"room":"Kragujevac"}');assert snap#>>'{messages,0,body}'='Kragujevac test';
 perform public.sigurni_signal_community(repeat('b',64),'ops_checkin','{"status":"ready","note":"Rezervno napajanje dostupno"}');
 payload:='{"id":"aaaaaaaa-1111-4111-8111-111111111111","title":"Provera rezervnog napajanja","detail":"Logistički test","assignee_id":"22222222-2222-4222-8222-222222222222","city":"Kragujevac","priority":"priority"}';
 begin perform public.sigurni_signal_community(repeat('b',64),'ops_task_create',payload);raise exception 'member created task';exception when insufficient_privilege then null;end;
 perform public.sigurni_signal_community(repeat('a',64),'ops_task_create',payload);
 perform public.sigurni_signal_community(repeat('a',64),'ops_task_create',payload); -- idempotent duplicate
 snap:=public.sigurni_signal_community(repeat('b',64),'ops_snapshot');assert jsonb_array_length(snap->'tasks')=1;assert jsonb_array_length(snap->'roster')=3;
 assert public.sigurni_signal_community(repeat('b',64),'ops_snapshot',jsonb_build_object('known_version',snap->>'version'))->>'unchanged'='true';
 begin perform public.sigurni_signal_community(repeat('c',64),'ops_task_status','{"id":"aaaaaaaa-1111-4111-8111-111111111111","revision":1,"status":"completed"}');raise exception 'unassigned member changed task';exception when insufficient_privilege then null;end;
 perform public.sigurni_signal_community(repeat('b',64),'ops_task_status','{"id":"aaaaaaaa-1111-4111-8111-111111111111","revision":1,"status":"accepted"}');
 begin perform public.sigurni_signal_community(repeat('b',64),'ops_task_status','{"id":"aaaaaaaa-1111-4111-8111-111111111111","revision":1,"status":"completed"}');raise exception 'stale update accepted';exception when serialization_failure then null;end;
 perform public.sigurni_signal_community(repeat('b',64),'ops_task_status','{"id":"aaaaaaaa-1111-4111-8111-111111111111","revision":2,"status":"completed"}');
 payload:='{"id":"bbbbbbbb-1111-4111-8111-111111111111","name":"Voda","city":"Kragujevac","quantity":5,"minimum":20,"unit":"l","note":"Test","revision":0}';
 begin perform public.sigurni_signal_community(repeat('b',64),'ops_supply_save',payload);raise exception 'member changed stock';exception when insufficient_privilege then null;end;
 perform public.sigurni_signal_community(repeat('a',64),'ops_supply_save',payload);
 begin perform public.sigurni_signal_community(repeat('a',64),'ops_supply_save',payload);raise exception 'stale stock accepted';exception when serialization_failure then null;end;
 begin perform public.sigurni_signal_community(repeat('a',64),'ops_supply_save',payload||'{"revision":1,"quantity":-1}');raise exception 'negative stock accepted';exception when invalid_parameter_value then null;end;
 perform public.sigurni_signal_community(repeat('a',64),'ops_supply_save',payload||'{"revision":1,"quantity":30}');
 snap:=public.sigurni_signal_community(repeat('b',64),'ops_snapshot');assert snap#>>'{tasks,0,status}'='completed';assert (snap#>>'{supplies,0,quantity}')::numeric=30;
 raise notice 'PASS operations: Kragujevac profile+chat, authenticated roster, self check-in, task assignment/status/idempotence, owner enforcement, inventory admin rights, stale-write protection, negative stock rejection, private table/function isolation';
end;$test$;
reset role;
update sigurni_signal_private.members set active=false where id='22222222-2222-4222-8222-222222222222';
set local role anon;
do $test$begin begin perform public.sigurni_signal_community(repeat('b',64),'ops_snapshot');raise exception 'disabled member admitted';exception when invalid_authorization_specification then null;end;end;$test$;
rollback;
