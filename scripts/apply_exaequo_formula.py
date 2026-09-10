from pathlib import Path
import re

HELPERS = r'''
        // === EX AEQUO: sorteggio deterministico senza criterio alfabetico ===
        const EX_AEQUO_CP = 2147483647; // numero primo fisso (2^31 - 1)

        function exAequoAscii(value) {
            return String(value ?? '')
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '')
                .replace(/[^\x20-\x7E]/g, '?')
                .toUpperCase();
        }

        function exAequoHash32(value, salt = '') {
            const s = exAequoAscii(salt + '|' + value);
            let h = 2166136261 >>> 0;
            for (let i = 0; i < s.length; i++) {
                h ^= s.charCodeAt(i);
                h = Math.imul(h, 16777619) >>> 0;
            }
            return h >>> 0;
        }

        function exAequoLabel(item) {
            return String(item?.display ?? item?.name ?? item?.listName ?? item?.id ?? '');
        }

        function exAequoCanonical(items) {
            return [...items].sort((a, b) => {
                const la = exAequoLabel(a), lb = exAequoLabel(b);
                const a1 = exAequoHash32(la, 'A'), b1 = exAequoHash32(lb, 'A');
                if (a1 !== b1) return a1 - b1;
                const a2 = exAequoHash32(la, 'B'), b2 = exAequoHash32(lb, 'B');
                if (a2 !== b2) return a2 - b2;
                return 0; // nessun fallback alfabetico
            });
        }

        function exAequoSeed(items, context = '') {
            const canonical = exAequoCanonical(items);
            const source = exAequoAscii(context + '|' + canonical.map(exAequoLabel).join('|'));
            let sum = 0;
            for (let i = 0; i < source.length; i++) {
                sum = (sum + source.charCodeAt(i)) % EX_AEQUO_CP;
            }
            return { seed: sum || 1, cp: EX_AEQUO_CP, source, canonical };
        }

        function exAequoPrng(seed) {
            let x = (seed >>> 0) || 1;
            return function() {
                x ^= (x << 13); x >>>= 0;
                x ^= (x >>> 17); x >>>= 0;
                x ^= (x << 5); x >>>= 0;
                return (x >>> 0) / 4294967296;
            };
        }

        function drawExAequo(items, context = '') {
            const meta = exAequoSeed(items, context);
            const ordered = [...meta.canonical];
            const rnd = exAequoPrng(meta.seed);
            for (let i = ordered.length - 1; i > 0; i--) {
                const j = Math.floor(rnd() * (i + 1));
                [ordered[i], ordered[j]] = [ordered[j], ordered[i]];
            }
            const audit = {
                context,
                formula: 'S_seed = (SUM ASCII(Carattere_i)) mod C_p',
                cp: meta.cp,
                seed: meta.seed,
                partecipanti: meta.canonical.map(exAequoLabel),
                ordineSorteggiato: ordered.map(exAequoLabel)
            };
            window.__EX_AEQUO_AUDIT__ = window.__EX_AEQUO_AUDIT__ || [];
            const key = JSON.stringify(audit);
            if (!window.__EX_AEQUO_AUDIT__.some(x => JSON.stringify(x) === key)) window.__EX_AEQUO_AUDIT__.push(audit);
            return { ordered, seed: meta.seed, cp: meta.cp, audit };
        }

        function sortCandidatesByVotesWithExAequo(items, context = 'SCRUTINIO') {
            const groups = new Map();
            for (const item of items) {
                const count = Number(item?.count || 0);
                if (!groups.has(count)) groups.set(count, []);
                groups.get(count).push(item);
            }
            const counts = [...groups.keys()].sort((a, b) => b - a);
            const out = [];
            for (const count of counts) {
                const group = groups.get(count);
                if (group.length > 1) out.push(...drawExAequo(group, context + '|VOTI=' + count).ordered);
                else out.push(...group);
            }
            return out;
        }

        function sortQuotientsWithExAequo(items, context = 'ATTRIBUZIONE_SEGGI') {
            const base = [...items].sort((a, b) => {
                if (Math.abs(Number(a.quotient) - Number(b.quotient)) >= 0.0001) return Number(b.quotient) - Number(a.quotient);
                if (Number(a.votes) !== Number(b.votes)) return Number(b.votes) - Number(a.votes);
                return 0;
            });
            const out = [];
            let i = 0;
            while (i < base.length) {
                const group = [base[i]];
                let j = i + 1;
                while (j < base.length && Math.abs(Number(base[j].quotient) - Number(base[i].quotient)) < 0.0001 && Number(base[j].votes) === Number(base[i].votes)) {
                    group.push(base[j]); j++;
                }
                if (group.length > 1) out.push(...drawExAequo(group, context + '|Q=' + Number(base[i].quotient).toFixed(8) + '|V=' + Number(base[i].votes)).ordered);
                else out.push(...group);
                i = j;
            }
            return out;
        }
'''

