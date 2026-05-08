import json
import os
from google import genai

# Dizin Ayarları (Kendi klasör yapına göre kontrol et)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_JSON = os.path.join(BASE_DIR, "inputs", "seed_urls.json")
POTENTIAL_NEW = os.path.join(BASE_DIR, "outputs", "potential_new_sites.json") # Crawler'ın yeni buldukları

def ai_gatekeeper():
    print("🤖 AI Gatekeeper Devrede: Yeni keşifler sorgulanıyor...")
    
    if not os.path.exists(POTENTIAL_NEW):
        print("[-] İncelenecek yeni site bulunmadı. Gatekeeper uyumaya devam ediyor.")
        return

    # API Key'i Actions Secrets'tan alacak
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    with open(POTENTIAL_NEW, 'r', encoding='utf-8') as f:
        new_sites = json.load(f)

    if not os.path.exists(SEED_JSON):
        seed_urls = []
    else:
        with open(SEED_JSON, 'r', encoding='utf-8') as f:
            seed_urls = json.load(f)
    
    existing_urls = [s.get("url") if isinstance(s, dict) else s for s in seed_urls]
    approved_count = 0
    
    for site in new_sites:
        url = site.get("url")
        title = site.get("entity_name", "Bilinmeyen Birim")

        # Eğer zaten seed listesindeyse atla
        if url in existing_urls:
            continue

        prompt = f"""
        Aşağıdaki Hacettepe Üniversitesi bağlantısını incele:
        URL: {url}
        BAŞLIK: {title}

        Bu site kalıcı bir akademik birim, fakülte, bölüm, enstitü veya uygulama merkezi mi? 
        Yoksa geçici bir sempozyum, konferans, duyuru sayfası, etkinlik veya öğrenci topluluğu mu?
        
        Sadece kalıcı ve resmi eğitim/idari birimler için 'ONAY' yaz. 
        Geçici, kişisel veya önemsiz sayfalar için 'RED' yaz.
        Cevabın SADECE bu iki kelimeden biri olsun. Başka hiçbir açıklama yapma.
        """

        try:
            response = client.models.generate_content(model="gemma-4-31b-it", contents=prompt)
            decision = response.text.strip().upper()

            if "ONAY" in decision:
                # Onaylananları Seed listesine ekle
                seed_urls.append({"entity_name": title, "url": url, "action_links": []})
                existing_urls.append(url)
                approved_count += 1
                print(f"[✓] KABUL EDİLDİ: {title} ({url})")
            else:
                print(f"[X] REDDEDİLDİ (Geçici/Gereksiz): {title}")
        except Exception as e:
            print(f"[!] Hata oluştu ({title}): {e}")
            continue

    # Güncellenmiş listeyi kaydet
    os.makedirs(os.path.dirname(SEED_JSON), exist_ok=True)
    with open(SEED_JSON, 'w', encoding='utf-8') as f:
        json.dump(seed_urls, f, ensure_ascii=False, indent=4)
    
    # İşlenen dosyayı sıfırla ki haftaya aynılarını sormasın
    with open(POTENTIAL_NEW, 'w', encoding='utf-8') as f:
        json.dump([], f)

    print(f"✅ Görev Tamam! {approved_count} yeni birim otonom olarak sisteme entegre edildi.")

if __name__ == "__main__":
    ai_gatekeeper()
