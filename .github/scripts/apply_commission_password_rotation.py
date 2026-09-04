from pathlib import Path

backend_path = Path('functions/index.js')
front_path = Path('index.html')
backend = backend_path.read_text(encoding='utf-8')
front = front_path.read_text(encoding='utf-8')

# 1) Blocca qualunque funzione privilegiata della Commissione finché la password bootstrap non viene cambiata.
old = """  if (MANAGEMENT_ROLES.has(role)) {\n    const staffExpiresAt = Number(request.auth.token.staffExpiresAt || 0);\n    if (!staffExpiresAt || Date.now() >= staffExpiresAt * 1000) {\n      throw new HttpsError('permission-denied', 'Credenziali gestionali scadute. Effettuare un nuovo accesso con credenziali valide.');\n    }\n  }\n  return { uid: request.auth.uid, role, claims: request.auth.token };\n}"""
new = """  if (MANAGEMENT_ROLES.has(role)) {\n    const staffExpiresAt = Number(request.auth.token.staffExpiresAt || 0);\n    if (!staffExpiresAt || Date.now() >= staffExpiresAt * 1000) {\n      throw new HttpsError('permission-denied', 'Credenziali gestionali scadute. Effettuare un nuovo accesso con credenziali valide.');\n    }\n  }\n  if (role === 'COMMISSIONE' && request.auth.token.mustChangePassword === true) {\n    throw new HttpsError('failed-precondition', 'Cambio password obbligatorio prima di utilizzare le funzioni della Commissione.');\n  }\n  return { uid: request.auth.uid, role, claims: request.auth.token };\n}"""
if old not in backend:
    raise SystemExit('Marker requireAuth non trovato')
backend = backend.replace(old, new, 1)

# 2) Porta la flag di cambio password nel token Firebase e nel profilo restituito al browser.
old = """  const claims = {\n    role,\n    scopeClass: record.scopeClass || 'TUTTE',\n    staffAccountId: docSnap.id,\n    ...(expiresAt ? { staffExpiresAt: Math.floor(expiresAt.getTime() / 1000) } : {})\n  };"""
new = """  const claims = {\n    role,\n    scopeClass: record.scopeClass || 'TUTTE',\n    staffAccountId: docSnap.id,\n    mustChangePassword: record.mustChangePassword === true,\n    ...(expiresAt ? { staffExpiresAt: Math.floor(expiresAt.getTime() / 1000) } : {})\n  };"""
if old not in backend:
    raise SystemExit('Marker claims non trovato')
backend = backend.replace(old, new, 1)

old = """      role,\n      scopeClass: record.scopeClass || 'TUTTE',\n      ...(expiresAt ? { expiresAt: expiresAt.toISOString(), expiresOn: expiryLabel(expiresAt) } : {})"""
new = """      role,\n      scopeClass: record.scopeClass || 'TUTTE',\n      mustChangePassword: record.mustChangePassword === true,\n      ...(expiresAt ? { expiresAt: expiresAt.toISOString(), expiresOn: expiryLabel(expiresAt) } : {})"""
if old not in backend:
    raise SystemExit('Marker profile non trovato')
backend = backend.replace(old, new, 1)

