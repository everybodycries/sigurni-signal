# Admin, chat i glasovni pozivi — izdanje 0.4

## Pristup za vlasnika

Prvi administratorski pristupni ključ predaje se kao zasebna lokalna JSON datoteka izvan izvornog i javnog paketa. U aplikaciji otvorite **Chat i pozivi → Učitaj datoteku ključa**. Nakon uspješne prijave otvorite **Admin**. Ključ se ne sprema u preglednik; prijava u jednoj kartici traje do osam sati. Ako otvorite novu karticu, ponovno učitajte ključ.

Isti osobni ključ koristi se za zajednicu i nove šifrirane kopije plana. Prethodni Supabase Auth način s e-mailom ostaje zasebna dodatna mogućnost. Supabase nadzorna ploča i drugi projekti nisu potrebni članovima. Ova nadogradnja ne mijenja njihove Auth postavke.

## Dodavanje članova

1. Administrator u Admin panelu upisuje oznaku pozivnice i preuzima JSON datoteku.
2. Pozivnica se predaje namijenjenom članu; vrijedi sedam dana i samo jednu uporabu.
3. Član otvara Chat i pozivi, učitava pozivnicu, odabire ime i grad te pristupa zajednici.
4. Preglednik priprema osobni pristupni ključ za preuzimanje. Potreban je za sljedeću prijavu.
5. Administrator može opozvati neiskorištenu pozivnicu, isključiti ili ponovno uključiti člana i dodijeliti administratorsku ulogu. Ne može sam sebi oduzeti pristup; mora ostati aktivan administrator. Pozivnica deaktiviranog ili razriješenog administratora više ne vrijedi.

Maksimalno 50 aktivnih članova, 200 povijesnih računa. Ovo je ograničen pilot za planiranih30 korisnika, a ne javna neograničena društvena mreža.

## Chat

Odaberite grupni kanal (svi članovi ili grad) ili pojedinačnog člana za privatni razgovor. Svaka poruka ima najviše1500 znakova. Ponovljeno slanje istog zahtjeva ne stvara duplikat. Najviše20 poruka/minuti i300/dan po članu; arhiva je ograničena na20000 poruka.

Kroz aplikacijski API privatni razgovor mogu dohvatiti samo njegova dva člana. Administratorski panel nema pristup tuđim privatnim razgovorima; vlasnik baze ima tehnički pristup pohranjenom tekstu jer chat nije krajnje šifriran. U grupnim kanalima može ukloniti sadržaj poruke; članovi tada vide oznaku moderiranja. Administratorske obavijesti su objave članova zajednice, a ne službene institucionalne potvrde.

Poruke su šifrirane tijekom HTTPS prijenosa, ali tekst u bazi nije krajnje šifriran. Prikazuje se povijest posljednjih30 dana. Ovlaštena aktivna aplikacija najviše jednom na sat čisti starije poruke/obavijesti, istekle pozive i stare pozivnice; audit do90 dana. Kad je aplikacija neaktivna/pauzirana nema zasebnog jamstva izvršavanja čišćenja. Chat je neovisan o lokalnom LoRa imeniku i nacrtima; ne šalje radio, SMS ili zahtjeve službama.

## Pozivi

Glasovni poziv je između dva preglednika. Oba korisnika trebaju internet i otvorenu aplikaciju. Poziv se ne preusmjerava na telefonski broj, ne zvoni u zatvorenoj aplikaciji i nema automatskog javljanja.

- Odaberite člana i pritisnite Nazovi. Mikrofon se traži tek na taj klik.
- Primatelj vidi dolazni poziv i bira Prihvati ili Odbij. Dolazna obavijest sama ne uključuje mikrofon.
- Tijekom poziva može se isključiti/uključiti mikrofon i prekinuti poziv. Ako preglednik blokira reprodukciju, pritisnite Uključi zvuk sugovornika.
- Status „Poziv je povezan” nastaje tek kad stvarni WebRTC peer connection prijavi uspostavljenu vezu. Signaling ili prihvat nije dokaz prijenosa zvuka.
- Neprihvaćeni poziv istječe za45 sekundi; maksimalno trajanje je60 minuta; najviše12 započetih poziva po satu.
- WebRTC prenosi zvuk između sudionika; baza čuva samo kratkotrajne opise povezivanja (SDP). SDP se briše pri završetku/isteku. Nema funkcije snimanja zvuka.
- Ova instalacija koristi javni STUN za otkrivanje mreže. Dodatni TURN relej nije konfiguriran. Na nekim NAT/firewall/mobilnim mrežama izravni poziv može ne uspjeti. To se prikazuje kao neuspjeh; nema plaćenog rezervnog preusmjeravanja.

