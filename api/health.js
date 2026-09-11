'use strict';

const adminApp = require('firebase-admin/app');
const adminFirestore = require('firebase-admin/firestore');

function ensureFirebaseAdmin() {
  try { return adminApp.getApp(); } catch (_) {}
  const raw = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
  if (!raw) throw new Error('FIREBASE_SERVICE_ACCOUNT_JSON non configurata.');
  const sa = JSON.parse(raw);
  return adminApp.initializeApp({
    credential: adminApp.cert(sa),
    projectId: sa.project_id
  });
}

function allowedOrigins() {
  const defaults = [
    'https://giuseppeborzumati-cmyk.github.io',
    'https://commissioneelettorale-boop.github.io'
  ];
  const extra = String(process.env.ALLOWED_ORIGINS || '')
    .split(',').map(v => v.trim()).filter(Boolean);
  return new Set([...defaults, ...extra]);
}

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  const origin = String(req.headers.origin || '');
  if (allowedOrigins().has(origin)) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') return res.status(405).json({ ok: false, error: 'method-not-allowed' });

  try {
    const app = ensureFirebaseAdmin();
    const db = adminFirestore.getFirestore(app);
    await db.collection('artifacts').limit(1).get();
    return res.status(200).json({
      ok: true,
      backend: true,
      firebase: true,
      appId: 'iis-levi-electoral-v3'
    });
  } catch (error) {
    console.error('[HEALTH]', error?.message || error);
    return res.status(503).json({ ok: false, backend: true, firebase: false });
  }
};
