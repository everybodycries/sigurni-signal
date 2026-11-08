# Provjera objave 0.2.1

Objavljeno na https://sigurni-signal.pages.dev/ putem statičnog Cloudflare Pages projekta. Izvorni kod i Android APK dostupni su u GitHub izdanju https://github.com/everybodycries/sigurni-signal/releases/tag/v0.2.1-web .

Provjeren je HTTPS, sigurnosna zaglavlja, javna konfiguracija, hash javnog izvornog paketa i hash APK-a iz metapodataka GitHub imovine. Playwright je na javnoj domeni potvrdio kontrolu service workera, ponovno otvaranje bez interneta te zasebni offline priručnik na /guide.html i /guide. Ispravljena je poteškoća s preusmjeravanjem HTML adresa na hostingu.

48 Python testova, 11 web testova i izolirani PostgreSQL testovi pravila pristupa prošli su. Raniji Android APK nije izmijenjen; ovo izdanje nadograđuje web i distribuciju.

Supabase migracija i šifrirane sigurnosne kopije su pripremljene. Nijedan postojeći Supabase projekt nije promijenjen; čeka se korisnikov odabir projekta. Javni web trenutačno prikazuje nepovezani cloud. Nema automatske sinkronizacije niti javne registracije.

Lokalna mreža i LoRa trebaju električnu energiju iz baterija ili drugog izvora. Objavljena web aplikacija i cloud ne dokazuju rad radijskih uređaja, međugradske veze, dozvole ili traženu autonomiju.

## Supabase dodatak 0.2.2

Korisnik je odobrio smještaj u postojeći projekt. Povezan je AstroZeus kroz novu zasebnu tablicu, bez promjene postojećih tablica ili Auth postavki. Hosted RLS testovi (vlasnički CRUD i odbijanje drugog vlasnika) prošli su u rollback transakciji. Tablica nakon provjere ostaje prazna. Stvarna prijava korisničkim vjerodajnicama nije ispitana. Objavljen je samo publishable API ključ.

Objava 0.2.2 provjerena na javnoj domeni: konfiguracija, omogućena forma prijave, odbijen anonimni REST zahtjev (401), hash izvornog paketa te ponovno otvaranje aplikacije i priručnika bez interneta. Hosted tablica ostaje prazna nakon testova.

Advisor prijavljuje da je naziv/struktura tablice vidljiva prijavljenim korisnicima kroz GraphQL; to proizlazi iz potrebnog SELECT prava. Podaci su ograničeni vlasničkim RLS-om. [Objašnjenje advisora](https://supabase.com/docs/guides/database/database-linter?lint=0027_pg_graphql_authenticated_table_exposed). Postojeće nalaze za druge aplikacije nismo mijenjali.
