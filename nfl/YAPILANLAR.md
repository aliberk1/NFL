# Yapılan çalışmanın teknik dökümü

**Hazırlayan:** [Ad Soyad] · **Tarih:** 27 Kasım 2026 · **Branch:** `task/nfl-tahmin-modelleri`

Bu belge, NFL projesinin ilk aşamasında yapılan tüm işi teknik ayrıntılarıyla anlatır. Amaç,
ekipteki herkesin kodu açmadan neyin, neden ve nasıl yapıldığını anlayabilmesi ve aynı sonuçları
yeniden üretebilmesidir. Bütün sayılar `nfl/ciktilar/` altındaki çıktılardan alınmıştır.

---

## 1. Problem tanımı

**Araştırma sorusu:** Bir NFL oyuncusunun verisinden, ileride takımında kalıcı rol edinip
edinmeyeceği tahmin edilebilir mi; hangi veri kaynağı (draft kararı, Combine ölçümleri, Combine
sensör kayıtları, çaylak sezonu maç verisi) bu tahmine gerçekten bilgi katar?

**Kısıtlar:**
- Yalnızca NFL Big Data Bowl 2027 yarışma verisi (dış veri yok).
- Her iddia, kod çıktısıyla doğrulanır; sonradan hipotez değiştirilmez (ön kayıt: `TASARIM.md`).

**Problem türleri:** ikili sınıflandırma (A, ileri tahmin, B1), regresyon (A2), çok sınıflı
zaman serisi sınıflandırması (C1).

---

## 2. Veri altyapısı

### 2.1 Ham veri ve bütünlük denetimi

Ham veri (yaklaşık 2,2 GB, 9 CSV) `data/nfl-big-data-bowl-2027/` altındadır (yerelde
`NFL PROJECT/nfl-big-data-bowl-2027/` klasörüne sembolik bağ). Yapılan bütünlük kontrolleri:

| Kontrol | Sonuç |
|---|---|
| Satır yapısı (sütun sayısı) | 22,6 milyon takip satırında bozuk satır yok |
| Birincil anahtar tekilliği | `players`, `combine_results`, `player_career_successes`: 510 tekil `nfl_id` |
| Yabancı anahtar bütünlüğü | Tüm dosyalardaki `nfl_id` → `players.csv`; tüm `game_id` → `games.csv` |
| Sezon tutarlılığı | Her `game_tracking_<yıl>.csv` yalnız kendi sezonunun maçlarını içerir |
| Kapsam | 510 oyuncunun 497'sinin `player_play` kaydı var (13 oyuncu hiç oynamamış) |

| Dosya | Satır | İçerik |
|---|---|---|
| `players.csv` | 510 | Draft yılı (2023: 160, 2024: 177, 2025: 173), pozisyon, draft sırası (127 oyuncu draft edilmemiş) |
| `combine_results.csv` | 510 | Combine ölçümleri; ör. `forty` %17, `three_cone` %65 eksik |
| `combine_tracking.csv` | 463.189 | Drill sensör kayıtları, 10 Hz (x, y, s, a, dis, dir), 56 drill türü |
| `game_tracking_2023/24/25.csv` | 3,7 / 7,8 / 11,2 milyon | Maç sensör kayıtları, 10 Hz, **yalnız bu 510 oyuncu** (22 oyuncunun tamamı değil) |
| `player_play.csv` | 314.197 kayıt | Oyuncu-oyun istatistikleri (rota, baskı, hedeflenme vb.) |
| `player_career_successes.csv` | 510 | Kariyer toplamları (2025 sonuna kadar; sezonlara bölünmemiş) |

### 2.2 Ortam

- Python 3.9.6 (makinede tek sürüm). Depodaki `requirements.txt` numpy 2.2.6 istediği için
  (Python ≥ 3.10) ayrı bir sanal ortam `.venv-ml` kuruldu; sürümler `requirements-ml.txt`'te sabit.
