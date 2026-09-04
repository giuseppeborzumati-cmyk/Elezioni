from pathlib import Path
import re

TARGETS = [Path("index.html"), Path("404.html")]

CSS = r'''
        /* Cabina elettorale protetta: deterrenza client-side, non sostituisce i controlli fisici */
        #privacy-shield {
            position: fixed; inset: 0; z-index: 2147483647;
            background: #020617; color: #fff;
            display: none; align-items: center; justify-content: center;
            text-align: center; padding: 2rem;
        }
        #privacy-shield.active { display: flex !important; }
        #privacy-shield .privacy-card {
            max-width: 560px; border: 1px solid rgba(255,255,255,.18);
            border-radius: 1.5rem; padding: 2rem;
            background: rgba(15,23,42,.96); box-shadow: 0 24px 80px rgba(0,0,0,.55);
        }
        .secure-ballot-active #app-container {
            -webkit-user-select: none; user-select: none;
            -webkit-touch-callout: none;
        }
        .secure-ballot-active img { -webkit-user-drag: none; user-drag: none; }
        .secure-watermark {
            position: fixed; inset: 0; z-index: 35; pointer-events: none;
            display: none; overflow: hidden; opacity: .07;
        }
        .secure-ballot-active .secure-watermark { display: block; }
        .secure-watermark::before {
            content: "CABINA ELETTORALE PROTETTA  •  RIPRODUZIONE VIETATA  •  ";
            position: absolute; width: 180%; left: -30%; top: 44%;
            transform: rotate(-24deg); white-space: nowrap;
            font-size: clamp(24px, 4vw, 54px); font-weight: 900; letter-spacing: .18em;
            color: #0f172a;
        }
        @media print {
            body * { visibility: hidden !important; }
            body::before {
                visibility: visible !important; content: "STAMPA DISABILITATA — CABINA ELETTORALE PROTETTA";
                position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
                background: #000; color: #fff; font: 800 22px/1.4 sans-serif; text-align: center; padding: 2rem;
            }
        }
'''

BODY_OVERLAY = r'''
    <div id="privacy-shield" role="alert" aria-live="assertive">
        <div class="privacy-card">
            <div class="text-5xl mb-4">🔒</div>
            <h2 class="text-xl md:text-2xl font-black mb-3">Schermo protetto</h2>
            <p class="text-sm text-slate-200 leading-relaxed">
                La cabina è stata oscurata perché la finestra ha perso il focus, è stato richiesto un tentativo di stampa/cattura
                oppure è stata abbandonata la modalità protetta. Torna alla finestra elettorale per proseguire.
            </p>
        </div>
    </div>
    <div class="secure-watermark" aria-hidden="true"></div>
'''

JS = r'''
        // --- Protezioni della cabina elettorale (best effort browser-side) ---
        let privacyShieldTimer = null;
        let protectedFullscreenRequested = false;

        function isSensitiveVotingView() {
            return ['votoConsiglio','votoIstituto','votoConsulta','votoClasseStudenti','votoClasseGenitori','riepilogo'].includes(String(currentView || ''));
        }

        function updateSecureCabinState() {
            const active = isSensitiveVotingView();
            document.body.classList.toggle('secure-ballot-active', active);
            const btn = document.getElementById('secure-cabin-button');
            if (btn) btn.classList.toggle('hidden', !active);
        }

        function showPrivacyShield(reason = 'privacy') {
            if (!isSensitiveVotingView()) return;
            const el = document.getElementById('privacy-shield');
            if (!el) return;
            el.dataset.reason = reason;
            el.classList.add('active');
        }

        function hidePrivacyShieldSoon() {
            clearTimeout(privacyShieldTimer);
            privacyShieldTimer = setTimeout(() => {
                if (document.visibilityState === 'visible' && document.hasFocus()) {
                    document.getElementById('privacy-shield')?.classList.remove('active');
                }
            }, 450);
        }

        window.enterProtectedCabin = async function() {
            try {
                if (document.documentElement.requestFullscreen && !document.fullscreenElement) {
                    await document.documentElement.requestFullscreen({ navigationUI: 'hide' }).catch(() => {});
                }
                protectedFullscreenRequested = true;
                hidePrivacyShieldSoon();
                showNotification('Cabina protetta attiva',
                    'Modalità a schermo intero attivata. Screenshot e fotografie esterne non possono essere garantiti dal browser: usare una postazione sorvegliata e senza telefoni esterni.',
                    'info');
            } catch(e) {}
        };

        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState !== 'visible') showPrivacyShield('visibilitychange');
            else hidePrivacyShieldSoon();
        });
        window.addEventListener('blur', () => showPrivacyShield('blur'));
        window.addEventListener('focus', hidePrivacyShieldSoon);
        document.addEventListener('fullscreenchange', () => {
            if (protectedFullscreenRequested && isSensitiveVotingView() && !document.fullscreenElement) {
                showPrivacyShield('fullscreen-exit');
            }
        });
        window.addEventListener('beforeprint', () => showPrivacyShield('print'));
        window.addEventListener('afterprint', hidePrivacyShieldSoon);

        document.addEventListener('contextmenu', (e) => {
            if (isSensitiveVotingView()) { e.preventDefault(); showPrivacyShield('contextmenu'); hidePrivacyShieldSoon(); }
        }, true);
        document.addEventListener('copy', (e) => {
            if (isSensitiveVotingView()) { e.preventDefault(); showPrivacyShield('copy'); hidePrivacyShieldSoon(); }
        }, true);
        document.addEventListener('cut', (e) => {
            if (isSensitiveVotingView()) { e.preventDefault(); }
        }, true);
        document.addEventListener('dragstart', (e) => {
            if (isSensitiveVotingView()) e.preventDefault();
        }, true);
        document.addEventListener('keydown', (e) => {
            if (!isSensitiveVotingView()) return;
            const k = String(e.key || '').toLowerCase();
            const blocked = k === 'printscreen' ||
                ((e.ctrlKey || e.metaKey) && ['p','s','u'].includes(k)) ||
                ((e.ctrlKey || e.metaKey) && e.shiftKey && ['i','j','c'].includes(k));
            if (blocked) {
                e.preventDefault(); e.stopPropagation();
                showPrivacyShield('capture-key');
                hidePrivacyShieldSoon();
            }
        }, true);
        navigator.mediaDevices?.addEventListener?.('devicechange', () => {
            if (isSensitiveVotingView()) hidePrivacyShieldSoon();
        });
'''

