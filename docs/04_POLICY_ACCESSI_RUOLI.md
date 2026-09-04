# 04 — Policy accessi e ruoli

## Principi

1. **Identità individuale:** gli account istituzionali non devono essere condivisi.
2. **Minimo privilegio:** ogni ruolo vede soltanto ciò che serve.
3. **Separazione dei compiti:** gestione aventi diritto, scrutinio, amministrazione cloud e conservazione devono essere attribuiti e controllati.
4. **Nessun accesso diretto all'urna dal browser:** le urne sono deny-by-default nelle Firestore Rules.
5. **No segreti nel repository:** password/service account/API private keys sono vietati nel codice.

## Matrice ruoli

| Funzione | Commissione | Dirigente | Vicepreside | DSGA | Segreteria | Referente | Elettore |
|---|---:|---:|---:|---:|---:|---:|---:|
| Configurazione elezioni | Sì | No | No | No | No | No | No |
| Gestione aventi diritto | Sì | No | No | No | No | No | No |
| Gestione account staff | Sì | No | No | No | No | No | No |
| Lettura diretta Firestore urna | **No** | **No** | **No** | **No** | **No** | **No** | **No** |
| Scrutinio schede anonimizzate | dopo chiusura | No | No | No | No | No | No |
| Risultati aggregati | Sì | secondo fase | secondo fase/scope | secondo fase | secondo fase | classe/componente | No |
| Preferenze parziali durante apertura | No | No | No | No | No | No | No |
| Voto | No | se avente diritto con token | idem | idem | idem | se avente diritto | Sì |
| Audit amministrativo | Sì | lettura autorizzata | lettura autorizzata | lettura autorizzata | lettura autorizzata | No | No |

## Password e MFA

- minimo 12 caratteri per account applicativi;
- una password diversa per ogni persona;
- `scrypt` + salt per le password applicative;
- MFA obbligatoria/recomandata fortemente per GitHub, Google/Firebase e console cloud;
- vietato trasmettere password via email non protetta o inserirle nei verbali;
- revoca immediata alla cessazione del ruolo.

## Sessioni

- timeout applicativo: 15 minuti di inattività;
- token di voto con una sola sessione attiva;
- sessione di voto revocata/consumata dopo la registrazione;
- logout obbligatorio su postazioni condivise.

## Revisione periodica

Prima di ogni consultazione la Commissione verifica elenco account, ruoli, ambiti di classe e stato attivo/disattivo. La verifica è verbalizzata.
