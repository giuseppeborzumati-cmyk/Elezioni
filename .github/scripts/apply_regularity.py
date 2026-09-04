from pathlib import Path


def before(text, marker, block):
    if block.strip() in text:
        return text
    if marker not in text:
        raise SystemExit(f'Marker mancante: {marker[:70]}')
    return text.replace(marker, block + '\n' + marker, 1)

# ================= BACKEND =================
p = Path('functions/index.js')
t = p.read_text(encoding='utf-8')

if 'REGULARITY_PRE_VOTE_CONTROLS' not in t:
    t = before(t, "const yearSuffix = (year) => String(year || '2026/2027').replace('/', '_');", r'''const REGULARITY_PRE_VOTE_CONTROLS = Object.freeze([
  'annualCircularRecorded','commissionAppointed','voterRollFinal','candidateListsValidated',
  'ballotApproved','privacyChecked','technicalTestPassed','softwareFrozen',
  'backupPlanReady','incidentPlanReady','communicationPublished'
]);
const REGULARITY_ALL_CONTROLS = new Set([...REGULARITY_PRE_VOTE_CONTROLS,'finalArchiveSealed','appealWindowClosed']);
const regularityStateRef = (year) => yearlyCollection('regolarita', year).doc('state');
const regularityAppeals = (year) => yearlyCollection('reclami_ricorsi', year);
const regularityEvents = (year) => yearlyCollection('eventi_procedimento', year);''')

if 'function emptyRegularityState()' not in t:
    t = before(t, 'async function authenticateStaff({ username, password, requestedRole, year }) {', r'''function emptyRegularityState() {
  return {
    annualCircularRecorded:false,commissionAppointed:false,voterRollFinal:false,candidateListsValidated:false,
    ballotApproved:false,privacyChecked:false,technicalTestPassed:false,softwareFrozen:false,
    backupPlanReady:false,incidentPlanReady:false,communicationPublished:false,resultsPublished:false,
    appealWindowClosed:false,finalArchiveSealed:false,legalHold:false,procedureClosed:false,
    emergencySuspended:false,notes:{}
  };
}
async function loadRegularityState(year) {
  const snap = await regularityStateRef(year).get();
  return {...emptyRegularityState(),...(snap.exists ? snap.data() : {})};
}
function regularityMissing(state) { return REGULARITY_PRE_VOTE_CONTROLS.filter(k => state[k] !== true); }
function timestampIso(v) {
  if (!v) return null;
  if (typeof v.toDate === 'function') return v.toDate().toISOString();
  const d = v instanceof Date ? v : new Date(v); return Number.isNaN(d.getTime()) ? null : d.toISOString();
}
function serializeRegularityState(state) {
  const out={...state}; ['updatedAt','resultsPublishedAt','procedureClosedAt','lastIncidentAt'].forEach(k=>{if(out[k])out[k]=timestampIso(out[k]);}); return out;
}
async function assertElectionReadyForVoting(year) {
  const s=await loadRegularityState(year), missing=regularityMissing(s);
  if(s.procedureClosed) throw new HttpsError('failed-precondition','Procedimento elettorale definitivamente chiuso.');
  if(s.emergencySuspended) throw new HttpsError('failed-precondition','Votazione sospesa dalla Commissione per evento verbalizzato.');
  if(missing.length) throw new HttpsError('failed-precondition',`Apertura bloccata: controlli di regolarità incompleti (${missing.join(', ')}).`);
}''')

needle="const config = await loadElectionConfig(year);\n  assertVotingOpen(config);"
if 'await assertElectionReadyForVoting(year);' not in t:
    if t.count(needle) < 2: raise SystemExit('Punti preflight voto non trovati')
    t=t.replace(needle,"const config = await loadElectionConfig(year);\n  await assertElectionReadyForVoting(year);\n  assertVotingOpen(config);",2)