# 3) Endpoint dedicato al cambio password bootstrap. Non usa requireAuth perché quella funzione blocca appositamente il token bootstrap.
marker = """exports.managementLogin = onCall({ region: REGION }, async (request) => {"""
change_fn = r"""
exports.changeCommissionPassword = onCall({ region: REGION }, async (request) => {
  if (!request.auth || normalize(request.auth.token.role) !== 'COMMISSIONE') {
    throw new HttpsError('unauthenticated', 'Sessione Commissione richiesta.');
  }
  const accountId = String(request.auth.token.staffAccountId || '').trim();
  const year = String(request.data?.annoScolastico || '').trim();
  const newPassword = String(request.data?.newPassword || '');
  const confirmPassword = String(request.data?.confirmPassword || '');
  if (!accountId || !/^20\d{2}\/20\d{2}$/.test(year)) {
    throw new HttpsError('invalid-argument', 'Account o anno scolastico non validi.');
  }
  if (newPassword !== confirmPassword) {
    throw new HttpsError('invalid-argument', 'Le due password non coincidono.');
  }
  if (newPassword.length < 16 || newPassword.length > 128 || !/[A-Z]/.test(newPassword) || !/[a-z]/.test(newPassword) || !/[0-9]/.test(newPassword) || !/[^A-Za-z0-9]/.test(newPassword)) {
    throw new HttpsError('invalid-argument', 'La nuova password deve contenere almeno 16 caratteri, maiuscole, minuscole, numeri e simboli.');
  }

  const ref = yearlyCollection('gestione_accessi', year).doc(accountId);
  const snap = await ref.get();
  if (!snap.exists) throw new HttpsError('not-found', 'Account Commissione non trovato.');
  const record = snap.data() || {};
  if (normalize(record.role) !== 'COMMISSIONE' || record.active === false) {
    throw new HttpsError('permission-denied', 'Account Commissione non autorizzato.');
  }
  if (!verifyScryptPassword(newPassword, record) && !legacyPasswordMatches(newPassword, record)) {
    const salt = crypto.randomBytes(24).toString('hex');
    const passwordHash = crypto.scryptSync(newPassword, salt, 64).toString('hex');
    await ref.update({
      passwordSalt: salt,
      passwordHash,
      mustChangePassword: false,
      bootstrapAccount: false,
      passwordChangedAt: admin.firestore.FieldValue.serverTimestamp(),
      passwordChangedBy: accountId
    });
  } else {
    throw new HttpsError('invalid-argument', 'La nuova password deve essere diversa dalla password temporanea o precedente.');
  }

  const claims = {
    role: 'COMMISSIONE',
    scopeClass: record.scopeClass || 'TUTTE',
    staffAccountId: accountId,
    mustChangePassword: false
  };
  const customToken = await admin.auth().createCustomToken(`staff-${accountId}-${crypto.randomUUID()}`, claims);
  await auditAdmin({ uid: accountId, role: 'COMMISSIONE' }, 'COMMISSION_PASSWORD_CHANGED', { accountId });
  return {
    ok: true,
    customToken,
    profile: {
      id: accountId,
      name: record.name || 'Commissione Elettorale',
      username: record.username || '',
      role: 'COMMISSIONE',
      mustChangePassword: false
    }
  };
});

"""
if marker not in backend:
    raise SystemExit('Marker managementLogin non trovato')
if 'exports.changeCommissionPassword' not in backend:
    backend = backend.replace(marker, change_fn + marker, 1)

backend_path.write_text(backend, encoding='utf-8')

# FRONTEND
# 4) Registra la callable.
old = """            commissionLogin: httpsCallable(functions, 'commissionLogin'),\n            managementLogin: httpsCallable(functions, 'managementLogin'),"""
new = """            commissionLogin: httpsCallable(functions, 'commissionLogin'),\n            changeCommissionPassword: httpsCallable(functions, 'changeCommissionPassword'),\n            managementLogin: httpsCallable(functions, 'managementLogin'),"""
if old not in front:
    raise SystemExit('Marker SECURE_API non trovato')
front = front.replace(old, new, 1)

# 5) Pagina dedicata nel router.
old = """                case 'adminLogin': renderAdminLogin(container); break;\n                case 'adminPanel': renderAdminPanel(container); break;"""
new = """                case 'adminLogin': renderAdminLogin(container); break;\n                case 'commissionPasswordChange': renderCommissionPasswordChange(container); break;\n                case 'adminPanel': renderAdminPanel(container); break;"""
if old not in front:
    raise SystemExit('Marker router admin non trovato')
front = front.replace(old, new, 1)

# 6) Login: se account bootstrap, niente pannello prima della rotazione.
old = """                const res = await SECURE_API.commissionLogin({ username, password, annoScolastico: configElezioni.annoScolastico });\n                await signInWithCustomToken(auth, res.data.customToken);\n                activeAdminTab = 'config';\n                startTokensListener();\n                resetIdleTimer();\n                showPage('adminPanel');"""
new = """                const res = await SECURE_API.commissionLogin({ username, password, annoScolastico: configElezioni.annoScolastico });\n                await signInWithCustomToken(auth, res.data.customToken);\n                resetIdleTimer();\n                if (res.data?.profile?.mustChangePassword === true) {\n                    showPage('commissionPasswordChange');\n                    return;\n                }\n                activeAdminTab = 'config';\n                startTokensListener();\n                showPage('adminPanel');"""
if old not in front:
    raise SystemExit('Marker checkAdminLogin non trovato')
