import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import sys
import io
import re
import trafilatura
from datetime import datetime
from urllib.parse import urljoin, urlparse

def duyuru_gecerli_mi(tarih_metni, baslik, kaynak):
    if not tarih_metni: return False, None, "no_text"
    patterns = [
        r'(\d{2}\.\d{2}\.202[56])',
        r'(202[56]-\d{2}-\d{2})',
        r'(\d{2}/(\d{2}/202[56]))',
        r'(\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+202[56])'
    ]
    match = None
    for p in patterns:
        match = re.search(p, str(tarih_metni), re.IGNORECASE)
        if match: break
    if not match: return False, None, "date_not_found"
    tarih_str = match.group(1)
    ann_date = None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            ann_date = datetime.strptime(tarih_str, fmt)
            break
        except: continue
    if not ann_date:
        tr_months = {"Ocak": "1", "Şubat": "2", "Mart": "3", "Nisan": "4", "Mayıs": "5", "Haziran": "6",
                     "Temmuz": "7", "Ağustos": "8", "Eylül": "9", "Ekim": "10", "Kasım": "11", "Aralık": "12"}
        for tr_m, m_num in tr_months.items():
            if tr_m.lower() in tarih_str.lower():
                standard_date = re.sub(tr_m, m_num, tarih_str, flags=re.IGNORECASE).replace(" ", ".")
                try:
                    parts = standard_date.split('.')
                    ann_date = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
                    break
                except: continue
    if not ann_date: return False, None, "parse_error"
    now = datetime.now() 
    if ann_date.year < 2025: return False, ann_date, "too_old"
    if ann_date > now and (ann_date - now).days > 60: return False, ann_date, "future"
    return True, ann_date, "valid"

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_JSON = os.path.join(ROOT_DIR, "public", "outputs", "hybrid_master.json")
OUTPUT_PINGER = os.path.join(ROOT_DIR, "public", "outputs", "announcements_live.json")

FALLBACK_SCHEMAS = [".duyurular_liste", ".duyurular", "#duyurular", ".duyuru", ".icerik_yazi", ".duyuru-liste", ".news-list", "article", ".content", "#content"]

FAKE_KEYWORDS = [
    "tiklayiniz", "detay", "devami", "daha fazla", "see all", "view all", "arsiv",
    "ileri", "geri", "hepsini goster", "tikla", "tumunu gor", "tumu", "tiklayin", 
    "detaylar", "sonraki", "onceki", "ana sayfa", "anasayfa", "iletisim", 
    "hakkimizda", "giris", "duyurular", "haberler", "contact", "home", "about", 
    "news", "announcements", "search", "login", "logout", "menu", "kapat", "ust", "basa don"
]

# 🚫 BLACKLIST: Duyuru çekilmesi istenmeyen alakasız yerler
BLACKLIST_DOMAINS = [
    "ego.gov.tr",
    "google.com",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "endokrin.hacettepe.edu.tr"
]

def normalize_text(text):
    if not text: return ""
    tr_map = str.maketrans("çğıöşüİĞIÖŞÜ", "cgiosuIGIOSU")
    text = str(text).translate(tr_map)
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip().lower()

async def fetch_announcement_detail_and_date(session, url, semaphore, title, entity_name):
    async with semaphore:
        try:
            async with session.get(url, timeout=20, ssl=False) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.get_text(" ", strip=True)
                    valid, d_obj, _ = duyuru_gecerli_mi(text, title, entity_name)
                    content_tags = soup.select('.icerik, .icerik_yazi, .content, #content, article')
                    temiz_metin = ""
                    if content_tags:
                        best_tag = max(content_tags, key=lambda t: len(t.get_text(strip=True)))
                        temiz_metin = best_tag.get_text(" ", strip=True)
                    if len(temiz_metin) < 50:
                        temiz_metin = trafilatura.extract(html, include_links=False) or ""
                    return re.sub(r'\s+', ' ', temiz_metin).strip(), d_obj
        except: pass
    return None, None