if 'exports.getRegularityState' not in t:
    t = before(t, "exports.getSecurityStatus = onCall({ region: REGION }, async (request) => {", r'''exports.getRegularityState = onCall({region:REGION}, async request => {
  requireAuth(request,['COMMISSIONE','DIRIGENTE','VICEPRESIDE','DSGA','SEGRETERIA']);
  const year=request.data?.annoScolastico, state=await loadRegularityState(year);
  const snap=await regularityAppeals(year).orderBy('filedAt','desc').limit(100).get();
  const appeals=snap.docs.map(d=>{const x=d.data()||{};return{id:d.id,protocolRef:x.protocolRef||'',subject:x.subject||'',status:x.status||'OPEN',decisionRef:x.decisionRef||'',filedAt:timestampIso(x.filedAt),decidedAt:timestampIso(x.decidedAt)}});
  const missing=regularityMissing(state);
  return{state:serializeRegularityState(state),appeals,missing,readyForVoting:missing.length===0&&!state.emergencySuspended&&!state.procedureClosed};
});

exports.setRegularityControl = onCall({region:REGION}, async request => {
  const actor=requireAuth(request,['COMMISSIONE']),year=request.data?.annoScolastico;
  const control=String(request.data?.control||''),value=request.data?.value===true,note=String(request.data?.note||'').trim().slice(0,1000);
  if(!REGULARITY_ALL_CONTROLS.has(control)) throw new HttpsError('invalid-argument','Controllo non valido.');
  const config=await loadElectionConfig(year);
  if(REGULARITY_PRE_VOTE_CONTROLS.includes(control)&&electionPhase(config)!=='BEFORE') throw new HttpsError('failed-precondition','I controlli preliminari non sono modificabili dopo l’apertura della finestra elettorale.');
  const ref=regularityStateRef(year);
  await db.runTransaction(async tx=>{const snap=await tx.get(ref),cur={...emptyRegularityState(),...(snap.exists?snap.data():{})};tx.set(ref,{[control]:value,notes:{...(cur.notes||{}),[control]:note},updatedAt:admin.firestore.FieldValue.serverTimestamp(),updatedBy:actor.uid},{merge:true});});
  await regularityEvents(year).add({type:'CONTROL_UPDATE',control,value,note,actorUid:actor.uid,at:admin.firestore.FieldValue.serverTimestamp()});
  await auditAdmin(actor,'REGULARITY_CONTROL_UPDATE',{control,value}); return{ok:true};
});

exports.recordResultsPublication = onCall({region:REGION}, async request => {
  const actor=requireAuth(request,['COMMISSIONE']),year=request.data?.annoScolastico;
  const protocolRef=String(request.data?.protocolRef||'').trim().slice(0,160), appealDeadline=String(request.data?.appealDeadline||'').trim();
  if(!protocolRef||!/^\d{4}-\d{2}-\d{2}$/.test(appealDeadline)) throw new HttpsError('invalid-argument','Inserire estremi pubblicazione e termine ricorsi AAAA-MM-GG.');
  if(electionPhase(await loadElectionConfig(year))==='OPEN') throw new HttpsError('failed-precondition','Non è possibile pubblicare risultati a urne aperte.');
  await regularityStateRef(year).set({resultsPublished:true,resultsPublishedAt:admin.firestore.FieldValue.serverTimestamp(),resultsPublicationProtocol:protocolRef,appealDeadline,appealWindowClosed:false,legalHold:true,updatedAt:admin.firestore.FieldValue.serverTimestamp(),updatedBy:actor.uid},{merge:true});
  await regularityEvents(year).add({type:'RESULTS_PUBLICATION',protocolRef,appealDeadline,actorUid:actor.uid,at:admin.firestore.FieldValue.serverTimestamp()});
  await auditAdmin(actor,'RESULTS_PUBLICATION_RECORDED',{protocolRef,appealDeadline}); return{ok:true};
});

exports.fileElectoralAppeal = onCall({region:REGION}, async request => {
  const actor=requireAuth(request,['COMMISSIONE']),year=request.data?.annoScolastico;
  const protocolRef=String(request.data?.protocolRef||'').trim().slice(0,160),subject=String(request.data?.subject||'').trim().slice(0,1000);
  if(!protocolRef||!subject) throw new HttpsError('invalid-argument','Protocollo e oggetto obbligatori.');
  const ref=regularityAppeals(year).doc(); await ref.set({protocolRef,subject,status:'OPEN',filedAt:admin.firestore.FieldValue.serverTimestamp(),createdBy:actor.uid});
  await regularityStateRef(year).set({legalHold:true,appealWindowClosed:false,updatedAt:admin.firestore.FieldValue.serverTimestamp()},{merge:true});
  await auditAdmin(actor,'ELECTORAL_APPEAL_FILED',{appealId:ref.id,protocolRef}); return{ok:true,id:ref.id};
});

exports.resolveElectoralAppeal = onCall({region:REGION}, async request => {
  const actor=requireAuth(request,['COMMISSIONE']),year=request.data?.annoScolastico,id=String(request.data?.id||''),decisionRef=String(request.data?.decisionRef||'').trim().slice(0,200);
  if(!id||!decisionRef) throw new HttpsError('invalid-argument','Ricorso e decisione obbligatori.');
  const ref=regularityAppeals(year).doc(id),snap=await ref.get(); if(!snap.exists) throw new HttpsError('not-found','Ricorso non trovato.');
  await ref.update({status:'RESOLVED',decisionRef,decidedAt:admin.firestore.FieldValue.serverTimestamp(),decidedBy:actor.uid});
  await auditAdmin(actor,'ELECTORAL_APPEAL_RESOLVED',{appealId:id,decisionRef}); return{ok:true};
});

exports.recordElectoralIncident = onCall({region:REGION}, async request => {
  const actor=requireAuth(request,['COMMISSIONE']),year=request.data?.annoScolastico;
  const protocolRef=String(request.data?.protocolRef||'').trim().slice(0,160),title=String(request.data?.title||'').trim().slice(0,200),details=String(request.data?.details||'').trim().slice(0,2000),suspend=request.data?.suspend===true;
  if(!title||!details) throw new HttpsError('invalid-argument','Titolo e descrizione obbligatori.');
  await regularityEvents(year).add({type:'INCIDENT',protocolRef,title,details,suspend,actorUid:actor.uid,at:admin.firestore.FieldValue.serverTimestamp()});
  await regularityStateRef(year).set({emergencySuspended:suspend,lastIncidentAt:admin.firestore.FieldValue.serverTimestamp(),updatedAt:admin.firestore.FieldValue.serverTimestamp(),updatedBy:actor.uid},{merge:true});
  await auditAdmin(actor,'ELECTORAL_INCIDENT_RECORDED',{protocolRef,title,suspend}); return{ok:true};
});

exports.setEmergencySuspension = onCall({region:REGION}, async request => {
  const actor=requireAuth(request,['COMMISSIONE']),year=request.data?.annoScolastico,suspended=request.data?.suspended===true,reason=String(request.data?.reason||'').trim().slice(0,1000);
  if(!reason) throw new HttpsError('invalid-argument','Motivazione obbligatoria.');
  await regularityStateRef(year).set({emergencySuspended:suspended,suspensionReason:reason,updatedAt:admin.firestore.FieldValue.serverTimestamp(),updatedBy:actor.uid},{merge:true});
  await regularityEvents(year).add({type:suspended?'SUSPENSION':'RESUMPTION',reason,actorUid:actor.uid,at:admin.firestore.FieldValue.serverTimestamp()});
  await auditAdmin(actor,suspended?'ELECTION_SUSPENDED':'ELECTION_RESUMED',{}); return{ok:true};
});

exports.closeElectoralProcedure = onCall({region:REGION}, async request => {
  const actor=requireAuth(request,['COMMISSIONE']),year=request.data?.annoScolastico,closureRef=String(request.data?.closureRef||'').trim().slice(0,200);
  if(!closureRef) throw new HttpsError('invalid-argument','Estremi verbale di chiusura obbligatori.');
  if(electionPhase(await loadElectionConfig(year))==='OPEN') throw new HttpsError('failed-precondition','Le urne sono ancora aperte.');
  const state=await loadRegularityState(year); if(!state.resultsPublished||!state.appealWindowClosed||!state.finalArchiveSealed) throw new HttpsError('failed-precondition','Completare pubblicazione, ricorsi e sigillo fascicolo.');
  const open=await regularityAppeals(year).where('status','==','OPEN').limit(1).get(); if(!open.empty) throw new HttpsError('failed-precondition','Esistono ricorsi ancora aperti.');
  const accounts=await yearlyCollection('gestione_accessi',year).get(); let count=0,batch=db.batch();
  for(const d of accounts.docs){if(MANAGEMENT_ROLES.has(normalize(d.data()?.role))){batch.update(d.ref,{active:false,closedProcedureRevocationAt:admin.firestore.FieldValue.serverTimestamp(),closedProcedureRevocationRef:closureRef});count++;if(count%400===0){await batch.commit();batch=db.batch();}}}
  if(count%400!==0) await batch.commit();
  await regularityStateRef(year).set({procedureClosed:true,procedureClosedAt:admin.firestore.FieldValue.serverTimestamp(),closureRef,legalHold:false,emergencySuspended:false,updatedAt:admin.firestore.FieldValue.serverTimestamp(),updatedBy:actor.uid},{merge:true});
  await regularityEvents(year).add({type:'PROCEDURE_CLOSED',closureRef,revokedManagementAccounts:count,actorUid:actor.uid,at:admin.firestore.FieldValue.serverTimestamp()});
  await auditAdmin(actor,'ELECTORAL_PROCEDURE_CLOSED',{closureRef,revokedManagementAccounts:count}); return{ok:true,revokedManagementAccounts:count};
});''')

