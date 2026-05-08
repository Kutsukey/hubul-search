"""
fix_hierarchy.py  v7  –  Hızlı ve Güvenli (Parallel 2 Workers)
===========================================================
Rate-limit (15 RPM) aşmadan 2 koldan çalışır.
"""

import json, os, re, sys, time, argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from google import genai
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

INPUT_FILE  = Path(__file__).parent / "hacettepe_entities_master.json"
OUTPUT_FILE = Path(__file__).parent / "hacettepe_tree_ready.json"
MODEL_NAME  = "gemma-4-26b-a4b-it"
MAX_WORKERS = 2 # RPM=15 için 2 worker ideal

def p(msg):
    print(msg, flush=True)

def build_prompt(entity):
    name = entity.get("entity_name", "")
    desc = (entity.get("description", "") or "")[:400]
    return f"""Birim: {name}. Açıklama: {desc}.
Bu bir "Bölüm" veya "Anabilim Dalı" ise bağlı olduğu "Fakülte"yi yaz (Örn: Mühendislik Fakültesi).
Diğer her şey için "Rektörlük" yaz.
SADECE JSON: {{"category": "...", "parent_entity": "..."}}"""

def extract_json(text):
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        return json.loads(text)
    except: return None

def process_item(client, entity, idx):
    name = entity.get("entity_name", "").lower()
    
    # Auto-filter
    llm_required = any(k in name for k in ["bölüm", "bilim dalı", "sanat dalı", "programı", "dalı"])
    if not llm_required:
        if any(k in name for k in ["müşavirliği", "başkanlığı", "müdürlüğü", "ofisi", "koordinatörlüğü", "merkezi", "fakültesi", "enstitüsü"]):
            entity["parent_entity"] = "Rektörlük"
            p(f"  [{idx+1}] (Auto) {entity['entity_name'][:40]:40s} -> Rektörlük")
            return idx

    # LLM
    try:
        time.sleep(4.5) # Worker başına 4.5s = toplam 2.25s per request (~26 RPM). 
        # Hmm, 26 RPM çok. 2 worker için 8 saniye sleep yapalım ki 15 RPM olsun.
        time.sleep(8.0) 
        resp = client.models.generate_content(model=MODEL_NAME, contents=build_prompt(entity))
        data = extract_json(resp.text)
        if data:
            entity.update(data)
            p(f"  [{idx+1}] (LLM)  {entity['entity_name'][:40]:40s} -> {data.get('parent_entity')}")
        return idx
    except Exception as e:
        return idx

def main():
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        entities = json.load(f)

    p(f"🚀 Hiyerarşi (V7 Parallel) başlıyor: {len(entities)} birim")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(process_item, client, entities[i], i): i for i in range(len(entities))}
        for _ in as_completed(futures): pass

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
    p("✅ BİTTİ!")

if __name__ == "__main__":
    main()