- PyTorch 2.8, Apple M4 GPU (MPS backend). CNN eğitimleri MPS'te, sklearn modelleri CPU'da.
- Streamlit uygulaması da aynı ortamdan çalışır (`python -m pipelines.ingest` → DuckDB;
  `streamlit run app/ui.py`). Uygulama test paketi: 100 testten 99'u geçti; başarısız olan
  `tests/test_similarity.py`, Python 3.10'a özgü `zip(..., strict=True)` kullanıyor (ortam kaynaklı).

---

## 3. Yazılım mimarisi (`nfl/`)

Modüler bir analiz hattı (pipeline). Her görev betiği aynı modülleri kullanır:

```
veri.py ──► ozellikler.py ──┐
            sezon.py ───────┼──► modeller.py ──► degerlendirme.py ──► grafikler.py ──► RAPOR.md
                            │    (fit/predict      (CV, metrik,         (PNG)            + CSV
                            │     arayüzü)          istatistik)
gorev_a.py / ileri_tahmin.py / gorev_a2.py / gorev_b1.py / gorev_c1.py  (orkestrasyon)
```

**Tasarım kararları:**
- **Ortak model arayüzü:** her model `fit(ctx, idx)` / `predict(ctx, idx)` uygular; `ctx` =
  `{X: DataFrame, y: ndarray, seq: dizi sözlüğü}`. Böylece sklearn ve PyTorch modelleri aynı CV
  döngüsünde, aynı bölmelerle karşılaştırılır.
- **Veri sızıntısı (data leakage) önleme:** ön işleme (`SimpleImputer(median, add_indicator=True)` +
  `StandardScaler`) bir `Pipeline` içinde yalnız eğitim katmanında `fit` edilir. CNN'in tablo girdisi
  de aynı şekilde. Combine takip z-skorları drill içinde etiket kullanmadan (denetimsiz) hesaplanır.
- **Tekrarlanabilirlik:** sabit rastgelelik tohumları (`seed = tekrar*100 + katman`), sabit
  model hiperparametreleri, önbelleğe alınmış ara diziler (`ciktilar/cache/*.npz`).
- **Otomatik raporlama:** her betik tabloları ve grafikleri kendisi üretir; rapordaki sayılar elle yazılmaz.

### 3.1 Özellik mühendisliği (feature engineering)

| Özellik seti | İçerik |
|---|---|
| **Draft** | `log(draft sırası)`, draft edilmeme bayrağı (sıra = 262), tur |
| **Bağlam** | Draft yaşı, draft sınıfı kukla değişkenleri, pozisyon grubu kukla değişkenleri (OL/DL/LB/DB/WR/TE) |
| **Combine** | 12 ölçüm + BMI + speed score (`ağırlık·200/forty⁴`) + NGS atletizm skoru |
| **Combine takip özeti** | Her deneme için tepe hız/ivme, ortalama hız, süre, ortalama dönüş hızı; drill içinde z-skoru; oyuncu başına en iyi deneme, drill'ler üzerinden ortalama; ayrıca 40 yarda / 3-cone / shuttle tepe hız-ivme |
| **Combine ham dizileri (CNN)** | Deneme başına `[s, a, dönüş hızı, kümülatif mesafe]`, 10 Hz, en fazla 160 kare, global standartlaştırma; 6.310 deneme |
| **Çaylak sezonu (B1)** | `player_play` normal sezon: snap, maç, maç başına snap, hücum payı, hedeflenme, rota sayısı, yakalama/koşu yardı, sack, tackle, baskı yeme oranı, rota başına hedeflenme; maç takip verisinden oyun başına tepe hız/ivme ortalaması ve 90. yüzdelik |
| **Rota dizileri (C1)** | Snap anından 35 kare (3,5 sn): `[dx, dy, vx, vy, s, a]`; oyun yönüne göre döndürme, başlangıca öteleme, saha merkezine göre aynalama (iç/dış) |

### 3.2 Modeller