p.write_text(t,encoding='utf-8')

# ================= FRONTEND =================
p=Path('index.html'); h=p.read_text(encoding='utf-8')
if 'getRegularityState: httpsCallable' not in h:
    m="getSecurityStatus: httpsCallable(functions, 'getSecurityStatus'),"
    a="""            getRegularityState: httpsCallable(functions, 'getRegularityState'),\n            setRegularityControl: httpsCallable(functions, 'setRegularityControl'),\n            recordResultsPublication: httpsCallable(functions, 'recordResultsPublication'),\n            fileElectoralAppeal: httpsCallable(functions, 'fileElectoralAppeal'),\n            resolveElectoralAppeal: httpsCallable(functions, 'resolveElectoralAppeal'),\n            recordElectoralIncident: httpsCallable(functions, 'recordElectoralIncident'),\n            setEmergencySuspension: httpsCallable(functions, 'setEmergencySuspension'),\n            closeElectoralProcedure: httpsCallable(functions, 'closeElectoralProcedure'),"""
    if m not in h: raise SystemExit('SECURE_API marker mancante')
    h=h.replace(m,m+'\n'+a,1)
if "id: 'regolarita'" not in h:
    h=h.replace("{ id: 'workflow_digitale', label: '11. Workflow Digitale & Verbali' }","{ id: 'workflow_digitale', label: '11. Workflow Digitale & Verbali' },\n                { id: 'regolarita', label: '12. Regolarità Elettorale' }",1)
    h=h.replace("else if(activeAdminTab === 'workflow_digitale') renderDigitalWorkflowTab(content);","else if(activeAdminTab === 'workflow_digitale') renderDigitalWorkflowTab(content);\n            else if(activeAdminTab === 'regolarita') renderRegularityTab(content);",1)

