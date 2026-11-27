# Ön kayıt: A2, B1 ve C1 görevlerinin tasarımı

Bu dosya **sonuçlar görülmeden önce** yazıldı (27 Kasım 2026). Hipotezler, hedefler, ölçütler
ve model seçme kuralı burada sabitlenir; sonuçlar ayrı raporlarda bu dosyayla karşılaştırılır.
Sonradan yapılan her değişiklik bu dosyanın sonuna tarihiyle eklenir.

## Ortak kurallar

- Yalnızca NFL Big Data Bowl 2027 yarışma verisi kullanılır.
- Ön işleme (doldurma, ölçekleme) yalnızca eğitim verisinde öğrenilir.
- Model ayarları sabittir; ayar araması yapılmaz.
- Model karşılaştırması: Friedman testi (ikiden fazla model), Nadeau-Bengio düzeltilmiş t-testi +
  Holm düzeltmesi (referansa karşı), eşli bootstrap güven aralığı.

---

## A2: Sezon başına snap sayısı (sayı tahmini / regresyon)

- **Soru:** Draft öncesi bilgilerle oyuncunun NFL'de sezon başına kaç snap oynayacağı tahmin edilebilir mi?
- **Birim:** oyuncu (510).
- **Hedef:** `(career_offensive_snaps + career_defensive_snaps) / oynanabilir sezon`.
- **Girdiler:** Görev A ile aynı 4 bilgi seti (Draft, Combine, Combine+Takip, Combine+Takip+Draft).
- **Modeller:** Ortalama (referans taban), Ridge, kNN, SVR, Rastgele Orman, Gradient Boosting, MLP.
- **Doğrulama:** 5-katlı × 5 tekrar; tabaka = draft yılı × hedefin çeyreği.
- **Ana ölçüt:** R² (katman ortalaması). Ek: MAE, Spearman sıra korelasyonu.
- **Referans:** R²'si en yüksek Draft modeli.
- **Hipotez H-A2:** Görev A ile tutarlı olarak, Combine/Takip bilgisi Draft modelinin R²'sini anlamlı
  biçimde artırmaz (Holm p ≥ 0.05).

## B1: Çaylak sezonundan sonraki sezonu tahmin

- **Soru:** Oyuncunun çaylak sezonundaki maç verisi, draft sırasının ötesinde, bir sonraki sezonda
  ne kadar oynayacağını tahmin etmeye yardım eder mi?
- **Birim:** oyuncu; 2023 sınıfı (çaylak 2023 → hedef 2024) ve 2024 sınıfı (çaylak 2024 → hedef 2025).
  Çaylak sezonunda hiç oynamayan oyuncular da dahildir (özellikleri 0).
- **Hedef (ana):** sonraki normal sezonda, `player_play` kayıtlarındaki snap sayısının kendi draft
  sınıfı ve pozisyon grubu içinde **ilk %25**'te olması (ve > 0). Kariyer toplamları sezonlara
  bölünmediği için hedef oyun kayıtlarından hesaplanır. Not: `player_play` hücum snaplerinin kariyer
  toplamının yaklaşık %79'unu, savunmanın %100'ünü kapsar (kontrol edildi).
- **Hedef (ek):** sonraki sezonun snap sayısı (log ölçeğinde regresyon).
- **Girdiler:**
  - Draft: Görev A'nın draft özellikleri.
  - Çaylak sezonu: snap, maç, maç başına snap, hücum/savunma payı, hedeflenme, yakalama yardı,
    baskı yeme oranı, sack, tackle ve maç hareket kaydından oyun başına en yüksek hız/ivme ortalaması.
  - Birleşik: Draft + Çaylak sezonu (+ Combine).
- **Modeller:** LogReg, Rastgele Orman, Gradient Boosting, SVM, kNN, MLP.
- **Doğrulama:** (1) 5-katlı × 5 tekrar; (2) **zaman testi:** 2023 sınıfıyla eğit, 2024 sınıfında test et.
- **Ana ölçüt:** ROC-AUC.
- **Referans:** en iyi Draft modeli.
- **Hipotez H-B1:** Çaylak sezonu bilgisi Draft modeline göre AUC'yi anlamlı biçimde artırır (Holm p < 0.05).
- **Gelecek tahmini:** seçilen model 2025 sınıfına uygulanır (çaylak 2025 → 2026, henüz bilinmiyor).

## C1: Rota tanıma (oyun bazında, CNN)

- **Soru:** Bir oyuncunun maç hareket kaydından koştuğu rota tanınabilir mi; CNN, el ile çıkarılan
  özelliklerle çalışan modellerden daha mı iyi?
- **Birim:** oyuncu-oyun; `route_ran` etiketi ve hareket kaydı olan kayıtlar (~53 bin).
- **Girdi:** topun oyuna girdiği an (`ball_snap`) ile sonraki 3,5 saniye (35 kare). Konum başlangıca
  göre kaydırılır; oyun yönü sağa çevrilir. Saha merkezine göre yan taraf aynalanır (sağ/sol yerine
  iç/dış). Not: hareket kayıtlarında top konumu olmadığı için iç/dış ayrımı saha merkezine göre
  **yaklaşık** yapılır.
- **Sınıflar:** en az 300 örneği olan rota türleri; diğerleri "DİĞER".
- **Modeller:** En sık sınıf (taban), LogReg, kNN, Rastgele Orman, Gradient Boosting, MLP
  (el ile çıkarılan özellikler), **1D-CNN** (ham dizi).
- **Doğrulama:** (1) oyuncuya göre gruplu 5-katlı (aynı oyuncu hem eğitimde hem testte olmaz);
  (2) **zaman testi:** 2023–2024 ile eğit, 2025'te test et.
- **Ana ölçüt:** makro-F1 (tüm sınıflara eşit ağırlık). Ek: doğruluk, sınıf bazında F1, karışıklık matrisi.
- **Hipotez H-C1:** 1D-CNN, en iyi özellik tabanlı modelden daha yüksek makro-F1 verir
  (zaman testinde McNemar testi p < 0.05).
