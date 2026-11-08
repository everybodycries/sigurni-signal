-- LOCAL TEST DATABASE ONLY: inserts two fixture auth.users in a rollback transaction.
-- Hosted projects may have user-insert triggers; do not run there without reviewing them.
begin;
insert into auth.users(id) values
 ('11111111-1111-4111-8111-111111111111'),
 ('22222222-2222-4222-8222-222222222222');

set local role authenticated;
select set_config('request.jwt.claims','{"sub":"11111111-1111-4111-8111-111111111111","role":"authenticated","is_anonymous":false}',true);
insert into public.sigurni_signal_backups(owner_id,envelope) values
 ('11111111-1111-4111-8111-111111111111',
  '{"version":1,"cipher":"AES-256-GCM","kdf":"PBKDF2-SHA256","iterations":600000,"salt":"AAAAAAAAAAAAAAAAAAAAAA==","iv":"AAAAAAAAAAAAAAAA","ciphertext":"AAAAAAAAAAAAAAAAAAAAAA=="}');

do $$ begin
  assert (select count(*) from public.sigurni_signal_backups)=1, 'owner cannot read own backup';
end $$;

update public.sigurni_signal_backups set updated_at = '2026-11-08T00:00:00Z'
 where owner_id = '11111111-1111-4111-8111-111111111111';

do $$ begin
  assert (select updated_at = '2026-11-08T00:00:00Z' from public.sigurni_signal_backups), 'owner update failed';
  begin
    update public.sigurni_signal_backups set owner_id='22222222-2222-4222-8222-222222222222';
    raise exception 'owner reassignment was allowed';
  exception when insufficient_privilege then null;
  end;
  begin
    insert into public.sigurni_signal_backups(owner_id,envelope)
    values ('22222222-2222-4222-8222-222222222222','{}');
    raise exception 'cross-owner insert was allowed';
  exception when insufficient_privilege then null;
  end;
end $$;

select set_config('request.jwt.claims','{"sub":"22222222-2222-4222-8222-222222222222","role":"authenticated","is_anonymous":false}',true);
do $$ declare changed integer; begin
  assert (select count(*) from public.sigurni_signal_backups)=0, 'non-owner read another backup';
  update public.sigurni_signal_backups set updated_at=now(); get diagnostics changed=row_count;
  assert changed=0, 'non-owner updated another backup';
  delete from public.sigurni_signal_backups; get diagnostics changed=row_count;
  assert changed=0, 'non-owner deleted another backup';
end $$;

-- Supabase anonymous sign-ins have the authenticated DB role; explicitly deny them.
select set_config('request.jwt.claims','{"sub":"11111111-1111-4111-8111-111111111111","role":"authenticated","is_anonymous":true}',true);
do $$ begin
  assert (select count(*) from public.sigurni_signal_backups)=0, 'anonymous-auth user read a backup';
  begin
    insert into public.sigurni_signal_backups(owner_id,envelope)
    values ('11111111-1111-4111-8111-111111111111','{}');
    raise exception 'anonymous-auth insert was allowed';
  exception when insufficient_privilege then null;
  end;
end $$;

reset role;
set local role anon;
select set_config('request.jwt.claims','{"role":"anon"}',true);
do $$ begin
  begin
    perform 1 from public.sigurni_signal_backups;
    raise exception 'anon read grant was present';
  exception when insufficient_privilege then null;
  end;
end $$;
reset role;
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"11111111-1111-4111-8111-111111111111","role":"authenticated","is_anonymous":false}',true);

do $$ begin
  begin
    update public.sigurni_signal_backups set envelope = envelope || '{"kdf":null}';
    raise exception 'null KDF accepted';
  exception when check_violation then null;
  end;
  begin
    update public.sigurni_signal_backups set envelope = envelope || '{"cipher":null}';
    raise exception 'null cipher accepted';
  exception when check_violation then null;
  end;
  begin
    update public.sigurni_signal_backups set envelope='{}';
    raise exception 'malformed envelope accepted';
  exception when check_violation then null;
  end;
  begin
    update public.sigurni_signal_backups set envelope = envelope || '{"plaintext":"private"}';
    raise exception 'extra plaintext field accepted';
  exception when check_violation then null;
  end;
  begin
    update public.sigurni_signal_backups set envelope = jsonb_set(envelope,'{ciphertext}',to_jsonb(repeat('A',500000)));
    raise exception 'oversized envelope accepted';
  exception when check_violation then null;
  end;
end $$;

delete from public.sigurni_signal_backups where owner_id='11111111-1111-4111-8111-111111111111';
do $$ begin assert (select count(*) from public.sigurni_signal_backups)=0, 'owner delete failed'; end $$;
rollback;
select 'PASS: owner CRUD, cross-owner isolation, owner reassignment denial, anon/anonymous denial, envelope and size checks; fixture transaction rolled back' as result;
