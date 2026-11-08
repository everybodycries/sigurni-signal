# Provjera zajednice 0.4 — 8. studenoga 2026.

## Potvrđeno ponašanje

- Privatna Sigurni Signal shema i jedan javni RPC s256-bitnim aplikacijskim ključevima; izvorne Auth tablice i ostale aplikacije nisu izmijenjene.
- Stvarna administracija kroz javno web sučelje: prijava lokalnom datotekom, kreiranje i iskorištavanje pozivnice, izvoz ključa člana, objava obavijesti, isključivanje/uključivanje člana te odbijanje samostalnog uklanjanja administratorskih ovlasti.
- Stvarni Supabase REST prijenos grupnih i privatnih poruka, ponovljeno slanje bez duplikata i odbijanje neovlaštenih administrator/DM/call radnji.
- End-to-end kroz preglednik: isti član učitava ključ, šifrira plan na uređaju, šalje vlastitu kopiju, mijenja lokalni plan, dešifrira spremljenu kopiju, potvrđuje obnovu i briše vlastitu kopiju. To nije simulirani cloudUI.
- Stvarni WebRTC audioRTP u oba smjera, mute/unmute i prekid s provjerom zaustavljenih audio zapisa. U jednom javnom testu izmjereno6280/5587 bajtova slanja/prijma na jednom peeru i obrnuto na drugom.
- Zvuk je bio sintetički iz Chromeovog testnog uređaja. Transportni test koristio je dva neovisna JS klijenta na istom računalu u izoliranom testnom pregledniku s dopuštenim loopbackkandidatima i isključenim testnim mDNSskrivanjem. To nije dokaz poziva između dvije mobilne ili različite NATmreže. Na uobičajenim mrežnim sučeljima ovog računala i neovisni referentni WebRTCtest nije se povezao.
- Mikrofon nije tražen pri prijavi, osvježavanju ili dolaznoj obavijesti. Traži se samo na izričit početak/prihvat. Rano otkazivanje i kasni asyncodgovori pokriveni su testovima.
- Cloudflare /api/turn primjenjuje provjeru aktivnog člana, ograničenja ulaza, dopušten Meteredhost/path i no-store; ne vraća privatni providerAPIkey. Ispravljena je razlika runtimea: Cloudflare fetch koristi manual preusmjeravanje uz odbijanje3xx, jer redirect:error nije podržan na edgeu.

## Testovi

49 Node web testova,48 Python baznih/gateway testova i15 operativnih testova: ukupno112 prolazi. Dodatno prolazi stvarni izolirani PostgreSQLintegracijski skup za ACL/RLS, pozivnice, uloge, privatne poruke, signale, kvote, smanjene snapshotodgovore, zadržavanje i šifrirane kopije. AndroidAPK0.1 nije mijenjan niti su prethodni JVMtestovi uključeni u ovaj broj.

Testovi su prvo reproducirali pa ispravili ključne probleme: povratak stare prijave nakon logouta, pogrešan Windowreceiver za fetch, predugo čekanje potpunog ICEgatheringa uz već postojeće LANkandidate, neispravan edge redirectmode te kriptografske operacije preko promjene korisničke sesije.

## TURN i besplatni plan

Korisnik je dovršio Meteredregistraciju. Na stvarnom računu odabran je Free Trial Global,500MBmjesečno, stops atmonthlylimit/nevercharged, bez uptimeSLA. Opća promotivna OpenRelaystranica navodi veće kvote; ne koristimo je kao dokaz kvote ovog računa.

Za izdavanje nove vjerodajnice preglednički alat zahtijeva potvrdu pri samoj radnji. Do nje i spremanja serversecreta TURN_API_URL/TURN_API_KEY relej nije aktiviran; ovlašteni /api/turn vraća503configured:false. Izravni STUNpoziv ostaje dostupan gdje mreža dopušta. Nema plaćenog fallbacka.

## Granice

Chat je pohranjen na poslužitelju i nije krajnje šifriran. U aplikacijskom APIju privatni razgovor dohvaćaju samo dva sudionika; vlasnik baze ima tehnički pristup pohranjenom tekstu. Šifrirani plan koristi zasebnu zaštitnu frazu koja se ne šalje poslužitelju.

Nisu potvrđeni fizički Android/iPhone mikrofon, rad preko stvarnih različitih WANmreža, zvonjenje u zatvorenoj aplikaciji (nije implementirano), PSTNpozivi/SMS (nisu dio sustava), radijske veze, dozvole ili autonomija napajanja. LoRa i lokalni offlineplan ostaju zasebni slojevi.