candidate_sort_re = re.compile(r"Object\.values\(([^\n\)]+(?:\[[^\]]+\])?)\)\s*\.sort\(\(a,\s*b\)\s*=>\s*\{\s*if\s*\(b\.count\s*===\s*a\.count\)\s*return\s+a\.display\.localeCompare\(b\.display\);\s*return\s+b\.count\s*-\s*a\.count;\s*\}\)", re.M)

explicit_old = "let sortedWinner = tieCandidates.sort((a,b) => a.display.localeCompare(b.display))[0];"
explicit_old2 = "let sortedWinner = tieCandidates.sort((a,b) => a.display.localeCompare(b.display))[0]; "

for filename in ('index.html', '404.html'):
    p = Path(filename)
    s = p.read_text(encoding='utf-8')

    if 'const EX_AEQUO_CP = 2147483647' not in s:
        anchor = '        async function renderScrutinioTab(container) {'
        if anchor not in s:
            raise SystemExit(f'Anchor scrutinio non trovato in {filename}')
        s = s.replace(anchor, HELPERS + '\n' + anchor, 1)

    # Sostituisce tutti gli ordinamenti elettorali dei candidati che usavano l'alfabeto in caso di parità.
    s, n_cand = candidate_sort_re.subn(lambda m: "sortCandidatesByVotesWithExAequo(Object.values(" + m.group(1) + "), 'SCRUTINIO')", s)

    # Spareggio esplicito per il secondo rappresentante.
    if explicit_old in s or explicit_old2 in s:
        s = s.replace(explicit_old2, "const exAequoDrawResult = drawExAequo(tieCandidates, 'SECONDO_RAPPRESENTANTE|' + String(configElezioni.annoScolastico || ''));\n                    let sortedWinner = exAequoDrawResult.ordered[0];")
        s = s.replace(explicit_old, "const exAequoDrawResult = drawExAequo(tieCandidates, 'SECONDO_RAPPRESENTANTE|' + String(configElezioni.annoScolastico || ''));\n                    let sortedWinner = exAequoDrawResult.ordered[0];")

    old_phrase = "<p>I candidati ${tieCandidates.map(c => `<strong>${c.display}</strong> (${c.count} voti)`).join(', ')} hanno ottenuto pari voti. Criterio alfabetico applicato per la proclamazione: <strong>${sortedWinner.display}</strong>.</p>"
    new_phrase = "<p>I candidati ${tieCandidates.map(c => `<strong>${c.display}</strong> (${c.count} voti)`).join(', ')} hanno ottenuto pari voti. È stato applicato esclusivamente il sorteggio matematico deterministico previsto: <code>S_seed = (Σ ASCII(Carattere_i)) mod C_p</code>, con <strong>C_p = ${exAequoDrawResult.cp}</strong> e <strong>S_seed = ${exAequoDrawResult.seed}</strong>. Nessun criterio alfabetico è utilizzato. Esito del sorteggio: <strong>${sortedWinner.display}</strong>.</p>"
    s = s.replace(old_phrase, new_phrase)

    # D'Hondt / attribuzione seggi: a parità perfetta di quoziente e voti niente alfabeto.
    q_re = re.compile(r"quotients\.sort\(\(a,\s*b\)\s*=>\s*\{\s*if\s*\(Math\.abs\(a\.quotient\s*-\s*b\.quotient\)\s*<\s*0\.0001\)\s*\{\s*if\s*\(a\.votes\s*===\s*b\.votes\)\s*\{\s*return\s+a\.listName\.localeCompare\(b\.listName\);\s*\}\s*return\s+b\.votes\s*-\s*a\.votes;\s*\}\s*return\s+b\.quotient\s*-\s*a\.quotient;\s*\}\);", re.M)
    s, n_q = q_re.subn("quotients = sortQuotientsWithExAequo(quotients, 'ATTRIBUZIONE_SEGGI');", s)

    # Verifiche forti: nello scrutinio non deve più esistere l'alfabeto come tie-break.
    if "Criterio alfabetico applicato" in s:
        raise SystemExit(f'Rimane la vecchia frase alfabetica in {filename}')
    if re.search(r"if\s*\(b\.count\s*===\s*a\.count\)\s*return\s+a\.display\.localeCompare\(b\.display\)", s):
        raise SystemExit(f'Rimane tie-break alfabetico candidati in {filename}')
    if "return a.listName.localeCompare(b.listName)" in s:
        raise SystemExit(f'Rimane tie-break alfabetico liste in {filename}')
    if 'S_seed = (Σ ASCII(Carattere_i)) mod C_p' not in s:
        raise SystemExit(f'Formula ex aequo non presente in {filename}')

    p.write_text(s, encoding='utf-8')
    print(filename, 'candidate_replacements=', n_cand, 'quotient_replacements=', n_q)
