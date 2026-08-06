# Consolle SPES Ginnastica Mestre 6.0.1

Applicazione desktop Windows per amministrazione, segreteria e consiglio direttivo della SPES Ginnastica Mestre A.S.D.

**Autore:** Cecchinato Simone

## Funzioni principali

- login con profili `admin`, `segreteria` e `consiglieri`;
- password iniziale `gamba` con cambio obbligatorio;
- permessi personalizzabili per singolo utente;
- database SQLite locale `consolle_spes.db`;
- registro attività e accessi;
- riconciliazione bancaria BCC, Volksbank e Nexi;
- convertitore compensi e gestione Cassa;
- archivio CSV separato per banca e anno;
- risultati FGI SPES, codice società `000112`;
- calendario gare dalla homepage FGI Veneto;
- PDF locale del TUNS 2027;
- backup, ripristino, impostazioni e aggiornamenti;
- collegamenti rapidi ai servizi SPES, Google, home banking e musica.

## Avvio locale

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
$env:PYTHONPATH="app"
.\.venv\Scripts\python.exe run.py
```

## Build Windows

Aprire **Actions → Build Consolle SPES Ginnastica Mestre Windows → Run workflow**.

Artifact prodotti:

- `Consolle_SPES_Ginnastica_Mestre_6_0_1_Portable`
- `Consolle_SPES_Ginnastica_Mestre_6_0_1_Setup`

I calcoli fiscali e contributivi sono simulazioni operative da verificare con il consulente.
