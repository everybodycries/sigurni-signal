-- Avoid repeatedly downloading unchanged member logistics on the free tier.
create or replace function sigurni_signal_private.operations(actor_id uuid,p_action text,p_data jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $ops$
declare
 actor sigurni_signal_private.members%rowtype;
 v_id uuid; v_owner uuid; v_city text; v_status text; v_title text; v_detail text; v_note text;
 v_version text;v_priority text;v_unit text;v_due timestamptz;v_quantity numeric;v_min numeric;v_revision integer;
 item sigurni_signal_private.tasks%rowtype;stock sigurni_signal_private.supplies%rowtype;
begin
 select * into actor from sigurni_signal_private.members where id=actor_id and active;
 if not found then raise exception using errcode='28000',message='Prijava nije važeća.';end if;
 if p_action='ops_snapshot' then
  select md5(concat_ws('|',
   (select coalesce(jsonb_agg(jsonb_build_array(m.id,m.nickname,m.city,m.role,m.active) order by m.id)::text,'') from sigurni_signal_private.members m),
   (select coalesce(jsonb_agg(jsonb_build_array(c.member_id,c.status,c.note,c.updated_at) order by c.member_id)::text,'') from sigurni_signal_private.checkins c),
   (select concat_ws(':',count(*),max(updated_at),sum(revision)) from sigurni_signal_private.tasks),
   (select concat_ws(':',count(*),max(updated_at),sum(revision)) from sigurni_signal_private.supplies))) into v_version;
  if p_data->>'known_version'=v_version then return jsonb_build_object('unchanged',true,'at',now(),'version',v_version);end if;
  return jsonb_build_object('version',v_version,'at',now(),'self_id',actor.id,'role',actor.role,
   'roster',(select coalesce(jsonb_agg(jsonb_build_object('id',m.id,'nickname',m.nickname,'city',m.city,'role',m.role,'status',c.status,'note',c.note,'updated_at',c.updated_at) order by m.city,m.nickname),'[]'::jsonb) from sigurni_signal_private.members m left join sigurni_signal_private.checkins c on c.member_id=m.id where m.active),
   'tasks',(select coalesce(jsonb_agg(t order by t.created_at desc),'[]'::jsonb) from sigurni_signal_private.tasks t),
   'supplies',(select coalesce(jsonb_agg(s order by s.city,s.name),'[]'::jsonb) from sigurni_signal_private.supplies s));
 end if;
 if (select count(*) from sigurni_signal_private.audit where audit.actor_id=actor.id and created_at>now()-interval '1 minute' and action like 'ops_%')>=20 then raise exception using errcode='54000',message='Previše izmena. Sačekaj jedan minut.';end if;
 if p_action='ops_checkin' then
  v_status:=p_data->>'status';v_note:=coalesce(p_data->>'note','');
  if v_status is null or v_status not in('ready','support','off_shift') or length(v_note)>240 or v_note ~ '[[:cntrl:]]' then raise exception using errcode='22023',message='Proveri stanje i napomenu (do 240 znakova).';end if;
  insert into sigurni_signal_private.checkins(member_id,status,note)values(actor.id,v_status,v_note)
   on conflict(member_id)do update set status=excluded.status,note=excluded.note,updated_at=now();v_id:=actor.id;
 elsif p_action='ops_task_status' then
  begin v_id:=(p_data->>'id')::uuid;v_revision:=(p_data->>'revision')::integer;exception when others then raise exception using errcode='22023',message='Neispravna oznaka zadatka.';end;
  select * into item from sigurni_signal_private.tasks where id=v_id for update;
  if not found then raise exception using errcode='22023',message='Zadatak ne postoji.';end if;
  if actor.role<>'admin' and item.assignee_id<>actor.id then raise exception using errcode='42501',message='Možeš ažurirati samo svoj zadatak.';end if;
  v_status:=p_data->>'status';
  if v_status is null or v_status not in('accepted','blocked','completed','cancelled') or (v_status='cancelled' and actor.role<>'admin') then raise exception using errcode='42501',message='Ta promena nije dozvoljena.';end if;
  if v_revision is distinct from item.revision then raise exception using errcode='40001',message='Zadatak je promenjen. Osveži tablu.';end if;
  if item.status in('completed','cancelled') and v_status<>item.status then raise exception using errcode='22023',message='Zatvoren zadatak se ne otvara ponovo; napravi novi.';end if;
  update sigurni_signal_private.tasks set status=v_status,revision=revision+1,updated_at=now() where id=v_id;
 elsif actor.role<>'admin' then raise exception using errcode='42501',message='Potreban je administrator.';
 elsif p_action='ops_task_create' then
  begin v_id:=(p_data->>'id')::uuid;v_owner:=(p_data->>'assignee_id')::uuid;v_due:=nullif(p_data->>'due_at','')::timestamptz;exception when others then raise exception using errcode='22023',message='Proveri člana i rok zadatka.';end;
  if v_id is null or v_owner is null then raise exception using errcode='22023',message='Nedostaje oznaka ili član.';end if;
  v_title:=btrim(p_data->>'title');v_detail:=coalesce(p_data->>'detail','');v_city:=p_data->>'city';v_priority:=p_data->>'priority';
  if v_title is null or length(v_title) not between 2 and 120 or v_title ~ '[[:cntrl:]]' or length(v_detail)>600 or v_detail ~ '[[:cntrl:]]' or v_city is null or v_city not in('Kragujevac','Zagreb','Sarajevo','Beograd') or v_priority is null or v_priority not in('routine','priority') then raise exception using errcode='22023',message='Proveri podatke zadatka.';end if;
  if not exists(select 1 from sigurni_signal_private.members where id=v_owner and active) then raise exception using errcode='22023',message='Odabrani član nije aktivan.';end if;
  select * into item from sigurni_signal_private.tasks where id=v_id;
  if found then
   if item.creator_id=actor.id and item.title=v_title and item.detail=v_detail and item.assignee_id=v_owner and item.city=v_city and item.priority=v_priority and item.due_at is not distinct from v_due then return jsonb_build_object('ok',true,'id',v_id);end if;
   raise exception using errcode='22023',message='Oznaka zadatka je već upotrebljena.';
  end if;
  if (select count(*) from sigurni_signal_private.tasks)>=1000 then raise exception using errcode='54000',message='Dostignut je pilot limit od 1000 zadataka.';end if;
  insert into sigurni_signal_private.tasks(id,title,detail,city,assignee_id,creator_id,priority,due_at)values(v_id,v_title,v_detail,v_city,v_owner,actor.id,v_priority,v_due);
 elsif p_action='ops_supply_save' then
  begin v_id:=(p_data->>'id')::uuid;v_revision:=(p_data->>'revision')::integer;v_quantity:=(p_data->>'quantity')::numeric;v_min:=(p_data->>'minimum')::numeric;exception when others then raise exception using errcode='22023',message='Proveri brojčane podatke zalihe.';end;
  v_title:=btrim(p_data->>'name');v_city:=p_data->>'city';v_unit:=btrim(p_data->>'unit');v_note:=coalesce(p_data->>'note','');
  if v_id is null or v_title is null or length(v_title) not between 2 and 80 or v_title ~ '[[:cntrl:]]' or v_city is null or v_city not in('Kragujevac','Zagreb','Sarajevo','Beograd') or v_unit is null or length(v_unit) not between 1 and 24 or v_unit ~ '[[:cntrl:]]' or length(v_note)>240 or v_note ~ '[[:cntrl:]]' or v_quantity is null or not(v_quantity between 0 and 1000000) or v_min is null or not(v_min between 0 and 1000000) then raise exception using errcode='22023',message='Proveri naziv, grad, jedinicu i količinu (0–1000000).';end if;
  select * into stock from sigurni_signal_private.supplies where id=v_id for update;
  if found then
   if v_revision is distinct from stock.revision then raise exception using errcode='40001',message='Zaliha je promenjena. Osveži tablu pre izmene.';end if;
   update sigurni_signal_private.supplies set name=v_title,city=v_city,unit=v_unit,note=v_note,quantity=v_quantity,minimum=v_min,revision=revision+1,updated_by=actor.id,updated_at=now() where id=v_id;
  else
   if v_revision is distinct from 0 then raise exception using errcode='40001',message='Zaliha nije pronađena. Osveži tablu.';end if;
   if (select count(*) from sigurni_signal_private.supplies)>=500 then raise exception using errcode='54000',message='Dostignut je pilot limit od 500 zaliha.';end if;
   insert into sigurni_signal_private.supplies(id,name,city,unit,note,quantity,minimum,updated_by)values(v_id,v_title,v_city,v_unit,v_note,v_quantity,v_min,actor.id);
  end if;
 else raise exception using errcode='22023',message='Nepoznata radnja.';
 end if;
 insert into sigurni_signal_private.audit(actor_id,action,target)values(actor.id,p_action,v_id::text);
 return jsonb_build_object('ok',true,'id',v_id);
end;$ops$;
revoke all on function sigurni_signal_private.operations(uuid,text,jsonb) from public,anon,authenticated;
