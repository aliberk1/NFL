# Ana Yarışma Teslim Paketi: OL Combine Faz Doğrulaması (`submission_mirror`)

Bu klasör, **NFL Big Data Bowl 2027** için ana yarışma teslim adayı olarak hazırlanan **"The Fastest Part Is the Exit: Phase-Aware Validation of Offensive Line Combine Tracking Across Drills, Movements, and Rookie Pass Protection"** çalışmasını içerir.

## Klasör İçeriği

- **`writeup_en.md`**: Kaggle Writeup yarışma metni (`< 2000` kelime sınırı içinde, 3 yayın kalitesinde görsel ve 2 kapsamlı tablo ile, doğrulanmış `yards` ve `yd/s` NGS fiziksel birimleriyle).
- **`mirror_phase_validation.ipynb` & `mirror_phase_validation.executed.ipynb`**: Ham yarışma CSV dosyalarından tüm faz ayrıştırmasını, 3-dril (`470` kayıt) denetimini, 2-tekrar güvenilirlik analizini, ikili ve sürekli NGS baskı olasılığı modellerini, erken maç hareketi (`0–1.5 s`) kontrolünü ve `400` tam yeniden eğitimli bootstrap belirsizlik analizini tek başına yeniden üreten CPU notebook'u.
- **`mirror_explorer.html`**: 113 Offensive Lineman için iki dilli (`TR` / `EN`), yıl ve pozisyon filtreli, sıralama seçenekli etkileşimli saha izi ve hız fazı inceleyicisi.
- **`figures/`**:
  - `mirror_phase_story.png`: 2023–2025 örnek oyuncularında saha izi (`yard`), tespit edilen dönüşler, `+1.5 yd` çıkış sınırı ve toplam hız $s(t)$ ile yanal hız $|v_y(t)|$ (`yd/s`) profilleri.
  - `mirror_ranking_shift.png`: Sınıf içi yüzdelik sıralama kırılması (`Spearman r = +0.005`) ve 3 OL Combine drilinde (`Mirror`, `5-Yard Wave`, `Pass Rush Drop` — `470/470` kayıt) %100 çıkış sprinti baskınlığı ile 2-tekrar güvenilirlik sınırı (`r = +0.510` vs. `r = +0.104`).
  - `mirror_model_comparison.png`: İkili baskı (süre düzeltmeli), ikili baskı (süre düzeltmesiz) ve sürekli NGS `peak_pressure_probability_allowed` hedeflerinde ileri-yıl (`2024` ve `2025`) MAE karşılaştırması.
  - `movement_bridge_results.png`: Maçın ilk `1.5` saniyesindeki yanal hız (`yd/s`) transfer analizi.
- **`verification.json` & `manifest.json`**: Bağımsız ortamda sıfırdan çalıştırma doğrulaması (`0` hata, `7/7` tablo birebir eşleşme) ve SHA-256 dosya bütünlük özeti.

## Kaggle Teslim Adımları

1. `mirror_phase_validation.ipynb` dosyasını Kaggle Notebook olarak içe aktarın, **NFL Big Data Bowl 2027** veri setini bağlayın ve CPU ile **Save & Run All (Commit)** çalıştırıp Notebook'u **Public** yapın.
2. Kaggle Writeup ekranında `writeup_en.md` metnini yapıştırın, `figures/` klasöründeki `mirror_phase_story.png`, `mirror_ranking_shift.png` ve `mirror_model_comparison.png` görsellerini yükleyin.
3. Çalıştırılmış Public Kaggle Notebook bağlantısını ve isteğe bağlı ek dosya olarak `mirror_explorer.html` inceleyicisini Writeup'a ekleyin.

## Yerel Yeniden Üretim ve Doğrulama

```powershell
D:\NFL\.venv\Scripts\python.exe scripts/build_mirror_notebook.py
D:\NFL\.venv\Scripts\python.exe scripts/verify_mirror_notebook.py
D:\NFL\.venv\Scripts\python.exe scripts/package_mirror_study.py
```
