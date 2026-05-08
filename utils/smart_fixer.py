import json
import os
import sys
import io

# Windows Console UTF-8 Fix
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MASTER_JSON = "outputs/hybrid_master.json"
HALLUCINATIONS_JSON = "outputs/flagged_hallucinations.json"

def smart_fix():
    print("🛠️ Smart Fixer Başlatılıyor... Halüsinasyonlar temizleniyor.")
    
    if not os.path.exists(MASTER_JSON) or not os.path.exists(HALLUCINATIONS_JSON):
        print("[!] Gerekli dosyalar bulunamadı.")
        return

    with open(MASTER_JSON, 'r', encoding='utf-8') as f:
        master_data = json.load(f)
        
    with open(HALLUCINATIONS_JSON, 'r', encoding='utf-8') as f:
        flagged_items = json.load(f)

    # Kolay erişim için bir harita oluştur (URL -> Gerçek İsim)
    fix_map = {item["url"]: item["actual_title"] for item in flagged_items}
    
    fixed_count = 0
    skipped_count = 0
    
    for entity in master_data:
        url = entity.get("url")
        if url in fix_map:
            actual = fix_map[url]
            
            # FİLTRE: Çok genel veya anlamsız isimleri atla
            black_list = ["giriş", "home", "ana sayfa", "hacettepe", "http", "faculty of test"]
            is_generic = any(x in actual.lower() for x in black_list)
            
            if not is_generic and len(actual) > 3:
                # LLM ismini yedekle ve güncelle
                old_name = entity["entity_name"]
                entity["entity_name"] = actual
                print(f"[✓] Düzeltildi: {old_name} -> {actual}")
                fixed_count += 1
            else:
                print(f"[!] Atlandı (Genel İsim): {actual}")
                skipped_count += 1
                
    # Sonuçları kaydet
    with open(MASTER_JSON, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ İşlem Tamamlandı!")
    print(f"📊 Toplam Düzeltilen: {fixed_count}")
    print(f"📊 Atlanan (Güvenli): {skipped_count}")

if __name__ == "__main__":
    smart_fix()
