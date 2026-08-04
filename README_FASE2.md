# SPES Tools - Fase 2

Questa patch aggiunge una prima maschera operativa:

- apertura file bancari;
- riconoscimento Nexi PDF, BCC PDF, Volksbank e BonSepa;
- anteprima modificabile;
- esportazione CSV TeamSystem;
- collegamento dei pulsanti "Convertitore bancario" e "Bonifici SEPA".

## Caricamento su GitHub

Caricare mantenendo questi percorsi:

- `app/spes_tools/UI/main_window.py`
- `app/spes_tools/UI/banking_window.py`
- `app/spes_tools/banking/__init__.py`
- `app/spes_tools/banking/parsers.py`
- `requirements.txt`
- `requirements-build.txt`

Dopo il commit, eseguire nuovamente il workflow.

## Controllo obbligatorio

Prima dell'uso contabile confrontare sempre numero movimenti, totali e causali ABI con il documento originale.