async def fetch_announcements(session, entity, semaphore, detail_semaphore):
    url = entity.get("announcement_url") or entity.get("url")
    entity_name = entity.get("entity_name")
    schemas = [entity.get("announcement_schema")] if entity.get("announcement_schema") else FALLBACK_SCHEMAS
    async with semaphore:
        try:
            async with session.get(url, timeout=30, ssl=False) as response:
                if response.status != 200: return None
                soup = BeautifulSoup(await response.text(), "html.parser")
                results = []
                # KÜTÜPHANE ÖZEL (Jilet Modu)
                if "library.hacettepe.edu.tr" in url:
                    # Kütüphane sitesindeki o temiz başlıkları tutan ana elemanlar
                    anchors = soup.find_all('a', attrs={"data-toggle": "collapse"})
                    for a_tag in anchors:
                        title_raw = a_tag.get_text(strip=True)
                        if ">>" in title_raw:
                            title = title_raw.split(">>")[-1].strip()
                            target_id = a_tag.get('href', '').replace('#', '')
                            body = soup.find(id=target_id)
                            if body and title:
                                link_elem = body.find('a', href=True)
                                if link_elem:
                                    # Tarih bul
                                    is_v, d_obj, _ = duyuru_gecerli_mi(title_raw, title, entity_name)
                                    results.append({
                                        "title": title,
                                        "link": urljoin(url, link_elem['href']),
                                        "date": d_obj.strftime("%d.%m.%Y %H:%M") if is_v else datetime.now().strftime("%d.%m.%Y %H:%M"),
                                        "source": entity_name,
                                        "entity": entity_name,
                                        "description": body.get_text(" ", strip=True)[:300]
                                    })
                    if results:
                        results.sort(key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y %H:%M"), reverse=True)
                        return {"entity": entity_name, "url": url, "last_updated": datetime.now().isoformat(), "items": results[:5]}

                for schema in schemas:
                    if not schema or schema == "null": continue
                    containers = soup.select(schema)
                    for container in containers:
                        for a in container.find_all("a", href=True):
                            if len(results) >= 5: break
                            title = a.get_text(strip=True)
                            norm = normalize_text(title)
                            # AGRESİF FİLTRE
                            if any(fake in norm for fake in FAKE_KEYWORDS) or len(title) < 5 or title.startswith("http"):
                                # Başlık Kurtarma (Parent)
                                curr = a
                                found_better = False
                                for _ in range(4):
                                    curr = curr.parent
                                    if not curr: break
                                    t_elem = curr.find(['h1','h2','h3','h4','h5','h6','strong','b'])
                                    if t_elem:
                                        t_text = t_elem.get_text(strip=True)
                                        t_norm = normalize_text(t_text)
                                        if len(t_text) > 10 and not any(f in t_norm for f in FAKE_KEYWORDS):
                                            title, norm, found_better = t_text, t_norm, True
                                            break
                                if not found_better:
                                    # Kütüphane ve Akordeon Tipi Yapılar: Linkin ebeveyni bir panel gövdesiyse kardeş başlığı bul
                                    body = a.find_parent(id=re.compile(r'^detay|^collapse|^panel', re.I))
                                    if body and body.get('id'):
                                        header_a = soup.find('a', href=re.compile(f"#{body['id']}$"))
                                        if header_a:
                                            t_text = header_a.get_text(strip=True).split('>>')[-1].strip()
                                            if len(t_text) > 8:
                                                title, norm, found_better = t_text, normalize_text(t_text), True
                                
                                if not found_better:
                                    # Normal hiyerarşide yukarı tırman
                                    curr = a
                                    for _ in range(5):
                                        curr = curr.parent
                                        if not curr: break
                                        header = curr.find(['h1','h2','h3','h4','h5','h6'], class_=re.compile(r'title|heading|header|toggle', re.I)) or \
                                                 curr.find(class_=re.compile(r'panel-title|accordion-header|card-header|heading', re.I))
                                        if header:
                                            t_text = header.get_text(strip=True).split('>>')[-1].strip()
                                            if len(t_text) > 10 and not any(f in normalize_text(t_text) for f in FAKE_KEYWORDS):
                                                title, norm, found_better = t_text, normalize_text(t_text), True
                                                break
                                
                                if not found_better:
                                    parent_text = a.parent.get_text(" ", strip=True)
                                    if ">>" in parent_text: parent_text = parent_text.split(">>")[-1].strip()
                                    if len(parent_text) > 150: parent_text = parent_text[:100].split('.')[0] + "..."
                                    p_norm = normalize_text(parent_text)
                                    if 15 < len(parent_text) < 200 and p_norm not in FAKE_KEYWORDS:
                                        title, norm, found_better = parent_text, p_norm, True
                                
                                if not found_better: continue

                            # 🛡️ SON SÜZGEÇ: Çöp fragmanları temizle
                            trash_exact = ["konusmacilar", "buradan", "erisebilirsiniz", "tiklayin", "kayit", "detaylar", "sunum", "video", "erisim adresi", "erisim", "adresi", "tiklayiniz", "kayit linki"]
                            if norm in trash_exact or len(title) < 8 or any(f == norm for f in FAKE_KEYWORDS):
                                continue

                            # Aynı birim içinde aynı başlığı 2. kez ekleme
                            if any(normalize_text(r["title"]) == norm for r in results): continue

                            href_raw = a["href"]
                            href_clean = re.sub(r'<[^>]+>', '', str(href_raw)).strip()
                            href = urljoin(url, href_clean)
                            if href_clean.startswith('#'): continue
                            
                            if any(normalize_text(r["title"]) == norm for r in results): continue
                            
                            date_obj = None
                            parent = a.parent
                            for _ in range(5):
                                if not parent: break
                                is_v, d_obj, _ = duyuru_gecerli_mi(parent.get_text(" ", strip=True), title, entity_name)
                                if is_v: date_obj = d_obj; break
                                parent = parent.parent
                            
                            detail_text = ""
                            if not date_obj and not href.lower().endswith('.pdf'):
                                detail_text, date_obj = await fetch_announcement_detail_and_date(session, href, detail_semaphore, title, entity_name)
                            elif not href.lower().endswith('.pdf'):
                                detail_text, _ = await fetch_announcement_detail_and_date(session, href, detail_semaphore, title, entity_name)
                            
                            if not date_obj: continue # TARİH YOKSA ŞUTLA
                            results.append({"title": title.strip(), "link": href, "date": date_obj.strftime("%d.%m.%Y %H:%M"), "source": entity_name, "entity": entity_name, "description": detail_text[:500] if detail_text else None})
                    if results: break
                if results:
                    results.sort(key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y %H:%M"), reverse=True)
                    return {"entity": entity_name, "url": url, "last_updated": datetime.now().isoformat(), "items": results}
        except: pass
    return None

async def main():
    print("[i] Duyuru Çekici başlatılıyor...")
    with open(MASTER_JSON, "r", encoding="utf-8") as f: master_data = json.load(f)
    targets = [e for e in master_data if e.get("url")]
    
    # Blacklist filtresi uygula
    targets = [
        e for e in targets 
        if not any(black in e.get("url", "").lower() for black in BLACKLIST_DOMAINS)
    ]
    
    sem, d_sem = asyncio.Semaphore(50), asyncio.Semaphore(15)
    async with aiohttp.ClientSession(headers={"User-Agent": "HacettepeSniper/1.0"}) as session:
        results = await asyncio.gather(*[fetch_announcements(session, e, sem, d_sem) for e in targets])
    live = [r for r in results if r]
    with open(OUTPUT_PINGER, "w", encoding="utf-8") as f: json.dump(live, f, ensure_ascii=False, indent=4)
    print(f"[+] Tamamlandı! {len(live)} birim.")

if __name__ == "__main__":
    if os.name == 'nt': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
