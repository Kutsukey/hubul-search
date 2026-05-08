import json
import os
import re
from collections import defaultdict

def extract_base_intent(intent):
    """Yılları temizleyip kelimenin özünü bulur."""
    return re.sub(r'\b(20\d{2})\b', '', intent).strip().lower()

def filter_outdated_links(action_links):
    temp_links = []
    
    for link in action_links:
        intent = link.get("intent", "")
        # Yazı içindeki tüm 20XX yıllarını bul
        years = [int(y) for y in re.findall(r'\b(20\d{2})\b', intent)]
        max_year = max(years) if years else 0
        
        # KURAL 1: İsmi 2021 ve öncesi olan her şeyi acımadan sil
        if 0 < max_year <= 2021:
            continue
            
        # KURAL 2: 2025 ve öncesi süreli (staj, burs vb.) şeyleri sil
        intent_lower = intent.lower()
        if 0 < max_year <= 2025:
            if any(kw in intent_lower for kw in ["staj", "burs", "başvuru", "basvuru", "kayıt", "yaz okulu", "sonuç"]):
                continue
                
        temp_links.append(link)
        
    # KURAL 3: Aynı isimdeki evrakların sadece EN GÜNCELİNİ tut
    grouped_links = defaultdict(list)
    for link in temp_links:
        base = extract_base_intent(link.get("intent", ""))
        grouped_links[base].append(link)
        
    final_links = []
    for base, links in grouped_links.items():
        if not base or base == "":
            final_links.extend(links)
            continue
            
        # Gruptaki en yüksek yılı bul
        max_group_year = 0
        for l in links:
            yrs = [int(y) for y in re.findall(r'\b(20\d{2})\b', l.get("intent", ""))]
            if yrs and max(yrs) > max_group_year:
                max_group_year = max(yrs)
                
        for l in links:
            yrs = [int(y) for y in re.findall(r'\b(20\d{2})\b', l.get("intent", ""))]
            link_max_year = max(yrs) if yrs else 0
            
            # Eğer linkin yılı, gruptaki en yüksek yıldan küçükse -> ÇÖP
            if 0 < link_max_year < max_group_year:
                print(f"   [v] Eski Versiyon Silindi: {l.get('intent')}")
            else:
                final_links.append(l)
                
    return final_links

# LLM'in kafasının karıştığı siteler ve ÖLÜ SİTELER için Kesin Kurallar
HARDCODED_OVERRIDES = {
    "cocuk.hacettepe.edu.tr": "Çocuk Sağlığı ve Hastalıkları Uygulama ve Araştırma Merkezi",
    "otk.hacettepe.edu.tr": "DELETE", # Konsey aktif değil, SİL GİTSİN!
    "yurt.hacettepe.edu.tr": "DELETE", # Barınma olarak güncellendi, eski URL'i siliyoruz
    "cs.hacettepe.edu.tr": "Bilgisayar Mühendisliği ve Yapay Zeka Mühendisliği Bölümü",
    "egitim-bulteni.hacettepe.edu.tr": "DELETE"
}

