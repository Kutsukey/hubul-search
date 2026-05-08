# Hubul | Hacettepe Akıllı Asistan (Search Engine)

Hacettepe Üniversitesi birimleri, duyuruları ve öğrenci işlemleri için geliştirilmiş, LLM destekli hibrit arama motoru.

## 🚀 Proje Durumu: "Jilet" Edition (v4.0)

Şu anki geliştirme aşamasında sistemin ana omurgası kurulmuş ve arama performansı optimize edilmiştir.

### 🏆 YAPILDI (Jilet Gibi Çalışanlar)
*   **[✓] Crawler'ı Dizginlemek:** Hantal ve tüm üniversiteyi tarayıp çöp toplayan A-Z tarayıcısı optimize edildi. Sadece `seed_urls` odaklı, temiz tarama mantığına geçildi.
*   **[✓] Subdomain Enjeksiyonu:** URL'lerdeki `cs`, `oidb`, `ee` gibi kıymetli kısaltmalar backend'de yakalanıp `search_alias` olarak arama indeksine gömüldü.
*   **[✓] Hiyerarşik Puanlama (Priority Score):** Tıp Fakültesi (+100) ile Seçmeli Dersler Koordinatörlüğü (-20) arasındaki ayrım yapıldı. Öğrencilerin en çok aradığı ana bölümler her zaman zirveye sabitlendi.
*   **[✓] UI Kurumsal Gürültü Temizliği:** Arayüzü şişiren "Hacettepe Üniversitesi" kelimeleri Regex ile temizlendi, kartlar sadeleştirildi.
*   **[✓] Frontend Mantıksal Arama ($and):** Fuse.js'in "cs ders" gibi çoklu kelimeleri hatalı algılama sorunu çözüldü. Kelimeler parçalanıp `$and` operatörü ile aratılıyor.
*   **[✓] UI Dolgu (Filler) Kartları:** Arama yapılmadan önce veya boş aramalarda gösterilecek "Sık Kullanılanlar / Son Ziyaret Edilenler" (localStorage tabanlı) mantığı eklendi.

### ⏳ YAPILMADI / BEKLEMEDE (Gelecek Vizyonu)
*   **[✓] AI Gatekeeper (Otonom Onay):** Yeni bulunan alt alan adlarını (subdomain) LLM'e sorup, sadece "Kalıcı Kurum" olanları seed listesine otomatik ekleyen otonom döngü pipeline'a entegre edildi.
*   **[ ] Çift Dilli (TR/EN) Birleştirme:** `validator.py` üzerinden İngilizce ve Türkçe departman linklerini aynı obje altında birleştirme (Örn: "cs courses" yazınca da aynı yerin çıkması).
*   **[ ] Hayalet Site Temizliği:** 2024 öncesinden kalma, güncel hiçbir intent barındırmayan müze kıvamındaki siteleri JSON'dan otomatik uçurma filtresi geliştirilecek.
*   **[ ] JSON Cache (İleriki Aşama):** Sayfa her yenilendiğinde JSON'ı tekrar fetch etmek yerine kullanıcının tarayıcı belleğine (IndexedDB) yazıp oradan okutmak.

## 🛠️ Teknoloji Yığını
*   **Frontend:** Vanilla JS, Fuse.js (Search Engine)
*   **Backend/Crawler:** Python, Crawl4AI, Playwright
*   **AI/LLM:** Google Gemini (Gemma-4 model)
*   **Workflow:** GitHub Actions

---
*Bu dosya projenin mevcut durumunu yansıtmak üzere otomatik olarak güncellenmektedir.*
