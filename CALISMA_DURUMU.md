# NFL Big Data Bowl 2027 — Güncel Çalışma Durumu ve Teslim Özeti

## Ana Yarışma Teslim Adayı: Offensive Line Combine Faz Doğrulaması (`submission_mirror/`)

Projedeki tüm pozisyon grupları (`OL`, `WR`, `TE`, `DL`, `DB`) ve `43` Combine drili uçtan uca denetlenmiş; yarışmada en yüksek metodolojik özgünlük, futbol geçerliliği ve istatistiksel disiplini sağlayan **Offensive Line Combine Faz Ayrıştırması ("The Fastest Part Is the Exit")** çalışması ana teslim paketi (`submission_mirror/`) olarak en üst seviyeye taşınmıştır.

### 1. Temel Araştırma Sorusu ve Somut Keşif

- **Soru:** NFL Scouting Combine'da Offensive Lineman (`C/G/T`) pas koruma ve ayak işi drillerinden çıkarılan hız metrikleriyle oyuncuları sıraladığımızda, gerçekten yanal pas koruma çevikliğini mi ölçüyoruz, yoksa dril sonundaki düz çıkış sprintini mi?
- **Evrensel Ölçüm Bulgusu (`470 / 470` Kayıt = `%100.0`):**
  - **Pass-Pro Mirror Drill (`113` oyuncu, `113` kayıt):** Kayıtların **%100.0'ında (`113/113`)** en yüksek hız yanal ayna fazında değil, `+1.5 yard` sınırından sonraki **çıkış sprintinde** oluşmaktadır. Yanal hız ile tüm-kayıt hızı sıralamalarının Spearman korelasyonu **`r = +0.005`**'tir (2025 üst çeyrekteki 9 oyuncudan yalnız 1'i ortaktır; örn. Donovan Jackson `+91.2 yp`, Dominick Puni `+88.1 yp`, Darnell Wright `−89.2 yp`, Tyler Booker `−94.1 yp` sıra değiştirmektedir).
  - **5-Yard Wave Drill (`118` oyuncu, `118` kayıt):** Kayıtların **%100.0'ında (`118/118`)** zirve hız çıkış sprintindedir; yanal faz hızı ile tüm-kayıt hızı korelasyonu **`r = −0.022`**'dir.
  - **Pass Rush Drop (`120` oyuncu, `239` kayıt):** Kayıtların **%100.0'ında (`239/239`)** zirve hız bitiş sprintindedir; pas seti yanal hızı ile tüm-kayıt hızı korelasyonu **`r = +0.147`**'dir.
- **Tekrar Güvenilirliği (Repeatability) ve Psikometrik Zayıflama Sınırı:**
  - `Pass Rush Drop` drilinde ikişer kaydı bulunan **118 OL oyuncusunda** çıkış sprinti hızı denemeden denemeye **`r = +0.510`** güvenilirlikle tekrarlanırken, koç/işaret yönlendirmeli pas seti yanal hızı yalnızca **`r = +0.104`** tekrar güvenilirliğine sahiptir. Bu bulgu, standartlaştırılmamış koç komutlarıyla yapılan tek tekrarlı dril ölçümlerinin maç tahmin gücünün neden psikometrik olarak sınırlandığını ($r_{XY} \le \sqrt{r_{XX} \cdot r_{YY}}$) matematiksel olarak açıklar.

### 2. Dört Aşamalı Doğrulama Hunisi ve Maç Sonuçları (`50` Çaylak OL, `20.853` Bire Bir Snap)

1. **Faz Ayrıştırma ve Fiziksel Değişmezlik:** `1.0`, `1.5` ve `2.0 yard` sınırlarında sıralama kararlılığı `Spearman r > 0.992`; 7 sentetik fiziksel değişmezlik testi (`translation`, `reflection`, `timestamp_shift`, `row_order` vb.) eksiksiz geçti.
2. **İleri-Yıl Bire Bir Pas Koruması (`2023 -> 2024` ve `2023–2024 -> 2025`):**
   - **Birincil Hedef (İkili `pressure_allowed`, Süre Düzeltmeli):** 2025 testinde çıkış sprintiyle kirlenmiş tüm-kayıt hızı MAE'yi kötüleştirirken (`2.502 -> 2.652 pp`), faz ayrıştırmalı mirror özellikleri MAE'yi `2.502`'den `2.482 pp`'ye (`+0.019 pp`) indirir. 400 tam yeniden eğitimli (full-refit) oyuncu bootstrap %95 güven aralığı **`[−0.264, +0.353] pp`** olup sıfırı içerir.
   - **Sürekli NGS Hedef Duyarlılığı (`peak_pressure_probability_allowed`):** Yarı-yarıya (split-half) maç güvenilirliği ikili baskıda `r = 0.367` iken sürekli NGS baskı olasılığında **`r = 0.696`**'ya yükselir. Bu daha yüksek güvenilirlikli hedefte de 2025'te tüm-kayıt hızı hatayı artırırken (`2.189 -> 2.215 pp`), mirror fazı özellikleri MAE'yi `2.189`'dan `2.157 pp`'ye (`+0.032 pp`, RMSE `2.639 -> 2.532 pp`) düşürür (%95 GA `[−0.139, +0.195] pp`).
3. **Ara Hareket Kontrolü (`0–1.5 s` Maç İçi Erken Yanal Hız, `20.110` Oyun):** Maç içi yanal hız maçtan maça çok kararlıdır (`split-half r = 0.797`), ancak Combine mirror yanal hızıyla korelasyonu düşüktür (`ham r = 0.053`, `yıl/pozisyon arındırılmış r = 0.120`) ve ileri-yıl MAE'yi düşürmez.

---

## İkinci (Yedek) Çalışma Adayı: Wide Receiver Hız Transferi (`submission/`)

- **Kapsam:** `58` çaylak WR (`10.944` rota oyunu) ve `81` çift denemeli WR Combine `40-yard dash` kaydı.
- **Sonuç:** Combine zirve hızı yüksek tekrar güvenilirliğine (`r = 0.893`) ve maç rota hızıyla anlamlı korelasyona (`r = 0.382`) sahiptir; ancak klasik `40-yard` süresini (`r = −0.852`) büyük ölçüde kopyaladığı için ileri-yıl tahmininde 2024'te MAE'yi iyileştirirken (`0.1808 -> 0.1535 yd/s`), 2025'te iyileştirmez (`0.1405 -> 0.1442 yd/s`).

---

## Temel Dosyalar ve Paketler

- **Ana Teslim Klasörü:** `submission_mirror/` (`writeup_en.md`, `mirror_phase_validation.ipynb`, `mirror_phase_validation.executed.ipynb`, `mirror_explorer.html`, `figures/`, `verification.json`, `manifest.json`)
- **Ana Teslim ZIP Arşivi:** `NFL_2027_mirror_arastirma_paketi.zip`
- **Yedek WR Teslim Klasörü ve ZIP Arşivi:** `submission/` ve `NFL_2027_teslim_paketi.zip`
- **Tüm Deneylerin Kayıt Defteri:** `reports/experiment_register.md`
