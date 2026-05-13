import asyncio
import os
import json
import time
import re
import hashlib
import sys
import io

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from typing import List, Optional
from urllib.parse import urlparse, urljoin, unquote
import aiohttp
from bs4 import BeautifulSoup
from google import genai
from pydantic import BaseModel, Field
# pyrefly: ignore [missing-import]
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

import trafilatura
import requests

# 🚀 CACHE ALTYAPISI (Fatura Kalkanı)
CACHE_FILE = "crawler_hash_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache_data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

def calculate_md5(text):
    # Metnin dijital parmak izini (Hash) çıkarır
    return hashlib.md5(text.encode('utf-8', errors='ignore')).hexdigest()

# Global Cache Objesi
URL_CACHE = load_cache()

# Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[UYARI] playwright kurulu değil. JS tabanlı sayfalar atlanacak.")

# Dizin Yapılandırması
# Proje kök dizinini sys.path'e ekleyelim ki utils import edilebilsin
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

try:
    from utils.config import INPUTS_DIR, OUTPUTS_DIR, SEED_JSON, AZ_LINKS_JSON, MASTER_JSON, PROCESSED_URLS_JSON
except ImportError:
    # Fallback if config is missing
    INPUTS_DIR = os.path.join(ROOT_DIR, "inputs")
    OUTPUTS_DIR = os.path.join(ROOT_DIR, "public", "outputs")
    SEED_JSON = os.path.join(INPUTS_DIR, "seed_urls.json")
    AZ_LINKS_JSON = os.path.join(INPUTS_DIR, "az_links.json")
    MASTER_JSON = os.path.join(OUTPUTS_DIR, "hybrid_master.json")
    PROCESSED_URLS_JSON = os.path.join(OUTPUTS_DIR, "processed_urls.json")

