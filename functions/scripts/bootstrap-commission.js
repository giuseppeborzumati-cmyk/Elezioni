'use strict';

/**
 * Bootstrap one-time dell'account iniziale della Commissione.
 *
 * IMPORTANTE:
 * - nel repository NON è presente la password in chiaro;
 * - è presente esclusivamente un verificatore scrypt con salt casuale;
 * - l'account nasce con mustChangePassword=true;
 * - al primo accesso la Commissione deve sostituire la password prima di usare
 *   qualunque funzione amministrativa.
 *
 * Questo script richiede credenziali Google/Firebase amministrative tramite
 * GOOGLE_APPLICATION_CREDENTIALS/ADC ed è richiamato dal workflow di deploy.
 */
const admin = require('firebase-admin');

if (!admin.apps.length) admin.initializeApp();
const db = admin.firestore();

const APP_ID = 'iis-levi-electoral-v3';
const YEAR = '2026/2027';
const USERNAME = 'commissione.presidente';
const DISPLAY_NAME = 'Presidente Commissione Elettorale';
const ROLE = 'COMMISSIONE';
const PASSWORD_SALT = 'e3a331be4e899010231dbf33b52d76b28de0c0519d830d6a';
const PASSWORD_HASH = 'd92d45c4eb958f167eebcb1e714d6a4d4b531bb3147fc906b523a700ee4d9b2dda7f31bdf16567d3b552a15f1cc86d825a0f2ee8cad858eeaf2a9a45d1531ea0';

function collectionForYear(year) {
  const suffix = year.replace('/', '_');
  return db.collection('artifacts').doc(APP_ID).collection('public').doc('data').collection(`gestione_accessi_${suffix}`);
}

(async () => {
  const collection = collectionForYear(YEAR);
  const existing = await collection.where('username', '==', USERNAME).limit(1).get();
  if (!existing.empty) {
    console.log(`Bootstrap Commissione: account ${USERNAME} già presente; nessuna credenziale è stata sovrascritta.`);
    process.exit(0);
  }

  const ref = collection.doc();
  await ref.set({
    name: DISPLAY_NAME,
    username: USERNAME,
    role: ROLE,
    scopeClass: 'TUTTE',
    active: true,
    passwordHash: PASSWORD_HASH,
    passwordSalt: PASSWORD_SALT,
    mustChangePassword: true,
    bootstrapAccount: true,
    bootstrapVersion: '2026-09-04',
    createdAt: admin.firestore.FieldValue.serverTimestamp(),
    createdBy: 'SECURE_BOOTSTRAP_DEPLOY'
  });

  console.log(`Bootstrap Commissione completato: ${USERNAME} (${ref.id}).`);
  console.log('La password in chiaro non è presente nel repository né nei log del workflow. Cambio obbligatorio al primo accesso.');
})().catch((err) => {
  console.error('Bootstrap Commissione fallito:', err && err.message ? err.message : err);
  process.exit(1);
});
