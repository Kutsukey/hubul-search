/**
 * Hubul | Hacettepe Akıllı Asistan Widget v4.1
 * Düzeltmeler:
 *  1. description alanı search_text'e eklendi → "akademik takvim" artık bulunuyor
 *  2. Arama yapılan intent otomatik highlight → "ders programı" yazınca ilgili chip mor yanıyor
 *  3. Duyurular ayrı Fuse indeksinde → "erasmus sonuçları" gibi sorgular duyuru kartı döndürüyor
 */

(function () {
    const CONFIG = {
        masterDataUrl: 'outputs/hybrid_master.json',
        announcementsUrl: 'outputs/announcements_live.json',
        corporatePurple: '#4f46e5',
        corporatePurpleHover: '#4338ca'
    };

    let masterData = [];
    let currentAnnouncements = [];
    let fuseInstance = null;
    let fuseAnnouncements = null; // YENİ: duyuru fuse indeksi
    const commonIntents = ["akademik takvim", "staj başvurusu", "yemekhane menüsü", "vpn kurulumu", "ders programı", "öğrenci işleri"];

    const styles = `
        :root {
            --h-bg-color: #f9fafb;
            --h-card-bg: #ffffff;
            --h-text-main: #111827;
            --h-text-muted: #6b7280;
            --h-purple: ${CONFIG.corporatePurple};
            --h-purple-hover: ${CONFIG.corporatePurpleHover};
            --h-tag-bg: #e0e7ff;
            --h-tag-text: #3730a3;
            --h-border: #e5e7eb;
        }

        #hubul-fab {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            background-color: var(--h-purple);
            color: white;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 28px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 999999;
            user-select: none;
        }

        #hubul-fab:hover {
            transform: scale(1.05) rotate(5deg);
            box-shadow: 0 6px 16px rgba(79, 70, 229, 0.6);
        }

        #hubul-panel {
            position: fixed;
            bottom: 100px;
            right: 30px;
            width: 400px;
            height: 600px;
            max-height: calc(100vh - 140px);
            background: var(--h-bg-color);
            border-radius: 20px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transform: translateY(30px) scale(0.95);
            opacity: 0;
            pointer-events: none;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.1);
            z-index: 999998;
            border: 1px solid var(--h-border);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        #hubul-panel.active {
            transform: translateY(0) scale(1);
            opacity: 1;
            pointer-events: auto;
        }

        .h-header {
            background: var(--h-purple);
            color: white;
            padding: 18px 20px;
            font-weight: 700;
            font-size: 17px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            letter-spacing: -0.5px;
        }

        .h-close {
            cursor: pointer;
            font-size: 24px;
            line-height: 1;
            opacity: 0.8;
            transition: opacity 0.2s;
        }
        .h-close:hover { opacity: 1; }

        .h-search-area {
            padding: 20px;
            background: white;
            border-bottom: 1px solid var(--h-border);
        }

        #h-input {
            width: 100%;
            padding: 14px 18px;
            font-size: 16px;
            border: 1px solid var(--h-border);
            border-radius: 12px;
            outline: none;
            box-sizing: border-box;
            transition: all 0.2s;
            font-family: inherit;
            background: #fdfdfd;
        }

        #h-input:focus {
            border-color: var(--h-purple);
            box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.1);
            background: white;
        }

        #h-suggestion {
            padding: 0 20px;
            margin-top: 10px;
            display: none;
            align-items: center;
            gap: 8px;
            overflow-x: auto;
            scrollbar-width: none;
        }
        #h-suggestion::-webkit-scrollbar { display: none; }

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
        .h-suggest-btn:hover { border-color: var(--h-purple); color: var(--h-purple); background: #f5f3ff; }

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

        /* YENİ: Duyuru kartı stili - entity kartlarından görsel olarak ayrışıyor */
        .h-result-card.h-ann-card {
            border-left: 3px solid var(--h-purple);
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
        .h-ann-title:hover { color: var(--h-purple); text-decoration: underline; }

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
            background: var(--h-tag-bg);
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 14px;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .h-ann-tag {
            background: var(--h-tag-text);
            color: #fff;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            flex-shrink: 0;
        }
        .h-announcement a { color: var(--h-tag-text); font-weight: 600; text-decoration: none; }

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
        .h-chip:hover { border-color: var(--h-purple); color: var(--h-purple); background: #f5f3ff; }
        /* DÜZELTME 2: highlight class artık doğru çalışıyor */
        .h-chip.highlight { background: var(--h-purple); color: white; border-color: var(--h-purple); }
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

        /* 🚌 CANLI RING ZAMANLAYICI STILLERI */
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
            #hubul-panel { width: calc(100vw - 40px); right: 20px; bottom: 90px; }
            #hubul-fab { bottom: 20px; right: 20px; }
        }
    `;

    const html = `
        <div id="hubul-fab" title="Hacettepe Akıllı Asistan">🔍</div>
        <div id="hubul-panel">
            <div class="h-header">
                <span>Hacettepe Akıllı Asistan</span>
                <span class="h-close" id="h-close">&times;</span>
            </div>
            <div class="h-search-area">
                <input type="text" id="h-input" placeholder="Yükleniyor..." autocomplete="off">
            </div>
            <div id="h-suggestion"></div>
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

        fab.onclick = () => {
            const isActive = panel.classList.toggle('active');
            if (isActive) {
                setTimeout(() => input.focus(), 400);
            }
        };

        close.onclick = () => {
            panel.classList.remove('active');
        };

        input.oninput = (e) => handleSearch(e.target.value);

        loadFuse(() => initData());
    }

    function getSubdomain(url) {
        if (!url) return "";
        return url.replace('https://', '').replace('http://', '').replace('www.', '').split('.')[0].toLowerCase();
    }

    // 🚦 Ring seferi var mı kontrol et (gece yarısı 00:00-06:00 arası dahil)
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

        // Aktif sefer var mı kontrol et
        for (let time of times) {
            let parts = time.split(':');
            let busMins = parseInt(parts[0]) * 60 + parseInt(parts[1]);
            let busHour = parseInt(parts[0]);

            // Gündüz saatlerinde gece yarısı seferlerini atla
            if (currentMins >= 360 && busHour < 3) continue;

            if (busMins >= currentMins) {
                nextMins = busMins - currentMins;
                break;
            }
        }

        // Gece yarısı (00:00-06:00) ilk sabah seferini kontrol et
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
        try {
            const res = await fetch(CONFIG.masterDataUrl);
            masterData = await res.json();

            // MEGA İNDEKS OLUŞTURMA
            masterData.forEach(item => {
                if (!item.search_alias && item.url) {
                    item.search_alias = getSubdomain(item.url);
                }
                const intents = item.action_links ? item.action_links.map(l => l.intent).join(" ") : "";
                const subs = item.sub_branches ? item.sub_branches.join(" ") : "";

                // 💉 FRONTEND SEO ENJEKSİYONU: Backend'i beklemeden gizli kelimeleri JS içinde çakıyoruz
                let extraKeywords = "";
                const nl = item.entity_name.toLocaleLowerCase('tr-TR');
                const isAcademic = nl.includes("bölümü") || nl.includes("fakültesi") || nl.includes("ana bilim") || nl.includes("enstitü");

                if (nl.includes("öğrenci") && nl.includes("işleri")) extraKeywords = "akademik takvim harç ödeme kayıt otomasyon transkript mezuniyet belge bilsis diploma";
                if (nl.includes("sağlık") && nl.includes("kültür")) extraKeywords = "yemekhane menü yemek yurt barınma kyk sks";
                if (nl.includes("bilgi işlem")) extraKeywords = "eduroam vpn wifi internet e-posta şifre şifremi unuttum";
                if (nl.includes("idari") && nl.includes("işler")) extraKeywords = "ring servis otobüs ulaşım saatleri";
                const isEU = nl.includes("dış ilişkiler") || nl.includes("uluslararası") || nl.includes("ab ofisi") || nl.includes("european") || nl.includes("avrupa") || nl.includes("erasmus");
                if (!isAcademic && isEU) extraKeywords = "erasmus yurtdışı değişim mevlana farabi";

                item.search_text = `${item.search_alias} ${item.entity_name} ${intents} ${subs} ${item.description || ""} ${extraKeywords}`.toLowerCase();
            });

            try {
                const annRes = await fetch(CONFIG.announcementsUrl);
                if (annRes.ok) {
                    currentAnnouncements = await annRes.json();
                    // DÜZELTME 3: Duyuruları düzleştirip ayrı Fuse indeksi oluştur
                    const flatAnnouncements = [];
                    currentAnnouncements.forEach(group => {
                        const groupEntityLower = group.entity.toLowerCase();
                        // 💉 DUYURU SEO ENJEKSİYONU: Entity adına göre gizli anahtar kelimeler ekliyoruz
                        let extraAnnKeywords = "";
                        const isEUGroup = groupEntityLower.includes("european") || groupEntityLower.includes("ab ofis") || groupEntityLower.includes("dış ilişkiler") || groupEntityLower.includes("uluslararası") || groupEntityLower.includes("avrupa");
                        if (isEUGroup) extraAnnKeywords = "erasmus değişim yurtdışı yurtdisi farabi mevlana staj hareketlilik";
                        if (groupEntityLower.includes("sağlık") && groupEntityLower.includes("kültür")) extraAnnKeywords = "yemekhane menü yurt barınma sks";
                        if (groupEntityLower.includes("öğrenci") && groupEntityLower.includes("işleri")) extraAnnKeywords = "akademik takvim harç kayıt transkript mezuniyet";

                        (group.items || []).forEach(item => {
                            flatAnnouncements.push({
                                title: item.title,
                                link: item.link,
                                source: item.source || group.entity,
                                entity: group.entity,
                                description: item.description || "",
                                search_text: `${item.title} ${item.source || group.entity} ${item.description || ""} ${extraAnnKeywords}`.toLowerCase()
                            });
                        });
                    });
                    fuseAnnouncements = new Fuse(flatAnnouncements, {
                        includeScore: true,
                        includeMatches: true, // 🚀 SİHİRLİ ÖZELLİK: Harflerin nerede eşleştiğini bize söyler
                        threshold: 0.45,
                        ignoreLocation: true,
                        ignoreFieldNorm: true, // Uzun duyuruları silmemesi için bu şart
                        keys: [
                            { name: 'title', weight: 3.0 },       // Başlıkta "Erasmus" geçerse → şampiyonluk skoru
                            { name: 'source', weight: 1.5 },       // Kaynak adı eşleşirse bonus
                            { name: 'description', weight: 1.2 }, // Duyuru gövdesinde "Erasmus" geçerse yakalanır
                            { name: 'search_text', weight: 1.0 }  // Enjekte edilen keyword'ler burada
                        ]
                    });
                }
            } catch (e) { }

            const fuseOptions = {
                includeScore: true,
                threshold: 0.45, // Kutuphne, aakademik takvm gibi yazım hataları için esnetildi
                ignoreLocation: true,
                useExtendedSearch: true,
                keys: [
                    { name: 'search_alias', weight: 5.0 },
                    { name: 'entity_name', weight: 3.0 },
                    { name: 'description', weight: 2.0 },
                    { name: 'search_text', weight: 1.0 }
                ]
            };
            fuseInstance = new Fuse(masterData, fuseOptions);

            input.placeholder = "Ne arıyorsun? (Örn: staj, oidb, akademik takvim)";
            showFiller();
        } catch (err) {
            input.placeholder = "Veri yüklenemedi.";
        }
    }

    function handleSearch(val) {
        const query = val.trim().toLocaleLowerCase('tr-TR');
        if (query.length < 2) {
            showFiller();
            return;
        }

        let searchTerms = query.split(/\s+/);
        
        // $and ÇOK KATIYDI, YERİNE ESNEK $or KULLANIYORUZ (ee yaz okulu hatasını çözer)
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

            // 🛡️ AKILLI MERKEZ KALKANI
            const isMerkez = nameLower.includes("merkezi") && (nameLower.includes("araştırma") || nameLower.includes("uygulama"));
            if (isMerkez) {
                // Merkez adındaki jenerik kelimeleri atıp anahtar kimliğini bul ("nüfus", "yuvam" gibi)
                const distinctWords = nameLower.replace(/araştırma|uygulama|ve|merkezi/g, '').trim().split(/\s+/).filter(w => w.length > 2);
                // Kullanıcı gerçekten bu merkezin spesifik adını mı aratmış?
                const userLookedForThis = searchTerms.some(term => distinctWords.some(dw => dw.includes(term) || term.includes(dw)));
                if (!userLookedForThis) return null; // Sadece "uygulama merkezi" yazıldıysa gizler, "nüfus" yazıldıysa gösterir
            }

            let score = (1 - fr.score) * 1000;
            score += (item.priority_score || 0);

            // 🚀 GOD MODE (Kısaltmalar ve Özel Durumlar)
            if (searchTerms.some(term => item.search_alias === term || item.search_alias === term + 'db' || item.search_alias + 'db' === term)) score += 10000;
            // Özel Alias'lar (ai aranınca Yapay Zeka gelmesi için)
            if (searchTerms.includes("ai") && nameLower.includes("yapay zeka")) score += 10000;

            // 👑 NİYET OKUYUCU (INTENT) MEGA BONUSLARI
            const isAcademic = nameLower.includes("bölümü") || nameLower.includes("fakültesi") || nameLower.includes("ana bilim") || nameLower.includes("enstitü");
            const isYurt = (query.includes("yurt") || query.includes("barınma") || query.includes("barinma")) && !query.includes("yurtdışı");

            // OİDB
            if (["takv", "akademik", "harç", "harc", "öde", "ode", "otomas", "transk", "mezun", "belge", "bilsis", "kayıt", "öğren", "ogren", "işler", "isler"].some(k => query.includes(k)) && nameLower.includes("öğrenci") && nameLower.includes("işleri")) score += 5000;

            // SKSDB (mennu gibi ağır yazım hataları için 'menn' eklendi)
            if ((isYurt || ["yemek", "ymek", "menü", "menu", "menn"].some(k => query.includes(k))) && nameLower.includes("sağlık") && nameLower.includes("kültür")) score += 5000;

            // Kütüphane
            if (["kütüphane", "kutuph"].some(k => query.includes(k)) && nameLower.includes("kütüphane")) score += 5000;

            // Bilgi İşlem (şifre ve unuttum eklendi)
            if (["eduroam", "vpn", "wifi", "internet", "şifre", "sifre", "unuttum"].some(k => query.includes(k)) && nameLower.includes("bilgi işlem")) score += 5000;

            // İdari İşler (Ring, Servis)
            const isRingSearch = ["ring", "servis", "otobus"].some(k => query.includes(k));
            const isIdariIsler = nameLower.includes("idari") && nameLower.includes("işler");
            if (isRingSearch && isIdariIsler) {
                // 🚦 Ring araması yapıldı ama seferler bitmişse gösterme
                if (!isRingActive()) return null;
                score += 5000;
            }

            // Dış İlişkiler / Erasmus (Kalkan Eklendi: Akademik bölümler bonus ALAMAZ)
            const isEU = nameLower.includes("dış ilişkiler") || nameLower.includes("uluslararası") || nameLower.includes("ab ofisi") || nameLower.includes("european") || nameLower.includes("avrupa") || nameLower.includes("erasmus");
            if (["erasmus", "yurtdışı", "yurtdisi", "değişim", "degisim", "mevlana", "farabi"].some(k => query.includes(k)) && !isAcademic && isEU) score += 5000;

            // Fakülte/Bölüm Adı Geçiyorsa Bonus (Hukuk yatay geçiş -> Hukuk Fakültesi'ni yukarı çeker)
            if (searchTerms.some(term => term.length > 3 && nameLower.includes(term))) score += 1000;

            const matchedIntents = item.action_links
                ? item.action_links.filter(l => searchTerms.some(t => l.intent.toLocaleLowerCase('tr-TR').includes(t))).map(l => l.intent)
                : [];

            return { item, score, matchedIntents };
        }).filter(res => res !== null); 

        entityResults.sort((a, b) => b.score - a.score);

        // 🎯 HİBRİT DUYURU MOTORU: Fuse.js (Yazım Hatası) + Jilet Kalkan (Harf Saçılması)
        let annResults = [];
        if (fuseAnnouncements) {
            const annSearchResults = fuseAnnouncements.search(query);
            
            // Eğer yazılan kelime 4 harften kısaysa tamamı, uzunsa en az 3 harfi YAN YANA eşleşmeli!
            const minSolidBlock = query.length < 4 ? query.length : 3;

            annResults = annSearchResults.filter(r => {
                const sourceLower = (r.item.source || "").toLowerCase();
                const isMerkezAnn = sourceLower.includes("merkezi") && (sourceLower.includes("araştırma") || sourceLower.includes("uygulama"));
                if (isMerkezAnn && r.score > 0.15) return false;
                if (r.score >= 0.45) return false; 
                
                // 🛡️ AMERİKAN KÜLTÜRÜ KALKANI (Scattered Letter Shield)
                // Fuse.js harfleri oradan buradan topladıysa çöpe atıyoruz.
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
                
                // Yan yana 3 harf bile eşleşmemişse, cümlenin içine saçılmış çöptür!
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
                    ${hasHistory ? `<button onclick="window.hubul_clear_history()" style="background:none; border:none; color:var(--h-text-muted); font-size:10px; cursor:pointer; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; transition:0.2s;" onmouseover="this.style.color='var(--h-purple)'" onmouseout="this.style.color='var(--h-text-muted)'">GEÇMİŞİ TEMİZLE</button>` : ''}
                </div>
            `;
        }

        // 📢 DUYURULAR (Filler modunda en üste, max 2 adet)
        if (isFiller && annResults.length > 0) {
            html += '<div class="h-section-label">📢 Duyurular</div>';
            annResults.slice(0, 2).forEach(r => {
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

        // TAM EŞLEŞME / ÖNERİLEN (İlk entity, 1 kart)
        if (entityResults.length > 0) {
            const firstLabel = isFiller ? 'Önerilen' : 'Tam Eşleşen';
            html += `<div class="h-section-label">${firstLabel}</div>`;
            const firstResult = entityResults[0];
            const item = firstResult.item;
            const matchedIntents = firstResult.matchedIntents || [];

            let cardHtml = `
                <div class="h-result-card" onclick="if(event.target.tagName !== 'A') { window.open('${item.url}','_blank'); hubul_save('${item.entity_name}'); }">
                    <div class="h-category-pill">${item.category || "Birim"}</div>
                    <h3 class="h-entity-title">${item.entity_name}</h3>
            `;

            // Entity'e ait duyuru - eşleşen duyuru yoksa entity-level göster
            const entityHasAnnInResults = annResults.some(a => a.ann.entity === item.entity_name);
            if (!entityHasAnnInResults) {
                const ann = currentAnnouncements.find(a => a.entity === item.entity_name);
                if (ann && ann.items && ann.items.length > 0) {
                    cardHtml += `<div class="h-announcement"><span class="h-ann-tag">Yeni</span><a href="${ann.items[0].link}" target="_blank" onclick="event.stopPropagation();">${ann.items[0].title}</a></div>`;
                }
            }

            if (item.action_links && item.action_links.length > 0) {
                cardHtml += '<div class="h-chips">';
                item.action_links.slice(0, 3).forEach(l => {
                    const isHighlight = matchedIntents.includes(l.intent);
                    const isJs = l.url.startsWith('javascript:');
                    cardHtml += `<a href="${l.url}" ${isJs ? '' : 'target="_blank"'} class="h-chip${isHighlight ? ' highlight' : ''}" onclick="event.stopPropagation(); hubul_save('${item.entity_name}');">
                        <span>${l.intent}</span>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
                    </a>`;
                });
                cardHtml += '</div>';
            }

            // 🚌 Ring kartı ise canlı zamanlayıcı
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

        // 📢 DUYURULAR (Arama sonrası, max 2 adet)
        if (!isFiller && annResults.length > 0) {
            html += '<div class="h-section-label" style="margin-top:8px;">📢 Duyurular</div>';
            annResults.slice(0, 2).forEach(r => {
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

        // DİĞER EŞLEŞENLER (Kalan entity'ler)
        if (entityResults.length > 1) {
            html += '<div class="h-section-label" style="margin-top:8px;">Diğer Sonuçlar</div>';
            html += entityResults.slice(1).map(r => {
                const item = r.item;
                const matchedIntents = r.matchedIntents || [];

                let cardHtml = `
                    <div class="h-result-card" onclick="if(event.target.tagName !== 'A') { window.open('${item.url}','_blank'); hubul_save('${item.entity_name}'); }">
                        <div class="h-category-pill">${item.category || "Birim"}</div>
                        <h3 class="h-entity-title">${item.entity_name}</h3>
                `;

                // Entity'e ait duyuru - eşleşen duyuru yoksa entity-level göster
                const entityHasAnnInResults = annResults.some(a => a.ann.entity === item.entity_name);
                if (!entityHasAnnInResults) {
                    const ann = currentAnnouncements.find(a => a.entity === item.entity_name);
                    if (ann && ann.items && ann.items.length > 0) {
                        cardHtml += `<div class="h-announcement"><span class="h-ann-tag">Yeni</span><a href="${ann.items[0].link}" target="_blank" onclick="event.stopPropagation();">${ann.items[0].title}</a></div>`;
                    }
                }

            if (item.action_links && item.action_links.length > 0) {
                cardHtml += '<div class="h-chips">';
                item.action_links.slice(0, 3).forEach(l => {
                    // DÜZELTME 2: intent sorguyla eşleşiyorsa highlight
                    const isHighlight = matchedIntents.includes(l.intent);
                    const isJs = l.url.startsWith('javascript:');
                    cardHtml += `<a href="${l.url}" ${isJs ? '' : 'target="_blank"'} class="h-chip${isHighlight ? ' highlight' : ''}" onclick="event.stopPropagation(); hubul_save('${item.entity_name}');">
                        <span>${l.intent}</span>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
                    </a>`;
                });
                cardHtml += '</div>';
            }

            // 🚌 EĞER BU KART RING KARTI İSE CANLI ZAMANLAYICIYI HESAPLA
            if (item.is_ring) {
                const now = new Date();
                const currentMins = now.getHours() * 60 + now.getMinutes();
                const day = now.getDay();
                const isWeekend = (day === 0 || day === 6); // 0: Pazar, 6: Cumartesi

                // 🚦 EGO 130 GERÇEK TARİFESİ (Sıkıştırılmış String Formatında)
                const egoHaftaIci = "00:10,00:40,01:25,06:35,06:40,06:45,06:50,06:55,07:00,07:03,07:06,07:09,07:12,07:15,07:18,07:21,07:24,07:27,07:30,07:33,07:36,07:39,07:42,07:45,07:48,07:51,07:54,07:57,08:00,08:03,08:06,08:09,08:12,08:15,08:18,08:21,08:24,08:27,08:30,08:33,08:36,08:39,08:42,08:45,08:48,08:51,08:54,08:57,09:00,09:03,09:06,09:09,09:12,09:15,09:18,09:21,09:24,09:27,09:30,09:33,09:36,09:39,09:42,09:45,09:48,09:51,09:54,09:57,10:00,10:08,10:14,10:20,10:26,10:32,10:38,10:44,10:50,10:56,11:02,11:08,11:14,11:20,11:26,11:32,11:38,11:44,11:50,11:56,12:02,12:08,12:11,12:14,12:17,12:20,12:23,12:26,12:29,12:32,12:35,12:38,12:41,12:44,12:47,12:50,12:53,12:56,12:59,13:02,13:05,13:08,13:11,13:14,13:17,13:20,13:23,13:26,13:29,13:32,13:35,13:38,13:41,13:44,13:47,13:50,13:53,13:56,13:59,14:02,14:05,14:08,14:11,14:14,14:17,14:20,14:23,14:26,14:29,14:32,14:35,14:38,14:41,14:44,14:47,14:50,14:53,14:56,14:59,15:02,15:05,15:08,15:11,15:14,15:17,15:20,15:23,15:26,15:29,15:32,15:35,15:38,15:41,15:44,15:47,15:50,15:53,15:56,15:59,16:02,16:05,16:08,16:11,16:14,16:17,16:20,16:23,16:26,16:29,16:32,16:35,16:38,16:41,16:44,16:47,16:50,16:53,16:56,17:00,17:05,17:10,17:15,17:20,17:25,17:30,17:35,17:40,17:45,17:50,17:55,18:00,18:05,18:10,18:15,18:20,18:25,18:30,18:35,18:40,18:45,18:50,18:55,19:00,19:05,19:10,19:15,19:20,19:25,19:30,19:38,19:46,19:54,20:02,20:10,20:18,20:26,20:34,20:42,20:50,20:58,21:06,21:14,21:22,21:30,21:38,21:46,21:54,22:02,22:10,22:18,22:26,22:34,22:42,22:50,22:58,23:06,23:14,23:22,23:30,23:40";
                const egoHaftaSonu = "00:10,00:40,01:25,06:35,06:45,06:50,07:05,07:15,07:20,07:35,07:45,07:50,08:05,08:20,08:25,08:30,08:40,08:50,09:00,09:10,09:20,09:30,09:40,09:50,10:00,10:10,10:20,10:30,10:40,10:50,11:00,11:10,11:20,11:30,11:40,11:50,12:00,12:10,12:20,12:30,12:40,12:50,13:00,13:10,13:20,13:30,13:40,13:50,14:00,14:10,14:20,14:30,14:40,14:50,15:00,15:10,15:20,15:30,15:40,15:50,16:00,16:10,16:20,16:30,16:40,16:50,17:00,17:10,17:20,17:30,17:40,17:50,18:00,18:10,18:20,18:30,18:40,18:50,19:00,19:10,19:20,19:30,19:40,19:50,20:00,20:10,20:20,20:30,20:40,20:50,21:00,21:10,21:20,21:30,21:40,21:50,22:00,22:10,22:20,22:30,22:40,22:50,23:00,23:10,23:20,23:30,23:40";

                const activeSchedule = isWeekend ? egoHaftaSonu : egoHaftaIci;
                const times = activeSchedule.split(',');

                let nextMins = -1;
                let foundTime = "";

                // 🕛 GECE YARISI ZEKASI v3.0 (Gündüz saatlerinde gece seferlerini atla)
                for (let time of times) {
                    let parts = time.split(':');
                    let busMins = parseInt(parts[0]) * 60 + parseInt(parts[1]);
                    let busHour = parseInt(parts[0]);

                    // Gündüz saatlerinde (06:00'dan sonra) gece yarısı seferlerini (00:00-02:00) atla
                    if (currentMins >= 360 && busHour < 3) {
                        continue; // Bu sefer gece yarısı, ama şu an gündüz - atla
                    }

                    if (busMins >= currentMins) {
                        nextMins = busMins - currentMins;
                        foundTime = time;
                        break;
                    }
                }

                // Eğer hiçbir sefer bulunamazsa ve gece yarısındaysak (00:00-06:00 arası)
                if (nextMins === -1 && currentMins < 360) {
                    // İlk seferi bul (yarın sabahki ilk sefer)
                    for (let time of times) {
                        let parts = time.split(':');
                        let busMins = parseInt(parts[0]) * 60 + parseInt(parts[1]);
                        let busHour = parseInt(parts[0]);

                        // Sabah seferlerini (06:35+) 'yarın' olarak hesapla
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

            cardHtml += `</div>`;
            return cardHtml;
        }).join('');
        }

        cont.innerHTML = html;
    }

    function showFiller() {
        const history = JSON.parse(localStorage.getItem('hubul_history') || '[]');
        let items = [];
        let hasHistory = false;

        // 1. ÖNCELİKLİ DUYURULAR (OİDB & SKSDB)
        const prioritySources = ["Öğrenci İşleri Daire Başkanlığı", "Sağlık, Kültür ve Spor Daire Başkanlığı"];
        let priorityAnns = [];
        currentAnnouncements.forEach(group => {
            if (prioritySources.includes(group.entity)) {
                (group.items || []).slice(0, 1).forEach(it => {
                    priorityAnns.push({
                        ann: { ...it, source: group.entity, entity: group.entity },
                        score: 1000
                    });
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
            const vips = masterData.filter(m => ["öidb", "yemekhane", "kütüphane"].some(k => m.entity_name.toLowerCase().includes(k)));
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
