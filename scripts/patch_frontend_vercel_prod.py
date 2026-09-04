from pathlib import Path
import re

BACKEND_URL = 'https://elezioni-primo-levi-vercel.vercel.app/api/call'
VERCEL_ORIGIN = 'https://elezioni-primo-levi-vercel.vercel.app'

proxy = r'''
        // Backend primario Vercel; Firebase Functions resta fallback tecnico.
        const VERCEL_BACKEND_URL = 'https://elezioni-primo-levi-vercel.vercel.app/api/call';
        const SECURE_API = new Proxy({}, {
            get: (_, functionName) => async (data = {}) => {
                const fallback = FIREBASE_API[functionName];
                const headers = { 'Content-Type': 'application/json' };
                if (auth.currentUser) {
                    const idToken = await auth.currentUser.getIdToken();
                    headers.Authorization = `Bearer ${idToken}`;
                }
                try {
                    const response = await fetch(VERCEL_BACKEND_URL, {
                        method: 'POST',
                        headers,
                        cache: 'no-store',
                        body: JSON.stringify({ name: String(functionName), data })
                    });
                    let payload = {};
                    try { payload = await response.json(); } catch (_) {}
                    if (!response.ok || payload.error) {
                        const err = new Error(payload?.error?.message || 'Operazione non completata.');
                        err.code = payload?.error?.code || (response.status === 401 ? 'unauthenticated' : 'internal');
                        throw err;
                    }
                    return { data: payload.data };
                } catch (vercelError) {
                    // Fallback solo per indisponibilità tecnica del backend Vercel.
                    const code = String(vercelError?.code || '');
                    const msg = String(vercelError?.message || '');
                    const technicalFailure = /unavailable|internal|network-request-failed/i.test(code) || /failed to fetch|network|cors|temporaneamente non disponibile/i.test(msg);
                    if (technicalFailure && typeof fallback === 'function') {
                        return await fallback(data);
                    }
                    throw vercelError;
                }
            }
        });'''

pattern = re.compile(r"const SECURE_API = Object\.freeze\(\{.*?\n\s*\}\);", re.S)

for name in ('index.html', '404.html'):
    p = Path(name)
    text = p.read_text(encoding='utf-8')

    if VERCEL_ORIGIN not in text.split('</head>', 1)[0]:
        text = text.replace(
            "https://securetoken.googleapis.com; object-src",
            "https://securetoken.googleapis.com https://elezioni-primo-levi-vercel.vercel.app; object-src",
            1
        )

    match = pattern.search(text)
    if not match:
        raise SystemExit(f'Blocco SECURE_API non trovato in {name}')
    firebase_block = match.group(0).replace('const SECURE_API = Object.freeze({', 'const FIREBASE_API = Object.freeze({', 1)
    text = text[:match.start()] + firebase_block + proxy + text[match.end():]

    text = text.replace(
        "showNotification('Accesso negato','Credenziali non valide o servizio di autenticazione non disponibile.','error');",
        "const authCode=String(e?.code||''); const authMsg=String(e?.message||''); const serviceUnavailable=/unavailable|internal|network-request-failed/i.test(authCode)||/failed to fetch|network|cors|temporaneamente non disponibile/i.test(authMsg); showNotification(serviceUnavailable?'Servizio Commissione non disponibile':'Accesso negato',serviceUnavailable?'Il servizio di autenticazione non è raggiungibile in questo momento.':'Username o password non validi.','error');",
        1
    )

    p.write_text(text, encoding='utf-8')

print('Frontend collegato al backend Vercel.')