| Model | Tür | Ayarlar (sabit) |
|---|---|---|
| Dummy | Taban çizgisi | Sınıf önceliği / ortalama / en sık sınıf |
| Lojistik Regresyon | Doğrusal, L2 | `C=0.3` (C1'de 1.0) |
| Ridge | Doğrusal regresyon, L2 | `alpha=3` |
| kNN | Örnek tabanlı | `k=25`, uzaklık ağırlıklı |
| SVM / SVR | RBF çekirdek | `C=1` |
| Rastgele Orman | Bagging, ağaç topluluğu | 500 ağaç (C1: 300), `min_samples_leaf=3` |
| Gradient Boosting | Histogram tabanlı boosting | `lr=0.05`, `max_depth=3`, 200 iterasyon, L2=1 |
| MLP | İleri beslemeli sinir ağı | 32 gizli birim (C1: 128-64), `alpha=1`, erken durdurma |
| **1D-CNN (set-of-sequences)** | Derin öğrenme, PyTorch | Deneme kodlayıcı: 3 × Conv1d (32-32-64 kanal, çekirdek 5/5/3, ikincisi dilation=2) + BatchNorm + ReLU, maskeli ortalama+max havuzlama, drill gömmesi (8 boyut); oyuncu düzeyinde maskeli ortalama; AdamW (lr 2e-3, wd 1e-3), %15 iç doğrulama ile erken durdurma (sabır 12) |
| **CNN-Hibrit** | Derin öğrenme + tablo | CNN gömmesi ⊕ standartlaştırılmış tablo özellikleri → MLP başlık |
| **Rota 1D-CNN (C1)** | Derin öğrenme | 3 × Conv1d (64-64-128, dilation 1/2/2) + BatchNorm, maskeli ortalama+max havuzlama, dropout 0,3; AdamW, %10 iç doğrulama, sabır 6, en fazla 40 epoch |

Sınıf ağırlıklandırması kullanılmadı (olasılık kalibrasyonunu ve Brier skorunu bozmaması için).

### 3.3 Değerlendirme ve istatistik

| Yöntem | Kullanım |
|---|---|
| Tekrarlı tabakalı k-katlı CV | 5 katman × 5 tekrar = 25 test (A, A2, B1); ileri tahminde 5 × 10 |
| Gruplu k-katlı CV | C1: oyuncuya göre gruplama (`GroupKFold`), aynı oyuncu hem eğitimde hem testte olmaz |
| Zamana dayalı doğrulama (temporal validation) | A: sınıf dışarıda bırakma; ileri tahmin ve B1: 2023 → 2024; C1: 2023–24 → 2025 |
| Metrikler | ROC-AUC, PR-AUC (average precision), Brier skoru, log-loss; regresyonda R², MAE, RMSE, Spearman; C1'de makro-F1, doğruluk, sınıf bazında F1, karışıklık matrisi |
| Friedman testi | Çok sayıda modelin katman skorlarında genel fark |
| Nadeau-Bengio düzeltilmiş tekrarlı t-testi | İki model arasındaki fark; CV katmanlarının bağımlılığı için varyans düzeltmesi `(1/J + n_test/n_train)` |
| Holm-Bonferroni | Çoklu karşılaştırma düzeltmesi |
| Eşli bootstrap (2000 tekrar) | OOF tahminleri üzerinde AUC/R² farkı ve %95 güven aralığı |
| McNemar testi | C1 zaman testinde iki sınıflandırıcının hata desenleri |
| Permütasyon önemi | Özellik katkısı (AUC kaybı) |
| Kalibrasyon eğrisi | Tahmin edilen olasılık ile gerçekleşen oran |

---

## 4. Görevler ve sonuçlar

### 4.1 Görev A: Draft öncesi veriden kalıcı starter tahmini (`gorev_a.py`)

- **Hedef:** `start_rate = ilk 11 başladığı maç / (17 × oynanabilir sezon) ≥ 0.5` → 103 / 510 (%20,2).
- **Hedef geçerliliği:** 12 All-Pro / Pro Bowl oyuncusunun 11'i pozitif sınıfta. Ödül tek başına
  hedef olamaz (12 örnek).
- **Dayanıklılık hedefleri:** eşik 0.4 (123 pozitif), 0.6 (83), pozisyon grubu × draft sınıfı
  içinde sezon başına snap'te ilk %20 (111).
- **24 model** = 4 özellik seti × 6 sklearn modeli + Dummy + 3 CNN varyantı; 5×5 CV.

| Özellik seti | En iyi model | AUC | PR-AUC | Brier |
|---|---|---|---|---|
| Draft | LogReg | **0,916** | 0,756 | 0,092 |
| Combine+Takip+Draft | CNN-Hibrit | 0,903 | 0,736 | 0,097 |
| Combine | LogReg | 0,745 | 0,489 | 0,139 |
| Combine+Takip | LogReg | 0,733 | 0,473 | 0,142 |
| Takip dizisi | 1D-CNN | 0,565 | 0,280 | 0,161 |

- Friedman χ² = 474,0, p = 1,9·10⁻⁸⁶.
- Draft referansına göre hiçbir Combine/Takip içeren model daha iyi değil (fark ≤ 0; en yakın:
  CNN-Hibrit −0,012, Holm p = 0,39).
- Sınıf dışarıda bırakma (Draft LogReg): 2023 0,921 · 2024 0,925 · 2025 0,894.
- Dayanıklılık: Draft en iyi set, 4 hedefin hepsinde (0,916 / 0,882 / 0,913 / 0,881).
- Pozisyon bazında Draft AUC: OL 0,970, TE 0,902, LB 0,893, DB 0,891, DL 0,879.
- Ödüllü oyuncuların Draft modelindeki ortalama yüzdeliği 0,859; Combine modelinde 0,684.
- Permütasyon önemi (Combine+Takip): en etkili özellik **draft yaşı** (AUC kaybı 0,129).

### 4.2 Gelecek tahmini: ilk 3 sezonda kalıcı starter (`ileri_tahmin.py`)

- 3 sezonu tamamen gözlenen tek sınıf olan 2023 (160 oyuncu, 36 pozitif) ile eğitim.
- Model seçimi (önceden belirlenen kural, 5×10 CV): **Draft LogReg, AUC 0,921** [0,860; 0,958].
- Zaman kontrolü (2023 → 2024, 2 sezonluk yaklaşık hedef): AUC 0,925.
- 2024 ve 2025 sınıflarındaki 350 oyuncu için 3 sezonluk olasılık tahmini
  (`gelecek_tahminleri.csv`); sonuçlar 2026 ve 2027 sezonu sonunda doğrulanabilir.

### 4.3 A2: Sezon başına snap sayısı, regresyon (`gorev_a2.py`)

| Özellik seti | En iyi model | R² | MAE (snap) | Spearman |
|---|---|---|---|---|
| Draft | Ridge | **0,541** | 156,7 | 0,753 |
| Combine+Takip+Draft | RandomForest | 0,533 | 164,7 | 0,743 |
| Combine | RandomForest | 0,204 | 222,8 | 0,440 |
| Ortalama tahmini | Dummy | −0,003 | 259,6 | — |

**H-A2 (Combine, Draft'a anlamlı katkı yapmaz): desteklendi.**

### 4.4 B1: Çaylak sezonundan sonraki sezon (`gorev_b1.py`)

- Hedef: sonraki normal sezonda `player_play` snap sayısının kendi draft sınıfı ve pozisyon grubu
  içinde ilk %25'te olması. 337 oyuncu (2023 ve 2024 sınıfları), 90 pozitif.
- Önemli veri notu: `player_play` normal sezon kayıtları kariyer hücum snaplerinin ~%79'unu,
  savunma snaplerinin %100'ünü kapsar (Pearson r = 0,96).

| Özellik seti | En iyi model | AUC |
|---|---|---|
| Draft + Çaylak | LogReg | **0,911** |
| Draft + Çaylak + Combine | RandomForest | 0,895 |
| Çaylak | LogReg | 0,884 |
| Draft | LogReg | 0,883 |

- Draft+Çaylak − Draft: +0,028 AUC; bootstrap %95 GA [0,007; 0,056]; düzeltilmiş t-testi p = 0,076;
  Holm p = 1,0. Zaman testi (2023 → 2024): 0,899 → 0,909.
- **H-B1 (çaylak sezonu anlamlı katkı yapar, Holm p < 0,05): desteklenmedi.** Yön pozitif, etki küçük.
- 2025 sınıfı için 2026 sezonu tahmini üretildi (`tahmin_2026.csv`).

### 4.5 C1: Maç hareket kaydından rota tanıma (`gorev_c1.py`)

- 52.930 oyuncu-oyun, 11 sınıf (10 rota + DİĞER: WHEEL, ANGLE), 156 oyuncu.
- Ön işleme doğrulandı: medyan son konum GO +16,2 yarda ileri; IN +4,1 yarda içeri; OUT −8,2 yarda dışarı.

| Model | Makro-F1 (gruplu 5-katlı) | Doğruluk |
|---|---|---|
| **1D-CNN** | **0,735** | 0,822 |
| MLP | 0,697 | 0,781 |
| Gradient Boosting | 0,680 | 0,757 |
| Rastgele Orman | 0,672 | 0,751 |
| LogReg | 0,636 | 0,728 |
| kNN | 0,632 | 0,713 |
| En sık sınıf | 0,028 | 0,183 |

- CNN her modelden anlamlı biçimde iyi (düzeltilmiş t-testi + Holm, en büyük p = 0,0075).
- Zaman testi (2023–24 → 2025): CNN 0,728, MLP 0,697; McNemar p = 1,1·10⁻⁷⁰.
- Sınıf bazında F1 (CNN, 2025): CROSS 0,86, OUT 0,85, HITCH 0,84, FLAT 0,84, GO 0,84, CORNER 0,81,
  IN 0,80, POST 0,77, SLANT 0,72, SCREEN 0,68, DİĞER 0,00 (74 örnek).
- **H-C1 (CNN özellik tabanlı modellerden iyi): desteklendi.**

---

## 5. Bulguların özeti

1. **Draft öncesi tahminde en güçlü sinyal draft sırasıdır** (AUC 0,92, R² 0,54). Combine ölçümleri
   ve Combine sensör kayıtları tek başına bilgi taşır (AUC 0,75) ancak draft sırasına ek bilgi katmaz.
   Bu sonuç 4 hedef tanımında, sınıf dışarıda bırakma testinde ve regresyonda tekrarlanır.
2. **Çaylak sezonu verisi** tahmini küçük ölçüde iyileştirir (+0,028 AUC) ama önceden belirlenen
   anlamlılık ölçütünü geçmez.
3. **Derin öğrenme veri miktarına bağlıdır:** 510 oyunculuk Görev A'da ham dizi CNN'i şansa yakın
   (0,565), 52.930 örnekli C1'de en iyi model (makro-F1 0,735).

## 6. Bilinen sınırlar

- Örnekler küçük (Görev A: 510; ileri tahmin: 160 eğitim oyuncusu); güven aralıkları buna göre okunmalı.
- Model hiperparametreleri aranmadı (adil karşılaştırma için sabit tutuldu).
- Kariyer toplamları sezonlara bölünmemiştir; B1 hedefi `player_play`'den hesaplanır ve hücum
  snaplerinin bir kısmını kaçırır.
- Maç takip verisi yalnız bu 510 oyuncuyu içerir; rakip/top konumu yoktur (C1'de iç/dış yönü
  saha merkezine göre yaklaşık).
- 2024–2025 gelecek tahminleri bugün doğrulanamaz.
- Görev A'nın hipotezi önceden yazılmamıştır; A2, B1, C1 için ön kayıt `TASARIM.md`'dedir.

## 7. Diğer çıktılar

- **Hoca sunumu (14 slayt, konuşmacı notlu):** Ã§evrim iÃ§i slayt belgesi; şu an yalnız sahibine
  açık, paylaşım ve PDF/PPTX dışa aktarma sayfanın Paylaş menüsünden yapılır. A2, B1 ve C1
  sonuçları henüz sunumda yok (bkz. `GOREVLER.md`).
- **Streamlit uygulaması:** yerelde gerçek veriyle çalıştırıldı; sohbet sekmesi Gemini
  (`gemini-3.5-flash-lite`, OpenAI uyumlu uç nokta) ile test edildi. Tahmin modelleri henüz
  uygulamaya bağlı değil (bkz. `GOREVLER.md`).
