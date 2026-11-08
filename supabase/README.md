# Optional encrypted planner backups

This directory is source only until a specific hosted project is selected and deployment is explicitly performed by the integration owner. It creates only `public.sigurni_signal_backups`; it does not alter existing tables or Auth settings.

Migration created with installed Supabase CLI2.90.0:

`migrations/20261108061256_sigurni_signal_encrypted_backups.sql`

The migration deliberately fails if that table already exists. Inspect existing tables first; do not replace the error with destructive drops or a broad migration reset. No paid project, branch or billing changes are needed.

## Client contract

One row per user:

```json
{
  "owner_id": "authenticated-user-uuid",
  "envelope": {
    "version": 1,
    "cipher": "AES-256-GCM",
    "kdf": "PBKDF2-SHA256",
    "iterations": 600000,
    "salt": "standard-base64-of-16-random-bytes",
    "iv": "standard-base64-of-12-random-bytes",
    "ciphertext": "standard-base64-of-ciphertext-and-GCM-tag"
  },
  "updated_at": "2026-11-08T00:00:00.000Z"
}
```

The `envelope` has exactly these7keys. `version` and `iterations` are JSON numbers. Salt uses24base64characters ending`==`; IV uses16base64characters with no padding. Ciphertext uses normal padded base64, not URL-safe base64. Envelope JSON serialized by Postgres must fit500000bytes; the web client further limits plaintext to64KiB. `updated_at` is a client timestamp, not an authority/receipt proof. No separate profile table, Storage bucket, Realtime publication or Edge Function is created.

Use a fresh random IV for each encryption and a fresh salt for each backup. Encryption passphrase is separate from account password, at least12characters in the client, never sent to Supabase. Losing it makes restore impossible. The local planner payload may include contacts/checklist/plan/settings, only after explicit upload; LoRa PSKs, private message history and automatic GPS uploads are out of scope. Schema validation cannot prove ciphertext was genuinely encrypted by a malicious client.

Only normal `authenticated` users can CRUD their own row via `owner_id = auth.uid()`. Both `USING` and `WITH CHECK` are present, so ownership cannot be reassigned. Supabase anonymous sign-in users also hold the authenticated role, so JWT`is_anonymous=true` is separately denied. `anon` and SQL`PUBLIC` have no table grants. No `user_metadata` authorization, privileged functions, triggers or RLS-bypassing views are added. `ON DELETE CASCADE` deletes the backup when its Auth owner is removed.

## Test evidence

`tests/local-results.txt` records an isolated PostgreSQL16 test: ownerCRUD, non-owner invisibility/update/delete isolation, forbidden owner reassignment/foreign insert, denied anon and authenticated-anonymous access, malformed/extra/null-KDF/null-cipher/oversize envelope rejection. Fixture inserts are rolled back. This tests real Postgres RLS with local equivalents of Supabase Auth helper functions; it is not a hosted Supabase or browser-auth end-to-end test.

Repeat with locally installed PostgreSQL binaries:

```sh
python3 supabase/tests/run_local.py
```

If necessary set`SIGURNI_PG_BIN=/path/to/postgresql/bin`. The runner creates a private temporary Unix-socket-only cluster, never connects to a hosted database and stops/removes it afterward. Do not run `local_auth_fixture.sql` against hosted Supabase. Do not run `rls.sql` on a hosted shared project without reviewing existing Auth user triggers and obtaining explicit authorization.

After deployment, `tests/hosted_readonly.sql` performs catalog-only inspection of RLS, policies, grants and constraints. Run project security advisors as well; preserve unrelated findings without modifying other applications.
