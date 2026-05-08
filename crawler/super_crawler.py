import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import urllib.parse
import sys
import io
import os

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

VIP_DOMAINS = ["hacettepe.edu.tr", "oidb.hacettepe.edu.tr", "sksdb.hacettepe.edu.tr", "sporsenligi.hacettepe.edu.tr"]
CRITICAL_KEYWORDS = [
    "ders program", "sınav takvim", "müfredat", "course schedule", 
    "akademik takvim", "yemek menü", "yemek liste", "spor şenli", 
    "fikstür", "staj", "yönetmelik", "formlar", "belgeler", "kayıt"
]

SEED_URLS = [
    "https://cs.hacettepe.edu.tr", 
    "https://sporsenligi.hacettepe.edu.tr",
    "https://beslenme.hacettepe.edu.tr",
    "https://oidb.hacettepe.edu.tr",
    "https://sksdb.hacettepe.edu.tr"
]

def is_critical_link(text):
    text_lower = text.lower().strip()
    return any(keyword in text_lower for keyword in CRITICAL_KEYWORDS)

def extract_links_with_retry(page, url):
    """Sayfaya gitmeyi 3 kez dener"""
    for i in range(3):
        try:
            print(f"   [i] Deneme {i+1}: {url}")
            page.goto(url, timeout=30000, wait_until="networkidle")
            return True
        except Exception as e:
            print(f"   [!] Hata: {e}")
            time.sleep(2)
    return False

def process_page(page, base_url):
    # 1. Artıları Aç (Expand All)
    try:
        if "cs.hacettepe" in base_url:
            page.wait_for_selector("#announcements", timeout=5000)
            triggers = page.locator('#announcements td.details-control')
        else:
            triggers = page.locator('td.details-control')
            
        count = triggers.count()
        if count > 0:
            print(f"   [+] {count} adet gizli satır açılıyor...")
            for i in range(min(count, 20)):
                try:
                    triggers.nth(i).click(force=True)
                except: continue
            page.wait_for_timeout(1000)
    except: pass

    # 2. SAYFADAKİ HTML'İ AL (Artık gizli olan her şey açığa çıktı)
    html_content = page.content()
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 🚨 EKRAN DİLİ KONTROLÜ VE ZORLA TÜRKÇEYE ÇEVİRME
    active_lang_span = soup.find('span', class_='but_lang_secili')
    if active_lang_span:
        current_lang = active_lang_span.get_text(strip=True).upper()
        if current_lang == "EN":
            print(f"   ⚠️ Sayfa İngilizce açıldı. Pes etmiyoruz, TR butonuna basılıyor...")
            try:
                # Ekranda "TR" yazan linki bul ve yapıştır
                tr_button = page.locator("a:has-text('TR'), .but_lang a:has-text('TR')").first
                
                # Eğer tıklanabilir bir TR butonu varsa
                if tr_button.count() > 0:
                    tr_button.click(force=True)
                    page.wait_for_load_state('networkidle') # Türkçe sayfanın yüklenmesini bekle
                    
                    # HTML'İ YENİDEN AL (Çünkü sayfa değişti, yeni menüler geldi)
                    html_content = page.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    print("   🇹🇷 Sayfa başarıyla Türkçe'ye çevrildi, taramaya devam ediliyor.")
            except Exception as e:
                print(f"   ❌ TR'ye çevirirken hata: {e}")

    # 3. Tüm Linkleri Topla
    page_title = soup.title.string.strip() if soup.title else base_url
    
    actions = []
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a['href']
        if text and is_critical_link(text):
            actions.append({
                "intent": text,
                "url": urllib.parse.urljoin(base_url, href)
            })
    return page_title, actions

def run():
    print("🚀 Iron Crawler Başlatılıyor...")
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()

        for url in SEED_URLS:
            print(f"\n🌐 Hedef: {url}")
            if extract_links_with_retry(page, url):
                title, actions = process_page(page, url)
                print(f"   ✅ {title} - {len(actions)} aksiyon yakalandı.")
                results.append({"url": url, "entity_name": title, "action_links": actions})
        
        browser.close()

    with open("outputs/super_crawled_data.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print("\n💾 Bitti. Sonuçlar 'outputs/super_crawled_data.json' içinde.")

if __name__ == "__main__":
    run()