os.makedirs(INPUTS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

env_path = os.path.join(ROOT_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# ==========================================
# 1. PYDANTIC VERİ MODELLERİ
# ==========================================
class ActionLink(BaseModel):
    intent: str = Field(..., description="Kullanıcıya gösterilecek kısa ve net eylem butonu metni (Örn: Staj Belgelerini İndir, Muafiyet Yönergesini Oku)")
    url: str = Field(..., description="Belgenin veya alt sayfanın tam URL adresi")

class HacettepeEntity(BaseModel):
    is_active: bool = Field(..., description="Büyük idari birimler/fakülteler ve mevzuat sayfaları için HER ZAMAN true. Sadece terk edilmiş küçük projeler/siteler için false.")
    entity_name: str = Field(..., description="Birimin adı (örn: Avrupa Birliği Koordinatörlüğü)")
    category: str = Field(..., description="Rektörlük, Fakülte, İdari Birim, Koordinatörlük, Araştırma Merkezi gibi etiketlerden biri")
    description: str = Field(..., description="LLM tarafından sayfa içeriğinden özetlenmiş kısa bilgi")
    action_links: List[ActionLink] = Field(default=[], description="Kullanıcının doğrudan işini çözeceği derin bağlantılar (Deep Links)")
    announcement_schema: Optional[str] = Field(None, description="Duyuruların bulunduğu HTML bölümünün CSS seçicisi (selector) veya yapısı.")
    sub_branches: List[str] = Field(default=[], description="Eğer sayfa içerisinde alt birimler listeleniyorsa bunların isimleri")

# ==========================================
# 2. YARDIMCI FONKSİYONLAR VE PLAYWRIGHT
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
    # 🚀 İNGİLİZCE KELİMELER EKLENDİ VE DOSYA ADINDA DA ARANMASI SAĞLANDI
    keywords = ['yönerge', 'yönetmelik', 'takvim', 'akademik', 'form', 'mevzuat',
                'directive', 'regulation', 'syllabus', 'internship', 'calendar', 'guide']
    if any(kw in url.lower() or kw in filename.lower() for kw in keywords):
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

PRIORITY_KEYWORDS = [
    "yonerge", "yonetmelik", "esaslar", "mevzuat", "karar", "senato",
    "directive", "regulation", "syllabus", "internship", "erasmus", "exchange", "international"
]

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

def extract_semantic_text(html: str) -> str:
    """Semantic Chunking: Sadece anlamlı etiketleri çıkararak LLM maliyetini düşürür."""
    try:
        temiz_metin = trafilatura.extract(html, include_links=False, include_images=False, include_formatting=False)
        if temiz_metin:
            return temiz_metin[:10000]
    except Exception as e:
        print(f"Trafilatura hatası (semantic): {e}")
    return ""

def get_clean_text_for_llm(raw_html):
    from bs4 import BeautifulSoup
    import re
    
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # 1. Standart çöpleri ve yan menüleri yok et
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "meta", "noscript"]):
        element.decompose()
        
    for noise_div in soup.find_all('div', class_=re.compile(r'menu|sidebar|widget', re.I)):
        noise_div.decompose()

    # 2. İçerik Alanını Avla (Kademeli Fallback)
    content_div = None
    containers = soup.find_all('div', class_=re.compile(r'\bcontainer\b'))
    
    if containers:
        content_div = max(containers, key=lambda c: len(c.get_text(strip=True)))
    else:
        content_div = soup.find(lambda tag: tag.name == "div" and (
            re.search(r'content|icerik|main|govde|sayfa|orta', str(tag.get('class', [])), re.I) or 
            re.search(r'content|icerik|main|govde', str(tag.get('id', '')), re.I)
        ))
    
    # 3. Metni Çıkar (TRAFILATURA ENTEGRASYONU)
    html_to_extract = str(content_div) if content_div else str(soup.body) if soup.body else raw_html
    
    try:
        import trafilatura
        temiz_metin = trafilatura.extract(html_to_extract, include_links=False, include_images=False, include_formatting=False)
        if temiz_metin:
            text = re.sub(r'\s+', ' ', temiz_metin) 
            return text[:3000]
    except Exception as e:
        print(f"Trafilatura hatası (llm): {e}")
        pass
        
    # Trafilatura sonuç veremezse klasik metoda dön
    if content_div:
        text = content_div.get_text(separator=' ', strip=True)
    else:
        text = soup.body.get_text(separator=' ', strip=True) if soup.body else soup.get_text(separator=' ', strip=True)
        
    text = re.sub(r'\s+', ' ', text) 
    return text[:3000]

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

    async def fetch_rendered_data(self, url: str):
        if not self._browser:
            return None
        async with self._semaphore:
            ctx = await self._browser.new_context(ignore_https_errors=True)
            page = await ctx.new_page()
            try:
                # Playwright'ı Hızlandır: Gereksiz assetleri engelle (Two-Phase Optimization)
                await page.route("**/*.{png,jpg,jpeg,gif,css,woff,woff2,svg,ico}", lambda route: route.abort())
                
                # 🚀 TIMEOUT 60 SANİYEYE ÇIKARILDI!
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Sayfayı biraz aşağı kaydır (Lazy load olan linkleri tetiklemek için)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1) # JS'in tepki vermesi için ufak bir bekleme
                
                # 1. Bize RAG için gereken düz metin
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
                
                # 2. Bize Link Avcılığı için gereken TAM RENDER EDİLMİŞ HTML
                html = await page.content()
                
                text_content = content if content and len(content) > 50 else None
                return html, text_content
            except Exception as e:
                # ÇÖKMEYİ ENGELLE, SADECE UYARI VER VE GEÇ
                print(f"[WARN] Playwright çöktü veya zaman aşımı ({url}): {e}")
                return None
            finally:
                await page.close()
                await ctx.close()

_pw_pool: PlaywrightPool | None = None

