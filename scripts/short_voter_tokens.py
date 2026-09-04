from pathlib import Path

for name in ("index.html","404.html"):
    p=Path(name)
    if not p.exists(): continue
    s=p.read_text(encoding="utf-8")
    old="""        function generateRandomSuffix(length = 16) {
            const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
            const bytes = new Uint8Array(length);
            crypto.getRandomValues(bytes);
            let result = '';
            for (let i = 0; i < length; i++) result += chars[bytes[i] % chars.length];
            return result;
        }"""
    new="""        function generateRandomSuffix(length = 10) {
            // Alfabeto Crockford-like: esclusi 0/O e 1/I/L per ridurre gli errori di digitazione.
            const chars = '23456789ABCDEFGHJKMNPQRSTUVWXYZ';
            const bytes = new Uint8Array(length);
            crypto.getRandomValues(bytes);
            let result = '';
            for (let i = 0; i < length; i++) result += chars[bytes[i] % chars.length];
            return result;
        }

        function generateShortVoterToken(prefix, classe = '', classBased = false) {
            const raw = generateRandomSuffix(10);
            const grouped = raw.slice(0, 5) + '-' + raw.slice(5);
            const shortPrefix = prefix === 'STU' ? 'S' : (prefix === 'GEN' ? 'G' : prefix);
            return classBased && classe ? `${shortPrefix}-${classe}-${grouped}` : `${shortPrefix}-${grouped}`;
        }"""
    if old not in s:
        raise SystemExit(f"generatore non trovato in {name}")
    s=s.replace(old,new,1)
    s=s.replace("uniqueToken = `${prefix}-${classe}-${generateRandomSuffix(20)}`;",
                "uniqueToken = generateShortVoterToken(prefix, classe, true);")
    s=s.replace("uniqueToken = `${prefix}-${generateRandomSuffix(24)}`;",
                "uniqueToken = generateShortVoterToken(prefix, '', false);")
    s=s.replace('placeholder="ES: STU-4A-X2Y9"', 'placeholder="ES: S-4A-K7M4Q-X9Z2R"')
    p.write_text(s,encoding="utf-8")
