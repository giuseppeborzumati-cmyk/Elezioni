from pathlib import Path

for fn in ('index.html','404.html'):
    p=Path(fn)
    if not p.exists():
        continue
    s=p.read_text(encoding='utf-8')
    old="""        window.toggleRegularityControl=async(control,value)=>{const note=document.getElementById('regularityNote')?.value?.trim()||'';try{await SECURE_API.setRegularityControl({annoScolastico:configElezioni.annoScolastico,control,value,note});renderActiveAdminTab();}catch(e){showNotification('Controllo non aggiornato',e.message||'Errore','error');}};"""
    new="""        window.toggleRegularityControl=async(control,value)=>{
            const typed=document.getElementById('regularityNote')?.value?.trim()||'';
            const label=(typeof REGULARITY_LABELS!=='undefined' && REGULARITY_LABELS[control]) ? REGULARITY_LABELS[control] : control;
            const autoNote=value
                ? `Confermato dalla Commissione Elettorale tramite pannello digitale: ${label}. Data/ora registrata automaticamente dal sistema.`
                : `Revocata dalla Commissione Elettorale tramite pannello digitale la precedente conferma: ${label}. Data/ora registrata automaticamente dal sistema.`;
            const note=typed || autoNote;
            try{
                await SECURE_API.setRegularityControl({annoScolastico:configElezioni.annoScolastico,control,value,note});
                const input=document.getElementById('regularityNote'); if(input) input.value='';
                renderActiveAdminTab();
            }catch(e){showNotification('Controllo non aggiornato',e.message||'Errore','error');}
        };"""
    if old not in s:
        raise SystemExit(f'anchor toggleRegularityControl non trovato in {fn}')
    s=s.replace(old,new,1)
    p.write_text(s,encoding='utf-8')
