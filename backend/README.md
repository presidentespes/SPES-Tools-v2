# Consolle SPES API 6.0.5

Backend centrale per la PWA mobile e, in futuro, per desktop e macOS.

## Avvio locale

Da PowerShell, nella cartella del progetto:

```powershell
$env:SPES_API_SECRET="una-chiave-casuale-lunga-almeno-32-caratteri"
$env:SPES_ALLOWED_ORIGINS="http://localhost:8080"
$env:PYTHONPATH="app"
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

API: `http://127.0.0.1:8000/api/health`
Documentazione tecnica: `http://127.0.0.1:8000/api/docs`

Per servire la PWA in locale:

```powershell
.\.venv\Scripts\python.exe -m http.server 8080 --directory mobile
```

Aprire `http://localhost:8080` e impostare come server API `http://127.0.0.1:8000`.

## Produzione

Il servizio deve essere pubblicato esclusivamente dietro HTTPS, ad esempio con Caddy o Nginx. Non esporre direttamente la porta 8000 su Internet. La chiave `SPES_API_SECRET` non deve essere caricata su GitHub.

Gli utenti iniziali sono `admin`, `segreteria` e `consiglieri`, tutti con password iniziale `gamba` e cambio obbligatorio. Prima della pubblicazione Internet cambiare immediatamente le password.
