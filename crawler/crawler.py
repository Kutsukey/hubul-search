import asyncio
import os
import json
import time
import re
from typing import List, Optional
from urllib.parse import urlparse, urljoin
import aiohttp
from bs4 import BeautifulSoup
import google.generativeai as genai
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

# Dizin Yapılandırması
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# Gerekli dizinleri oluştur
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# .env dosyasını bul ve yükle (Script alt klasörde olduğu için üst klasöre de bak)
env_path = os.path.join(os.path.dirname(BASE_DIR), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# ==========================================
# 1. PYDANTIC VERİ MODELİ
# ==========================================
class HacettepeEntity(BaseModel):
    entity_name: str = Field(..., description="Birimin adı (örn: Avrupa Birliği Koordinatörlüğü)")
    category: str = Field(..., description="Rektörlük, Fakülte, İdari Birim, Koordinatörlük, Araştırma Merkezi gibi etiketlerden biri")
    description: str = Field(..., description="LLM tarafından sayfa içeriğinden özetlenmiş kısa bilgi")
    important_links: List[str] = Field(default=[], description="Sayfadaki 'Kararlar', 'Yönetmelikler', 'PDF', 'Mevzuat' linklerini içeren liste")
    announcement_schema: Optional[str] = Field(None, description="Duyuruların bulunduğu HTML bölümünün CSS seçicisi (selector) veya yapısı.")
    sub_branches: List[str] = Field(default=[], description="Eğer sayfa içerisinde alt birimler listeleniyorsa bunların isimleri")

# ==========================================
# 2. A-Z LİNK TOPLAYICI (Filtreleme Dahil)
# ==========================================
BLACKLIST_DOMAINS = ["bologna.hacettepe.edu.tr", "arsiv.hacettepe.edu.tr", "endokrin.hacettepe.edu.tr"]

def is_allowed_url(url: str) -> bool:
    """URL'nin taranmaya uygun olup olmadığını kontrol eder."""
    try:
        parsed = urlparse(url)
        if "hacettepe.edu.tr" not in parsed.netloc:
            return False
        for black_domain in BLACKLIST_DOMAINS:
            if black_domain in parsed.netloc:
                return False
        if url.startswith(('mailto:', 'tel:', 'javascript:')):
            return False
        return True
    except:
        return False

async def fetch_az_links(session: aiohttp.ClientSession) -> List[str]:
    """Hacettepe A-Z sayfasından tüm alt kurum linklerini toplar ve inputs klasörüne kaydeder."""
    print("[i] A-Z Dizini taranıyor...")
    alphabet = "ABCÇDEFGHIİJKLMNOÖPRSTUÜVYZ"
    base_url = "https://www.hacettepe.edu.tr/hakkinda/AZ/"
    all_links = set()
    
    async def fetch_letter(char: str):
        url = f"{base_url}{char}"
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href'].strip()
                        if href.startswith('http') and is_allowed_url(href):
                            parsed = urlparse(href)
                            if parsed.netloc != "www.hacettepe.edu.tr" and parsed.netloc != "hacettepe.edu.tr":
                                all_links.add(href.rstrip('/'))
        except Exception as e:
            print(f"[!] {url} alınamadı: {e}")

    tasks = [fetch_letter(char) for char in alphabet]
    await asyncio.gather(*tasks)
    
    links_list = sorted(list(all_links))
    
    # Linkleri input klasörüne kaydet
    az_file = os.path.join(INPUT_DIR, "az_links.json")
    with open(az_file, "w", encoding="utf-8") as f:
        json.dump(links_list, f, ensure_ascii=False, indent=4)
    
    print(f"[+] Toplam {len(links_list)} link bulundu ve '{az_file}' dosyasına kaydedildi.")
    return links_list

# ==========================================
# 3. CUSTOM LLM PIPELINE (Gemma ile Pydantic)
# ==========================================
async def extract_entity_data_with_gemma(markdown_content: str, url: str, model: genai.GenerativeModel) -> Optional[dict]:
    """Markdown verisini Gemma'ya gönderip Pydantic modeline uygun JSON alır."""
    prompt = f"""Sen uzman bir Veri Mühendisisin. Aşağıdaki Hacettepe Üniversitesi alt sitesine ait markdown içeriğini analiz et.
Görevin, içerikten kurum hiyerarşisini, duyuru yapısını ve önemli bağlantıları çıkararak belirlenen JSON şemasına uyan bir obje döndürmektir.

İçerik:
{markdown_content[:15000]}
"""
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                text = text[start_idx:end_idx+1]
        
        text = text.strip()
        try:
            data = json.loads(text)
            entity = HacettepeEntity(**data)
            return entity.model_dump()
        except:
            return None
    except Exception as e:
        print(f"[!] Gemma hatası ({url}): {e}")
        return None

# ==========================================
# 4. SINGLE URL PROCESSOR
# ==========================================
async def process_single_url(url: str, crawler: AsyncWebCrawler, model: genai.GenerativeModel) -> Optional[dict]:
    """Tek bir URL'yi tarar ve Gemma ile analiz eder."""
    try:
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        crawl_result = await crawler.arun(url=url, config=config)
        if crawl_result.success:
            entity_data = await extract_entity_data_with_gemma(crawl_result.markdown, url, model)
            if entity_data:
                entity_data["url"] = url
                return entity_data
    except Exception as e:
        print(f"[!] Hata ({url}): {e}")
    return None

# ==========================================
# 5. BATCH PROCESSOR
# ==========================================
async def crawl_batch(links: List[str]):
    """Linkleri iki farklı Gemma modeliyle paralel (30 concurrent) işler."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] Hata: API anahtarı bulunamadı.")
        return

    genai.configure(api_key=api_key)
    
    # İki farklı model kurulumu
    model_26b = genai.GenerativeModel('gemma-4-26b-a4b-it')
    model_31b = genai.GenerativeModel('gemma-4-31b-it')
    
    # Her model için 15 istek sınırı (Toplam 30)
    sem_26b = asyncio.Semaphore(15)
    sem_31b = asyncio.Semaphore(15)
    
    results = []
    
    async with AsyncWebCrawler(verbose=False) as crawler:
        async def sem_task(url, model, semaphore, model_label):
            async with semaphore:
                res = await process_single_url(url, crawler, model)
                if res:
                    site_name = urlparse(url).netloc.replace(".", "_")
                    output_path = os.path.join(OUTPUT_DIR, f"output_{site_name}.json")
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(res, f, ensure_ascii=False, indent=4)
                    print(f"[+] {model_label} Başarılı: {url}")
                    return res
                return None
                
        tasks = []
        for i, url in enumerate(links):
            # Modelleri dönüşümlü olarak kullan
            if i % 2 == 0:
                tasks.append(sem_task(url, model_26b, sem_26b, "Gemma-26b"))
            else:
                tasks.append(sem_task(url, model_31b, sem_31b, "Gemma-31b"))
                
        print(f"[i] {len(links)} URL için paralel işlem başlatılıyor (15+15 batch)...")
        for coro in asyncio.as_completed(tasks):
            res = await coro
            if res: results.append(res)
                
    if results:
        master_file = os.path.join(OUTPUT_DIR, "hacettepe_entities_master.json")
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n[+] Tamamlandı! Toplam {len(results)} başarılı sonuç master dosyaya kaydedildi.")

async def main():
    print("=== Hacettepe IA Pipeline Crawler (Dual-Model Parallel) ===")
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        az_links = await fetch_az_links(session)
    
    if not az_links:
        az_file = os.path.join(INPUT_DIR, "az_links.json")
        if os.path.exists(az_file):
            with open(az_file, "r", encoding="utf-8") as f:
                az_links = json.load(f)

    if az_links:
        await crawl_batch(az_links)

if __name__ == "__main__":
    asyncio.run(main())
