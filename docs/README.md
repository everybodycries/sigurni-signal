# Operativna dokumentacija

Počnite s prirucnik-offline.html. Samostalan je i pogodan za lokalni ispis/PDF iz preglednika. Obnova: `python3 docs/build_docs.py` iz korijena projekta. Upute su datirani nacrti koji čekaju stručni pregled.

Poglavlja: prirucnik.md, iphone-priprema.md, regulatorna-provjera.md, terenska-provjera.md i napajanje-i-nabava.md. Sadržaj ne potvrđuje propise, domet ili sigurnost skloništa.

U templates/ su prazni RF, naponski, operaterski, nabavni i uređajni obrasci. Stvarne zapise držite u privatnoj kopiji. Local-rf ima540planiranih redova, intercity-rf270; mjerenja su prazna. Sve aktivacijske zapreke početno blocked. Quotes nema stvarnih ponuda; budžet5–15tisućaEUR je nepotvrđena pretpostavka bez razvoja.

Procjena: `python3 docs/evaluate_field.py local docs/templates/local-rf.csv` ili `intercity`. Procjena zapisa nije provjera autentičnosti ili pravne dopuštenosti. Ne izostavljajte neuspjele trase, smjerove ili termine. Prazni obrasci moraju svugdje biti unverified. Vremenske oznake unose se kao UTC Z ili+00:00, uz lokalni datum/vremensku zonu za međugradski test.

Napajanje: `python3 docs/power_calculator.py --daily-wh 100 --days 3 --efficiency 0.8 --usable-fraction 0.9`. Rezultat je nazivniWh s30%rezerve i gubicima, ne izmjerenih72h. Ispitajte vršnu struju, temperaturu, odspojenu mrežu i solar; telefoni se testiraju48h s bankovima.

Integritet: `python3 docs/verify_content.py`. SHA256 nije institucionalni digitalni potpis. Testovi alata: `python3 -m unittest discover -s docs -p 'test_*.py' -v`. Cjelovito stanje: implementation-status.md.
