import asyncio
import os
import json
import shutil
import sys
import io
import re
from urllib.parse import urlparse, urljoin
import aiohttp
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Dizin Ayarları
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_JSON = os.path.join(BASE_DIR, "public", "outputs", "hybrid_master.json")
BACKUP_JSON = os.path.join(BASE_DIR, "public", "outputs", "hybrid_master_backup.json")

env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

async def fetch_html_and_extract_schema(session, client, model_name, entity, semaphore):
    base_url = entity.get("url", "").rstrip('/')
    if not base_url: return entity
        
    if entity.get("announcement_schema") and entity.get("announcement_url"):
        return entity
        
    async with semaphore:
        print(f"[*] İşleniyor: {base_url}", flush=True)
        
        # 1. Ana Sayfayı Çek ve Linkleri Bul
        target_urls = [base_url]
        try:
            async with session.get(base_url, timeout=12, ssl=False) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Duyuru linklerini avla
                    for a in soup.find_all('a', href=True):
                        text = a.get_text(strip=True).lower()
                        href = a['href']
                        if any(kw in text for kw in ["duyuru", "haber", "announcement", "news"]):
                            full_url = urljoin(base_url, href).rstrip('/')
                            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                                if full_url not in target_urls:
                                    target_urls.append(full_url)
        except:
            pass

        # Statik fallback listesi
        fallbacks = ["/duyurular", "/duyuru", "/haberler", "/haber"]
        for fb in fallbacks:
            u = base_url + fb
            if u not in target_urls: target_urls.append(u)

        # 2. Aday Sayfaları Tek Tek Kontrol Et (Max 4 deneme)
        for target_url in target_urls[:5]:
            try:
                async with session.get(target_url, timeout=10, ssl=False) as response:
                    if response.status != 200: continue
                    html = await response.text()
                
                soup = BeautifulSoup(html, "html.parser")
                content = str(soup.body)[:12000] if soup.body else html[:12000]
                
                prompt = f"Bu HTML'de duyuru listesinin CSS Seçicisini bul (örn: .news-list). Sadece seçiciyi yaz, yoksa 'null' yaz. HTML: {content}"
                
                response = await asyncio.to_thread(client.models.generate_content, model=model_name, contents=prompt)
                if response and response.text:
                    result = response.text.strip().strip("`").strip("'").strip('"')
                    if result and result.lower() != "null" and not " " in result and (result.startswith(".") or result.startswith("#")):
                        entity["announcement_schema"] = result
                        entity["announcement_url"] = target_url
                        print(f"[+] Schema bulundu ({target_url}): {result}", flush=True)
                        return entity
            except: continue
                
        print(f"[-] Başarısız: {base_url}", flush=True)
    return entity

async def main():
    print("[i] Akıllı Patcher başlatılıyor...", flush=True)
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] Hata: GOOGLE_API_KEY bulunamadı.", flush=True)
        return

    client = genai.Client(api_key=api_key)
    model_name = "gemma-4-31b-it" 
    
    if not os.path.exists(MASTER_JSON): return
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        master_data = json.load(f)
        
    null_items = [x for x in master_data if not x.get("announcement_schema") or x.get("announcement_schema") == "null"]
    print(f"[i] Toplam {len(master_data)} kayıt. {len(null_items)} tanesi boş.", flush=True)
    
    if not os.path.exists(BACKUP_JSON):
        shutil.copy2(MASTER_JSON, BACKUP_JSON)
    
    semaphore = asyncio.Semaphore(4) 
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [fetch_html_and_extract_schema(session, client, model_name, entity, semaphore) for entity in master_data]
        updated_data = await asyncio.gather(*tasks)
        
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)
        
    print(f"[+] Bitti!", flush=True)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
