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
    """
    Tarih ayıklar ve geçerlilik kontrolü yapar.
    Döner: (bool_gecerli, date_obj, reason)
    """
    if not tarih_metni:
        return False, None, "no_text"
        
    patterns = [
        r'(\d{2}\.\d{2}\.\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4})'
    ]
    
    match = None
    for p in patterns:
        match = re.search(p, str(tarih_metni), re.IGNORECASE)
        if match:
            break
            
    if not match:
        return False, None, "date_not_found"
        
    tarih_str = match.group(1)
    ann_date = None
    
    # 1. Standart formatlar
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            ann_date = datetime.strptime(tarih_str, fmt)
            break
        except: continue
            
    # 2. Türkçe ay isimleri
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
                        
    if not ann_date:
        return False, None, "parse_error"
        
    now = datetime.now() 
    # 2025 ve sonrası duyuruları kabul et (Mayıs 2026'dayız, 2025 makul bir sınır)
    if ann_date.year < 2025:
        return False, ann_date, "too_old_year"
    if ann_date > now:
        return False, ann_date, "future_date"
        
    title_lower = baslik.lower()
    source_lower = kaynak.lower()
    idari_birimler = ["öğrenci işleri", "oidb", "sağlık kültür", "sks", "rektörlük"]
    hayati_kelimeler = ["sınav", "takvim", "başvuru", "program", "kayıt", "muafiyet"]
    
    is_idari = any(birim in source_lower for birim in idari_birimler)
    is_hayati = any(kelime in title_lower for kelime in hayati_kelimeler)

    max_age_days = 90 if (is_idari and is_hayati) else 30
    age_days = (now - ann_date).days
    
    if age_days > max_age_days:
        return False, ann_date, "ttl_expired"
        
    return True, ann_date, "valid"

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Proje kök dizinini sys.path'e ekleyelim
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Proje kök dizinini bul
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Config'e falan güvenme, yolu direkt jilet gibi kendin çak:
MASTER_JSON = os.path.join(ROOT_DIR, "public", "outputs", "hybrid_master.json")
OUTPUT_PINGER = os.path.join(ROOT_DIR, "public", "outputs", "announcements_live.json")

# Hacettepe sitelerinde en sık kullanılan duyuru seçicileri
FALLBACK_SCHEMAS = [
    ".duyurular_liste", ".duyurular", "#duyurular", ".duyuru",
    ".icerik_yazi", ".duyuru-liste", ".manset-container", ".news-list",
    "#manset", ".announcements", ".news", "article", ".content", "#content",
    "main", ".main", ".container", "#main", ".page-content", ".entry-content"
]

async def fetch_announcement_detail(session, url, semaphore):
    """
    Duyuru linkine gider ve trafilatura ile temiz metin çeker.
    """
    async with semaphore:
        try:
            async with session.get(url, timeout=10, ssl=False) as response:
                if response.status == 200:
                    html = await response.text()
                    # Sadece ana içeriği süzerek al
                    temiz_metin = trafilatura.extract(html, include_links=False, include_images=False, include_formatting=False)
                    if temiz_metin:
                        # Gereksiz boşlukları temizle ve ilk 200 karakteri al (veya tamamını)
                        return re.sub(r'\s+', ' ', temiz_metin).strip()
        except:
            pass
    return None

