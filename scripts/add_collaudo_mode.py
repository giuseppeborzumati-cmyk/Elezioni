from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

def replace_once(old, new, label):
    global s
    if old not in s:
        raise SystemExit(f'Anchor non trovato: {label}')
    s = s.replace(old, new, 1)

replace_once(
    '</header>\n\n    <main',
    '''</header>\n\n    <div id="test-mode-banner" class="hidden sticky top-0 z-40 bg-amber-400 text-slate-950 border-b-2 border-amber-600 shadow-md">\n        <div class="container mx-auto px-4 py-2 text-center text-xs md:text-sm font-black uppercase tracking-wide">\n            MODALITÀ DI PROVA / COLLAUDO ATTIVA — NESSUN VOTO DI PROVA VIENE REGISTRATO NELLE URNE REALI\n        </div>\n    </div>\n\n    <main''',
    'banner prova'
)

replace_once(
    'annoScolastico: "2026/2027",\n            tipologiaElezioni:',
    'annoScolastico: "2026/2027",\n            modalitaProva: false,\n            tipologiaElezioni:',
    'flag modalitaProva'
)

s = s.replace(
    'window.configElezioni = configElezioni;',
    'window.configElezioni = configElezioni;\n        setTimeout(() => { try { updateTestModeBanner(); } catch(e) {} }, 0);'
)

replace_once(
    "{ id: 'workflow_digitale', label: '11. Workflow Digitale & Verbali' },\n                { id: 'regolarita', label: '12. Regolarità Elettorale' }",
    "{ id: 'workflow_digitale', label: '11. Workflow Digitale & Verbali' },\n                { id: 'regolarita', label: '12. Regolarità Elettorale' },\n                { id: 'collaudo', label: '13. Versione di Prova / Collaudo' }",
    'tab collaudo'
)

anchor = '        function renderActiveAdminTab() {'
if anchor not in s:
    raise SystemExit('Anchor non trovato: renderActiveAdminTab')

