/**
 * Hubul | Hacettepe Akıllı Asistan Widget v4.0 (Jilet Edition)
 */

(function() {
    const CONFIG = {
        masterDataUrl: 'outputs/hybrid_master.json',
        announcementsUrl: 'outputs/announcements_live.json',
        corporatePurple: '#4f46e5',
        corporatePurpleHover: '#4338ca'
    };

    let masterData = [];
    let currentAnnouncements = [];
    let fuseInstance = null; 
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
        .h-chip.highlight { background: var(--h-purple); color: white; border-color: var(--h-purple); }
        .h-chip svg { width: 14px; height: 14px; opacity: 0.6; }
        .h-chip.highlight svg { opacity: 1; }

        .h-empty { text-align: center; color: var(--h-text-muted); padding: 40px 20px; font-size: 14px; }
        
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
            panel.classList.add('active');
            fab.style.transform = 'scale(0)';
            setTimeout(() => input.focus(), 400);
        };

        close.onclick = () => {
            panel.classList.remove('active');
            fab.style.transform = 'scale(1)';
        };

        input.oninput = (e) => handleSearch(e.target.value);
        
        loadFuse(() => initData());
    }

    function getSubdomain(url) {
        if (!url) return "";
        return url.replace('https://', '').replace('http://', '').replace('www.', '').split('.')[0].toLowerCase();
    }

    async function initData() {
        const input = document.getElementById('h-input');
        try {
            const res = await fetch(CONFIG.masterDataUrl);
            masterData = await res.json();
            
            masterData.forEach(item => {
                if (!item.search_alias && item.url) {
                    item.search_alias = getSubdomain(item.url);
                }
            });

            try {
                const annRes = await fetch(CONFIG.announcementsUrl);
                if (annRes.ok) currentAnnouncements = await annRes.json();
            } catch(e) {}

            const options = {
                includeScore: true,
                threshold: 0.3,
                ignoreLocation: true,
                keys: [
                    { name: 'search_alias', weight: 5.0 },
                    { name: 'entity_name', weight: 2.0 },
                    { name: 'action_links.intent', weight: 0.5 }
                ]
            };
            fuseInstance = new Fuse(masterData, options);

            input.placeholder = "Ne arıyorsun? (Örn: staj)";
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

        const fuseResults = fuseInstance.search(query);

        let results = fuseResults.map(fr => {
            let item = fr.item;
            let score = (1 - fr.score) * 1000;
            score += (item.priority_score || 0);
            return { item, score };
        });

        results.sort((a, b) => b.score - a.score);
        render(results.slice(0, 6));
    }

    function render(results) {
        const cont = document.getElementById('h-results');
        if (results.length === 0) {
            cont.innerHTML = '<div class="h-empty">Sonuç bulunamadı.</div>';
            return;
        }

        cont.innerHTML = results.map(r => {
            const item = r.item;
            let html = `
                <div class="h-result-card" onclick="if(event.target.tagName !== 'A') { window.open('${item.url}','_blank'); hubul_save('${item.entity_name}'); }">
                    <div class="h-category-pill">${item.category || "Birim"}</div>
                    <h3 class="h-entity-title">${item.entity_name}</h3>
            `;

            const ann = currentAnnouncements.find(a => a.entity === item.entity_name);
            if (ann && ann.items && ann.items.length > 0) {
                html += `<div class="h-announcement"><span class="h-ann-tag">Yeni</span><a href="${ann.items[0].link}" target="_blank">${ann.items[0].title}</a></div>`;
            }

            if (item.action_links && item.action_links.length > 0) {
                html += '<div class="h-chips">';
                item.action_links.slice(0, 3).forEach(l => {
                    html += `<a href="${l.url}" target="_blank" class="h-chip" onclick="event.stopPropagation(); hubul_save('${item.entity_name}');">
                        <span>${l.intent}</span>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17l9.2-9.2M17 17V7H7"/></svg>
                    </a>`;
                });
                html += '</div>';
            }
            html += `</div>`;
            return html;
        }).join('');
    }

    function showFiller() {
        const history = JSON.parse(localStorage.getItem('hubul_history') || '[]');
        let items = [];
        if (history.length > 0) {
            history.forEach(n => {
                const found = masterData.find(m => m.entity_name === n);
                if (found) items.push({ item: found, score: 1 });
            });
        }
        if (items.length < 3) {
            const vips = masterData.filter(m => ["öidb", "yemekhane", "kütüphane"].some(k => m.entity_name.toLowerCase().includes(k)));
            vips.forEach(v => {
                if (!items.find(i => i.item.entity_name === v.entity_name)) items.push({ item: v, score: 1 });
            });
        }
        render(items.slice(0, 3));
    }

    window.hubul_save = (name) => {
        let h = JSON.parse(localStorage.getItem('hubul_history') || '[]');
        h = h.filter(x => x !== name);
        h.unshift(name);
        localStorage.setItem('hubul_history', JSON.stringify(h.slice(0, 5)));
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inject);
    } else {
        inject();
    }
})();
