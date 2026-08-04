# Caricamento con GitHub Desktop

1. Installa e apri GitHub Desktop.
2. Accedi con lo stesso account GitHub del repository `SPES-Tools-v2`.
3. Seleziona **File > Clone repository** e clona `presidentespes/SPES-Tools-v2`.
4. Apri la cartella clonata con **Repository > Show in Explorer**.
5. Elimina il contenuto della cartella clonata, ma non eliminare la cartella nascosta `.git`.
6. Copia qui tutto il contenuto di questo pacchetto.
7. Torna in GitHub Desktop: compariranno i file modificati.
8. Scrivi come riepilogo: `Aggiornamento SPES Configuratore Contabile 4.0`.
9. Premi **Commit to main** e poi **Push origin**.
10. Su GitHub apri **Actions > Build SPES Tools Windows** e avvia il workflow.

Non caricare manualmente `dist`, `build`, file `.exe`, ambienti `.venv` o ZIP: sono esclusi dal file `.gitignore`.
