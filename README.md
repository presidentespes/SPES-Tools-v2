# SPES Configuratore Contabile 5.3

Applicazione desktop Windows per riconciliazione bancaria, conversione compensi,
gestione cassa, causali ABI e storico operazioni.

## Funzioni principali

- Nexi PDF: movimenti, bollo e spese estratto conto.
- BCC RelaxBanking PDF: descrizioni multi-riga e soggetto ordinante.
- Volksbank: causale `99 VOLKSBANK` configurabile per bonifici in entrata con parole chiave.
- Bonifici SEPA: beneficiario nel campo SOGGETTO.
- Convertitore compensi: anteprima immediata, franchigia contributiva EUR 5.100,
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


## Installer e backup

La versione 5.1 produce un Setup.exe e include backup/ripristino configurazione e controllo aggiornamenti.


## Esportazione CSV TeamSystem

- l'operatore sceglie la cartella di destinazione;
- l'ultima cartella viene ricordata;
- il nome è generato automaticamente, ad esempio `bcc_feb_2025.csv`;
- per periodi su più mesi viene usato un nome come `bcc_nov-dic_2025.csv`;
- se il file esiste già viene creato automaticamente `_2`, `_3` e così via.


## Novita 5.3

- Archivio operazioni separato in BCC, Volksbank, Nexi e Cassa, con sottocartelle per anno.
- Sei collegamenti rapidi nella dashboard: Sportivi in Cloud, Wellness in Cloud, Cassa in Cloud, SPES Connect e due playlist Spotify.
- Pulsanti dedicati nello Storico per aprire le cartelle di ciascun archivio.
