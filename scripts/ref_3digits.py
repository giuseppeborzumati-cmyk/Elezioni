from pathlib import Path
p=Path('functions/index.js')
s=p.read_text(encoding='utf-8')
old="""        let key;
        do {
          key = `REF-${type === 'STUDENTE' ? 'STU' : 'GEN'}-${crypto.randomBytes(10).toString('base64url').replace(/[^A-Z0-9]/gi, '').toUpperCase().slice(0, 12)}`;
        } while (current[key]);
        current[key] = { classe: cls, tipo: type };"""
new="""        let key = null;
        const prefix = type === 'STUDENTE' ? 'REF-STU' : 'REF-REF';
        for (let attempt = 0; attempt < 2500 && !key; attempt++) {
          const n = crypto.randomInt(0, 1000).toString().padStart(3, '0');
          const candidate = prefix + n;
          if (!current[candidate]) key = candidate;
        }
        if (!key) {
          for (let i = 0; i < 1000 && !key; i++) {
            const candidate = prefix + String(i).padStart(3, '0');
            if (!current[candidate]) key = candidate;
          }
        }
        if (!key) throw new HttpsError('resource-exhausted', 'Esauriti i codici referente disponibili per ' + prefix + '.');
        current[key] = { classe: cls, tipo: type };"""
if old not in s: raise SystemExit('generatore referenti non trovato')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')