async def fetch(session, url, semaphore):
    async with semaphore:
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status == 200 and 'text/html' in resp.headers.get('Content-Type', ''):
                    raw_html = await resp.text()
                    
                    soup_quick = BeautifulSoup(raw_html, 'html.parser')
                    body_text = soup_quick.get_text(separator=' ', strip=True)
                    
                    # Eğer sayfa JS ile yükleniyorsa Playwright'ı devreye sok
                    if is_js_candidate(url, body_text) and _pw_pool is not None:
                        rendered_data = await _pw_pool.fetch_rendered_data(url)
                        if rendered_data:
                            rendered_html, js_text = rendered_data
                            return rendered_html, url, js_text
                            
                    # Normal sayfaysa eski usul devam
                    return raw_html, url, None
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

async def crawl_tree_async(start_url, max_pages=150):
    """Deep Crawler bileşeni: BFS ile ağacı tarar ve yeni subdomainleri keşfeder."""
    queue = [start_url]
    visited_pages = set([start_url])
    start_netloc = urlparse(start_url).netloc.lower()
    
    tree_data = {
        "sayfalar": [],
        "dosyalar": [],
        "bilgi_sayfalari": [],
        "discovered_subdomains": set() # Yeni keşfedilen siteler
    }
    
    found_urls = set([start_url])
    priority_visited = 0
    hard_limit = 500 
    
    semaphore = asyncio.Semaphore(30)
    connector = aiohttp.TCPConnector(ssl=False)
    
    seen_hashes = set()
    seen_filenames = {}

    async with aiohttp.ClientSession(connector=connector) as session:
        while queue and (len(visited_pages) <= max_pages or priority_visited < 10):
            if len(visited_pages) > hard_limit: break
            
            batch_size = min(30, len(queue))
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
                    
                    # --- KEŞİF (DISCOVERY) MANTIĞI ---
                    target_netloc = urlparse(full_url).netloc.lower()
                    if target_netloc != start_netloc:
                        # Farklı bir subdomain bulduk
                        if target_netloc.endswith("hacettepe.edu.tr"):
                            new_root = f"https://{target_netloc}"
                            tree_data["discovered_subdomains"].add(new_root)
                        continue 

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

async def fetch_az_links(session: aiohttp.ClientSession) -> List[str]:
    print("[i] A-Z Dizini taranıyor...")
    alphabet = "ABCÇDEFGHIİJKLMNOÖPRSŞTUÜVYZ"
    base_url = "https://www.hacettepe.edu.tr/hakkinda/AZ/"
    all_links = set()
    BLACKLIST_DOMAINS = ["bologna.hacettepe.edu.tr", "arsiv.hacettepe.edu.tr", "egzersizdebeslenme.hacettepe.edu.tr"]
    
    async def fetch_letter(char: str):
        url = f"{base_url}{char}"
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    for a in soup.find_all('a', href=True):
                        href = a['href'].strip()
                        if href.startswith('http'):
                            parsed = urlparse(href)
                            if "hacettepe.edu.tr" in parsed.netloc and not any(b in parsed.netloc for b in BLACKLIST_DOMAINS):
                                if parsed.netloc != "www.hacettepe.edu.tr" and parsed.netloc != "hacettepe.edu.tr":
                                    all_links.add(href.rstrip('/'))
        except Exception as e:
            print(f"[!] {url} alınamadı: {e}")

    tasks = [fetch_letter(char) for char in alphabet]
    await asyncio.gather(*tasks)
    
    links_list = sorted(list(all_links))
    az_file = AZ_LINKS_JSON
    with open(az_file, "w", encoding="utf-8") as f:
        json.dump(links_list, f, ensure_ascii=False, indent=4)
    print(f"[+] Toplam {len(links_list)} link bulundu ve kaydedildi.")
    return links_list

