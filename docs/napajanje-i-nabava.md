# Napajanje i nabava

Radni budžet5.000–15.000EUR je nepotvrđena pretpostavka za opremu, bez razvoja aplikacije. Nema stvarnih ponuda, odobrene potrošnje ili unaprijed dostupnih radioklubova.

## Sastav
30 osobnih LoRa uređaja i6 rezervnih (barem3 sa samostalnim unosom/prikazom/alarmom),3 USB bazna radija/računala, do3 povišena čvora i do3 pristupna čvora/antenska rješenja za podrume prema mjerenju. Zasebne HF stanice/antene/napajanje za baze, lokalni PMR446 uređaji gdje su dopušteni, baterijski prijamnici, powerbankovi i rezervni kabeli. nRF52/SX1262 je početni kandidat; konkretan model i sukladnost provjeriti prije nabave.

## Proračun
Najprije izmjeriti Wh/dan u stvarnom radnom profilu. Nazivni kapacitetWh = Wh/dan × broj dana ×1,30 / (učinkovitost pretvorbe × uporabljivi udio kapaciteta). Upotrebljivi udio uzima u obzir temperaturu, dopuštenu dubinu pražnjenja i starenje. Faktore ne umanjivati dvaput ako su gubici već obuhvaćeni mjerenjem. Za planerskih100Wh/dan,3dana,0,8 učinkovitosti i0,9 uporabljivog udjela potrebno je oko542Wh nazivno. To je proračun, ne izmjerena autonomija.

Baze/čvorovi ciljaju72h bez mreže i bez doprinosa sunca; telefoni48h s powerbankovima. Solar samo produljuje autonomiju. Provjeriti vršnu struju HF emitiranja, osigurače, vodove, temperaturu, zaštitu baterije i upute proizvođača. Antene i uzemljenje postavlja osposobljena osoba uz odobrenje lokacije. Odspojena rezerva nije dokaz EMP otpornosti.

## Nabava po fazama
Prvo regulatorna i RF izvedivost te raspoloživi operateri/lokacije. Zatim mali lokalni komplet i mjerenja; tek potom puna oprema. Popuniti bom.csv i tri usporedive ponude u quotes.csv. Odvojiti PDV, dostavu/uvoz, instalacije, baterije, rezervu, održavanje i razvoj. Ponuda treba navesti stvarni model, uvjete, dostupnost, izvor i datum; prazna polja ostaju prazna.
