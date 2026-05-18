# Hubul

> 📘 **Sistem Devir, Kurulum ve Bakım Dokümanı:** Projenin yeni ekibe devredilmesi, kurulum adımları, otonom zeka kuralları ve rutin operasyon detayları için hazırlanan kapsamlı [MAINTENANCE.md](file:///c:/Users/ACER/Desktop/a-z-hacettepe/MAINTENANCE.md) dokümanını okumayı unutmayın.

Hubul, Hacettepe Üniversitesi'nin dağınık web yapısı içinde birim, sayfa, belge ve duyuru bulmayı hızlandırmak için geliştirilmiş bir arama katmanıdır.

Proje iki ana parçadan oluşur:

- `Data Pipeline (Python)`: Üniversite sitelerini tarar, anlamlı bağlantıları ayrıştırır ve LLM desteğiyle yapılandırılmış JSON veri üretir.
- `Frontend / Widget (public/)`: Üretilen veriyi istemci tarafında `Fuse.js` ile indeksler ve statik arayüz üzerinden sunar.

Temel hedef, kullanıcıyı ana sayfalarda dolaştırmak yerine doğrudan ilgili kaynağa götürmektir. Mümkün olduğunda sonuç sadece kurum ana sayfasını değil, "ders programı", "staj", "mevzuat", "formlar" ve "duyurular" gibi derin bağlantıları da döndürür.

## Çalışma Akışı

Sistemin temel akışı şu şekildedir:

1. Başlangıç URL'leri seed listesi veya Hacettepe A-Z dizini üzerinden toplanır.
2. Crawler, hedef sitelerde alt sayfaları ve dokümanları asenkron olarak tarar.
3. LLM katmanı, her kurumsal birim için yapılandırılmış veri çıkarır.
4. Temizleme ve puanlama aşamasında gereksiz kayıtlar ayıklanır; `search_alias`, `priority_score` ve `search_text` gibi alanlar hesaplanır.
5. Üretilen veri `public/outputs/` altına yazılır.
6. Ön yüzde `Fuse.js` ile arama yapılır; sonuçlar birim kartı, derin bağlantılar ve varsa güncel duyurularla birlikte gösterilir.

## Dizin Yapısı

```text
.
|-- crawler/                Python tabanlı crawler ve veri üretim scriptleri
|-- utils/                  temizleme, skorlama ve doğrulama araçları
|-- public/                 statik arayüz, widget ve JSON çıktıları
|   |-- outputs/
|   |-- index.html
|   `-- ia-widget.js
|-- .github/workflows/      otomasyon süreçleri
|-- requirements.txt
`-- README.md
```

Öne çıkan dosyalar:

- `crawler/hybrid_hacettepe_crawler_3.py`: aktif ana veri üretim pipeline'ı
- `crawler/announcement_pinger.py`: güncel duyuruları toplayan modül
- `utils/veri_temizleyici.py`: tekilleştirme, filtreleme ve skorlama scripti
- `utils/auto_gatekeeper.py`: yeni subdomain'ler için LLM tabanlı onay katmanı
- `public/index.html`: statik arama arayüzü
- `public/ia-widget.js`: gömülebilir widget sürümü

## Kurulum

### Gereksinimler

- Python `3.10+`
- Playwright + Chromium
- `GOOGLE_API_KEY`

### 1. Depoyu klonlayın

```bash
git clone <repo-url>
cd hubul-search
```

### 2. Sanal ortam oluşturun

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Ortam değişkenlerini tanımlayın

Kök dizinde bir `.env` dosyası oluşturun:

```env
GOOGLE_API_KEY=your_api_key_here
```

Not:

- Sadece `public/` tarafını çalıştıracaksanız API anahtarı zorunlu değil.
- Crawler, gatekeeper ve validasyon akışları için `GOOGLE_API_KEY` gerekli.

## Lokal Geliştirme

Ön yüz statik çalıştığı için basit bir HTTP sunucusu yeterlidir:

```bash
cd public
python -m http.server 8000
```

Tarayıcıda `http://localhost:8000` adresini açın.

İlgili dosyalar:

- `index.html`: arama arayüzü
- `ia-widget.js`: widget yükleyicisi
- `outputs/hybrid_master.json`: ana indeks verisi
- `outputs/announcements_live.json`: duyuru verisi

## Veri Pipeline Kullanımı

Repo içinde birkaç crawler sürümü var; aktif ana akış `crawler/hybrid_hacettepe_crawler_3.py` üzerinden ilerliyor.

### 1. Master veri setini üretme

```bash
python crawler/hybrid_hacettepe_crawler_3.py
```

Bu adım:

- seed listesi veya A-Z dizininden başlangıç URL'lerini toplar
- alt sayfaları ve dosyaları derin tarar
- JS ağırlıklı sayfalarda Playwright kullanır
- Gemma tabanlı modellerle veri çıkarımı yapar
- yeni keşfedilen subdomain'leri ayrı dosyada toplar

### 2. Temizleme ve skorlama

```bash
python utils/veri_temizleyici.py
```

Bu adım:

- isimleri sadeleştirir
- hardcoded düzeltmeleri uygular
- zayıf veya eski bağlantıları ayıklar
- arama için yardımcı skor alanlarını üretir

### 3. Duyuru senkronizasyonu

```bash
python crawler/announcement_pinger.py
```

Bu script, mevcut `hybrid_master.json` üzerinden duyuru alanlarını tarar ve `announcements_live.json` üretir.

### 4. Gatekeeper

```bash
python utils/auto_gatekeeper.py
```

Bu adım, crawler tarafından keşfedilen yeni endpoint'leri değerlendirir ve kurumsal olarak anlamlı görülenleri seed listesine ekler.

## Otomasyonlar

`.github/workflows/` altında iki ana otomasyon bulunuyor:

- `daily_announcements.yml`: günlük duyuru güncellemesi
- `audit_pipeline.yml`: haftalık `gatekeeper -> crawler -> temizleme` zinciri

Bu yapı, veri setinin düzenli olarak güncel kalmasını sağlar.

## Şu Ana Kadar Yapılanlar

- [x] Seed listesi ve LLM tabanlı (Gemma/Gemini) otonom kurum keşif akışı kuruldu
- [x] Playwright ve Trafilatura kullanılarak JavaScript render'lı sitelerden semantik metin ayıklama sistemi entegre edildi
- [x] MD5 hash karşılaştırması ile içeriği değişmeyen sayfalar tespit edilerek gereksiz LLM çağrıları ve tarama süresi önemli ölçüde azaltıldı
- [x] Aynı kurumun TR ve EN sayfaları ayrı ayrı analiz edilip tek bir kayıt altında birleştirildi.
- [x] LocalStorage ve SWR (Stale-While-Revalidate) mantığıyla sıfır bekleme süreli istemci taraflı JSON önbellek mekanizması uygulandı
- [x] Hacettepe kurumsal kimliğine uygun arayüz tasarımı; iOS Safari zoom hatası, safe area desteği ve mobil UX iyileştirmeleri tamamlandı
- [x] Çok kelimeli arama (`$and`), kelime bazlı önceliklendirme (`priority_score`) ve false-positive önleme (bitişik karakter eşleşme) Fuse.js üzerinde uygulandı
- [x] Günlük duyuru senkronizasyonu ve haftalık tam veri yenileme (`audit_pipeline`) GitHub Actions üzerinden otomatize edildi; gereksiz domain ve `www` kirliliği temizlendi
- [x] Kalıcı URL kara listesi (`crawler_blacklist.json`) eklendi; ölü veya zaman aşımına uğrayan bağlantılar otomatik olarak diske yazılarak sonraki çalıştırmalarda atlanıyor
- [x] Tıp Fakültesi için Mega-Kart asimilasyon prompt'u eklendi; anabilim dalı linkleri ayrı kayıt yerine tek kart altında toplandı
- [x] Arama motoru SEO enjeksiyonu: AB Ofisi/Erasmus, SKS/yemekhane ve Bilgi İşlem/eduroam için görünmez `search_text` anahtar kelimeleri eklendi
- [x] Fuse.js sorgu motoru yeniden yazıldı; kavramsal yönlendirme (Erasmus → AB Ofisi), birebir isim eşleşme bonusu ve arayüz skoru yönetimi iyileştirildi
- [x] `isNew` (7 gün) flag'i ile duyuruların önceliklendirme mantığı güncellendi; ana sayfa ve widget'ta VIP duyuru filtrelemesi uygulandı
- [x] Supabase tabanlı kullanıcı "Bulamadım" raporlama sistemi `ia-widget.js`'e entegre edildi; buton durumu (iletiliyor / teşekkürler / hata) yönetimi eklendi
- [x] Visual Viewport API ile mobil klavye uyumu sağlandı; klavye açıldığında widget paneli otomatik olarak klavye üstüne sabitleniyor
- [x] `endokrin.hacettepe.edu.tr` kara listeye alındı (crawler, announcement_pinger ve eski crawler sürümlerinde)
- [x] Otonom Temizlikçi (Cleanup) protokolü: `veri_temizleyici.py` işlem bittikten sonra ham `output_*.json` dosyalarını otomatik olarak temizliyor
- [x] Detaylı devir teslim, kurulum ve bakım (maintenance) dokümantasyonu ([MAINTENANCE.md](file:///c:/Users/ACER/Desktop/a-z-hacettepe/MAINTENANCE.md)) tamamlandı

## Yapılması Beklenenler

- [ ] Duyuru içeriklerinde tam metin arama desteği
- [ ] Hangi kurumların veya anahtar kelimelerin ne sıklıkla arandığını ölçen anonim arama loglama altyapısı (Supabase `search_logs` tablosu hazır; otomatik kayıt mekanizması eklenecek)
- [ ] Crawler job'larının bağımsız parçalara ayrılması ve GitHub Actions üzerinden kritik hata ile başarı bildirimleri için Telegram/Discord webhook desteği

## Katkıda Bulunmak İçin

Katkı verirken şu sırayı izlemek projenin veri bütünlüğü açısından kritiktir:

1. `public/outputs/` altındaki `hybrid_master.json` ve `announcements_live.json` yapılarını inceleyerek veriyi tanıyın.
2. Crawler, LLM promptları veya temizleyici utility tarafında dar kapsamlı bir değişiklik yapın.
3. Tüm pipeline'ı çalıştırmak yerine yalnızca ilgili modülü veya belirli bir seed URL'sini test edin.
4. `git diff` ile JSON farkını inceledikten sonra arayüzü yerel ortamda açıp arama sonuçlarının öneriler ve tam eşleşme mantığını bozmadığını doğrulayın.

PR açmadan önce dikkat edilmesi gereken noktalar:

- Kurumsal eşleşmelerde alakasız sonuçların (false positive) öne çıkmaması
- CSS selector veya URL kuralı değişikliklerinin kırık bağlantıya yol açmaması
- Veri birleştirme aşamasında aynı birimin birden fazla kayıt olarak görünmemesi

## Geliştirici Notları

- Geliştiriciler ve sistemi yönetecek olanlar, cron job zamanlamaları, Supabase telemetri entegrasyonu ve `jargonMap` gibi otonom zeka ayarları için mutlaka [MAINTENANCE.md](file:///c:/Users/ACER/Desktop/a-z-hacettepe/MAINTENANCE.md) dokümanını kılavuz olarak kullanmalıdır.
- Frontend tarafı herhangi bir build tool (Webpack, Vite, npm) kullanmaz. `ia-widget.js` doğrudan CDN mantığıyla herhangi bir sayfaya entegre edilebilecek şekilde tasarlanmıştır.
- Repo içinde eski veya deneysel crawler scriptleri bulunabilir; ancak bunların tamamı aktif GitHub Actions akışının parçası değildir. Ana pipeline `hybrid_hacettepe_crawler_3.py` ve veri temizleyici scriptler üzerinden yürür.
- Bazı Python scriptleri, eksik `inputs/` ve `outputs/` dizinlerini ilk çalıştırmada otomatik olarak oluşturur.
