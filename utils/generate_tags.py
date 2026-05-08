import json
import asyncio
import os
import sys
from google import genai
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

# .env dosyasını yükle (API Key için)
load_dotenv()

INPUT_FILE = "hacettepe_tree_ready.json"
OUTPUT_FILE = "hacettepe_tree_tagged.json"
MODEL_NAME = "gemma-4-31b-it"

async def generate_tags_for_entity(entity: dict, client: genai.Client, semaphore: asyncio.Semaphore):
    async with semaphore:
        prompt = f"""Sen Hacettepe Üniversitesi'nde okuyan panik halinde, işini hızlıca çözmek isteyen bir öğrencisin. 
Aşağıdaki resmi birimin adını ve özetini okuyup, bir öğrencinin bu birime ulaşmak için arama çubuğuna yazacağı en yaygın 5 ile 8 adet "Görev Odaklı" anahtar kelimeyi (tag) üret.

Kurum Adı: {entity.get('entity_name')}
Açıklama: {entity.get('description')}
Kategorisi: {entity.get('category')}

KURALLAR:
1. Asla resmi kurum adını tam olarak tekrar etme. 
2. Niyeti (Intent) yakala. Ne yapmak istiyor? (Örn: belge almak, para ödemek, itiraz etmek).
3. Hacettepe argosunu ve kısaltmalarını kullan (Örn: çap, yandal, not dökümü, ring saatleri, kkm, mediko, tek ders).
4. Çıktı SADECE küçük harflerle yazılmış bir JSON string dizisi (array) olmalıdır. Başka hiçbir açıklama metni veya markdown karakteri (```json) EKLEME.

ÖRNEK ÇIKTI:
["yemekhane menüsü", "burs başvurusu", "mediko randevu", "öğrenci toplulukları", "kısmi zamanlı"]
"""
        try:
            # Yapılandırılmış JSON çıktısı almak için model ayarları
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=MODEL_NAME,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.7, # Yaratıcı argolar üretmesi için biraz yüksek
                    response_mime_type="application/json",
                )
            )
            
            # API'den gelen JSON formatındaki stringi Python listesine çevir
            tags = json.loads(response.text.strip())
            
            # Entity'e tags alanını ekle
            entity["tags"] = tags
            print(f"[+] Etiketlendi: {entity.get('entity_name')}\n    Tags: {tags}\n", flush=True)
            
            # API free-tier limiti (15 RPM) için bekleme süresi
            await asyncio.sleep(4.5)
            return entity
            
        except Exception as e:
            print(f"[-] Hata ({entity.get('entity_name')}): {e}")
            entity["tags"] = [] # Hata olursa boş liste ata, sistemi durdurma
            return entity

async def main():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] Hata: GOOGLE_API_KEY bulunamadı.")
        return

    client = genai.Client(api_key=api_key)
    
    if not os.path.exists(INPUT_FILE):
        print(f"[!] Hata: {INPUT_FILE} bulunamadı.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        entities = json.load(f)

    print(f"[i] Toplam {len(entities)} birim için Görev Odaklı etiketler (tags) üretiliyor...")
    
    # API limitlerine takılmamak için eşzamanlı istek sayısını düşürdük (gemma-4 free tier limiti 15 RPM)
    semaphore = asyncio.Semaphore(1) 
    tasks = [generate_tags_for_entity(entity, client, semaphore) for entity in entities]
    
    updated_entities = await asyncio.gather(*tasks)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_entities, f, ensure_ascii=False, indent=4)
        
    print(f"\n[✓] İşlem tamam! Yeni veri seti '{OUTPUT_FILE}' olarak kaydedildi.")

if __name__ == "__main__":
    asyncio.run(main())
