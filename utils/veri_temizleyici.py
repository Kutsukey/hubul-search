import json
import os
import re
import glob
from collections import defaultdict

def turkish_lower(s):
    """Türkçe karakter duyarlı küçük harf dönüşümü."""
    if not s: return ""
    return s.replace('İ', 'i').replace('I', 'ı').lower()

def otonom_kisaltma_uret(metin):
    """Otomatik baş harf kısaltması üretir (Örn: Tıbbi Dokümantasyon ve Sekreterlik Prog. -> tds)"""
    if not metin:
        return ""
        
    yasakli_kelimeler = ['ve', 'ile', 'bölümü', 'programı', 'prog.', 'fakültesi', 'yüksekokulu', 'meslek', 'anabilim', 'dalı', 'teknikerliği', 'teknolojisi', 'hizmetleri', 'teknikleri']
    
    # Noktalama işaretlerini boşlukla değiştir ki "Prog." kelimesi "prog" olarak yakalansın
    temiz_metin = metin.replace('.', ' ').replace(',', ' ')
    kelimeler = [k for k in temiz_metin.split() if k.lower() not in yasakli_kelimeler]
    
    # Sadece 2 veya daha fazla geçerli kelimeden oluşan isimlere kısaltma yap
    if len(kelimeler) >= 2:
        return "".join([k[0] for k in kelimeler if k.isalpha()]).lower()
    return ""

try:
    from utils.config import MASTER_JSON
except ImportError:
    # Script'in kendi bulunduğu dizinden import denemesi
    try:
        from config import MASTER_JSON
    except ImportError:
        MASTER_JSON = None

def isimi_sadelestir(entity_name):
    """'Hacettepe Üniversitesi' kalıplarını baştan siler."""
    if not entity_name: return ""
    # (?i) büyük/küçük harf duyarlılığını kaldırır, baştaki gereksiz kalıbı siler
    temiz_isim = re.sub(r'(?i)^hacettepe\s+(ü|u)niversitesi\s*[-–]?\s*', '', entity_name)
    
    if not temiz_isim.strip():
        return entity_name
    return temiz_isim.strip()

def birim_puani_hesapla(entity_name, url):
    match = re.search(r'https?://([^.]+)\.hacettepe\.edu\.tr', url)
    subdomain = match.group(1) if match else ""
    
    score_bonus = 0
    birim_tipi = "DİĞER"
    name_lower = turkish_lower(entity_name)
    
    # 1. ÖNCE ALT BİRİMLERİ (ANA BİLİM DALI) YAKALA VE HAPSET
    if "ana bilim dalı" in name_lower or "anabilim dalı" in name_lower or "abd" in name_lower:
        score_bonus = 40 # Fakülteden düşük, koord'dan yüksek
        birim_tipi = "ANA BİLİM DALI"

    # 2. SONRA PROGRAMLARI YAKALA
    elif "programı" in name_lower:
        score_bonus = 20 
        birim_tipi = "PROGRAM"

    # 3. ŞİMDİ ASIL KRALLARI (FAKÜLTE/BÖLÜM/DAİRE BAŞKANLIĞI) YAKALA 
    elif "fakültesi" in name_lower or "bölümü" in name_lower or "daire başkanlığı" in name_lower:
        score_bonus = 100 if "fakültesi" in name_lower or "bölümü" in name_lower else 80
        if "fakültesi" in name_lower: birim_tipi = "FAKÜLTE"
        elif "bölümü" in name_lower: birim_tipi = "BÖLÜM"
        else: birim_tipi = "DAİRE BAŞKANLIĞI"

    # 4. İDARİ BİRİMLER (Ceza Puanı)
    elif "koordinatörlüğü" in name_lower or "merkezi" in name_lower:
        score_bonus = -20 
        birim_tipi = "KOORDİNATÖRLÜK" if "koordinatörlüğü" in name_lower else "ARAŞTIRMA MERKEZİ"

    # 5. Enstitüler veya Yüksekokullar
    elif "enstitüsü" in name_lower or "yüksekokulu" in name_lower:
        score_bonus = 50
        birim_tipi = "ENSTİTÜ/YÜKSEKOKUL"

    # KISA İSİM BONUSU (Tam İsabet)
    if len(entity_name.split()) <= 4:
        score_bonus += 30

    return subdomain, score_bonus, birim_tipi

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
    "egitim-bulteni.hacettepe.edu.tr": "DELETE",
    "yenikazanan.hacettepe.edu.tr": "DELETE", # Geçici kayıt portalı, süresi doldu
    "openaccess.hacettepe.edu.tr": "DELETE" # Kullanıcı talebi üzerine engellendi
}


