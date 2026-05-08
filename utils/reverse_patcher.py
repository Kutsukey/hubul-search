import asyncio
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import sys
import io

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MASTER_JSON = "outputs/hybrid_master.json"

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

async def check_schema_success(session, entity, semaphore):
    url = entity.get("url")
    # Zaten bir schema varsa (yamalıysa) elleme
    if entity.get("announcement_schema") and entity.get("announcement_schema") != "null":
        return None
        
    async with semaphore:
        try:
            async with session.get(url, timeout=10, ssl=False) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                for schema in FALLBACK_SCHEMAS:
                    container = soup.select_one(schema)
                    if container:
                        # Bu container gerçekten link içeriyor mu? (Boş kutu olmasın)
                        links = container.find_all("a", href=True)
                        if len(links) > 0:
                            return {"entity_name": entity["entity_name"], "found_schema": schema}
        except Exception:
            pass
    return None

async def main():
    print("[i] Reverse Patcher başlatılıyor... (Fallback'leri yakalayıp ana JSON'a işleme)")
    
    if not os.path.exists(MASTER_JSON):
        print(f"[!] Hata: {MASTER_JSON} bulunamadı.")
        return
        
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        master_data = json.load(f)
        
    targets = [e for e in master_data if e.get("url") and (not e.get("announcement_schema") or e.get("announcement_schema") == "null")]
    print(f"[i] Toplam {len(targets)} birim kontrol edilecek.")
    
    semaphore = asyncio.Semaphore(50)
    async with aiohttp.ClientSession(headers={"User-Agent": "HacettepeReversePatcher/1.0"}) as session:
        tasks = [check_schema_success(session, entity, semaphore) for entity in targets]
        results = await asyncio.gather(*tasks)
        
    # Başarılı eşleşmeleri filtrele
    success_map = {r["entity_name"]: r["found_schema"] for r in results if r}
    
    # Master JSON'ı güncelle
    patched_count = 0
    for entity in master_data:
        name = entity["entity_name"]
        if name in success_map:
            entity["announcement_schema"] = success_map[name]
            patched_count += 1
            
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=4)
        
    print(f"[+] Tersine yama tamamlandı! {patched_count} birim için çalışan schema bulundu ve kaydedildi.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
