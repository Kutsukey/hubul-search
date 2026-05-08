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
MASTER_JSON = os.path.join(BASE_DIR, "public", "outputs", "hybrid_master.json")
REPORT_JSON = os.path.join(BASE_DIR, "public", "outputs", "validation_report.json")

def validate_data():
    print("⚖️ Savcı LLM Devreye Giriyor: Niyetler sorgulanıyor...")
    
    # Proje standartlarına uygun olarak GOOGLE_API_KEY kullanılıyor
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] Hata: GOOGLE_API_KEY bulunamadı.")
        return

    client = genai.Client(api_key=api_key)
    
    if not os.path.exists(MASTER_JSON):
        print(f"[!] Hata: {MASTER_JSON} bulunamadı.")
        return

    with open(MASTER_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    report = []
    
    # Çok fazla veri olduğu için 20'li paketler halinde LLM'e gönderiyoruz
    # Sınırı aşmamak için hızı kontrol ediyoruz
    for i in range(0, len(data), 20):
        chunk = data[i:i+20]
        payload = []
        for item in chunk:
            intents = [a.get("intent") for a in item.get("action_links", [])]
            if intents:
                payload.append({
                    "entity": item.get("entity_name"),
                    "intents": intents
                })

        if not payload:
            continue

        prompt = f"""
        Sen bir kalite denetçisisin. Aşağıdaki üniversite birimleri ve onlara bağlı 'niyetleri' (intent) incele.
        Hatalı olanları (anlamsız kelimeler, kurumla alakasız işler, bozuk Türkçe, LLM halüsinasyonları) tespit et.
        YALNIZCA şu formatta bir JSON listesi döndür, başka açıklama yapma:
        [ {{"entity": "...", "bad_intent": "...", "reason": "..."}} ]

        Eğer her şey düzgünse boş liste döndür: []

        VERİ:
        {json.dumps(payload, ensure_ascii=False)}
        """

        try:
            # Model ismi proje standartlarına uygun (gemini-2.0-flash veya gemma varyantı seçilebilir, flash hız için ideal)
            response = client.models.generate_content(model="gemma-4-26b-a4b-it", contents=prompt)
            if response.text:
                text = response.text.strip()
                # Markdown bloklarını temizle
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                
                findings = json.loads(text)
                if isinstance(findings, list):
                    report.extend(findings)
                print(f"[*] {min(i+20, len(data))} birim denetlendi... Bulunan hata: {len(findings)}")
        except Exception as e:
            print(f"[!] Paket işlenirken hata: {e}")

    with open(REPORT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Denetim tamamlandı! {len(report)} adet şüpheli durum raporlandı.")
    print(f"📁 Rapor: {REPORT_JSON}")

if __name__ == "__main__":
    validate_data()