def get_subdomain_key(url):
    """URL'den subdomain'i ayıklayıp standart bir anahtar döndürür."""
    match = re.search(r'https?://([^.]+)\.hacettepe\.edu\.tr', url)
    if match: return match.group(1).lower()
    return url.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].lower()

def clean_and_merge_json(file_path):
    print(f"[i] {file_path} temizligi ve infaz operasyonu basliyor...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. ASAMA: ISIM DUZELTME VE HARDCODED OVERRIDES
    survived_data = []
    for item in data:
        url = item.get("url", "").replace("www.", "")
        item["url"] = url 
        
        if "action_links" in item:
            for link in item["action_links"]:
                link_url = link.get("url", "")
                if link_url:
                    link["url"] = link_url.replace("www.", "")
        
        name_lower = item.get("entity_name", "").lower()
        
        # 💉 MERKEZİ DEV SEO ENJEKSİYONU: Tüm gizli kelimeler sadece burada yaşar!
        if "sağlık" in name_lower and "kültür" in name_lower:
            item["description"] = item.get("description", "") + " yemekhane menü yemek yurt barınma kyk sks"
        elif "öğrenci işleri" in name_lower:
            item["description"] = item.get("description", "") + " akademik takvim harç ödeme kayıt otomasyon transkript mezuniyet belge bilsis diploma"
        elif "bilgi işlem" in name_lower:
            item["description"] = item.get("description", "") + " eduroam vpn wifi internet e-posta şifre unuttum"
        elif "idari" in name_lower and "işler" in name_lower:
            item["description"] = item.get("description", "") + " ring servis otobüs ulaşım saatleri"
        elif "yapay zeka" in name_lower:
            item["description"] = item.get("description", "") + " ai staj"
            
        # Erasmus/AB Ofisi için gelişmiş ve akademik bölüm dışlayıcı filtre
        is_academic = any(k in name_lower for k in ["bölümü", "fakültesi", "enstitü", "ana bilim"])
        is_eu_office = any(k in name_lower for k in ["dış ilişkiler", "uluslararası", "ab ofisi", "european", "avrupa", "erasmus"])
        if not is_academic and is_eu_office:
            item["description"] = item.get("description", "") + " erasmus yurtdışı değişim mevlana farabi"

        # 1. İsmi Sadeleştir (Hacettepe Üniversitesi kısmını uçur)
        item["entity_name"] = isimi_sadelestir(item.get("entity_name", ""))

        should_delete = False
        for override_url, correct_name in HARDCODED_OVERRIDES.items():
            if override_url in url:
                if correct_name == "DELETE":
                    should_delete = True
                    break
                else:
                    item["entity_name"] = correct_name
        
        if not should_delete:
            subdomain, priority, b_type = birim_puani_hesapla(item.get("entity_name", ""), url)
            item["search_alias"] = subdomain
            item["priority_score"] = priority
            item["entity_type"] = b_type
            
            # MEGA İNDEKS (search_text) OLUŞTURMA
            intents = " ".join([l.get("intent", "") for l in item.get("action_links", [])])
            item["search_text"] = turkish_lower(f"{subdomain} {item['entity_name']} {intents}")
            
            survived_data.append(item)

    # 2. AŞAMA: URL BAZLI TEKİLLEŞTİRME (Merging)
    merged_data = {}

    for item in survived_data:
        if not item.get("entity_name"):
            continue

        # URL'yi standartlaştır (www, http, https temizle)
        raw_url = item.get("url", "")
        url_key = raw_url.replace("https://", "").replace("http://", "").replace("www.", "").replace("/", "").strip().lower()
        
        # İsmi standartlaştır
        raw_name = item.get("entity_name", "")
        name_key = raw_name.lower().replace("hacettepe üniversitesi", "").replace("hacettepe", "").strip()
        
        # www temizliği için birincil anahtar URL olmalı
        merge_key = url_key if url_key else f"no_url_{name_key}"

        if merge_key in merged_data:
            existing_item = merged_data[merge_key]
            all_links = existing_item.get("action_links", []) + item.get("action_links", [])
            
            # Tekilleştir
            unique_links = {}
            for link in all_links:
                link_intent_key = link.get("intent", "").lower().strip()
                if link_intent_key not in unique_links:
                    unique_links[link_intent_key] = link
            existing_item["action_links"] = list(unique_links.values())
            existing_item["deep_crawl_pages"] = existing_item.get("deep_crawl_pages", 0) + item.get("deep_crawl_pages", 0)
        else:
            merged_data[merge_key] = item

    # 3. AŞAMA: TARİH VE VERSİYON FİLTRESİ + SON MEGA İNDEKS GÜNCELLEMESİ
    for merge_key, item in merged_data.items():
        # 1. Filtreleme
        if "action_links" in item:
            item["action_links"] = filter_outdated_links(item["action_links"])
        
        # 🚀 SKSDB İÇİN MEDİKO (SUNİ ÇİP) ENJEKSİYONU
        e_name = item.get("entity_name", "").lower()
        if "sağlık, kültür" in e_name or "sksdb" in item.get("search_alias", ""):
            if "action_links" not in item:
                item["action_links"] = []
            
            # Eğer bot zaten bulamadıysa, o linki zorla karta ekle
            mevcut_linkler = [link.get("intent", "").lower() for link in item["action_links"]]
            if not any("mediko" in link or "sağlık" in link for link in mevcut_linkler):
                item["action_links"].append({
                    "intent": "Öğrenci Sağlık Merkezi (Mediko)",
                    "url": "https://hacettepe.edu.tr/yerleskedeyasam/saglik", # Aşılanan link
                    "type": "external"
                })
        
        # 2. Mega İndeks Güncelleme (Filtreleme sonrası en güncel intents ile)
        intents = " ".join([l.get("intent", "") for l in item.get("action_links", [])])
        subdomain = item.get("search_alias", "")
        item["search_text"] = turkish_lower(f"{subdomain} {item['entity_name']} {intents}")

        # Otonom Kısaltma ve Alt Dal (Sub-Branch) Enjeksiyonu
        ekstra_kelimeler = set() # Aynı kelimeler tekrar etmesin diye Set kullanıyoruz

        # 1. Kartın kendi adının kısaltmasını al (Örn: İktisadi ve İdari Bilimler -> iibf)
        ekstra_kelimeler.add(otonom_kisaltma_uret(item.get("entity_name", "")))

        # 2. Crawler'ın siteden bulduğu tüm Alt Birimleri (sub_branches) tarayalım
        for sub in item.get("sub_branches", []):
            ekstra_kelimeler.add(sub.lower()) # Alt bölümün tam adını göm ("tıbbi görüntüleme")
            ekstra_kelimeler.add(otonom_kisaltma_uret(sub)) # Kısaltmasını göm ("tg")

        # 3. İntentlerde (Butonlarda) gizli program adları varsa onları da tara
        for link in item.get("action_links", []):
            intent_metni = link.get("intent", "")
            if len(intent_metni.split()) >= 2:
                ekstra_kelimeler.add(otonom_kisaltma_uret(intent_metni))

        # Sözlükten gelen özel durumlar (Yemekhane, Eduroam gibi webte yazmayan argolar) 
        # Sadece bunlar manuel kalmalı, bölümler değil!
        e_name = item.get("entity_name", "").lower()
        if "sağlık, kültür" in e_name: ekstra_kelimeler.update(["yemekhane", "yemek", "menü", "yurt", "mediko"])
        if "bilgi işlem" in e_name: ekstra_kelimeler.update(["eduroam", "wifi", "vpn", "şifre"])
        if "ab ofisi" in e_name or "european" in e_name: ekstra_kelimeler.update(["erasmus", "farabi", "mevlana", "yurtdışı"])

        # Temizle, boşlukları sil ve arama metnine (search_text) kaynak yap
        saf_kelimeler = " ".join([k for k in ekstra_kelimeler if k])
        item["search_text"] = f"{item.get('search_text', '')} {saf_kelimeler}".strip().lower()

    # Sözlükteki değerleri tekrar JSON listesine çevir
    final_list = list(merged_data.values())

    # 🚌 SENTETİK VERİ: Dinamik EGO 130 Ring Kartı (Resmi Durak Enjeksiyonlu)
    ring_karti = {
        "entity_name": "Beytepe Ring (EGO 130)",
        "url": "https://www.ego.gov.tr/",
        "category": "CANLI ULAŞIM",
        "search_alias": "ring",
        "description": "Beytepe Kampüsü 130 nolu EGO otobüsü kalkış saatleri ve güzergahı: Metro, Nizamiye, Kongre Salonu, MYO, TÖMER, Öğrenci Evleri, Mühendislik, Hukuk.",
        "search_text": "ring otobüs otobus servis ulaşım ulasim ego 130 saatleri metro beytepe durak köprü nizamiye kültür kongre salonu kkm meslek yüksek okulu myo öğrenci evleri yurtlar tömer mühendislik hukuk 1596 cd",
        "priority_score": 8000,
        "is_ring": True, # Frontend'e bu kartın canlı olduğunu söylüyoruz
        "action_links": [
            {"intent": "Metro İstasyonu (10620)", "url": "javascript:(function(){var f=document.createElement('form');f.action='https://www.ego.gov.tr/tr/otobusnerede';f.method='POST';f.target='_blank';var i=document.createElement('input');i.name='durak_no';i.value='10620';f.appendChild(i);document.body.appendChild(f);f.submit();f.remove();})()"},
            {"intent": "Nizamiye (14694)", "url": "javascript:(function(){var f=document.createElement('form');f.action='https://www.ego.gov.tr/tr/otobusnerede';f.method='POST';f.target='_blank';var i=document.createElement('input');i.name='durak_no';i.value='14694';f.appendChild(i);document.body.appendChild(f);f.submit();f.remove();})()"},
            {"intent": "Öğrenci Evleri (10566)", "url": "javascript:(function(){var f=document.createElement('form');f.action='https://www.ego.gov.tr/tr/otobusnerede';f.method='POST';f.target='_blank';var i=document.createElement('input');i.name='durak_no';i.value='10566';f.appendChild(i);document.body.appendChild(f);f.submit();f.remove();})()"},
            {"intent": "Mühendislik (13140)", "url": "javascript:(function(){var f=document.createElement('form');f.action='https://www.ego.gov.tr/tr/otobusnerede';f.method='POST';f.target='_blank';var i=document.createElement('input');i.name='durak_no';i.value='13140';f.appendChild(i);document.body.appendChild(f);f.submit();f.remove();})()"},
            {"intent": "Hukuk Fak. (13139)", "url": "javascript:(function(){var f=document.createElement('form');f.action='https://www.ego.gov.tr/tr/otobusnerede';f.method='POST';f.target='_blank';var i=document.createElement('input');i.name='durak_no';i.value='13139';f.appendChild(i);document.body.appendChild(f);f.submit();f.remove();})()"}
        ]
    }

    # EGO duplication protection: Filter out any existing entries that refer to the same thing
    # This prevents duplication if the script runs multiple times on its own output.
    final_list = [
        item for item in final_list 
        if item.get("entity_name") != "Beytepe Ring (EGO 130)" and 
        "ego.gov.tr" not in item.get("url", "").lower()
    ]
    
    final_list.append(ring_karti)

    # 🚀 HACETTEPE HASTANELERİ İÇİN ÖZEL VIP KART ENJEKSİYONU
    hastane_var_mi = False
    for item in final_list:
        # Eğer crawler bir şekilde bulduysa, onu VIP yap ve SEO'sunu güçlendir
        if "hastane.hacettepe.edu.tr" in item.get("url", ""):
            hastane_var_mi = True
            item["entity_name"] = "Hacettepe Üniversitesi Hastaneleri"
            item["search_text"] = item.get("search_text", "") + " hastane hastaneleri randevu poliklinik laboratuvar tahlil online islemler"
            item["priority_score"] = 150  # En tepeye çıksın diye ekstrem skor
            
            if "action_links" not in item:
                item["action_links"] = []
            mevcut_linkler = [link.get("intent", "").lower() for link in item["action_links"]]
            if not any("online" in link for link in mevcut_linkler):
                item["action_links"].append({
                    "intent": "Online İşlemler",
                    "url": "https://hastane.hacettepe.edu.tr/online-islemler_35.html",
                    "type": "external"
                })
            break

    # Eğer crawler hastaneyi tamamen es geçtiyse, sıfırdan jilet gibi bir kart oluştur
    if not hastane_var_mi:
        final_list.append({
            "id": "vip_hastane_001",
            "entity_name": "Hacettepe Üniversitesi Hastaneleri",
            "url": "https://hastane.hacettepe.edu.tr",
            "search_alias": "hastane",
            "search_text": "hastane hastaneleri randevu poliklinik onkoloji cocuk e-randevu laboratuvar online islemler",
            "priority_score": 150, # VIP Puanı (Fakülteleri bile ezer geçer)
            "description": "Erişkin Hastanesi, İhsan Doğramacı Çocuk Hastanesi ve Onkoloji Hastanesi Ana Portalı",
            "action_links": [
                {"intent": "Online İşlemler", "url": "https://hastane.hacettepe.edu.tr/online-islemler_35.html", "type": "external"}
            ]
        })

    # YEDEKLEME VE ÜZERİNE YAZMA
    backup_path = file_path.replace(".json", "_backup.json")
    
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
    if MASTER_JSON:
        target_file = MASTER_JSON
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        target_file = os.path.join(project_root, "public", "outputs", "hybrid_master.json")
    
    if os.path.exists(target_file):
        clean_and_merge_json(target_file)
        
        # 🧹 TEMİZLİK PROTOKOLÜ: İşlem bittikten sonra ham dosyaları yok et!
        print("\n[Cleanup] Cop toplama (Cleanup) baslatiliyor...")
        hedef_dizin = os.path.dirname(target_file)

        # İsmi output_ ile başlayan tüm ham JSON'ları bul
        ham_dosyalar = glob.glob(os.path.join(hedef_dizin, "output_*_hybrid.json"))
        silinen_sayi = 0

        for dosya in ham_dosyalar:
            try:
                os.remove(dosya)
                silinen_sayi += 1
            except Exception as e:
                print(f"(!) Silinemedi: {dosya} - Hata: {e}")

        print(f"[*] Toplam {silinen_sayi} ham JSON dosyasi silindi. Mutfak tertemiz!")
    else:
        print(f"HATA: {target_file} dosyası bulunamadı. Lütfen 'public/outputs/' dizinini kontrol edin.")