# ==========================================
# 4. CUSTOM LLM PIPELINE (FAZ 2 İÇİN)
# ==========================================
async def extract_entity_data_with_gemma(
    html_content: str, 
    crawled_tree_data: dict, 
    url: str, 
    client: genai.Client, 
    model_name: str,
    sub_pages_markdown: List[str] = None
) -> Optional[dict]:
    
    clean_html = get_clean_text_for_llm(html_content)
    found_pdfs = [f"{d['baslik']} - {d['url']}" for d in crawled_tree_data.get('dosyalar', [])]
    found_pages = [p['baslik'] for p in crawled_tree_data.get('sayfalar', [])][:150] 
    
    prompt = f"""Sen uzman bir Veri Mühendisisin. Aşağıda Hacettepe Üniversitesi'nin bir birimine ait ana sayfanın semantik metni, botumuzun bulduğu önemli alt sayfa içerikleri ve dosyalar yer alıyor.

ÖNEMLİ GÖREVLERİN (GÜVENLİK FİLTRELERİ VE ÇİFT DİL DESTEĞİ):
1. ZAMAN KONTROLÜ (is_active): 
   - DİKKAT: "Öğrenci İşleri (OİDB)", "Daire Başkanlığı", "Fakülte", "Enstitü", "Koordinatörlük" gibi BÜYÜK ve TEMEL idari/akademik birimler, son duyuru tarihi eski olsa dahi KESİNLİKLE TRUE olarak işaretlenmelidir.
   - SADECE sayfa sıradan bir etkinlik, geçici bir proje, veya öğrenci topluluğu izlenimi veriyorsa ve yeni hiçbir hareketlilik yoksa FALSE yap (Zombi site).

2. AKSİYON LİNKLERİ (BILINGUAL DEEP LINKING): Botumuz bu birimin altında yüzlerce sayfa ve PDF buldu. Öğrenciler ve personel için İŞLEM veya BİLGİ niteliği taşıyan **TÜM ÖNEMLİ LİNKLERİ** seç.
   - 🌍 DİKKAT (ÇİFT DİL): Eğer sayfanın hem Türkçe hem İngilizce versiyonu veya belgeleri varsa (Örn: "Staj Yönergesi" ve "Internship Directive"), İKİSİNİ DE AYRI AYRI EKLE! Yabancı öğrenciler için İngilizce belgeleri kesinlikle atlama.
   - Bunları "Staj Yönergesini İncele", "Download Internship Directive" gibi net, tıklanabilir EYLEM (intent) isimleriyle eşleştirerek 'action_links' listesine ekle.

KATEGORİ SEÇİMİ: "Rektörlük", "Fakülte", "Enstitü", "Yüksekokul / Meslek Yüksekokulu", "Bölüm", "Ana Bilim Dalı", "İdari Birim", "Koordinatörlük", "Araştırma Merkezi", "Diğer" arasından seç.

CSS SEÇİCİ KURALI: Duyuruların listelendiği ana <div>/<ul> taşıyıcısının CSS Seçicisini bul (örn: '.news-list'). Yoksa null dön.

BOTUN BULDUĞU ÖNEMLİ DOSYALAR:
{chr(10).join(found_pdfs) if found_pdfs else "Dosya bulunamadı."}

BOTUN BULDUĞU ALT SAYFALAR (İlk 150):
{chr(10).join(found_pages) if found_pages else "Alt sayfa bulunamadı."}

ÖNCELİKLİ ALT SAYFA İÇERİKLERİ (Mevzuat/Hakkımızda vb.):
{chr(10).join(sub_pages_markdown) if sub_pages_markdown else "Ekstra alt sayfa içeriği bulunamadı."}

ANA SAYFA HTML İÇERİĞİ:
{clean_html}

JSON Şeması:
{{
  "is_active": "Boolean",
  "entity_name": "Birimin tam Türkçe adı (Örn: Bilgisayar Mühendisliği Bölümü)",
  "category": "Kategorilerden biri",
  "description": "Sayfanın amacını anlatan 1-2 cümlelik Türkçe bilgi. BUNA EK OLARAK, yabancı öğrencilerin bu birimi bulabilmesi için cümlenin sonuna mutlaka o bölümle ilgili 4-5 adet global İngilizce arama terimi ekle (Örn: computer engineering, syllabus, internship, curriculum, contact).",
  "action_links": [
      {{
          "intent": "Staj Yönergesini İncele",
          "url": "https://..."
      }},
      {{
          "intent": "Download Internship Directive",
          "url": "https://..."
      }}
  ],
  "announcement_schema": "CSS seçicisi",
  "sub_branches": ["Alt bölümler"]
}}

Kurallar:
1. YALNIZCA geçerli bir JSON döndür (Markdown code block içinde).
2. Site URL'si: {url}
"""
    try:
        response = await asyncio.to_thread(client.models.generate_content, model=model_name, contents=prompt)
        text = response.text.strip()
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if match: text = match.group(1)
        else:
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1: text = text[start_idx:end_idx+1]
        
        data = json.loads(text.strip())
        return HacettepeEntity(**data).model_dump()
    except Exception as e:
        print(f"[!] Gemma/JSON Hatası Faz 2 ({url}): {e}")
        return None

