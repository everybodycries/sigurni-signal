-- Sigurni Signal optional encrypted backups. No existing tables/Auth settings are changed.
-- The client encrypts before upload; never store LoRa PSKs or automatically upload messages/GPS.
-- Abort on a pre-existing table instead of silently changing somebody else's schema.
create table public.sigurni_signal_backups (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  envelope jsonb not null,
  updated_at timestamptz not null default now(),
  constraint sigurni_signal_backup_envelope_shape check (
    jsonb_typeof(envelope) = 'object'
    and envelope ?& array['version','cipher','kdf','iterations','salt','iv','ciphertext']
    and envelope - array['version','cipher','kdf','iterations','salt','iv','ciphertext'] = '{}'::jsonb
    and envelope->'version' = '1'::jsonb
    and envelope->'cipher' = '"AES-256-GCM"'::jsonb
    and envelope->'kdf' = '"PBKDF2-SHA256"'::jsonb
    and envelope->'iterations' = '600000'::jsonb
    and jsonb_typeof(envelope->'salt') = 'string'
    and (envelope->>'salt') ~ '^[A-Za-z0-9+/]{22}==$'
    and jsonb_typeof(envelope->'iv') = 'string'
    and (envelope->>'iv') ~ '^[A-Za-z0-9+/]{16}$'
    and jsonb_typeof(envelope->'ciphertext') = 'string'
    and length(envelope->>'ciphertext') >= 24
    and length(envelope->>'ciphertext') % 4 = 0
    and (envelope->>'ciphertext') ~ '^[A-Za-z0-9+/]+={0,2}$'
  ),
  constraint sigurni_signal_backup_size check (octet_length(envelope::text) <= 500000)
);

comment on table public.sigurni_signal_backups is
  'Optional client-encrypted planner backup, one per authenticated owner. Not an emergency message transport; no cloud dependency for offline use.';
comment on column public.sigurni_signal_backups.envelope is
  'AES-256-GCM ciphertext envelope: version1, AES-256-GCM, PBKDF2-SHA256/600000,16-byte salt and12-byte IV, standard padded base64. Exact fields only. Passphrase never uploaded.';
comment on column public.sigurni_signal_backups.updated_at is
  'Client-supplied backup modification time; not proof of message receipt, authority or RF availability.';

alter table public.sigurni_signal_backups enable row level security;
alter table public.sigurni_signal_backups force row level security;
revoke all on table public.sigurni_signal_backups from public, anon, authenticated;
grant select, insert, update, delete on table public.sigurni_signal_backups to authenticated;

create policy sigurni_signal_backup_owner_only
  on public.sigurni_signal_backups
  for all to authenticated
  using (
    owner_id = (select auth.uid())
    and coalesce((select auth.jwt())->>'is_anonymous', 'false') = 'false'
  )
  with check (
    owner_id = (select auth.uid())
    and coalesce((select auth.jwt())->>'is_anonymous', 'false') = 'false'
  );
