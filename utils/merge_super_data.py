import json
import os
import sys
import io

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Dizin Ayarları
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER_JSON = os.path.join(BASE_DIR, "public", "outputs", "hybrid_master.json")
SUPER_DATA_JSON = os.path.join(BASE_DIR, "public", "outputs", "super_crawled_data.json")

def merge_super_data():
    print("🧬 Veri Birleştirme (Smart Merge) Başlatılıyor...")
    
    if not os.path.exists(MASTER_JSON) or not os.path.exists(SUPER_DATA_JSON):
        print("[!] Gerekli dosyalar bulunamadı.")
        return

    with open(MASTER_JSON, 'r', encoding='utf-8') as f:
        master_data = json.load(f)
        
    with open(SUPER_DATA_JSON, 'r', encoding='utf-8') as f:
        super_data = json.load(f)

    # Kolay erişim için bir harita oluştur (URL -> Super Item)
    super_map = {item["url"]: item for item in super_data}
    
    merged_count = 0
    new_actions_count = 0
    
    for entity in master_data:
        url = entity.get("url")
        if url in super_map:
            super_item = super_map[url]
            
            # 1. İsim Güncelleme (Super Crawler başlığı daha günceldir)
            if super_item.get("entity_name"):
                entity["entity_name"] = super_item["entity_name"]
            
            # 2. Aksiyon Linklerini Birleştir (Tekilleştirerek)
            existing_actions = entity.get("action_links", [])
            new_actions = super_item.get("action_links", [])
            
            # URL bazlı tekilleştirme
            action_urls = {a["url"]: a for a in existing_actions}
            for na in new_actions:
                if na["url"] not in action_urls:
                    action_urls[na["url"]] = na
                    new_actions_count += 1
            
            entity["action_links"] = list(action_urls.values())
            merged_count += 1
            
    # Sonuçları kaydet
    with open(MASTER_JSON, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Birleştirme Tamamlandı!")
    print(f"📊 Güncellenen Birim Sayısı: {merged_count}")
    print(f"📊 Eklenen Yeni Kritik Link Sayısı: {new_actions_count}")

if __name__ == "__main__":
    merge_super_data()
