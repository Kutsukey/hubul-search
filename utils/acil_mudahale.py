import json
import os

def heal_json():
    print("Ambulans geldi, yarali kelimeler araniyor...")
    
    # Hedef dosyalari listele
    targets = [
        "public/outputs/hybrid_master.json",
        "hacettepe_ia_pipeline/outputs/hybrid_master.json"
    ]
    
    for file_path in targets:
        if not os.path.exists(file_path):
            print(f"UYARI: {file_path} bulunamadi, geciliyor...")
            continue

        print(f"INCELENIYOR: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        healed_count = 0
        
        for item in data:
            if "action_links" in item:
                for link in item["action_links"]:
                    intent = link.get("intent", "")
                    original_intent = intent
                    
                    # Önce hatalı katmerli düzeltmeleri (GörGörüntüle) temizle
                    if "GörGörüntüle" in intent:
                        intent = intent.replace("GörGörüntüle", "Görüntüle")
                    
                    # 1. "üntüle" faciasini düzelt (Sadece Görüntüle yoksa yap)
                    if "üntüle" in intent and "Görüntüle" not in intent:
                        intent = intent.replace("üntüle", "Görüntüle")
                        
                    # 2. "Ok" faciasini düzelt
                    if (intent.endswith(" Ok") or intent.endswith(" ok")) and not intent.endswith(" Oku"):
                        intent = intent + "u"

                    # 3. " ni İncele/Oku" gibi bağlaç hatalarını düzelt
                    if " ni İncele" in intent:
                        intent = intent.replace(" ni İncele", "nu İncele")
                    if " ni Oku" in intent:
                        intent = intent.replace(" ni Oku", "nu Oku")
                    if " ni Görüntüle" in intent:
                        intent = intent.replace(" ni Görüntüle", "nu Görüntüle")
                    
                    # 4. "İletişim ne Ulaş" -> "İletişime Ulaş"
                    if "İletişim ne Ulaş" in intent:
                        intent = intent.replace("İletişim ne Ulaş", "İletişime Ulaş")
                    
                    # 5. "Staj ni" -> "Staj Bilgilerini"
                    if "Staj ni" in intent:
                        intent = intent.replace("Staj ni", "Staj Bilgilerini")

                    # Eğer değişiklik yapıldıysa JSON'a kaydet
                    if original_intent != intent:
                        link["intent"] = intent
                        healed_count += 1
                        # print output might be too long, but let's keep a sample
                        if healed_count < 20:
                            print(f"   TEDAVI EDILDI: '{original_intent}' -> '{intent}'")

        if healed_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"OK: {file_path} icin operasyon basarili! {healed_count} adet iyilesirme yapildi.")
        else:
            print(f"INFO: {file_path} icinde yarali kelimeye rastlanmadi.")

    print(f"\nTum operasyonlar tamamlandi.")

if __name__ == "__main__":
    heal_json()
