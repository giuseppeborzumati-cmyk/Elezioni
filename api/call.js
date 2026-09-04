'use strict';

const backend = require('../functions/index.js');
const { getAuth } = require('firebase-admin/auth');

const STATUS_BY_CODE = {
  'invalid-argument': 400,
  'failed-precondition': 400,
  'unauthenticated': 401,
  'permission-denied': 403,
  'not-found': 404,
  'already-exists': 409,
  'resource-exhausted': 429,
  'deadline-exceeded': 504,
  'unavailable': 503,
  'internal': 500
};

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');

  if (req.method === 'OPTIONS') {
    res.setHeader('Allow', 'POST, OPTIONS');
    return res.status(204).end();
  }
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST, OPTIONS');
    return res.status(405).json({ error: { code: 'method-not-allowed', message: 'Metodo non consentito.' } });
  }

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    const name = String(body.name || '').trim();
    const data = body.data && typeof body.data === 'object' ? body.data : {};
    if (!/^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(name)) {
      return res.status(400).json({ error: { code: 'invalid-argument', message: 'Funzione non valida.' } });
    }

    const fn = backend[name];
    if (!fn || typeof fn.run !== 'function') {
      return res.status(404).json({ error: { code: 'not-found', message: 'Funzione non disponibile.' } });
    }

    let auth = undefined;
    const header = String(req.headers.authorization || '');
    if (header.startsWith('Bearer ')) {
      const idToken = header.slice(7).trim();
      if (idToken) {
        const decoded = await getAuth().verifyIdToken(idToken, true);
        auth = { uid: decoded.uid, token: decoded };
      }
    }

    const result = await fn.run({ data, auth, rawRequest: req });
    return res.status(200).json({ data: result });
  } catch (error) {
    const code = String(error?.code || 'internal').replace(/^functions\//, '');
    const status = STATUS_BY_CODE[code] || 500;
    const message = status >= 500 ? 'Servizio temporaneamente non disponibile.' : String(error?.message || 'Operazione non completata.');
    if (status >= 500) console.error('[VERCEL_BACKEND]', code, error?.message || error);
    return res.status(status).json({ error: { code, message } });
  }
};
