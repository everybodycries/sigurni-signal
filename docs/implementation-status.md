# Stanje implementacije — 08.11.2026.

Isporuka je softverski pilot za provjeru, s izgrađenim Android APK-om. Stvarni radijski pilot nije aktiviran.

| Zahtjev | Dokaz | Status |
|---|---|---|
| Native Android Kotlin/Compose, BLE/Protobuf, Keystore, red, karte i vodiči | Gradle `testDebugUnitTest assembleDebug` uspješan; Android JVM7/7 | Kompilacija potvrđena |
| APK potpis | Android apksigner: `Verifies`, APKsignaturev2,1signer | Potvrđeno; debug/test potpis |
| Bazna SQLite logika, HTTP i stvarni SDK ugovor |38/38unittest s opcionalnimSDK2.7.11, bez preskakanja | Potvrđeno softverskim testovima |
| CSV evaluator, datumi/termini i proračun |15/15unittest | Potvrđeno softverskim testovima |
| Lokalna pohrana poruke i odvojeni status | Playwright: pregled/suglasnost, spremanje u red bez radija, prikaz Spremljeno | Potvrđeno u pregledniku |
| Javni radiogram i HF blokada | Playwright: točan tekst i izričita suglasnost, odobrenje disabled bez dokaza | Potvrđeno u pregledniku |
| Šest offline vodiča | Integritet i struktura provjereni; Playwright šest lokalnih vodiča | Sadržaj dostupan; stručni pregled nije potvrđen |
| Stvarni Android/iPhone, BLE radio i pozadinski prijam | Nema dostupnog uređaja/radija/emulatora; instrumentation nisu pokrenuti | Neprovjereno |
| Offline karte i skloništa | Podrška pripremi licenciranog MapLibre paketa; pločice nisu uključene, točke prazne | Nije pripremljeno ni terenski potvrđeno |
| HR/BA/RS dozvole, dostupni operateri i lokacije | Prazni obrasci;12HF uvjeta početno nedostaje | Blokirano za aktivaciju |
| Domet,95%lokalnih/90%međugradskih i72h/48h |540praznih lokalnih,270praznih međugradskih zapisa; mjerenja nisu izvedena | Neprovjereno |
| iPhone podrška | Postupak za službeni besplatni Meshtastic + spremljeni priručnik | Dokumentirano, nije vlastita iOS aplikacija |

Ukupno60automatiziranih testova prošlo:38baznih/SDK +15terenskih alata/kalkulatora +7AndroidJVM. Ti testovi nisu60terenskih radijskih pokusa.

## Pregled i ispravci

Neovisni pregled bazne logike pronašao je skrivanje starog otvorenog zahtjeva nakon500novih poruka; ispravljeno je zadržavanjem svih otvorenih zahtjeva i punim izvozom. Evaluator je mogao spojiti različite dane ili prihvatiti pogrešan termin; sada provjerava08/14/20, dane1–3, datum i vremenski prozor. Dodatni testovi potvrđuju da ručno zatvaranje prekida buduća slanja i da potvrđene poruke ne pune aktivni red. Android read-drain model ima test za obavijest tijekom već pokrenutog praznog BLE čitanja. Pronađene MapLibre nullability greške popravljene su prije uspješne izgradnje.

## Ograničenja i postavke

Slanje na USB početno je isključeno. Bez serijskog puta nema radijske veze; nema simuliranog uspjeha. Privatni primarni kanal/profil/MQTT provjeravaju se iz prijavljenih postavki, ne predstavljaju pravno odobrenje. Radio ACK i tvrdnja POTVRDA ne postaju ljudska potvrda. HF je isključivo operaterski postupak; nema funkcije za automatsko HF emitiranje. Nije kupljena oprema, kontaktiran operater, poslana vanjska poruka ili aktivirana služba.

U baznoj konzoli SQLite je zaštićen dozvolama OS-a, a ne enkripcijom cijele baze. Android šifrira sadržaj, ali metapodaci ostaju. Prije uporabe pripremiti zaštićen račun/disk i sigurnosne kopije. Članovi privatnog kanala nisu time službeno identificirani. Vodiči su pripremne parafraze s izvorima, ne službena upozorenja ili terapija.

Zbog iCloud evikcije i ograničenja diska konačna isporuka čuva se u direktoriju `.nosync`. Radne stare mape nisu dio ZIP-a. Izvori i APK u ovoj isporuci usklađeni su s uspješnom izgradnjom; ključevi za potpisivanje nisu uključeni.

## Ponovljiva provjera

Iz korijena izvornog paketa:

```
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s docs -p 'test_*.py' -v
python3 docs/verify_content.py
node --check station/static/app.js
```

SDK ugovorni testovi preskaču se ako SDK nije instaliran. Za korišteni rezultat instaliran je službeni Meshtastic2.7.11. Android upute su u android/README.md. Izvještaji su station-test-results.txt, field-test-results.txt, android-jvm-tests.xml i zapisi Gradle izgradnje. Izvorni ZIP isključuje APK, build-cache, bazu i privatne ključeve; APK je zasebna datoteka.
