import json
import requests
from bs4 import BeautifulSoup
import difflib
import urllib3
import os
import sys
import io

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# SSL hatalarını gizle (Üniversite sitelerinde çok olur)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Metin benzerlik oranını hesaplayan fonksiyon
def get_similarity(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

# İsimleri karşılaştırmadan önce temizleyen fonksiyon
def clean_text(text):
    if not text: return ""
    return text.lower().replace("hacettepe üniversitesi", "").replace("hacettepe", "").replace("-", "").strip()

def run_title_detective(file_path):
    print("🔍 Title Dedektifi Çalışıyor... Sitelere hızlıca bakılıyor.\n")
    
    if not os.path.exists(file_path):
        print(f"HATA: {file_path} bulunamadı.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    flagged_items = []
    
    # Çok yavaşlamamak için limitli bir eşzamanlılık yerine seri ama hızlı gidiyoruz
    for item in data:
        url = item.get("url")
        llm_name = item.get("entity_name", "")
        
        if not url or url == "#" or not llm_name:
            continue
            
        try:
            # Sadece siteye girip çıkıyoruz, 5 saniye bekleme süresi
            response = requests.get(url, timeout=5, verify=False)
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Kaynak: <title> etiketi
            title_tag = soup.title
            page_title = title_tag.string.strip() if title_tag and title_tag.string else ""
            
            # 2. Kaynak: .banner_uni_bolum div'i (Hacettepe özel yapısı)
            banner_div = soup.select_one(".banner_uni_bolum")
            banner_text = banner_div.get_text(strip=True) if banner_div else ""
            
            # Gerçek ismi belirle: Banner varsa daha güvenilirdir
            actual_title = banner_text if banner_text else page_title
            
            if not actual_title:
                continue

            # İsimleri temizle ve karşılaştır
            clean_llm = clean_text(llm_name)
            clean_title = clean_text(actual_title)
            
            # Eğer kelimeler birbirinin içinde geçmiyorsa ve benzerlik %40'ın altındaysa yakala!
            if clean_llm not in clean_title and clean_title not in clean_llm:
                sim_score = get_similarity(clean_llm, clean_title)
                
                if sim_score < 0.4:
                    print(f"🚨 ŞÜPHELİ BULUNDU: {url}")
                    print(f"   🤖 LLM'in Uydurduğu: {llm_name}")
                    print(f"   🌐 Gerçek Title:     {actual_title}\n")
                    sys.stdout.flush()
                    
                    flagged_items.append({
                        "url": url,
                        "llm_name": llm_name,
                        "actual_title": actual_title
                    })
                    
        except Exception as e:
            # Site ölmüşse veya çok yavaşsa buraya düşer
            pass

    print(f"\n✅ Tarama Bitti! Toplam {len(flagged_items)} adet potansiyel halüsinasyon yakalandı.")
    
    # Raporu JSON olarak kaydet
    if flagged_items:
        output_path = "outputs/flagged_hallucinations.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(flagged_items, f, ensure_ascii=False, indent=4)
        print(f"📁 Hatalı kayıtlar '{output_path}' dosyasına kaydedildi.")

if __name__ == "__main__":
    run_title_detective("outputs/hybrid_master.json")