block = r'''
        function updateTestModeBanner() {
            const banner = document.getElementById('test-mode-banner');
            if (!banner) return;
            banner.classList.toggle('hidden', configElezioni.modalitaProva !== true);
        }

        function makeTestVoter(token) {
            const t = String(token || '').trim().toUpperCase();
            const common = {
                sessionId: `TEST-${Date.now()}-${Math.random().toString(36).slice(2)}`,
                indirizzo: 'COLLAUDO',
                voted_consiglio: false,
                voted_istituto: false,
                voted_consulta: false,
                voted_classe_studente: false,
                voted_classe_genitore: false
            };
            if (t === 'PROVA-STUDENTE-1A') return { ...common, tipo: 'STUDENTE', classe: '1A' };
            if (t === 'PROVA-GENITORE-1A') return { ...common, tipo: 'GENITORE', classe: '1A' };
            return null;
        }

        function readElectionTestLog() {
            try { return JSON.parse(localStorage.getItem('levi-election-test-log') || '[]'); }
            catch(e) { return []; }
        }

        function writeElectionTestLog(rows) {
            try { localStorage.setItem('levi-election-test-log', JSON.stringify(rows.slice(-50))); } catch(e) {}
        }

        function renderCollaudoTab(container) {
            const active = configElezioni.modalitaProva === true;
            const log = readElectionTestLog();
            const last = log.length ? log[log.length - 1] : null;
            container.innerHTML = `
                <div class="space-y-5">
                    <div class="rounded-2xl border-2 ${active ? 'border-amber-400 bg-amber-50' : 'border-emerald-200 bg-emerald-50'} p-5 shadow-sm">
                        <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                            <div>
                                <div class="text-[10px] font-black uppercase tracking-widest ${active ? 'text-amber-700' : 'text-emerald-700'}">Stato collaudo</div>
                                <h3 class="text-lg font-black text-slate-900 mt-1">${active ? 'VERSIONE DI PROVA ATTIVA' : 'MODALITÀ REALE / PRODUZIONE'}</h3>
                                <p class="text-xs text-slate-600 mt-2 max-w-3xl">Quando la modalità prova è attiva, i token di collaudo percorrono tutte le schermate di voto ma l'invio finale viene simulato nel browser e non scrive nelle urne Firestore reali.</p>
                            </div>
                            <div class="flex flex-wrap gap-2">
                                ${active
                                    ? `<button onclick="setElectionTestMode(false)" class="px-4 py-2 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-black">DISATTIVA PROVA E TORNA AL REALE</button>`
                                    : `<button onclick="setElectionTestMode(true)" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-slate-950 text-xs font-black">ATTIVA VERSIONE DI PROVA</button>`}
                            </div>
                        </div>
                    </div>

                    <div class="grid md:grid-cols-2 gap-4">
                        <div class="bg-white rounded-2xl border p-5">
                            <h4 class="font-black text-slate-900 text-sm mb-3">Token di collaudo</h4>
                            <div class="space-y-2 text-xs">
                                <div class="p-3 bg-slate-50 border rounded-xl"><b>Studente 1A:</b> <code class="font-black">PROVA-STUDENTE-1A</code></div>
                                <div class="p-3 bg-slate-50 border rounded-xl"><b>Genitore 1A:</b> <code class="font-black">PROVA-GENITORE-1A</code></div>
                            </div>
                            <p class="text-[11px] text-slate-500 mt-3">Questi token funzionano esclusivamente quando la modalità prova è attiva e non corrispondono a credenziali reali presenti nel registro elettorale.</p>
                        </div>
                        <div class="bg-white rounded-2xl border p-5">
                            <h4 class="font-black text-slate-900 text-sm mb-3">Diagnostica tecnica reale</h4>
                            <p class="text-xs text-slate-600 mb-3">Controlla backend Vercel, collegamento Firebase e stato di sicurezza senza inserire voti.</p>
                            <button onclick="runElectionTechnicalCheck()" class="px-4 py-2 rounded-xl bg-blue-900 hover:bg-blue-950 text-white text-xs font-black">ESEGUI TEST BACKEND / FIREBASE</button>
                            <div id="technical-check-result" class="mt-3 text-xs"></div>
                        </div>
                    </div>

                    <div class="bg-white rounded-2xl border p-5">
                        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                            <div>
                                <h4 class="font-black text-slate-900 text-sm">Registro locale prove</h4>
                                <p class="text-xs text-slate-500">Memorizza solo data, tipo elettore, classe e tipologie di scheda testate; non memorizza preferenze.</p>
                            </div>
                            <button onclick="clearElectionTestLog()" class="px-3 py-2 rounded-xl border border-red-200 text-red-700 hover:bg-red-50 text-xs font-black">AZZERA REGISTRO PROVE</button>
                        </div>
                        <div class="mt-3 text-xs text-slate-700">Prove completate su questo dispositivo: <b>${log.length}</b>${last ? ` — ultima: ${new Date(last.at).toLocaleString('it-IT')}` : ''}</div>
                    </div>

                    <div class="bg-slate-900 text-white rounded-2xl p-5">
                        <h4 class="font-black text-sm mb-3">Checklist prima dell'attivazione reale</h4>
                        <div class="grid md:grid-cols-2 gap-x-6 gap-y-2 text-xs">
                            <div>☐ Accesso Commissione e cambio password verificati</div>
                            <div>☐ Backend/Firebase: test tecnico verde</div>
                            <div>☐ Registro studenti e genitori caricato</div>
                            <div>☐ Liste e candidati verificati</div>
                            <div>☐ Date/orari Europe/Rome corretti</div>
                            <div>☐ Percorso studente provato fino alla conferma</div>
                            <div>☐ Percorso genitore provato fino alla conferma</div>
                            <div>☐ Modalità prova DISATTIVATA prima dell'apertura</div>
                            <div>☐ Controlli di regolarità completati</div>
                            <div>☐ Backup/piano incidenti e versione software congelata</div>
                        </div>
                    </div>
                </div>`;
            if (window.lucide) lucide.createIcons();
        }

        window.setElectionTestMode = async function(enabled) {
            if (!auth.currentUser) return showNotification('Autenticazione richiesta','Accedere come Commissione per modificare la modalità di esercizio.','error');
            const previous = configElezioni.modalitaProva === true;
            configElezioni.modalitaProva = enabled === true;
            configElezioni.modalitaProvaUpdatedAt = new Date().toISOString();
            try {
                await SECURE_API.saveElectionConfig({ config: configElezioni, annoScolastico: configElezioni.annoScolastico });
                window.configElezioni = configElezioni;
                updateTestModeBanner();
                showNotification(
                    configElezioni.modalitaProva ? 'Modalità prova attivata' : 'Modalità reale ripristinata',
                    configElezioni.modalitaProva ? 'I test non scriveranno nelle urne reali.' : 'I token di prova sono stati disabilitati. Verificare la checklist prima dell’apertura.',
                    configElezioni.modalitaProva ? 'info' : 'success'
                );
                renderCollaudoTab(document.getElementById('admin-tab-content'));
            } catch (e) {
                configElezioni.modalitaProva = previous;
                updateTestModeBanner();
                showNotification('Modifica non salvata', e?.message || 'Impossibile aggiornare la modalità di esercizio.', 'error');
            }
        };

        window.runElectionTechnicalCheck = async function() {
            const out = document.getElementById('technical-check-result');
            if (out) out.innerHTML = '<span class="font-bold text-blue-700">Controllo in corso...</span>';
            try {
                const healthRes = await fetch('https://elezioni-primo-levi-vercel.vercel.app/api/health', { cache: 'no-store' });
                const health = await healthRes.json();
                if (!healthRes.ok || health.ok !== true || health.backend !== true || health.firebase !== true) throw new Error('Backend/Firebase non operativo.');
                if (auth.currentUser) {
                    await SECURE_API.getSecurityStatus({ annoScolastico: configElezioni.annoScolastico });
                }
                if (out) out.innerHTML = '<div class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-black">✓ Backend Vercel operativo<br>✓ Firebase operativo<br>✓ API protetta raggiungibile</div>';
                showNotification('Test tecnico superato','Backend, Firebase e API risultano raggiungibili.','success');
            } catch (e) {
                if (out) out.innerHTML = `<div class="p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 font-black">✕ ${e?.message || 'Test non superato'}</div>`;
                showNotification('Test tecnico non superato', e?.message || 'Verificare il backend prima di procedere.', 'error');
            }
        };

        window.clearElectionTestLog = function() {
            try { localStorage.removeItem('levi-election-test-log'); } catch(e) {}
            renderCollaudoTab(document.getElementById('admin-tab-content'));
            showNotification('Registro prove azzerato','Sono stati eliminati solo i log locali di collaudo.','success');
        };

'''
s = s.replace(anchor, block + anchor, 1)

