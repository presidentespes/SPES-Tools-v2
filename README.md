# SPES Configuratore Contabile 5.0

Applicazione desktop Windows per riconciliazione bancaria, conversione compensi,
gestione cassa, causali ABI e storico operazioni.

## Funzioni principali

- Nexi PDF: movimenti, bollo e spese estratto conto.
- BCC RelaxBanking PDF: descrizioni multi-riga e soggetto ordinante.
- Volksbank: causale `99 VOLKSBANK` configurabile per bonifici in entrata con parole chiave.
- Bonifici SEPA: beneficiario nel campo SOGGETTO.
- Convertitore compensi: anteprima immediata, franchigia contributiva EUR 5.000,
  lordo già percepito e PDF.
- Gestione Cassa: CSV/Excel e causali `35CASSA`-`46CASSA`.
- Causali ABI e regole automatiche modificabili dall'app.
- Test automatici eseguiti nella build GitHub Actions.

## Compilazione

Aprire **Actions → Build SPES Configuratore Contabile Windows → Run workflow**.
L'artifact prodotto è `SPES_Configuratore_Contabile_5_0`.

## Avvio locale

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH="app"
python run.py
```

I calcoli fiscali e contributivi sono simulazioni operative da verificare con il consulente.
