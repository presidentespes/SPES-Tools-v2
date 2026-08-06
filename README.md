# Consolle SPES Ginnastica Mestre 5.4.0

Applicazione desktop Windows per amministrazione, segreteria e consiglio direttivo della SPES Ginnastica Mestre.

## Accesso iniziale

Utenti iniziali: `admin`, `segreteria`, `consiglieri`. La password iniziale è `gamba` e deve essere modificata obbligatoriamente al primo accesso.

## Permessi

Il profilo assegna una configurazione iniziale, ma l'amministratore può personalizzare per ogni utente la visibilità di singoli moduli e collegamenti. Le password non vengono salvate in chiaro.

## Autore

Cecchinato Simone

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

## Risultati FGI SPES (5.3.3)

Il modulo usa il codice societario FGI `000112`, considera la stagione dal 1 settembre al 31 agosto, estrae le righe SPES da classifiche PDF/Excel/CSV e consente filtro per atleta, filtro disciplina ed esportazione. Su Windows viene registrata un'attività pianificata settimanale ogni lunedì alle ore 01:00; l'aggiornamento può essere avviato anche manualmente dalla finestra Risultati FGI.

## Regolamento FGI integrato (5.3.4)
Il pulsante **Regolamento FGI** apre il PDF T.U.N.S. 2027 incluso nell'app, senza collegarsi al sito FGI.
