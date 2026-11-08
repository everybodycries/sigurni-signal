# Sigurni Signal — web 0.2 i Android pilot 0.1

Nadogradnja uključuje instalabilni web s lokalnim planom, offline priručnikom, pripremom radijskih nacrta, šifriranim izvozom i pripremljenim Supabase povezivanjem. Web nije radioodašiljač. Android APK zadržava vlastiti provjereni pilot build i odvojenu verziju0.1.

- Javni web: https://sigurni-signal.pages.dev (adresu potvrditi u docs/deployment-status.json nakon objave).
- Android i izvorni release: https://github.com/527bcyxhtg-web/sigurni-signal/releases/tag/v0.2.0-web
- Lokalni javni web: `python3 -m gateway.server` → http://127.0.0.1:8088 ; eksplicitniLAN: `python3 -m gateway.server --lan`.
- Privatna bazna konzola ostaje odvojena: upute ispod. Ne izlagati je javnom internetu.
- Supabase je neobvezan; aktivno povezivanje čeka odabir postojećeg projekta. Nije stvoren plaćeni projekt niti promijenjenAuth.

Detalji: [web nadogradnja](docs/web-upgrade.md), [vlastita mreža](docs/offgrid-deployment.md), [Supabase](docs/supabase-setup.md). Sve mreže trebaju energiju; baterije/solar i radijski domet zahtijevaju stvarnu provjeru.

## Pokretanje baze

Potreban je Python3.9 ili noviji. Konzola bez stvarnog USB radija radi samo sa standardnom bibliotekom. Na Macu otvorite `start-station.command`, ili u ovom direktoriju pokrenite:

```sh
python3 -m station.server --port 18765 --db ../../work/station-data.nosync/station.sqlite3
```

Otvorite http://127.0.0.1:18765 na istom računalu. Konzola sluša samo127.0.0.1; nema oblaka, računa ili obvezne internetske usluge. Ctrl+C zaustavlja proces. Podaci se spremaju u lokalnu SQLite bazu; odabrana `.nosync` mapa na Macu izbjegava iCloud sinkronizaciju. Nema mobilnog SMS-a ili automatskog kontakta112.

Za stvarni radio prije događaja pripremite virtualno okruženje i službeni SDK:

```sh
python3 -m venv ../../work/station-venv.nosync
../../work/station-venv.nosync/bin/python -m pip install -r requirements-radio.txt
../../work/station-venv.nosync/bin/python -m station.server --port 18765 --db ../../work/station-data.nosync/station.sqlite3 --serial /dev/ttyACM0
```

Na Macu odaberite stvarni `/dev/cu.usb…` put. Radio se ne traži automatski. Službenim klijentom unaprijed konfigurirajte provjeren lokalno dopušten profil, privatni primarni kanal0 i isključite MQTT/uplink/downlink. Ograničenje emitiranja ostaje uključeno. Konzola čita profil; blokira slanje za neprovjeren profil, javni ključ i internetsko prosljeđivanje. EU_868 je kandidat, nije pravna potvrda. U Oprema i kontakti izričito omogućite lokalni red uz operatera i referencu provjere. Početno je slanje isključeno.

## Android

Instalirajte `sigurni-signal-pilot.apk` prije događaja. To je uspješno izgrađen i provjereno potpisan **debug/pilot APK**, ne produkcijsko izdanje. Dodatni LoRa radio je obvezan za LoRa komunikaciju. Dopustite Bluetooth, odaberite radio i pregledajte lokalni profil prije omogućavanja reda. Jedan klijent upravlja radiom; službeni klijent treba odspojiti. Upute i izvorni kod: `android/README.md`.

Na iPhoneu pilot koristi postojeću besplatnu službenu Meshtastic aplikaciju i unaprijed spremljene dokumente. Nema vlastite objedinjene iOS aplikacije. Upute: `docs/iphone-priprema.md`.

## Ponašanje poruka

Najviše200UTF-8bajtova s oznakom `[A7K42P9Q] `. Normalni rok slanja24h, pomoć1h; najviše početni i dva dodatna pokušaja. Osobna potvrda odvojena je od radijskog ACK-a i tekstualne tvrdnje `POTVRDA ID`. Neizvjesno slanje nakon prekida traži pregled. Istek ne zatvara pomoć. Zatvaranje zahtjeva zaustavlja buduće pokušaje, ali već predanu poruku ne opoziva iz zraka. Otvoreni zahtjevi ostaju vidljivi i uz mnogo novih poruka.

Međugradski radiogram je zaseban točan javni tekst s izričitom suglasnošću. Operater evidentira provjeru i ručni prijenos; aplikacija ne upravlja HF odašiljačem. Svi uvjeti za propise, operatere, lokacije i izmjerene veze početno su neispunjeni. Unos dokaza je operaterova evidencija, ne automatska pravna potvrda.

## Offline sadržaj i provjera

`docs/prirucnik-offline.html` je samostalni priručnik bez mrežnih resursa, pogodan za ispis/PDF iz preglednika. Šest vodiča ima navedene izvore i status pregleda. Nema izmjerenog zračenja, doza joda, odbrojavanja do sigurnog izlaska, potvrđenih skloništa ili ruta kroz fallout.

`docs/templates/` sadrži prazne RF, naponske, operaterske, nabavne i uređajne obrasce. Prazni predlošci nisu rezultati. Kalkulator i evaluator provjeravaju unesene brojeve/zapise, ne njihovu autentičnost ili zakonitost.

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s docs -p 'test_*.py' -v
python3 docs/verify_content.py
python3 docs/evaluate_field.py local docs/templates/local-rf.csv
python3 docs/evaluate_field.py intercity docs/templates/intercity-rf.csv
```

SDK ugovorni testovi preskaču se ako opcionalni SDK nije instaliran. Za isporučenu provjeru instaliran je Meshtastic2.7.11 i nisu preskočeni. Stanje i dokazi: `docs/implementation-status.md`.

## Pohrana i licence

Bazna SQLite datoteka ima OS dozvole0600, nije punom enkripcijom baze zaštićena od prijavljenog korisnika. Za pilot koristiti zaštićen račun i šifrirani disk. Android šifrira sadržaj/nazive pomoću Keystorea; rutni identifikatori, vrijeme i stanja ostaju metapodaci. Android backup je isključen. Gubitak Keystore ključa može značiti gubitak čitljivosti lokalne povijesti.

GPL-3.0-only za novi kod; upstream licence i atribucije su u LICENSE, THIRD_PARTY.md i Android izvornicima. Nema kupljene opreme ili aktiviranog radijskog pilota. Stvarne veze, rad na telefonima, dozvole i autonomija tek moraju biti dokazani.
