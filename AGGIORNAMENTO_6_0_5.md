# Consolle SPES Ginnastica Mestre 6.0.5

## Backend centrale e accesso mobile

- aggiunto backend FastAPI con database SQLite dedicato;
- login mobile con token firmato e scadenza;
- profili e permessi identici a quelli desktop;
- il Presidente/Admin visualizza tutte le funzioni anche da mobile;
- Segreteria e Consiglieri vedono solo i moduli autorizzati;
- cambio password iniziale obbligatorio;
- API per utente corrente, dashboard, moduli visibili e gestione utenti admin;
- PWA mobile collegata al backend con login, logout e stato connessione;
- conferma preventiva per le funzioni sensibili se la password iniziale non è stata cambiata;
- Dockerfile e docker-compose per la pubblicazione del server;
- workflow GitHub Actions dedicato ai test e al pacchetto backend.

## Sicurezza

Il backend va pubblicato esclusivamente tramite HTTPS. La variabile `SPES_API_SECRET` deve essere una chiave casuale di almeno 32 caratteri e non deve essere salvata nel repository. Prima della pubblicazione Internet vanno cambiate le password iniziali `gamba`.

## Stato del progetto

Questa versione introduce l'infrastruttura centrale. I collegamenti web sono già utilizzabili da mobile. La sincronizzazione completa di risultati FGI, calendario, PDF, documenti e dati amministrativi sarà realizzata sui nuovi endpoint del backend nelle versioni successive.
