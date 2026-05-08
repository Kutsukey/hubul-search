import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import sys
import io
import re
from datetime import datetime

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MASTER_JSON = "outputs/hybrid_master.json"
OUTPUT_PINGER = "outputs/announcements_live.json"

# Hacettepe sitelerinde en sık kullanılan duyuru seçicileri
FALLBACK_SCHEMAS = [
    ".duyurular_liste", 
    "#duyurular", 
    ".icerik_yazi", 
    ".duyuru-liste", 
    ".manset-container",
    ".news-list",
    "#manset"
]

async def fetch_announcements(session, entity, semaphore):
    url = entity.get("url")
    # Eğer özel bir schema varsa onu kullan, yoksa fallback listesini dene
    target_schema = entity.get("announcement_schema")
    schemas_to_try = [target_schema] if target_schema and target_schema != "null" else FALLBACK_SCHEMAS
    
    async with semaphore:
        try:
            async with session.get(url, timeout=15, ssl=False) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                announcements = []
                
                for schema in schemas_to_try:
                    container = soup.select_one(schema)
                    if container:
                        # Bu container içindeki linkleri bul
                        links = container.find_all("a", href=True)
                        valid_count = 0
                        for a in links:
                            if valid_count >= 3: 
                                break
                                
                            title = a.get_text(strip=True)
                            # Regex ile hem tüm boşlukları hem de Türkçe karakterleri normalize et
                            norm_title = re.sub(r'\s+', ' ', title).strip().lower().replace('ı', 'i').replace('i̇', 'i')
                            
                            # 1. KESİN EŞLEŞME (Çöpe atılacak jenerik butonlar)
                            exact_fakes = ["tıklayınız", "detay", "devamı", "daha fazla", "see all", "view all", "arşiv", "arsiv", "ileri", "geri", "hepsini göster", "tıkla", "tümünü gör", "tümü", "tıklayın", "tıklayınız...", "detaylar"]
                            
                            # 2. İÇİNDE GEÇENLER
                            contains_fakes = ["tüm duyurular", "tüm haberler", "diğer duyurular", "duyuru arşivi"]
                            
                            # Filtreleme Mantığı
                            is_fake = False
                            if any(fake == norm_title for fake in exact_fakes):
                                is_fake = True
                            elif any(fake in norm_title for fake in contains_fakes):
                                is_fake = True
                            elif title.startswith("http") or len(title) < 8: # Çok kısa veya çıplak URL
                                is_fake = True
                            
                            # Eğer her şey tamamsa GERÇEK DUYURUDUR!
                            if not is_fake:
                                href = a["href"]
                                if not href.startswith("http"):
                                    from urllib.parse import urljoin
                                    href = urljoin(url, href)
                                
                                announcements.append({
                                    "title": title,
                                    "link": href,
                                    "source": entity.get("entity_name")
                                })
                                valid_count += 1
                        
                        if announcements:
                            # print(f"[+] Duyuru yakalandı ({schema}): {url}")
                            break # Bir schema çalıştıysa diğerlerine bakma
                
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
    print("[i] Sniper Bot (Duyuru Çekici) başlatılıyor...")
    
    if not os.path.exists(MASTER_JSON):
        print(f"[!] Hata: {MASTER_JSON} bulunamadı.")
        return
        
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        master_data = json.load(f)
        
    # Sadece URL'si olanları işle
    targets = [e for e in master_data if e.get("url")]
    print(f"[i] Toplam {len(targets)} birim taranacak.")
    
    semaphore = asyncio.Semaphore(50) # Pinger çok hafiftir, 50 concurrency güvenli.
    
    async with aiohttp.ClientSession(headers={"User-Agent": "HacettepeSniper/1.0"}) as session:
        tasks = [fetch_announcements(session, entity, semaphore) for entity in targets]
        results = await asyncio.gather(*tasks)
        
    # Boş sonuçları temizle
    live_data = [r for r in results if r]
    
    with open(OUTPUT_PINGER, "w", encoding="utf-8") as f:
        json.dump(live_data, f, ensure_ascii=False, indent=4)
        
    print(f"[+] Tarama tamamlandı! {len(live_data)} birimden güncel duyuru çekildi.")
    print(f"[+] Sonuçlar: {OUTPUT_PINGER}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