if 'async function renderRegularityTab' not in h:
    marker='        async function renderDigitalWorkflowTab(container) {'
    renderer=r'''        const REGULARITY_LABELS=Object.freeze({annualCircularRecorded:'Circolare MIM/USR annuale acquisita e protocollata',commissionAppointed:'Commissione elettorale formalmente nominata',voterRollFinal:'Elenchi elettorali definitivi e reclami sugli elenchi conclusi',candidateListsValidated:'Liste e candidature convalidate',ballotApproved:'Scheda elettorale approvata e congelata',privacyChecked:'Privacy/GDPR e minimizzazione verificati',technicalTestPassed:'Collaudo tecnico verbalizzato e superato',softwareFrozen:'Versione software/commit congelata',backupPlanReady:'Backup e ripristino verificati',incidentPlanReady:'Piano incidenti/sospensione/ripresa approvato',communicationPublished:'Comunicazioni agli elettori pubblicate',finalArchiveSealed:'Fascicolo finale sigillato con verbali/hash/evidenze',appealWindowClosed:'Termine reclami/ricorsi concluso e verificato'});
        async function renderRegularityTab(container){
          container.innerHTML='<div class="bg-white rounded-3xl border p-6 font-bold">Verifica regolarità...</div>';
          try{const r=await SECURE_API.getRegularityState({annoScolastico:configElezioni.annoScolastico}),s=r.data?.state||{},appeals=r.data?.appeals||[],missing=r.data?.missing||[],ready=r.data?.readyForVoting===true;
          const pre=Object.keys(REGULARITY_LABELS).filter(k=>!['finalArchiveSealed','appealWindowClosed'].includes(k));
          const card=k=>`<div class="p-3 rounded-2xl border ${s[k]?'bg-emerald-50 border-emerald-200':'bg-red-50 border-red-200'}"><div class="flex justify-between gap-2"><div><b class="text-[11px]">${s[k]?'✓':'✕'} ${REGULARITY_LABELS[k]}</b><div class="text-[9px] text-slate-500">${s.notes?.[k]||'Nessuna annotazione.'}</div></div><button onclick="window.toggleRegularityControl('${k}',${!s[k]})" class="px-2 py-1 rounded-lg text-[9px] font-black ${s[k]?'bg-slate-200':'bg-emerald-700 text-white'}">${s[k]?'Revoca':'Conferma'}</button></div></div>`;
          const rows=appeals.map(a=>`<tr class="border-t"><td class="p-2">${a.protocolRef||'—'}</td><td class="p-2">${a.subject||'—'}</td><td class="p-2 font-black">${a.status}</td><td class="p-2">${a.decisionRef||'—'}</td><td class="p-2">${a.status==='OPEN'?`<button onclick="window.resolveRegularityAppeal('${a.id}')" class="px-2 py-1 bg-emerald-700 text-white rounded-lg">Decisione</button>`:'Definito'}</td></tr>`).join('');
          container.innerHTML=`<div class="w-full space-y-5 font-semibold"><div class="bg-white rounded-3xl shadow border p-6"><div class="flex justify-between gap-4"><div><span class="text-[9px] bg-blue-900 text-white px-2 py-1 rounded font-black">REGOLARITÀ PROCEDIMENTO</span><h3 class="text-xl font-black mt-2">A.S. ${configElezioni.annoScolastico}</h3><p class="text-[10px] text-slate-500">O.M. 215/1991 e s.m.i. · circolare annuale MIM/USR · Nota MIM 3803/2026 · GDPR/CAD/AgID. I controlli tecnici non sostituiscono gli atti formali.</p></div><div class="p-3 rounded-2xl ${ready?'bg-emerald-100 text-emerald-900':'bg-red-100 text-red-900'}"><b>${ready?'APERTURA ABILITATA':'APERTURA BLOCCATA'}</b></div></div>${missing.length?`<div class="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-[10px]"><b>Mancano:</b> ${missing.map(k=>REGULARITY_LABELS[k]||k).join(' · ')}</div>`:''}<div class="mt-4 grid md:grid-cols-2 gap-3">${pre.map(card).join('')}</div><input id="regularityNote" placeholder="Annotazione, protocollo, verbale o delibera" class="mt-4 w-full p-2.5 border rounded-xl text-xs"></div>
          <div class="grid lg:grid-cols-2 gap-5"><div class="bg-white rounded-3xl shadow border p-5 space-y-2"><b>Pubblicazione risultati / termini ricorsi</b><input id="regPubProtocol" placeholder="Protocollo/estremi pubblicazione" class="w-full p-2 border rounded-xl text-xs"><input id="regAppealDeadline" type="date" class="w-full p-2 border rounded-xl text-xs"><button onclick="window.recordRegularityPublication()" class="w-full p-2 bg-blue-900 text-white rounded-xl text-xs font-black">Registra pubblicazione</button><div class="text-[10px]">${s.resultsPublished?'Registrata: '+(s.resultsPublicationProtocol||''):'Non registrata'}</div></div><div class="bg-white rounded-3xl shadow border p-5 space-y-2"><b>Incidente / sospensione</b><input id="regIncidentTitle" placeholder="Titolo" class="w-full p-2 border rounded-xl text-xs"><input id="regIncidentProtocol" placeholder="Protocollo/verbale" class="w-full p-2 border rounded-xl text-xs"><textarea id="regIncidentDetails" placeholder="Descrizione, impatto, decisione" class="w-full p-2 border rounded-xl text-xs"></textarea><label class="text-[10px]"><input id="regIncidentSuspend" type="checkbox"> sospendi nuovi accessi al voto</label><button onclick="window.recordRegularityIncident()" class="w-full p-2 bg-amber-600 text-white rounded-xl text-xs font-black">Registra incidente</button><button onclick="window.resumeRegularityElection()" class="w-full p-2 bg-slate-100 rounded-xl text-xs font-black">Registra ripresa</button><div class="text-[10px] font-black">${s.emergencySuspended?'VOTAZIONE SOSPESA':'Nessuna sospensione attiva'}</div></div></div>
          <div class="bg-white rounded-3xl shadow border p-5"><b>Registro reclami / ricorsi</b><div class="grid md:grid-cols-[1fr_2fr_auto] gap-2 mt-2"><input id="regAppealProtocol" placeholder="Protocollo" class="p-2 border rounded-xl text-xs"><input id="regAppealSubject" placeholder="Oggetto sintetico (senza dati eccedenti)" class="p-2 border rounded-xl text-xs"><button onclick="window.fileRegularityAppeal()" class="px-4 bg-red-700 text-white rounded-xl text-xs font-black">Registra</button></div><div class="overflow-auto mt-3 border rounded-xl"><table class="w-full text-[10px]"><tbody>${rows||'<tr><td class="p-5 text-center">Nessun ricorso registrato.</td></tr>'}</tbody></table></div><div class="mt-2 text-[10px]"><b>Legal hold:</b> ${s.legalHold?'ATTIVO':'non attivo'}</div></div>
          <div class="bg-white rounded-3xl shadow border p-5"><b>Chiusura definitiva e conservazione</b><p class="text-[10px] text-slate-500">Richiede pubblicazione, termine ricorsi chiuso, nessun ricorso aperto e fascicolo sigillato. Revoca automaticamente Dirigente, Vicepreside, DSGA e Segreteria.</p><div class="grid md:grid-cols-2 gap-3 mt-3">${card('appealWindowClosed')}${card('finalArchiveSealed')}</div><div class="flex gap-2 mt-3"><input id="regClosureRef" placeholder="Estremi verbale/provvedimento di chiusura" class="flex-1 p-2 border rounded-xl text-xs"><button onclick="window.closeRegularityProcedure()" class="px-4 bg-slate-900 text-white rounded-xl text-xs font-black" ${s.procedureClosed?'disabled':''}>${s.procedureClosed?'CHIUSO':'Chiudi definitivamente'}</button></div></div></div>`;lucide.createIcons();}catch(e){container.innerHTML=`<div class="bg-white rounded-3xl border p-8 text-red-700 font-bold">Impossibile caricare la regolarità: ${e.message||'errore'}</div>`;}}
        window.toggleRegularityControl=async(control,value)=>{const note=document.getElementById('regularityNote')?.value?.trim()||'';try{await SECURE_API.setRegularityControl({annoScolastico:configElezioni.annoScolastico,control,value,note});renderActiveAdminTab();}catch(e){showNotification('Controllo non aggiornato',e.message||'Errore','error');}};
        window.recordRegularityPublication=async()=>{try{await SECURE_API.recordResultsPublication({annoScolastico:configElezioni.annoScolastico,protocolRef:document.getElementById('regPubProtocol').value.trim(),appealDeadline:document.getElementById('regAppealDeadline').value});renderActiveAdminTab();}catch(e){showNotification('Pubblicazione non registrata',e.message||'Errore','error');}};
        window.fileRegularityAppeal=async()=>{try{await SECURE_API.fileElectoralAppeal({annoScolastico:configElezioni.annoScolastico,protocolRef:document.getElementById('regAppealProtocol').value.trim(),subject:document.getElementById('regAppealSubject').value.trim()});renderActiveAdminTab();}catch(e){showNotification('Ricorso non registrato',e.message||'Errore','error');}};
        window.resolveRegularityAppeal=async id=>{const decisionRef=prompt('Protocollo/estremi della decisione:');if(!decisionRef)return;try{await SECURE_API.resolveElectoralAppeal({annoScolastico:configElezioni.annoScolastico,id,decisionRef});renderActiveAdminTab();}catch(e){showNotification('Decisione non registrata',e.message||'Errore','error');}};
        window.recordRegularityIncident=async()=>{try{await SECURE_API.recordElectoralIncident({annoScolastico:configElezioni.annoScolastico,title:document.getElementById('regIncidentTitle').value.trim(),protocolRef:document.getElementById('regIncidentProtocol').value.trim(),details:document.getElementById('regIncidentDetails').value.trim(),suspend:document.getElementById('regIncidentSuspend').checked});renderActiveAdminTab();}catch(e){showNotification('Incidente non registrato',e.message||'Errore','error');}};
        window.resumeRegularityElection=async()=>{const reason=prompt('Motivazione e verbale di ripresa:');if(!reason)return;try{await SECURE_API.setEmergencySuspension({annoScolastico:configElezioni.annoScolastico,suspended:false,reason});renderActiveAdminTab();}catch(e){showNotification('Ripresa non registrata',e.message||'Errore','error');}};
        window.closeRegularityProcedure=async()=>{const closureRef=document.getElementById('regClosureRef').value.trim();if(!closureRef)return showNotification('Dato mancante','Inserire gli estremi della chiusura.','error');if(!confirm('Confermare la chiusura definitiva e la revoca degli accessi gestionali?'))return;try{const r=await SECURE_API.closeElectoralProcedure({annoScolastico:configElezioni.annoScolastico,closureRef});showNotification('Procedimento chiuso',`Accessi revocati: ${r.data?.revokedManagementAccounts||0}`,'success');renderActiveAdminTab();}catch(e){showNotification('Chiusura non consentita',e.message||'Errore','error');}};'''
    if marker not in h: raise SystemExit('Renderer marker mancante')
    h=h.replace(marker,renderer+'\n'+marker,1)

p.write_text(h,encoding='utf-8'); Path('404.html').write_text(h,encoding='utf-8')
Path('docs/14_REGOLARITA_PROCEDIMENTO_ELETTORALE.md').write_text("""# 14 — Regolarità del procedimento elettorale\n\nLa piattaforma usa controlli bloccanti prima del voto, audit server-side, registro incidenti, pubblicazione risultati, registro reclami/ricorsi, legal hold, sigillo del fascicolo e chiusura definitiva con revoca degli accessi gestionali. Tali controlli non sostituiscono O.M. 215/1991 e s.m.i., circolare MIM/USR annuale, atti della Commissione, GDPR/CAD/AgID e conservazione documentale dell'Istituto.\n\nLa cessazione degli accessi operativi non equivale alla cancellazione degli atti soggetti a conservazione.\n""",encoding='utf-8')