Radijskih i internetskih potvrda ne treba poistovjećivati s dolaskom pomoći. Za govor bez interneta projektni plan i dalje predviđa zasebne voki-tokije i vlastito napajanje.

## Tehnička izolacija i besplatna ograničenja

Podaci zajednice su u novoj privatnoj shemi `sigurni_signal_private`. Sve tablice imaju RLS i FORCE RLS te nemaju izravan pristup za anon/authenticated uloge. Jedini javni RPC provjerava slučajni256-bitni aplikacijski ključ i trenutačnu aktivnost/ulogu za svaku radnju. U bazi su samo SHA256 sažeci pristupnih ključeva i pozivnica. PUBLIC execute je opozvan, a dozvola RPC-a namjerno je dana API ulogama radi ovog zasebnog načina prijave. `search_path` je prazan; svi objekti su kvalificirani shemom. Nema oslanjanja na korisnički promjenjiv metadata za ovlasti.

Supabase advisor stoga informativno navodi privatne RLS tablice bez politike i upozorava na namjerno javno pozivljiv SECURITY DEFINER RPC. To nije oznaka da se preskače autorizacija: autorizacija je provjerena u funkciji i testovima. [RLS bez politike](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy), [anon RPC](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [authenticated RPC](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).

Povijest i mrežni opisi šalju se samo kad su promijenjeni. Vidljivi chat se provjerava otprilike svake4 sekunde, skrivena kartica sporije. Uloge/ključevi provjeravaju se i za nepromijenjeni sadržaj. Besplatni Supabase/Cloudflare limiti i moguća pauza ostaju granice dostupnosti; nije uključena naplata niti jamstvo neprekidnog rada.

Izvori: [WebRTC povezivanje i TURN](https://webrtc.org/getting-started/peer-connections), [pristup mikrofonu i HTTPS](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia), [Supabase funkcije](https://supabase.com/docs/guides/database/functions).

## Besplatni TURN relej

Pripremljen je Cloudflare Pages endpoint POST /api/turn. Prvo provjerava aktivni ključ člana preko Supabase RPC-a, a zatim na poslužitelju dohvaća kratkotrajne ICE vjerodajnice iz Metered/Open Relay API-ja. Privatni providerAPIkey ne vraća se pregledniku i ne ulazi u izvorni paket. Odgovori se ne spremaju u cache.

Račun se otvara osobnim podacima vlasnika i novom lozinkom. U korisnikovom računu provjeren je i aktiviran Free Trial Global:500MB mjesečno, zaustavljanje na limitu, never charged, bez uptime SLA. Opća Open Relay stranica oglašava drugačiju kvotu; za ovaj projekt vrijedi stvarna kvota prikazana u računu. Ne aktivirati plaćeni paket ili automatsku nadoplatu. Dok račun i dvije poslužiteljske tajne nisu postavljeni, endpoint za ovlaštenog člana vraća503configured:false, a poziv pokušava izravniSTUN način uz vidljivu poruku. To nije potvrda aktivnogTURN-a.

Tajne TURN_API_URL i TURN_API_KEY postavljaju se izvan javnog izvora. Lokalni operator može upisati {"apiUrl":"https://IME.metered.live/api/v1/turn/credentials","apiKey":"..."} u privatnu datoteku pa pokrenuti `python3 tools/configure_turn.py /put/do/privatne-datoteke.json`. Alat predaje vrijednosti Wrangleru krozstdin; ne stavljati ključ u argument komandne linije ili javni webconfig. Nakon toga ponovno objaviti Pages i potvrditi stvarni RTP preko relay kandidata.

Izvor besplatnog paketa i API-ja: https://www.metered.ca/tools/openrelay/ .
