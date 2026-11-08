# Web 0.2: besplatan javni portal i vlastita lokalna mreža

Javni portal je statička PWA: lokalni plan, imenik, priprema kratkih nacrta za radio, vodiči, preuzimanja, proračun napajanja i šifrirane kopije. Ne šaljeLoRa/SOS, ne kontaktira112 i ne tvrdi da je nacrt dostavljen. Stvarni radijski sloj ostaje Androidpilot0.1/Meshtastic i lokalna bazna konzola.

## Objavljivanje bez pretplate

CloudflarePages pruža besplatnu *.pages.dev adresu sHTTPS-om; koristi se samo statički sadržaj, bez plaćenih Functions/R2 ili kupnje domene. Ograničenje25MiB po datoteci znači da se AndroidAPK preuzima preko GitHubReleases, a ne iz Pages pohrane. GitHub javniGPLizvor i releaseassets ne traže pretplatu. SupabaseFree ima500MB baze,2aktivna projekta i može se pauzirati nakon tjedan dana neaktivnosti. Nema plaćenog fallbacka niti zaobilaženja mirovanja automatiziranim pingovima.

Izvori provjereni08.11.2026: https://developers.cloudflare.com/pages/platform/limits/ ; https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases ; https://supabase.com/pricing . Uvjeti se mogu promijeniti; prije proširenja provjeriti stvarnu potrošnju i plan računa.

## Priprema za rad bez interneta

Prvo otvoriti HTTPS portal, pričekati Spremljeno i po želji dodati na početni zaslon. Isključiti internet i provjeriti ponovno otvaranje, plan i vodiče. PWA sprema samo aplikacijski sadržaj; APK/izvorniZIP treba zasebno preuzeti. Browser može ukloniti pohranu pri nedostatku prostora. Postoji šifrirani izvoz plana; čuvati ga izvan uređaja i frazu odvojeno.

Lokalni plan u IndexedDB nije potpuni šifrirani sef. Šifrirana datoteka/Supabasekopija koristeAES-256-GCM,PBKDF2-SHA256/600000 i zasebnu frazu. Kopija sadrži kontakte, pripremu i obiteljski dogovor; ne sadrži nacrte, radijske ključeve niGPS. Lozinka računa i fraza nisu isto. Fraza se ne sprema niti šalje poslužitelju. Prijavni token ostaje samo u memoriji kartice; nema automatske sinkronizacije.

## Supabase

Kôd i vlasničkaRLSpravila spremni su u supabase/. Stvarnu bazu nije dopušteno odabrati napamet između postojećih projekata. Organizacija ima2aktivna projekta naFreeplanu; novi nije stvoren, nijedan postojeći nije pauziran. Do korisnikova odabira javna konfiguracija ima supabase:null; lokalne funkcije i šifrirane datoteke rade.

Nakon odabira: pregled postojeće sheme, primjena jedne prefiksirane tablice, stvarnaRLSprovjera, publishablekey uweb/config.json i novo izdanje. Service-role/secret ključ nikad ne ide u web. Javna registracija nije uključena: zadaniSMTP ima ograničenja, postojećaAuthkonfiguracija nije promijenjena. Račun aplikacije nije isto što i račun za SupabaseDashboard. Detalji u supabase-setup.md.

## Vlastiti odvojeni dio mreže

Pokrenuti `python3 -m gateway.server` za lokalno čitanje ili eksplicitni `--lan` za izoliraniLAN. Poslužuje samoweb/, bez privatnogstationAPI-ja ili baza. Ethernet ili lokalniWi-Fi mogu raditi bezWANveze; sami uređaji trebaju baterije. LoRa je sloj kratkih poruka, ne širokopojasni internet. LokalniHTTP na tuđojIPadresinema puni sigurniPWA/WebCryptokontekst: ne upisivati lozinke; šifriranje/prijava su isključeni. PripremitiPWAprekoHTTPS-a unaprijed. Upute i fizički testovi u offgrid-deployment.md.

Nije implementiran internet bez energije niti dokazana gradska pokrivenost. Potrebne su stvarne dozvole, operateri, uređaji, trase i mjerenja72h/48h.

## Obnova javnog paketa

`python3 tools/build_web.py` priprema isključivo statičke resurse iSWcache. `python3 tools/package_release.py` radi javni izvorniZIP i web/downloads/source.zip; APK je zaseban. Ponovno provjeriti privatne podatke iSHA256prije objave. IzvorniAPK treba biti dostupan lokalno ili konfigurirani nativeSha256mora već biti provjeren. CLIautorizacije, privatni ključevi i radne baze nisu dio izdanja.
