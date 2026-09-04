from pathlib import Path

for fn in ('index.html','404.html'):
    p=Path(fn)
    if not p.exists(): continue
    s=p.read_text(encoding='utf-8')
    a=s.find('        function generateRandomSuffix(')
    b=s.find('\n\n        async function ensureReferentiKeysForClasses',a)
    if a<0 or b<0: raise SystemExit('helper token non trovato '+fn)
    block='''        function randomThreeDigits() {
            const bytes = new Uint16Array(1);
            crypto.getRandomValues(bytes);
            return String(bytes[0] % 1000).padStart(3, '0');
        }

        function voterTokenPrefix(componentType) {
            const t = String(componentType || '').toUpperCase();
            if (t === 'STUDENTE') return 'STU';
            if (t === 'GENITORE') return 'GEN';
            return t.slice(0,3) || 'TOK';
        }

        async function buildUsedTokenSet() {
            const used = new Set((activeTokensList || []).map(t => String(t.id || '').toUpperCase()));
            try {
                const snap = await getDocs(getCollectionRef('tokens'));
                snap.forEach(d => used.add(String(d.id || '').toUpperCase()));
            } catch(e) {}
            return used;
        }

        function nextUniqueThreeDigitToken(prefix, used) {
            for (let attempt = 0; attempt < 2500; attempt++) {
                const code = prefix + randomThreeDigits();
                if (!used.has(code)) { used.add(code); return code; }
            }
            for (let i=0;i<1000;i++) {
                const code = prefix + String(i).padStart(3,'0');
                if (!used.has(code)) { used.add(code); return code; }
            }
            throw new Error('Esauriti i 1000 codici disponibili per il prefisso ' + prefix + '.');
        }'''
    s=s[:a]+block+s[b:]
    s=s.replace("const prefix = componentType.substring(0, 3);\n                const generatedClasses = new Set();", "const prefix = voterTokenPrefix(componentType);\n                const generatedClasses = new Set();\n                const usedTokens = await buildUsedTokenSet();", 1)
    s=s.replace("""                    let uniqueToken = \"\";
                    if (componentType === 'STUDENTE' || componentType === 'GENITORE') {
                        uniqueToken = generateShortVoterToken(prefix, classe, true);
                        generatedClasses.add(classe);
                    } else {
                        uniqueToken = generateShortVoterToken(prefix, '', false);
                    }""", """                    const uniqueToken = nextUniqueThreeDigitToken(prefix, usedTokens);
                    if (componentType === 'STUDENTE' || componentType === 'GENITORE') generatedClasses.add(classe);""", 1)
    s=s.replace("const prefix = componentType.substring(0, 3);\n            const generatedClasses = new Set();", "const prefix = voterTokenPrefix(componentType);\n            const generatedClasses = new Set();\n            const usedTokens = await buildUsedTokenSet();", 1)
    s=s.replace("""                let uniqueToken = '';
                if (isClassBased) {
                    uniqueToken = generateShortVoterToken(prefix, classe, true);
                    generatedClasses.add(classe);
                } else {
                    uniqueToken = generateShortVoterToken(prefix, '', false);
                }""", """                const uniqueToken = nextUniqueThreeDigitToken(prefix, usedTokens);
                if (isClassBased) generatedClasses.add(classe);""", 1)
    s=s.replace('placeholder=\"ES: S-4A-K7M4Q-X9Z2R\"','placeholder=\"ES: STU123\"',1)
    p.write_text(s,encoding='utf-8')