# Hubul Search — Devir Teslim, Kurulum ve Bakım Dokümanı

[![Setup & Configuration Check](https://github.com/Kutsukey/hubul-search/actions/workflows/verify_setup.yml/badge.svg)](https://github.com/Kutsukey/hubul-search/actions/workflows/verify_setup.yml)

> **Proje:** Hubul Search — Hacettepe Üniversitesi Otonom Arama Motoru  
> **Geliştiren:** Hacettepe Üniversitesi Dijital Dönüşüm Ofisi  
> **Belge Türü:** Enterprise Devir Teslim & Operasyon Kılavuzu  
> **Son Güncelleme:** Mayıs 2026

---

## İçindekiler

1. [Sistem Genel Bakış](#1-sistem-genel-bakış)
2. [Otonom Arama Zekası — Temel Mekanizmalar](#2-otonom-arama-zekası--temel-mekanizmalar)
3. [Mimari ve Dizin Yapısı](#3-mimari-ve-dizin-yapısı)
4. [Devreye Alma — Adım Adım Kurulum](#4-devreye-alma--adım-adım-kurulum)
5. [GitHub Actions — Otomasyon Takvimi](#5-github-actions--otomasyon-takvimi)
6. [Bakım ve Günlük Operasyon](#6-bakım-ve-günlük-operasyon)
7. [Veri Pipeline El ile Çalıştırma](#7-veri-pipeline-el-ile-çalıştırma)
8. [Telemetri ve Supabase Logları](#8-telemetri-ve-supabase-logları)
9. [Sorun Giderme](#9-sorun-giderme)
10. [Kritik Dosyalar Referansı](#10-kritik-dosyalar-referansı)

---

## 1. Sistem Genel Bakış

Hubul Search, Hacettepe Üniversitesi'nin dağınık web yapısını tek bir zeki arama katmanına indirgeyen, **tamamen otonom** bir bilgi erişim sistemidir.

Sistem üç katmandan oluşur:

| Katman | Teknoloji | Görev |
|---|---|---|
| **Frontend / Widget** | Vanilla JS (`ia-widget.js`), Fuse.js | İstemci tarafında arama, sonuç gösterimi |
| **Veri Pipeline** | Python 3.10+, crawl4ai, Playwright, Gemma LLM | Kurumsal siteleri tarar, LLM ile yapılandırır |
| **Telemetri & Backend** | Supabase (PostgreSQL) | Arama logları, "bulunamadı" kayıtları |

### Veri Akışı

```
Hacettepe Siteleri
      │
      ▼
[hybrid_hacettepe_crawler_3.py]  ← BFS tarama + Playwright (JS sayfalar)
      │                            + Gemma LLM veri çıkarımı
      ▼
[veri_temizleyici.py]            ← Tekilleştirme, puanlama, SEO enjeksiyonu
      │
      ▼
public/outputs/hybrid_master.json  ←  Frontend bu dosyayı okur
      │
      ▼
[announcement_pinger.py]         ← Günlük duyuru çekimi
      │
      ▼
public/outputs/announcements_live.json

      Tüm bu akış → GitHub Actions ile otomatik tetiklenir
                   → Netlify/Vercel'e otomatik deploy edilir
```

---

## 2. Otonom Arama Zekası — Temel Mekanizmalar

> **Önemli:** Bu sistem basit bir kelime eşleştirici değildir. Aşağıdaki altı mekanizma, sistemin "otonom zekasını" oluşturur. Yeni ekibin bu mekanizmaları anlaması, herhangi bir müdahalede kritik önem taşır.

### 2.1 Subdomain Zekası

Crawler, taranan her sitenin URL'sinden subdomain'i otomatik çeker ve `search_alias` alanına yazar.

```
https://cge.hacettepe.edu.tr  →  search_alias: "cge"
https://bilsis.hacettepe.edu.tr  →  search_alias: "bilsis"
```

Kullanıcı `"cge"` yazdığında, widget bu alias üzerinden Çocuk Gelişimi Bölümü'nü en üste taşır. Bu mantık `ia-widget.js` içindeki `getSubdomain()` fonksiyonu ve `veri_temizleyici.py` içindeki `birim_puani_hesapla()` tarafından üretilir.

### 2.2 Jargon Rewriter — Kampüs Argosu Çevirmeni

`ia-widget.js` içindeki `jargonMap` nesnesi, öğrenci argosunu anlık olarak resmi dile çevirir:

```javascript
const jargonMap = {
    "cge":    "cocuk gelisimi",
    "iibf":   "iktisadi ve idari",
    "shmyo":  "saglik hizmetleri meslek",
    "mediko": "saglik kultur",
    "bilsis": "bilgi islem",
    "oidb":   "ogrenci isleri",
    "obs":    "ogrenci bilgi",
    "kyk":    "yurt",
    "bim":    "bilgi islem",
    "cap":    "cift anadal",
    "fen":    "fen fakultesi",
    "tip":    "tip fakultesi"
    // ...
};
```

Kullanıcı `"iibf burs"` yazdığında sistem bunu `"iktisadi ve idari burs"` olarak işler. **Yeni jargon eklemek için bu nesneye tek satır eklenmesi yeterlidir.**

### 2.3 VIP Hiyerarşisi — Önceliklendirme Puanı

`veri_temizleyici.py` içindeki `birim_puani_hesapla()` fonksiyonu her kuruma bir `priority_score` atar:

| Birim Türü | Skor Bonusu |
|---|---|
| Fakülte / Bölüm | +100 |
| Daire Başkanlığı | +80 |
| Enstitü / Yüksekokul | +50 |
| Ana Bilim Dalı | +40 |
| Program | +20 |
| Koordinatörlük / Araştırma Merkezi | -20 |

Bu sayede "Tıp Fakültesi" araması yapıldığında, fakülte kartı alakasız araştırma merkezlerini ezip her zaman en üstte çıkar.

### 2.4 Çarpım Skoru — Entity Blindness Fix

Duyuru aramasında, duyurunun başlığına ek olarak duyuruyu yayınlayan **kurumun adı** da sorguyla eşleştirilir. Kurum adı eşleşirse skor çarpanı devreye girer:

```javascript
// ia-widget.js — Küresel Duyuru Arama Motoru
const entityMatchScore = meaningfulSearchTerms.some(t => eNameNorm.includes(t)) ? 1.5 : 1.0;
let score = 1.0 - (titleMatchScore * 0.3 * entityMatchScore) - (matchCount * 0.1);
```

Örnek: `"matematik"` arandığında Matematik Bölümü'nden çıkan duyurular, başka birimlerden çıkan duyurulara göre 1.5x daha güçlü skora sahip olur.

### 2.5 Çöp Öğütücü — Garbage Filter

Fuse.js'in harf benzerliğine dayalı sahte eşleşmelerini engelleyen katman. `ia-widget.js` içindeki `handleSearch()` fonksiyonunun sonunda yer alır:

```javascript
// Hiçbir kuralla eşleşmeyen sonuçlar doğrudan 1.0 (çöp) skora düşürülür
newScore = 1.0;
// ...
entityResults = entityResults.filter(r => r.score < 0.4);
```

"zattiri zottu" gibi anlamsız aramalar sonuç döndürmez.

### 2.6 Zombi Kalkanı — Ölü Site Filtresi

İki mekanizma ile çalışır:

1. **LLM Faz 1 Filtresi:** `hybrid_hacettepe_crawler_3.py`, her siteyi crawl etmeden önce Gemma'ya sorar: *"Bu bir kurumsal birim mi, yoksa terk edilmiş proje mi?"* `false` dönen siteler veri setine girmez.
2. **Kara Liste:** Timeout alan veya ölü siteler `crawler_blacklist.json`'a otomatik yazılır. Sonraki taramalarda bu siteler atlanır.

---

## 3. Mimari ve Dizin Yapısı

```
a-z-hacettepe/
│
├── .github/
│   └── workflows/
│       ├── audit_pipeline.yml       # Haftalık: Gatekeeper → Crawler → Temizleyici
│       └── daily_announcements.yml  # Günlük (08:00 UTC): Duyuru çekimi
│
├── crawler/
│   ├── hybrid_hacettepe_crawler_3.py  ← AKTİF ANA CRAWLER
│   └── announcement_pinger.py         ← Duyuru senkronizasyon scripti
│
├── utils/
│   ├── config.py               # Tüm dosya yolları buradan yönetilir
│   ├── veri_temizleyici.py     # Tekilleştirme, puanlama, SEO enjeksiyonu
│   ├── auto_gatekeeper.py      # Yeni subdomain keşif ve onay katmanı
│   └── validator.py            # Veri kalite kontrolü
│
├── public/
│   ├── index.html              # Bağımsız arama arayüzü
│   ├── ia-widget.js            # Herhangi bir sayfaya gömülebilir widget
│   └── outputs/
│       ├── hybrid_master.json       ← ANA VERİ İNDEKSİ (frontend bunu okur)
│       └── announcements_live.json  ← CANLI DUYURULAR
│
├── inputs/
│   ├── seed_urls.json    # Crawler'ın başlangıç URL listesi
│   └── az_links.json     # Hacettepe A-Z dizininden çekilen linkler
│
├── crawler_hash_cache.json  # MD5 hash cache (LLM maliyet kalkanı)
├── crawler_blacklist.json   # Kalıcı kara liste (ölü/zaman aşımı siteleri)
├── requirements.txt
└── .env                     # GOOGLE_API_KEY buraya
```

---

## 4. Devreye Alma — Adım Adım Kurulum

### Adım 1 — Repository'yi Fork'layın

Sistemin bağımsız çalışması için repoyu **kendi GitHub organizasyonunuza fork'lamanız zorunludur.** Fork olmadan GitHub Actions secrets tanımlayamazsınız.

```
GitHub → Repo sayfası → Fork → Create fork
```

### Adım 2 — GitHub Secrets Tanımlayın

Fork'ladığınız repoda şu secret'ları ekleyin:

```
Settings → Secrets and variables → Actions → New repository secret
```

| Secret Adı | Açıklama |
|---|---|
| `GOOGLE_API_KEY` | Google AI Studio'dan alınan Gemma/Gemini API anahtarı |

> **Not:** GitHub Actions üzerinde çalışan otonom veri tarama (crawler) adımları için `GOOGLE_API_KEY` gereklidir.

### Adım 3 — Supabase Kurulumu (Telemetri)

Supabase telemetrisi, kullanıcıların bulamadığı aramaları kaydetmek için kullanılır. Bu işlem **istemci (tarayıcı) tarafında** çalıştığı için veriler GitHub Actions Secrets üzerinden okunmaz, doğrudan kod dosyalarına eklenmelidir.

1. [supabase.com](https://supabase.com) üzerinde yeni bir proje açın.
2. SQL Editor'de aşağıdaki SQL komutunu çalıştırarak hem tabloyu oluşturun hem de anonim anahtarın güvenliğini sağlamak için RLS (Row Level Security) politikasını tanımlayın (böylece dışarıdan sadece veri eklenebilir, mevcut veriler okunamaz veya silinemez):

```sql
-- 1. Tabloyu oluşturun
CREATE TABLE search_logs (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    found BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Row Level Security aktif edin
ALTER TABLE search_logs ENABLE ROW LEVEL SECURITY;

-- 3. Sadece veri eklemeye (INSERT) izin veren politikayı tanımlayın
CREATE POLICY "Herkes veri ekleyebilir" ON search_logs
    FOR INSERT 
    TO public
    WITH CHECK (true);
```

3. `public/ia-widget.js` ve `public/index.html` dosyalarının içindeki `SUPABASE_URL` ve `SUPABASE_ANON_KEY` alanlarını kendi projenizin değerleriyle güncelleyin.

### Adım 4 — Frontend Deployment (Netlify / Vercel)

Frontend tamamen statik JavaScript'tir. Ekstra sunucu veya build adımı gerekmez.

**Netlify:**
```
Add new site → Import an existing project → GitHub reponuzu seçin
Base directory: public
Publish directory: public
Build command: (boş bırakın)
```

**Vercel:**
```
Add New Project → GitHub reponuzu seçin
Framework Preset: Other
Output Directory: public
```

Deploy tamamlandığında sistem canlıya alınmış olur. Bundan sonra her `git push`, otomatik olarak yeni versiyonu yayınlar.

### Adım 5 — Python Ortamı (Crawler için)

Crawler'ı yerel ortamda veya GitHub Actions dışında çalıştırmak isterseniz:

```bash
# 1. Sanal ortam oluştur
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Playwright Chromium'u yükle (JS sayfalar için zorunlu)
playwright install chromium

# 4. .env dosyası oluştur
echo "GOOGLE_API_KEY=your_key_here" > .env
```

### Adım 6 — Lokal Test

Ön yüz dosyalarını test etmek için `public` klasörünün içinden HTTP sunucusunu başlatmak en doğrusudur (böylece göreceli yollar doğru çözümlenir):

```bash
cd public
python -m http.server 8000
# Tarayıcıda: http://localhost:8000
```

---

## 5. GitHub Actions — Otomasyon Takvimi

Sistem üç ayrı otomasyon pipeline'ı ile çalışır.

### Pipeline 0 — Kurulum ve Konfigürasyon Kontrolü (Setup Check)

**Dosya:** `.github/workflows/verify_setup.yml`  
**Zamanlama:** Her `push`, `pull_request` adımında veya manuel olarak tetiklendiğinde.  
**Yapılan İş:** Projenin bağımlılıklarının doğru kurulduğunu, gerekli dosya yapısının mevcut olduğunu, `GOOGLE_API_KEY`'in geçerliliğini ve Supabase telemetri veritabanı bağlantısının sorunsuz çalıştığını kontrol eder.

### Pipeline 1 — Günlük Duyuru Güncellemesi

**Dosya:** `.github/workflows/daily_announcements.yml`  
**Zamanlama:** Her gün **08:00 UTC** (11:00 TSİ)  
**Yapılan İş:** Tüm kurumların duyuru sayfalarını tarar, `announcements_live.json`'ı günceller ve otomatik commit atar.

```yaml
# Zamanlama değiştirmek için:
on:
  schedule:
    - cron: '0 8 * * *'  # Her gün 08:00 UTC
                          # Örnek değişiklik: '0 6 * * *' → 06:00 UTC (09:00 TSİ)
```

### Pipeline 2 — Haftalık Audit Pipeline (Ana Veri Yenileme)

**Dosya:** `.github/workflows/audit_pipeline.yml`  
**Zamanlama:** Her **Pazartesi 00:00 UTC**  
**Yapılan İş:** Tam pipeline zinciri:

```
auto_gatekeeper.py     ← Yeni subdomain'leri keşfeder ve onaylar
        ↓
hybrid_hacettepe_crawler_3.py  ← Tüm seed listesini yeniden tarar
        ↓
veri_temizleyici.py    ← Verileri temizler, puanlar, birleştirir
        ↓
git commit & push      ← hybrid_master.json güncellenir, otomatik deploy
```

**Zamanlamayı değiştirmek için:**
```yaml
on:
  schedule:
    - cron: "0 0 * * 1"   # Pazartesi 00:00 UTC
    # Örnek: "0 0 * * 0"  → Pazar
    # Örnek: "0 0 1 * *"  → Her ayın 1'i
```

**Workflow'u manuel tetiklemek için:**  
`GitHub → Actions → İlgili workflow → Run workflow`

---

## 6. Bakım ve Günlük Operasyon

> Bu bölüm, **koda dokunmadan** sistemi yönetmek için gereken tüm adımları içerir.

### 6.1 Yeni Jargon / Kısaltma Eklemek

Öğrenciler yeni bir kısaltma kullanmaya başladığında (örn. yeni bir fakülte kısaltması), tek yapılacak iş `ia-widget.js` dosyasındaki `jargonMap` nesnesine bir satır eklemektir:

```javascript
// ia-widget.js — yaklaşık satır 641
const jargonMap = {
    "cge":    "cocuk gelisimi",
    "iibf":   "iktisadi ve idari",
    // ... mevcut girdiler ...

    // YENİ EKLENEBİLECEK ÖRNEKLER:
    "hef":    "hukuk egitim",
    "ebs":    "elektronik belge",
    "ubs":    "uzaktan eğitim"
};
```

Değişikliği kaydedin ve `git push` yapın. Netlify/Vercel otomatik deploy eder.

### 6.2 Supabase "Bulunamadı" Loglarını Okumak

Öğrencilerin arayıp bulamadığı kelimeleri Supabase panelinizden periyodik olarak okuyun:

```sql
-- En çok aranıp bulunamayan sorgular (Son 30 gün)
SELECT query, COUNT(*) as arama_sayisi
FROM search_logs
WHERE found = false
  AND created_at > NOW() - INTERVAL '30 days'
GROUP BY query
ORDER BY arama_sayisi DESC
LIMIT 50;
```

Bu sorgunun çıktısı, `jargonMap`'e eklenmesi gereken yeni girdileri ve crawler'ın kaçırdığı kurumları gösterir.

### 6.3 Bir Kurumu Kara Listeye Almak

Bir sitenin arama sonuçlarında çıkmasını kalıcı olarak engellemek için `crawler_blacklist.json` dosyasına URL ekleyin:

```json
[
  "https://endokrin.hacettepe.edu.tr",
  "https://arsiv.hacettepe.edu.tr",
  "https://yeni-engellenmesi-gereken-site.hacettepe.edu.tr"
]
```

Kara listedeki siteler bir sonraki crawler çalışmasında hem taranmaz hem de mevcut `hybrid_master.json`'dan çıkarılır.

### 6.4 Kara Listeden Çıkarma

```json
// crawler_blacklist.json'dan ilgili URL'yi silin
// Ardından veri_temizleyici.py içindeki HARDCODED_OVERRIDES'ı kontrol edin:

HARDCODED_OVERRIDES = {
    "otk.hacettepe.edu.tr": "DELETE",  # Bu satırı kaldırırsanız site geri döner
    ...
}
```

Sonra `audit_pipeline`'ı manuel tetikleyin.

### 6.5 Kurumun Adını veya Açıklamasını Düzeltmek

LLM'in yanlış isimlendirdiği kurumlar için `veri_temizleyici.py` içindeki `HARDCODED_OVERRIDES` sözlüğüne müdahale edin:

```python
HARDCODED_OVERRIDES = {
    "cs.hacettepe.edu.tr": "Bilgisayar Mühendisliği ve Yapay Zeka Mühendisliği Bölümü",
    # Yeni düzeltme eklemek için:
    "yeni-subdomain.hacettepe.edu.tr": "Doğru Kurum Adı",
}
```

Ardından `python utils/veri_temizleyici.py` çalıştırın veya pipeline'ı tetikleyin.

---

## 7. Veri Pipeline El ile Çalıştırma

Otomasyonu beklemeden veriyi güncellemek gerektiğinde:

```bash
# Sadece duyuruları güncelle (hızlı, ~5-10 dakika)
python crawler/announcement_pinger.py

# Sadece temizleyiciyi çalıştır (mevcut JSON'ı düzelt)
python utils/veri_temizleyici.py

# Yeni subdomain'leri keşfet ve onayla
python utils/auto_gatekeeper.py

# Tam veri yenileme (uzun sürer, ~2-4 saat)
python crawler/hybrid_hacettepe_crawler_3.py
```

**Önemli:** Tam pipeline sırası şu şekilde çalışmalıdır:
```
auto_gatekeeper.py → hybrid_hacettepe_crawler_3.py → veri_temizleyici.py
```

### MD5 Hash Cache Sistemi

Crawler, her sayfanın MD5 parmak izini `crawler_hash_cache.json`'da saklar. Sayfa içeriği değişmemişse LLM çağrısı atlanır — bu API maliyetini %70-90 oranında düşürür.

Cache'i sıfırlamak için (zorla yeniden tarama):
```bash
# Tüm cache'i temizle
echo "{}" > crawler_hash_cache.json
```

---

## 8. Telemetri ve Supabase Logları

### Mevcut Log Tabloları

| Tablo | İçerik |
|---|---|
| `search_logs` | Tüm arama sorguları ve bulunamadı flagları |

### Önerilen Periyodik Kontroller

**Haftalık:**
```sql
-- Başarısız aramaların oranı
SELECT 
    DATE_TRUNC('day', created_at) as gun,
    COUNT(*) FILTER (WHERE found = false) as bulunamadi,
    COUNT(*) as toplam,
    ROUND(COUNT(*) FILTER (WHERE found = false)::numeric / COUNT(*) * 100, 1) as basarisizlik_orani
FROM search_logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY 1 ORDER BY 1;
```

**Aylık:**
```sql
-- En çok aranan 20 terim
SELECT query, COUNT(*) as adet
FROM search_logs
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY query
ORDER BY adet DESC
LIMIT 20;
```

---

## 9. Sorun Giderme

### Arama sonuçları eskimiş / güncellenmiyor

1. GitHub Actions sekmesinden son workflow çalışmasını kontrol edin.
2. `public/outputs/hybrid_master.json` dosyasının son commit tarihine bakın.
3. Widget, `localStorage`'da 2 saatlik cache tutar. Test için tarayıcı localStorage'ını temizleyin:
   ```javascript
   // Tarayıcı konsoluna yapıştırın:
   localStorage.removeItem('hubul_master_data');
   localStorage.removeItem('hubul_last_fetch');
   location.reload();
   ```

### Crawler çalışıyor ama bir kurum çıkmıyor

1. `crawler_blacklist.json` dosyasında o sitenin URL'si olup olmadığını kontrol edin.
2. `veri_temizleyici.py` içindeki `HARDCODED_OVERRIDES`'da `"DELETE"` olarak işaretlenmiş olabilir.
3. LLM Faz 1 filtresi "kurumsal değil" diye reddetmiş olabilir — `processed_urls.json` dosyasını inceleyin.

### GitHub Actions başarısız oluyor

1. `GOOGLE_API_KEY` secret'ının geçerli ve aktif olduğunu doğrulayın.
2. Google AI API kota limitini kontrol edin.
3. Playwright bağımlılık kurulumunda hata varsa workflow log'larına bakın.

### Bir bölüm yanlış sırada çıkıyor

`priority_score` değerini `hybrid_master.json`'da doğrudan düzenleyebilirsiniz (kalıcı çözüm için `HARDCODED_OVERRIDES` veya `birim_puani_hesapla()` fonksiyonunu güncelleyin).

---

## 10. Kritik Dosyalar Referansı

| Dosya | Değiştirme Sıklığı | Kimin Değiştireceği |
|---|---|---|
| `public/ia-widget.js` → `jargonMap` | Aylık (yeni argolar çıktıkça) | Operasyon ekibi |
| `crawler_blacklist.json` | İhtiyaç oldukça | Operasyon ekibi |
| `utils/veri_temizleyici.py` → `HARDCODED_OVERRIDES` | İhtiyaç oldukça | Operasyon ekibi |
| `.github/workflows/*.yml` → `cron` | Sezonluk | Teknik ekip |
| `inputs/seed_urls.json` | Yeni kurum eklenince | Teknik ekip |
| `utils/config.py` | Nadiren | Teknik ekip |
| `crawler/hybrid_hacettepe_crawler_3.py` | Nadiren (mimari değişim) | Teknik ekip |

---

## Önemli Notlar

> **Sistem self-hosted değildir:** Frontend tamamen statik olduğu için Netlify/Vercel üzerinde ek sunucu maliyeti oluşturmaz. Tek maliyet kalemi Google AI API kullanımıdır; MD5 hash cache sistemi bu maliyeti dramatik biçimde düşürür.

> **Koda müdahaleden kaçının:** Operasyonun %90'ı `jargonMap`, `HARDCODED_OVERRIDES` ve `crawler_blacklist.json` üzerinden yönetilebilir. Temel arama mantığına dokunmadan sistemi yıllarca işletmek mümkündür.

> **Supabase loglarını düzenli okuyun:** "Bulunamadı" logları, sistemin kör noktalarını gösterir. Bu loglar beslenmeden jargon sözlüğü güncellenmezse arama kalitesi zamanla düşer.

---

*Bu doküman, Hubul Search sistemini devralan teknik ve operasyon ekiplerine yönelik hazırlanmıştır. Sorular ve güncellemeler için proje `README.md` ve kaynak kod yorumları birincil referans kaynaklarıdır.*
