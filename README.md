# Piattaforma Elettorale Unificata — ITSCG Primo Levi di Seregno

Repository tecnico della piattaforma elettorale digitale dell'Istituto.

## Stato del progetto

Il codice è stato riorganizzato prendendo come base l'interfaccia originaria e mantenendo i pulsanti e le aree operative: Cabina elettorale, Norme & Commissione, Referenti Studenti, Referenti Genitori, Dirigenza/Vicepresidenza/DSGA/Segreteria e Commissione.

La soluzione è **progettata per soddisfare i requisiti tecnico-organizzativi** richiamati dalla Nota MIM prot. AOODPIT n. 3803 del 30 giugno 2026 e dal relativo Allegato tecnico. La conformità effettiva non deriva dal solo software: prima dell'uso reale devono essere completati collaudo, DPIA, regolamento d'Istituto, configurazione cloud, nomine/accordi privacy, procedure di conservazione, backup e approvazioni interne indicate nella cartella `docs/`.

## Architettura di sicurezza

- il browser non possiede password amministrative hard-coded;
- le credenziali del personale sono verificate lato server;
- le password degli account gestionali sono derivate con `scrypt` e salt casuale;
- la registrazione del voto avviene esclusivamente tramite Cloud Function;
- i documenti delle urne non contengono nome, token, ID utente, sessione, IP o timestamp;
- nessun campo `vote_id_*` collega il registro degli aventi diritto a una scheda;
- le sessioni di voto sono temporanee e il collegamento di sessione viene eliminato nella stessa transazione che registra la scheda;
- le Firestore Security Rules vietano a qualunque client la lettura/scrittura diretta delle urne;
- durante la votazione non vengono esposte preferenze parziali;
- Commissione, Dirigenza, Segreteria e Referenti ricevono viste diverse in base al ruolo e alla fase elettorale;
- le operazioni amministrative server-side sono registrate in `audit_admin` senza dati sul contenuto del voto;
- le operazioni distruttive sull'urna sono disabilitate dal canale web ordinario.

## Struttura

```text
index.html                    frontend, interfaccia originaria adattata
firestore.rules               regole Firestore fail-closed
firebase.json                 configurazione Firebase
.firebaserc                   progetto Firebase di riferimento
functions/index.js            API server-side e logica voto
functions/package.json        dipendenze Cloud Functions
functions/scripts/            provisioning, bonifica e preflight
.github/workflows/            pubblicazione GitHub Pages e workflow Firebase
docs/                         fascicolo tecnico-organizzativo
```

## Pubblicazione del sito

Il frontend può essere pubblicato con GitHub Pages. È incluso il workflow `.github/workflows/pages.yml`.

Il backend **non può essere eseguito da GitHub Pages**: per le votazioni reali deve essere distribuito su Firebase Functions e devono essere applicate le regole Firestore. Il workflow `.github/workflows/firebase-backend.yml` è predisposto per il deploy dopo l'inserimento del service account come GitHub Secret.

## Prima messa in esercizio

1. configurare Firebase/Firestore/Functions;
2. distribuire `firestore.rules` e `functions/`;
3. creare almeno un account personale `COMMISSIONE` con lo script offline di provisioning;
4. eseguire la bonifica dei dati legacy, se il database era già utilizzato;
5. eseguire il preflight tecnico;
6. completare DPIA, informativa, registro trattamenti e accordi ex art. 28 GDPR ove applicabili;
7. approvare/aggiornare il regolamento d'Istituto;
8. eseguire e verbalizzare collaudo funzionale e di sicurezza;
9. configurare conservazione documentale e responsabilità;
10. solo dopo il via libera formale attivare una consultazione reale.

Vedere `docs/12_PROCEDURA_MESSA_IN_ESERCIZIO.md`.

## Fonti principali

- Nota MIM prot. AOODPIT n. 3803 del 30 giugno 2026 — attività collegiali deliberative a distanza.
- Allegato tecnico del 28 aprile 2026 — requisiti tecnico-organizzativi per gestione digitale degli organi collegiali e operazioni di voto.
- Regolamento (UE) 2016/679 (GDPR) e D.Lgs. 196/2003.
- D.Lgs. 82/2005 (CAD).
- Linee guida AgID sulla formazione, gestione e conservazione dei documenti informatici.

Riferimenti e link sono raccolti in `docs/00_FONTI_NORMATIVE.md`.

## Controlli automatici GitHub

Il repository include inoltre:

- **CodeQL** per l'analisi statica del codice JavaScript/TypeScript;
- **Dependabot** per proporre aggiornamenti controllati di dipendenze npm e GitHub Actions;
- una **Security Policy** che vieta la pubblicazione di credenziali/dati reali e disciplina la segnalazione delle vulnerabilità.

Gli aggiornamenti di sicurezza non vanno applicati automaticamente durante una consultazione: ogni modifica alla logica di voto, alle Rules o alle dipendenze deve essere testata e associata a un nuovo collaudo/versione identificata da commit SHA.
