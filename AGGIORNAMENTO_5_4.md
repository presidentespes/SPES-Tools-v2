# Consolle SPES Ginnastica Mestre 5.4.0

## Accesso e profili

- nome ufficiale: **Consolle SPES Ginnastica Mestre**;
- autore: **Cecchinato Simone**;
- utenti iniziali: `admin`, `segreteria`, `consiglieri`;
- password iniziale: `gamba`, con cambio obbligatorio al primo accesso;
- password archiviate con PBKDF2-SHA256 e salt casuale;
- profili base con permessi distinti.

## Permessi personalizzati

L'amministratore può creare utenti, scegliere il profilo, attivare/disattivare l'account e decidere quali singoli pulsanti o moduli mostrare. Può inoltre ripristinare i permessi del profilo e reimpostare la password iniziale.

## Profili predefiniti

- **Admin:** accesso completo.
- **Segreteria:** Gmail segreteria, Wellness in Cloud, Risultati FGI, Calendario gare, Regolamento FGI e sito SPES.
- **Consiglieri:** Gmail consiglio, Drive SPES, gestionali autorizzati, area FGI, musica e sito SPES; nessun accesso bancario o PEC.
