# Consolle SPES Ginnastica Mestre 6.0.4

## macOS
- Nuovo workflow GitHub Actions `build-macos.yml`.
- Generazione dell'applicazione `Consolle SPES Ginnastica Mestre.app`.
- Pacchetto ZIP compatibile con macOS 11 o successivo.
- Build su runner Apple Silicon (`macos-14`).

## Mobile
- Primo prototipo PWA installabile su iPhone, iPad e Android.
- Dashboard responsive per Presidente/Admin con accesso completo.
- Manifest, service worker e cache offline della shell grafica.
- Collegamenti rapidi a Gmail, Drive, FGI Veneto e sito SPES.

## Nota di sicurezza
Il prototipo mobile è una base grafica installabile. Per condividere dati reali, utenti, permessi, contabilità e documenti tra desktop e mobile servirà un backend HTTPS centralizzato. Non vengono inserite credenziali o dati bancari nel codice della PWA.
