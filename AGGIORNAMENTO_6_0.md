# Consolle SPES Ginnastica Mestre 6.0.0

## Novità principali

- persistenza utenti, permessi, impostazioni di sistema e registro attività su database SQLite `consolle_spes.db`;
- profili iniziali `admin`, `segreteria` e `consiglieri`, con password iniziale `gamba` e cambio obbligatorio;
- permessi personalizzabili per ogni singolo utente;
- registro degli accessi riusciti e falliti, cambi password, gestione utenti e apertura dei moduli;
- nuova finestra **Registro attività**, visibile agli utenti autorizzati;
- backup aggiornato per includere il database SQLite;
- mantenimento dei moduli contabili, Area FGI, calendario FGI Veneto, PDF TUNS 2027 e collegamenti web;
- installer, metadati e workflow aggiornati alla versione 6.0.0.

## Migrazione

Al primo avvio la Consolle crea automaticamente il database nella cartella dati dell'utente. I file operativi precedenti restano invariati. Prima dell'aggiornamento è comunque consigliato creare un backup dalla versione installata.

## Pubblicazione

Commit consigliato: `Versione 6.0.0 - SQLite, profili, permessi e registro attività`.
