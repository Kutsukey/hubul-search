import json
import os
import sys
import io
from google import genai

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Dizin Ayarları
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Crawler artık seed_urls.json kullanıyor
SEED_JSON = os.path.join(BASE_DIR, "inputs", "seed_urls.json")
POTENTIAL_NEW = os.path.join(BASE_DIR, "public", "outputs", "potential_new_sites.json")

def ai_gatekeeper():
    print("🤖 AI Gatekeeper: Yeni keşifler sorgulanıyor...")
    
    if not os.path.exists(POTENTIAL_NEW):
        print("[-] İncelenecek yeni site bulunmadı.")
        return

    # Proje standartlarına uygun GOOGLE_API_KEY kullanımı
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] Hata: GOOGLE_API_KEY bulunamadı.")
        return

    client = genai.Client(api_key=api_key)
    # Kullanıcının özellikle istediği gemma modeli
    model_name = "gemma-4-26b-a4b-it"
    
    with open(POTENTIAL_NEW, 'r', encoding='utf-8') as f:
        new_sites = json.load(f) 

    if not os.path.exists(SEED_JSON):
        seed_urls = []
    else:
        with open(SEED_JSON, 'r', encoding='utf-8') as f:
            seed_urls = json.load(f)
    
    approved_count = 0
    
    for site in new_sites:
        url = site.get("url")
        title = site.get("entity_name", "İsimsiz Birim")

        # Zaten seed listesinde varsa atla
        if any(s.get('url') == url for s in seed_urls if isinstance(s, dict)) or url in seed_urls:
            continue

        prompt = f"""
        Aşağıdaki Hacettepe Üniversitesi bağlantısını incele:
        URL: {url}
        BAŞLIK: {title}

        Bu site kalıcı bir akademik birim, fakülte, bölüm veya uygulama merkezi mi? 
        Yoksa geçici bir sempozyum, konferans, duyuru sayfası veya 'zattirizurt' etkinliği mi?
        
        Sadece kalıcı ve önemli birimler için 'ONAY' yaz. 
        Geçici, kişisel veya önemsiz sayfalar için 'RED' yaz.
        Cevabın sadece bu iki kelimeden biri olsun.
        """

        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            decision = response.text.strip().upper()

            if "ONAY" in decision:
                # Seed listesine ekle
                # az_links.json formatı bir liste (string veya dict olabilir, crawler dict bekliyor genelde)
                seed_urls.append(url) # Crawler hem list[str] hem list[dict] destekliyor gibi ama main'de fetch_az_links str listesi döner
                approved_count += 1
                print(f"[✓] ONAYLANDI: {title} ({url})")
            else:
                print(f"[X] REDDEDİLDİ: {title}")
        except Exception as e:
            print(f"[!] Hata ({url}): {e}")
            continue

    # Güncellenmiş seed listesini kaydet
    with open(SEED_JSON, 'w', encoding='utf-8') as f:
        json.dump(seed_urls, f, ensure_ascii=False, indent=4)
    
    # İşlenen dosyayı temizle veya işaretle
    try:
        os.remove(POTENTIAL_NEW)
    except:
        pass
        
    print(f"✅ İşlem bitti! {approved_count} yeni birim otonom olarak seed listesine eklendi.")

if __name__ == "__main__":
    ai_gatekeeper()
