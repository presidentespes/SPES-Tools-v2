# Consolle SPES Ginnastica Mestre 5.4.1

## Correzioni

- Corretto l'avvio della finestra principale dopo il login.
- `MainWindow` ora riceve correttamente l'utente autenticato.
- Lo sfondo della dashboard riceve la sessione utente senza generare errori.
- Mantenuti profili, permessi personalizzati e cambio password obbligatorio.

## Verifica locale

```powershell
$env:PYTHONPATH="app"
.\.venv\Scripts\python.exe run.py
```
