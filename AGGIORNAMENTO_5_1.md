# SPES Configuratore Contabile 5.1 Professional

## Novità

- installer Windows guidato con collegamenti Start/Desktop e disinstallazione;
- proprietà EXE con nome prodotto, azienda e versione;
- modulo Impostazioni;
- esportazione e ripristino di configurazione ABI, regole e storico in un unico ZIP;
- controllo delle release GitHub e download dell'installer quando disponibile;
- build GitHub Actions con artifact portabile e Setup.exe;
- pubblicazione automatica della release quando viene creato un tag `v5.1`.

## Build ordinaria

Dopo Commit e Push, aprire Actions e avviare il workflow. Scaricare l'artifact:

`SPES_Configuratore_Contabile_5_1_Setup`

## Pubblicazione aggiornamento automatico

In GitHub Desktop creare il tag `v5.1` e pubblicarlo. Il workflow creerà una GitHub Release con il Setup.exe. Le installazioni precedenti potranno rilevarla dal modulo Impostazioni.