# ==========================================
# 5. TWO-PHASE SINGLE HYBRID URL PROCESSOR
# ==========================================
async def process_single_hybrid_url(url: str, crawler: AsyncWebCrawler, client: genai.Client, model_name: str) -> Optional[tuple]:
    try:
        # Sayfayı çek
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, word_count_threshold=15, 
            excluded_tags=['nav', 'footer', 'header', 'script', 'style', 'aside', 'iframe', 'noscript'],
            remove_overlay_elements=True,
            page_timeout=60000 
        )
        result = await crawler.arun(url=url, config=config)

        if not result.success:
            print(f"[WARN] Sayfa çekilemedi: {url}")
            return None, []

        # 🚀 MD5 HASH KONTROLÜ (LLM FATURA KALKANI)
        # Sayfanın text halini al ve parmak izini çıkar
        page_content = result.markdown or result.html or ""
        current_hash = calculate_md5(page_content)

        # Eğer bu URL daha önce işlendiyse ve parmak izi DEĞİŞMEDİYSE:
        if url in URL_CACHE and URL_CACHE[url].get("hash") == current_hash:
            print(f"[⚡ CACHE HIT] {url} değişmemiş! LLM atlanıyor (Maliyet: 0 TL).")
            # Hiç LLM'e gitmeden, dünkü hazır JSON'ı geri dön!
            cached_entry = URL_CACHE[url]
            return cached_entry["data"], cached_entry.get("discovered", [])

        print(f"[🔍 YENİ/DEĞİŞMİŞ SAYFA] {url} analiz ediliyor...")

        # --- FAZ 1: Hızlı Ön İnceleme ---
        phase1_res = result # Use the already fetched result
        if not phase1_res.success:
            return None, []
            
        semantic_html = extract_semantic_text(phase1_res.cleaned_html)
        
        phase1_prompt = f"""Aşağıda Hacettepe Üniversitesi'ne ait bir sayfanın metni var.
Bu sayfa bir Fakülte, Enstitü, Koordinatörlük, Merkez veya Daire Başkanlığı gibi "Kurumsal ve Büyük" bir birim mi? Yoksa alakasız bir proje, kişisel sayfa, tek bir etkinlik veya boş bir arşiv sayfası mı?
Eğer kurumsal, önemli bir birimse TRUE dön.
Eğer sadece bir bireysel laboratuvar, yayın listesi, etkinlik vb. ise FALSE dön.

SAYFA METNİ:
{semantic_html[:3000]}

Sadece geçerli bir JSON dön:
{{ "is_valid_entity": true/false }}
"""
        response_p1 = await asyncio.to_thread(client.models.generate_content, model=model_name, contents=phase1_prompt)
        text_p1 = response_p1.text.strip()
        match_p1 = re.search(r'```(?:json)?\s*(.*?)\s*```', text_p1, re.DOTALL)
        if match_p1: text_p1 = match_p1.group(1)
        else:
            s_idx = text_p1.find('{')
            e_idx = text_p1.rfind('}')
            if s_idx != -1 and e_idx != -1: text_p1 = text_p1[s_idx:e_idx+1]
        
        p1_data = json.loads(text_p1.strip())
        is_valid = p1_data.get("is_valid_entity", False)
        
        # Hardcoded Whitelist (Daire Başkanlıkları vb.)
        subdomain = urlparse(url).netloc.split('.')[0]
        if subdomain.endswith('db') or 'daire' in url.lower() or 'baskanligi' in url.lower():
            is_valid = True
            
        if not is_valid:
            print(f"[-] FAZ 1 Reddedildi (Kurumsal Değil): {url}")
            return {"is_valid_entity": False}, [] # Sadece sinyal dönüyoruz

        print(f"[+] FAZ 1 Onaylandı, Derin Tarama Başlıyor: {url}")
        
        # FAZ 2: Derin Dalış (Deep Dive)
        tree_data = await crawl_tree_async(url, max_pages=150) # Kullanıcının isteğiyle 150
        discovered = list(tree_data.get("discovered_subdomains", []))
        
        priority_keywords = [
            "mevzuat", "yönerge", "yonerge", "yonetmelik", "hakkinda", "tarihce",
            "about", "history", "directive", "regulation", "mission"
        ]
        priority_urls = []
        for page_info in tree_data.get("sayfalar", []):
            if any(k in page_info["url"].lower() for k in priority_keywords):
                priority_urls.append(page_info["url"])
                if len(priority_urls) >= 3: break
                    
        sub_pages_markdown = []
        for p_url in priority_urls:
            p_res = await crawler.arun(url=p_url, config=config)
            if p_res.success:
                sub_pages_markdown.append(f"URL: {p_url}\nİÇERİK:\n{p_res.markdown[:2500]}")
        
        # Faz 2: Geniş çaplı veri çıkarımı
        entity_data = await extract_entity_data_with_gemma(
            phase1_res.html, tree_data, url, client, model_name,
            sub_pages_markdown=sub_pages_markdown
        )
        
        if entity_data:
            entity_data["url"] = url
            entity_data["deep_crawl_files"] = len(tree_data.get("dosyalar", []))
            entity_data["deep_crawl_pages"] = len(tree_data.get("sayfalar", []))
            
            # 🚀 YENİ VERİYİ VE YENİ PARMAK İZİNİ CACHE'E KAYDET
            URL_CACHE[url] = {
                "hash": current_hash,
                "data": entity_data,
                "discovered": discovered
            }
            save_cache(URL_CACHE) # Diske yaz ki yarın hatırlasın
            
            return entity_data, discovered
            
    except Exception as e:
        print(f"[!] Hybrid Hata ({url}): {e}")
    return None, []

