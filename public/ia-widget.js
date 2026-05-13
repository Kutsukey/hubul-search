(function () {
    const CONFIG = {
        masterDataUrl: 'outputs/hybrid_master.json',
        announcementsUrl: 'outputs/announcements_live.json',
        corporateRed: '#A6192E',
        corporateRedLight: 'rgba(166, 25, 46, 0.08)'
    };

    let masterData = [];
    let currentAnnouncements = [];
    let fuseInstance = null;
    let fuseAnnouncements = null;
    const commonIntents = ["akademik takvim", "staj başvurusu", "yemekhane menüsü", "vpn kurulumu", "ders programı", "öğrenci işleri"];

    const styles = `
        /* TEMA ARŞİVİ VE KÖK RENKLER */
        
        /* AKTİF TEMA: Hacettepe Kurumsal Kırmızı*/
        :root {
            --h-primary: #A6192E; 
            --h-primary-light: rgba(166, 25, 46, 0.08); 
            --h-bg-color: #ffffff;
            --h-border: #e5e7eb;
            --h-text-main: #111827;
            --h-text-muted: #6b7280;
        }

        /* =========================================================
        ARŞİVLENMİŞ TEMA: "Cyberpunk AI / Start-Up" Moru
        =========================================================
        :root {
            --h-primary: #4f46e5; 
            --h-primary-light: rgba(79, 70, 229, 0.08); 
            --h-bg-color: #ffffff;
            --h-border: #e5e7eb;
            --h-text-main: #111827;
            --h-text-muted: #6b7280;
        }
        */

        #hubul-fab {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 56px;
            height: 56px;
            background: #ffffff;
            color: var(--h-primary); /* Kırmızı İkon */
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08), 0 0 0 1px rgba(166, 25, 46, 0.1);
            z-index: 999999;
            transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
            user-select: none;
        }

        #hubul-fab:hover {
            transform: scale(1.05) translateY(-2px);
            box-shadow: 0 8px 24px rgba(166, 25, 46, 0.15), 0 0 0 1px rgba(166, 25, 46, 0.15);
        }

        #hubul-fab svg {
            width: 24px;
            height: 24px;
            transition: transform 0.3s ease;
        }

        #hubul-fab:hover svg {
            transform: scale(1.1);
        }

        @property --h-angle {
            syntax: '<angle>';
            initial-value: 0deg;
            inherits: false;
        }

        #hubul-panel {
            position: fixed;
            bottom: 100px;
            right: 30px;
            width: 400px;
            height: 600px;
            max-height: calc(100vh - 120px);
            background: 
                linear-gradient(var(--h-bg-color), var(--h-bg-color)) padding-box,
                conic-gradient(from var(--h-angle), transparent 20%, rgba(166, 25, 46, 0.1) 80%, rgba(166, 25, 46, 1) 100%) border-box;
            border: 1.5px solid transparent; 
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.12);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transform: translateY(15px);
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s ease-out, transform 0.2s ease-out;
            z-index: 999998;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            padding-bottom: env(safe-area-inset-bottom);
        }

        .h-panel-active {
            opacity: 1 !important;
            transform: translateY(0) !important;
            pointer-events: all !important;
            animation: h-spin-border 1.5s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }

        @keyframes h-spin-border {
            100% { --h-angle: 360deg; }
        }

        .h-close {
            cursor: pointer;
            font-size: 28px;
            line-height: 1;
            color: var(--h-text-muted);
            transition: color 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 8px;
            margin-right: -8px;
        }
        .h-close:hover { color: var(--h-text-main); background: var(--h-bg-color); }

        .h-search-area {
            padding: 16px 20px;
            background: white;
            border-bottom: 1px solid var(--h-border);
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .h-search-icon {
            width: 20px;
            height: 20px;
            color: var(--h-primary);
            flex-shrink: 0;
            opacity: 0.8;
        }

        #h-input {
            flex: 1;
            padding: 4px 0;
            font-size: 16px !important; 
            border: none;
            outline: none;
            background: transparent;
            font-family: inherit;
            color: var(--h-text-main);
            font-weight: 500;
        }
        
        #h-input::placeholder { color: #9ca3af; font-weight: 400; }

        .h-suggest-btn {
            background: white;
            color: var(--h-text-muted);
            padding: 7px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid var(--h-border);
            transition: 0.2s;
            white-space: nowrap;
        }
        .h-suggest-btn:hover { border-color: var(--h-primary); color: var(--h-primary); background: var(--h-primary-light); }

        #h-results {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .h-result-card {
            background: white;
            border-radius: 12px;
            padding: 14px 16px;
            border: 1px solid var(--h-border);
            cursor: pointer;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            transition: all 0.2s ease;
            text-align: left;
        }
        .h-result-card:hover {
            border-color: #d1d5db;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.05);
            transform: translateY(-1px);
        }

        .h-result-card.h-ann-card {
            border-left: 3px solid var(--h-primary);
            background: #fafafa;
        }
        .h-ann-card-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        .h-ann-source {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--h-text-muted);
        }
        .h-ann-title {
            font-size: 13.5px;
            font-weight: 600;
            color: var(--h-text-main);
            line-height: 1.45;
            text-decoration: none;
            display: block;
        }
        .h-ann-title:hover { color: var(--h-primary); text-decoration: underline; }

        .h-category-pill {
            font-size: 10px;
            color: var(--h-text-muted);
            margin-bottom: 5px;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.8px;
        }

        .h-entity-title {
            font-size: 16px;
            font-weight: 700;
            color: var(--h-text-main);
            margin: 0 0 10px 0;
            letter-spacing: -0.4px;
            line-height: 1.3;
        }

        .h-announcement {
            background: var(--h-primary-light);
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 14px;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .h-ann-tag {
            background: var(--h-primary);
            color: #fff;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            flex-shrink: 0;
        }
        .h-announcement a { color: var(--h-primary); font-weight: 600; text-decoration: none; }

        .h-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .h-chip {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: #fff;
            border: 1px solid var(--h-border);
            border-radius: 8px;
            padding: 7px 12px;
            font-size: 12.5px;
            font-weight: 600;
            color: var(--h-text-main);
            text-decoration: none;
            transition: 0.2s;
        }
        .h-chip:hover { border-color: var(--h-primary); color: var(--h-primary); background: var(--h-primary-light); }
        .h-chip.highlight { background: var(--h-primary); color: white; border-color: var(--h-primary); }
        .h-chip svg { width: 14px; height: 14px; opacity: 0.6; }
        .h-chip.highlight svg { opacity: 1; }

        .h-section-label {
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--h-text-muted);
            padding: 4px 4px 0;
        }

        .h-empty { text-align: center; color: var(--h-text-muted); padding: 40px 20px; font-size: 14px; }

        .h-skeleton {
            height: 75px;
            background: linear-gradient(90deg, #f0f0f0 25%, #e5e7eb 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: h-skeleton-loading 1.5s infinite;
            border-radius: 12px;
            margin-bottom: 12px;
            border: 1px solid var(--h-border);
        }
        .h-skeleton-small { height: 40px; width: 60%; margin-top: 8px; }
        @keyframes h-skeleton-loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .h-live-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
            border: 1px solid #86efac;
            border-radius: 8px;
            padding: 8px 12px;
            margin-top: 10px;
            font-size: 12px;
            font-weight: 600;
            color: #166534;
        }
        .h-live-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        @media (max-width: 480px) {
            #hubul-panel { width: calc(100vw - 32px); right: 16px; bottom: 85px; border-radius: 20px; }
            #hubul-fab { bottom: 20px; right: 16px; }
        }

        .h-result-card, .h-skeleton, .h-section-label {
            animation: h-card-pop 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
            opacity: 0;
            transform: translateY(15px) scale(0.98);
        }
        
        .h-section-label { animation-delay: 0.02s; }
        .h-result-card:nth-child(1), .h-skeleton:nth-child(1) { animation-delay: 0.05s; }
        .h-result-card:nth-child(2), .h-skeleton:nth-child(2) { animation-delay: 0.10s; }
        .h-result-card:nth-child(3), .h-skeleton:nth-child(3) { animation-delay: 0.15s; }
        .h-result-card:nth-child(4), .h-skeleton:nth-child(4) { animation-delay: 0.20s; }
        .h-result-card:nth-child(5) { animation-delay: 0.25s; }

        @keyframes h-card-pop {
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
    `;

    const html = `
        <div id="hubul-fab" title="Hacettepe Akıllı Asistan">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
        </div>
        <div id="hubul-panel">
            <div class="h-search-area">
                <svg class="h-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                <input type="text" id="h-input" placeholder="Sistem hazırlanıyor..." autocomplete="off">
                <span class="h-close" id="h-close">&times;</span>
            </div>
            <div id="h-results"></div>
        </div>
    `;

    function loadFuse(callback) {
        if (window.Fuse) return callback();
        const script = document.createElement('script');
        script.src = "https://cdn.jsdelivr.net/npm/fuse.js@7.0.0";
        script.onload = callback;
        document.head.appendChild(script);
    }

    function inject() {
        const styleEl = document.createElement('style');
        styleEl.textContent = styles;
        document.head.appendChild(styleEl);

        const container = document.createElement('div');
        container.innerHTML = html;
        document.body.appendChild(container);

        const fab = document.getElementById('hubul-fab');
        const panel = document.getElementById('hubul-panel');
        const close = document.getElementById('h-close');
        const input = document.getElementById('h-input');

        fab.addEventListener('click', (e) => {
            e.stopPropagation();
            const isActive = panel.classList.toggle('h-panel-active');
            if (isActive) {
                setTimeout(() => input.focus(), 400);
            }
        });

        close.addEventListener('click', () => {
            panel.classList.remove('h-panel-active');
        });

        document.addEventListener('click', (e) => {
            if (!panel.contains(e.target) && !fab.contains(e.target) && panel.classList.contains('h-panel-active')) {
                panel.classList.remove('h-panel-active');
            }
        });

        input.oninput = (e) => handleSearch(e.target.value);

        loadFuse(() => initData());
    }

    function getSubdomain(url) {
        if (!url) return "";
        return url.replace('https://', '').replace('http://', '').replace('www.', '').split('.')[0].toLowerCase();
    }

    function isRingActive() {
        const now = new Date();
        const currentMins = now.getHours() * 60 + now.getMinutes();
        const day = now.getDay();
        const isWeekend = (day === 0 || day === 6);

        const egoHaftaIci = "00:10,00:40,01:25,06:35,06:40,06:45,06:50,06:55,07:00,07:03,07:06,07:09,07:12,07:15,07:18,07:21,07:24,07:27,07:30,07:33,07:36,07:39,07:42,07:45,07:48,07:51,07:54,07:57,08:00,08:03,08:06,08:09,08:12,08:15,08:18,08:21,08:24,08:27,08:30,08:33,08:36,08:39,08:42,08:45,08:48,08:51,08:54,08:57,09:00,09:03,09:06,09:09,09:12,09:15,09:18,09:21,09:24,09:27,09:30,09:33,09:36,09:39,09:42,09:45,09:48,09:51,09:54,09:57,10:00,10:08,10:14,10:20,10:26,10:32,10:38,10:44,10:50,10:56,11:02,11:08,11:14,11:20,11:26,11:32,11:38,11:44,11:50,11:56,12:02,12:08,12:11,12:14,12:17,12:20,12:23,12:26,12:29,12:32,12:35,12:38,12:41,12:44,12:47,12:50,12:53,12:56,12:59,13:02,13:05,13:08,13:11,13:14,13:17,13:20,13:23,13:26,13:29,13:32,13:35,13:38,13:41,13:44,13:47,13:50,13:53,13:56,13:59,14:02,14:05,14:08,14:11,14:14,14:17,14:20,14:23,14:26,14:29,14:32,14:35,14:38,14:41,14:44,14:47,14:50,14:53,14:56,14:59,15:02,15:05,15:08,15:11,15:14,15:17,15:20,15:23,15:26,15:29,15:32,15:35,15:38,15:41,15:44,15:47,15:50,15:53,15:56,15:59,16:02,16:05,16:08,16:11,16:14,16:17,16:20,16:23,16:26,16:29,16:32,16:35,16:38,16:41,16:44,16:47,16:50,16:53,16:56,17:00,17:05,17:10,17:15,17:20,17:25,17:30,17:35,17:40,17:45,17:50,17:55,18:00,18:05,18:10,18:15,18:20,18:25,18:30,18:35,18:40,18:45,18:50,18:55,19:00,19:05,19:10,19:15,19:20,19:25,19:30,19:38,19:46,19:54,20:02,20:10,20:18,20:26,20:34,20:42,20:50,20:58,21:06,21:14,21:22,21:30,21:38,21:46,21:54,22:02,22:10,22:18,22:26,22:34,22:42,22:50,22:58,23:06,23:14,23:22,23:30,23:40";
        const egoHaftaSonu = "00:10,00:40,01:25,06:35,06:45,06:50,07:05,07:15,07:20,07:35,07:45,07:50,08:05,08:20,08:25,08:30,08:40,08:50,09:00,09:10,09:20,09:30,09:40,09:50,10:00,10:10,10:20,10:30,10:40,10:50,11:00,11:10,11:20,11:30,11:40,11:50,12:00,12:10,12:20,12:30,12:40,12:50,13:00,13:10,13:20,13:30,13:40,13:50,14:00,14:10,14:20,14:30,14:40,14:50,15:00,15:10,15:20,15:30,15:40,15:50,16:00,16:10,16:20,16:30,16:40,16:50,17:00,17:10,17:20,17:30,17:40,17:50,18:00,18:10,18:20,18:30,18:40,18:50,19:00,19:10,19:20,19:30,19:40,19:50,20:00,20:10,20:20,20:30,20:40,20:50,21:00,21:10,21:20,21:30,21:40,21:50,22:00,22:10,22:20,22:30,22:40,22:50,23:00,23:10,23:20,23:30,23:40";

        const activeSchedule = isWeekend ? egoHaftaSonu : egoHaftaIci;
        const times = activeSchedule.split(',');

        let nextMins = -1;

        for (let time of times) {
            let parts = time.split(':');
            let busMins = parseInt(parts[0]) * 60 + parseInt(parts[1]);
            let busHour = parseInt(parts[0]);

            if (currentMins >= 360 && busHour < 3) continue;

            if (busMins >= currentMins) {
                nextMins = busMins - currentMins;
                break;
            }
        }

        if (nextMins === -1 && currentMins < 360) {
            for (let time of times) {
                let parts = time.split(':');
                let busMins = parseInt(parts[0]) * 60 + parseInt(parts[1]);
                let busHour = parseInt(parts[0]);
                if (busHour >= 6) {
                    nextMins = (busMins + 24 * 60) - currentMins;
                    break;
                }
            }
        }

        return nextMins !== -1;
    }

    async function initData() {
        const input = document.getElementById('h-input');
        const cacheKey = 'hubul_master_data';
        const annCacheKey = 'hubul_ann_data';
        const cacheTimeKey = 'hubul_last_fetch';

        const cachedMaster = localStorage.getItem(cacheKey);
        const cachedAnn = localStorage.getItem(annCacheKey);
        const now = new Date().getTime();

        if (cachedMaster) {
            masterData = JSON.parse(cachedMaster);
            input.placeholder = "Ne arıyorsun? (Örn: oidb, erasmus)";
            showFiller(); // Cache var, anında göster!
        } else {
            showFiller(true);
        }
        if (cachedAnn) {
            currentAnnouncements = JSON.parse(cachedAnn);
        }

        async function refreshData() {
            try {
                const lastFetch = localStorage.getItem(cacheTimeKey);

                if (lastFetch && (now - parseInt(lastFetch)) < 1 * 60 * 60 * 1000) return;

                const cacheBuster = '?v=' + now;
                const [res, annRes] = await Promise.all([
                    fetch(CONFIG.masterDataUrl + cacheBuster),
                    fetch(CONFIG.announcementsUrl + cacheBuster)
                ]);

                if (res.ok && annRes.ok) {
                    const newMaster = await res.json();
                    const newAnn = await annRes.json();

                    if (JSON.stringify(newMaster) !== cachedMaster) {
                        masterData = newMaster;
                        localStorage.setItem(cacheKey, JSON.stringify(newMaster));

                        masterData.forEach(item => {
                            if (!item.search_alias && item.url) item.search_alias = getSubdomain(item.url);
                            const intents = item.action_links ? item.action_links.map(l => l.intent).join(" ") : "";
                            const subs = item.sub_branches ? item.sub_branches.join(" ") : "";
                            item.search_text = `${item.search_alias} ${item.entity_name} ${intents} ${subs} ${item.description || ""}`.toLowerCase();
                        });
                    }

                    if (JSON.stringify(newAnn) !== cachedAnn) {
                        currentAnnouncements = newAnn;
                        localStorage.setItem(annCacheKey, JSON.stringify(newAnn));
                    }

                    localStorage.setItem(cacheTimeKey, now.toString());
                }
            } catch (e) { console.error("Veri güncellenemedi:", e); }
        }

        if (!cachedMaster) {
            await refreshData();
            input.placeholder = "Ne arıyorsun? (Örn: staj, oidb)";
            if (!input.value.trim()) showFiller(false);
        } else {
            refreshData();
        }

        const flatAnnouncements = [];
        currentAnnouncements.forEach(group => {
            (group.items || []).forEach(item => {
                flatAnnouncements.push({
                    title: item.title, link: item.link, source: item.source || group.entity, entity: group.entity,
                    search_text: `${item.title} ${item.source || group.entity}`.toLowerCase()
                });
            });
        });
        fuseAnnouncements = new Fuse(flatAnnouncements, {
            includeScore: true, includeMatches: true, threshold: 0.45, ignoreLocation: true, ignoreFieldNorm: true,
            keys: [{ name: 'title', weight: 3.0 }, { name: 'source', weight: 1.5 }, { name: 'search_text', weight: 1.0 }]
        });

        fuseInstance = new Fuse(masterData, {
            includeScore: true, threshold: 0.45, ignoreLocation: true, useExtendedSearch: true,
            keys: [{ name: 'search_alias', weight: 5.0 }, { name: 'entity_name', weight: 3.0 }, { name: 'description', weight: 2.0 }, { name: 'search_text', weight: 1.0 }]
        });
    }

    function handleSearch(val) {
        const query = val.trim().toLocaleLowerCase('tr-TR');
        if (query.length < 2) {
            showFiller();
            return;
        }

        let searchTerms = query.split(/\s+/);

        let fuseQuery = {
            $or: searchTerms.map(term => ({
                $or: [
                    { search_alias: term },
                    { entity_name: term },
                    { description: term },
                    { search_text: term }
                ]
            }))
        };

        const fuseResults = fuseInstance.search(fuseQuery);
        let entityResults = fuseResults.map(fr => {
            let item = fr.item;
            const nameLower = item.entity_name.toLocaleLowerCase('tr-TR');

            let score = (1 - fr.score) * 1000;
            score += (item.priority_score || 0);

            if (searchTerms.some(term => item.search_alias === term || item.search_alias === term + 'db' || item.search_alias + 'db' === term)) score += 10000;
            if (searchTerms.includes("ai") && nameLower.includes("yapay zeka")) score += 10000;

            const isAcademic = nameLower.includes("bölümü") || nameLower.includes("fakültesi") || nameLower.includes("ana bilim") || nameLower.includes("enstitü");
            const isYurt = (query.includes("yurt") || query.includes("barınma") || query.includes("barinma")) && !query.includes("yurtdışı");

            if (["takv", "akademik", "harç", "harc", "öde", "ode", "otomas", "transk", "mezun", "belge", "bilsis", "kayıt", "öğren", "ogren", "işler", "isler"].some(k => query.includes(k)) && nameLower.includes("öğrenci") && nameLower.includes("işleri")) score += 5000;

            if ((isYurt || ["yemek", "ymek", "menü", "menu", "menn"].some(k => query.includes(k))) && nameLower.includes("sağlık") && nameLower.includes("kültür")) score += 5000;

            if (["kütüphane", "kutuph"].some(k => query.includes(k)) && nameLower.includes("kütüphane")) score += 5000;

            if (["eduroam", "vpn", "wifi", "internet", "şifre", "sifre", "unuttum"].some(k => query.includes(k)) && nameLower.includes("bilgi işlem")) score += 5000;

            const isRingSearch = ["ring", "servis", "otobus"].some(k => query.includes(k));
            const isIdariIsler = nameLower.includes("idari") && nameLower.includes("işler");
            if (isRingSearch && isIdariIsler) {
                if (!isRingActive()) return null;
                score += 5000;
            }

            const isEU = nameLower.includes("dış ilişkiler") || nameLower.includes("uluslararası") || nameLower.includes("ab ofisi") || nameLower.includes("european") || nameLower.includes("avrupa") || nameLower.includes("erasmus");
            if (["erasmus", "yurtdışı", "yurtdisi", "değişim", "degisim", "mevlana", "farabi"].some(k => query.includes(k)) && !isAcademic && isEU) score += 5000;

            if (searchTerms.some(term => term.length > 3 && nameLower.includes(term))) score += 1000;

            const matchedIntents = item.action_links
                ? item.action_links.filter(l => searchTerms.some(t => l.intent.toLocaleLowerCase('tr-TR').includes(t))).map(l => l.intent)
                : [];

            return { item, score, matchedIntents };
        }).filter(res => res !== null);

        // 🛡️ RING KARTI İÇİN KESKİN NİŞANCI KALKANI (Spring, Engineering Tıkacı)
        entityResults = entityResults.filter(r => {
            if (r.item.is_ring) {
                // Kullanıcının yazdığı cümleyi kelime kelime parçala
                const qWords = query.toLowerCase().trim().split(/\s+/);

                // Sadece ve SADECE bu kelimeler TAM OLARAK yazıldıysa Ring kartı çıkabilir
                const allowedTriggers = ["ring", "130", "otobüs", "otobus", "servis", "ego", "ulaşım", "beytepe"];

                // Yazılan kelimelerden en az biri listemizdekilerle BİREBİR eşleşiyor mu?
                const isExactMatch = qWords.some(w => allowedTriggers.includes(w));

                return isExactMatch; // Eşleşmiyorsa acımadan false dön ve kartı çöpe at!
            }
            return true; // Ring değilse normal kurallarla devam et
        });

        entityResults.sort((a, b) => b.score - a.score);

        let annResults = [];
        if (fuseAnnouncements) {
            const annSearchResults = fuseAnnouncements.search(query);

            const minSolidBlock = query.length < 4 ? query.length : 3;

            annResults = annSearchResults.filter(r => {
                const sourceLower = (r.item.source || "").toLowerCase();
                const isMerkezAnn = sourceLower.includes("merkezi") && (sourceLower.includes("araştırma") || sourceLower.includes("uygulama"));
                if (isMerkezAnn && r.score > 0.15) return false;
                if (r.score >= 0.45) return false;

                let hasSolidBlock = false;
                if (r.matches) {
                    for (const match of r.matches) {
                        for (const [start, end] of match.indices) {
                            if ((end - start + 1) >= minSolidBlock) {
                                hasSolidBlock = true;
                                break;
                            }
                        }
                        if (hasSolidBlock) break;
                    }
                }

                if (!hasSolidBlock) return false;

                return true;
            }).slice(0, 2).map(r => ({ ann: r.item, score: (1 - r.score) * 800 }));
        }

        render(entityResults.slice(0, 5), annResults);
    }

    function render(entityResults, annResults = [], isFiller = false, hasHistory = false) {
        const cont = document.getElementById('h-results');

        if (entityResults.length === 0 && annResults.length === 0) {
            cont.innerHTML = '<div class="h-empty">Sonuç bulunamadı.</div>';
            return;
        }

        let html = '';

        if (isFiller) {
            const title = hasHistory ? "🕒 Son Ziyaretler & Öneriler" : "💡 Öneriler";
            html += `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; padding-top:4px;">
                    <div class="h-section-label" style="padding:0">${title}</div>
                    ${hasHistory ? `<button onclick="window.hubul_clear_history()" style="background:none; border:none; color:var(--h-text-muted); font-size:10px; cursor:pointer; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; transition:0.2s;" onmouseover="this.style.color='var(--h-primary)'" onmouseout="this.style.color='var(--h-text-muted)'">GEÇMİŞİ TEMİZLE</button>` : ''}
                </div>
            `;
        }

        const renderedEntityNames = entityResults.map(r => r.item.entity_name);

        const standaloneAnns = annResults.filter(r => !renderedEntityNames.includes(r.ann.entity));

        if (isFiller && standaloneAnns.length > 0) {
            html += '<div class="h-section-label">📢 Duyurular</div>';
            standaloneAnns.slice(0, 2).forEach(r => {
                const ann = r.ann;
                html += `
                    <div class="h-result-card h-ann-card" onclick="window.open('${ann.link}','_blank'); hubul_save('__ann__${ann.entity}');">
                        <div class="h-ann-card-header">
                            <span class="h-ann-tag">Yeni</span>
                            <span class="h-ann-source">${ann.source}</span>
                        </div>
                        <div class="h-ann-title">${ann.title}</div>
                    </div>
                `;
            });
        }

        if (entityResults.length > 0) {
            if (!isFiller) {
                html += `<div class="h-section-label">Tam Eşleşen</div>`;
            }
            const firstResult = entityResults[0];
            const item = firstResult.item;
            const matchedIntents = firstResult.matchedIntents || [];

            let cardHtml = `
                <div class="h-result-card" onclick="if(event.target.tagName !== 'A') { window.open('${item.url}','_blank'); hubul_save('${item.entity_name}'); }">
                    <div class="h-category-pill">${item.category || "Birim"}</div>
                    <h3 class="h-entity-title">${item.entity_name}</h3>
            `;

            const ann = currentAnnouncements.find(a => a.entity === item.entity_name);
            if (ann && ann.items && ann.items.length > 0) {
                cardHtml += `<div class="h-announcement"><span class="h-ann-tag">Yeni</span><a href="${ann.items[0].link}" target="_blank" onclick="event.stopPropagation();">${ann.items[0].title}</a></div>`;
            }

            if (item.action_links && item.action_links.length > 0) {
                cardHtml += '<div class="h-chips">';

                // 🚀 ZEKİ SIRALAMA: Aranan kelimeye uyan butonları en öne çek!
                const searchVal = document.getElementById('h-input').value.toLowerCase().trim();
                let sortedLinks = [...item.action_links];

                if (searchVal.length > 2) {
                    sortedLinks.sort((a, b) => {
                        const aMatch = a.intent.toLowerCase().includes(searchVal) || a.url.toLowerCase().includes(searchVal) ? 1 : 0;
                        const bMatch = b.intent.toLowerCase().includes(searchVal) || b.url.toLowerCase().includes(searchVal) ? 1 : 0;
                        return bMatch - aMatch; // Eşleşenleri başa at
                    });
                }

                // Şimdi güvenle ilk 3'ü alabiliriz, çünkü önemli olanlar artık en önde!
                sortedLinks.slice(0, 3).forEach(l => {
                    const isHighlight = searchVal.length > 2 && (l.intent.toLowerCase().includes(searchVal) || l.url.toLowerCase().includes(searchVal));
                    const isJs = l.url.startsWith('javascript:');
                    cardHtml += `<a href="${l.url}" ${isJs ? '' : 'target="_blank"'} class="h-chip${isHighlight ? ' highlight' : ''}" onclick="event.stopPropagation(); hubul_save('${item.entity_name}');">
                        <span>${l.intent}</span>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
                    </a>`;
                });
                cardHtml += '</div>';
            }

            if (item.is_ring) {
                const now = new Date();
                const currentMins = now.getHours() * 60 + now.getMinutes();
                const day = now.getDay();
                const isWeekend = (day === 0 || day === 6);

                const egoHaftaIci = "00:10,00:40,01:25,06:35,06:40,06:45,06:50,06:55,07:00,07:03,07:06,07:09,07:12,07:15,07:18,07:21,07:24,07:27,07:30,07:33,07:36,07:39,07:42,07:45,07:48,07:51,07:54,07:57,08:00,08:03,08:06,08:09,08:12,08:15,08:18,08:21,08:24,08:27,08:30,08:33,08:36,08:39,08:42,08:45,08:48,08:51,08:54,08:57,09:00,09:03,09:06,09:09,09:12,09:15,09:18,09:21,09:24,09:27,09:30,09:33,09:36,09:39,09:42,09:45,09:48,09:51,09:54,09:57,10:00,10:08,10:14,10:20,10:26,10:32,10:38,10:44,10:50,10:56,11:02,11:08,11:14,11:20,11:26,11:32,11:38,11:44,11:50,11:56,12:02,12:08,12:11,12:14,12:17,12:20,12:23,12:26,12:29,12:32,12:35,12:38,12:41,12:44,12:47,12:50,12:53,12:56,12:59,13:02,13:05,13:08,13:11,13:14,13:17,13:20,13:23,13:26,13:29,13:32,13:35,13:38,13:41,13:44,13:47,13:50,13:53,13:56,13:59,14:02,14:05,14:08,14:11,14:14,14:17,14:20,14:23,14:26,14:29,14:32,14:35,14:38,14:41,14:44,14:47,14:50,14:53,14:56,14:59,15:02,15:05,15:08,15:11,15:14,15:17,15:20,15:23,15:26,15:29,15:32,15:35,15:38,15:41,15:44,15:47,15:50,15:53,15:56,15:59,16:02,16:05,16:08,16:11,16:14,16:17,16:20,16:23,16:26,16:29,16:32,16:35,16:38,16:41,16:44,16:47,16:50,16:53,16:56,17:00,17:05,17:10,17:15,17:20,17:25,17:30,17:35,17:40,17:45,17:50,17:55,18:00,18:05,18:10,18:15,18:20,18:25,18:30,18:35,18:40,18:45,18:50,18:55,19:00,19:05,19:10,19:15,19:20,19:25,19:30,19:38,19:46,19:54,20:02,20:10,20:18,20:26,20:34,20:42,20:50,20:58,21:06,21:14,21:22,21:30,21:38,21:46,21:54,22:02,22:10,22:18,22:26,22:34,22:42,22:50,22:58,23:06,23:14,23:22,23:30,23:40";
                const egoHaftaSonu = "00:10,00:40,01:25,06:35,06:45,06:50,07:05,07:15,07:20,07:35,07:45,07:50,08:05,08:20,08:25,08:30,08:40,08:50,09:00,09:10,09:20,09:30,09:40,09:50,10:00,10:10,10:20,10:30,10:40,10:50,11:00,11:10,11:20,11:30,11:40,11:50,12:00,12:10,12:20,12:30,12:40,12:50,13:00,13:10,13:20,13:30,13:40,13:50,14:00,14:10,14:20,14:30,14:40,14:50,15:00,15:10,15:20,15:30,15:40,15:50,16:00,16:10,16:20,16:30,16:40,16:50,17:00,17:10,17:20,17:30,17:40,17:50,18:00,18:10,18:20,18:30,18:40,18:50,19:00,19:10,19:20,19:30,19:40,19:50,20:00,20:10,20:20,20:30,20:40,20:50,21:00,21:10,21:20,21:30,21:40,21:50,22:00,22:10,22:20,22:30,22:40,22:50,23:00,23:10,23:20,23:30,23:40";

                const activeSchedule = isWeekend ? egoHaftaSonu : egoHaftaIci;
                const times = activeSchedule.split(',');

                let nextMins = -1;
                let foundTime = "";

                for (let time of times) {
                    let parts = time.split(':');
                    let busMins = parseInt(parts[0]) * 60 + parseInt(parts[1]);
                    let busHour = parseInt(parts[0]);
                    if (currentMins >= 360 && busHour < 3) continue;
                    if (busMins >= currentMins) {
                        nextMins = busMins - currentMins;
                        foundTime = time;
                        break;
                    }
                }

                if (nextMins === -1 && currentMins < 360) {
                    for (let time of times) {
                        let parts = time.split(':');
                        let busMins = parseInt(parts[0]) * 60 + parseInt(parts[1]);
                        let busHour = parseInt(parts[0]);
                        if (busHour >= 6) {
                            nextMins = (busMins + 24 * 60) - currentMins;
                            foundTime = time;
                            break;
                        }
                    }
                }

                let statusText = "Sonraki Kalkış Aranıyor...";
                if (nextMins !== -1) {
                    if (nextMins === 0) statusText = `Şu an kalkıyor! (${foundTime})`;
                    else statusText = `Sonraki Ring: ${nextMins} dk sonra (${foundTime})`;
                } else {
                    statusText = "Bugün için seferler sona erdi.";
                }

                cardHtml += `
                    <div class="h-live-badge">
                        <div class="h-live-dot"></div>
                        <span>${statusText}</span>
                    </div>
                `;
            }

            cardHtml += '</div>';
            html += cardHtml;
        }

        if (!isFiller && standaloneAnns.length > 0) {
            html += '<div class="h-section-label" style="margin-top:8px;">📢 Duyurular</div>';
            standaloneAnns.slice(0, 2).forEach(r => {
                const ann = r.ann;
                html += `
                    <div class="h-result-card h-ann-card" onclick="window.open('${ann.link}','_blank'); hubul_save('__ann__${ann.entity}');">
                        <div class="h-ann-card-header">
                            <span class="h-ann-tag">Yeni</span>
                            <span class="h-ann-source">${ann.source}</span>
                        </div>
                        <div class="h-ann-title">${ann.title}</div>
                    </div>
                `;
            });
        }

        if (entityResults.length > 1) {
            if (!isFiller) {
                html += '<div class="h-section-label" style="margin-top:8px;">Diğer Sonuçlar</div>';
            }
            html += entityResults.slice(1).map(r => {
                const item = r.item;
                const matchedIntents = r.matchedIntents || [];

                let cardHtml = `
                    <div class="h-result-card" onclick="if(event.target.tagName !== 'A') { window.open('${item.url}','_blank'); hubul_save('${item.entity_name}'); }">
                        <div class="h-category-pill">${item.category || "Birim"}</div>
                        <h3 class="h-entity-title">${item.entity_name}</h3>
                `;

                const ann = currentAnnouncements.find(a => a.entity === item.entity_name);
                if (ann && ann.items && ann.items.length > 0) {
                    cardHtml += `<div class="h-announcement"><span class="h-ann-tag">Yeni</span><a href="${ann.items[0].link}" target="_blank" onclick="event.stopPropagation();">${ann.items[0].title}</a></div>`;
                }

                if (item.action_links && item.action_links.length > 0) {
                    cardHtml += '<div class="h-chips">';

                    // 🚀 ZEKİ SIRALAMA: Aranan kelimeye uyan butonları en öne çek!
                    const searchVal = document.getElementById('h-input').value.toLowerCase().trim();
                    let sortedLinks = [...item.action_links];

                    if (searchVal.length > 2) {
                        sortedLinks.sort((a, b) => {
                            const aMatch = a.intent.toLowerCase().includes(searchVal) || a.url.toLowerCase().includes(searchVal) ? 1 : 0;
                            const bMatch = b.intent.toLowerCase().includes(searchVal) || b.url.toLowerCase().includes(searchVal) ? 1 : 0;
                            return bMatch - aMatch; // Eşleşenleri başa at
                        });
                    }

                    sortedLinks.slice(0, 3).forEach(l => {
                        const isHighlight = searchVal.length > 2 && (l.intent.toLowerCase().includes(searchVal) || l.url.toLowerCase().includes(searchVal));
                        const isJs = l.url.startsWith('javascript:');
                        cardHtml += `<a href="${l.url}" ${isJs ? '' : 'target="_blank"'} class="h-chip${isHighlight ? ' highlight' : ''}" onclick="event.stopPropagation(); hubul_save('${item.entity_name}');">
                            <span>${l.intent}</span>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
                        </a>`;
                    });
                    cardHtml += '</div>';
                }
                cardHtml += '</div>';
                return cardHtml;
            }).join('');
        }

        cont.innerHTML = html;
    }

    function showFiller(isLoading = false) {
        const cont = document.getElementById('h-results');

        if (isLoading) {
            cont.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; padding-top:4px;">
                    <div class="h-section-label" style="padding:0">💡 Kampüs Hazırlanıyor...</div>
                </div>
                <div class="h-skeleton"></div>
                <div class="h-skeleton"></div>
                <div class="h-skeleton h-skeleton-small"></div>
            `;
            return;
        }

        if (masterData.length === 0) return;

        const history = JSON.parse(localStorage.getItem('hubul_history') || '[]');
        let items = [];
        let hasHistory = false;

        const prioritySources = ["Öğrenci İşleri Daire Başkanlığı", "Sağlık, Kültür ve Spor Daire Başkanlığı"];
        let priorityAnns = [];
        currentAnnouncements.forEach(group => {
            if (prioritySources.includes(group.entity)) {
                (group.items || []).slice(0, 1).forEach(it => {
                    priorityAnns.push({ ann: { ...it, source: group.entity, entity: group.entity }, score: 1000 });
                });
            }
        });

        if (history.length > 0) {
            history.forEach(n => {
                if (n.startsWith('__ann__')) return;
                const found = masterData.find(m => m.entity_name === n);
                if (found) { items.push({ item: found, score: 1, matchedIntents: [] }); hasHistory = true; }
            });
        }
        if (items.length < 3) {
            const vips = masterData.filter(m => {
                if (m.is_ring) return true;
                const n = m.entity_name.toLowerCase();
                const a = (m.search_alias || "").toLowerCase();
                return ["öidb", "yemekhane", "kütüphane"].some(k => n.includes(k) || a === k);
            });

            vips.forEach(v => {
                if (!items.find(i => i.item.entity_name === v.entity_name)) items.push({ item: v, score: 1, matchedIntents: [] });
            });
        }
        render(items.slice(0, 3), priorityAnns.slice(0, 2), true, hasHistory);
    }

    window.hubul_save = (name) => {
        let h = JSON.parse(localStorage.getItem('hubul_history') || '[]');
        h = h.filter(x => x !== name);
        h.unshift(name);
        localStorage.setItem('hubul_history', JSON.stringify(h.slice(0, 5)));
    };

    window.hubul_clear_history = () => {
        localStorage.removeItem('hubul_history');
        showFiller();
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inject);
    } else {
        inject();
    }
})();
