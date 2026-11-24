# NFL Big Data Bowl 2027 — Proje Sonuç ve Değerlendirme Raporu

## 1. Neden `submission_mirror/` ("The Fastest Part Is the Exit") Yarışma İçin En Güçlü Çalışmadır?

NFL Big Data Bowl jürisi (NFL kulüp analistleri ve lig veri bilimcileri), aşırı uyum (overfitting) yapılmış kara-kutu modeller yerine **doğrudan futbol operasyonuna dokunan somut bir ölçüm keşfini**, **kusursuz istatistiksel doğrulamayı** ve **etkileşimli/görsel kanıtları** ödüllendirmektedir.

Bu projede yapılan uçtan uca analiz ve geliştirmeler sonucunda `submission_mirror/` çalışması dört temel sütun üzerine oturtulmuştur:

1. **Evrensel ve Çarpıcı Bir Ölçüm Keşfi (`470 / 470` Kayıtta `%100.0` Çıkış Sprinti Baskınlığı):**
   - Yalnızca `Pass-Pro Mirror Drill` (`113/113`) değil, tüm OL Combine ayak işi drillerinde (`5-Yard Wave Drill` `118/118` ve `Pass Rush Drop` `239/239` dahil toplam `470` kaydın tamamında) oyuncuların en yüksek hızı yanal koruma veya pas seti fazında değil, dril sonundaki **çıkış sprintinde** oluşmaktadır.
   - Faz ayrıştırması yapılmadığında "dril hızı" adı altında aslında düz koşu sprinti ölçülmekte ve oyuncu sıralamaları tamamen bozulmaktadır (`Mirror Spearman r = +0.005`, `Wave r = −0.022`, `Drop r = +0.147`).
2. **Tekrar Güvenilirliği (Repeatability) ile Matematiksel Açıklama:**
   - İkişer kez koşulan `Pass Rush Drop` drilinde (`118` OL çifti), çıkış sprinti hızı `r = +0.510` güvenilirlikle tekrarlanırken, koç/işaret yönlendirmeli yanal pas seti hızı yalnızca `r = +0.104` tekrar güvenilirliğine sahiptir. Bu bulgu, standartlaştırılmamış görsel/koç komutlarına dayalı drillerde tek denemelik ölçümlerin neden maç tahmininde psikometrik zayıflama (`attenuation`) sınırına takıldığını kanıtlar.
3. **İkili ve Sürekli NGS Hedeflerinde Sızıntısız İleri-Yıl (`Out-of-Time`) Modelleme (`50` OL, `20.853` Snap):**
   - Hem ikili `pressure_allowed` (maç yarı-yarıya güvenilirliği `r = 0.367`) hem de sürekli NGS `peak_pressure_probability_allowed` (maç yarı-yarıya güvenilirliği `r = 0.696`) hedeflerinde, çıkış sprintiyle kirlenmiş `whole_drill_speed` 2025 tahmin hatasını kötüleştirirken, faz ayrıştırmalı `mirror_phase` özellikleri hatayı doğru yönde azaltmaktadır (`2.502 -> 2.482 pp` ve `2.189 -> 2.157 pp`).
   - Buna karşın `400` tam yeniden eğitimli (full-refit) oyuncu bootstrap güven aralığı (`[−0.264, +0.353] pp`) sıfırı içermektedir; bu nedenle sonuçlar abartılmadan, dürüst bir **4-aşamalı doğrulama hunisi** olarak sunulmuştur.
4. **İki Dilli (`TR` / `EN`) Etkileşimli Oyuncu Faz İnceleyicisi (`mirror_explorer.html`):**
   - 113 OL oyuncusunun tamamı için draft yılı, pozisyon (`T/G/C`) ve sıralama ölçütüne göre filtreleme yapan, saha izini (`yard`), `+1.5 yd` çıkış sınırını, tespit edilen dönüşleri ve toplam hız $s(t)$ ile yanal hız $|v_y(t)|$ (`yd/s`) eğrilerini gösteren tek-dosyalık çevrimdışı HTML aracı hazırlanmıştır.

## 2. Teslim Dosyaları

- **Ana Yarışma Metni (İngilizce, `< 2000` kelime):** `submission_mirror/writeup_en.md`
- **Doğrulanmış Kaggle Notebook:** `submission_mirror/mirror_phase_validation.ipynb` ve `submission_mirror/mirror_phase_validation.executed.ipynb`
- **Görseller (`submission_mirror/figures/`):**
  - `mirror_phase_story.png`
  - `mirror_ranking_shift.png`
  - `mirror_model_comparison.png`
  - `movement_bridge_results.png`
- **Etkileşimli İnceleyici:** `submission_mirror/mirror_explorer.html`
- **Tam Teslim Paketi:** `NFL_2027_mirror_arastirma_paketi.zip`