async def fetch_announcements(session, entity, semaphore, detail_semaphore):
    url = entity.get("url")
    target_schema = entity.get("announcement_schema")
    schemas_to_try = [target_schema] if target_schema and target_schema != "null" else FALLBACK_SCHEMAS
    
    # Aynı birim içinde mükerrer linkleri engellemek için
    seen_links = set()
    
    async with semaphore:
        try:
            async with session.get(url, timeout=15, ssl=False) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                announcements = []
                for schema in schemas_to_try:
                    if not schema: continue
                    containers = soup.select(schema)
                    for container in containers:
                        links = container.find_all("a", href=True)
                        valid_count = 0
                        for a in links:
                            if valid_count >= 5: break
                                
                            title = a.get_text(strip=True)
                            norm_title = re.sub(r'\s+', ' ', title).strip().lower().replace('ı', 'i').replace('i̇', 'i')
                            
                            exact_fakes = [
                                "tıklayınız", "detay", "devamı", "daha fazla", "see all", "view all", "arşiv", "arsiv",
                                "ileri", "geri", "hepsini göster", "tıkla", "tümünü gör", "tümü", "tıklayın", "tıklayınız...", "detaylar",
                                "ana sayfa", "anasayfa", "iletişim", "hakkımızda", "hakkimizda", "giriş", "giris",
                                "duyurular", "haberler", "yukarı", "aşağı", "asagi", "contact", "home", "about",
                                "news", "announcements", "main page", "türkçe", "english", "tr", "en",
                                "yukari", "site map", "site haritası", "arama", "search", "login", "logout",
                                "menü", "menu", "kapat", "close", "üst", "üste", "başa dön", "basa don"
                            ]
                            contains_fakes = [
                                "tüm duyurular", "tüm haberler", "diğer duyurular", "duyuru arşivi",
                                "ana sayfa", "iletişim", "hakkımızda", "giriş", "duyurular", "haberler",
                                "site haritası", "contact", "home", "about", "news", "announcements",
                                "search", "login", "logout", "yukarı çık", "başa dön", "tümünü oku",
                                "detaylı bilgi", "daha detaylı", "yönetim", "akademik", "öğrenci", "personel"
                            ]
                            
                            is_fake = False
                            if any(fake == norm_title for fake in exact_fakes): is_fake = True
                            elif any(fake in norm_title for fake in contains_fakes): is_fake = True
                            elif title.startswith("http") or len(title) < 5: is_fake = True
                            
                            # Navigasyon linklerini (ana sayfa, iletişim, menü vb.) filtrele
                            if not is_fake:
                                href = a["href"]
                                href_full = urljoin(url, href)
                                href_path = urlparse(href_full).path.lower()
                                href_last = href_path.strip('/').split('/')[-1] if href_path.strip('/') else ''
                                nav_pages = {
                                    'index.html', 'index.php', 'index.htm', 'default.aspx', 'default.html',
                                    'tr', 'en', 'tr/', 'en/',
                                    'iletisim', 'iletisim.html', 'iletisim.php',
                                    'hakkimizda', 'hakkimizda.html', 'hakkimizda.php', 'hakkımızda',
                                    'duyurular', 'duyurular.html', 'duyurular.php', 'duyurular/',
                                    'haberler', 'haberler.html', 'haberler.php',
                                    'giris', 'giris.html', 'giris.php',
                                    'contact', 'contact.html', 'home', 'home.html',
                                    'about', 'about.html', 'news', 'news.html',
                                    'announcements', 'announcements.html', 'main', 'main.html',
                                    'galeri', 'fotograflar', 'videolar',
                                    'bolum', 'bolumler', 'programlar', 'kadro',
                                    'personel', 'ogrenci', 'ogrenciler',
                                    'akademik', 'yonetim', 'kurumsal', 'tarihce',
                                    'misyon', 'vizyon', 'sss', 'faq',
                                    'arama', 'search', 'login', 'logout',
                                    'kayit', 'kayit.html', 'kayit.php', 'kayıt', 'kayıt.html'
                                }
                                if href.startswith('#') or not href_last or href_last in nav_pages:
                                    is_fake = True
                                else:
                                    href = href_full
                            
                            if not is_fake:
                                # Tarih bulma mantığı - Parent Climb
                                curr = a
                                tarih_alani = None
                                for _ in range(3):
                                    curr = curr.parent
                                    if not curr: break
                                    tarih_alani = curr.find(class_=re.compile(r'tarih|date|duyuru_tarih|updated|published', re.I)) or \
                                                  curr.find(['code', 'small', 'time', 'span'], class_=re.compile(r'date|tarih', re.I)) or \
                                                  curr.find(['code', 'small', 'time'])
                                    if tarih_alani: break
                                
                                if tarih_alani:
                                    tarih_metni = tarih_alani.get_text(" ", strip=True)
                                else:
                                    # Parent metni çok gürültülü oluyor; sadece başlıkta tarih ara
                                    tarih_metni = title
                                
                                kaynak = entity.get("entity_name", "")
                                is_valid, ann_date, reason = duyuru_gecerli_mi(tarih_metni, title, kaynak)
                                
                                # Tarih bulunamazsa risk alıp kabul et
                                if not is_valid and reason == "date_not_found":
                                    is_valid = True
                                    tarih_metni = "Tarih Belirtilmemiş"
                                
                                if is_valid:
                                    if href not in seen_links:
                                        announcements.append({
                                            "title": title,
                                            "link": href,
                                            "date": tarih_metni,
                                            "source": kaynak,
                                            "entity": entity.get("entity_name")
                                        })
                                        seen_links.add(href)
                                        valid_count += 1
                        if announcements: break
                    if announcements: break
                
                # Duyuru içeriklerini trafilatura ile temizle (Opsiyonel: Hız için paralel)
                if announcements:
                    detail_tasks = [fetch_announcement_detail(session, ann["link"], detail_semaphore) for ann in announcements]
                    details = await asyncio.gather(*detail_tasks)
                    for i, detail in enumerate(details):
                        if detail:
                            # Eğer başlık çok kısaysa veya "tıklayınız" gibi bir şeyse, trafilatura'dan gelen ilk cümleyi kullanabiliriz
                            # Ama şimdilik sadece 'description' olarak ekleyelim
                            announcements[i]["description"] = detail[:500] # İlk 500 karakter yeterli
                
                if announcements:
                    return {
                        "entity": entity.get("entity_name"),
                        "url": url,
                        "last_updated": datetime.now().isoformat(),
                        "items": announcements
                    }
        except Exception:
            pass
    return None

async def main():
    print("[i] Duyuru Çekici başlatılıyor...")
    if not os.path.exists(MASTER_JSON):
        print(f"[!] Hata: {MASTER_JSON} bulunamadı.")
        return
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        master_data = json.load(f)
    targets = [e for e in master_data if e.get("url")]
    print(f"[i] Toplam {len(targets)} birim taranacak.")
    semaphore = asyncio.Semaphore(50)
    detail_semaphore = asyncio.Semaphore(15) # Global semaphore: Toplamda en fazla 15 paralel detay çekimi
    
    async with aiohttp.ClientSession(headers={"User-Agent": "HacettepeSniper/1.0"}) as session:
        tasks = [fetch_announcements(session, entity, semaphore, detail_semaphore) for entity in targets]
        results = await asyncio.gather(*tasks)
    live_data = [r for r in results if r]
    with open(OUTPUT_PINGER, "w", encoding="utf-8") as f:
        json.dump(live_data, f, ensure_ascii=False, indent=4)
    print(f"[+] Tarama tamamlandı! {len(live_data)} birimden duyuru çekildi.")
    print(f"[+] Sonuçlar: {OUTPUT_PINGER}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
