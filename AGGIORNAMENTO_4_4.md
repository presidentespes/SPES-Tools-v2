# Aggiornamento 4.4

## Volksbank - causale 99

I bonifici in entrata ricevono la causale ABI `99 VOLKSBANK` quando la descrizione contiene, senza distinzione tra maiuscole/minuscole o accenti, una delle parole:

- `quota`
- `mensile`
- `mensilita` / `mensilità`
- `corso`

Gli altri bonifici in entrata mantengono la causale ABI ordinaria `47 VOLKSBANK`.

La nuova causale è modificabile nella scheda VOLKSBANK della finestra Causali ABI, con chiave `quota_corso_entrata`.
