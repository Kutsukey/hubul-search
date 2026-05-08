import asyncio
import os
import json
import time
import re
import hashlib
from typing import List, Optional
from urllib.parse import urlparse, urljoin, unquote
import aiohttp
from bs4 import BeautifulSoup
from google import genai
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

# Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[UYARI] playwright kurulu değil. JS tabanlı sayfalar atlanacak.")

# Dizin Yapılandırması
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "inputs")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

env_path = os.path.join(os.path.dirname(BASE_DIR), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# ==========================================
# 1. PYDANTIC VERİ MODELİ
# ==========================================
class HacettepeEntity(BaseModel):
    is_active: bool = Field(..., description="Sitedeki son duyuru, etkinlik veya footer telif yılı 2024 ve öncesine aitse FALSE. Güncel bir siteyse TRUE.")
    is_valid_entity: bool = Field(..., description="Eğer bu sayfa büyük bir kurumsal birim DEĞİLSE (örneğin; laboratuvarlar, araştırma grupları, veri koleksiyonları, yayın listeleri, kişisel sayfalar) KESİNLİKLE FALSE yap.")
    entity_name: str = Field(..., description="Birimin adı (örn: Avrupa Birliği Koordinatörlüğü)")
    category: str = Field(..., description="Rektörlük, Fakülte, İdari Birim, Koordinatörlük, Araştırma Merkezi gibi etiketlerden biri")
    description: str = Field(..., description="LLM tarafından sayfa içeriğinden özetlenmiş kısa bilgi")
    important_links: List[str] = Field(default=[], description="Sayfadaki 'Kararlar', 'Yönetmelikler', 'PDF', 'Mevzuat' linklerini içeren liste")
    announcement_schema: Optional[str] = Field(None, description="Duyuruların bulunduğu HTML bölümünün CSS seçicisi (selector) veya yapısı.")
    sub_branches: List[str] = Field(default=[], description="Eğer sayfa içerisinde alt birimler listeleniyorsa bunların isimleri")

# ==========================================
# 2. DEEP CRAWLER YARDIMCI FONKSİYONLARI VE PLAYWRIGHT
# ==========================================
ALLOWED_DOMAIN = "hacettepe.edu.tr"

FILE_EXTENSIONS = {
    'pdf': ('.pdf',),
    'excel': ('.xls', '.xlsx'),
    'word': ('.doc', '.docx'),
    'archive': ('.zip', '.rar')
}

def get_file_type(url):
    lower_path = urlparse(url).path.lower()
    for ftype, exts in FILE_EXTENSIONS.items():
        if lower_path.endswith(exts):
            return ftype
    return None

def is_clean_for_rag(url):
    url_lower = url.lower()
    RAG_NOISE_PATTERNS = [r"/arsiv/", r"/archive/", r"/galeri/", r"/gallery/"]
    return not any(re.search(pattern, url_lower) for pattern in RAG_NOISE_PATTERNS)

def score_document_relevance(url, filename, size_bytes):
    score = 0
    keywords = ['yönerge', 'yönetmelik', 'takvim', 'akademik', 'form', 'mevzuat']
    if any(kw in url.lower() for kw in keywords):
        score += 1
    if re.search(r'\d{4}', filename):
        score += 1
    if size_bytes > 50 * 1024:
        score += 1
    return score >= 2

def is_valid_internal_link(url):
    parsed = urlparse(url)
    if ALLOWED_DOMAIN not in parsed.netloc:
        return False
    if url.startswith(('mailto:', 'tel:', 'javascript:')):
        return False
    return True

def clean_url(url):
    return url.split('#')[0].rstrip('/')

PRIORITY_KEYWORDS = ["yonerge", "yonetmelik", "esaslar", "mevzuat", "karar", "senato"]

JS_RENDER_URL_PATTERNS = [
    r"/duyuru", r"/haber", r"/icerik", r"/news", r"/announcements",
    r"/etkinlik", r"/events", r"/blog"
]
JS_LOADING_TEXTS = ["loading", "yükleniyor", "lütfen bekleyin", "please wait", "skeleton"]
JS_BODY_MIN_CHARS = 200

def is_js_candidate(url: str, body_text: str) -> bool:
    url_lower = url.lower()
    has_pattern = any(re.search(p, url_lower) for p in JS_RENDER_URL_PATTERNS)
    body_short = len(body_text.strip()) < JS_BODY_MIN_CHARS
    has_loading = any(t in body_text.lower() for t in JS_LOADING_TEXTS)
    return has_pattern and (body_short or has_loading)

class PlaywrightPool:
    def __init__(self, concurrency: int = 3):
        self._playwright = None
        self._browser = None
        self._semaphore = asyncio.Semaphore(concurrency)

    async def start(self):
        if not PLAYWRIGHT_AVAILABLE:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        print("[Playwright] Chromium browser havuzu başlatıldı.")

    async def stop(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("[Playwright] Chromium browser havuzu durduruldu.")

    async def fetch_js(self, url: str) -> str | None:
        if not self._browser:
            return None
        async with self._semaphore:
            ctx = await self._browser.new_context(ignore_https_errors=True)
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                content = await page.evaluate("""
                    () => {
                        const selectors = ['.content', 'article', 'main', '#root', '#app',
                                          '.duyuru', '.haber', '.icerik', '.announcement'];
                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el && el.innerText.trim().length > 100) return el.innerText.trim();
                        }
                        return document.body.innerText.trim();
                    }
                """)
                return content if content and len(content) > 50 else None
            except Exception as e:
                # Sessiz başarısızlık (konsolu kirletmemek için logu kapattık veya debug eklenebilir)
                return None
            finally:
                await page.close()
                await ctx.close()

_pw_pool: PlaywrightPool | None = None

async def fetch(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200 and 'text/html' in resp.headers.get('Content-Type', ''):
                    html = await resp.text()
                    soup_quick = BeautifulSoup(html, 'html.parser')
                    body_text = soup_quick.get_text(separator=' ', strip=True)
                    if is_js_candidate(url, body_text) and _pw_pool is not None:
                        js_text = await _pw_pool.fetch_js(url)
                        if js_text:
                            return html, url, js_text
                    return html, url, None
        except Exception:
            pass
    return None, url, None

async def fetch_head(session, url, semaphore):
    async with semaphore:
        size, etag, last_modified = 0, None, None
        try:
            async with session.head(url, timeout=5) as resp:
                size = int(resp.headers.get('Content-Length', 0))
                etag = resp.headers.get('ETag')
                last_modified = resp.headers.get('Last-Modified')
        except Exception:
            pass
        return size, etag, last_modified

async def crawl_tree_async(start_url, max_pages=12):
    """Deep Crawler bileşeni: BFS ile ağacı tarar."""
    queue = [start_url]
    visited_pages = set([start_url])
    
    tree_data = {
        "sayfalar": [],
        "dosyalar": [],
        "bilgi_sayfalari": [],
        "suspected_duplicates": []
    }
    
    found_urls = set([start_url])
    priority_visited = 0
    hard_limit = 50 # Her alt site için max derinlik güvenliği
    
    semaphore = asyncio.Semaphore(15)
    connector = aiohttp.TCPConnector(ssl=False)
    
    seen_hashes = set()
    seen_filenames = {}

    async with aiohttp.ClientSession(connector=connector) as session:
        while queue and (len(visited_pages) <= max_pages or priority_visited < 10):
            if len(visited_pages) > hard_limit: break
            
            batch_size = min(15, len(queue))
            current_urls = [queue.pop(0) for _ in range(batch_size)]
            
            tasks = [fetch(session, u, semaphore) for u in current_urls]
            results = await asyncio.gather(*tasks)
            
            file_head_tasks = []
            file_meta_info = []

            for result in results:
                html, current_url, js_text = result
                if not html: continue
                
                if js_text:
                    tree_data["bilgi_sayfalari"].append({
                        "url": current_url,
                        "tip": "Bilgi Sayfası",
                        "icerik": js_text[:5000],
                        "kaynak": "playwright"
                    })
                
                soup = BeautifulSoup(html, 'html.parser')
                
                for a_tag in soup.find_all('a', href=True):
                    raw_href = a_tag['href'].strip()
                    if not raw_href: continue
                    
                    full_url = clean_url(urljoin(current_url, raw_href))
                    if not is_valid_internal_link(full_url): continue
                    if not is_clean_for_rag(full_url): continue
                    
                    link_text = a_tag.get_text(strip=True) or unquote(full_url.split('/')[-1])
                    file_type = get_file_type(full_url)
                    
                    if full_url not in found_urls:
                        found_urls.add(full_url)
                        
                        is_priority = any(k in full_url.lower() for k in PRIORITY_KEYWORDS)
                        
                        if file_type:
                            file_head_tasks.append(fetch_head(session, full_url, semaphore))
                            file_meta_info.append({
                                "url": full_url,
                                "type": file_type,
                                "text": link_text,
                                "source": current_url
                            })
                        else:
                            tree_data["sayfalar"].append({
                                "baslik": link_text,
                                "url": full_url
                            })
                            
                            if full_url not in visited_pages:
                                if len(visited_pages) < max_pages:
                                    visited_pages.add(full_url)
                                    queue.append(full_url)
                                elif is_priority:
                                    visited_pages.add(full_url)
                                    queue.append(full_url)
                                    priority_visited += 1

            if file_head_tasks:
                head_results = await asyncio.gather(*file_head_tasks)
                for index, (size_bytes, etag, last_modified) in enumerate(head_results):
                    meta = file_meta_info[index]
                    full_url = meta["url"]
                    filename = unquote(full_url.split('/')[-1])
                    
                    canonical_path = urlparse(full_url).path.rstrip('/')
                    path_hash = hashlib.md5(canonical_path.encode()).hexdigest()
                    
                    if path_hash in seen_hashes: continue
                    seen_hashes.add(path_hash)

                    if filename in seen_filenames and seen_filenames[filename] != full_url:
                        continue
                        
                    seen_filenames[filename] = full_url

                    if not score_document_relevance(full_url, filename, size_bytes):
                        continue

                    tree_data["dosyalar"].append({
                        "tip": meta["type"],
                        "baslik": meta["text"],
                        "url": full_url,
                        "kaynak_sayfa": meta["source"]
                    })
            await asyncio.sleep(0.1)
    
    return tree_data

# ==========================================
# 3. A-Z LİNK TOPLAYICI
# ==========================================
BLACKLIST_DOMAINS = ["bologna.hacettepe.edu.tr", "arsiv.hacettepe.edu.tr"]

def is_allowed_az_url(url: str) -> bool:
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
    print("[i] A-Z Dizini taranıyor...")
    alphabet = "ABCÇDEFGHIİJKLMNOÖPRSŞTUÜVYZ"
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
                        if href.startswith('http') and is_allowed_az_url(href):
                            parsed = urlparse(href)
                            if parsed.netloc != "www.hacettepe.edu.tr" and parsed.netloc != "hacettepe.edu.tr":
                                all_links.add(href.rstrip('/'))
        except Exception as e:
            print(f"[!] {url} alınamadı: {e}")

    tasks = [fetch_letter(char) for char in alphabet]
    await asyncio.gather(*tasks)
    
    links_list = sorted(list(all_links))
    az_file = os.path.join(INPUT_DIR, "az_links.json")
    with open(az_file, "w", encoding="utf-8") as f:
        json.dump(links_list, f, ensure_ascii=False, indent=4)
    print(f"[+] Toplam {len(links_list)} link bulundu ve kaydedildi.")
    return links_list

# ==========================================
# 4. CUSTOM LLM PIPELINE (Gemma + Pydantic + Hybrid Veri)
# ==========================================
async def extract_entity_data_with_gemma(html_content: str, crawled_tree_data: dict, url: str, client: genai.Client, model_name: str) -> Optional[dict]:
    # Deep Crawler'dan gelen verileri hazırla
    found_pdfs = [f"{d['baslik']} - {d['url']}" for d in crawled_tree_data.get('dosyalar', [])]
    found_pages = [p['baslik'] for p in crawled_tree_data.get('sayfalar', [])][:40] # İlk 40 sayfa
    
    prompt = f"""Sen uzman bir Veri Mühendisisin. Aşağıda Hacettepe Üniversitesi'nin bir birimine ait ana sayfanın HTML içeriği ve botumuzun alt sayfalarda bulduğu dosyalar yer alıyor.

ÖNEMLİ GÖREVLERİN (GÜVENLİK FİLTRELERİ):
1. ZAMAN KONTROLÜ (is_active): 
   - Sitedeki en son tarih 2024 veya öncesiyse FALSE yap.
   - EĞER sitede hiçbir güncel tarih (2025 veya 2026) YOKSA, 
   - EĞER Duyurular/Haberler kısmı boşsa veya "Kayıt bulunamadı" diyorsa,
   - EĞER içerik sadece genel görev tanımlarından ibaretse ve hiçbir güncel hareketlilik ibaresi yoksa,
   KESİNLİKLE 'is_active' alanını FALSE yap. Burası bir "Zombi" sitedir.
2. KİMLİK KONTROLÜ (is_valid_entity): Biz sadece Fakülte, Bölüm, Enstitü, İdari Ofis ve Ana Merkezler gibi "Büyük Kurumsal Birimleri" haritalandırıyoruz. Eğer incelediğin sayfa;
   - Bir bölümün altındaki bireysel bir laboratuvar (örn: FoodOmics Laboratory vb.), 
   - Araştırma grubu veya proje sayfası,
   - Alt koleksiyonlar (Culture Collection vb.),
   - Sadece yayın/makale listesi,
   - Etkinlik/Konferans arşivi,
   - veya bir hocanın kişisel sayfasıysa...
   'is_valid_entity' alanını KESİNLİKLE FALSE yap. Laboratuvarlar ve araştırma grupları bağımsız bir kurumsal birim DEĞİLDİR.

KATEGORİ SEÇİMİ: SADECE şu listeden seçim yap. İsimlerdeki ipuçlarına dikkat et:
   - "Rektörlük"
   - "Fakülte"
   - "Enstitü" (Lisansüstü eğitim yerleri)
   - "Yüksekokul / Meslek Yüksekokulu" (Ön lisans/Hazırlık)
   - "Bölüm" (Fakülte altındaki ana lisans birimleri)
   - "Ana Bilim Dalı" (Enstitü veya Bölüm altındaki spesifik dallar)
   - "İdari Birim" (Daire Başkanlıkları, Müşavirlikler, Müdürlükler)
   - "Koordinatörlük" (İsminde Koordinatörlüğü geçenler)
   - "Araştırma Merkezi" (İsminde Uygulama ve Araştırma Merkezi / AM geçenler)
   - "Diğer"

CSS SEÇİCİ KURALI: 'announcement_schema' alanı için HTML kodunu incele. Duyuruların listelendiği ana <div> veya <ul> taşıyıcısının CSS Class'ını veya ID'sini bul (örn: '.news-list', '#duyurular_liste'). SADECE CSS SEÇİCİSİNİ YAZ. Asla Markdown başlığı (##) veya düz metin yazma! Eğer sayfada duyuru alanı yoksa null dön.

BOTUN BULDUĞU ÖNEMLİ DOSYALAR (PDF, Yönerge, Karar vb.):
{chr(10).join(found_pdfs) if found_pdfs else "Dosya bulunamadı."}

BOTUN BULDUĞU ALT SAYFALAR:
{chr(10).join(found_pages) if found_pages else "Alt sayfa bulunamadı."}

ANA SAYFA HTML İÇERİĞİ:
{html_content[:15000]}

JSON Şeması:
{{
  "is_active": "Sitedeki son tarih 2024 veya öncesi ise false, yoksa true (Boolean)",
  "is_valid_entity": "Kurumsal bir birim değilse false, geçerliyse true (Boolean)",
  "entity_name": "Birimin tam adı (String)",
  "category": "Yukarıda verilen SADECE belirtilen kategorilerden biri (String)",
  "description": "Sayfanın amacı ve işlevi hakkında kısa özet (String)",
  "important_links": ["Kararlar, Yönetmelikler, Mevzuat vb. önemli sayfaların tam URL'leri (String Listesi)"],
  "announcement_schema": "Duyuruların bulunduğu HTML bölümünün olası CSS seçicisi veya yapısı. Bulamazsan null (String veya null)",
  "sub_branches": ["Eğer sayfada alt bölümler/birimler listeleniyorsa bunların isimleri (String Listesi)"]
}}

Kurallar:
1. YALNIZCA geçerli bir JSON döndür. Markdown code block (```json ... ```) kullanabilirsin ancak dışında metin olmasın.
2. Sayfada yeterli bilgi yoksa, eldeki verilerle en iyi tahmini yap, boş bırakılabilecek listeleri boş bırak.
3. Site URL'si: {url}
"""
    try:
        response = await asyncio.to_thread(client.models.generate_content, model=model_name, contents=prompt)
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
        except Exception as e:
            print(f"[!] JSON Parse Hatası ({url}): {e}")
            return None
    except Exception as e:
        print(f"[!] Gemma hatası ({url}): {e}")
        return None

# ==========================================
# 5. SINGLE HYBRID URL PROCESSOR
# ==========================================
async def process_single_hybrid_url(url: str, crawler: AsyncWebCrawler, client: genai.Client, model_name: str) -> Optional[dict]:
    try:
        # 1. Aşama: Deep Crawl (Alt linkler ve PDF'ler toplanır)
        tree_data = await crawl_tree_async(url, max_pages=12) 
        
        # 2. Aşama: Crawl4AI ile Ana Sayfa Markdown çekimi
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        crawl_result = await crawler.arun(url=url, config=config)
        
        # 3. Aşama: Verilerin birleştirilip Gemma'ya gönderilmesi
        if crawl_result.success:
            entity_data = await extract_entity_data_with_gemma(crawl_result.cleaned_html, tree_data, url, client, model_name)
            if entity_data:
                entity_data["url"] = url
                # İsteğe bağlı olarak Deep Crawl verilerini de JSON'a dahil edebiliriz
                entity_data["deep_crawl_files"] = len(tree_data.get("dosyalar", []))
                entity_data["deep_crawl_pages"] = len(tree_data.get("sayfalar", []))
                return entity_data
    except Exception as e:
        print(f"[!] Hybrid Hata ({url}): {e}")
    return None

# ==========================================
# 6. BATCH PROCESSOR
# ==========================================
async def crawl_batch(links: List[str]):
    """Linkleri iki farklı Gemma modeliyle paralel işler."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] Hata: API anahtarı bulunamadı.")
        return

    client = genai.Client(api_key=api_key)
    
    model_26b = 'gemma-4-26b-a4b-it'
    model_31b = 'gemma-4-31b-it'
    
    sem_26b = asyncio.Semaphore(15)
    sem_31b = asyncio.Semaphore(15)
    
    results = []
    rejected_urls = []
    processed_urls = []
    
    # Global Playwright havuzunu başlat
    global _pw_pool
    if PLAYWRIGHT_AVAILABLE:
        _pw_pool = PlaywrightPool(concurrency=10)
        await _pw_pool.start()
    
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            async def sem_task(url, client, model_name, semaphore, model_label):
                site_name = urlparse(url).netloc.replace(".", "_")
                output_path = os.path.join(OUTPUT_DIR, f"output_{site_name}_hybrid.json")
                
                # RESUME ÖZELLİĞİ
                if os.path.exists(output_path):
                    try:
                        with open(output_path, "r", encoding="utf-8") as f:
                            res = json.load(f)
                        processed_urls.append(url)
                        return res
                    except:
                        pass

                async with semaphore:
                    res = await process_single_hybrid_url(url, crawler, client, model_name)
                    if res:
                        if not res.get("is_active", True) or not res.get("is_valid_entity", True):
                            print(f"[-] Çöpe Atıldı (Zombi veya Alakasız): {url} - {res.get('entity_name', 'Bilinmeyen')}")
                            rejected_urls.append(url)
                            processed_urls.append(url)
                            return None
                        
                        res.pop("is_active", None) 
                        res.pop("is_valid_entity", None) 

                        site_name = urlparse(url).netloc.replace(".", "_")
                        output_path = os.path.join(OUTPUT_DIR, f"output_{site_name}_hybrid.json")
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(res, f, ensure_ascii=False, indent=4)
                        print(f"[+] {model_label} Hybrid Başarılı: {url}")
                        processed_urls.append(url)
                        return res
                    return None
                    
            tasks = []
            for i, url in enumerate(links):
                if i % 2 == 0:
                    tasks.append(sem_task(url, client, model_26b, sem_26b, "Gemma-26b"))
                else:
                    tasks.append(sem_task(url, client, model_31b, sem_31b, "Gemma-31b"))
                    
            print(f"[i] {len(links)} URL için Hybrid paralel işlem başlatılıyor (15+15 batch)...")
            for coro in asyncio.as_completed(tasks):
                res = await coro
                if res: results.append(res)
    finally:
        # Havuzu kapat
        if _pw_pool:
            await _pw_pool.stop()
                
    if results:
        master_file = os.path.join(OUTPUT_DIR, "hybrid_master.json")
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n[+] Tamamlandı! Toplam {len(results)} başarılı sonuç '{master_file}' dosyasına kaydedildi.")

    # AZ_LINKS GÜNCELLEME (Queue Temizliği)
    if processed_urls:
        az_file = os.path.join(INPUT_DIR, "az_links.json")
        if os.path.exists(az_file):
            with open(az_file, "r", encoding="utf-8") as f:
                current_links = json.load(f)
            
            # Başarılı ve çöpe gidenleri çıkar (Processed = Success + Rejected)
            new_links = [l for l in current_links if l not in processed_urls]
            
            with open(az_file, "w", encoding="utf-8") as f:
                json.dump(new_links, f, ensure_ascii=False, indent=4)
            
            print(f"[Queue] {len(processed_urls)} link listeden temizlendi. Kalan: {len(new_links)}")

# ==========================================
# 7. ANA AKIŞ
# ==========================================
async def main():
    print("=== Hacettepe Hybrid Deep-RAG Pipeline ===")
    
    az_file = os.path.join(INPUT_DIR, "az_links.json")
    az_links = []
    
    if os.path.exists(az_file):
        with open(az_file, "r", encoding="utf-8") as f:
            az_links = json.load(f)
    
    if not az_links:
        print("[i] Liste boş veya bulunamadı, web üzerinden taranıyor...")
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            az_links = await fetch_az_links(session)

    if az_links:
        await crawl_batch(az_links)

if __name__ == "__main__":
    asyncio.run(main())
