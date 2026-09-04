from pathlib import Path

FILES = [Path('index.html'), Path('404.html')]

NEW_CSP = "default-src 'self'; script-src 'self' 'unsafe-inline' https://www.gstatic.com; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data: https:; connect-src 'self' https://*.googleapis.com https://*.firebaseio.com https://*.cloudfunctions.net https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://elezioni-primo-levi-vercel.vercel.app; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; frame-src 'none'; child-src 'none'; media-src 'none'; form-action 'self'; upgrade-insecure-requests"

MIM_ITEMS = """
        const MIM_PRODUCTION_CONTROLS = Object.freeze({
            dpiaCompleted: 'DPIA / valutazione con il DPO formalizzata e acquisita agli atti',
            providerDocumentationAcquired: 'Documentazione tecnica e contrattuale dei fornitori cloud acquisita',
            cloudDataLocationReviewed: 'Localizzazione, trasferimenti e ruoli privacy dei dati verificati',
            metadataUnlinkabilityReviewed: 'Verifica documentata che log/metadati non consentano correlazione identità-voto',
            structuralSeparationReviewed: 'Separazione strutturale autenticazione/urna verificata e verbalizzata',
            testEnvironmentSeparated: 'Ambiente di collaudo separato logicamente dalla produzione',
            controlledDevicesReady: 'Postazioni scolastiche controllate / kiosk e divieto di dispositivi personali predisposti',
            restoreTestDocumented: 'Backup e prova di ripristino eseguiti e verbalizzati',
            agidConservationPlanApproved: 'Verbali, evidenze, hash e conservazione documentale secondo procedura AgID predisposti',
            providerSecurityReviewed: 'Misure di sicurezza, audit, incident response e continuità dei fornitori riesaminate'
        });

        function mimComplianceState() {
            return { ...(configElezioni.mimCompliance || {}) };
        }

        function mimProductionMissing() {
            const state = mimComplianceState();
            return Object.keys(MIM_PRODUCTION_CONTROLS).filter(k => state[k] !== true);
        }

        window.updateMimComplianceControl = async function(control, value) {
            if (!Object.prototype.hasOwnProperty.call(MIM_PRODUCTION_CONTROLS, control)) return;
            if (!auth.currentUser) return showNotification('Autenticazione richiesta','Accedere come Commissione.','error');
            const previous = { ...(configElezioni.mimCompliance || {}) };
            configElezioni.mimCompliance = { ...previous, [control]: value === true, updatedAt: new Date().toISOString() };
            try {
                await SECURE_API.saveElectionConfig({ config: configElezioni, annoScolastico: configElezioni.annoScolastico });
                window.configElezioni = configElezioni;
                renderCollaudoTab(document.getElementById('admin-tab-content'));
            } catch (e) {
                configElezioni.mimCompliance = previous;
                showNotification('Controllo MIM non salvato', e?.message || 'Operazione non completata.', 'error');
            }
        };

        async function verifyProductionReadiness() {
            const errors = [];
            try {
                const h = await fetch('https://elezioni-primo-levi-vercel.vercel.app/api/health', { cache:'no-store' });
                const j = await h.json();
                if (!h.ok || j.ok !== true || j.backend !== true || j.firebase !== true) errors.push('Backend/Firebase non risulta verde.');
            } catch (e) { errors.push('Backend/Firebase non raggiungibile.'); }
            try {
                const r = await SECURE_API.getRegularityState({ annoScolastico: configElezioni.annoScolastico });
                if (r.data?.readyForVoting !== true) {
                    const missing = Array.isArray(r.data?.missing) ? r.data.missing.join(', ') : 'controlli incompleti';
                    errors.push('Regolarità elettorale incompleta: ' + missing + '.');
                }
            } catch (e) { errors.push('Impossibile verificare i controlli di regolarità.'); }
            const mimMissing = mimProductionMissing();
            if (mimMissing.length) errors.push('Checklist MIM incompleta: ' + mimMissing.map(k => MIM_PRODUCTION_CONTROLS[k]).join(' · '));
            if (configElezioni.bloccaSmartphoneReali === false) errors.push('Blocco best-effort smartphone reali disattivato.');
            return { ok: errors.length === 0, errors };
        }
"""

