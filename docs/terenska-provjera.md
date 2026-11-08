# Terenska provjera i prihvat pilota

Bez stvarnih radija i mjerenja svi rezultati ostaju UNVERIFIED. Korištenje softverskih testova ne zamjenjuje terenski rad.

## Lokalni RF
Prije početka odaberite točne izravne trase, trase preko čvora i stvarni unutarnji/podrumski prostor u svakom gradu. Najmanje30 poruka po smjeru i trasi, uz ciljanih95% primitka u120s. Zapisujte sve pokušaje, uključujući gubitke i kasne primitke. Provjerite vremenske oznake prije testa. Testirati deset korisnika po gradu, zagušenje, ispad čvora i dosegnuta zakonska ograničenja bez njihovog zaobilaženja.

## Međugradski RF
Sva tri gradska para, tri uzastopna dana, prozori08:00/14:00/20:00 u trajanju30min prema vremenskoj zoni grada. Predložak ima deset radiograma po paru i prozoru. Unositi lokalni datum i UTC vrijeme, ponuđene, prihvaćene, odbijene i primljene poruke. Cilj je90% prihvaćenih preneseno do kraja prozora. Ne spajati različite datume u jedan uzorak. Nedostajući prozor ili premalo zapisa nije prolaz. Primitak baze i primitak osobe odvojene su provjere.

## Telefon i radio
Na stvarnim Androidima/iPhoneima ispitati zaključavanje, pozadinu, prisilno zatvaranje, restart, prekid BLE-a i ponovno spajanje. Provjeriti hoće li konkretan radio prikazati propuštene poruke. Testirati hrvatske znakove, byte-limit, duplikate, sukobe oznaka, pogrešno vrijeme, nepoznate pošiljatelje i gubitak ključa. Privatni tekst se nikad ne prenosi javno bez zasebne suglasnosti.

## Napajanje i vježba
Baze/čvorovi72h bez mreže i bez doprinosa solara; telefoni48h s pripadajućim powerbankovima prema dogovorenom profilu. Uključiti tri dnevna radna prozora, stvarno slušanje, emitiranu snagu, USB uređaje i temperature. Jedna vježba vodi od osobe u skloništu preko dviju baza do primateljeve potvrde, bez izlaska radi signala. Pri kvaru koristiti unaprijed postavljenu sigurnu antenu/pristupni čvor i rezervni postupak.

## Izvještaj
Obrasci su u templates/. Ne mijenjati izvorne prazne predloške stvarnim osobnim podacima. U izvještaj uključiti sve odabrane trase i sve neuspjehe. Kratak prolaz ne dokazuje cjelogodišnju dostupnost, javnu pokrivenost ili certificiranu otpornost na EMP.
