# Consolle SPES 6.0.6 - pubblicazione cloud

Questa versione pubblica backend e PWA mobile dallo stesso servizio HTTPS.

## Railway

1. Crea un nuovo progetto Railway collegato al repository GitHub `SPES-Tools-v2`.
2. Railway usera `railway.json` e `backend/Dockerfile`.
3. Nelle variabili del servizio aggiungi:
   - `SPES_API_SECRET`: chiave casuale di almeno 32 caratteri;
   - `SPES_ALLOWED_ORIGINS`: dominio Railway o dominio personalizzato;
   - `SPES_API_DB=/srv/spes/data/consolle_spes_server.db`.
4. Aggiungi un volume persistente montato in `/srv/spes/data`.
5. In Networking genera un dominio pubblico.
6. Verifica `https://DOMINIO/api/health`.
7. Apri `https://DOMINIO/` per installare la PWA su telefono o tablet.

## Dominio definitivo

Quando disponibile, collega `consolle.spesginnasticamestre.it` e imposta:

```text
SPES_ALLOWED_ORIGINS=https://consolle.spesginnasticamestre.it
```

## Primo accesso

Gli utenti iniziali sono `admin`, `segreteria` e `consiglieri`, con password temporanea `gamba`. Il cambio password e obbligatorio. Prima di rendere pubblico il servizio, accedi e modifica immediatamente tutte le password temporanee.

## Dati persistenti

Il database deve rimanere nel volume `/srv/spes/data`. Senza volume, utenti, password e log potrebbero andare persi a ogni nuova distribuzione.