# ==========================================
# 6. BATCH PROCESSOR (STATE PERSISTENCE + 2'Lİ MODEL)
# ==========================================
async def crawl_batch(initial_links: List[str]):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: return
    client = genai.Client(api_key=api_key)
    
    model_26b = 'gemma-4-26b-a4b-it'
    model_31b = 'gemma-4-31b-it'
    
    sem_26b = asyncio.Semaphore(6)
    sem_31b = asyncio.Semaphore(6)
    
    # State Persistence: Kaldığımız yeri hatırlama (Resume)
    processed_urls_file = PROCESSED_URLS_JSON
    if os.path.exists(processed_urls_file):
        try:
            with open(processed_urls_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    processed_urls = {u: "Önceki çalışmadan (Sebep bilinmiyor)" for u in data}
                else:
                    processed_urls = data
        except:
            processed_urls = {}
    else:
        processed_urls = {}
        
    discovered_urls = set(initial_links)
    newly_discovered = set()
    results = []
    
    queue = asyncio.Queue()
    for link in initial_links:
        if link not in processed_urls:
            await queue.put(link)
    
    global _pw_pool
    if PLAYWRIGHT_AVAILABLE:
        _pw_pool = PlaywrightPool(concurrency=12)
        await _pw_pool.start()
    
    task_counter = 0

    async def worker():
        nonlocal task_counter
        async with AsyncWebCrawler(verbose=False) as crawler:
            while not queue.empty():
                url = await queue.get()
                if url in processed_urls:
                    queue.task_done()
                    continue
                
                task_counter += 1
                is_26b = (task_counter % 2 == 1)
                
                target_model = model_26b if is_26b else model_31b
                target_sem = sem_26b if is_26b else sem_31b
                model_label = "26b" if is_26b else "31b"

                status_reason = "İşlenemedi / Hata (Timeout vb.)"
                async with target_sem:
                    res_tuple = await process_single_hybrid_url(url, crawler, client, target_model)
                    if res_tuple:
                        entity_data, discovered = res_tuple
                        if entity_data:
                            # Faz 1'den red yediyse is_valid_entity False gelir.
                            is_valid2 = entity_data.get("is_valid_entity", True)
                            is_active2 = entity_data.get("is_active", True)
                            
                            subdomain = urlparse(url).netloc.split('.')[0]
                            if subdomain.endswith('db') or 'daire' in url.lower() or 'baskanligi' in url.lower():
                                is_valid2 = True
                                is_active2 = True
                                
                            if not is_valid2 or not is_active2:
                                status_reason = "Kurumsal değil veya Zombi Site (Reddedildi)"
                            else:
                                entity_data.pop("is_active", None); entity_data.pop("is_valid_entity", None)
                                site_name = urlparse(url).netloc.replace(".", "_")
                                output_path = os.path.join(OUTPUTS_DIR, f"output_{site_name}_hybrid.json")
                                with open(output_path, "w", encoding="utf-8") as f:
                                    json.dump(entity_data, f, ensure_ascii=False, indent=4)
                                print(f"[+] Hybrid Başarılı (FAZ 2) [{model_label}]: {url}")
                                results.append(entity_data)
                                status_reason = "Başarıyla eklendi"
                        
                        for d_url in discovered:
                            if d_url not in discovered_urls and d_url not in processed_urls:
                                discovered_urls.add(d_url)
                                newly_discovered.add(d_url)
                                await queue.put(d_url)
                                print(f"[KEŞİF] Yeni birim bulundu: {d_url}")
                
                # İşlenen URL'i kaydet (Resume)
                processed_urls[url] = status_reason
                with open(processed_urls_file, "w", encoding="utf-8") as f:
                    json.dump(processed_urls, f, ensure_ascii=False, indent=4)
                    
                queue.task_done()

    try:
        print(f"[i] Two-Phase Crawl Modu Başlatıldı. Kuyrukta: {queue.qsize()} birim.")
        workers = [asyncio.create_task(worker()) for _ in range(12)]
        await asyncio.gather(*workers)
    finally:
        if _pw_pool: await _pw_pool.stop()
                
    if results:
        master_file = MASTER_JSON
        # Eğer master file varsa üstüne ekle (Resume logic)
        if os.path.exists(master_file):
            try:
                with open(master_file, "r", encoding="utf-8") as f:
                    old_results = json.load(f)
                results = old_results + results
            except:
                pass
                
        with open(master_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n[+] Tamamlandı! Toplam {len(results)} sonuç kaydedildi.")
        
    if newly_discovered:
        from utils.config import POTENTIAL_NEW_JSON
        potential_file = POTENTIAL_NEW_JSON
        potential_data = [{"url": u, "entity_name": urlparse(u).netloc} for u in newly_discovered]
        with open(potential_file, "w", encoding="utf-8") as f:
            json.dump(potential_data, f, ensure_ascii=False, indent=4)
        print(f"[i] {len(newly_discovered)} yeni potansiyel birim kaydedildi: {potential_file}")

# ==========================================
# 7. ANA AKIŞ
# ==========================================
async def main():
    print("=== Hacettepe Hybrid Two-Phase Crawl Pipeline v4.0 ===")
    
    seed_file = SEED_JSON
    seed_links = []
    
    if os.path.exists(seed_file):
        with open(seed_file, "r", encoding="utf-8") as f:
            seed_links = json.load(f)
    
    if not seed_links:
        print("[i] Liste boş veya bulunamadı, web üzerinden taranıyor...")
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            seed_links = await fetch_az_links(session)

    if seed_links:
        await crawl_batch(seed_links)

if __name__ == "__main__":
    asyncio.run(main())