BUTTON = r'''
                <button id="secure-cabin-button" onclick="enterProtectedCabin()" class="hidden bg-slate-950 hover:bg-black text-white font-extrabold py-1.5 px-3 rounded-lg shadow transition-all flex items-center gap-1.5 border border-slate-700">
                    <i data-lucide="lock-keyhole" class="w-3.5 h-3.5 text-yellow-300"></i> Cabina protetta
                </button>
'''

for p in TARGETS:
    if not p.exists():
        continue
    s = p.read_text(encoding='utf-8')

    # local vendor scripts, immutable copies in repo
    repl = {
        'https://cdn.tailwindcss.com':'vendor/tailwindcss.js',
        'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js':'vendor/xlsx.full.min.js',
        'https://unpkg.com/lucide@1.34.0/dist/umd/lucide.min.js':'vendor/lucide.min.js',
        'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js':'vendor/jspdf.umd.min.js',
        'https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.29/jspdf.plugin.autotable.min.js':'vendor/jspdf.plugin.autotable.min.js',
        'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js':'vendor/jszip.min.js',
    }
    for a,b in repl.items():
        s = s.replace(a,b)

    # restrict CSP script-src after moving main third-party libs local
    s = s.replace(
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdnjs.cloudflare.com https://unpkg.com https://www.gstatic.com;",
        "script-src 'self' 'unsafe-inline' https://www.gstatic.com;"
    )

    if '/* Cabina elettorale protetta:' not in s:
        s = s.replace('</style>', CSS + '\n    </style>', 1)

    if 'id="privacy-shield"' not in s:
        s = s.replace('<body class="flex flex-col justify-between relative min-h-screen">',
                      '<body class="flex flex-col justify-between relative min-h-screen">\n' + BODY_OVERLAY, 1)

    if 'id="secure-cabin-button"' not in s:
        anchor = '<div id="header-actions" class="flex items-center space-x-3"></div>'
        s = s.replace(anchor, '<div class="flex items-center gap-2">' + BUTTON + anchor + '</div>', 1)

    if '// --- Protezioni della cabina elettorale' not in s:
        anchor = "        let currentView = 'studentLogin';"
        if anchor not in s:
            raise SystemExit(f'Anchor currentView non trovato in {p}')
        s = s.replace(anchor, anchor + '\n' + JS, 1)

    # ensure state updates after each page render
    if 'updateSecureCabinState();' not in s:
        needle = '            updateHeaderActions();\n            lucide.createIcons();'
        if needle in s:
            s = s.replace(needle, '            updateHeaderActions();\n            updateSecureCabinState();\n            lucide.createIcons();', 1)
        else:
            raise SystemExit(f'Anchor showPage non trovato in {p}')

    # add explicit note in collaudo checklist
    marker = 'ESEGUI TEST BACKEND / FIREBASE'
    if marker in s and 'TEST PRIVACY CABINA' not in s:
        s = s.replace(marker, 'ESEGUI TEST BACKEND / FIREBASE', 1)
        note_anchor = '<div id="technical-check-result" class="mt-3 text-xs"></div>'
        s = s.replace(note_anchor, note_anchor + '''
                            <div class="mt-4 p-3 rounded-xl bg-slate-50 border text-[11px] text-slate-700 leading-relaxed">
                                <b>TEST PRIVACY CABINA:</b> entra in una scheda di prova, premi “Cabina protetta”, prova cambio scheda/finestra, Ctrl/Cmd+P, menu contestuale e PrintScreen.
                                La pagina deve oscurarsi. Per fotografie con un secondo dispositivo resta obbligatoria una misura organizzativa/fisica.
                            </div>''', 1)

    p.write_text(s, encoding='utf-8')
