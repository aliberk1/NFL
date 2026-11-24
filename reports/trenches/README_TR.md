# OL Combine Faz Doğrulaması — Ana Yarışma Teslim Çalışması

## Genel Bakış

Bu çalışma, **NFL Big Data Bowl 2027 ("Combine to NFL Performance")** için ana yarışma teslim adayı (`submission_mirror/`) olarak geliştirilmiş ve genişletilmiştir. Çalışma, Offensive Line (`C/G/T`) Combine takip verilerinde dril içi faz ayrıştırmasının (phase segmentation) neden zorunlu olduğunu ve yeni bir takip metriğinin draft kararlarında kullanılmadan önce hangi dört aşamalı doğrulama hunisinden geçmesi gerektiğini ortaya koyar.

### 1. Evrensel Ölçüm Bulgusu: 3 OL Drilinde 470 / 470 Kayıtta Çıkış Sprinti Baskınlığı

- **Pass-Pro Mirror Drill:** 121 OL oyuncusunun kaydı incelendi; kalite ve en az iki yön değişimi kriterlerini geçen **113 kaydın 113'ünde (%100.0)** en yüksek hız yanal ayna fazında değil, `+1.5 yard` sınırından sonraki **çıkış sprintinde** oluşmaktadır. Yanal hız ile tüm kayıt hızı sıralamalarının Spearman korelasyonu **`r = +0.005`** düzeyindedir (2025 üst çeyrekteki 9 oyuncudan yalnız 1'i ortaktır).
- **5-Yard Wave Drill (Slide & Shuffle):** Kabul edilen **118 kaydın 118'inde (%100.0)** zirve hız çıkış sprintindedir; yanal kayma fazı hızı ile tüm kayıt hızı arasındaki sıralama korelasyonu **`r = −0.022`**'dir.
- **Pass Rush Drop (Kick-Slide):** Kabul edilen **239 kaydın 239'unda (%100.0)** zirve hız bitiş sprintindedir; pas seti yanal hızı ile tüm kayıt hızı arasındaki korelasyon **`r = +0.147`**'dir.
- **Sınır Sağlamlığı ve Fiziksel Değişmezlik:** Çıkış eşiği `1.0`, `1.5` veya `2.0 yard` seçildiğinde yanal hız sıralaması neredeyse değişmez (`Spearman r > 0.992`). Ayrıca 7 sentetik birim testi (koordinat öteleme, yansıtma, zaman kaydırma, satır sırası vb.) tam değişmezliği doğrular.

### 2. Tekrar Güvenilirliği (Repeatability) ve Psikometrik Zayıflama Sınırı

- Mirror drilinde oyuncu başına tek kayıt bulunurken, **Pass Rush Drop** drilinde **118 OL oyuncusunun ikişer takip kaydı** mevcuttur.
- İki deneme arasında **çıkış sprinti hızı orta-yüksek düzeyde tekrarlanabilirken (`r = +0.510`)**, koç/işaret yönlendirmeli **pas seti yanal hızı düşük tekrar güvenilirliğine sahiptir (`r = +0.104`)**.
- Psikometrik zayıflama teoremine ($r_{XY} \le \sqrt{r_{XX} \cdot r_{YY}}$) göre, koç komutuna bağlı drillerde tek denemelik yanal hızın düşük tekrar güvenilirliği, maç performansıyla olan korelasyonu matematiksel olarak sınırlandırmaktadır.

### 3. Çaylak Bire Bir Pas Koruması Doğrulaması (50 OL, 20.853 Snap)

Üç farklı hedef tanımında ileri-yıl (`2023 -> 2024` ve `2023–2024 -> 2025`) sızıntısız modeller (`Ridge alpha=10`) karşılaştırılmıştır:
1. **Birincil Hedef (İkili `pressure_allowed`, Süre Düzeltmeli):** 2025'te çıkış sprintiyle kirlenmiş `whole_drill_speed` eklemek MAE'yi `2.502`'den `2.652 pp`'ye kötüleştirirken, faz ayrıştırmalı `mirror_phase` özellikleri MAE'yi `2.482 pp`'ye (`+0.019 pp`) indirir. Ancak 400 tam yeniden eğitimli (full-refit) oyuncu bootstrap %95 güven aralığı **`[−0.264, +0.353] pp`** olup sıfırı içerir.
2. **Önceden Bildirilmiş Duyarlılık (Dropback Süresi Düzeltmesi Olmadan):** 2025 MAE `2.351`'den `2.365 pp`'ye değişir (`−0.014 pp`).
3. **Sürekli NGS Hedef Duyarlılığı (`peak_pressure_probability_allowed`):** İkili baskı etiketinin yarı-yarıya (split-half) maç güvenilirliği `r = 0.367` iken, sürekli NGS baskı olasılığının maç güvenilirliği **`r = 0.696`**'ya çıkar. Bu daha güvenilir hedefte de tüm-kayıt hızı 2025 MAE'yi kötüleştirirken (`2.189 -> 2.215 pp`), mirror fazı özellikleri MAE'yi `2.157 pp`'ye (`+0.032 pp`, RMSE `2.639 -> 2.532 pp`) iyileştirir; %95 güven aralığı `[−0.139, +0.195] pp` yine sıfırı kapsar.

### 4. Ara Hareket Kontrolü: Maçın İlk 1.5 Saniyesindeki Yanal Hız (20.110 Oyun)

- Oyuncuların maç içi erken yanal hızı maçtan maça oldukça kararlıdır (**split-half `r = 0.797`**), ancak Combine mirror yanal hızıyla korelasyonu zayıftır (`ham r = 0.053`, `yıl/pozisyon arındırılmış r = 0.120`) ve ileri-yıl MAE değerini düşürmez (`2024: 0.0916 -> 0.0923 yd/s`, `2025: 0.1070 -> 0.1087 yd/s`).

## Dosyalar

- **`mirror_explorer.html`**: İki dilli (`TR` / `EN`), yıl/pozisyon filtreli ve sıralamalı etkileşimli oyuncu faz inceleyicisi.
- `mirror_phase_story.png`: Üç draft sınıfından saha izi (`yard`), dönüş noktaları ve hız (`yd/s`) profilleri.
- `mirror_ranking_shift.png`: Sınıf içi yüzdelik kırılması (`r = +0.005`) ve 3 OL drilinde (`470/470`) çıkış sprinti baskınlığı.
- `mirror_model_comparison.png`: Üç pas koruma hedef tanımında ileri-yıl MAE karşılaştırması.
- `movement_bridge_results.png`: Maçın ilk 1.5 saniyesindeki yanal hız transferi.
- `ol_drill_suite_audit.csv`: 3 OL Combine drili faz denetimi özet tablosu.
- `mirror_all_phase_checks.pdf`: 113 kabul edilen kaydın tamamının görsel denetim sayfaları.
- `mirror_validation.json`: 7 fiziksel değişmezlik testi ve 400 tam yeniden eğitimli bootstrap sonuçları.

## Çalıştırma Komutları

```powershell
D:\NFL\.venv\Scripts\python.exe scripts/prepare_ol_metadata.py
D:\NFL\.venv\Scripts\python.exe scripts/extract_mirror_features.py
D:\NFL\.venv\Scripts\python.exe scripts/analyze_mirror_protection.py
D:\NFL\.venv\Scripts\python.exe scripts/extract_ol_movement.py
D:\NFL\.venv\Scripts\python.exe scripts/analyze_ol_movement.py
D:\NFL\.venv\Scripts\python.exe scripts/mirror_measurement_report.py
D:\NFL\.venv\Scripts\python.exe scripts/validate_mirror_study.py
```
