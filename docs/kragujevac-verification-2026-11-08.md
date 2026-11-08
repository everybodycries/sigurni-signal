# Provera izdanja 0.5.0 — 8. novembar 2026.

## Dogovoreni rezultat

Terenska koordinacija i logistika na srpskoj latinici. Kragujevac je početni grad novog lokalnog plana i glavni centar; Zagreb je povezana baza. Stari gradovi, lični ključevi, pozivnice, razgovori i rezervne kopije ostaju kompatibilni. Lični profil i grad ranije sačuvanog plana nisu automatski izmenjeni.

## Izvedeno i provereno

- Aktivna privatna logistika: ručno lično javljanje, gradski imenik timova, zadaci sa odgovornim članom/prioritetom/rokom, stanje prihvaćeno/zastoj/završeno/otkazano i popis zaliha sa minimumima.
- Kragujevac prihvaćen u novoj prijavi, izmeni profila i gradskom chatu; provereno preko stvarnog Supabase RPC-a i testnih članova.
- Administratorske mutacije i vlasništvo zadatka proveravaju se na serveru; privatna pomoćna SQL funkcija nije direktno dostupna API ulogama. Proverene RLS/FORCE RLS i nedostatak anonimnih tabelarnih privilegija na sve tri nove tabele.
- Revizije sprečavaju prepisivanje novijeg stanja. Ponovljena identična dodela ne pravi novi zadatak. Nevažeći ključevi, deaktivirani članovi, negativne količine i tuđi zadaci su odbijeni.
- Osvežavanje table na 30 sekundi u otvorenom prikazu šalje samo verziju i vreme kada se podaci nisu promenili. Podaci nisu zapisani u lokalne keševe.
- 52 Node testa: svi prošli. Python: 48 pokrenuto, 46 prošlo i 2 preskočena jer opciona Meshtastic biblioteka nije instalirana. Dokumentacija: 15 prošlo. Ukupno 113 prošlo, 2 preskočeno. Izolovane PostgreSQL integracione tvrdnje za prethodne i nove mogućnosti su dodatno prošle.
- Stvarni Chrome: administrator dodeljuje logistički zadatak i popisuje zalihu, član iz Kragujevca potvrđuje stanje, prihvata i završava zadatak; Zagreb pristupa preko iste postojeće strukture pozivnica. Testni sadržaj i korisnici uklonjeni po završetku.
- Svih 11 stranica provereno na 320, 390 i 1440 piksela bez horizontalnog prelivanja. Proveren izostanak grešaka JavaScripta, skrivanje administracije članu, čišćenje podataka pri odjavi, učitavanje plana posle offline ponovnog otvaranja i početni grad Kragujevac.
- Postojeći TURN endpoint ostaje odvojen od keša i provider ključ ostaje samo na serveru. Granica paketa ostaje 500 MB mesečno sa hardstopom bez naplate. Prethodni v0.4.1 forsirani RTP relay dokaz ostaje istorijski dokaz; ovo izdanje ne tvrdi novi test razgovora na fizičkim telefonima.

## Pozivnice

Privatni paket sadrži 6 Kragujevac + 6 Zagreb. Šest neiskorišćenih ranije sarajevskih pozivnica je preraspoređeno Kragujevcu, bez novog izdavanja ključeva; zagrebačke su iste kao ranije. Rok ostaje 15. novembar 2026. oko 15:00 po lokalnom vremenu. Administrator ne treba da deli isti pristup različitim osobama iz starog i novog paketa. Sadržaj privatnog paketa nije u javnom izvoru ili hostingu.

## Preostale granice

- Android izvor uključuje Kragujevac, srpsku latinicu i početni centar mape. Pokušaj izgradnje bez novih preuzimanja nije uspeo: nedostaje keširani com.android.application Gradle plugin 9.0.1, a Android SDK nije pronađen. Nema novog APK-a, potpisa ili ponovo potvrđenih JVM testova. Preuzimanje ostaje jasno označen prethodni APK 0.1.0-pilot. Za novu logistiku koristi se web/PWA.
- Radijska veza Kragujevac–Zagreb, stvarni telefoni/BLE, dozvole, zračenje i naponska autonomija nisu dokazani softverskim testovima. Nema vojne sertifikacije, garancije tajnosti chata ili akreditacije za poverljive podatke.
- Izvorni stručni priručnici zadržani su bez automatske izmene zdravstvenih preporuka; lokalni stručni pregled ostaje otvoren.

## Supabase bezbednosni savetnik

Nove privatne tabele namerno imaju RLS bez dozvoljavajućih politika — direktan pristup je zabranjen ([objašnjenje](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy)). Postojeći javni capability RPC je namerno dostupan API ulogama uz obaveznu proveru ličnog ključa za svaku zaštićenu radnju ([anon upozorenje](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [authenticated upozorenje](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable)). Ranije upozorenje o GraphQL metapodacima stare Auth-backed tabele nije novo i njena postojeća vlasnička RLS zaštita nije menjana. Ostale aplikacije u projektu nisu menjane.
