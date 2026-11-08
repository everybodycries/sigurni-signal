-- Safe read-only catalog verification after an explicitly authorized deployment.
select c.relname, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as rls_forced
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relname='sigurni_signal_backups';
select policyname, roles, cmd, qual, with_check
from pg_policies where schemaname='public' and tablename='sigurni_signal_backups';
select grantee,privilege_type from information_schema.role_table_grants
where table_schema='public' and table_name='sigurni_signal_backups'
order by grantee,privilege_type;
select conname,pg_get_constraintdef(oid) as definition from pg_constraint
where conrelid='public.sigurni_signal_backups'::regclass order by conname;
