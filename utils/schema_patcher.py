import asyncio
import os
import json
import shutil
import sys
import io
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

MASTER_JSON = "outputs/hybrid_master.json"
BACKUP_JSON = "outputs/hybrid_master_backup.json"

load_dotenv()

async def fetch_html_and_extract_schema(session, client, model_name, entity, semaphore):
    url = entity.get("url")
    if not url:
        return entity
        
    # Zaten daha önceden patchlenmişse atla
    if entity.get("announcement_schema") and entity.get("announcement_schema") != "null":
        return entity
        
    async with semaphore:
        try:
            # 1. Sadece ana sayfaya istek at
            async with session.get(url, timeout=15, ssl=False) as response:
                if response.status != 200:
                    return entity
                raw_content = await response.read()
                html = raw_content.decode('utf-8', errors='ignore')
                
            # 2. HAM HTML'i ayrıştır ve ilk 10.000 karakteri al
            soup = BeautifulSoup(html, "html.parser")
            body = soup.body
            if not body:
                return entity
                
            raw_body = str(body)[:10000]
            
            # 3. LLM'e CSS seçiciyi sor
            prompt = f"""Aşağıdaki üniversite sayfası HTML kodunda, duyuruların veya haberlerin listelendiği ana çerçevenin (container) CSS Seçicisini bul. (Örn: '.news-list', '#duyurular', '.manset-container'). YALNIZCA geçerli bir CSS seçici string'i döndür. Eğer bulamazsan 'null' yaz. Başka hiçbir kelime veya markdown kullanma.

HTML:
{raw_body}
"""
            
            max_retries = 3
            result = None
            
            for attempt in range(max_retries):
                try:
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=model_name,
                        contents=prompt
                    )
                    if response and response.text:
                        result = response.text.strip().strip("`").strip("'").strip('"')
                        break
                    else:
                        raise Exception("Boş cevap döndü")
                except Exception as api_err:
                    err_msg = str(api_err).lower()
                    print(f"[*] Deneme {attempt+1} Hatası ({url}): {api_err}")
                    sys.stdout.flush()
                    await asyncio.sleep(5 * (attempt + 1))
            
            if result and result.lower() != "null" and not " " in result and (result.startswith(".") or result.startswith("#")):
                entity["announcement_schema"] = result
                print(f"[+] Schema bulundu: {url} -> {result}")
            else:
                print(f"[-] Schema bulunamadı: {url} ({result})")
            
            sys.stdout.flush()
            # Dakikada 15 istek sınırına (15 RPM) takılmamak için 5 saniye bekliyoruz
            await asyncio.sleep(5)
                
        except Exception as e:
            print(f"[!] İstek Hatası ({url}): {e}")
            sys.stdout.flush()
            
    return entity

async def main():
    print("[i] Patcher (Gemma-31b) başlatılıyor...")
    sys.stdout.flush()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    model_name = "gemma-4-31b-it" 
    
    if not os.path.exists(MASTER_JSON):
        print(f"[!] Hata: {MASTER_JSON} dosyası bulunamadı.")
        return
        
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        master_data = json.load(f)
        
    print(f"[i] Toplam {len(master_data)} kayıt işlenecek.")
    sys.stdout.flush()
    
    if not os.path.exists(BACKUP_JSON):
        shutil.copy2(MASTER_JSON, BACKUP_JSON)
        print(f"[i] Yedek alındı: {BACKUP_JSON}")
        sys.stdout.flush()
    
    # Eşzamanlılık 2
    semaphore = asyncio.Semaphore(2)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HacettepePatcher/1.0"}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [fetch_html_and_extract_schema(session, client, model_name, entity, semaphore) for entity in master_data]
        updated_data = await asyncio.gather(*tasks)
        
    with open(MASTER_JSON, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)
        
    print(f"[+] İşlem tamamlandı! Schema yamaları {MASTER_JSON} üzerine başarıyla yazıldı.")
    sys.stdout.flush()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