replace_once(
    "else if(activeAdminTab === 'regolarita') renderRegularityTab(content);",
    "else if(activeAdminTab === 'regolarita') renderRegularityTab(content);\n            else if(activeAdminTab === 'collaudo') renderCollaudoTab(content);",
    'router collaudo'
)

old_login = """const ws=votingWindowStatus();
                if(ws.configured && !ws.open) throw new Error(ws.reason==='before'?'Le votazioni non sono ancora aperte.':'Le votazioni sono terminate.');
                const res=await SECURE_API.validateVoterToken({token, annoScolastico:configElezioni.annoScolastico});
                const d=res.data;"""
new_login = """if(!configElezioni.modalitaProva) {
                    const ws=votingWindowStatus();
                    if(ws.configured && !ws.open) throw new Error(ws.reason==='before'?'Le votazioni non sono ancora aperte.':'Le votazioni sono terminate.');
                }
                let d;
                if(configElezioni.modalitaProva) {
                    d = makeTestVoter(token);
                    if(!d) throw new Error('Modalità prova attiva: utilizzare PROVA-STUDENTE-1A oppure PROVA-GENITORE-1A.');
                } else {
                    const res=await SECURE_API.validateVoterToken({token, annoScolastico:configElezioni.annoScolastico});
                    d=res.data;
                }"""
replace_once(old_login, new_login, 'login token prova')

old_vote = """const payload={ sessionId:secureVotingSession, annoScolastico:configElezioni.annoScolastico, ballots:cartVotes };
                const res=await SECURE_API.castVote(payload);
                secureVotingSession=null; currentUserData=null; cartVotes={consiglio:null,istituto:null,consulta:null,classeStudente:null,classeGenitore:null};
                showPage('success', !!res.data.fullyCompleted);"""
new_vote = """const payload={ sessionId:secureVotingSession, annoScolastico:configElezioni.annoScolastico, ballots:cartVotes };
                let res;
                if(configElezioni.modalitaProva) {
                    const types = Object.entries(cartVotes).filter(([,v]) => !!v).map(([k]) => k);
                    const rows = readElectionTestLog();
                    rows.push({ at:new Date().toISOString(), tipo:currentUserData?.tipo||'TEST', classe:currentUserData?.classe||'', schede:types });
                    writeElectionTestLog(rows);
                    res={data:{fullyCompleted:true,testMode:true}};
                    showNotification('Voto di prova completato','Percorso verificato. Nessuna scheda è stata scritta nelle urne reali.','success');
                } else {
                    res=await SECURE_API.castVote(payload);
                }
                secureVotingSession=null; currentUserData=null; cartVotes={consiglio:null,istituto:null,consulta:null,classeStudente:null,classeGenitore:null};
                showPage('success', !!res.data.fullyCompleted);"""
replace_once(old_vote, new_vote, 'invio voto prova')

for required in ['Versione di Prova / Collaudo','PROVA-STUDENTE-1A','runElectionTechnicalCheck','modalitaProva']:
    if required not in s:
        raise SystemExit(f'Patch incompleta: manca {required}')

p.write_text(s, encoding='utf-8')
Path('404.html').write_text(s, encoding='utf-8')
print('PATCH_COLLAUDO_OK')
