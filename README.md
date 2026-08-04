# SPES Tools 3.3


Questa versione aggiunge alla Fase 2:

- **CAF Tools**: calcolo indicativo lordo/netto, aliquote modificabili ed esportazione PDF;
- **Causali ABI**: editor persistente per NEXI, BCC e VOLKSBANK;
- **Storico**: registra esportazioni bancarie e PDF CAF;
- configurazioni e storico salvati in `%APPDATA%\\SPES_Tools`;
- i parser bancari leggono le causali ABI salvate dall'utente.

## Build

1. Caricare tutto il contenuto nel repository GitHub, inclusa `.github`.
2. Aprire **Actions**.
3. Avviare **Build SPES Tools Windows**.
4. Scaricare l'artifact `SPES_Tools_Windows_Fase3`.

## Avvertenza CAF

Il calcolo lordo/netto e indicativo e non sostituisce un cedolino, un prospetto fiscale o la consulenza di un professionista abilitato.

## Avvertenza contabile

Prima dell'importazione in TeamSystem verificare sempre il numero dei movimenti, i totali Dare/Avere e le causali ABI rispetto al documento originale.

## Versione 3.2 - correzioni

- Parser Nexi compatibile con gli estratti in cui il testo PDF viene estratto senza spazi o interruzioni di riga.
- Inclusione automatica di imposta di bollo e spese invio estratto conto.
- Campo `Lordo gia percepito` visibile e modificabile per il profilo `Collaboratore sportivo`.
- Visualizzazione e stampa PDF del lordo cumulato.


## Correzioni 3.3
- Campo Lordo gia percepito anche per Pensionato.
- Calcolo sportivo 2026 con soglia contributiva 5.000 euro, IVS su 50% imponibile e quota collaboratore 1/3.
- Anteprima automatica del risultato senza creare il PDF.
