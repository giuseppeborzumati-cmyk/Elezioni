'use strict';

const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const adminApp = require('firebase-admin/app');
const adminFirestore = require('firebase-admin/firestore');
const adminAuth = require('firebase-admin/auth');

let backendPromise;

class HttpsError extends Error {
  constructor(code, message, details) {
    super(String(message || 'Operazione non completata.'));
    this.name = 'HttpsError';
    this.code = String(code || 'internal');
    this.details = details;
  }
}

function onCall(optionsOrHandler, maybeHandler) {
  const handler = typeof optionsOrHandler === 'function' ? optionsOrHandler : maybeHandler;
  if (typeof handler !== 'function') throw new Error('Handler callable non valido.');
  return Object.freeze({ run: handler });
}

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

function loadBackend() {
  if (!backendPromise) {
    backendPromise = Promise.resolve().then(() => {
      ensureFirebaseAdmin();
      const sourcePath = path.join(process.cwd(), 'functions', 'index.js');
      const source = fs.readFileSync(sourcePath, 'utf8');
      if (!source.includes("const APP_ID = 'iis-levi-electoral-v3'")) {
        throw new Error('Sorgente backend non riconosciuto.');
      }
      const module = { exports: {} };
      const firebaseAppCompat = { ...adminApp, initializeApp: ensureFirebaseAdmin };
      const allowedRequire = (id) => {
        if (id === 'firebase-functions/v2/https') return { onCall, HttpsError };
        if (id === 'firebase-admin/app') return firebaseAppCompat;
        if (id === 'firebase-admin/firestore') return adminFirestore;
        if (id === 'firebase-admin/auth') return adminAuth;
        if (id === 'crypto' || id === 'node:crypto') return crypto;
        throw new Error('Modulo backend non autorizzato: ' + id);
      };
      const context = {
        module, exports: module.exports, require: allowedRequire,
        Buffer, console, Intl, Date, Math, JSON, Object, Array, String, Number,
        Boolean, Set, Map, Promise, RegExp, Error, TypeError, parseInt, parseFloat,
        setTimeout, clearTimeout, URL, URLSearchParams, process
      };
      vm.runInNewContext(source, context, { filename: 'functions/index.js', timeout: 5000 });
      return module.exports;
    });
  }
  return backendPromise;
}

const STATUS = {
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

  const origin = String(req.headers.origin || '');
  const origins = allowedOrigins();
  if (origins.has(origin)) res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Vary', 'Origin');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') {
    return res.status(405).json({ error: { code: 'method-not-allowed', message: 'Metodo non consentito.' } });
  }

  try {
    const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    const name = String(body.name || '').trim();
    const data = body.data && typeof body.data === 'object' ? body.data : {};
    if (!/^[A-Za-z][A-Za-z0-9_]{0,79}$/.test(name)) {
      throw new HttpsError('invalid-argument', 'Funzione non valida.');
    }

    const backend = await loadBackend();
    const fn = backend[name];
    if (!fn || typeof fn.run !== 'function') throw new HttpsError('not-found', 'Funzione non disponibile.');

    let auth;
    const header = String(req.headers.authorization || '');
    if (header.startsWith('Bearer ')) {
      const token = header.slice(7).trim();
      if (token) {
        const decoded = await adminAuth.getAuth().verifyIdToken(token, true);
        auth = { uid: decoded.uid, token: decoded };
      }
    }

    const result = await fn.run({ data, auth, rawRequest: req });
    return res.status(200).json({ data: result });
  } catch (error) {
    const code = String(error?.code || 'internal').replace(/^functions\//, '');
    const status = STATUS[code] || 500;
    const message = status >= 500
      ? 'Servizio temporaneamente non disponibile.'
      : String(error?.message || 'Operazione non completata.');
    if (status >= 500) console.error('[ELEZIONI]', code, error?.stack || error);
    return res.status(status).json({ error: { code, message } });
  }
};
