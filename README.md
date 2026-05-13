# Hubul

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

- [x] Ana veri üretim hattı, seed listesi ve LLM tabanlı keşif akışı kuruldu
- [x] Playwright ve Trafilatura ile dinamik/semantik içerik ayıklama eklendi
- [x] `search_alias`, SEO enjeksiyonu ve `priority_score` optimizasyonları yapıldı
- [x] Çok kelimeli arama ($and) ve bitişik karakter eşleşme (Shield) mantığı uygulandı
- [x] Günlük duyuru senkronizasyonu ve haftalık `audit_pipeline` otomatize edildi
- [x] EGO "Otobüs Nerede" sistemi için dinamik yönlendirme kartı entegre edildi
- [x] URL temizliği (www stripping) ve gereksiz domain filtrelemeleri sağlandı
- [x] Widget tarafına geçmiş takibi, "Geçmişi Temizle" ve UI sadeleştirmeleri yapıldı
- [x] Crawler stabilizasyonu için timeout ve hata toleransları artırıldı

## Yapılması Beklenenler

- [ ] TR / EN sayfaların tek bir kurumsal kayıt altında birleştirilmesi
- [ ] Duyuru içeriklerinde tam metin arama desteği ve UI entegrasyonu
- [ ] Frontend tarafında büyük veriler için JSON cache mekanizması
- [ ] Mobil uyumluluk ve erişilebilirlik iyileştirmeleri

## Katkıda Bulunmak İçin

Katkı verirken şu akış genelde daha sağlıklı:

1. Önce `public/outputs/` altındaki JSON yapısını inceleyin.
2. Crawler veya utility tarafında dar kapsamlı bir değişiklik yapın.
3. Tüm pipeline'ı çalıştırmak yerine mümkünse sadece ilgili modülü test edin.
4. JSON farkını gördükten sonra arayüzü açıp sonucu manuel kontrol edin.

Dikkat edilmesi gereken yerler:

- kurumsal eşleşmelerde false positive üretmemek
- kırık link oluşturabilecek selector veya kural değişiklikleri
- fazla jenerik duyuru seçicileri
- aynı birimin birden fazla kayıt halinde görünmesi

## Geliştirici Notları

- Repo içinde eski veya deneysel crawler dosyaları bulunuyor; hepsi aktif akışın parçası değil.
- Frontend tarafı build tool kullanmıyor; doğrudan statik dosya olarak çalışıyor.
- Bazı scriptler çalışma sırasında eksik `inputs/` ve `outputs/` dizinlerini kendileri oluşturuyor.
