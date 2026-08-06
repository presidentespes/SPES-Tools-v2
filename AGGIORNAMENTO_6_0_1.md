# Aggiornamento 6.0.1

## Calendario gare FGI Veneto

La ricerca del calendario gare parte esclusivamente dalla homepage:

`https://www.fgiveneto.it/home.asp`

La Consolle:

- analizza i comunicati visibili nella homepage;
- segue solamente i comunicati collegati dalla homepage;
- scarica l'allegato PDF del calendario più recente;
- ignora esplicitamente la vecchia sezione `Calendario Gare`, ferma al 2024;
- mantiene disponibile l'ultimo PDF locale in caso di errore di rete.

Sono stati aggiunti test automatici che verificano che la pagina archivio/calendario non venga interrogata.
