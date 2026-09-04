from pathlib import Path

for fn in ('index.html','404.html'):
    p=Path(fn)
    if not p.exists(): continue
    s=p.read_text(encoding='utf-8')
    s=s.replace("            const tabs = [\n                { id: 'config', label: '1. Configurazione & Regole' },", "            const tabs = [\n                { id: 'apertura', label: 'APERTURA VOTAZIONI' },\n                { id: 'config', label: '1. Configurazione & Regole' },", 1)
    s=s.replace("let activeAdminTab = 'config';", "let activeAdminTab = 'apertura';", 1)
    s=s.replace("            if(activeAdminTab === 'config') renderConfigTab(content);", "            if(activeAdminTab === 'apertura') renderOpeningTab(content);\n            else if(activeAdminTab === 'config') renderConfigTab(content);", 1)
    anchor='        function renderActiveAdminTab() {'
    if anchor not in s: raise SystemExit('router apertura non trovato '+fn)
    block=r'''
        function romeParts(date = new Date()) {
            const parts = Object.fromEntries(new Intl.DateTimeFormat('it-IT',{
                timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit',
                hour:'2-digit',minute:'2-digit',hourCycle:'h23'
            }).formatToParts(date).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
            return { date: parts.day+'/'+parts.month+'/'+parts.year, time: parts.hour+':'+parts.minute };
        }

        async function refreshOpeningStatus() {
            const box=document.getElementById('opening-status-box');
            if(!box) return;
            box.innerHTML='<div class="p-4 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 font-bold">Verifica in corso...</div>';
            const r=await verifyProductionReadiness();
            if(r.ok) {
                box.innerHTML='<div class="p-4 rounded-xl bg-emerald-50 border-2 border-emerald-300 text-emerald-900"><div class="font-black text-lg">✓ SISTEMA PRONTO</div><div class="text-xs mt-1">Puoi aprire le votazioni con un solo pulsante.</div></div>';
            } else {
                box.innerHTML='<div class="p-4 rounded-xl bg-amber-50 border-2 border-amber-300 text-amber-950"><div class="font-black">PRIMA DI APRIRE MANCA:</div><div class="text-xs mt-2 space-y-1">'+r.errors.map(e=>'<div>• '+e+'</div>').join('')+'</div></div>';
            }
        }

        function renderOpeningTab(container) {
            const w=votingWindowStatus();
            container.innerHTML=`
                <div class="max-w-4xl mx-auto space-y-5">
                    <div class="bg-gradient-to-br from-blue-950 to-slate-900 text-white rounded-3xl p-6 shadow-xl">
                        <div class="text-[10px] uppercase tracking-[.2em] text-blue-200 font-black">Gestione semplificata</div>
                        <h3 class="text-2xl font-black mt-1">Apertura votazioni</h3>
                        <p class="text-sm text-slate-300 mt-2">I controlli obbligatori restano attivi, ma l'apertura si gestisce da questa sola schermata.</p>
                        <div class="mt-4 bg-white/10 rounded-2xl p-4 text-sm"><b>Stato:</b> ${w.open?'APERTE':(w.reason==='before'?'NON ANCORA APERTE':'CHIUSE')}<br><span class="text-xs text-slate-300">${configElezioni.calendario?.votingStartDate||'—'} ${configElezioni.calendario?.votingStartTime||''} → ${configElezioni.calendario?.votingEndDate||'—'} ${configElezioni.calendario?.votingEndTime||''}</span></div>
                    </div>
                    <div id="opening-status-box"></div>
                    <div class="grid md:grid-cols-3 gap-4">
                        <button onclick="refreshOpeningStatus()" class="p-5 rounded-2xl bg-blue-50 border-2 border-blue-200 hover:bg-blue-100 text-blue-950 text-left"><div class="text-2xl mb-2">①</div><div class="font-black">VERIFICA</div><div class="text-[10px] mt-1">Ti dice solo cosa manca.</div></button>
                        <button onclick="openElectionNow()" class="p-5 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white text-left shadow-lg"><div class="text-2xl mb-2">②</div><div class="font-black">APRI ORA</div><div class="text-[10px] mt-1">Disattiva la prova e apre subito.</div></button>
                        <button onclick="closeElectionNow()" class="p-5 rounded-2xl bg-red-600 hover:bg-red-700 text-white text-left shadow-lg"><div class="text-2xl mb-2">③</div><div class="font-black">CHIUDI ORA</div><div class="text-[10px] mt-1">Blocca immediatamente nuovi voti.</div></button>
                    </div>
                    <div class="bg-white border rounded-2xl p-5"><label class="text-xs font-black">Durata automatica dopo “APRI ORA”</label><select id="quickOpeningHours" class="mt-2 w-full md:w-52 p-3 border rounded-xl font-bold"><option value="1">1 ora</option><option value="2">2 ore</option><option value="4" selected>4 ore</option><option value="6">6 ore</option><option value="8">8 ore</option></select><p class="text-[10px] text-slate-500 mt-2">Le date dettagliate restano modificabili nella Configurazione.</p></div>
                </div>`;
            refreshOpeningStatus();
        }

        window.openElectionNow = async function() {
            if(!auth.currentUser) return showNotification('Accesso richiesto','Accedere come Commissione.','error');
            const readiness=await verifyProductionReadiness();
            if(!readiness.ok){ await refreshOpeningStatus(); return showNotification('Apertura bloccata','Completa solo gli elementi indicati nel riquadro giallo.','error'); }
            if(!confirm('Confermi l’apertura immediata delle votazioni reali?')) return;
            const hours=Math.min(8,Math.max(1,parseInt(document.getElementById('quickOpeningHours')?.value||'4')));
            const now=new Date(), end=new Date(now.getTime()+hours*3600000);
            const a=romeParts(new Date(now.getTime()-60000)), b=romeParts(end);
            configElezioni.modalitaProva=false;
            configElezioni.calendario={...(configElezioni.calendario||{}),votingStartDate:a.date,votingStartTime:a.time,votingEndDate:b.date,votingEndTime:b.time};
            try {
                await SECURE_API.saveElectionConfig({config:configElezioni,annoScolastico:configElezioni.annoScolastico});
                window.configElezioni=configElezioni; updateTestModeBanner();
                showNotification('VOTAZIONI APERTE','Chiusura automatica prevista tra '+hours+' ore.','success');
                renderOpeningTab(document.getElementById('admin-tab-content'));
            } catch(e) { showNotification('Apertura non riuscita',e.message||'Errore','error'); }
        };

        window.closeElectionNow = async function() {
            if(!auth.currentUser) return showNotification('Accesso richiesto','Accedere come Commissione.','error');
            if(!confirm('Confermi la chiusura immediata delle votazioni?')) return;
            const t=romeParts(new Date(Date.now()-60000));
            configElezioni.calendario={...(configElezioni.calendario||{}),votingEndDate:t.date,votingEndTime:t.time};
            try {
                await SECURE_API.saveElectionConfig({config:configElezioni,annoScolastico:configElezioni.annoScolastico});
                window.configElezioni=configElezioni;
                showNotification('VOTAZIONI CHIUSE','Non vengono più accettati nuovi voti.','success');
                renderOpeningTab(document.getElementById('admin-tab-content'));
            } catch(e) { showNotification('Chiusura non riuscita',e.message||'Errore','error'); }
        };

'''
    s=s.replace(anchor,block+anchor,1)
    p.write_text(s,encoding='utf-8')