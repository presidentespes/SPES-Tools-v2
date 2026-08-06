# Aggiornamento 6.0.2 - Archivio locale classifiche FGI

- Al primo avvio, se l'archivio locale manca o ha più di 7 giorni, la Consolle avvia subito il download delle classifiche FGI in background.
- L'attività pianificata Windows continua a riscaricare e aggiornare l'archivio ogni lunedì alle 01:00.
- La ricerca per atleta e disciplina usa esclusivamente il file locale `fgi_results.json`, quindi non interroga il sito durante ogni ricerca.
- La data dell'ultimo aggiornamento viene salvata in `fgi_results_metadata.json` e mostrata nella finestra Risultati FGI.
- Il pulsante manuale aggiorna l'archivio completo dal sito solo quando richiesto dall'operatore.