def clean_and_merge_json(file_path):
    print(f"[i] {file_path} temizligi ve infaz operasyonu basliyor...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. ASAMA: ISIM DUZELTME VE INFAZ (Hard Delete)
    survived_data = []
    for item in data:
        url = item.get("url", "")
        should_delete = False
        
        for override_url, correct_name in HARDCODED_OVERRIDES.items():
            if override_url in url:
                if correct_name == "DELETE":
                    should_delete = True
                    print(f"[-] Cop Kutusuna Atildi: {url}")
                    break
                else:
                    item["entity_name"] = correct_name
        
        if not should_delete:
            # Varsayılan olarak is_active: true ekle (eğer yoksa)
            if "is_active" not in item:
                item["is_active"] = True
            survived_data.append(item)

    # 2. AŞAMA: URL BAZLI TEKİLLEŞTİRME (Merging)
    merged_data = {}

    for item in survived_data:
        if not item.get("entity_name"):
            continue

        # 🛡️ OTORİTE FİLTRESİ: OİDB dışındaki birimlerde "Akademik Takvim" linklerini temizle
        if "oidb.hacettepe.edu.tr" not in item.get("url", ""):
            item["action_links"] = [a for a in item.get("action_links", []) if "akademik takvim" not in a.get("intent", "").lower()]

        # 🧹 ÇİRKİN LİNK VE ESKİ CS LİNKLERİ TEMİZLİĞİ
        if item.get("action_links"):
            item["action_links"] = [
                a for a in item["action_links"] 
                if not a.get("intent", "").startswith("http") and 
                "muhfak.hacettepe.edu.tr/tr/menu/yararli_belgeler-178" not in a.get("url", "") and
                "intern.cs.hacettepe.edu.tr" not in a.get("url", "") # Eski CS Staj linklerini sil
            ]
            
            # 🎯 CS ÖZEL MODERNİZASYON (İsimleri güzelleştir ve tekilleştir)
            if "cs.hacettepe.edu.tr" in item.get("url", ""):
                modernized_links = []
                seen_intents = set()
                for a in item["action_links"]:
                    url = a.get("url", "")
                    if "#courseschedule_undergraduate" in url:
                        a["intent"] = "Lisans Ders Programı (CS/AI)"
                    elif "#curriculum_ce" in url:
                        a["intent"] = "Bilgisayar Müh. Müfredatı"
                    elif "#curriculum_ai" in url:
                        a["intent"] = "Yapay Zeka Müh. Müfredatı"
                    elif "#awards" in url:
                        a["intent"] = "Ödüller ve Başarılar"
                    elif "#courseschedule_graduate" in url: # Graduate programını siliyoruz (Talep üzerine)
                        continue
                        
                    if a["intent"] not in seen_intents:
                        modernized_links.append(a)
                        seen_intents.add(a["intent"])
                item["action_links"] = modernized_links

        # URL'yi standartlaştır (www, http, https temizle)
        raw_url = item.get("url", "")
        url_key = raw_url.replace("https://", "").replace("http://", "").replace("www.", "").replace("/", "").strip().lower()
        
        # İsmi standartlaştır
        raw_name = item.get("entity_name", "")
        name_key = raw_name.lower().replace("hacettepe üniversitesi", "").replace("hacettepe", "").strip()
        
        # www temizliği için birincil anahtar URL olmalı
        # Eğer URL yoksa isme güveniyoruz
        merge_key = url_key if url_key else f"no_url_{name_key}"

        if merge_key in merged_data:
            # Aynı isimde kurum bulundu! Linkleri birleştiriyoruz.
            existing_item = merged_data[merge_key]
            
            # Eski ve yeni linkleri aynı havuza at
            all_links = existing_item.get("action_links", []) + item.get("action_links", [])

            # Linkleri "intent" (isim) bazında tekilleştir (Aynı linkten 2 tane olmasın)
            unique_links = {}
            for link in all_links:
                link_intent_key = link.get("intent", "").lower().strip()
                if link_intent_key not in unique_links:
                    unique_links[link_intent_key] = link

            # Temizlenmiş linkleri eski kuruma geri yükle
            existing_item["action_links"] = list(unique_links.values())

            # Derin tarama istatistiklerini topla (Emeğimiz boşa gitmesin)
            existing_item["deep_crawl_pages"] = existing_item.get("deep_crawl_pages", 0) + item.get("deep_crawl_pages", 0)
            existing_item["deep_crawl_files"] = existing_item.get("deep_crawl_files", 0) + item.get("deep_crawl_files", 0)

        else:
            # Kurum ilk defa geliyorsa haritaya doğrudan ekle
            merged_data[merge_key] = item

    # Sözlükteki değerleri tekrar JSON listesine çevir
    final_list = list(merged_data.values())
    # 3. AŞAMA: YEDEKLEME VE ÜZERİNE YAZMA
    backup_path = file_path.replace(".json", "_backup.json")
    
    # Eğer daha önceden yedek varsa onu sil ki hata vermesin
    if os.path.exists(backup_path):
        os.remove(backup_path)
        
    os.rename(file_path, backup_path)

    # 3. AŞAMA: TARİH VE VERSİYON FİLTRESİ (Nuclear Cleanup)
    for merge_key, item in merged_data.items():
        if "action_links" in item:
            item["action_links"] = filter_outdated_links(item["action_links"])

    # Sözlükteki değerleri tekrar JSON listesine çevir
    final_list = list(merged_data.values())
    
    # Sonuçları kaydet
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, ensure_ascii=False, indent=4)
    
    print(f"Veritabanı temizliği kusursuz tamamlandı!")
    print(f"Temizlik öncesi satır sayısı: {len(data)}")
    print(f"Birleştirme sonrası net kurum sayısı: {len(final_list)}")
    print(f"Orijinal çöp verin şuraya yedeklendi: {backup_path}")

# Scripti Ateşle
if __name__ == "__main__":
    # Proje kök dizinini baz alarak yolu belirle
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    target_file = os.path.join(project_root, "public", "outputs", "hybrid_master.json")
    
    if os.path.exists(target_file):
        clean_and_merge_json(target_file)
    else:
        print(f"HATA: {target_file} dosyası bulunamadı. Lütfen 'public/outputs/' dizinini kontrol edin.")