front = front.replace(old, new, 1)

# 7) UI cambio password obbligatorio.
marker = """        function renderAdminPanel(container) {"""
block = r'''
        function renderCommissionPasswordChange(container) {
            container.innerHTML = `
                <div class="max-w-lg mx-auto bg-white/95 backdrop-blur-md p-8 rounded-2xl shadow-xl border border-amber-200 mt-8 animate-fade-in w-full font-semibold">
                    <div class="text-center mb-6">
                        <i data-lucide="key-round" class="mx-auto w-12 h-12 text-amber-600 mb-2"></i>
                        <h2 class="text-xl font-black text-slate-800">Cambio password obbligatorio</h2>
                        <p class="text-xs text-slate-500 mt-2">La credenziale iniziale della Commissione è temporanea. Prima di accedere al pannello amministrativo devi impostare una password personale.</p>
                    </div>
                    <div class="bg-amber-50 border border-amber-200 rounded-xl p-3 text-[10px] text-amber-950 mb-5">
                        La nuova password deve avere almeno <b>16 caratteri</b> e contenere maiuscole, minuscole, numeri e simboli. Non riutilizzare la password temporanea e non comunicarla via e-mail o chat.
                    </div>
                    <form onsubmit="event.preventDefault(); window.changeInitialCommissionPassword();" class="space-y-4">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Nuova password</label>
                            <input id="commissionNewPwd" type="password" minlength="16" maxlength="128" autocomplete="new-password" required class="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-900 outline-none">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1">Ripeti nuova password</label>
                            <input id="commissionNewPwd2" type="password" minlength="16" maxlength="128" autocomplete="new-password" required class="w-full border border-slate-300 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-900 outline-none">
                        </div>
                        <button type="submit" class="w-full bg-blue-900 hover:bg-blue-800 text-white font-black rounded-xl py-3 text-xs uppercase tracking-wide">Salva nuova password e accedi</button>
                    </form>
                    <button onclick="window.logoutCommissionForcedChange()" class="w-full mt-3 text-[10px] text-slate-500 hover:text-slate-800 underline">Annulla e disconnetti</button>
                </div>`;
            if (window.lucide) lucide.createIcons();
        }

        window.logoutCommissionForcedChange = async function() {
            try { await signOut(auth); } catch(e) {}
            showPage('adminLogin');
        };

        window.changeInitialCommissionPassword = async function() {
            const p1 = document.getElementById('commissionNewPwd')?.value || '';
            const p2 = document.getElementById('commissionNewPwd2')?.value || '';
            if (p1 !== p2) return showNotification('Password diverse','Le due password non coincidono.','error');
            if (p1.length < 16 || !/[A-Z]/.test(p1) || !/[a-z]/.test(p1) || !/[0-9]/.test(p1) || !/[^A-Za-z0-9]/.test(p1)) {
                return showNotification('Password non sufficientemente robusta','Usa almeno 16 caratteri con maiuscole, minuscole, numeri e simboli.','error');
            }
            try {
                const res = await SECURE_API.changeCommissionPassword({
                    annoScolastico: configElezioni.annoScolastico,
                    newPassword: p1,
                    confirmPassword: p2
                });
                await signOut(auth);
                await signInWithCustomToken(auth, res.data.customToken);
                activeAdminTab = 'config';
                startTokensListener();
                resetIdleTimer();
                showNotification('Password aggiornata','La password temporanea è stata revocata. Conserva la nuova password in modo sicuro.','success');
                showPage('adminPanel');
            } catch (e) {
                console.error(e);
                showNotification('Cambio password non riuscito', e?.message || 'Operazione non completata.', 'error');
            }
        };

'''
if marker not in front:
    raise SystemExit('Marker renderAdminPanel non trovato')
if 'function renderCommissionPasswordChange' not in front:
    front = front.replace(marker, block + marker, 1)

front_path.write_text(front, encoding='utf-8')
Path('404.html').write_text(front, encoding='utf-8')
print('Patch Commissione applicata')
