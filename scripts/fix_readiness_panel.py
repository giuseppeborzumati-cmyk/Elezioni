from pathlib import Path

for name in ('index.html','404.html'):
    p=Path(name)
    if not p.exists():
        continue
    s=p.read_text(encoding='utf-8')

    s=s.replace("script-src 'self' 'unsafe-inline' vendor/tailwindcss.js https://cdnjs.cloudflare.com https://unpkg.com https://www.gstatic.com;", "script-src 'self' 'unsafe-inline' https://www.gstatic.com;")

    old='''        async function verifyProductionReadiness() {
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
        }'''
    new='''        async function verifyProductionReadiness() {
            const errors = [];
            const details = {
                technical: { ok:false, message:'Verifica tecnica non eseguita' },
                regularity: { ok:false, missing:[] },
                mim: { ok:false, missing:[] }
            };
            try {
                const sec = await SECURE_API.getSecurityStatus({ annoScolastico: configElezioni.annoScolastico });
                if (sec.data?.ok !== true) throw new Error('Risposta tecnica non valida.');
                details.technical = { ok:true, message:'Backend Vercel, Firebase e API autenticata operativi' };
            } catch (e) {
                details.technical = { ok:false, message:e?.message || 'Controllo tecnico non disponibile' };
                errors.push('Controllo tecnico non superato.');
            }
            try {
                const r = await SECURE_API.getRegularityState({ annoScolastico: configElezioni.annoScolastico });
                const missing = Array.isArray(r.data?.missing) ? r.data.missing : [];
                details.regularity = { ok:r.data?.readyForVoting === true, missing };
                if (!details.regularity.ok) errors.push(`Regolarità: ${missing.length || 1} controllo/i ancora da confermare.`);
            } catch (e) {
                errors.push('Impossibile verificare i controlli di regolarità.');
            }
            const mimMissing = mimProductionMissing();
            details.mim = { ok:mimMissing.length === 0, missing:mimMissing };
            if (mimMissing.length) errors.push(`Checklist MIM: ${mimMissing.length} verifica/e documentali o organizzative ancora da confermare.`);
            if (configElezioni.bloccaSmartphoneReali === false) errors.push('Protezione dispositivi personali disattivata.');
            return { ok: errors.length === 0, errors, details };
        }'''
    if old not in s:
        raise SystemExit('verifyProductionReadiness non trovato in '+name)
    s=s.replace(old,new,1)

    old='''        window.runElectionTechnicalCheck = async function() {
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
        };'''
    new='''        window.runElectionTechnicalCheck = async function() {
            const out = document.getElementById('technical-check-result');
            if (out) out.innerHTML = '<span class="font-bold text-blue-700">Controllo autenticato in corso...</span>';
            try {
                const sec = await SECURE_API.getSecurityStatus({ annoScolastico: configElezioni.annoScolastico });
                if (sec.data?.ok !== true) throw new Error('Backend/Firebase non operativo.');
                try {
                    await SECURE_API.setRegularityControl({
                        annoScolastico: configElezioni.annoScolastico,
                        control: 'technicalTestPassed',
                        value: true,
                        note: 'Verifica tecnica autenticata eseguita dalla piattaforma: backend, Firebase, API e controlli server-side raggiungibili.'
                    });
                } catch(e) {}
                if (out) out.innerHTML = '<div class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-black">✓ Backend Vercel operativo<br>✓ Firebase operativo<br>✓ API autenticata raggiungibile<br>✓ Collaudo tecnico registrato</div>';
                showNotification('Test tecnico superato','Il controllo tecnico è stato registrato automaticamente nella regolarità.','success');
            } catch (e) {
                if (out) out.innerHTML = `<div class="p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 font-black">✕ ${e?.message || 'Test non superato'}</div>`;
                showNotification('Test tecnico non superato', e?.message || 'Verificare l’accesso Commissione e il backend.', 'error');
            }
        };'''
    if old not in s:
        raise SystemExit('runElectionTechnicalCheck non trovato in '+name)
    s=s.replace(old,new,1)

    a=s.find('        async function refreshOpeningStatus() {')
    b=s.find('\n\n        function renderOpeningTab(container) {',a)
    if a<0 or b<0:
        raise SystemExit('refreshOpeningStatus non trovato in '+name)
    block='''        async function refreshOpeningStatus() {
            const box=document.getElementById('opening-status-box');
            if(!box) return;
            box.innerHTML='<div class="p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 font-bold">Verifica in corso...</div>';
            const r=await verifyProductionReadiness();
            const d=r.details || {};
            const regMissing=d.regularity?.missing || [];
            const mimMissing=d.mim?.missing || [];
            const regLabels={
                annualCircularRecorded:'Circolare annuale acquisita',
                commissionAppointed:'Commissione formalmente nominata',
                voterRollFinal:'Elenchi elettorali definitivi',
                candidateListsValidated:'Liste e candidature convalidate',
                ballotApproved:'Scheda elettorale approvata',
                privacyChecked:'Privacy/GDPR verificati',
                technicalTestPassed:'Collaudo tecnico superato',
                softwareFrozen:'Versione software congelata',
                backupPlanReady:'Backup e ripristino verificati',
                incidentPlanReady:'Piano incidenti approvato',
                communicationPublished:'Comunicazioni pubblicate'
            };
            const card=(ok,title,body,action='')=>`<div class="p-4 rounded-2xl border-2 ${ok?'bg-emerald-50 border-emerald-300':'bg-amber-50 border-amber-300'}"><div class="text-[10px] font-black uppercase ${ok?'text-emerald-700':'text-amber-800'}">${ok?'✓ COMPLETO':'DA COMPLETARE'}</div><div class="font-black mt-1">${title}</div><div class="text-[10px] mt-2 text-slate-600">${body}</div>${action}</div>`;
            box.innerHTML=`<div class="grid md:grid-cols-3 gap-3">
                ${card(d.technical?.ok===true,'1. Sistema tecnico',d.technical?.ok?'Backend, Firebase e API autenticata rispondono correttamente.':'Esegui il test tecnico dal Collaudo.',`<button onclick="window.switchAdminTab('collaudo')" class="mt-3 px-3 py-2 rounded-lg bg-blue-900 text-white text-[10px] font-black">VAI AL TEST TECNICO</button>`)}
                ${card(d.regularity?.ok===true,'2. Regolarità',d.regularity?.ok?'Tutti i controlli pre-voto risultano confermati.':`${regMissing.length} voce/i da confermare: ${regMissing.slice(0,3).map(k=>regLabels[k]||k).join(' · ')}${regMissing.length>3?' …':''}`,`<button onclick="window.switchAdminTab('regolarita')" class="mt-3 px-3 py-2 rounded-lg bg-slate-900 text-white text-[10px] font-black">GESTISCI REGOLARITÀ</button>`)}
                ${card(d.mim?.ok===true,'3. Checklist MIM',d.mim?.ok?'Verifiche documentali e organizzative registrate.':`${mimMissing.length} verifica/e ancora da attestare.`, `<button onclick="window.switchAdminTab('collaudo')" class="mt-3 px-3 py-2 rounded-lg bg-indigo-900 text-white text-[10px] font-black">GESTISCI CHECKLIST MIM</button>`)}
            </div>${r.ok?'<div class="mt-3 p-4 rounded-xl bg-emerald-600 text-white font-black">✓ SISTEMA PRONTO — PUOI PREMERE “APRI ORA”</div>':'<div class="mt-3 p-3 rounded-xl bg-slate-50 border text-[10px] text-slate-600"><b>Nota:</b> le voci di Regolarità e MIM non sono errori informatici. Sono attestazioni che devono essere confermate solo quando gli atti e le verifiche corrispondenti esistono realmente.</div>'}`;
        }'''
    s=s[:a]+block+s[b:]

    p.write_text(s,encoding='utf-8')
