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
        ARŞİVLENMİŞ TEMA: "Cyberpunk AI / Start-Up / Hacettepe" Moru
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
            max-height: calc(100dvh - 120px); 
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
            transition: opacity 0.2s ease-out, transform 0.2s ease-out, bottom 0.2s ease-out, max-height 0.2s ease-out; 
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
        .h-result-card.h-exact-card {
            border: 1px solid rgba(166, 25, 46, 0.18);
            box-shadow: 0 4px 18px rgba(166, 25, 46, 0.07), 0 1px 3px rgba(166, 25, 46, 0.03);
            background: linear-gradient(145deg, #ffffff, rgba(166, 25, 46, 0.015));
        }
        .h-result-card.h-exact-card:hover {
            box-shadow: 0 8px 24px rgba(166, 25, 46, 0.14), 0 3px 8px rgba(166, 25, 46, 0.06);
            border-color: rgba(166, 25, 46, 0.3);
            transform: translateY(-2px);
        }
        .h-divider {
            height: 1px;
            background: var(--h-border);
            margin: 4px 0;
            opacity: 0.35;
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

    function isTitleMatchingSearch(title) {
        const query = document.getElementById('h-input').value.toLowerCase().trim();
        if (!query) return false;
        return title.toLowerCase().includes(query);
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

    function prepareMasterData(data) {
        data.forEach(item => {
            if (!item.search_alias && item.url) item.search_alias = getSubdomain(item.url);
            
            // SEO ENJEKSİYONU: Makineye bilmediği kavramları gizlice öğretiyoruz
            let extraKeywords = "";
            const eName = item.entity_name.toLowerCase();
            
            // Erasmus ve Yurtdışı kelimelerini AB Ofisi'nin zihnine kazı!
            if (eName.includes("ab ofisi") || eName.includes("european") || eName.includes("dış ilişkiler")) {
                extraKeywords += " erasmus yurtdışı değişim farabi mevlana";
            }
            // Yemek, Yurt gibi kelimeleri SKS'nin zihnine kazı!
            if (eName.includes("sağlık") && eName.includes("kültür")) {
                extraKeywords += " yemekhane yemek menü yurt barınma mediko";
            }
            // İnternet sorunlarını Bilgi İşlem'e bağla!
            if (eName.includes("bilgi işlem")) {
                extraKeywords += " eduroam wifi vpn şifre internet";
            }

            // Bölüm, fakülte, enstitü ve yüksekokullara genel akademik kelimeleri ekle!
            const cat = (item.category || "").toLowerCase();
            if (cat.includes("bölüm") || cat.includes("fakülte") || cat.includes("enstitü") || cat.includes("yüksekokul")) {
                extraKeywords += " sınav vize final bütünleme ders programı müfredat";
            }

            const intents = item.action_links ? item.action_links.map(l => l.intent).join(" ") : "";
            const subs = item.sub_branches ? item.sub_branches.join(" ") : "";
            
            // extraKeywords'ü görünmez arama metnine (search_text) gömüyoruz!
            item.search_text = `${item.search_alias} ${item.entity_name} ${intents} ${subs} ${item.description || ""} ${extraKeywords}`.toLowerCase();
        });
    }

    function buildMasterFuse(data) {
        prepareMasterData(data);
        fuseInstance = new Fuse(data, {
            includeScore: true, threshold: 0.38, ignoreLocation: true, useExtendedSearch: true, // 🚀 0.25'İ 0.38 YAPTIK! Kapıyı VIP'ler geçebilsin diye biraz araladık.
            keys: [{ name: 'search_alias', weight: 5.0 }, { name: 'entity_name', weight: 3.0 }, { name: 'description', weight: 2.0 }, { name: 'search_text', weight: 1.0 }]
        });
    }

    function buildAnnouncementsFuse(data) {
        const flatAnnouncements = [];
        const now = new Date();
        data.forEach(group => {
            (group.items || []).forEach(item => {
                let isNew = false;
                try {
                    const parts = item.date.split(' ')[0].split('.');
                    const d = new Date(parts[2], parts[1] - 1, parts[0]);
                    isNew = (now - d) / (1000 * 60 * 60 * 24) <= 7;
                } catch (e) { }
                item.isNew = isNew;

                flatAnnouncements.push({
                    title: item.title, link: item.link, source: item.source || group.entity, entity: group.entity,
                    isNew: isNew,
                    search_text: `${item.title} ${item.source || group.entity}`.toLowerCase()
                });
            });
        });
        fuseAnnouncements = new Fuse(flatAnnouncements, {
            includeScore: true, includeMatches: true, threshold: 0.4, ignoreLocation: true, ignoreFieldNorm: true, useExtendedSearch: true,
            keys: [
                { name: 'title', weight: 0.7 },
                { name: 'entity', weight: 0.3 },
                { name: 'source', weight: 0.3 }
            ]
        });
    }

    async function initData() {
        const input = document.getElementById('h-input');
        const cacheKey = 'hubul_master_data';
        const annCacheKey = 'hubul_ann_data';
        const cacheTimeKey = 'hubul_last_fetch';

        const cachedMaster = localStorage.getItem(cacheKey);
        const cachedAnn = localStorage.getItem(annCacheKey);
        const now = new Date().getTime();
        const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

        if (cachedMaster && !isLocal) {
            masterData = JSON.parse(cachedMaster);
            input.placeholder = "Ne arıyorsun? (Örn: oidb, erasmus)";
            showFiller(); // Cache var, anında göster!
        } else {
            showFiller(true);
        }
        if (cachedAnn && !isLocal) {
            currentAnnouncements = JSON.parse(cachedAnn);
        }

        async function refreshData() {
            try {
                const lastFetch = localStorage.getItem(cacheTimeKey);
                const cacheBuster = '?v=' + now;

                let fetchPromises = [];
                let isMasterFetching = false;

                if (!lastFetch || (now - parseInt(lastFetch)) > 2 * 60 * 60 * 1000 || isLocal) {
                    fetchPromises.push(fetch(CONFIG.masterDataUrl + cacheBuster).then(res => res.json()));
                    isMasterFetching = true;
                } else {
                    fetchPromises.push(Promise.resolve(null));
                }

                fetchPromises.push(fetch(CONFIG.announcementsUrl + cacheBuster).then(res => res.json()));

                const [newMaster, newAnn] = await Promise.all(fetchPromises);

                if (isMasterFetching && newMaster && (!masterData || JSON.stringify(newMaster) !== JSON.stringify(masterData))) {
                    masterData = newMaster;
                    localStorage.setItem(cacheKey, JSON.stringify(newMaster));
                    localStorage.setItem(cacheTimeKey, now.toString());
                    buildMasterFuse(masterData);
                }

                if (newAnn && (!currentAnnouncements || JSON.stringify(newAnn) !== JSON.stringify(currentAnnouncements))) {
                    currentAnnouncements = newAnn;
                    localStorage.setItem(annCacheKey, JSON.stringify(newAnn));
                    buildAnnouncementsFuse(newAnn);
                }

            } catch (e) { console.error("Veri güncellenemedi:", e); }
        }

        if (!cachedMaster || isLocal) {
            await refreshData();
            input.placeholder = "Ne arıyorsun? (Örn: oidb, erasmus)";
            if (!input.value.trim()) showFiller(false);
        } else {
            refreshData();
        }

        buildAnnouncementsFuse(currentAnnouncements);
        buildMasterFuse(masterData);
    }

    // 🧠 TÜRKÇE KARAKTER NORMALİZATÖRÜ (ASCII FOLDING)
    const normalizeTR = (text) => {
        if (!text) return "";
        return text.toLowerCase()
            .replace(/ğ/g, 'g').replace(/ü/g, 'u').replace(/ş/g, 's')
            .replace(/ı/g, 'i').replace(/ö/g, 'o').replace(/ç/g, 'c');
    };

    function handleSearch(val) {
        const query = val.trim().toLocaleLowerCase('tr-TR');
        if (query.length < 2) {
            showFiller();
            return;
        }

        let searchTerms = query.split(/\s+/);

        const entitySearchResults = fuseInstance.search(query);

        let entityResults = entitySearchResults.map(r => ({
            item: r.item,
            score: r.score,
            matchedIntents: r.item.action_links
                ? r.item.action_links.filter(l => searchTerms.some(t => l.intent.toLocaleLowerCase('tr-TR').includes(t))).map(l => l.intent)
                : []
        }));

        // 🚀 ZEKİ KAVRAMA, HİYERARŞİ VE TÜRKÇE SONEK KANUNU (V4)
        let exactQuery = normalizeTR(query).trim();

        // 🚀 KAMPÜS ARGOSU ÇEVİRMENİ (Token-Based Query Rewriter)
        const jargonMap = {
            "cge": "cocuk gelisimi", "iibf": "iktisadi ve idari", "shmyo": "saglik hizmetleri meslek",
            "mediko": "saglik kultur", "bilsis": "bilgi islem", "akad": "akademik takvim",
            "oidb": "ogrenci isleri", "obs": "ogrenci bilgi", "agno": "agirlikli genel not",
            "cap": "cift anadal", "dis": "dis hekimligi", "ebe": "ebelik", "hem": "hemsirelik",
            "kyk": "yurt", "bim": "bilgi islem", "sksdb": "saglik kultur spor",
            "fen": "fen fakultesi", "tip": "tip fakultesi"
        };

        // Kullanıcının "cge sınav" sorgusunu anında "cocuk gelisimi sinav"a çevirir
        const rewrittenTerms = exactQuery.split(/\s+/).map(token => jargonMap[token] || token);
        exactQuery = rewrittenTerms.join(" ");
        const meaningfulSearchTerms = exactQuery.split(/\s+/).filter(t => t.length > 2); 

        entityResults.forEach(r => {
            // Kurum isimlerini ve SEO'ları da normalize et (Örn: "Çocuk Gelişimi" -> "cocuk gelisimi")
            const eName = normalizeTR(r.item.entity_name);
            const eAlias = normalizeTR(r.item.search_alias);
            const sText = normalizeTR(r.item.search_text);

            const hasExactIntentMatch = r.item.action_links && r.item.action_links.some(l =>
                l.intent && new RegExp(`\\b${exactQuery}\\b`).test(normalizeTR(l.intent))
            );
            const hasSeoMatch = new RegExp(`\\b${exactQuery}\\b`).test(sText);
            const hasAllTerms = meaningfulSearchTerms.every(term => sText.includes(term));
            const hasNamePartial = meaningfulSearchTerms.some(term => new RegExp(`\\b${term}\\b`).test(eName));
            // Aranan kelimelerden herhangi biri SEO'da veya Subdomain'de (search_text) BİREBİR geçiyor mu?
            const hasSubdomainOrSeoMatch = meaningfulSearchTerms.some(term => new RegExp(`\\b${term}\\b`).test(sText));

            let newScore = r.score;

            // KAVRAMSAL YÖNLENDİRME
            const isErasmusQuery = exactQuery.includes("erasmus") || exactQuery.includes("yurtdışı") || exactQuery.includes("değişim");
            const isEUOffice = eName.includes("ab ofisi") || eName.includes("european") || eName.includes("dış ilişkiler") || eAlias === "erasmus";

            if (isErasmusQuery && isEUOffice) {
                newScore = 0.000000001; 
            }
            // 1. Mutlak Kral
            else if (eName === exactQuery || eName === `${exactQuery} bolumu` || eName === `${exactQuery} muhendisligi`) {
                newScore = 0.00000001;
            }
            // 2. Başlangıç Tutması (Hiyerarşili)
            else if (eName.startsWith(`${exactQuery} `) || eName === exactQuery) {
                if (eName.includes("bolumu") || eName.includes("fakultesi")) newScore = 0.0000001;
                else if (eName.includes("merkez") || eName.includes("uam")) newScore = 0.0000009;
                else newScore = 0.0000005;
            }
            // 🚀 2.5 ÖZ İSİM KRALLIĞI (SBF'yi ezen kural)
            else if (meaningfulSearchTerms.filter(term => eName.includes(term)).length >= 2) {
                // Eğer bölüm veya fakülteyse, dağınık SEO'ları (0.005) ezip geçecek bir skor ver!
                if (eName.includes("bolumu") || eName.includes("fakultesi")) newScore = 0.0000002;
                else newScore = 0.0000008;
            }
            // 3. İsim İçinde Tam Geçiş
            else if (new RegExp(`\\b${exactQuery}\\b`).test(eName)) {
                if (eName.includes("bolumu") || eName.includes("fakultesi")) newScore = 0.000001;
                else newScore = 0.000005;
            }
            // 4. Alias / Çip / SEO Tam Eşleşmesi
            else if (eAlias === exactQuery || hasExactIntentMatch || hasSeoMatch) {
                newScore = 0.001;
            }
            // 5. AND MANTIĞI (Tüm kelimeler bir yerlerde geçiyor)
            else if (hasAllTerms) {
                newScore = 0.005;
            }
            // 🚀 6. KISMİ EŞLEŞME VEYA SUBDOMAIN KALKANI (İşte Çocuk Gelişimini ölümden kurtaran kural!)
            // İsminde veya Subdomain'inde (cge gibi) kelimenin BİRİ bile geçiyorsa bu kartı ipten al!
            else if (hasNamePartial || hasSubdomainOrSeoMatch) {
                if (eName.includes("bolumu") || eName.includes("fakultesi")) newScore = 0.01;
                else newScore = 0.05; 
            }
            // 6. ÇÖP VE ANABİLİM/MERKEZ KATİLİ
            else {
                // 🚀 KESİN İNFAZ: Eğer hiçbir kuralımızla eşleşmediyse (zattiri zottu gibi), 
                // Fuse.js'in harf benzerliği avansına güvenme! Skoru 1.0 (ÇÖP) yap.
                newScore = 1.0; 
            }

            // PRİO İSYANI: JSON'dan gelen emeği (priority_score) ekle
            const prioBonus = (r.item.priority_score || 0) * 0.0000000001;
            r.score = newScore - prioBonus;
        });

        // Skorları ZORLA yeniden sırala
        entityResults.sort((a, b) => a.score - b.score);

        // 🚀 YENİ ÇÖP ÖĞÜTÜCÜ: +5 gibi saçma diktatör cezalar yerine, sadece Fuse.js'in matematiksel olarak kötü bulduğu (0.4 ve üstü) şeyleri gizle!
        entityResults = entityResults.filter(r => r.score < 0.4);

        // RING KARTI İÇİN KESKİN NİŞANCI KALKANI (Spring, Engineering Tıkacı)
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



        // 🚀 KÜRESEL DUYURU ARAMA MOTORU (TOKEN-BASED & TYPO TOLERANT)
        let annResults = [];

        if (meaningfulSearchTerms.length > 0) {
            let flatAnnouncements = [];
            currentAnnouncements.forEach(group => {
                (group.items || []).forEach(item => {
                    flatAnnouncements.push({
                        title: item.title,
                        link: item.link,
                        source: item.source || group.entity,
                        entity: group.entity
                    });
                });
            });

            let customAnnResults = flatAnnouncements.map(ann => {
                const titleNorm = normalizeTR(ann.title || "");
                const eNameNorm = normalizeTR(ann.entity || ann.source || "");
                const combinedText = `${titleNorm} ${eNameNorm}`;

                let matchCount = 0;
                meaningfulSearchTerms.forEach(term => {
                    if (combinedText.includes(term)) matchCount += 1;
                    else if (term.length >= 4 && combinedText.includes(term.substring(0, 4))) matchCount += 0.8;
                });

                // 🚀 ÇARPIM SKORU MANTIĞI
                // Kurum adında eşleşme varsa 1.5x çarpan ver, yoksa 1.0 (Etkisiz)
                const entityMatchScore = meaningfulSearchTerms.some(t => eNameNorm.includes(t)) ? 1.5 : 1.0;
                
                // Başlıktaki kelime eşleşme sayısı
                const titleMatchScore = meaningfulSearchTerms.filter(t => titleNorm.includes(t)).length;

                // Skor ne kadar düşükse o kadar iyi. Kurum uyuşuyorsa skor çok daha hızlı düşer (iyileşir)
                let score = 1.0 - (titleMatchScore * 0.3 * entityMatchScore) - (matchCount * 0.1);

                return { ann: ann, score: score, matchCount: matchCount };
            });

            // Sadece aranan kelimelerden en az biriyle (veya typosuyla) eşleşen duyuruları tut
            customAnnResults = customAnnResults.filter(r => r.matchCount > 0.5);

            // En iyi skora göre sırala
            customAnnResults.sort((a, b) => a.score - b.score);

            // En iyi 2 duyuruyu al
            annResults = customAnnResults.slice(0, 2);
        }

        render(entityResults.slice(0, 5), annResults);
    }

    function render(entityResults, annResults = [], isFiller = false, hasHistory = false) {
        const cont = document.getElementById('h-results');

        // 1. Durum: Hiç sonuç yoksa
        if (entityResults.length === 0 && annResults.length === 0) {
            cont.innerHTML = `
                <div class="h-empty">
                    <p style="margin-bottom: 12px;">Sonuç bulunamadı.</p>
                    <button onclick="window.hubul_report(this)" class="h-suggest-btn">Aradığını bulamadın mı? Bize bildir</button>
                </div>
            `;
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
            const firstResult = entityResults[0];
            const item = firstResult.item;
            const matchedIntents = firstResult.matchedIntents || [];

            const cardClass = isFiller ? "h-result-card" : "h-result-card h-exact-card";
            let cardHtml = `
                <div class="${cardClass}" onclick="if(event.target.tagName !== 'A') { window.open('${item.url}','_blank'); hubul_save('${item.entity_name}'); }">
                    <div class="h-category-pill">${item.category || "Birim"}</div>
                    <h3 class="h-entity-title">${item.entity_name}</h3>
            `;

            const ann = currentAnnouncements.find(a => a.entity === item.entity_name);
            if (ann && ann.items && ann.items.length > 0) {
                cardHtml += `<div class="h-announcement"><span class="h-ann-tag">Yeni</span><a href="${ann.items[0].link}" target="_blank" onclick="event.stopPropagation();">${ann.items[0].title}</a></div>`;
            }

            if (item.action_links && item.action_links.length > 0) {
                cardHtml += '<div class="h-chips">';

                // 🚀 ZEKİ SIRALAMA VE ZERO-STATE (BOŞ EKRAN) MANTIĞI
                const searchVal = normalizeTR(document.getElementById('h-input').value.trim());
                let sortedLinks = [...item.action_links];

                if (searchVal.length > 2) {
                    // 1. Durum: Kullanıcı arama yaptıysa, yazdığı kelimeye uyan butonları öne çek!
                    sortedLinks.sort((a, b) => {
                        const aMatch = normalizeTR(a.intent).includes(searchVal) || a.url.toLowerCase().includes(searchVal) ? 1 : 0;
                        const bMatch = normalizeTR(b.intent).includes(searchVal) || b.url.toLowerCase().includes(searchVal) ? 1 : 0;
                        return bMatch - aMatch; 
                    });
                } else {
                    // 2. Durum: BOŞ EKRAN (Zero-State). Kullanıcı hiçbir şey yazmadı.
                    // En çok tıklanan ve can alıcı butonları (Yeni Kazanan, Menü, Takvim) zorla öne çek!
                    const hotTopics = ["yeni kazanan", "aday", "akademik takvim", "yemek", "menü", "öğrenci bilgi", "bilsis", "iletişim"];
                    sortedLinks.sort((a, b) => {
                        const aHot = hotTopics.some(ht => a.intent.toLowerCase().includes(ht)) ? 1 : 0;
                        const bHot = hotTopics.some(ht => b.intent.toLowerCase().includes(ht)) ? 1 : 0;
                        return bHot - aHot;
                    });
                }

                // Şimdi güvenle ilk 3'ü alabiliriz, çünkü önemli olanlar artık en önde!
                sortedLinks.slice(0, 3).forEach(l => {
                    const isHighlight = searchVal.length > 2 && normalizeTR(l.intent).includes(searchVal);
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
                html += '<div class="h-divider"></div>';
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

                    // 🚀 ZEKİ SIRALAMA VE ZERO-STATE (BOŞ EKRAN) MANTIĞI
                    const searchVal = normalizeTR(document.getElementById('h-input').value.trim());
                    let sortedLinks = [...item.action_links];

                    if (searchVal.length > 2) {
                        // 1. Durum: Kullanıcı arama yaptıysa, yazdığı kelimeye uyan butonları öne çek!
                        sortedLinks.sort((a, b) => {
                            const aMatch = normalizeTR(a.intent).includes(searchVal) || a.url.toLowerCase().includes(searchVal) ? 1 : 0;
                            const bMatch = normalizeTR(b.intent).includes(searchVal) || b.url.toLowerCase().includes(searchVal) ? 1 : 0;
                            return bMatch - aMatch; 
                        });
                    } else {
                        // 2. Durum: BOŞ EKRAN (Zero-State). Kullanıcı hiçbir şey yazmadı.
                        const hotTopics = ["yeni kazanan", "aday", "akademik takvim", "yemek", "menü", "öğrenci bilgi", "bilsis", "iletişim"];
                        sortedLinks.sort((a, b) => {
                            const aHot = hotTopics.some(ht => a.intent.toLowerCase().includes(ht)) ? 1 : 0;
                            const bHot = hotTopics.some(ht => b.intent.toLowerCase().includes(ht)) ? 1 : 0;
                            return bHot - aHot;
                        });
                    }

                    sortedLinks.slice(0, 3).forEach(l => {
                        const isHighlight = searchVal.length > 2 && normalizeTR(l.intent).includes(searchVal);
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

        // 2. Durum: Sonuçlar listelendi, en alta zarif bir buton koyalım
        if (!isFiller) {
            html += `
                <div style="text-align: center; margin-top: 15px; padding-bottom: 10px;">
                    <button onclick="window.hubul_report(this)" style="background:none; border:none; color:var(--h-text-muted); font-size:12px; cursor:pointer; text-decoration:underline; transition:0.2s;" onmouseover="this.style.color='var(--h-primary)'" onmouseout="this.style.color='var(--h-text-muted)'">
                        Aradığını bulamadın mı? Bize bildir.
                    </button>
                </div>
            `;
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

        let priorityAnns = [];
        
        // 🚀 1. DUYURU FİLTRESİ: Sadece "Baba" kurumların duyuruları anasayfada çıksın
        const vipAnnSources = ["öğrenci işleri", "sağlık, kültür", "hacettepe üniversitesi", "öidb", "sksdb", "rektörlük"];

        currentAnnouncements.forEach(group => {
            const eName = (group.entity || "").toLowerCase();
            const isVipSource = vipAnnSources.some(vip => eName.includes(vip));

            // Eğer kurum VIP listedeyse ve duyurusu "Yeni" ise ana sayfaya al!
            if (isVipSource) {
                let matchCount = 0;
                (group.items || []).forEach(it => {
                    if (matchCount < 4 && (it.isNew || isTitleMatchingSearch(it.title))) {
                        priorityAnns.push({ ann: { ...it, source: group.entity, entity: group.entity }, score: 100 });
                        matchCount++;
                    }
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
            // 🚀 2. VIP 3'LÜ KART (İlk açılışta öğrenciyi vuracak altın vuruş)
            const vips = [];
            
            // 1 numara: Ana Sayfa
            const mainPage = masterData.find(m => m.entity_name === "Hacettepe Üniversitesi");
            if (mainPage) vips.push(mainPage);
            
            // 2 numara: Yemekhane
            const sks = masterData.find(m => m.entity_name.toLowerCase().includes("sağlık, kültür ve spor"));
            if (sks) vips.push(sks);

            // 3 numara: Öğrenci İşleri
            const oidb = masterData.find(m => m.entity_name.toLowerCase().includes("öğrenci işleri"));
            if (oidb) vips.push(oidb);

            vips.forEach(v => {
                if (!items.find(i => i.item.entity_name === v.entity_name) && items.length < 3) {
                    items.push({ item: v, score: 1, matchedIntents: [] });
                }
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

    window.hubul_report = async (btnElement) => {
        const query = document.getElementById('h-input').value.trim();
        if (!query) return;

        // Tıklanan butonu bul ve görsel geri bildirim ver (Spam'i engelle)
        const btn = btnElement || event.target;
        const oldText = btn.innerText;
        btn.innerText = "İletiliyor...";
        btn.style.pointerEvents = "none";

        try {
            // 🚀 SUPABASE BİLGİLERİ (Proje devredileceği için sadece 'anon' key kullanıyoruz)
            const SUPABASE_URL = "https://ksishnnumgdmouinmsfq.supabase.co"; 
            const SUPABASE_ANON_KEY = "sb_publishable_3x7pu1oykynlDVb1-f6OgQ_ySyzqUry";

            // Supabase REST API'sine doğrudan güvenli POST isteği
            const response = await fetch(`${SUPABASE_URL}/rest/v1/search_logs`, {
                method: 'POST',
                headers: {
                    'apikey': SUPABASE_ANON_KEY,
                    'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal' // Sunucuyu yormamak için başarılıysa boş dön dedik
                },
                body: JSON.stringify({
                    query: query
                    // created_at tarihini Supabase otomatik ekleyecek
                })
            });

            if (!response.ok) throw new Error("Supabase API Hatası");

            btn.innerText = "Teşekkürler! İncelenmek üzere iletildi.";
            btn.style.color = "var(--h-primary)";
            
            // 3 saniye sonra butonu eski haline getir
            setTimeout(() => { 
                btn.innerText = oldText; 
                btn.style.color = "";
                btn.style.pointerEvents = "all"; 
            }, 3000);

        } catch (e) {
            console.error("Log gönderilemedi:", e);
            btn.innerText = "Bağlantı hatası!";
            setTimeout(() => { 
                btn.innerText = oldText; 
                btn.style.pointerEvents = "all"; 
            }, 3000);
        }
    };

    window.hubul_clear_history = () => {
        localStorage.removeItem('hubul_history');
        showFiller();
    };

    // 📱 MOBİL KLAVYE UYUMU (Visual Viewport API)
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', () => {
            const panel = document.getElementById('hubul-panel');
            if (panel && panel.classList.contains('h-panel-active')) {
                // Ekranın toplam boyundan, klavye açıldıktan sonraki boyunu çıkarıyoruz
                const keyboardHeight = window.innerHeight - window.visualViewport.height;

                if (keyboardHeight > 50) {
                    // KLAVYE AÇIK: Paneli klavyenin hemen üstüne (10px boşlukla) sabitle ve boyunu kısalt
                    panel.style.bottom = (keyboardHeight + 10) + 'px';
                    panel.style.maxHeight = (window.visualViewport.height - 20) + 'px';
                } else {
                    // KLAVYE KAPALI: Orijinal yerine (mobildeyse 85px, webde 100px) geri dön
                    const isMobile = window.innerWidth <= 480;
                    panel.style.bottom = isMobile ? '85px' : '100px';
                    panel.style.maxHeight = 'calc(100dvh - 120px)';
                }
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inject);
    } else {
        inject();
    }
})();
