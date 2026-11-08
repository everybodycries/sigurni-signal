# Supabase povezivanje — opcionalna sigurnosna kopija

Status 2026-11-08: korisnik je odobrio smještaj u postojeći projekt gdje ne smeta. Odabran je AstroZeus (`idgjvhuctieesmkyiwfl`). Dodana je samo tablica `public.sigurni_signal_backups` kroz migraciju. Postojeće tablice i Auth postavke nisu izmijenjene. Prisilni RLS, zabrana anon pristupa i vlasnički CRUD s odbijanjem drugog vlasnika potvrđeni su na hosted bazi u transakciji koja je rollbackana. Prijava stvarnim korisničkim vjerodajnicama nije testirana; koristi se postojeći aplikacijski račun, ne Supabase dashboard račun.

## Odabir projekta i postavljanje

1. Odabrati točan postojeći projekt. Integrator prvo provjerava njegove tablice i uvjete plana.
2. Pregledati `supabase/migrations/20261108061256_sigurni_signal_encrypted_backups.sql`. Dodaje samo `public.sigurni_signal_backups`; postojeće ime uzrokuje prekid, ne prepisivanje.
3. Nakon odobrenog postavljanja provjeriti RLS/policy/grants/constraints putem `supabase/tests/hosted_readonly.sql` i securityadvisors. Lokalni testovi već potvrđuju izolaciju dvaju korisnika u stvarnom PostgreSQL-u.
4. U javnu konfiguraciju aplikacije staviti samo URL projekta i publishableAPIključ. Nikad service_role, secretključ, SQLlozinku ili managementtoken.
5. Provjeriti registraciju/prijavu, korisnikovu vlastitu kopiju, odbijanje drugog korisnika te izričito preuzimanje/dešifriranje kopije. Browser-auth i hostedRLS testove navesti odvojeno od lokalnih.

Tablica sadrži vlasničkiUUID, šifriranu JSON omotnicu i vrijeme izmjene. Nema javnog čitanja. Aplikacija šifrira prije uploada koristeći korisnikovu zasebnu passphrase; ona ne ide u Supabase. Potrebni su HTTPS/securecontext i WebCrypto za taj dio. Lokalni priručnik i plan ostaju uporabivi bez prijave ili oblaka. Ne sinkroniziraju se automatski privatne poruke, radio ključevi ili GPS.

## Važna ograničenja besplatne usluge

Prema provjerenim uvjetima08.11.2026., Free uključuje do2aktivna projekta,500MB baze,1GBStorage,5GBegress i može pauzirati projekt nakon tjedan dana neaktivnosti. Ne postavljati lažne keepaliveposlove radi zaobilaženja pravila. Ne pretpostavljati neprekidnu dostupnost; pauza/quota/neuspjeli internet ne smiju blokirati lokalnu aplikaciju i BLE/LoRa komunikaciju.

Besplatni ugrađeni SMTP nije javna produkcijska pošta. Bez customSMTP-a Supabase šalje Auth poštu samo prethodno autoriziranim adresama članova projektnog tima, uz trenutačno ograničenje2poruke/sat i bez SLA-a. Postojeći projekt možda već ima svojSMTP/OAuth; to treba provjeriti prije obećanja registracije vanjskih korisnika. Ne isključivati potvrdu e-pošte, ne dodavati članove organizacije ili mijenjati tuđu e-poštu samo da registracija prividno proradi. Moguće besplatne alternative valja zasebno provjeriti i konfigurirati; slanje poruke nije izvedeno u sklopu ovih lokalnih testova.

## Što testovi dokazuju

Izolirani PostgreSQL16: ownerCRUD, nevidljivost tuđih redaka, odbijanje tuđih izmjena/brisanja, zabranjena promjena vlasnika, anon/anonymousdeny i provjera omotnice/veličine. TestnaAuthschema nije hosted Supabase. Svi testni korisnici i podaci bili su lokalni i vraćeni rollbackom; privremeni poslužitelj je ugašen. Nisu poslane poruke e-pošte ili promijenjene hostedusluge.

## Izvori

- [Supabase cijene i Free ograničenja](https://supabase.com/pricing)
- [RLS i ownerpolicies](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [PasswordAuth](https://supabase.com/docs/guides/auth/passwords)
- [SMTP ograničenja](https://supabase.com/docs/guides/auth/auth-smtp)
- [API ključevi](https://supabase.com/docs/guides/api/api-keys)

Detaljan wirecontract i ponovljiv lokalni test su u `supabase/README.md`.
