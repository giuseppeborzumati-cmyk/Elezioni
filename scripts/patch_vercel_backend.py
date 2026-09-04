from pathlib import Path
import re

p = Path('functions/index.js')
s = p.read_text()
s = s.replace(
    "const { initializeApp } = require('firebase-admin/app');",
    "const { initializeApp, cert, getApps } = require('firebase-admin/app');"
)
s = s.replace(
    "initializeApp();\nconst db = getFirestore();",
    "const rawServiceAccount = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;\n"
    "if (!getApps().length) {\n"
    "  if (rawServiceAccount) {\n"
    "    const serviceAccount = JSON.parse(rawServiceAccount);\n"
    "    initializeApp({ credential: cert(serviceAccount), projectId: serviceAccount.project_id });\n"
    "  } else { initializeApp(); }\n"
    "}\nconst db = getFirestore();"
)
p.write_text(s)

proxy = '''        // Backend server-side eseguito su Vercel: nessun segreto nel browser.
        const SECURE_API = new Proxy({}, {
            get: (_, functionName) => async (data = {}) => {
                const headers = { 'Content-Type': 'application/json' };
                if (auth.currentUser) {
                    const idToken = await auth.currentUser.getIdToken();
                    headers.Authorization = `Bearer ${idToken}`;
                }
                let response;
                try {
                    response = await fetch('/api/call', {
                        method: 'POST', headers, cache: 'no-store',
                        body: JSON.stringify({ name: String(functionName), data })
                    });
                } catch (_) {
                    const err = new Error('Servizio di autenticazione non raggiungibile.');
                    err.code = 'unavailable';
                    throw err;
                }
                let payload = {};
                try { payload = await response.json(); } catch (_) {}
                if (!response.ok || payload.error) {
                    const err = new Error(payload?.error?.message || 'Operazione non completata.');
                    err.code = payload?.error?.code || (response.status === 401 ? 'unauthenticated' : 'internal');
                    throw err;
                }
                return { data: payload.data };
            }
        });'''

pattern = re.compile(
    r"\s*// Nessun segreto amministrativo è incorporato nel browser\.\s*\n"
    r"\s*const SECURE_API = Object\.freeze\(\{.*?\n\s*\}\);",
    re.S
)

for name in ('index.html', '404.html'):
    f = Path(name)
    text = f.read_text()
    updated, count = pattern.subn('\n' + proxy, text, count=1)
    if count != 1:
        raise SystemExit(f'Blocco SECURE_API non trovato in {name}')
    f.write_text(updated)

print('Patch Vercel applicata correttamente.')