for p in FILES:
    s = p.read_text(encoding='utf-8')

    # CSP più stretta e rimozione dipendenza font remota.
    import re
    s, n = re.subn(r'<meta http-equiv="Content-Security-Policy" content="[^"]+">', f'<meta http-equiv="Content-Security-Policy" content="{NEW_CSP}">', s, count=1)
    if n != 1: raise SystemExit(f'CSP non trovata in {p}')
    s = s.replace('    <meta name="referrer" content="no-referrer">', '    <meta name="referrer" content="no-referrer">\n    <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">\n    <meta http-equiv="Pragma" content="no-cache">\n    <meta http-equiv="Expires" content="0">', 1)
    s = s.replace("        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');\n        \n", '', 1)
    s = s.replace("font-family: 'Inter', sans-serif;", "font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;", 1)

    # Footer: niente overclaim di conformità.
    s = s.replace('Sistema predisposto secondo requisiti MIM • Segretezza e separazione identità/voto verificate lato server',
                  'Sistema sottoposto a controlli tecnici secondo Allegato MIM 2026 • Idoneità finale subordinata a collaudo, verifiche privacy/DPO e documentazione dei fornitori', 1)

    # Overlay persistente con rientro esplicito.
    old_card = '''            <p class="text-sm text-slate-200 leading-relaxed">\n                La cabina è stata oscurata perché la finestra ha perso il focus, è stato richiesto un tentativo di stampa/cattura\n                oppure è stata abbandonata la modalità protetta. Torna alla finestra elettorale per proseguire.\n            </p>'''
    new_card = old_card + '''\n            <button onclick="enterProtectedCabin()" class="mt-6 px-5 py-3 rounded-xl bg-white text-slate-950 font-black text-sm shadow-lg">RIENTRA NELLA CABINA PROTETTA</button>\n            <p class="mt-3 text-[10px] text-slate-400">Il browser applica misure di deterrenza; una fotografia effettuata con un dispositivo esterno richiede comunque postazione controllata e misure fisiche/organizzative.</p>'''
    if old_card not in s: raise SystemExit(f'Overlay card non trovata in {p}')
    s = s.replace(old_card, new_card, 1)

    s = s.replace("        let protectedFullscreenRequested = false;", "        let protectedFullscreenRequested = false;\n        let protectedCabinEntered = false;", 1)

    old_update = '''        function updateSecureCabinState() {\n            const active = isSensitiveVotingView();\n            document.body.classList.toggle('secure-ballot-active', active);\n            const btn = document.getElementById('secure-cabin-button');\n            if (btn) btn.classList.toggle('hidden', !active);\n        }'''
    new_update = '''        function updateSecureCabinState() {\n            const active = isSensitiveVotingView();\n            document.body.classList.toggle('secure-ballot-active', active);\n            const btn = document.getElementById('secure-cabin-button');\n            if (btn) btn.classList.toggle('hidden', !active);\n            if (active && !protectedCabinEntered) showPrivacyShield('enter-sensitive-view');\n            if (!active) {\n                protectedCabinEntered = false;\n                protectedFullscreenRequested = false;\n                document.getElementById('privacy-shield')?.classList.remove('active');\n            }\n        }'''
    if old_update not in s: raise SystemExit(f'updateSecureCabinState non trovato in {p}')
    s = s.replace(old_update, new_update, 1)

    s = s.replace("            el.dataset.reason = reason;\n            el.classList.add('active');", "            el.dataset.reason = reason;\n            protectedCabinEntered = false;\n            el.classList.add('active');", 1)

    old_hide = '''        function hidePrivacyShieldSoon() {\n            clearTimeout(privacyShieldTimer);\n            privacyShieldTimer = setTimeout(() => {\n                if (document.visibilityState === 'visible' && document.hasFocus()) {\n                    document.getElementById('privacy-shield')?.classList.remove('active');\n                }\n            }, 450);\n        }'''
    new_hide = '''        function hidePrivacyShieldSoon(force = false) {\n            clearTimeout(privacyShieldTimer);\n            privacyShieldTimer = setTimeout(() => {\n                if ((force || protectedCabinEntered) && document.visibilityState === 'visible' && document.hasFocus()) {\n                    document.getElementById('privacy-shield')?.classList.remove('active');\n                }\n            }, 150);\n        }'''
    if old_hide not in s: raise SystemExit(f'hidePrivacyShieldSoon non trovato in {p}')
    s = s.replace(old_hide, new_hide, 1)

    s = s.replace("                protectedFullscreenRequested = true;\n                hidePrivacyShieldSoon();", "                protectedFullscreenRequested = true;\n                protectedCabinEntered = true;\n                hidePrivacyShieldSoon(true);", 1)
    s = s.replace("            else hidePrivacyShieldSoon();", "            else { /* resta oscurato finché l’elettore non rientra esplicitamente */ }", 1)
    s = s.replace("        window.addEventListener('focus', hidePrivacyShieldSoon);", "        window.addEventListener('focus', () => { /* nessun auto-sblocco */ });", 1)
    s = s.replace("        window.addEventListener('afterprint', hidePrivacyShieldSoon);", "        window.addEventListener('afterprint', () => showPrivacyShield('afterprint'));", 1)
    s = s.replace("if (isSensitiveVotingView()) { e.preventDefault(); showPrivacyShield('contextmenu'); hidePrivacyShieldSoon(); }", "if (isSensitiveVotingView()) { e.preventDefault(); showPrivacyShield('contextmenu'); }", 1)
    s = s.replace("if (isSensitiveVotingView()) { e.preventDefault(); showPrivacyShield('copy'); hidePrivacyShieldSoon(); }", "if (isSensitiveVotingView()) { e.preventDefault(); showPrivacyShield('copy'); }", 1)
    s = s.replace("                showPrivacyShield('capture-key');\n                hidePrivacyShieldSoon();", "                showPrivacyShield('capture-key');", 1)
    s = s.replace("            if (isSensitiveVotingView()) hidePrivacyShieldSoon();", "            if (isSensitiveVotingView()) showPrivacyShield('devicechange');", 1)

    # Blocco best-effort smartphone reali + input più sicuro.
    s = s.replace('            modalitaProva: false,', '            modalitaProva: false,\n            bloccaSmartphoneReali: true,\n            mimCompliance: {},', 1)
    s = s.replace('<input type="text" id="tokenInput" placeholder="ES: STU-4A-X2Y9"', '<input type="text" id="tokenInput" autocomplete="off" autocapitalize="characters" autocorrect="off" spellcheck="false" inputmode="text" placeholder="ES: STU-4A-X2Y9"', 1)
    s = s.replace('Digita il codice segreto (Token) per votare dal tuo dispositivo.', 'Digita il codice segreto (Token) esclusivamente dalla postazione autorizzata predisposta per la votazione.', 1)

    login_anchor = "        window.handleStudentLogin = async function() {"
    if login_anchor not in s: raise SystemExit(f'handleStudentLogin non trovato in {p}')
    smartphone_fn = '''        function isLikelyPersonalSmartphone() {\n            const ua = String(navigator.userAgent || '');\n            const mobile = /Android|iPhone|iPod|Windows Phone|IEMobile|Opera Mini/i.test(ua);\n            const ipadDesktopMode = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;\n            return mobile && !ipadDesktopMode;\n        }\n\n'''
    s = s.replace(login_anchor, smartphone_fn + login_anchor, 1)
    token_check = "            if (!token) { errEl.textContent='Inserisci il Token.'; errEl.classList.remove('hidden'); return; }"
    token_gate = token_check + "\n            if (!configElezioni.modalitaProva && configElezioni.bloccaSmartphoneReali !== false && isLikelyPersonalSmartphone()) { errEl.textContent='Per la votazione reale è richiesta una postazione autorizzata dell’Istituto. Il voto da smartphone personale è bloccato.'; errEl.classList.remove('hidden'); return; }"
    if token_check not in s: raise SystemExit(f'token check non trovato in {p}')
    s = s.replace(token_check, token_gate, 1)

    # Checklist MIM e gate produzione.
    coll_anchor = "        function renderCollaudoTab(container) {"
    if coll_anchor not in s: raise SystemExit(f'renderCollaudoTab non trovato in {p}')
    s = s.replace(coll_anchor, MIM_ITEMS + "\n" + coll_anchor, 1)

    checklist_anchor = '''                    <div class="bg-slate-900 text-white rounded-2xl p-5">\n                        <h4 class="font-black text-sm mb-3">Checklist prima dell'attivazione reale</h4>'''
    mim_ui = '''                    <div class="bg-white rounded-2xl border-2 border-blue-200 p-5">\n                        <div class="flex items-start justify-between gap-4 mb-3"><div><h4 class="font-black text-blue-950 text-sm">Gate MIM 2026 — documentazione e ambiente reale</h4><p class="text-[10px] text-slate-500 mt-1">Una voce va confermata solo dopo verifica documentale/tecnica reale. Il codice non sostituisce DPO, atti dell’Istituto o documentazione dei fornitori.</p></div><span class="text-[10px] font-black px-2 py-1 rounded ${mimProductionMissing().length ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'}">${mimProductionMissing().length ? mimProductionMissing().length + ' MANCANTI' : 'COMPLETO'}</span></div>\n                        <div class="grid md:grid-cols-2 gap-2">\n                            ${Object.entries(MIM_PRODUCTION_CONTROLS).map(([k,label]) => `<label class="flex gap-2 items-start p-3 rounded-xl border ${mimComplianceState()[k]===true?'bg-emerald-50 border-emerald-200':'bg-slate-50'}"><input type="checkbox" class="mt-0.5" ${mimComplianceState()[k]===true?'checked':''} onchange="updateMimComplianceControl('${k}',this.checked)"><span class="text-[10px] font-bold text-slate-800">${label}</span></label>`).join('')}\n                        </div>\n                    </div>\n\n'''
    if checklist_anchor not in s: raise SystemExit(f'checklist anchor non trovato in {p}')
    s = s.replace(checklist_anchor, mim_ui + checklist_anchor, 1)

    setmode_anchor = "            const previous = configElezioni.modalitaProva === true;"
    gate = '''            if (enabled !== true) {\n                const readiness = await verifyProductionReadiness();\n                if (!readiness.ok) {\n                    return showNotification('Modalità reale BLOCCATA', readiness.errors.join(' | '), 'error');\n                }\n                if (!window.confirm('Tutti i controlli tecnici, MIM, privacy/DPO e organizzativi risultano completati. Confermare il passaggio alla MODALITÀ REALE?')) return;\n            }\n'''
    if setmode_anchor not in s: raise SystemExit(f'set mode anchor non trovato in {p}')
    s = s.replace(setmode_anchor, gate + setmode_anchor, 1)

    p.write_text(s, encoding='utf-8')

print('FINAL_MIM_HARDENING_OK')
