# Migrazione completa verso commissioneelettorale-boop/Elezione_Levi

## Obiettivo

Trasferire l'intera piattaforma elettorale nel repository:

`commissioneelettorale-boop/Elezione_Levi`

mantenendo separati dal codice tutti i segreti, le password e le chiavi private.

## Contenuto da trasferire

La copia deve comprendere integralmente:

- `index.html` e `404.html`;
- librerie locali `vendor/`;
- immagini e risorse statiche;
- `firestore.rules`;
- `firebase.json` e `.firebaserc`;
- backend Firebase in `functions/`;
- backend Vercel in `api/`;
- `package.json` e `vercel.json`;
- documentazione `docs/`;
- workflow GitHub in `.github/workflows/`;
- `.gitignore`, `.nojekyll`, `.env.example`;
- README e documentazione di sicurezza.

## URL previsto del frontend

`https://commissioneelettorale-boop.github.io/Elezione_Levi/`

Origin da autorizzare lato backend:

`https://commissioneelettorale-boop.github.io`

## Firebase

Il progetto attualmente utilizzato è `mio-sistema-voto`.

Se si mantiene lo stesso progetto Firebase, non è necessario duplicare Firestore o gli account applicativi. Il nuovo frontend utilizza gli stessi dati e le stesse regole, purché le configurazioni Firebase restino coerenti.

### Dominio Firebase Authentication

In Firebase Console > Authentication > Settings > Authorized domains aggiungere:

`commissioneelettorale-boop.github.io`

Non rimuovere il precedente dominio finché il collaudo del nuovo sito non è concluso.

## Vercel

Il repository di migrazione contiene ora un backend Vercel self-contained:

- `api/call.js`;
- `api/health.js`;
- `package.json`;
- `vercel.json`.

Il backend carica localmente `functions/index.js`; non dipende da un download runtime del sorgente GitHub.

### Variabili Vercel obbligatorie

Configurare come Secret/Environment Variable, senza inserirle nel repository:

- `FIREBASE_SERVICE_ACCOUNT_JSON` = JSON del service account Firebase attivo;
- `ALLOWED_ORIGINS` = `https://commissioneelettorale-boop.github.io,https://giuseppeborzumati-cmyk.github.io` durante la transizione.

Dopo il collaudo e la dismissione del vecchio frontend, l'origine precedente può essere rimossa.

## GitHub Pages

È presente `.github/workflows/pages.yml`.

Il workflow pubblica esclusivamente i file del frontend (`index.html`, `404.html`, `vendor/`, immagini e `.nojekyll`) e non pubblica la cartella backend come sito statico.

Nel repository di destinazione impostare GitHub Pages con sorgente **GitHub Actions** se richiesto dall'interfaccia GitHub.

## GitHub Secrets

I GitHub Secret NON vengono trasferiti copiando il repository.

Se si intende utilizzare anche il workflow Firebase, ricreare nel repository di destinazione:

`FIREBASE_SERVICE_ACCOUNT_MIO_SISTEMA_VOTO`

Il valore deve essere inserito esclusivamente nell'area Secrets di GitHub e non deve mai essere scritto in file, issue, commit o log.

## CORS e frontend

Il frontend attuale utilizza:

`https://elezioni-primo-levi-vercel.vercel.app/api/call`

Il backend Vercel presente in questa migrazione ammette sia l'origine precedente sia:

`https://commissioneelettorale-boop.github.io`

Se viene creato un nuovo progetto Vercel con un nuovo dominio, aggiornare `VERCEL_BACKEND_URL` in `index.html` e `404.html` con il nuovo endpoint `/api/call`.

## Verifiche obbligatorie dopo il trasferimento

1. GitHub Pages restituisce HTTP 200.
2. Tutte le librerie `vendor/` vengono caricate dallo stesso dominio.
3. Firebase Authentication accetta il nuovo dominio.
4. `/api/health` restituisce `ok:true`, `backend:true`, `firebase:true`.
5. Login Commissione funzionante.
6. Login referente funzionante.
7. Token elettore validato lato server.
8. Modalità prova funzionante senza scrittura nelle urne reali.
9. Doppio voto respinto.
10. Finestra temporale apertura/chiusura rispettata lato server.
11. Scrutinio e risultati non visibili prima della fase prevista.
12. CORS consente il nuovo dominio e rifiuta origini non autorizzate.
13. Nessun Secret presente nel repository.
14. Regole Firestore sottoposte a verifica.
15. Commit finale della release annotato nel verbale di collaudo.

## Passaggio definitivo

Effettuare il cambio definitivo soltanto dopo un collaudo completo sul nuovo URL. Fino a quel momento mantenere il vecchio frontend come fallback tecnico, senza duplicare o resettare i dati elettorali reali.
